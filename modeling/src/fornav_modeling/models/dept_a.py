# 진료과 모델 A(backlog 06): 버튼 피처 → 질환 확률(LightGBM 다중 분류) → 질환별 진료과 비율로 합산 → Department 10종 분포.
# - 입력은 features/buttons.py의 FEATURE_NAMES 순서 그대로다. 학습 원본(Kaggle)에는 부위·증상만 있어 나머지 피처는 전부 결측이고,
#   LightGBM은 학습 때 값이 없던 피처로는 분기하지 않으므로 서빙 때 그 값이 들어와도 예측이 바뀌지 않는다(테스트로 확인).
# - 질환명은 이 모듈 안에서만 쓴다. 내보내는 파일에는 질환 번호(클래스 순서)별 진료과 비율 행렬만 두고, 출력·메타데이터·리포트에는
#   질환명을 넣지 않는다. 진료과 정답은 질환 라벨을 disease_department.csv로 바꾼 1순위 진료과다.
# - 데이터가 작다(train 189행, 질환 40종, 질환당 2~7행). 잎 크기를 작게 두고 라운드 수는 train 안 3겹 교차검증으로 정한다.

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold

from fornav_modeling.data import split
from fornav_modeling.data.download import sha256_file
from fornav_modeling.evaluate import topk_metrics, topk_table
from fornav_modeling.features.buttons import FEATURE_NAMES, featurize, featurize_many
from fornav_modeling.labels import department as dept
from fornav_modeling.schema import DEPARTMENTS, Department

SEED = 20261028
PARAMS = {
    "objective": "multiclass",
    "learning_rate": 0.05,
    "num_leaves": 7,
    "min_data_in_leaf": 3,
    "lambda_l2": 1.0,
    "seed": SEED,
    "deterministic": True,
    "num_threads": 1,
    "force_row_wise": True,
    "verbosity": -1,
}
MAX_ROUNDS = 1000
EARLY_STOPPING_ROUNDS = 50
CV_FOLDS = 3  # 질환당 train 행이 2~7개라 5겹은 한 겹에 질환이 빠진다

MODEL_FILE = "model.txt"  # LightGBM 텍스트(질환 번호 0..K-1을 예측한다)
DEPARTMENTS_FILE = "departments.json"  # 질환 번호별 진료과 비율 행렬. 질환명은 없다
METADATA_FILE = "metadata.json"  # 임시 형식. 확정은 backlog 08


class DeptA:
    name = "dept_a"

    def __init__(self, booster: lgb.Booster | None = None, class_departments: np.ndarray | None = None):
        self.booster = booster
        self.class_departments = class_departments  # (질환 수, len(DEPARTMENTS)), 행 합 1

    def fit(self, X: np.ndarray, y: np.ndarray, class_departments: np.ndarray, num_rounds: int | None = None) -> "DeptA":
        """y는 질환 번호(0..K-1). num_rounds를 주지 않으면 X, y 안에서 교차검증 조기 종료로 정한다."""
        params = PARAMS | {"num_class": len(class_departments)}
        if num_rounds is None:
            num_rounds = cv_num_rounds(X, y, params)
        self.booster = lgb.train(params, _dataset(X, y), num_boost_round=num_rounds)
        self.class_departments = class_departments
        return self

    @property
    def num_rounds(self) -> int:
        return self.booster.current_iteration()

    def predict_disease_proba(self, X: np.ndarray) -> np.ndarray:
        """내부 산출물. 바깥으로 내보내지 않는다."""
        return self.booster.predict(X)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """(행 수, len(DEPARTMENTS)) 진료과 확률. 질환 확률 × 질환별 진료과 비율의 합."""
        return self.predict_disease_proba(X) @ self.class_departments

    def to_files(self) -> dict[str, str]:
        departments = {"labels": list(DEPARTMENTS), "class_departments": np.round(self.class_departments, 6).tolist()}
        return {MODEL_FILE: self.booster.model_to_string(), DEPARTMENTS_FILE: json.dumps(departments, indent=1) + "\n"}

    @classmethod
    def from_files(cls, texts: Mapping[str, str]) -> "DeptA":
        departments = json.loads(texts[DEPARTMENTS_FILE])
        if departments["labels"] != list(DEPARTMENTS):
            raise ValueError(f"{DEPARTMENTS_FILE}의 진료과 순서가 지금 코드와 다르다")
        booster = lgb.Booster(model_str=texts[MODEL_FILE])
        if booster.feature_name() != list(FEATURE_NAMES):
            raise ValueError(f"{MODEL_FILE}의 피처 순서가 지금 코드와 다르다")
        return cls(booster, np.array(departments["class_departments"], dtype=np.float64))


def department_proba(model: DeptA, intake: Mapping[str, Any]) -> dict[Department, float]:
    """입력 dict 하나 → {진료과: 확률}. 키는 DEPARTMENTS 10종 그대로(순서 포함)이고 질환명은 없다."""
    proba = model.predict_proba(np.array([featurize(intake)], dtype=np.float64))[0]
    return {d: float(p) for d, p in zip(DEPARTMENTS, proba, strict=True)}


def class_department_matrix(classes: list[str], disease_department: Mapping[str, dept.Distribution]) -> np.ndarray:
    """질환 순서 → (질환 수, 진료과 수) 비율 행렬."""
    if missing := [c for c in classes if c not in disease_department]:
        raise KeyError(f"disease_department.csv에 없는 질환 {len(missing)}개")
    return np.array([[disease_department[c].get(d, 0.0) for d in DEPARTMENTS] for c in classes], dtype=np.float64)


def true_departments(diseases, disease_department: Mapping[str, dept.Distribution]) -> np.ndarray:
    """질환 라벨 → 1순위 진료과 번호(DEPARTMENTS 순서). 진료과 Top-k 적중률의 정답."""
    return np.array([DEPARTMENTS.index(dept.top(disease_department[d], 1)[0]) for d in diseases], dtype=np.int64)


def cv_num_rounds(X: np.ndarray, y: np.ndarray, params: dict) -> int:
    result = lgb.cv(
        params,
        _dataset(X, y),
        num_boost_round=MAX_ROUNDS,
        folds=StratifiedKFold(CV_FOLDS, shuffle=True, random_state=SEED).split(X, y),
        callbacks=[lgb.early_stopping(EARLY_STOPPING_ROUNDS, verbose=False)],
    )
    return len(result["valid multi_logloss-mean"])


def _dataset(X: np.ndarray, y: np.ndarray) -> lgb.Dataset:
    return lgb.Dataset(X, label=y, feature_name=list(FEATURE_NAMES), free_raw_data=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


# ---- 라운드 실행: 학습·검증셋 평가·저장(scripts/train_dept_a.py), test 평가(scripts/evaluate.py) ----


def train_round(processed_dir: Path, splits_dir: Path, tables_dir: Path, model_dir: Path, reports_dir: Path, round_name: str) -> dict:
    """train으로 학습하고 valid(Kaggle)와 진료과 검증셋(department_guide.csv)으로 평가해 저장한다. test는 읽지 않는다."""
    train, valid = (split.load_symptom_dev(processed_dir, splits_dir, name) for name in split.DEV_SPLITS)
    disease_department = dept.read_disease_department(tables_dir)
    classes = sorted(train["disease"].unique())
    if unseen := set(valid["disease"]) - set(classes):
        raise ValueError(f"valid에만 있는 질환 {len(unseen)}개 — 분할을 확인한다")
    matrix = class_department_matrix(classes, disease_department)
    X_train, y_train = featurize_many(train.to_dict("records")), _encode(train["disease"], classes)
    X_valid, y_valid = featurize_many(valid.to_dict("records")), _encode(valid["disease"], classes)

    model = DeptA().fit(X_train, y_train, matrix)
    results = {
        "valid": _evaluate(model, X_valid, valid["disease"], y_valid, disease_department),
        "valid_baseline_prior": _prior_baseline(y_train, matrix, valid["disease"], disease_department),
        "cv_train_valid": _cv_train_valid(
            model.num_rounds,
            np.vstack([X_train, X_valid]),
            np.concatenate([y_train, y_valid]),
            matrix,
            pd.concat([train["disease"], valid["disease"]]),
            disease_department,
        ),
        "guide": evaluate_guide(model, tables_dir, splits_dir),
    }

    files = model.to_files()
    _refuse_if_tested(model_dir, reports_dir, round_name, files)
    report = {
        "round": round_name,
        "model_version": f"dept_a/{round_name}",
        "seed": SEED,
        "lightgbm_params": PARAMS | {"num_class": len(classes)},
        "num_rounds": model.num_rounds,
        "num_rounds_rule": f"train 안 층화 {CV_FOLDS}겹 교차검증, multi_logloss 조기 종료({EARLY_STOPPING_ROUNDS}라운드)",
        "data": {
            "processed_sha256": sha256_file(processed_dir / split.SYMPTOM_PROCESSED_FILE),
            **{f"{name}_ids_sha256": sha256_file(split.split_path(splits_dir, name, "symptom")) for name in split.DEV_SPLITS},
            "disease_department_sha256": sha256_file(tables_dir / dept.DISEASE_DEPARTMENT),
            "rows": {"train": len(train), "valid": len(valid)},
            "classes": len(classes),
        },
        "feature_names": list(FEATURE_NAMES),
        "labels": list(DEPARTMENTS),
        "truth": "질환 라벨을 disease_department.csv로 바꾼 1순위 진료과",
        "results": results,
    }

    model_dir.mkdir(parents=True, exist_ok=True)
    for file_name, text in files.items():
        (model_dir / file_name).write_text(text)
    metadata = {k: report[k] for k in ("model_version", "seed", "lightgbm_params", "num_rounds", "data", "feature_names", "labels")}
    metadata |= {
        "status": "임시(backlog 06). 형식 확정은 backlog 08",
        "files": {name: sha256_text(text) for name, text in files.items()},
        "output": "질환 확률(내부) × departments.json의 질환 번호별 진료과 비율 → 진료과 10종 확률",
    }
    (model_dir / METADATA_FILE).write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    _write_report(
        reports_dir,
        f"dept_a_{round_name}",
        report,
        {
            "LightGBM valid(Kaggle)": results["valid"]["department"],
            "기준선: train 질환 빈도 valid(Kaggle)": results["valid_baseline_prior"],
            "LightGBM train+valid 3겹 교차검증": results["cv_train_valid"]["department"],
            "LightGBM 진료과 검증셋(guide)": results["guide"]["all"],
        },
    )
    return report


def evaluate_guide(model: DeptA, tables_dir: Path, splits_dir: Path) -> dict:
    """진료과 검증셋(backlog 05): 조합 하나(부위 1, 증상 1, 손상 여부) → 진료과 Top-k. 정답은 안내 페이지의 1순위."""
    guide = dept.read_guide(tables_dir)
    ids = (splits_dir / dept.VALID_IDS).read_text().split()
    if ids != sorted(guide):
        raise ValueError(f"{dept.VALID_IDS}와 {dept.GUIDE}가 다르다. scripts/build_tables.py를 다시 돌린다")
    injury = {"yes": True, "no": False, "any": None}
    intakes = []
    for cid in ids:
        body_part, symptom, inj = cid.split("-")
        intakes.append({"body_parts": [body_part], "symptoms": [symptom], "injury": injury[inj]})
    proba = model.predict_proba(featurize_many(intakes))
    y = np.array([DEPARTMENTS.index(guide[cid].department) for cid in ids], dtype=np.int64)
    reviewed = np.array([guide[cid].reviewed for cid in ids])
    return {
        "all": topk_metrics(proba, y, DEPARTMENTS),
        "reviewed_yes": topk_metrics(proba[reviewed], y[reviewed], DEPARTMENTS) if reviewed.any() else None,
        "reviewed_no_rows": int((~reviewed).sum()),
    }


def evaluate_test_round(test: pd.DataFrame, model_dir: Path, tables_dir: Path, reports_dir: Path, round_name: str) -> dict:
    """저장한 모델로 test(Kaggle)를 평가해 '최종'으로 기록한다. 라운드마다 한 번만 — 이미 있으면 멈춘다."""
    name = f"dept_a_{round_name}_test"
    if (reports_dir / f"{name}.json").exists():
        raise FileExistsError(f"{name}.json이 이미 있다. test 평가는 라운드마다 한 번만 한다. 조정했다면 새 라운드로 기록한다")
    metadata = json.loads((model_dir / METADATA_FILE).read_text())
    texts = {f: (model_dir / f).read_text() for f in (MODEL_FILE, DEPARTMENTS_FILE)}
    if {f: sha256_text(t) for f, t in texts.items()} != metadata["files"]:
        raise ValueError(f"{model_dir}의 모델 파일이 {METADATA_FILE}에 적힌 해시와 다르다")
    model = DeptA.from_files(texts)
    X = featurize_many(test.to_dict("records"))
    y = true_departments(test["disease"], dept.read_disease_department(tables_dir))
    result = topk_metrics(model.predict_proba(X), y, DEPARTMENTS)
    report = {
        "round": round_name,
        "final": True,
        "note": "test 평가는 이 라운드에서 한 번만 했다",
        "rows": len(test),
        "files": metadata["files"],
        "department": result,
    }
    _write_report(reports_dir, name, report, {"LightGBM test(Kaggle) — 최종": result})
    return report


def _encode(diseases, classes: list[str]) -> np.ndarray:
    return np.array([classes.index(d) for d in diseases], dtype=np.int64)


def _evaluate(model: DeptA, X: np.ndarray, diseases, y: np.ndarray, disease_department) -> dict:
    disease_hit = model.predict_disease_proba(X).argmax(axis=1) == y
    return {
        "department": topk_metrics(model.predict_proba(X), true_departments(diseases, disease_department), DEPARTMENTS),
        "disease_top1": {"n": int(disease_hit.sum()), "of": len(y)},  # 질환명 없이 건수만
    }


def _prior_baseline(y_train: np.ndarray, matrix: np.ndarray, diseases, disease_department) -> dict:
    """입력을 보지 않고 train 질환 빈도 × 진료과 비율로 같은 분포를 내는 기준선."""
    prior = np.bincount(y_train, minlength=len(matrix)) / len(y_train) @ matrix
    return topk_metrics(np.tile(prior, (len(diseases), 1)), true_departments(diseases, disease_department), DEPARTMENTS)


def _cv_train_valid(num_rounds: int, X: np.ndarray, y: np.ndarray, matrix: np.ndarray, diseases: pd.Series, disease_department) -> dict:
    """train+valid를 층화 3겹으로 나눠 각 행을 그 행이 빠진 모델로 예측한다(라운드 수는 train으로 정한 값 고정)."""
    proba = np.zeros((len(y), len(DEPARTMENTS)))
    disease_hit = np.zeros(len(y), dtype=bool)
    for train_idx, held_idx in StratifiedKFold(CV_FOLDS, shuffle=True, random_state=SEED).split(X, y):
        model = DeptA().fit(X[train_idx], y[train_idx], matrix, num_rounds=num_rounds)
        proba[held_idx] = model.predict_proba(X[held_idx])
        disease_hit[held_idx] = model.predict_disease_proba(X[held_idx]).argmax(axis=1) == y[held_idx]
    return {
        "department": topk_metrics(proba, true_departments(diseases, disease_department), DEPARTMENTS),
        "disease_top1": {"n": int(disease_hit.sum()), "of": len(y)},
    }


def _refuse_if_tested(model_dir: Path, reports_dir: Path, round_name: str, files: dict[str, str]) -> None:
    if not (reports_dir / f"dept_a_{round_name}_test.json").exists():
        return
    old = {f: (model_dir / f).read_text() if (model_dir / f).exists() else None for f in files}
    if old != files:
        raise FileExistsError(f"{round_name}는 이미 test로 평가했는데 모델이 달라졌다. 새 라운드 이름으로 학습한다")


def _write_report(reports_dir: Path, name: str, report: dict, table: dict[str, dict]) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / f"{name}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    (reports_dir / f"{name}.md").write_text(f"# {name}\n\n진료과 Top-k 적중률(분자/분모)\n\n" + topk_table(table))
