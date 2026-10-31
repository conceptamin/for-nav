# 버튼 입력 → 피처가 결정적이고 순서가 고정인지.

import math
from pathlib import Path

import numpy as np
import pytest

from fornav_modeling.features.buttons import FEATURE_NAMES, featurize, featurize_many
from fornav_modeling.schema import BODY_PARTS, SYMPTOMS

MODELING = Path(__file__).resolve().parents[1]

INTAKE = {
    "id": "x",
    "language": "en",
    "body_parts": ["hand", "arm"],
    "symptoms": ["cut", "bleeding"],
    "onset": "today",
    "pain_score": 6,
    "mental": "alert",
    "age_group": "30to44",
    "sex": "male",
    "injury": True,
}


def as_dict(vector):
    return dict(zip(FEATURE_NAMES, vector, strict=True))


def test_feature_order_is_fixed():
    # 순서가 바뀌면 학습한 모델과 어긋난다. 바꿀 때는 이 목록과 모델 버전을 함께 올린다.
    assert FEATURE_NAMES[: len(BODY_PARTS)] == tuple(f"body_{b}" for b in BODY_PARTS)
    assert FEATURE_NAMES[len(BODY_PARTS) : len(BODY_PARTS) + len(SYMPTOMS)] == tuple(f"symptom_{s}" for s in SYMPTOMS)
    assert FEATURE_NAMES[-6:] == ("pain_score", "mental", "age_group", "onset", "sex_male", "injury")
    assert len(FEATURE_NAMES) == len(set(FEATURE_NAMES)) == 34


def test_featurize_is_deterministic():
    first = featurize(INTAKE)
    assert first == featurize(dict(INTAKE)) == featurize(dict(reversed(list(INTAKE.items()))))
    # 목록 안 순서와 중복은 결과에 영향이 없다
    assert first == featurize({**INTAKE, "body_parts": ["arm", "hand", "arm"], "symptoms": ("bleeding", "cut")})
    assert len(first) == len(FEATURE_NAMES)


def test_featurize_values():
    f = as_dict(featurize(INTAKE))
    assert f["body_hand"] == f["body_arm"] == 1.0 and f["body_head"] == 0.0
    assert f["symptom_cut"] == f["symptom_bleeding"] == 1.0 and f["symptom_fever"] == 0.0
    assert (f["pain_score"], f["mental"], f["age_group"], f["onset"], f["sex_male"], f["injury"]) == (6.0, 0.0, 1.0, 0.0, 1.0, 1.0)


def test_missing_values_become_nan_and_empty_lists_zero():
    f = as_dict(featurize({"id": "x", "language": "ko", "onset": None, "pain_score": float("nan")}))
    for name in ("pain_score", "mental", "age_group", "onset", "sex_male", "injury"):
        assert math.isnan(f[name])
    assert all(f[n] == 0.0 for n in FEATURE_NAMES if n.startswith(("body_", "symptom_")))


def test_numpy_list_input_from_parquet():
    assert featurize({**INTAKE, "body_parts": np.array(["hand", "arm"], dtype=object)}) == featurize(INTAKE)


@pytest.mark.parametrize(
    "change",
    [
        {"body_parts": ["neck"]},
        {"symptoms": "cut"},
        {"onset": "month"},
        {"mental": "drowsy"},
        {"sex": "m"},
        {"pain_score": 11},
        {"pain_score": True},
        {"injury": "yes"},
    ],
)
def test_unknown_values_raise(change):
    with pytest.raises(ValueError):
        featurize({**INTAKE, **change})


def test_featurize_many_shape():
    assert featurize_many([INTAKE, INTAKE]).shape == (2, len(FEATURE_NAMES))
    assert featurize_many([]).shape == (0, len(FEATURE_NAMES))
