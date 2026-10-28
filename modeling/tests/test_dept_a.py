# 진료과 모델 A: 출력이 진료과 10종뿐인지(질환명 비노출), 버튼에 없는 피처가 예측을 바꾸지 않는지, 표준화·분할·Top-k 지표. 가짜 데이터로 본다.

from pathlib import Path

import numpy as np
import pytest
from test_determinism import synthetic_dept

from fornav_modeling.data import kaggle_symptom, split
from fornav_modeling.evaluate import topk_metrics
from fornav_modeling.models.dept_a import DeptA, class_department_matrix, department_proba, true_departments
from fornav_modeling.schema import DEPARTMENTS

MODELING = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def model():
    X, y, matrix = synthetic_dept()
    return DeptA().fit(X, y, matrix)


def test_output_keys_are_departments_only(model):
    out = department_proba(model, {"body_parts": ["head"], "symptoms": ["pain"]})
    assert list(out) == list(DEPARTMENTS)
    assert sum(out.values()) == pytest.approx(1.0)
    assert all(isinstance(v, float) and v >= 0 for v in out.values())


def test_non_button_features_do_not_change_prediction(model):
    # 학습 원본에는 부위·증상만 있다. 서빙 때 통증 점수·나이대 등이 들어와도 확률이 같아야 한다.
    base = {"body_parts": ["head"], "symptoms": ["pain"]}
    full = base | {"pain_score": 9, "mental": "verbal", "age_group": "65plus", "onset": "week", "sex": "male", "injury": True}
    assert department_proba(model, full) == department_proba(model, base)


def test_department_proba_follows_class_matrix(model):
    # synthetic_dept: 머리+통증 → 질환 3 → 진료과 DEPARTMENTS[6]
    out = department_proba(model, {"body_parts": ["head"], "symptoms": ["pain"]})
    assert max(out, key=out.get) == DEPARTMENTS[6]


def test_class_department_matrix_and_truth():
    table = {"a": {"internal": 0.7, "family": 0.3}, "b": {"ortho": 1.0}}
    matrix = class_department_matrix(["b", "a"], table)
    assert matrix.shape == (2, len(DEPARTMENTS))
    assert matrix[0, DEPARTMENTS.index("ortho")] == 1.0 and matrix[1, DEPARTMENTS.index("family")] == 0.3
    assert true_departments(["a", "b"], table).tolist() == [DEPARTMENTS.index("internal"), DEPARTMENTS.index("ortho")]
    with pytest.raises(KeyError):
        class_department_matrix(["c"], table)


def test_from_files_rejects_other_label_order(model):
    files = model.to_files()
    files["departments.json"] = files["departments.json"].replace('"ortho"', '"xxx"', 1)
    with pytest.raises(ValueError):
        DeptA.from_files(files)


def test_topk_metrics_counts_and_ties():
    proba = np.array([[0.5, 0.3, 0.2], [0.2, 0.3, 0.5], [0.4, 0.4, 0.2]])
    m = topk_metrics(proba, np.array([1, 0, 1]), ("a", "b", "c"))
    # 셋째 행은 a·b 동점 → 순서가 앞선 a가 1위
    assert m["top1"] == {"n": 0, "of": 3, "value": 0.0}
    assert m["top2"] == {"n": 2, "of": 3, "value": 0.6667}
    assert m["per_class"]["b"]["top2"] == {"n": 2, "of": 2, "value": 1.0}
    assert "c" not in m["per_class"]


SYMPTOM_MAP = {
    "itching": (["skin"], ["rash"]),
    "skin_rash": (["skin"], ["rash"]),
    "fatigue": (["whole"], []),
    "knee_pain": (["leg"], ["pain"]),
}


def test_standardize_dedupes_converts_and_drops_empty():
    rows = [
        ("A", ["itching", "skin_rash"]),
        ("A", ["skin_rash", "itching"]),  # 같은 집합 → 하나로
        ("B", ["fatigue"]),  # 우리 증상이 없다 → 버린다
        ("C", ["knee_pain", "fatigue"]),
    ]
    table, summary = kaggle_symptom.standardize(rows, SYMPTOM_MAP)
    assert table["id"].tolist() == ["symptom_0001", "symptom_0002"]
    assert table["disease"].tolist() == ["A", "C"]
    assert table["body_parts"].tolist() == [["skin"], ["leg", "whole"]]  # schema 순서
    assert table["symptoms"].tolist() == [["rash"], ["pain"]]
    assert summary["unique_rows"] == 3 and summary["dropped_no_symptom"] == {"rows": 1, "diseases_lost": 1}
    with pytest.raises(KeyError):
        kaggle_symptom.standardize([("A", ["unknown"])], SYMPTOM_MAP)


def test_committed_symptom_splits_are_disjoint_and_stratified():
    ids = {name: split.read_split_ids(MODELING / "data" / "splits", name, "symptom") for name in split.SPLITS}
    assert sum(len(v) for v in ids.values()) == len(set().union(*ids.values())) == 292
    assert all(v == sorted(v) for v in ids.values())


def test_load_symptom_dev_refuses_test(tmp_path):
    with pytest.raises(ValueError):
        split.load_symptom_dev(tmp_path, tmp_path, "test")
