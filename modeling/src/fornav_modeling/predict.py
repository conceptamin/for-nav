# 백엔드가 부를 예측 함수(backlog 08). 입력은 백엔드 Intake 필드 이름(snake_case)의 dict, 출력은 TriageResult.model 자리에 넣을 dict.
# - 아티팩트(models/<이름>/v1/)만 읽는다. 학습 코드(fornav_modeling.models.*, scikit-learn)를 import하지 않는다
#   (tests/test_predict_contract.py가 확인한다). 불러올 때 metadata.json에 적힌 sha256과 파일이 다르면 멈춘다.
# - 레드플래그·명확 케이스 규칙은 백엔드가 이 함수 앞에서 실행한다. 여기에는 규칙이 없다.
# - 응급도 입력의 "모름"(사용자와 정함, 2026-10-28): 의식 상태를 모르면 alert(앱을 쓰는 사람). 성별·나이대·손상 여부를 모르면
#   가능한 값을 모두 넣어 보고 응급 확률이 가장 높은 조합을 쓴다. 학습 데이터에 결측이 없던 이 피처들은 LightGBM이 NaN을 0으로 보아
#   응급 확률이 가장 낮은 쪽(30세 미만 등)으로 처리하기 때문이다. 통증 점수·발생 시점은 학습 때 결측을 봤으므로 그대로 둔다.
# - 진료과: 모델 A·B 분포의 가중 평균. 최대 확률이 폴백 기준값 미만이면 상위 2개를 가정의학과·내과로 바꾼다.
# 앙상블·모델 B 추론 함수(combine, top2, predict_from_weights)는 학습 코드도 이 모듈에서 가져다 쓴다 — 서빙과 학습이 같은 함수다.

import hashlib
import itertools
import json
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np

from fornav_modeling.explain import top_contributions
from fornav_modeling.features.buttons import AGE_GROUPS, FEATURE_NAMES, SEXES, featurize
from fornav_modeling.schema import DEPARTMENTS, Department

ACUITIES = ("emergency", "today", "outpatient")  # labels/ktas.py와 같은 순서(test_predict_contract가 확인)
EMERGENCY = 0
MODELS_DIR = Path(__file__).resolve().parents[2] / "models"
VERSION = "v1"
SHAP_TOP_N = 3

# 응급도 "모름" 처리. 이 키들은 백엔드 Intake에 아직 없어 같은 dict에 더 받는다(features/buttons.py)
UNKNOWN_MENTAL = "alert"
WORST_CASE_FIELDS: dict[str, tuple] = {"sex": SEXES, "age_group": AGE_GROUPS, "injury": (True, False)}
UNKNOWN_RULE = "의식 상태 모름 → alert. 성별·나이대·손상 여부 모름 → 가능한 값 조합 중 응급 확률이 가장 높은 것(같으면 sex·age_group·injury 나열 순서상 앞선 것)"


class ArtifactError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# 예측
# ---------------------------------------------------------------------------
def predict(intake: Mapping[str, Any], models_dir: Path | None = None) -> dict:
    """Intake dict → {acuity, acuityProba, departmentProba, departmentTop2, departmentFallback, shap}."""
    a = load_artifacts(str(models_dir or MODELS_DIR))
    x, acuity_proba = worst_case_acuity(a["acuity_booster"], intake)
    acuity = decide_acuity(acuity_proba, a["acuity_threshold"])
    department = combine(dept_a_proba(a, intake), dept_b_proba(a, intake), a["weight_a"])
    top, fallback = top2(department, a["fallback_threshold"], a["fallback"])  # 조정·평가(models/ensemble.py)와 같은 값으로 고른다
    # 모델 A의 질환별 진료과 비율은 소수 넷째 자리로 반올림돼 행 합이 1에서 1e-4쯤 벗어난다. 내보내는 분포만 합 1로 맞춘다
    department = department / department.sum()
    return {
        "acuity": acuity,
        "acuityProba": {k: float(p) for k, p in zip(ACUITIES, acuity_proba, strict=True)},
        "departmentProba": {d: float(p) for d, p in zip(DEPARTMENTS, department, strict=True)},
        "departmentTop2": top,
        "departmentFallback": fallback,
        "shap": top_contributions(a["acuity_booster"], x, ACUITIES.index(acuity), SHAP_TOP_N),
    }


def worst_case_acuity(booster: lgb.Booster, intake: Mapping[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    """(쓴 피처 벡터, 응급도 확률). 모르는 값은 UNKNOWN_RULE대로 채운다."""
    base = dict(intake)
    if base.get("mental") is None:
        base["mental"] = UNKNOWN_MENTAL
    unknown = [k for k in WORST_CASE_FIELDS if base.get(k) is None]
    candidates = [base | dict(zip(unknown, values, strict=True)) for values in itertools.product(*(WORST_CASE_FIELDS[k] for k in unknown))]
    X = np.array([featurize(c) for c in candidates], dtype=np.float64)
    proba = booster.predict(X)
    best = int(np.argmax(proba[:, EMERGENCY]))  # 같으면 앞선 조합
    return X[best], proba[best]


def decide_acuity(proba: np.ndarray, threshold: float) -> str:
    """응급 확률 ≥ 임계값이면 emergency, 아니면 today·outpatient 중 큰 쪽(models/acuity.decide와 같다)."""
    if proba[EMERGENCY] >= threshold:
        return "emergency"
    return ACUITIES[1 + int(np.argmax(proba[1:]))]


def dept_a_proba(a: Mapping[str, Any], intake: Mapping[str, Any]) -> np.ndarray:
    x = np.array([featurize(intake)], dtype=np.float64)
    return (a["dept_a_booster"].predict(x) @ a["class_departments"])[0]


def dept_b_proba(a: Mapping[str, Any], intake: Mapping[str, Any]) -> np.ndarray:
    return predict_from_weights(a["dept_b_weights"], np.array([featurize(intake)], dtype=np.float64))[0]


def combine(p_a: np.ndarray, p_b: np.ndarray, weight_a: float) -> np.ndarray:
    """모델 A·B 진료과 분포의 가중 평균(가중치 합 1)."""
    return weight_a * np.asarray(p_a) + (1 - weight_a) * np.asarray(p_b)


def top2(proba: np.ndarray, fallback_threshold: float, fallback: tuple[Department, Department]) -> tuple[list[Department], bool]:
    """(상위 2개, 폴백 여부). 최대 확률이 기준값 미만이면 fallback을 돌려준다. 동점이면 DEPARTMENTS 순서가 앞선 쪽."""
    if float(np.max(proba)) < fallback_threshold:
        return list(fallback), True
    order = sorted(range(len(DEPARTMENTS)), key=lambda i: (-proba[i], i))
    return [DEPARTMENTS[i] for i in order[:2]], False


# ---------------------------------------------------------------------------
# 모델 B 추론(weights.json만으로 동작). models/dept_b.py도 이 함수를 쓴다
# ---------------------------------------------------------------------------
def forward(weights: Mapping[str, Any], X_in: np.ndarray) -> np.ndarray:
    """(행 수, 입력 수) → (행 수, 10) 확률. 손상 여부 결측 처리는 하지 않는다(predict_from_weights가 한다)."""
    W1, b1, W2, b2 = (np.asarray(weights[k], dtype=np.float64) for k in ("W1", "b1", "W2", "b2"))
    h = np.maximum(X_in @ W1 + b1, 0.0)
    return softmax(h @ W2 + b2)


def predict_from_weights(weights: Mapping[str, Any], X: np.ndarray) -> np.ndarray:
    """FEATURE_NAMES 순서의 피처 → 진료과 확률. 부위·증상 결측은 0(선택 안 함), 손상 여부 결측은 손상 있음·없음 예측의 평균."""
    if list(weights["feature_names"]) != list(FEATURE_NAMES) or list(weights["labels"]) != list(DEPARTMENTS):
        raise ValueError("weights.json의 피처·라벨 순서가 지금 코드와 다르다")
    X = np.asarray(X, dtype=np.float64)
    X_in = np.nan_to_num(X[:, [FEATURE_NAMES.index(n) for n in weights["input_features"]]], nan=0.0)
    injury = weights["input_features"].index("injury")
    unknown = np.isnan(X[:, FEATURE_NAMES.index("injury")])
    proba = forward(weights, X_in)
    if unknown.any():
        yes, no = X_in[unknown].copy(), X_in[unknown].copy()
        yes[:, injury], no[:, injury] = 1.0, 0.0
        proba[unknown] = (forward(weights, yes) + forward(weights, no)) / 2
    return proba


def softmax(z: np.ndarray) -> np.ndarray:
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


# ---------------------------------------------------------------------------
# 아티팩트 읽기
# ---------------------------------------------------------------------------
@lru_cache(maxsize=4)
def load_artifacts(models_dir: str) -> dict[str, Any]:
    """models/{acuity,dept_a,dept_b,ensemble}/v1/을 읽어 검증한다. 파일 내용(텍스트·JSON)만 읽고 코드를 실행하지 않는다."""
    root = Path(models_dir)
    texts = {name: read_verified(root / name / VERSION) for name in ("acuity", "dept_a", "dept_b", "ensemble")}
    acuity_meta, ensemble = json.loads(texts["acuity"]["metadata.json"]), json.loads(texts["ensemble"]["ensemble.json"])
    departments = json.loads(texts["dept_a"]["departments.json"])
    for name in ("acuity", "dept_a"):
        meta = json.loads(texts[name]["metadata.json"])
        if meta["feature_names"] != list(FEATURE_NAMES) or meta["labels"] != list(ACUITIES if name == "acuity" else DEPARTMENTS):
            raise ArtifactError(f"{name}/{VERSION}의 피처·라벨 순서가 지금 코드와 다르다")
    if departments["labels"] != list(DEPARTMENTS) or list(ensemble["fallback"]) == [] or set(ensemble["fallback"]) - set(DEPARTMENTS):
        raise ArtifactError("dept_a 진료과 순서나 ensemble 폴백 값이 열거값과 다르다")
    return {
        "acuity_booster": lgb.Booster(model_str=texts["acuity"]["model.txt"]),
        "acuity_threshold": float(acuity_meta["threshold"]),
        "dept_a_booster": lgb.Booster(model_str=texts["dept_a"]["model.txt"]),
        "class_departments": np.array(departments["class_departments"], dtype=np.float64),
        "dept_b_weights": json.loads(texts["dept_b"]["weights.json"]),
        "weight_a": float(ensemble["weight_a"]),
        "fallback_threshold": float(ensemble["fallback_threshold"]),
        "fallback": tuple(ensemble["fallback"]),
    }


def read_verified(model_dir: Path) -> dict[str, str]:
    """metadata.json과 거기 적힌 파일들. 해시가 다르면 ArtifactError."""
    metadata = (model_dir / "metadata.json").read_text()
    texts = {"metadata.json": metadata}
    for name, digest in json.loads(metadata)["files"].items():
        text = (model_dir / name).read_text()
        if hashlib.sha256(text.encode()).hexdigest() != digest:
            raise ArtifactError(f"{model_dir / name}가 metadata.json에 적힌 sha256과 다르다")
        texts[name] = text
    return texts
