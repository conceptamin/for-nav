# 버튼 입력 → 피처 벡터. 학습(kaggle_triage 표준 테이블의 행)과 서빙(predict.py)이 이 함수 하나를 쓴다.
# 입력은 백엔드 Intake 필드 이름(snake_case)의 dict다. 통증 점수·의식 상태·나이대·성별·손상 여부는 백엔드 Intake의 선택 필드다
# (백엔드 backlog 10). 프론트는 아직 보내지 않아 대개 비어 있다.
# 피처 순서는 FEATURE_NAMES로 고정한다. 순서나 인코딩을 바꾸면 학습한 모델과 맞지 않으므로 모델 버전을 올린다.
# 값을 모르면(키가 없거나 None) NaN으로 둔다. 원본에 없는 발생 시점(onset)은 학습 데이터 전체가 NaN이다.

import math
from collections.abc import Iterable, Mapping
from typing import Any, get_args

import numpy as np

from fornav_modeling.schema import BODY_PARTS, ONSETS, SYMPTOMS, AgeGroup, Mental, Sex

# 순서 있는 값은 튜플 순서가 곧 피처 값(0, 1, 2, …)이다. 열거값은 schema.py(백엔드 vocab.py와 같은 값)에 있다.
MENTALS: tuple[Mental, ...] = get_args(Mental)
AGE_GROUPS: tuple[AgeGroup, ...] = get_args(AgeGroup)
SEXES: tuple[Sex, ...] = get_args(Sex)
_AGE_GROUP_LOWER = (0, 30, 45, 65)  # AGE_GROUPS 각 구간의 하한(이상)

FEATURE_NAMES: tuple[str, ...] = (
    *(f"body_{b}" for b in BODY_PARTS),  # 여러 개 선택 → 0/1
    *(f"symptom_{s}" for s in SYMPTOMS),  # 여러 개 선택 → 0/1
    "pain_score",  # 0–10
    "mental",  # MENTALS 순서 0–3
    "age_group",  # AGE_GROUPS 순서 0–3
    "onset",  # ONSETS 순서 0–3 (today → week)
    "sex_male",  # female 0, male 1
    "injury",  # 손상(외상) 여부 0/1
)


def age_to_group(age: float) -> AgeGroup:
    if math.isnan(age) or age < 0:
        raise ValueError(f"나이가 올바르지 않다: {age!r}")
    return next(g for g, lower in zip(reversed(AGE_GROUPS), reversed(_AGE_GROUP_LOWER), strict=True) if age >= lower)


def featurize(intake: Mapping[str, Any]) -> list[float]:
    """Intake 형태 dict → FEATURE_NAMES 순서의 float 목록. 열거값 밖의 값은 ValueError."""
    body_parts = _multi_hot(intake.get("body_parts"), BODY_PARTS, "body_parts")
    symptoms = _multi_hot(intake.get("symptoms"), SYMPTOMS, "symptoms")
    return [
        *body_parts,
        *symptoms,
        _pain_score(intake.get("pain_score")),
        _ordinal(intake.get("mental"), MENTALS, "mental"),
        _ordinal(intake.get("age_group"), AGE_GROUPS, "age_group"),
        _ordinal(intake.get("onset"), ONSETS, "onset"),
        _ordinal(intake.get("sex"), SEXES, "sex"),
        _flag(intake.get("injury"), "injury"),
    ]


def featurize_many(intakes: Iterable[Mapping[str, Any]]) -> np.ndarray:
    """여러 입력 → (행 수, len(FEATURE_NAMES)) float64 배열."""
    rows = [featurize(intake) for intake in intakes]
    return np.array(rows, dtype=np.float64).reshape(len(rows), len(FEATURE_NAMES))


def _missing(value: Any) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


def _multi_hot(values: Iterable[str] | None, vocab: tuple[str, ...], name: str) -> list[float]:
    # parquet에서 읽은 목록은 numpy 배열이라 list로만 받지 않는다. 문자열 하나는 목록으로 보지 않는다.
    if values is None:
        return [0.0] * len(vocab)
    if isinstance(values, str):
        raise ValueError(f"{name}는 목록이어야 한다: {values!r}")
    chosen = set(values)
    if unknown := chosen - set(vocab):
        raise ValueError(f"{name}에 모르는 값: {sorted(unknown)}")
    return [1.0 if v in chosen else 0.0 for v in vocab]


def _ordinal(value: Any, vocab: tuple[str, ...], name: str) -> float:
    if _missing(value):
        return math.nan
    if value not in vocab:
        raise ValueError(f"{name}에 모르는 값: {value!r} (가능한 값: {', '.join(vocab)})")
    return float(vocab.index(value))


def _pain_score(value: Any) -> float:
    if _missing(value):
        return math.nan
    if isinstance(value, bool) or not 0 <= value <= 10:
        raise ValueError(f"pain_score는 0~10이어야 한다: {value!r}")
    return float(value)


def _flag(value: Any, name: str) -> float:
    if _missing(value):
        return math.nan
    if not isinstance(value, bool | np.bool_):
        raise ValueError(f"{name}는 True/False여야 한다: {value!r}")
    return 1.0 if value else 0.0
