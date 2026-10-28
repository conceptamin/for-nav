# 같은 seed로 두 번 학습하면 같은 모델 문자열(해시)이 나오는지, 저장한 텍스트로 다시 불러도 예측이 같은지(응급도, 진료과 모델 A·B).

import hashlib

import numpy as np

from fornav_modeling.features.buttons import FEATURE_NAMES
from fornav_modeling.models import dept_b
from fornav_modeling.models.acuity import LightGBMAcuity, LogisticAcuity
from fornav_modeling.models.dept_a import DeptA

ONSET = FEATURE_NAMES.index("onset")
PAIN = FEATURE_NAMES.index("pain_score")


def synthetic(n=300, seed=0):
    """버튼 피처 모양의 가짜 데이터. 0/1 열 + 통증 점수, onset은 학습 원본처럼 전부 결측."""
    rng = np.random.default_rng(seed)
    X = rng.integers(0, 2, size=(n, len(FEATURE_NAMES))).astype(np.float64)
    X[:, PAIN] = rng.integers(0, 11, size=n)
    X[:, ONSET] = np.nan
    y = np.where(X[:, PAIN] >= 8, 0, np.where(X[:, 0] + X[:, 1] >= 1, 1, 2))
    flip = rng.random(n) < 0.15
    y[flip] = rng.integers(0, 3, size=flip.sum())
    return X, y


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def test_lightgbm_same_seed_same_model_string():
    X, y = synthetic()
    first, second = LightGBMAcuity().fit(X, y), LightGBMAcuity().fit(X, y)
    assert first.num_rounds == second.num_rounds > 0
    assert digest(first.to_text()) == digest(second.to_text())


def test_logistic_same_data_same_text():
    X, y = synthetic()
    assert digest(LogisticAcuity().fit(X, y).to_text()) == digest(LogisticAcuity().fit(X, y).to_text())


def test_saved_text_predicts_the_same():
    X, y = synthetic()
    for model in (LightGBMAcuity().fit(X, y), LogisticAcuity().fit(X, y)):
        loaded = type(model).from_text(model.to_text())
        assert np.array_equal(loaded.predict_proba(X), model.predict_proba(X)), model.name


def synthetic_dept(n=240, seed=0):
    """진료과 모델 A 모양의 가짜 데이터: 부위·증상 0/1 열만 있고 나머지 피처는 학습 원본처럼 전부 결측. 질환 4종."""
    rng = np.random.default_rng(seed)
    X = np.full((n, len(FEATURE_NAMES)), np.nan)
    X[:, :28] = rng.integers(0, 2, size=(n, 28))
    y = (X[:, 0] + 2 * X[:, 13]).astype(np.int64)  # body_head, symptom_pain 조합 → 0..3
    matrix = np.eye(4, 10)[:, ::-1]  # 질환 i → 진료과 9-i
    return X, y, matrix


def test_dept_a_same_seed_same_files():
    X, y, matrix = synthetic_dept()
    first, second = DeptA().fit(X, y, matrix), DeptA().fit(X, y, matrix)
    assert first.num_rounds == second.num_rounds > 0
    assert {k: digest(v) for k, v in first.to_files().items()} == {k: digest(v) for k, v in second.to_files().items()}


def test_dept_a_saved_files_predict_the_same():
    X, y, matrix = synthetic_dept()
    model = DeptA().fit(X, y, matrix)
    assert np.allclose(DeptA.from_files(model.to_files()).predict_proba(X), model.predict_proba(X))


DEPT_B_TABLE = {
    "hand-cut-yes": {"ortho": 0.6, "surgery": 0.4},
    "eye-pain-no": {"ophth": 1.0},
    "skin-rash-any": {"derm": 0.5, "family": 0.5},
    "abdomen-pain-no": {"internal": 0.7, "family": 0.3},
}


def test_dept_b_same_seed_same_weights():
    _, X, T, w = dept_b.training_rows(DEPT_B_TABLE)
    first, second = dept_b.DeptB().fit(X, T, w, 1e-3, 200), dept_b.DeptB().fit(X, T, w, 1e-3, 200)
    assert digest(first.to_text()) == digest(second.to_text())


def test_lightgbm_with_augmented_rows_same_model_string():
    from fornav_modeling.models import acuity

    X, y = synthetic()
    first = LightGBMAcuity().fit(*acuity.augment(X, y), copies=acuity.AUGMENT_COPIES)
    second = LightGBMAcuity().fit(*acuity.augment(X, y), copies=acuity.AUGMENT_COPIES)
    assert digest(first.to_text()) == digest(second.to_text())
