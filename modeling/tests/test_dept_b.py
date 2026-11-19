# 진료과 모델 B: weights.json만으로 한 추론이 학습 코드와 같은지, 출력 형태, 손상 여부 결측 처리, 역전파, 학습·검증 분리. 가짜 데이터로 본다.

import json
from pathlib import Path

import numpy as np
import pytest
from test_determinism import DEPT_B_TABLE

from fornav_modeling.features.buttons import FEATURE_NAMES, featurize_many
from fornav_modeling.labels import department as dept
from fornav_modeling.models import dept_b
from fornav_modeling.schema import DEPARTMENTS

MODELING = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def trained():
    _, X, T, w = dept_b.training_rows(DEPT_B_TABLE)
    params = dept_b._init()
    for _ in dept_b._adam(params, X, T, w, 1e-3, 300):
        pass
    return params, X


def test_json_weights_match_training_forward(trained):
    params, X = trained
    weights = json.loads(json.dumps(dept_b._export(params)))  # weights.json으로 쓰고 다시 읽은 것과 같다
    full = np.full((len(X), len(FEATURE_NAMES)), np.nan)
    full[:, [FEATURE_NAMES.index(n) for n in dept_b.INPUT_FEATURES]] = X
    assert np.array_equal(dept_b.predict_from_weights(weights, full), dept_b.forward(params, X))


def test_output_is_ten_departments_summing_to_one(trained):
    weights = dept_b._export(trained[0])
    out = dept_b.department_proba(weights, {"body_parts": ["hand", "arm"], "symptoms": ["cut", "swelling"], "injury": True})
    assert list(out) == list(DEPARTMENTS)
    assert sum(out.values()) == pytest.approx(1.0)


def test_unknown_injury_averages_both(trained):
    weights = dept_b._export(trained[0])
    base = {"body_parts": ["hand"], "symptoms": ["cut"]}
    yes, no, unknown = (dept_b.department_proba(weights, base | {"injury": v}) for v in (True, False, None))
    assert all(unknown[d] == pytest.approx((yes[d] + no[d]) / 2) for d in DEPARTMENTS)


def test_non_table_features_do_not_change_prediction(trained):
    weights = dept_b._export(trained[0])
    base = {"body_parts": ["eye"], "symptoms": ["pain"], "injury": False}
    full = base | {"pain_score": 9, "mental": "verbal", "age_group": "65plus", "onset": "week", "sex": "male"}
    assert dept_b.department_proba(weights, full) == dept_b.department_proba(weights, base)


def test_from_weights_rejects_other_label_order(trained):
    weights = dept_b._export(trained[0]) | {"labels": list(reversed(DEPARTMENTS))}
    with pytest.raises(ValueError):
        dept_b.predict_from_weights(weights, featurize_many([{"body_parts": ["eye"], "symptoms": ["pain"]}]))


def test_gradients_match_finite_differences():
    rng = np.random.default_rng(1)
    _, X, T, w = dept_b.training_rows(DEPT_B_TABLE)
    params = {k: v + rng.normal(0, 0.1, v.shape) for k, v in dept_b._init().items()}  # 편향도 0이 아니게
    _, grads = dept_b.loss_and_gradients(params, X, T, w, 1e-2)
    eps = 1e-6
    for key in ("W1", "b1", "W2", "b2"):
        for idx in [tuple(rng.integers(0, s) for s in params[key].shape) for _ in range(5)]:
            plus = {k: v.copy() for k, v in params.items()}
            minus = {k: v.copy() for k, v in params.items()}
            plus[key][idx] += eps
            minus[key][idx] -= eps
            numeric = (dept_b.loss_and_gradients(plus, X, T, w, 1e-2)[0] - dept_b.loss_and_gradients(minus, X, T, w, 1e-2)[0]) / (2 * eps)
            assert grads[key][idx] == pytest.approx(numeric, abs=1e-6), (key, idx)


def test_training_rows_split_any_into_two_half_weights():
    cids, X, T, w = dept_b.training_rows(DEPT_B_TABLE)
    assert cids.count("skin-rash-any") == 2 and len(cids) == 5
    injury = dept_b.INPUT_FEATURES.index("injury")
    rows = [i for i, c in enumerate(cids) if c == "skin-rash-any"]
    assert sorted(X[rows, injury].tolist()) == [0.0, 1.0] and w[rows].tolist() == [0.5, 0.5]
    assert np.allclose(T.sum(axis=1), 1.0)


def test_split_table_holds_out_same_combos():
    train, held = dept_b.split_table(DEPT_B_TABLE, ["hand-cut-any", "skin-rash-no"])
    assert sorted(held) == ["hand-cut-yes", "skin-rash-any"]
    assert sorted(train) == ["abdomen-pain-no", "eye-pain-no"]


def test_committed_tables_hold_out_every_guide_combo():
    ids, _ = dept.guide_set(MODELING / "data" / "tables", MODELING / "data" / "splits")
    train, held = dept_b.split_table(dept.read_button_department(MODELING / "data" / "tables"), ids)
    assert not any(dept.same_combo(c, v) for c in train for v in ids)
    assert len(train) + len(held) == 143  # backlog 13에서 빈 조합 14개를 채웠다


def test_kl_divergence():
    T = np.array([[0.5, 0.5, 0.0], [1.0, 0.0, 0.0]])
    assert dept_b.kl_divergence(T, T).tolist() == [0.0, 0.0]
    assert dept_b.kl_divergence(T, np.array([[0.25, 0.25, 0.5]] * 2))[1] == pytest.approx(np.log(4))


def test_seed_members_average_their_predictions():
    _, X, T, w = dept_b.training_rows(DEPT_B_TABLE)
    seeds = (dept_b.SEED, dept_b.SEED + 1)
    both = dept_b.DeptB().fit(X, T, w, 1e-3, 100, hidden=8, seeds=seeds)
    each = [dept_b.DeptB().fit(X, T, w, 1e-3, 100, hidden=8, seeds=(s,)) for s in seeds]
    full = featurize_many([{"body_parts": ["hand"], "symptoms": ["cut"]}, {"body_parts": ["eye"], "symptoms": ["pain"], "injury": False}])
    weights = json.loads(json.dumps(both.weights))
    assert len(weights["members"]) == 2 and weights["hidden"] == 8
    assert np.allclose(dept_b.predict_from_weights(weights, full), np.mean([m.predict_proba(full) for m in each], axis=0))


def test_synthetic_pairs_share_one_part_and_mix():
    table = {
        "hand-cut-yes": {"ortho": 0.6, "surgery": 0.4},
        "hand-pain-no": {"ortho": 1.0},
        "hand-burn-any": {"surgery": 1.0},
        "arm-cut-yes": {"surgery": 1.0},
    }
    pairs = {cid: (intake, mixed) for cid, intake, mixed in dept_b.synthetic_pairs(table, "mean")}
    # 손상 있음·없음 쌍(hand-cut-yes + hand-pain-no)과 부위·증상이 둘 다 다른 쌍은 없다
    assert sorted(pairs) == ["arm-cut-yes+hand-cut-yes", "hand-burn-any+hand-cut-yes", "hand-burn-any+hand-pain-no"]
    intake, mixed = pairs["arm-cut-yes+hand-cut-yes"]
    assert intake == {"body_parts": ["arm", "hand"], "symptoms": ["cut"], "injury": True}
    assert mixed[DEPARTMENTS.index("surgery")] == pytest.approx(0.7)
    assert pairs["hand-burn-any+hand-pain-no"][0]["injury"] is False
    product = {cid: mixed for cid, _, mixed in dept_b.synthetic_pairs(table, "product")}
    assert sum(product["arm-cut-yes+hand-cut-yes"]) == pytest.approx(1.0)
    assert product["arm-cut-yes+hand-cut-yes"][DEPARTMENTS.index("surgery")] > 0.7  # 곱하면 둘 다 높은 쪽이 더 커진다


def test_synthetic_rows_weigh_pair_weight_of_singles():
    _, _, _, w = dept_b.training_rows(DEPT_B_TABLE, "mean", 0.5)
    singles = len(dept_b.training_rows(DEPT_B_TABLE)[3])
    assert w[:singles].sum() == pytest.approx(len(DEPT_B_TABLE)) and w[singles:].sum() == pytest.approx(0.5 * len(DEPT_B_TABLE))


def test_choose_setting_needs_more_than_v0_spread():
    def cv(mean, std=0.0):
        return {"summary": {"kl_mean": {"mean": mean, "std": std}}}

    assert dept_b.choose_setting({"v0": cv(0.40, 0.05), "wide": cv(0.36)}) == "v0"
    assert dept_b.choose_setting({"v0": cv(0.40, 0.05), "wide": cv(0.34), "wide_seeds5": cv(0.30)}) == "wide_seeds5"


def test_backoff_uses_same_combo_then_part_averages():
    train = {"hand-cut-yes": {"surgery": 1.0}, "hand-pain-no": {"ortho": 1.0}, "arm-rash-any": {"derm": 1.0}}
    out = dept_b.backoff_predictor(train, ["hand-cut-any", "arm-cut-yes"])
    assert out[0][DEPARTMENTS.index("surgery")] == 1.0
    # arm-cut: 같은 부위(arm-rash) 평균과 같은 증상(hand-cut) 평균의 평균
    assert out[1][DEPARTMENTS.index("derm")] == pytest.approx(0.5) and out[1][DEPARTMENTS.index("surgery")] == pytest.approx(0.5)
