# 진료과 모델 B(backlog 07): 버튼 조합 → 진료과 10종 분포. button_department.csv의 분포를 소프트 라벨로 학습하는 2층 MLP(numpy).
# - 입력은 features/buttons.py의 FEATURE_NAMES 중 부위 13·증상 15·손상 여부 1 = 29개 열이다. 표에는 이것만 있어 나머지 피처는 쓰지 않는다.
# - 손상 여부: 표의 any 조합은 손상 있음·없음 두 행으로 펴서 각각 가중치 0.5로 학습한다. 서빙 때 손상 여부를 모르면(NaN)
#   손상 있음·없음 두 예측의 평균을 낸다.
# - 검증셋은 05의 진료과 안내 조합(dept_valid.txt)이다. 그 조합과 같은 표 행(same_combo)은 학습에서 뺀다.
#   L2 세기와 에폭 수는 남은 학습 행 안 5겹 교차검증(소프트 교차엔트로피)으로 정해, 검증셋은 평가에만 쓴다(사용자와 정함).
# - 전체 배치 Adam, float64, seed 고정 → 같은 데이터면 같은 가중치. 가중치는 JSON으로 내보내고, 불러올 때 코드를 실행하지 않는다.
# - backlog 13: 학습 설정(Setting)을 묶었다. V0은 07의 설정, 후보(CANDIDATES)는 찾는 범위를 넓힌 것(은닉 {8, 16, 32} × L2 5개 × 에폭 5 간격),
#   seed 5개로 학습한 MLP의 평균, 두 개 선택 행 합성(같은 부위의 두 증상 또는 같은 증상의 두 부위. 분포는 평균 또는 곱한 뒤 정규화)이다.
#   설정은 학습 표를 조합 단위 5겹 × 반복 5번으로 나눈 교차검증(repeated_cv)으로 고른다. 안내 조합 검증셋은 고르는 데 쓰지 않는다.
#   합성 행은 학습 명령 안에서만 만들고 표(button_department.csv)는 단일 조합 그대로 둔다(사용자 결정, 2026-11-19).

import hashlib
import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass, replace
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.model_selection import KFold

from fornav_modeling.data import split
from fornav_modeling.evaluate import ratio, topk_metrics, topk_table
from fornav_modeling.features.buttons import FEATURE_NAMES, featurize, featurize_many
from fornav_modeling.labels import department as dept
from fornav_modeling.predict import forward, predict_from_weights
from fornav_modeling.predict import softmax as _softmax
from fornav_modeling.schema import DEPARTMENTS, Department

SEED = 20261028
INPUT_FEATURES: tuple[str, ...] = tuple(n for n in FEATURE_NAMES if n.startswith(("body_", "symptom_")) or n == "injury")
_INPUT_INDEX = [FEATURE_NAMES.index(n) for n in INPUT_FEATURES]
HIDDEN = 32
LEARNING_RATE = 0.01
L2_GRID = (1e-4, 1e-3, 1e-2)
MAX_EPOCHS = 3000
CHECK_EVERY = 25
CV_FOLDS = 5
CV_REPEATS = 5  # repeated_cv: 조합 단위 5겹을 seed를 바꿔 다섯 번
PAIR_FLOOR = 0.01  # 곱한 뒤 정규화할 때 한쪽에만 있는 진료과가 0이 되지 않게 더하는 값(표의 PROB_FLOOR와 같다)
PAIR_WEIGHT = 0.5  # 합성 행 가중치 합 = 단일 조합 행 가중치 합 × 이 값
GUIDE_WEIGHT = 1.0


@dataclass(frozen=True)
class Setting:
    """학습 설정. 하이퍼파라미터는 hidden × l2 × 에폭(check_every 간격, max_epochs까지)에서 학습 조합 5겹 교차검증으로 고른다."""

    hidden: tuple[int, ...] = (HIDDEN,)
    l2: tuple[float, ...] = L2_GRID
    max_epochs: int = MAX_EPOCHS
    check_every: int = CHECK_EVERY
    seeds: tuple[int, ...] = (SEED,)  # 여럿이면 같은 하이퍼파라미터로 seed마다 학습해 평균한다
    pairs: str | None = None  # None | "mean" | "product"
    pair_weight: float = PAIR_WEIGHT
    guide: bool = False  # backlog 19: 학습용 안내 조합(department_guide_train.csv)을 학습 행으로 더한다
    guide_weight: float = GUIDE_WEIGHT  # 안내 조합 버튼 키 하나의 가중치(표 조합 하나 = 1)


V0 = Setting()
_WIDE = Setting(hidden=(8, 16, 32), l2=(1e-3, 3e-3, 1e-2, 3e-2, 1e-1), max_epochs=2000, check_every=5)
_SEEDS5 = tuple(SEED + i for i in range(5))
CANDIDATES: dict[str, Setting] = {
    "v0": V0,
    "wide": _WIDE,
    "wide_seeds5": replace(_WIDE, seeds=_SEEDS5),
    "wide_seeds5_pairs_mean": replace(_WIDE, seeds=_SEEDS5, pairs="mean"),
    "wide_seeds5_pairs_product": replace(_WIDE, seeds=_SEEDS5, pairs="product"),
    "v0_guide": replace(V0, guide=True),
    "wide_seeds5_guide": replace(_WIDE, seeds=_SEEDS5, guide=True),
    "wide_seeds5_pairs_mean_guide": replace(_WIDE, seeds=_SEEDS5, pairs="mean", guide=True),
}
Guide = Mapping[str, tuple[dict, dept.Distribution]]  # dept.guide_train_table의 결과

WEIGHTS_FILE = "weights.json"
METADATA_FILE = "metadata.json"  # 임시 형식. 확정은 backlog 08


# ---------------------------------------------------------------------------
# 추론. forward·predict_from_weights는 서빙(predict.py)과 같은 함수를 쓴다
# ---------------------------------------------------------------------------
def department_proba(weights: Mapping[str, Any], intake: Mapping[str, Any]) -> dict[Department, float]:
    """입력 dict 하나 → {진료과: 확률}. 키는 DEPARTMENTS 10종 그대로(순서 포함)."""
    proba = predict_from_weights(weights, np.array([featurize(intake)], dtype=np.float64))[0]
    return {d: float(p) for d, p in zip(DEPARTMENTS, proba, strict=True)}


# ---------------------------------------------------------------------------
# 학습
# ---------------------------------------------------------------------------
class DeptB:
    name = "dept_b"

    def __init__(self, weights: dict[str, Any] | None = None):
        self.weights = weights

    def fit(
        self, X_in: np.ndarray, T: np.ndarray, w: np.ndarray, l2: float, epochs: int, hidden: int = HIDDEN, seeds: tuple[int, ...] = (SEED,)
    ) -> "DeptB":
        """X_in: (행, 29) 0/1, T: (행, 10) 소프트 라벨, w: 행 가중치. 전체 배치 Adam으로 epochs번. seed가 여럿이면 seed마다 학습해 평균한다."""
        members = []
        for seed in seeds:
            params = _init(seed, hidden)
            for _ in _adam(params, X_in, T, w, l2, epochs):
                pass
            members.append(params)
        self.weights = _export(members[0]) if len(members) == 1 else _export_members(members)
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return predict_from_weights(self.weights, X)

    def to_text(self) -> str:
        return json.dumps(self.weights, indent=1) + "\n"

    @classmethod
    def from_text(cls, text: str) -> "DeptB":
        return cls(json.loads(text))


def _init(seed: int = SEED, hidden: int = HIDDEN) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(seed)
    n_in, n_out = len(INPUT_FEATURES), len(DEPARTMENTS)
    return {
        "W1": rng.normal(0.0, np.sqrt(2.0 / n_in), size=(n_in, hidden)),
        "b1": np.zeros(hidden),
        "W2": rng.normal(0.0, np.sqrt(1.0 / hidden), size=(hidden, n_out)),
        "b2": np.zeros(n_out),
    }


def soft_cross_entropy(P: np.ndarray, T: np.ndarray, w: np.ndarray) -> float:
    return float(-(w * (T * np.log(np.clip(P, 1e-12, None))).sum(axis=1)).sum() / w.sum())


def loss_and_gradients(params: Mapping[str, np.ndarray], X: np.ndarray, T: np.ndarray, w: np.ndarray, l2: float) -> tuple[float, dict]:
    """손실 = 가중 소프트 교차엔트로피 + l2/2·(‖W1‖² + ‖W2‖²)와 그 기울기."""
    weight = (w / w.sum())[:, None]
    pre = X @ params["W1"] + params["b1"]
    h = np.maximum(pre, 0.0)
    P = _softmax(h @ params["W2"] + params["b2"])
    loss = soft_cross_entropy(P, T, w) + l2 / 2 * float((params["W1"] ** 2).sum() + (params["W2"] ** 2).sum())
    dz = weight * (P - T)
    dh = (dz @ params["W2"].T) * (pre > 0)
    grads = {"W2": h.T @ dz + l2 * params["W2"], "b2": dz.sum(axis=0), "W1": X.T @ dh + l2 * params["W1"], "b1": dh.sum(axis=0)}
    return loss, grads


def _adam(params: dict[str, np.ndarray], X: np.ndarray, T: np.ndarray, w: np.ndarray, l2: float, epochs: int):
    """한 에폭마다 params를 고치고 에폭 번호(1부터)를 내준다."""
    m = {k: np.zeros_like(v) for k, v in params.items()}
    v = {k: np.zeros_like(p) for k, p in params.items()}
    beta1, beta2, eps = 0.9, 0.999, 1e-8
    for epoch in range(1, epochs + 1):
        _, grads = loss_and_gradients(params, X, T, w, l2)
        for k, g in grads.items():
            m[k] = beta1 * m[k] + (1 - beta1) * g
            v[k] = beta2 * v[k] + (1 - beta2) * g * g
            params[k] -= LEARNING_RATE * (m[k] / (1 - beta1**epoch)) / (np.sqrt(v[k] / (1 - beta2**epoch)) + eps)
        yield epoch


def _header() -> dict[str, Any]:
    return {
        "feature_names": list(FEATURE_NAMES),
        "input_features": list(INPUT_FEATURES),
        "labels": list(DEPARTMENTS),
        "activation": "relu",
        "injury_missing": "손상 있음·없음 두 예측의 평균",
    }


def _layers(params: dict[str, np.ndarray]) -> dict[str, Any]:
    return {k: params[k].tolist() for k in ("W1", "b1", "W2", "b2")}


def _export(params: dict[str, np.ndarray]) -> dict[str, Any]:
    return _header() | {"hidden": int(params["b1"].shape[0])} | _layers(params)


def _export_members(members: list[dict[str, np.ndarray]]) -> dict[str, Any]:
    """seed마다 학습한 MLP 여럿. predict.forward가 각 확률을 평균한다."""
    return _header() | {
        "hidden": int(members[0]["b1"].shape[0]),
        "average": "members 확률의 평균",
        "members": [_layers(m) for m in members],
    }


def training_rows(
    table: Mapping[str, dept.Distribution],
    pairs: str | None = None,
    pair_weight: float = PAIR_WEIGHT,
    guide: Guide | None = None,
    guide_weight: float = GUIDE_WEIGHT,
) -> tuple[list[str], np.ndarray, np.ndarray, np.ndarray]:
    """{combo_id: 분포} → (행마다의 combo_id, X_in, T, w). any 조합은 손상 있음·없음 두 행(가중치 0.5씩)으로 편다.
    pairs가 있으면 synthetic_pairs의 두 개 선택 행을 뒤에 붙인다. 합성 행 가중치 합은 단일 조합 행 가중치 합 × pair_weight."""
    cids, rows, targets, weights = [], [], [], []
    for cid, dist in table.items():
        _append(cids, rows, targets, weights, cid, dept.combo_intake(cid), [dist.get(d, 0.0) for d in DEPARTMENTS], 1.0)
    if pairs is not None:
        synthetic = synthetic_pairs(table, pairs)
        each = pair_weight * len(table) / len(synthetic) if synthetic else 0.0
        for cid, intake, target in synthetic:
            _append(cids, rows, targets, weights, cid, intake, target, each)
    for key, (intake, dist) in (guide or {}).items():
        _append(cids, rows, targets, weights, f"guide:{key}", intake, [dist.get(d, 0.0) for d in DEPARTMENTS], guide_weight)
    return cids, np.array(rows), np.array(targets), np.array(weights)


def _append(cids: list, rows: list, targets: list, weights: list, cid: str, intake: dict, target: list[float], weight: float) -> None:
    flags = [True, False] if intake["injury"] is None else [intake["injury"]]
    for flag in flags:
        cids.append(cid)
        rows.append(np.array(featurize(intake | {"injury": flag}), dtype=np.float64)[_INPUT_INDEX])
        targets.append(target)
        weights.append(weight / len(flags))


_PAIR_INJURY = {("yes", "yes"): "yes", ("no", "no"): "no", ("any", "any"): "any", ("any", "yes"): "yes", ("any", "no"): "no"}


def synthetic_pairs(table: Mapping[str, dept.Distribution], how: str) -> list[tuple[str, dict, list[float]]]:
    """표의 두 조합 중 부위나 증상 하나만 같은 쌍 → 두 개 선택 입력(부위 2·증상 1 또는 부위 1·증상 2)과 섞은 분포.
    손상 여부가 맞지 않는 쌍(있음·없음)은 뺀다. how: "mean"(두 분포의 평균) 또는 "product"(PAIR_FLOOR를 더해 곱한 뒤 정규화)."""
    out = []
    for a, b in combinations(sorted(table), 2):
        (ba, sa, ia), (bb, sb, ib) = a.split("-"), b.split("-")
        injury = _PAIR_INJURY.get(tuple(sorted((ia, ib))))
        if injury is None or (ba == bb) == (sa == sb):
            continue
        ta = np.array([table[a].get(d, 0.0) for d in DEPARTMENTS])
        tb = np.array([table[b].get(d, 0.0) for d in DEPARTMENTS])
        if how == "mean":
            mixed = (ta + tb) / 2
        elif how == "product":
            mixed = (ta + PAIR_FLOOR) * (tb + PAIR_FLOOR)
            mixed = mixed / mixed.sum()
        else:
            raise ValueError(f"합성 방식은 mean·product 중 하나다: {how!r}")
        intake = {"body_parts": sorted({ba, bb}), "symptoms": sorted({sa, sb}), "injury": dept.INJURY_FLAGS[injury]}
        out.append((f"{a}+{b}", intake, mixed.tolist()))
    return out


def select_hyperparams(table: Mapping[str, dept.Distribution], setting: Setting = V0, guide: Guide | None = None) -> dict:
    """학습 조합을 5겹으로 나눠(조합 단위, any의 두 행은 같은 겹) 은닉 × L2 × 에폭을 고른다. 기준은 겹 밖 단일 조합의 소프트 교차엔트로피 평균.
    합성 행은 겹 안 조합끼리만 만든다. 초기화 seed는 setting.seeds[0]."""
    combos = sorted(table)
    folds = list(KFold(CV_FOLDS, shuffle=True, random_state=SEED).split(combos))
    checkpoints = list(range(setting.check_every, setting.max_epochs + 1, setting.check_every))
    grid = [(h, l2) for h in setting.hidden for l2 in setting.l2]
    losses = {cell: np.zeros(len(checkpoints)) for cell in grid}
    for train_idx, held_idx in folds:
        train_fold = {combos[i]: table[combos[i]] for i in train_idx}
        _, X_tr, T_tr, w_tr = training_rows(train_fold, setting.pairs, setting.pair_weight, _guide(setting, guide), setting.guide_weight)
        _, X_ho, T_ho, w_ho = training_rows({combos[i]: table[combos[i]] for i in held_idx})
        for hidden, l2 in grid:
            params = _init(setting.seeds[0], hidden)
            for epoch in _adam(params, X_tr, T_tr, w_tr, l2, setting.max_epochs):
                if epoch % setting.check_every == 0:
                    losses[hidden, l2][epoch // setting.check_every - 1] += soft_cross_entropy(forward(params, X_ho), T_ho, w_ho) / CV_FOLDS
    (hidden, l2), i = min(((cell, int(np.argmin(curve))) for cell, curve in losses.items()), key=lambda c: losses[c[0]][c[1]])
    rule = (
        f"학습 조합 {CV_FOLDS}겹 교차검증(조합 단위), 은닉 {list(setting.hidden)} × L2 {list(setting.l2)} × "
        f"에폭 {setting.check_every}~{setting.max_epochs}({setting.check_every} 간격), 겹 밖 소프트 교차엔트로피 평균 최소"
    )
    return {
        "hidden": hidden,
        "l2": l2,
        "epochs": checkpoints[i],
        "cv_soft_cross_entropy": round(float(losses[hidden, l2][i]), 6),
        "grid": {
            f"hidden={h} l2={k}": {"best_epochs": checkpoints[int(np.argmin(c))], "best_loss": round(float(c.min()), 6)}
            for (h, k), c in losses.items()
        },
        "rule": rule,
    }


def _guide(setting: Setting, guide: Guide | None) -> Guide | None:
    if setting.guide and guide is None:
        raise ValueError("안내 조합을 쓰는 설정인데 guide_train_table을 넘기지 않았다")
    return guide if setting.guide else None


def fit_setting(table: Mapping[str, dept.Distribution], setting: Setting = V0, guide: Guide | None = None) -> tuple["DeptB", dict]:
    """설정대로 하이퍼파라미터를 고르고 표 전체(합성 행·안내 조합 행 포함)로 학습한다.
    하이퍼파라미터 교차검증의 겹 밖 손실은 표 조합으로만 잰다(안내 조합 행은 모든 겹에서 학습에 들어간다)."""
    hyper = select_hyperparams(table, setting, guide)
    _, X, T, w = training_rows(table, setting.pairs, setting.pair_weight, _guide(setting, guide), setting.guide_weight)
    model = DeptB().fit(X, T, w, hyper["l2"], hyper["epochs"], hyper["hidden"], setting.seeds)
    return model, hyper | {"train_rows": len(T)}


# ---- 표 성능 반복 교차검증과 비교 기준선(backlog 13) ----


def repeated_cv(table: Mapping[str, dept.Distribution], predictor, repeats: int = CV_REPEATS) -> dict:
    """조합 단위 5겹을 repeats번(seed SEED+r) 나눠, 겹 밖 조합을 predictor(학습 표, 조합 목록) → 확률로 예측한다.
    반복마다 KL 평균과 표 1순위 대비 Top-1·Top-2(분자·분모)를 내고, 반복 사이 평균·표준편차를 적는다."""
    combos = sorted(table)
    per_repeat = []
    for r in range(repeats):
        proba = np.zeros((len(combos), len(DEPARTMENTS)))
        for train_idx, held_idx in KFold(CV_FOLDS, shuffle=True, random_state=SEED + r).split(combos):
            held = [combos[i] for i in held_idx]
            proba[held_idx] = predictor({combos[i]: table[combos[i]] for i in train_idx}, held)
        T = np.array([[table[c].get(d, 0.0) for d in DEPARTMENTS] for c in combos])
        m = topk_metrics(proba, T.argmax(axis=1), DEPARTMENTS)
        per_repeat.append({"kl_mean": float(kl_divergence(T, proba).mean()), "top1": m["top1"], "top2": m["top2"]})
    summary = {}
    for key in ("kl_mean", "top1", "top2"):
        values = np.array([p[key] if key == "kl_mean" else p[key]["value"] for p in per_repeat])
        summary[key] = {"mean": round(float(values.mean()), 4), "std": round(float(values.std()), 4)}
    return {"combos": len(combos), "folds": CV_FOLDS, "repeats": repeats, "summary": summary, "per_repeat": per_repeat}


def mlp_predictor(setting: Setting, guide: Guide | None = None):
    def predict(train: Mapping[str, dept.Distribution], cids: list[str]) -> np.ndarray:
        model, _ = fit_setting(train, setting, guide)
        return model.predict_proba(featurize_many([dept.combo_intake(c) for c in cids]))

    return predict


def logistic_predictor(train: Mapping[str, dept.Distribution], cids: list[str]) -> np.ndarray:
    """다항 로지스틱 회귀(scikit-learn, C=1). 소프트 라벨은 (행, 진료과)마다 확률 × 행 가중치를 표본 가중치로 펴서 학습한다.
    손상 여부 모름은 MLP와 같이 있음·없음 예측의 평균."""
    from sklearn.linear_model import LogisticRegression

    _, X, T, w = training_rows(train)
    keep = T > 0
    rows, labels = np.nonzero(keep)
    model = LogisticRegression(C=1.0, max_iter=5000).fit(X[rows], labels, sample_weight=(T * w[:, None])[keep])

    def proba(X_in: np.ndarray) -> np.ndarray:
        out = np.zeros((len(X_in), len(DEPARTMENTS)))
        out[:, model.classes_] = model.predict_proba(X_in)
        return out

    X_full = featurize_many([dept.combo_intake(c) for c in cids])
    X_in = np.nan_to_num(X_full[:, _INPUT_INDEX], nan=0.0)
    unknown = np.isnan(X_full[:, FEATURE_NAMES.index("injury")])
    injury = INPUT_FEATURES.index("injury")
    yes, no = X_in.copy(), X_in.copy()
    yes[:, injury], no[:, injury] = 1.0, 0.0
    return np.where(unknown[:, None], (proba(yes) + proba(no)) / 2, proba(X_in))


def backoff_predictor(train: Mapping[str, dept.Distribution], cids: list[str]) -> np.ndarray:
    """표 조회 + 백오프: 같은 조합(same_combo) 행의 평균, 없으면 같은 부위 행 평균과 같은 증상 행 평균의 평균, 그것도 없으면 전체 평균."""

    def vec(cid: str) -> np.ndarray:
        return np.array([train[cid].get(d, 0.0) for d in DEPARTMENTS])

    everything = np.mean([vec(c) for c in train], axis=0)
    out = []
    for cid in cids:
        if same := [c for c in train if dept.same_combo(c, cid)]:
            out.append(np.mean([vec(c) for c in same], axis=0))
            continue
        body, symptom, _ = cid.split("-")
        parts = [[c for c in train if c.split("-")[i] == v] for i, v in ((0, body), (1, symptom))]
        parts = [np.mean([vec(c) for c in p], axis=0) for p in parts if p]
        out.append(np.mean(parts, axis=0) if parts else everything)
    return np.array(out)


def lookup_upper_bound(table: Mapping[str, dept.Distribution], cids: list[str]) -> np.ndarray:
    """표 상한: 조합과 같은 표 행(학습에서 뺀 행 포함)의 분포를 그대로 답으로. 표 행이 없으면 0(오답으로 센다)."""
    out = []
    for cid in cids:
        same = [c for c in table if dept.same_combo(c, cid)]
        out.append(np.mean([[table[c].get(d, 0.0) for d in DEPARTMENTS] for c in same], axis=0) if same else np.zeros(len(DEPARTMENTS)))
    return np.array(out)


def choose_setting(cv: Mapping[str, dict]) -> str:
    """KL 평균이 가장 낮은 후보. 단, V0보다 V0의 반복 간 표준편차 이상 낮지 않으면 v0을 둔다(편차를 넘을 때만 개선으로 본다)."""
    base = cv["v0"]["summary"]["kl_mean"]
    best = min(cv, key=lambda k: (cv[k]["summary"]["kl_mean"]["mean"], k))
    return best if base["mean"] - cv[best]["summary"]["kl_mean"]["mean"] > base["std"] else "v0"


def split_table(table: Mapping[str, dept.Distribution], valid_ids: list[str], test_ids: list[str] = ()) -> tuple[dict, dict]:
    """(학습 표, 검증용으로 뺀 표). 검증 조합과 same_combo인 표 행은 학습에서 빼 검증용으로 둔다.
    최종 평가용 조합(backlog 18, id만)과 same_combo인 행은 학습에서도 검증용에서도 뺀다."""
    final = {cid for cid in table if any(dept.same_combo(cid, t) for t in test_ids)}
    held = {cid for cid in table if cid not in final and any(dept.same_combo(cid, v) for v in valid_ids)}
    return {c: d for c, d in table.items() if c not in held | final}, {c: table[c] for c in sorted(held)}


def kl_divergence(T: np.ndarray, P: np.ndarray) -> np.ndarray:
    """행마다 KL(표 분포 ‖ 모델 분포). 표에서 0인 칸은 더하지 않는다."""
    T, P = np.asarray(T), np.clip(np.asarray(P), 1e-12, None)
    return np.where(T > 0, T * np.log(np.where(T > 0, T, 1.0) / P), 0.0).sum(axis=1)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


# ---- 라운드 실행: 학습·검증셋 평가·저장(scripts/train_dept_b.py), test 평가(scripts/evaluate.py) ----

# 표에 없는 조합(부위·증상 쌍이 표에 없거나 여러 개 선택). 상위 2개가 상식과 맞는지 결과에 적는다
UNSEEN_EXAMPLES: tuple[dict, ...] = (
    {"body_parts": ["back"], "symptoms": ["bleeding"], "injury": True},
    {"body_parts": ["arm"], "symptoms": ["rash"]},
    {"body_parts": ["teeth"], "symptoms": ["fever"]},
    {"body_parts": ["whole"], "symptoms": ["bleeding"], "injury": True},
    {"body_parts": ["hand"], "symptoms": ["cut", "bleeding"], "injury": True},
    {"body_parts": ["head", "whole"], "symptoms": ["fever", "cough"], "injury": False},
)


def cv_round(tables_dir: Path, splits_dir: Path, reports_dir: Path) -> dict:
    """학습 표(검증·최종 평가 조합과 같은 행을 뺀 표)로 후보 설정·비교 기준선을 반복 교차검증하고 고른 설정을 적는다(backlog 13 2·5·6단계)."""
    valid_ids, _ = dept.guide_set(tables_dir, splits_dir)
    train_table, _ = split_table(dept.read_button_department(tables_dir), valid_ids, dept.held_test_ids(splits_dir))
    guide = dept.guide_train_table(tables_dir, splits_dir)
    cv = {name: repeated_cv(train_table, mlp_predictor(setting, guide)) for name, setting in CANDIDATES.items()}
    chosen = choose_setting(cv)
    baselines = {"logistic": repeated_cv(train_table, logistic_predictor), "backoff": repeated_cv(train_table, backoff_predictor)}
    report = {
        "button_department_sha256": _sha256_file(tables_dir / dept.BUTTON_DEPARTMENT),
        "train_combos": len(train_table),
        "candidates": {name: asdict(setting) for name, setting in CANDIDATES.items()},
        "cv": cv,
        "baselines": baselines,
        "chosen": chosen,
        "rule": choose_setting.__doc__,
    }
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "dept_b_cv.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    lines = [
        "# dept_b_cv",
        "",
        f"학습 표 {len(train_table)}개 조합, 조합 단위 {CV_FOLDS}겹 × 반복 {CV_REPEATS}번. 평균 ± 반복 간 표준편차. Top-k 정답은 표 1순위",
        "",
        "| 설정 | KL 평균 | Top-1 | Top-2 |",
        "|---|---|---|---|",
    ]
    for name, result in {**cv, **baselines}.items():
        m = result["summary"]
        cells = [f"{m[k]['mean']:.4f} ± {m[k]['std']:.4f}" for k in ("kl_mean", "top1", "top2")]
        lines.append(f"| {name}{' (선택)' if name == chosen else ''} | " + " | ".join(cells) + " |")
    (reports_dir / "dept_b_cv.md").write_text("\n".join(lines) + "\n")
    return report


def train_round(
    tables_dir: Path, splits_dir: Path, processed_dir: Path, models_dir: Path, reports_dir: Path, round_name: str, setting_name: str = "v0"
) -> dict:
    """표에서 검증·최종 평가 조합을 빼고 설정대로 학습해, 검증셋(안내 정답)·뺀 표 행·질환·증상 valid로 평가하고 저장한다.
    안내 조합은 비교 기준선(옛 v0 가중치, V0 설정 재학습, 로지스틱, 표 조회 + 백오프, 표 상한)과 같은 셋으로 잰다."""
    setting = CANDIDATES[setting_name]
    model_dir = models_dir / "dept_b" / round_name
    table = dept.read_button_department(tables_dir)
    valid_ids, guide = dept.guide_set(tables_dir, splits_dir)
    train_table, held_table = split_table(table, valid_ids, dept.held_test_ids(splits_dir))
    guide_train = dept.guide_train_table(tables_dir, splits_dir) if setting.guide else None
    model, hyper = fit_setting(train_table, setting, guide_train)
    valid = split.load_symptom_dev(processed_dir, splits_dir, "valid")

    old_v0 = json.loads((models_dir / "dept_b" / "v0" / WEIGHTS_FILE).read_text())
    X_guide = featurize_many([dept.combo_intake(cid) for cid in valid_ids])
    comparisons = {
        "v0(옛 가중치, 최종 평가 조합도 학습)": predict_from_weights(old_v0, X_guide),
        "V0 설정 재학습(이 표)": fit_setting(train_table, V0)[0].predict_proba(X_guide) if setting_name != "v0" else None,
        "로지스틱": logistic_predictor(train_table, valid_ids),
        "표 조회 + 백오프": backoff_predictor(train_table, valid_ids),
        "표 상한(뺀 행 포함)": lookup_upper_bound(table, valid_ids),
        f"{round_name}({setting_name})": model.predict_proba(X_guide),
    }
    results = {
        "guide": _evaluate_guide(model, valid_ids, guide),
        "guide_comparison": {name: _guide_metrics(p, valid_ids, guide) for name, p in comparisons.items() if p is not None},
        "held_out_table": _evaluate_table(model, held_table),
        "train_table": _evaluate_table(model, train_table),
        "unseen_examples": [_example(model, intake) for intake in UNSEEN_EXAMPLES],
        "symptom_valid": _evaluate_symptom(model.weights, valid, tables_dir),
        "symptom_valid_old_v0": _evaluate_symptom(old_v0, valid, tables_dir),
    }
    text = model.to_text()
    _refuse_if_tested(model_dir, reports_dir, round_name, text)
    report = {
        "round": round_name,
        "model_version": f"dept_b/{round_name}",
        "seed": SEED,
        "setting": {"name": setting_name, **asdict(setting)},
        "architecture": {
            "inputs": len(INPUT_FEATURES),
            "hidden": hyper["hidden"],
            "activation": "relu",
            "outputs": len(DEPARTMENTS),
            "members": len(setting.seeds),
            "optimizer": f"전체 배치 Adam, 학습률 {LEARNING_RATE}",
        },
        "hyperparams": hyper,
        "data": {
            "button_department_sha256": _sha256_file(tables_dir / dept.BUTTON_DEPARTMENT),
            "dept_valid_sha256": _sha256_file(splits_dir / dept.VALID_IDS),
            "combos": {
                "table": len(table),
                "train": len(train_table),
                "held_out": len(held_table),
                "dropped_final": len(table) - len(train_table) - len(held_table),
                "guide": len(valid_ids),
            },
            "train_rows": hyper["train_rows"],
            "guide_train_keys": len(guide_train or {}),
            "guide_train_rows": len(dept.read_guide_train(tables_dir)) if setting.guide else 0,
        },
        "input_features": list(INPUT_FEATURES),
        "labels": list(DEPARTMENTS),
        "results": results,
    }
    model_dir.mkdir(parents=True, exist_ok=True)
    (model_dir / WEIGHTS_FILE).write_text(text)
    metadata = {
        k: report[k] for k in ("model_version", "seed", "setting", "architecture", "hyperparams", "data", "input_features", "labels")
    }
    metadata |= {
        "status": "학습 라운드. 서빙 묶음은 export.py가 쓴다",
        "files": {WEIGHTS_FILE: sha256_text(text)},
        "feature_names": list(FEATURE_NAMES),
    }
    (model_dir / METADATA_FILE).write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    table_md = {f"안내 조합 — {name}": m["all"] for name, m in results["guide_comparison"].items()}
    table_md |= {f"안내 외상·산재 — {name}": m["trauma"] for name, m in results["guide_comparison"].items()}
    table_md["MLP 학습에서 뺀 표 행(정답 = 표 1순위)"] = results["held_out_table"]["vs_table_top1"]
    table_md |= {f"질환·증상 valid {k} — {round_name}": v for k, v in results["symptom_valid"].items()}
    table_md |= {f"질환·증상 valid {k} — 옛 v0": v for k, v in results["symptom_valid_old_v0"].items()}
    _write_report(reports_dir, f"dept_b_{round_name}", report, table_md)
    return report


def _guide_metrics(proba: np.ndarray, ids: list[str], guide: Mapping[str, dept.GuideAnswer]) -> dict:
    y = np.array([DEPARTMENTS.index(guide[cid].department) for cid in ids], dtype=np.int64)
    trauma = np.array([dept.is_trauma(cid) for cid in ids])
    return {
        "all": topk_metrics(proba, y, DEPARTMENTS),
        "trauma": topk_metrics(proba[trauma], y[trauma], DEPARTMENTS),
        "non_trauma": topk_metrics(proba[~trauma], y[~trauma], DEPARTMENTS),
    }


def _evaluate_symptom(weights: Mapping[str, Any], rows: pd.DataFrame, tables_dir: Path) -> dict:
    """질환·증상 valid(정답 = 질환의 1순위 진료과): 전체·출처별·버튼 수별. 여러 개 선택 입력 성능은 버튼 수별로 본다."""
    from fornav_modeling.models.dept_a import row_masks, true_departments

    proba = predict_from_weights(weights, featurize_many(rows.to_dict("records")))
    y = true_departments(rows["disease"], dept.read_disease_department(tables_dir))
    return {name: topk_metrics(proba[m], y[m], DEPARTMENTS) for name, m in row_masks(rows).items() if m.any()}


def evaluate_test_round(test: pd.DataFrame, model_dir: Path, tables_dir: Path, reports_dir: Path, round_name: str) -> dict:
    """Kaggle 질환·증상 test(정답 = 질환의 1순위 진료과)로 한 번 평가해 '최종'으로 기록한다. 모델 B는 Kaggle로 학습하지 않았다."""
    from fornav_modeling.models.dept_a import true_departments

    name = f"dept_b_{round_name}_test"
    if (reports_dir / f"{name}.json").exists():
        raise FileExistsError(f"{name}.json이 이미 있다. test 평가는 라운드마다 한 번만 한다. 조정했다면 새 라운드로 기록한다")
    metadata = json.loads((model_dir / METADATA_FILE).read_text())
    text = (model_dir / WEIGHTS_FILE).read_text()
    if {WEIGHTS_FILE: sha256_text(text)} != metadata["files"]:
        raise ValueError(f"{model_dir}의 {WEIGHTS_FILE}가 {METADATA_FILE}에 적힌 해시와 다르다")
    proba = predict_from_weights(json.loads(text), featurize_many(test.to_dict("records")))
    result = topk_metrics(proba, true_departments(test["disease"], dept.read_disease_department(tables_dir)), DEPARTMENTS)
    report = {
        "round": round_name,
        "final": True,
        "note": "test 평가는 이 라운드에서 한 번만 했다. Kaggle 행은 증상 여러 개·손상 여부 모름",
        "rows": len(test),
        "files": metadata["files"],
        "department": result,
    }
    _write_report(reports_dir, name, report, {"MLP test(Kaggle) — 최종": result})
    return report


def _evaluate_guide(model: DeptB, ids: list[str], guide: Mapping[str, dept.GuideAnswer]) -> dict:
    proba = model.predict_proba(featurize_many([dept.combo_intake(cid) for cid in ids]))
    y = np.array([DEPARTMENTS.index(guide[cid].department) for cid in ids], dtype=np.int64)
    reviewed = np.array([guide[cid].reviewed for cid in ids])
    trauma = np.array([dept.is_trauma(cid) for cid in ids])
    return {
        "all": topk_metrics(proba, y, DEPARTMENTS),
        "reviewed_yes": topk_metrics(proba[reviewed], y[reviewed], DEPARTMENTS) if reviewed.any() else None,
        "reviewed_no_rows": int((~reviewed).sum()),
        "trauma": topk_metrics(proba[trauma], y[trauma], DEPARTMENTS),
        "non_trauma": topk_metrics(proba[~trauma], y[~trauma], DEPARTMENTS),
        "trauma_ids": [cid for cid, t in zip(ids, trauma, strict=True) if t],
    }


def _evaluate_table(model: DeptB, table: Mapping[str, dept.Distribution]) -> dict:
    """표 행(조합당 하나, any는 손상 여부 모름으로 예측) → KL 평균, 표 1순위 대비 Top-k. 외상·산재 조합을 따로 센다."""
    cids = list(table)
    proba = model.predict_proba(featurize_many([dept.combo_intake(c) for c in cids]))
    T = np.array([[table[c].get(d, 0.0) for d in DEPARTMENTS] for c in cids])
    kl = kl_divergence(T, proba)
    trauma = np.array([dept.is_trauma(c) for c in cids])
    y = T.argmax(axis=1)  # 동점이면 DEPARTMENTS 순서가 앞선 쪽 — dept.top과 같다
    return {
        "kl_mean": round(float(kl.mean()), 4),
        "kl_mean_trauma": round(float(kl[trauma].mean()), 4) if trauma.any() else None,
        "kl_mean_non_trauma": round(float(kl[~trauma].mean()), 4) if (~trauma).any() else None,
        "vs_table_top1": topk_metrics(proba, y, DEPARTMENTS),
        "trauma_vs_table_top1": topk_metrics(proba[trauma], y[trauma], DEPARTMENTS) if trauma.any() else None,
        "trauma_rows": ratio(trauma.sum(), len(cids)),
    }


def _example(model: DeptB, intake: dict) -> dict:
    out = department_proba(model.weights, intake)
    top2 = sorted(out, key=lambda d: (-out[d], DEPARTMENTS.index(d)))[:2]
    return {"input": intake, "sum": round(sum(out.values()), 6), "top2": {d: round(out[d], 4) for d in top2}}


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _refuse_if_tested(model_dir: Path, reports_dir: Path, round_name: str, text: str) -> None:
    if not (reports_dir / f"dept_b_{round_name}_test.json").exists():
        return
    path = model_dir / WEIGHTS_FILE
    if not path.exists() or path.read_text() != text:
        raise FileExistsError(f"{round_name}는 이미 test로 평가했는데 모델이 달라졌다. 새 라운드 이름으로 학습한다")


def _write_report(reports_dir: Path, name: str, report: dict, table: dict[str, dict]) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / f"{name}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    (reports_dir / f"{name}.md").write_text(f"# {name}\n\n진료과 Top-k 적중률(분자/분모)\n\n" + topk_table(table))
