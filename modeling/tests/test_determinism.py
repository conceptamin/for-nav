# 같은 seed로 두 번 학습하면 같은 모델 문자열(해시)이 나오는지, 저장한 텍스트로 다시 불러도 예측이 같은지.

import hashlib

import numpy as np

from fornav_modeling.features.buttons import FEATURE_NAMES
from fornav_modeling.models.acuity import LightGBMAcuity, LogisticAcuity

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
