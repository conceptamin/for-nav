# 진료과 모델 B(backlog 07): 버튼 조합 → 진료과 10종 분포. button_department.csv의 분포를 소프트 라벨로 학습하는 2층 MLP(numpy).
# - 입력은 features/buttons.py의 FEATURE_NAMES 중 부위 13·증상 15·손상 여부 1 = 29개 열이다. 표에는 이것만 있어 나머지 피처는 쓰지 않는다.
# - 손상 여부: 표의 any 조합은 손상 있음·없음 두 행으로 펴서 각각 가중치 0.5로 학습한다. 서빙 때 손상 여부를 모르면(NaN)
#   손상 있음·없음 두 예측의 평균을 낸다.
# - 검증셋은 05의 진료과 안내 조합(dept_valid.txt)이다. 그 조합과 같은 표 행(same_combo)은 학습에서 뺀다.
#   L2 세기와 에폭 수는 남은 학습 행 안 5겹 교차검증(소프트 교차엔트로피)으로 정해, 검증셋은 평가에만 쓴다(사용자와 정함).
# - 전체 배치 Adam, float64, seed 고정 → 같은 데이터면 같은 가중치. 가중치는 JSON으로 내보내고, 불러올 때 코드를 실행하지 않는다.

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.model_selection import KFold

from fornav_modeling.evaluate import ratio, topk_metrics, topk_table
from fornav_modeling.features.buttons import FEATURE_NAMES, featurize, featurize_many
from fornav_modeling.labels import department as dept
from fornav_modeling.schema import DEPARTMENTS, Department

SEED = 20261028
INPUT_FEATURES: tuple[str, ...] = tuple(n for n in FEATURE_NAMES if n.startswith(("body_", "symptom_")) or n == "injury")
_INPUT_INDEX = [FEATURE_NAMES.index(n) for n in INPUT_FEATURES]
_INJURY = INPUT_FEATURES.index("injury")
HIDDEN = 32
LEARNING_RATE = 0.01
L2_GRID = (1e-4, 1e-3, 1e-2)
MAX_EPOCHS = 3000
CHECK_EVERY = 25
CV_FOLDS = 5

WEIGHTS_FILE = "weights.json"
METADATA_FILE = "metadata.json"  # 임시 형식. 확정은 backlog 08


# ---------------------------------------------------------------------------
# 추론(JSON 가중치만으로 동작)
# ---------------------------------------------------------------------------
def forward(weights: Mapping[str, Any], X_in: np.ndarray) -> np.ndarray:
    """(행 수, 29) 입력 → (행 수, 10) 확률. 손상 여부 결측 처리는 하지 않는다(predict_from_weights가 한다)."""
    W1, b1, W2, b2 = (np.asarray(weights[k], dtype=np.float64) for k in ("W1", "b1", "W2", "b2"))
    h = np.maximum(X_in @ W1 + b1, 0.0)
    return _softmax(h @ W2 + b2)


def predict_from_weights(weights: Mapping[str, Any], X: np.ndarray) -> np.ndarray:
    """FEATURE_NAMES 순서의 피처 → 진료과 확률. weights.json을 json.loads한 dict만 있으면 된다.
    부위·증상 결측은 0(선택 안 함), 손상 여부 결측은 손상 있음·없음 예측의 평균."""
    if list(weights["feature_names"]) != list(FEATURE_NAMES) or list(weights["labels"]) != list(DEPARTMENTS):
        raise ValueError(f"{WEIGHTS_FILE}의 피처·라벨 순서가 지금 코드와 다르다")
    X_in = np.nan_to_num(np.asarray(X, dtype=np.float64)[:, [FEATURE_NAMES.index(n) for n in weights["input_features"]]], nan=0.0)
    injury = weights["input_features"].index("injury")
    unknown = np.isnan(np.asarray(X, dtype=np.float64)[:, FEATURE_NAMES.index("injury")])
    proba = forward(weights, X_in)
    if unknown.any():
        yes, no = X_in[unknown].copy(), X_in[unknown].copy()
        yes[:, injury], no[:, injury] = 1.0, 0.0
        proba[unknown] = (forward(weights, yes) + forward(weights, no)) / 2
    return proba


def department_proba(weights: Mapping[str, Any], intake: Mapping[str, Any]) -> dict[Department, float]:
    """입력 dict 하나 → {진료과: 확률}. 키는 DEPARTMENTS 10종 그대로(순서 포함)."""
    proba = predict_from_weights(weights, np.array([featurize(intake)], dtype=np.float64))[0]
    return {d: float(p) for d, p in zip(DEPARTMENTS, proba, strict=True)}


def _softmax(z: np.ndarray) -> np.ndarray:
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


# ---------------------------------------------------------------------------
# 학습
# ---------------------------------------------------------------------------
class DeptB:
    name = "dept_b"

    def __init__(self, weights: dict[str, Any] | None = None):
        self.weights = weights

    def fit(self, X_in: np.ndarray, T: np.ndarray, w: np.ndarray, l2: float, epochs: int) -> "DeptB":
        """X_in: (행, 29) 0/1, T: (행, 10) 소프트 라벨, w: 행 가중치. 전체 배치 Adam으로 epochs번."""
        params = _init()
        for _ in _adam(params, X_in, T, w, l2, epochs):
            pass
        self.weights = _export(params)
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return predict_from_weights(self.weights, X)

    def to_text(self) -> str:
        return json.dumps(self.weights, indent=1) + "\n"

    @classmethod
    def from_text(cls, text: str) -> "DeptB":
        return cls(json.loads(text))


def _init() -> dict[str, np.ndarray]:
    rng = np.random.default_rng(SEED)
    n_in, n_out = len(INPUT_FEATURES), len(DEPARTMENTS)
    return {
        "W1": rng.normal(0.0, np.sqrt(2.0 / n_in), size=(n_in, HIDDEN)),
        "b1": np.zeros(HIDDEN),
        "W2": rng.normal(0.0, np.sqrt(1.0 / HIDDEN), size=(HIDDEN, n_out)),
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


def _export(params: dict[str, np.ndarray]) -> dict[str, Any]:
    return {
        "feature_names": list(FEATURE_NAMES),
        "input_features": list(INPUT_FEATURES),
        "labels": list(DEPARTMENTS),
        "hidden": HIDDEN,
        "activation": "relu",
        "injury_missing": "손상 있음·없음 두 예측의 평균",
        **{k: params[k].tolist() for k in ("W1", "b1", "W2", "b2")},
    }


def training_rows(table: Mapping[str, dept.Distribution]) -> tuple[list[str], np.ndarray, np.ndarray, np.ndarray]:
    """{combo_id: 분포} → (행마다의 combo_id, X_in, T, w). any 조합은 손상 있음·없음 두 행(가중치 0.5씩)으로 편다."""
    cids, rows, targets, weights = [], [], [], []
    for cid, dist in table.items():
        intake = dept.combo_intake(cid)
        flags = [True, False] if intake["injury"] is None else [intake["injury"]]
        for flag in flags:
            x = np.array(featurize(intake | {"injury": flag}), dtype=np.float64)[_INPUT_INDEX]
            cids.append(cid)
            rows.append(x)
            targets.append([dist.get(d, 0.0) for d in DEPARTMENTS])
            weights.append(1.0 / len(flags))
    return cids, np.array(rows), np.array(targets), np.array(weights)


def select_hyperparams(table: Mapping[str, dept.Distribution]) -> dict:
    """학습 조합을 5겹으로 나눠(조합 단위, any의 두 행은 같은 겹) L2 × 에폭을 고른다. 기준은 겹 밖 소프트 교차엔트로피 평균."""
    combos = sorted(table)
    folds = list(KFold(CV_FOLDS, shuffle=True, random_state=SEED).split(combos))
    checkpoints = list(range(CHECK_EVERY, MAX_EPOCHS + 1, CHECK_EVERY))
    losses = {l2: np.zeros(len(checkpoints)) for l2 in L2_GRID}
    for train_idx, held_idx in folds:
        _, X_tr, T_tr, w_tr = training_rows({combos[i]: table[combos[i]] for i in train_idx})
        _, X_ho, T_ho, w_ho = training_rows({combos[i]: table[combos[i]] for i in held_idx})
        for l2 in L2_GRID:
            params = _init()
            for epoch in _adam(params, X_tr, T_tr, w_tr, l2, MAX_EPOCHS):
                if epoch % CHECK_EVERY == 0:
                    losses[l2][epoch // CHECK_EVERY - 1] += soft_cross_entropy(forward(params, X_ho), T_ho, w_ho) / CV_FOLDS
    l2, i = min(((l2, int(np.argmin(curve))) for l2, curve in losses.items()), key=lambda c: losses[c[0]][c[1]])
    return {
        "l2": l2,
        "epochs": checkpoints[i],
        "cv_soft_cross_entropy": round(float(losses[l2][i]), 6),
        "grid": {str(k): {"best_epochs": checkpoints[int(np.argmin(c))], "best_loss": round(float(c.min()), 6)} for k, c in losses.items()},
        "rule": f"학습 조합 {CV_FOLDS}겹 교차검증(조합 단위), L2 {list(L2_GRID)} × 에폭 {CHECK_EVERY}~{MAX_EPOCHS}({CHECK_EVERY} 간격), 겹 밖 소프트 교차엔트로피 평균 최소",
    }


def split_table(table: Mapping[str, dept.Distribution], valid_ids: list[str]) -> tuple[dict, dict]:
    """(학습 표, 검증용으로 뺀 표). 검증 조합과 same_combo인 표 행은 학습에서 뺀다."""
    held = {cid for cid in table if any(dept.same_combo(cid, v) for v in valid_ids)}
    return {c: d for c, d in table.items() if c not in held}, {c: table[c] for c in sorted(held)}


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


def train_round(tables_dir: Path, splits_dir: Path, model_dir: Path, reports_dir: Path, round_name: str) -> dict:
    """표에서 검증 조합을 빼고 학습해, 검증셋(안내 정답)과 뺀 표 행(HIRA 분포)으로 평가하고 저장한다."""
    table = dept.read_button_department(tables_dir)
    valid_ids, guide = dept.guide_set(tables_dir, splits_dir)
    train_table, held_table = split_table(table, valid_ids)
    hyper = select_hyperparams(train_table)
    _, X_train, T_train, w_train = training_rows(train_table)
    model = DeptB().fit(X_train, T_train, w_train, hyper["l2"], hyper["epochs"])

    results = {
        "guide": _evaluate_guide(model, valid_ids, guide),
        "held_out_table": _evaluate_table(model, held_table),
        "train_table": _evaluate_table(model, train_table),
        "unseen_examples": [_example(model, intake) for intake in UNSEEN_EXAMPLES],
    }
    text = model.to_text()
    _refuse_if_tested(model_dir, reports_dir, round_name, text)
    report = {
        "round": round_name,
        "model_version": f"dept_b/{round_name}",
        "seed": SEED,
        "architecture": {
            "inputs": len(INPUT_FEATURES),
            "hidden": HIDDEN,
            "activation": "relu",
            "outputs": len(DEPARTMENTS),
            "optimizer": f"전체 배치 Adam, 학습률 {LEARNING_RATE}",
        },
        "hyperparams": hyper,
        "data": {
            "button_department_sha256": _sha256_file(tables_dir / dept.BUTTON_DEPARTMENT),
            "dept_valid_sha256": _sha256_file(splits_dir / dept.VALID_IDS),
            "combos": {"table": len(table), "train": len(train_table), "held_out": len(held_table), "guide": len(valid_ids)},
            "train_rows_after_any_split": len(T_train),
        },
        "input_features": list(INPUT_FEATURES),
        "labels": list(DEPARTMENTS),
        "results": results,
    }
    model_dir.mkdir(parents=True, exist_ok=True)
    (model_dir / WEIGHTS_FILE).write_text(text)
    metadata = {k: report[k] for k in ("model_version", "seed", "architecture", "hyperparams", "data", "input_features", "labels")}
    metadata |= {
        "status": "임시(backlog 07). 형식 확정은 backlog 08",
        "files": {WEIGHTS_FILE: sha256_text(text)},
        "feature_names": list(FEATURE_NAMES),
    }
    (model_dir / METADATA_FILE).write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    _write_report(
        reports_dir,
        f"dept_b_{round_name}",
        report,
        {
            "MLP 진료과 검증셋(guide, 정답 = 안내 1순위)": results["guide"]["all"],
            "MLP 검증셋 중 외상·산재 조합": results["guide"]["trauma"],
            "MLP 검증셋 중 그 밖의 조합": results["guide"]["non_trauma"],
            "MLP 학습에서 뺀 표 행(정답 = 표 1순위)": results["held_out_table"]["vs_table_top1"],
        },
    )
    return report


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
