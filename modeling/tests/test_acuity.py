# 응급도 결정 규칙·임계값 선택·지표·SHAP이 정한 대로 동작하는지. 실제 데이터 없이 가짜 데이터로 본다.

import math

import numpy as np
import pytest
import shap
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from test_determinism import ONSET, synthetic

from fornav_modeling import explain
from fornav_modeling.evaluate import classification_metrics, metrics_table
from fornav_modeling.features.buttons import FEATURE_NAMES
from fornav_modeling.models import acuity
from fornav_modeling.models.acuity import EMERGENCY, LightGBMAcuity, LogisticAcuity, decide, select_threshold

PROBA = np.array(
    [
        [0.30, 0.50, 0.20],
        [0.10, 0.20, 0.70],
        [0.60, 0.30, 0.10],
        [0.05, 0.25, 0.70],
    ]
)


def test_decide_argmax_and_threshold():
    assert decide(PROBA, None).tolist() == [1, 2, 0, 2]
    # 응급 확률이 임계값 이상이면 응급, 아니면 나머지 두 클래스 중 큰 쪽
    assert decide(PROBA, 0.10).tolist() == [0, 0, 0, 2]
    assert decide(PROBA, 0.70).tolist() == [1, 2, 1, 2]


def test_select_threshold_meets_recall_with_best_precision():
    y = np.array([0, 0, 0, 0, 1, 1, 2, 2, 2, 2])
    p = np.array([0.9, 0.8, 0.3, 0.1, 0.85, 0.4, 0.35, 0.2, 0.05, 0.02])
    # 재현율 3/4를 만드는 가장 높은 임계값은 0.3(정밀도 3/6). 경계는 0.3과 바로 아래 0.2의 중간
    chosen = select_threshold(y, p, target_recall=0.75)
    assert chosen["recall"] == [3, 4] and chosen["precision"] == [3, 6]
    assert chosen["threshold"] == pytest.approx(0.25)
    # 재현율 4/4는 0.1까지 내려야 한다(정밀도 4/8)
    full = select_threshold(y, p, target_recall=1.0)
    assert full["recall"] == [4, 4] and full["precision"] == [4, 8]
    assert full["threshold"] == pytest.approx(0.075)
    assert (decide(np.column_stack([p, 1 - p, np.zeros_like(p)]), full["threshold"]) == EMERGENCY).sum() == 8


def test_select_threshold_needs_positives():
    with pytest.raises(ValueError):
        select_threshold(np.array([1, 2]), np.array([0.5, 0.1]))


def test_classification_metrics_counts():
    m = classification_metrics(np.array([0, 0, 1, 2, 2]), np.array([0, 1, 1, 2, 0]))
    assert m["per_class"]["emergency"]["recall"] == {"n": 1, "of": 2, "value": 0.5}
    assert m["per_class"]["emergency"]["precision"] == {"n": 1, "of": 2, "value": 0.5}
    assert m["per_class"]["today"]["precision"] == {"n": 1, "of": 2, "value": 0.5}
    assert m["accuracy"] == {"n": 3, "of": 5, "value": 0.6}
    assert m["confusion"]["matrix"] == [[1, 1, 0], [0, 1, 0], [1, 0, 1]]
    assert "1/2 (50.0%)" in metrics_table({"x": m})


def test_unseen_onset_does_not_change_prediction():
    # 학습 데이터 전체가 onset 결측이면, 서빙 때 onset 값이 들어와도 예측이 같아야 한다(backlog 03 결과)
    X, y = synthetic()
    for model in (LightGBMAcuity().fit(X, y), LogisticAcuity().fit(X, y)):
        filled = X.copy()
        filled[:, ONSET] = 3
        assert np.allclose(model.predict_proba(filled), model.predict_proba(X)), model.name


def test_logistic_matches_sklearn_pipeline():
    X, y = synthetic()
    pipeline = make_pipeline(
        SimpleImputer(strategy="median", keep_empty_features=True), StandardScaler(), LogisticRegression(max_iter=5000)
    )
    assert np.allclose(LogisticAcuity().fit(X, y).predict_proba(X), pipeline.fit(X, y).predict_proba(X))


def test_shap_values_match_shap_library():
    X, y = synthetic()
    booster = LightGBMAcuity().fit(X, y).booster
    ours = explain.shap_values(booster, X[:20])
    theirs = np.asarray(shap.TreeExplainer(booster).shap_values(X[:20]))  # (행, 피처, 클래스)
    assert np.allclose(ours, theirs.transpose(0, 2, 1), atol=1e-6)


def test_top_contributions_shape_and_order():
    X, y = synthetic()
    booster = LightGBMAcuity().fit(X, y).booster
    top = explain.top_contributions(booster, X[0], EMERGENCY, n=3)
    assert len(top) == 3 and all(set(t) == {"feature", "value", "contribution"} for t in top)
    assert all(t["feature"] in FEATURE_NAMES and t["contribution"] != 0 for t in top)
    assert [abs(t["contribution"]) for t in top] == sorted((abs(t["contribution"]) for t in top), reverse=True)
    assert "onset" not in {t["feature"] for t in explain.top_contributions(booster, X[0], EMERGENCY, n=len(FEATURE_NAMES))}
    assert all(t["value"] is None or not math.isnan(t["value"]) for t in top)


def test_test_evaluation_runs_once_per_round(tmp_path):
    (tmp_path / "acuity_v0_test.json").write_text("{}")
    with pytest.raises(FileExistsError):
        acuity.evaluate_test_round(None, tmp_path, tmp_path, "v0")


# v2: 결측을 섞은 학습(backlog 10) ----------------------------------------------


def test_augment_adds_blank_and_half_blank_copies():
    X, y = synthetic(50)
    X_aug, y_aug = acuity.augment(X, y)
    n, cols = len(X), [FEATURE_NAMES.index(f) for f in acuity.UNKNOWN_FEATURES]
    assert X_aug.shape == (3 * n, X.shape[1]) and np.array_equal(y_aug, np.tile(y, 3))
    assert np.array_equal(X_aug[:n], X, equal_nan=True)
    assert np.isnan(X_aug[n : 2 * n][:, cols]).all()
    others = [i for i in range(X.shape[1]) if i not in cols]
    assert np.array_equal(X_aug[n:, others], np.vstack([X, X])[:, others], equal_nan=True)  # 다른 피처는 그대로
    half = np.isnan(X_aug[2 * n :][:, cols]).mean()
    assert 0.3 < half < 0.7
    assert np.array_equal(acuity.augment(X, y)[0], X_aug, equal_nan=True)  # seed 고정


def test_grouped_folds_keep_copies_together():
    _, y = synthetic(100)
    folds = acuity.grouped_folds(np.tile(y, 3), copies=3)
    for train_idx, held_idx in folds:
        assert not set(train_idx % 100) & set(held_idx % 100)
        assert len(held_idx) % 3 == 0
    # copies=1이면 이전(StratifiedKFold) 그대로 — v0 라운드 수가 바뀌지 않는다
    plain = list(acuity.StratifiedKFold(acuity.CV_FOLDS, shuffle=True, random_state=acuity.SEED).split(np.zeros(100), y))
    assert all(np.array_equal(a[1], b[1]) for a, b in zip(acuity.grouped_folds(y), plain, strict=True))


def test_backend_profile_blanks_unknown_and_sets_alert():
    X, _ = synthetic(10)
    B = acuity.backend_profile(X)
    for name in acuity.UNKNOWN_FEATURES:
        assert np.isnan(B[:, FEATURE_NAMES.index(name)]).all()
    assert (B[:, FEATURE_NAMES.index("mental")] == 0).all()


def test_select_threshold_profiles_meets_target_on_every_profile():
    y = np.array([0, 0, 0, 0, 1, 1, 2, 2])
    p = {"full": np.array([0.9, 0.8, 0.7, 0.6, 0.5, 0.2, 0.1, 0.05]), "backend": np.array([0.4, 0.3, 0.2, 0.1, 0.35, 0.25, 0.15, 0.05])}
    r = acuity.select_threshold_profiles(y, p, target_recall=1.0)
    assert r["threshold"] == min(acuity.select_threshold(y, v, 1.0)["threshold"] for v in p.values())
    assert all(v["recall"] == [4, 4] for v in r["per_profile"].values())
