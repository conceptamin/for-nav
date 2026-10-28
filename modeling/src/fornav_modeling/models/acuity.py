# 응급도 3단계 분류(backlog 04). 입력은 버튼 피처(features/buttons.py의 FEATURE_NAMES 순서)뿐이다.
# - LightGBMAcuity: 서빙 후보. seed·deterministic·num_threads=1로 고정해 같은 데이터면 같은 모델 문자열이 나온다
# - LogisticAcuity: 비교 모델. 같은 인터페이스(fit, predict_proba, to_text/from_text)
# 결정 규칙(decide): emergency 확률이 임계값 이상이면 emergency, 아니면 나머지 두 클래스 중 확률이 큰 쪽.
# 임계값은 검증셋으로만 정한다(select_threshold). 내보내기 형식은 pickle을 쓰지 않는다(LightGBM 텍스트, JSON).

import hashlib
import json
import math
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler

from fornav_modeling.data import split
from fornav_modeling.data.download import sha256_file
from fornav_modeling.evaluate import classification_metrics, metrics_table
from fornav_modeling.explain import top_contributions
from fornav_modeling.features.buttons import FEATURE_NAMES, featurize_many
from fornav_modeling.labels.ktas import ACUITIES
from fornav_modeling.schema import ONSETS

SEED = 20261028
EMERGENCY = ACUITIES.index("emergency")
TARGET_RECALL = 0.95  # 검증셋 응급 재현율 목표(사용자와 정함, backlog 04)

LGBM_PARAMS = {
    "objective": "multiclass",
    "num_class": len(ACUITIES),
    "learning_rate": 0.05,
    "num_leaves": 15,
    "min_data_in_leaf": 20,
    "lambda_l2": 1.0,
    "seed": SEED,
    "deterministic": True,
    "num_threads": 1,
    "force_row_wise": True,  # deterministic=True일 때 히스토그램 방식을 고정한다
    "verbosity": -1,
}
MAX_ROUNDS = 1000
EARLY_STOPPING_ROUNDS = 50
CV_FOLDS = 5


class LightGBMAcuity:
    name = "lightgbm"

    def __init__(self, booster: lgb.Booster | None = None):
        self.booster = booster

    def fit(self, X: np.ndarray, y: np.ndarray, num_rounds: int | None = None) -> "LightGBMAcuity":
        """num_rounds를 주지 않으면 X, y 안에서 5겹 교차검증 조기 종료로 정한다(검증셋·테스트셋은 쓰지 않는다)."""
        if num_rounds is None:
            num_rounds = cv_num_rounds(X, y)
        self.booster = lgb.train(LGBM_PARAMS, _dataset(X, y), num_boost_round=num_rounds)
        return self

    @property
    def num_rounds(self) -> int:
        return self.booster.current_iteration()

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return self.booster.predict(X)

    def to_text(self) -> str:
        return self.booster.model_to_string()

    @classmethod
    def from_text(cls, text: str) -> "LightGBMAcuity":
        return cls(lgb.Booster(model_str=text))


class LogisticAcuity:
    """결측은 학습 중앙값으로 채우고 표준화한 뒤 다항 로지스틱 회귀. 예측은 저장한 수치만으로 numpy로 한다."""

    name = "logistic"

    def __init__(self, params: dict[str, np.ndarray] | None = None):
        self.params = params

    def fit(self, X: np.ndarray, y: np.ndarray) -> "LogisticAcuity":
        # keep_empty_features: 학습 데이터 전체가 결측인 열(onset)도 0으로 남겨 피처 순서를 유지한다
        imputer = SimpleImputer(strategy="median", keep_empty_features=True).fit(X)
        scaler = StandardScaler().fit(imputer.transform(X))
        clf = LogisticRegression(C=1.0, max_iter=5000).fit(scaler.transform(imputer.transform(X)), y)
        if clf.classes_.tolist() != list(range(len(ACUITIES))):
            raise ValueError(f"학습 데이터에 없는 클래스가 있다: {clf.classes_}")
        self.params = {
            "median": imputer.statistics_,
            "mean": scaler.mean_,
            "scale": scaler.scale_,
            "coef": clf.coef_,
            "intercept": clf.intercept_,
        }
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        p = self.params
        X = np.where(np.isnan(X), p["median"], X)
        logits = ((X - p["mean"]) / p["scale"]) @ p["coef"].T + p["intercept"]
        logits -= logits.max(axis=1, keepdims=True)
        exp = np.exp(logits)
        return exp / exp.sum(axis=1, keepdims=True)

    def to_text(self) -> str:
        payload = {"feature_names": list(FEATURE_NAMES), "labels": list(ACUITIES), **{k: v.tolist() for k, v in self.params.items()}}
        return json.dumps(payload, indent=1) + "\n"

    @classmethod
    def from_text(cls, text: str) -> "LogisticAcuity":
        payload = json.loads(text)
        if payload["feature_names"] != list(FEATURE_NAMES) or payload["labels"] != list(ACUITIES):
            raise ValueError("저장된 로지스틱 모델의 피처·라벨 순서가 지금 코드와 다르다")
        return cls({k: np.array(payload[k], dtype=np.float64) for k in ("median", "mean", "scale", "coef", "intercept")})


def encode_labels(labels) -> np.ndarray:
    return np.array([ACUITIES.index(a) for a in labels], dtype=np.int64)


def cv_num_rounds(X: np.ndarray, y: np.ndarray) -> int:
    """층화 5겹 교차검증에서 multi_logloss가 가장 낮은 라운드 수."""
    result = lgb.cv(
        LGBM_PARAMS,
        _dataset(X, y),
        num_boost_round=MAX_ROUNDS,
        folds=StratifiedKFold(CV_FOLDS, shuffle=True, random_state=SEED).split(X, y),
        callbacks=[lgb.early_stopping(EARLY_STOPPING_ROUNDS, verbose=False)],
    )
    return len(result["valid multi_logloss-mean"])


def decide(proba: np.ndarray, threshold: float | None) -> np.ndarray:
    """확률 → 클래스 번호. threshold가 None이면 argmax."""
    if threshold is None:
        return proba.argmax(axis=1)
    rest = proba.copy()
    rest[:, EMERGENCY] = -math.inf
    return np.where(proba[:, EMERGENCY] >= threshold, EMERGENCY, rest.argmax(axis=1))


def select_threshold(y: np.ndarray, p_emergency: np.ndarray, target_recall: float = TARGET_RECALL) -> dict:
    """응급 재현율이 target_recall 이상인 임계값 중 응급 정밀도가 가장 높은 것(같으면 더 높은 임계값).
    고른 값은 그 행의 확률과 바로 아래 확률의 중간으로 둔다 — 같은 행이 응급으로 잡히고, 소수점 차이로 경계가 뒤집히지 않는다."""
    positive = y == EMERGENCY
    if not positive.any():
        raise ValueError("응급 행이 없어 임계값을 정할 수 없다")
    values = np.unique(p_emergency)[::-1]  # 높은 값부터. 임계값을 내릴수록 응급으로 잡는 행이 늘어난다
    best = None
    for i, t in enumerate(values):
        flagged = p_emergency >= t
        tp = int((flagged & positive).sum())
        if tp < target_recall * positive.sum():
            continue
        precision = tp / int(flagged.sum())
        if best is None or precision > best["precision"]:
            lower = values[i + 1] if i + 1 < len(values) else 0.0
            best = {"index": i, "precision": precision, "threshold": float((t + lower) / 2), "tp": tp, "flagged": int(flagged.sum())}
    return {
        "rule": f"검증셋 응급 재현율 ≥ {target_recall}인 임계값 중 응급 정밀도 최대(같으면 높은 임계값), 경계는 바로 아래 확률과의 중간",
        "target_recall": target_recall,
        "threshold": best["threshold"],
        "recall": [best["tp"], int(positive.sum())],
        "precision": [best["tp"], best["flagged"]],
    }


def out_of_fold_proba(make_model, X: np.ndarray, y: np.ndarray, folds: int = CV_FOLDS) -> np.ndarray:
    """층화 k겹으로 각 행을 그 행이 빠진 모델로 예측한다. make_model(X, y) → 학습한 모델."""
    proba = np.zeros((len(y), len(ACUITIES)))
    for train_idx, held_idx in StratifiedKFold(folds, shuffle=True, random_state=SEED).split(X, y):
        proba[held_idx] = make_model(X[train_idx], y[train_idx]).predict_proba(X[held_idx])
    return proba


def _dataset(X: np.ndarray, y: np.ndarray) -> lgb.Dataset:
    return lgb.Dataset(X, label=y, feature_name=list(FEATURE_NAMES), free_raw_data=False)


# ---- 라운드 실행: 학습·검증셋 평가·저장(scripts/train_acuity.py), test 평가(scripts/evaluate.py) ----

MODEL_FILE = "model.txt"  # LightGBM 텍스트
LOGISTIC_FILE = "logistic.json"
METADATA_FILE = "metadata.json"  # 임시 형식. 확정은 backlog 08
SHAP_TOP_N = 3


def train_round(processed_dir: Path, splits_dir: Path, model_dir: Path, reports_dir: Path, round_name: str) -> dict:
    """train으로 두 모델을 학습하고, valid로 임계값을 정해 평가하고, train+valid 5겹 교차검증 수치를 더해 저장한다.
    test는 읽지 않는다. 이 라운드의 test 평가가 이미 있는데 모델이 바뀌면 덮어쓰지 않고 멈춘다."""
    train, valid = (split.load_dev(processed_dir, splits_dir, name) for name in split.DEV_SPLITS)
    X_train, y_train = featurize_many(train.to_dict("records")), encode_labels(train["acuity"])
    X_valid, y_valid = featurize_many(valid.to_dict("records")), encode_labels(valid["acuity"])
    X_dev, y_dev = np.vstack([X_train, X_valid]), np.concatenate([y_train, y_valid])

    lightgbm = LightGBMAcuity().fit(X_train, y_train)
    logistic = LogisticAcuity().fit(X_train, y_train)
    models = {
        lightgbm.name: (lightgbm, lambda X, y: LightGBMAcuity().fit(X, y, num_rounds=lightgbm.num_rounds)),
        logistic.name: (logistic, lambda X, y: LogisticAcuity().fit(X, y)),
    }

    results = {}
    for name, (model, make_model) in models.items():
        proba = model.predict_proba(X_valid)
        threshold = select_threshold(y_valid, proba[:, EMERGENCY])
        oof = out_of_fold_proba(make_model, X_dev, y_dev)
        results[name] = {
            "threshold": threshold,
            "valid": {
                "argmax": classification_metrics(y_valid, decide(proba, None)),
                "threshold": classification_metrics(y_valid, decide(proba, threshold["threshold"])),
            },
            "cv_train_valid": {
                "argmax": classification_metrics(y_dev, decide(oof, None)),
                "threshold": classification_metrics(y_dev, decide(oof, threshold["threshold"])),
            },
            "onset_max_proba_change": _onset_effect(model, X_valid),
        }

    texts = {MODEL_FILE: lightgbm.to_text(), LOGISTIC_FILE: logistic.to_text()}
    _refuse_if_tested(model_dir, reports_dir, round_name, texts)
    report = {
        "round": round_name,
        "model_version": f"acuity/{round_name}",
        "seed": SEED,
        "lightgbm_params": LGBM_PARAMS,
        "num_rounds": lightgbm.num_rounds,
        "num_rounds_rule": f"train 안 층화 {CV_FOLDS}겹 교차검증, multi_logloss 조기 종료({EARLY_STOPPING_ROUNDS}라운드)",
        "data": {
            "processed_sha256": sha256_file(processed_dir / split.PROCESSED_FILE),
            **{f"{name}_ids_sha256": sha256_file(split.split_path(splits_dir, name)) for name in split.DEV_SPLITS},
            "rows": {"train": len(train), "valid": len(valid)},
        },
        "feature_names": list(FEATURE_NAMES),
        "labels": list(ACUITIES),
        "cv_note": "cv_train_valid는 train+valid를 층화 5겹으로 나눈 교차검증 예측. 임계값은 valid로 정한 값을 그대로 쓰므로 valid 행에 대해서는 낙관적이다",
        "models": results,
        "shap_examples_valid": _shap_examples(lightgbm, valid, X_valid, results[lightgbm.name]["threshold"]["threshold"]),
    }

    model_dir.mkdir(parents=True, exist_ok=True)
    for file_name, text in texts.items():
        (model_dir / file_name).write_text(text)
    metadata = {k: report[k] for k in ("model_version", "seed", "lightgbm_params", "num_rounds", "data", "feature_names", "labels")}
    metadata |= {
        "status": "임시(backlog 04). 형식 확정은 backlog 08",
        "files": {MODEL_FILE: sha256_text(texts[MODEL_FILE]), LOGISTIC_FILE: sha256_text(texts[LOGISTIC_FILE])},
        "thresholds": {name: r["threshold"] for name, r in results.items()},
        "decision_rule": "emergency 확률 ≥ 임계값이면 emergency, 아니면 today·outpatient 중 확률이 큰 쪽",
    }
    (model_dir / METADATA_FILE).write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    table = {f"{n} {part} ({rule})": r[part][rule] for part in ("valid", "cv_train_valid") for n, r in results.items() for rule in r[part]}
    _write_report(reports_dir, f"acuity_{round_name}", report, table)
    return report


def evaluate_test_round(test: pd.DataFrame, model_dir: Path, reports_dir: Path, round_name: str) -> dict:
    """저장한 모델과 valid로 정한 임계값으로 test를 평가해 '최종'으로 기록한다. 라운드마다 한 번만 — 이미 있으면 멈춘다."""
    name = f"acuity_{round_name}_test"
    if (reports_dir / f"{name}.json").exists():
        raise FileExistsError(f"{name}.json이 이미 있다. test 평가는 라운드마다 한 번만 한다. 조정했다면 새 라운드로 기록한다")
    metadata = json.loads((model_dir / METADATA_FILE).read_text())
    texts = {f: (model_dir / f).read_text() for f in (MODEL_FILE, LOGISTIC_FILE)}
    if {f: sha256_text(t) for f, t in texts.items()} != metadata["files"]:
        raise ValueError(f"{model_dir}의 모델 파일이 {METADATA_FILE}에 적힌 해시와 다르다")
    models = {
        LightGBMAcuity.name: LightGBMAcuity.from_text(texts[MODEL_FILE]),
        LogisticAcuity.name: LogisticAcuity.from_text(texts[LOGISTIC_FILE]),
    }

    X, y = featurize_many(test.to_dict("records")), encode_labels(test["acuity"])
    results = {}
    for model_name, model in models.items():
        proba, threshold = model.predict_proba(X), metadata["thresholds"][model_name]["threshold"]
        results[model_name] = {
            "threshold": threshold,
            "argmax": classification_metrics(y, decide(proba, None)),
            "threshold_rule": classification_metrics(y, decide(proba, threshold)),
        }
    report = {
        "round": round_name,
        "final": True,
        "note": "test 평가는 이 라운드에서 한 번만 했다",
        "rows": len(test),
        "files": metadata["files"],
        "models": results,
    }
    _write_report(
        reports_dir, name, report, {f"{n} ({rule})": r[rule] for n, r in results.items() for rule in ("argmax", "threshold_rule")}
    )
    return report


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _onset_effect(model, X: np.ndarray) -> float:
    """학습 데이터에 onset이 전부 결측이다. 서빙 때 onset 값이 들어와도 예측이 그대로인지 본다(값 0~3 각각, 확률 차의 최댓값)."""
    column = FEATURE_NAMES.index("onset")
    base = model.predict_proba(X)
    changes = []
    for value in range(len(ONSETS)):
        filled = X.copy()
        filled[:, column] = value
        changes.append(float(np.abs(model.predict_proba(filled) - base).max()))
    return max(changes)


def _shap_examples(model: LightGBMAcuity, valid: pd.DataFrame, X: np.ndarray, threshold: float) -> list[dict]:
    """valid에서 최종 예측 클래스별로 id 순 첫 행 하나씩. 그 예측 클래스에 대한 상위 기여 피처."""
    proba = model.predict_proba(X)
    predicted = decide(proba, threshold)
    examples = []
    for class_index, acuity in enumerate(ACUITIES):
        rows = np.flatnonzero(predicted == class_index)
        if not len(rows):
            continue
        i = int(rows[0])
        examples.append(
            {
                "id": valid["id"].iloc[i],
                "true": valid["acuity"].iloc[i],
                "predicted": acuity,
                "proba": {a: round(float(p), 4) for a, p in zip(ACUITIES, proba[i], strict=True)},
                "top": top_contributions(model.booster, X[i], class_index, SHAP_TOP_N),
            }
        )
    return examples


def _refuse_if_tested(model_dir: Path, reports_dir: Path, round_name: str, texts: dict[str, str]) -> None:
    if not (reports_dir / f"acuity_{round_name}_test.json").exists():
        return
    old = {f: (model_dir / f).read_text() if (model_dir / f).exists() else None for f in texts}
    if old != texts:
        raise FileExistsError(f"{round_name}는 이미 test로 평가했는데 모델이 달라졌다. 새 라운드 이름으로 학습한다")


def _write_report(reports_dir: Path, name: str, report: dict, table: dict[str, dict]) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / f"{name}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    (reports_dir / f"{name}.md").write_text(f"# {name}\n\n" + metrics_table(table))
