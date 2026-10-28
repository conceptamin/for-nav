# 버튼 입력 → 피처가 결정적이고 순서가 고정인지, 원본 → 표준 테이블 변환과 주증상 매핑 표가 열거값을 지키는지.

import ast
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from fornav_modeling.data import kaggle_triage
from fornav_modeling.features import buttons
from fornav_modeling.features.buttons import FEATURE_NAMES, age_to_group, featurize, featurize_many
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


@pytest.mark.parametrize(
    ("age", "group"),
    [(15.5, "under30"), (29.9, "under30"), (30, "30to44"), (44.9, "30to44"), (45, "45to64"), (65, "65plus"), (95.8, "65plus")],
)
def test_age_to_group(age, group):
    assert age_to_group(age) == group


def test_buttons_does_not_import_vitals():
    # 활력징후는 서빙 경로에 들어가면 안 된다(09에서 predict.py까지 확인한다).
    tree = ast.parse(Path(buttons.__file__).read_text())
    imported = [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)] + [
        a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names
    ]
    assert not any("vitals" in (m or "") for m in imported)


def test_chief_complaint_map_is_valid():
    # 열거값 밖의 값, 정규화 안 된 키, 중복, 빈 출처가 있으면 read_chief_complaint_map이 ValueError를 낸다.
    mapping = kaggle_triage.read_chief_complaint_map(MODELING / "data" / "tables")
    assert len(mapping) > 0


def raw_frame(**overrides):
    row = {
        "Sex": 2,
        "Age": 67.5,
        "Injury": 2,
        "Chief_complain": "  Finger  Laceration ",
        "Mental": 1,
        "Pain": 1,
        "NRS_pain": 4.0,
        "SBP": "130",
        "DBP": "측불",
        "HR": 80,
        "RR": 20,
        "BT": 36.6,
        "Saturation": None,
        "KTAS_RN": 3,
        "KTAS_expert": 2,
    }
    return pd.DataFrame([{**row, **overrides}])


CC_MAP = {"finger laceration": (["hand"], ["cut"]), "mental change": ([], [])}


def test_standardize_converts_codes():
    row = kaggle_triage.standardize(raw_frame(), CC_MAP).iloc[0]
    assert row["id"] == "triage_0001"
    assert (row["sex"], row["injury"], row["mental"], row["age_group"]) == ("male", True, "alert", "65plus")
    assert list(row["body_parts"]) == ["hand"] and list(row["symptoms"]) == ["cut"] and row["chief_complaint_mapped"]
    assert row["pain_score"] == 4.0 and row["onset"] is None
    assert (row["acuity"], row["acuity_rn"]) == ("emergency", "today")
    assert row["sbp"] == 130.0 and math.isnan(row["dbp"]) and math.isnan(row["saturation"])
    # 표준 테이블 행을 그대로 featurize에 넘길 수 있다
    assert len(featurize(row.to_dict())) == len(FEATURE_NAMES)


def test_standardize_pain_and_unmapped():
    table = kaggle_triage.standardize(
        pd.concat([raw_frame(Pain=0, NRS_pain=None), raw_frame(Pain=1, NRS_pain=None, Chief_complain="mental change")]), CC_MAP
    )
    assert table["pain_score"].iloc[0] == 0.0 and math.isnan(table["pain_score"].iloc[1])
    assert not table["chief_complaint_mapped"].iloc[1]


def test_standardize_rejects_unknown_codes_and_complaints():
    with pytest.raises(KeyError):
        kaggle_triage.standardize(raw_frame(Chief_complain="new complaint"), CC_MAP)
    with pytest.raises(ValueError):
        kaggle_triage.standardize(raw_frame(Mental=5), CC_MAP)
    with pytest.raises(ValueError):
        kaggle_triage.standardize(raw_frame(SBP="??"), CC_MAP)
