# 앙상블 조정(backlog 08, 16): 행렬로 계산한 적중·폴백이 서빙 함수(predict.top2)와 같은지, 출처 균형 점수와 동점 규칙.

import numpy as np

from fornav_modeling.models import ensemble
from fornav_modeling.predict import combine, top2
from fornav_modeling.schema import DEPARTMENTS


def test_outcomes_match_serving_top2():
    rng = np.random.default_rng(0)
    p_a, p_b = rng.dirichlet(np.ones(10), 200), rng.dirichlet(np.ones(10), 200)
    p_a[:5] = p_b[:5] = np.full(10, 0.1)  # 전부 동점 → DEPARTMENTS 순서
    y = rng.integers(0, 10, 200)
    for w, t in [(0.0, 0.0), (0.4, 0.25), (1.0, 0.6)]:
        got = ensemble.outcomes(p_a, p_b, y, w, t)
        for i in range(len(y)):
            top, fell = top2(combine(p_a[i], p_b[i], w), t, ensemble.FALLBACK)
            assert got["fallback"][i] == fell
            assert got["top1"][i] == (top[0] == DEPARTMENTS[y[i]])
            assert got["top2"][i] == (DEPARTMENTS[y[i]] in top)


def test_balanced_scores_weigh_each_source_equally():
    # 격자 칸 2개. 출처 g(2행)·k(4행). 칸 0: g 2/2, k 0/4 → 1.0. 칸 1: g 0/2, k 4/4 → 1.0. 칸 2: g 1/2, k 4/4 → 1.5
    hits = np.array([[[1, 1, 0, 0, 0, 0], [0, 0, 1, 1, 1, 1], [1, 0, 1, 1, 1, 1]]], dtype=bool)
    source = np.array(["g", "g", "k", "k", "k", "k"])
    scores = ensemble.balanced_scores(hits, source)
    assert list(scores[0]) == [2 * 4, 4 * 2, 1 * 4 + 4 * 2]
    # 한 행을 빼면 그 출처의 분모도 준다: 행 0을 빼면 g는 1행
    assert list(ensemble.balanced_scores(hits, source, np.arange(6) != 0)[0]) == [1 * 4, 4 * 1, 0 * 4 + 4 * 1]


def test_pick_prefers_half_weight_then_higher_threshold():
    scores = np.zeros((len(ensemble.WEIGHT_GRID), len(ensemble.THRESHOLD_GRID)), dtype=object)
    scores[:, :] = 5
    assert ensemble.pick(scores) == (0.5, ensemble.THRESHOLD_GRID[-1])
    scores[2, 0] = 6
    assert ensemble.pick(scores) == (ensemble.WEIGHT_GRID[2], 0.0)
