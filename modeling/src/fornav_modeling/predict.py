# 백엔드가 부를 예측 함수(backlog 08). 입력은 백엔드 Intake 필드 이름(snake_case)의 dict, 출력은 TriageResult.model 자리에 넣을 dict.
# - 진료과만 예측한다. 응급도 모델은 앱이 응급 여부를 판정하지 않기로 해서 지웠다(backlog 15).
# - 아티팩트(models/<이름>/v2/)만 읽는다. 학습 코드(fornav_modeling.models.*, scikit-learn)를 import하지 않는다
#   (tests/test_predict_contract.py가 확인한다). 불러올 때 metadata.json에 적힌 sha256과 파일이 다르면 멈춘다.
# - 진료과 규칙표는 백엔드가 이 함수 앞에서 실행한다. 여기에는 규칙이 없다.
# - 백엔드 Intake에 없는 피처(통증 점수·의식 상태·나이대·성별)는 NaN이다. 모델 A는 이 넷과 발생 시점·손상 여부를 쓰지 않고(피처 중요도 0),
#   모델 B는 부위·증상에 손상 여부만 더 쓴다.
# - 진료과: 모델 A·B 분포의 가중 평균. 최대 확률이 폴백 기준값 미만이면 상위 2개를 가정의학과·내과로 바꾼다.
# 앙상블·모델 B 추론 함수(combine, top2, predict_from_weights)는 학습 코드도 이 모듈에서 가져다 쓴다 — 서빙과 학습이 같은 함수다.

import hashlib
import json
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np

from fornav_modeling.features.buttons import FEATURE_NAMES, featurize
from fornav_modeling.schema import DEPARTMENTS, Department

MODELS_DIR = Path(__file__).resolve().parents[2] / "models"
VERSION = "v2"


class ArtifactError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# 예측
# ---------------------------------------------------------------------------
def predict(intake: Mapping[str, Any], models_dir: Path | None = None) -> dict:
    """Intake dict → {departmentProba, departmentTop2, departmentFallback}."""
    a = load_artifacts(str(models_dir or MODELS_DIR))
    department = combine(dept_a_proba(a, intake), dept_b_proba(a, intake), a["weight_a"])
    top, fallback = top2(department, a["fallback_threshold"], a["fallback"])  # 조정·평가(models/ensemble.py)와 같은 값으로 고른다
    # 모델 A의 질환별 진료과 비율은 소수 넷째 자리로 반올림돼 행 합이 1에서 1e-4쯤 벗어난다. 내보내는 분포만 합 1로 맞춘다
    department = department / department.sum()
    return {
        "departmentProba": {d: float(p) for d, p in zip(DEPARTMENTS, department, strict=True)},
        "departmentTop2": top,
        "departmentFallback": fallback,
    }


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
    """models/{dept_a,dept_b,ensemble}/<VERSION>/을 읽어 검증한다. 파일 내용(텍스트·JSON)만 읽고 코드를 실행하지 않는다."""
    root = Path(models_dir)
    texts = {name: read_verified(root / name / VERSION) for name in ("dept_a", "dept_b", "ensemble")}
    ensemble = json.loads(texts["ensemble"]["ensemble.json"])
    departments = json.loads(texts["dept_a"]["departments.json"])
    meta = json.loads(texts["dept_a"]["metadata.json"])
    if meta["feature_names"] != list(FEATURE_NAMES) or meta["labels"] != list(DEPARTMENTS):
        raise ArtifactError(f"dept_a/{VERSION}의 피처·라벨 순서가 지금 코드와 다르다")
    if departments["labels"] != list(DEPARTMENTS) or list(ensemble["fallback"]) == [] or set(ensemble["fallback"]) - set(DEPARTMENTS):
        raise ArtifactError("dept_a 진료과 순서나 ensemble 폴백 값이 열거값과 다르다")
    return {
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
