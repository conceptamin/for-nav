# 진료과 모델 A(backlog 06): 버튼 피처 → 질환 확률(LightGBM 다중 분류) → 질환별 진료과 비율로 합산 → Department 10종 분포.
# - 입력은 features/buttons.py의 FEATURE_NAMES 순서 그대로다. 학습 원본(Kaggle)에는 부위·증상만 있어 나머지 피처는 전부 결측이고,
#   LightGBM은 학습 때 값이 없던 피처로는 분기하지 않으므로 서빙 때 그 값이 들어와도 예측이 바뀌지 않는다(테스트로 확인).
# - 질환명은 이 모듈 안에서만 쓴다. 내보내는 파일에는 질환 번호(클래스 순서)별 진료과 비율 행렬만 두고, 출력·메타데이터·리포트에는
#   질환명을 넣지 않는다. 진료과 정답은 질환 라벨을 disease_department.csv로 바꾼 1순위 진료과다.
# - 학습 데이터(backlog 16): Kaggle + DDXPlus를 합친 표(data/split.py). 질환 라벨 80개, 진료과 비율은 disease_department.csv.
#   클래스는 그 표의 라벨 전부다(train에 없는 라벨도 둔다. 벡터 단위로 나누면 행이 적은 질환이 train에 안 들어갈 수 있다).
# - 가중치: split.train_weights(같은 벡터 안 질환 몫 × 출처마다 합이 같게). 라운드 수는 train 안 3겹 교차검증으로 정하고,
#   겹은 버튼 벡터 단위로 나눈다(같은 벡터가 두 겹에 있으면 조기 종료가 늦어진다. v2는 189행에 954라운드였다).

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

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
CV_FOLDS = 3

MODEL_FILE = "model.txt"  # LightGBM 텍스트(질환 번호 0..K-1을 예측한다)
DEPARTMENTS_FILE = "departments.json"  # 질환 번호별 진료과 비율 행렬. 질환명은 없다
METADATA_FILE = "metadata.json"  # 임시 형식. 확정은 backlog 08


class DeptA:
    name = "dept_a"

    def __init__(self, booster: lgb.Booster | None = None, class_departments: np.ndarray | None = None):
        self.booster = booster
        self.class_departments = class_departments  # (질환 수, len(DEPARTMENTS)), 행 합 1

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        class_departments: np.ndarray,
        num_rounds: int | None = None,
        weight: np.ndarray | None = None,
        groups: np.ndarray | None = None,
    ) -> "DeptA":
        """y는 질환 번호(0..K-1). num_rounds를 주지 않으면 X, y 안에서 교차검증 조기 종료로 정한다(groups가 있으면 그룹 단위 겹)."""
        params = PARAMS | {"num_class": len(class_departments)}
        if num_rounds is None:
            num_rounds = cv_num_rounds(X, y, params, weight, groups)
        self.booster = lgb.train(params, _dataset(X, y, weight), num_boost_round=num_rounds)
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


def cv_num_rounds(X: np.ndarray, y: np.ndarray, params: dict, weight: np.ndarray | None = None, groups: np.ndarray | None = None) -> int:
    result = lgb.cv(
        params,
        _dataset(X, y, weight),
        num_boost_round=MAX_ROUNDS,
        folds=list(_folds(X, y, groups)),
        callbacks=[lgb.early_stopping(EARLY_STOPPING_ROUNDS, verbose=False)],
    )
    return len(result["valid multi_logloss-mean"])


def _folds(X: np.ndarray, y: np.ndarray, groups: np.ndarray | None):
    """층화 겹. groups가 있으면 같은 그룹(버튼 벡터)은 한 겹에만 둔다."""
    groups = np.arange(len(y)) if groups is None else groups
    return StratifiedGroupKFold(CV_FOLDS, shuffle=True, random_state=SEED).split(X, y, groups)


def _dataset(X: np.ndarray, y: np.ndarray, weight: np.ndarray | None = None) -> lgb.Dataset:
    return lgb.Dataset(X, label=y, weight=weight, feature_name=list(FEATURE_NAMES), free_raw_data=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


# ---- 라운드 실행: 학습·검증셋 평가·저장(scripts/train_dept_a.py), test 평가(scripts/evaluate.py) ----


def train_round(processed_dir: Path, splits_dir: Path, tables_dir: Path, model_dir: Path, reports_dir: Path, round_name: str) -> dict:
    """train으로 학습하고 valid(출처별)와 진료과 검증셋(department_guide.csv)으로 평가해 저장한다. test는 읽지 않는다."""
    train, valid = (split.load_symptom_dev(processed_dir, splits_dir, name) for name in split.DEV_SPLITS)
    disease_department = dept.read_disease_department(tables_dir)
    classes = sorted(disease_department)
    if unknown := (set(train["disease"]) | set(valid["disease"])) - set(classes):
        raise ValueError(f"disease_department.csv에 없는 질환 라벨 {len(unknown)}개 — scripts/build_tables.py를 다시 돌린다")
    matrix = class_department_matrix(classes, disease_department)
    X_train, y_train = featurize_many(train.to_dict("records")), _encode(train["disease"], classes)
    X_valid, y_valid = featurize_many(valid.to_dict("records")), _encode(valid["disease"], classes)
    w_train, g_train = split.train_weights(train), train["vector"].to_numpy()

    model = DeptA().fit(X_train, y_train, matrix, weight=w_train, groups=g_train)
    dev = pd.concat([train, valid], ignore_index=True)
    results = {
        "valid": evaluate_rows(model, valid, disease_department),
        "valid_baseline_prior": _prior_baseline(y_train, w_train, matrix, valid, disease_department),
        "cv_train_valid": _cv_train_valid(
            model.num_rounds,
            np.vstack([X_train, X_valid]),
            np.concatenate([y_train, y_valid]),
            matrix,
            dev,
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
        "num_rounds_rule": f"train 안 층화 {CV_FOLDS}겹 교차검증(버튼 벡터 그룹 단위), multi_logloss 조기 종료({EARLY_STOPPING_ROUNDS}라운드)",
        "data": {
            "processed_sha256": sha256_file(processed_dir / split.SYMPTOM_PROCESSED_FILE),
            **{f"{name}_ids_sha256": sha256_file(split.split_path(splits_dir, name, "symptom")) for name in split.DEV_SPLITS},
            "disease_department_sha256": sha256_file(tables_dir / dept.DISEASE_DEPARTMENT),
            "rows": {"train": len(train), "valid": len(valid)},
            "rows_by_source": {name: _count(part["source"]) for name, part in (("train", train), ("valid", valid))},
            "classes": len(classes),
            "classes_in_train": int(train["disease"].nunique()),
            "sources": {
                "kaggle": "Kaggle Disease Symptom Prediction(CC BY-SA 4.0)",
                "ddxplus": "DDXPlus(CC BY 4.0, 합성 환자). 근거·질환 매핑 표는 LLM 초안이고 사람 검토 전(reviewed=no, 사용자 결정 2026-11-19)",
            },
            "weight_rule": "같은 출처·같은 버튼 벡터 안 질환 몫(DDXPlus 환자 수 비율, Kaggle 균등) × 출처마다 합이 같게",
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
        "status": "학습 라운드. 서빙 묶음은 export.py가 쓴다",
        "files": {name: sha256_text(text) for name, text in files.items()},
        "output": "질환 확률(내부) × departments.json의 질환 번호별 진료과 비율 → 진료과 10종 확률",
    }
    (model_dir / METADATA_FILE).write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    _write_report(
        reports_dir,
        f"dept_a_{round_name}",
        report,
        {
            **{f"LightGBM valid {k}": v for k, v in results["valid"].items()},
            **{
                f"기준선(train 질환 빈도) valid {k}": v for k, v in results["valid_baseline_prior"].items() if k in ("전체", *split.SOURCES)
            },
            "LightGBM train+valid 3겹 교차검증(벡터 그룹)": results["cv_train_valid"]["department"],
            "LightGBM 진료과 검증셋(guide) 전체": results["guide"]["all"],
            "LightGBM 진료과 검증셋(guide) reviewed=yes": results["guide"]["reviewed_yes"],
        },
    )
    return report


BUTTON_BUCKETS = (("버튼 2개", 2, 2), ("버튼 3~4개", 3, 4), ("버튼 5개 이상", 5, 99))  # 부위 + 증상 수. 앱 사용자는 보통 2~3개


def row_masks(rows: pd.DataFrame) -> dict[str, np.ndarray]:
    """평가를 나눠 적는 행 묶음: 전체, 출처별, 버튼 수별(부위 + 증상)."""
    buttons = np.array([len(b) + len(s) for b, s in zip(rows["body_parts"], rows["symptoms"], strict=True)])
    masks = {"전체": np.ones(len(rows), dtype=bool)}
    masks |= {source: (rows["source"] == source).to_numpy() for source in split.SOURCES}
    masks |= {name: (buttons >= lo) & (buttons <= hi) for name, lo, hi in BUTTON_BUCKETS}
    return masks


def evaluate_rows(model: "DeptA", rows: pd.DataFrame, disease_department) -> dict[str, dict]:
    """행 묶음마다 진료과 Top-k(분자·분모). 행이 없는 묶음은 뺀다."""
    proba = model.predict_proba(featurize_many(rows.to_dict("records")))
    y = true_departments(rows["disease"], disease_department)
    return {name: topk_metrics(proba[m], y[m], DEPARTMENTS) for name, m in row_masks(rows).items() if m.any()}


def evaluate_guide(model: DeptA, tables_dir: Path, splits_dir: Path) -> dict:
    """진료과 검증셋(backlog 05): 조합 하나(부위 1, 증상 1, 손상 여부) → 진료과 Top-k. 정답은 안내 페이지의 1순위."""
    ids, guide = dept.guide_set(tables_dir, splits_dir)
    proba = model.predict_proba(featurize_many([dept.combo_intake(cid) for cid in ids]))
    y = np.array([DEPARTMENTS.index(guide[cid].department) for cid in ids], dtype=np.int64)
    reviewed = np.array([guide[cid].reviewed for cid in ids])
    return {
        "all": topk_metrics(proba, y, DEPARTMENTS),
        "reviewed_yes": topk_metrics(proba[reviewed], y[reviewed], DEPARTMENTS) if reviewed.any() else None,
        "reviewed_no_rows": int((~reviewed).sum()),
    }


def evaluate_test_round(test: pd.DataFrame, model_dir: Path, tables_dir: Path, reports_dir: Path, round_name: str) -> dict:
    """저장한 모델로 test(출처별·버튼 수별)를 평가해 '최종'으로 기록한다. 라운드마다 한 번만 — 이미 있으면 멈춘다."""
    name = f"dept_a_{round_name}_test"
    if (reports_dir / f"{name}.json").exists():
        raise FileExistsError(f"{name}.json이 이미 있다. test 평가는 라운드마다 한 번만 한다. 조정했다면 새 라운드로 기록한다")
    metadata = json.loads((model_dir / METADATA_FILE).read_text())
    texts = {f: (model_dir / f).read_text() for f in (MODEL_FILE, DEPARTMENTS_FILE)}
    if {f: sha256_text(t) for f, t in texts.items()} != metadata["files"]:
        raise ValueError(f"{model_dir}의 모델 파일이 {METADATA_FILE}에 적힌 해시와 다르다")
    result = evaluate_rows(DeptA.from_files(texts), test, dept.read_disease_department(tables_dir))
    report = {
        "round": round_name,
        "final": True,
        "note": "test 평가는 이 라운드에서 한 번만 했다",
        "rows": len(test),
        "rows_by_source": _count(test["source"]),
        "files": metadata["files"],
        "department": result,
    }
    _write_report(reports_dir, name, report, {f"LightGBM test {k} — 최종": v for k, v in result.items()})
    return report


def _count(values) -> dict[str, int]:
    return {k: int(v) for k, v in pd.Series(values).value_counts().sort_index().items()}


def _encode(diseases, classes: list[str]) -> np.ndarray:
    index = {c: i for i, c in enumerate(classes)}
    return np.array([index[d] for d in diseases], dtype=np.int64)


def _prior_baseline(y_train: np.ndarray, w_train: np.ndarray, matrix: np.ndarray, rows: pd.DataFrame, disease_department) -> dict:
    """입력을 보지 않고 train 질환 빈도(학습 가중치) × 진료과 비율로 같은 분포를 내는 기준선. 행 묶음마다."""
    prior = np.bincount(y_train, weights=w_train, minlength=len(matrix)) / w_train.sum() @ matrix
    proba, y = np.tile(prior, (len(rows), 1)), true_departments(rows["disease"], disease_department)
    return {name: topk_metrics(proba[m], y[m], DEPARTMENTS) for name, m in row_masks(rows).items() if m.any()}


def _cv_train_valid(num_rounds: int, X: np.ndarray, y: np.ndarray, matrix: np.ndarray, rows: pd.DataFrame, disease_department) -> dict:
    """train+valid를 벡터 그룹 층화 3겹으로 나눠 각 행을 그 행이 빠진 모델로 예측한다(라운드 수는 train으로 정한 값 고정)."""
    proba = np.zeros((len(y), len(DEPARTMENTS)))
    disease_hit = np.zeros(len(y), dtype=bool)
    groups = rows["vector"].to_numpy()
    for train_idx, held_idx in _folds(X, y, groups):
        part = rows.iloc[train_idx]
        model = DeptA().fit(X[train_idx], y[train_idx], matrix, num_rounds=num_rounds, weight=split.train_weights(part))
        proba[held_idx] = model.predict_proba(X[held_idx])
        disease_hit[held_idx] = model.predict_disease_proba(X[held_idx]).argmax(axis=1) == y[held_idx]
    return {
        "department": topk_metrics(proba, true_departments(rows["disease"], disease_department), DEPARTMENTS),
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
