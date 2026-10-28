# 진료과 앙상블(backlog 08): 모델 A·B 분포의 가중 평균 + 저확신 폴백. 가중 평균·상위 2개·폴백 함수는 predict.py에 있고(서빙과 같은 함수),
# 여기서는 가중치와 폴백 기준값을 고르고 평가한다.
# - 조정 셋(사용자와 정함, 2026-10-28): 진료과 검증셋(05의 안내 조합 29건) + Kaggle 질환·증상 valid 44건 = 73건. 기준은 Top-2 적중 수.
#   같으면 가중치가 0.5에 가까운 쪽, 그다음 폴백 기준값이 높은 쪽 — 적중을 잃지 않는 한 확신이 낮은 입력은 가정의학과·내과로 보낸다
#   (설계 원칙 "확신도가 낮으면 폴백"). 낮은 쪽을 고르면 적중이 같은 0.0(폴백 없음)이 뽑혀 폴백이 사라진다.
# - 같은 행으로 고르고 재면 낙관적이라, 한 행씩 빼고 나머지 72건으로 고른 값으로 뺀 행을 재는 leave-one-out 수치를 함께 적는다.
# - 최종은 Kaggle test 59건 1회(정답 = 질환의 1순위 진료과). 진료과 모델에 다른 테스트셋은 없다.

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from fornav_modeling.data import split
from fornav_modeling.evaluate import ratio
from fornav_modeling.features.buttons import featurize_many
from fornav_modeling.labels import department as dept
from fornav_modeling.models import dept_a, dept_b
from fornav_modeling.predict import combine, top2
from fornav_modeling.schema import DEPARTMENTS

WEIGHT_GRID = tuple(round(0.1 * i, 1) for i in range(11))  # 모델 A 가중치. B는 1 - A
THRESHOLD_GRID = (0.0, *(round(0.05 * i, 2) for i in range(3, 13)))  # 0.0 = 폴백 없음, 0.15~0.60
FALLBACK = ("family", "internal")
INITIAL_WEIGHT = 0.5
ENSEMBLE_FILE = "ensemble.json"


def outcomes(p_a: np.ndarray, p_b: np.ndarray, y: np.ndarray, weight_a: float, threshold: float) -> dict[str, np.ndarray]:
    """행마다 Top-1·Top-2 적중과 폴백 여부. 폴백이면 상위 2개는 FALLBACK이다."""
    top1, top2_hit, fell = [], [], []
    for pa, pb, truth in zip(p_a, p_b, y, strict=True):
        top, fallback = top2(combine(pa, pb, weight_a), threshold, FALLBACK)
        top1.append(top[0] == DEPARTMENTS[truth])
        top2_hit.append(DEPARTMENTS[truth] in top)
        fell.append(fallback)
    return {"top1": np.array(top1), "top2": np.array(top2_hit), "fallback": np.array(fell)}


def select(p_a: np.ndarray, p_b: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    """가중치 × 폴백 기준값 격자에서 Top-2 적중 수 최대. 같으면 가중치가 0.5에 가까운 쪽, 그다음 기준값이 높은 쪽."""
    scored = [
        (int(outcomes(p_a, p_b, y, w, t)["top2"].sum()), -abs(w - INITIAL_WEIGHT), t, w, t) for w in WEIGHT_GRID for t in THRESHOLD_GRID
    ]
    best = max(scored)
    return best[3], best[4]


def leave_one_out(p_a: np.ndarray, p_b: np.ndarray, y: np.ndarray) -> dict[str, np.ndarray]:
    """행마다 그 행을 뺀 나머지로 고른 가중치·기준값으로 그 행을 잰다."""
    rows = {"top1": [], "top2": [], "fallback": []}
    for i in range(len(y)):
        keep = np.arange(len(y)) != i
        w, t = select(p_a[keep], p_b[keep], y[keep])
        one = outcomes(p_a[i : i + 1], p_b[i : i + 1], y[i : i + 1], w, t)
        for k in rows:
            rows[k].append(bool(one[k][0]))
    return {k: np.array(v) for k, v in rows.items()}


def summarize(result: dict[str, np.ndarray], mask: np.ndarray | None = None) -> dict:
    mask = np.ones(len(result["top2"]), dtype=bool) if mask is None else mask
    return {k: ratio(result[k][mask].sum(), mask.sum()) for k in ("top1", "top2", "fallback")}


# ---- 라운드 실행(scripts/tune_ensemble.py, scripts/evaluate.py --model ensemble) ----


def component_probas(models_dir: Path, rows: list[dict], component_round: str = "v0") -> tuple[np.ndarray, np.ndarray]:
    """입력 dict 목록 → (모델 A 분포, 모델 B 분포). 저장된 v0 모델을 읽는다."""
    a_dir, b_dir = models_dir / "dept_a" / component_round, models_dir / "dept_b" / component_round
    model_a = dept_a.DeptA.from_files({f: (a_dir / f).read_text() for f in (dept_a.MODEL_FILE, dept_a.DEPARTMENTS_FILE)})
    weights_b = json.loads((b_dir / dept_b.WEIGHTS_FILE).read_text())
    X = featurize_many(rows)
    return model_a.predict_proba(X), dept_b.predict_from_weights(weights_b, X)


def tuning_rows(processed_dir: Path, splits_dir: Path, tables_dir: Path) -> tuple[list[dict], np.ndarray, np.ndarray, np.ndarray]:
    """(입력 dict, 정답 진료과 번호, 출처 — guide/kaggle, 외상·산재 여부). 안내 조합 29건 + Kaggle valid 44건."""
    ids, guide = dept.guide_set(tables_dir, splits_dir)
    valid = split.load_symptom_dev(processed_dir, splits_dir, "valid")
    rows = [dept.combo_intake(cid) for cid in ids] + valid.to_dict("records")
    y = np.concatenate(
        [
            [DEPARTMENTS.index(guide[cid].department) for cid in ids],
            dept_a.true_departments(valid["disease"], dept.read_disease_department(tables_dir)),
        ]
    ).astype(np.int64)
    source = np.array(["guide"] * len(ids) + ["kaggle"] * len(valid))
    trauma = np.array([dept.is_trauma(cid) for cid in ids] + [False] * len(valid))
    return rows, y, source, trauma


def tune_round(processed_dir: Path, splits_dir: Path, tables_dir: Path, models_dir: Path, reports_dir: Path, round_name: str) -> dict:
    rows, y, source, trauma = tuning_rows(processed_dir, splits_dir, tables_dir)
    p_a, p_b = component_probas(models_dir, rows)
    weight_a, threshold = select(p_a, p_b, y)
    masks = {"all": None, "guide": source == "guide", "kaggle_valid": source == "kaggle", "guide_trauma": trauma}
    candidates = {
        "A 단독": (1.0, 0.0),
        "B 단독": (0.0, 0.0),
        "0.5 : 0.5, 폴백 없음": (0.5, 0.0),
        f"선택(A {weight_a}, 폴백 기준 {threshold})": (weight_a, threshold),
    }
    results = {name: {m: summarize(outcomes(p_a, p_b, y, w, t), mask) for m, mask in masks.items()} for name, (w, t) in candidates.items()}
    loo = leave_one_out(p_a, p_b, y)
    grid = {f"{w}": {f"{t}": int(outcomes(p_a, p_b, y, w, t)["top2"].sum()) for t in THRESHOLD_GRID} for w in WEIGHT_GRID}
    params = {
        "weight_a": weight_a,
        "weight_b": round(1 - weight_a, 1),
        "fallback_threshold": threshold,
        "fallback": list(FALLBACK),
        "components": {"dept_a": "dept_a/v0", "dept_b": "dept_b/v0"},
    }
    text = json.dumps(params, ensure_ascii=False, indent=1) + "\n"
    _refuse_if_tested(models_dir / "ensemble" / round_name, reports_dir, round_name, text)
    report = {
        "round": round_name,
        "params": params,
        "rule": "조정 셋(안내 조합 29 + Kaggle valid 44) Top-2 적중 수 최대. 같으면 A 가중치가 0.5에 가까운 쪽, 그다음 폴백 기준값이 높은 쪽(적중을 잃지 않는 한 폴백)",
        "grid": {"weights": list(WEIGHT_GRID), "thresholds": list(THRESHOLD_GRID), "top2_hits_all": grid},
        "rows": {
            "all": len(y),
            "guide": int((source == "guide").sum()),
            "kaggle_valid": int((source == "kaggle").sum()),
            "guide_trauma": int(trauma.sum()),
        },
        "results": results,
        "leave_one_out": {m: summarize(loo, mask) for m, mask in masks.items()},
        "guide_reviewed_no": "안내 조합 29건은 모두 reviewed=no",
    }
    model_dir = models_dir / "ensemble" / round_name
    model_dir.mkdir(parents=True, exist_ok=True)
    (model_dir / ENSEMBLE_FILE).write_text(text)
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / f"ensemble_{round_name}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    (reports_dir / f"ensemble_{round_name}.md").write_text(
        _markdown(f"ensemble_{round_name}", {**results, "leave-one-out(선택 규칙)": report["leave_one_out"]})
    )
    return report


def evaluate_test_round(test: pd.DataFrame, models_dir: Path, tables_dir: Path, reports_dir: Path, round_name: str) -> dict:
    """선택한 가중치·기준값으로 Kaggle test를 한 번 평가해 '최종'으로 기록한다. A·B 단독도 같은 행으로 함께 적는다."""
    name = f"ensemble_{round_name}_test"
    if (reports_dir / f"{name}.json").exists():
        raise FileExistsError(f"{name}.json이 이미 있다. test 평가는 라운드마다 한 번만 한다. 조정했다면 새 라운드로 기록한다")
    text = (models_dir / "ensemble" / round_name / ENSEMBLE_FILE).read_text()
    params = json.loads(text)
    p_a, p_b = component_probas(models_dir, test.to_dict("records"))
    y = dept_a.true_departments(test["disease"], dept.read_disease_department(tables_dir))
    results = {
        f"앙상블(A {params['weight_a']}, 폴백 기준 {params['fallback_threshold']}) — 최종": summarize(
            outcomes(p_a, p_b, y, params["weight_a"], params["fallback_threshold"])
        ),
        "A 단독": summarize(outcomes(p_a, p_b, y, 1.0, 0.0)),
        "B 단독": summarize(outcomes(p_a, p_b, y, 0.0, 0.0)),
    }
    report = {
        "round": round_name,
        "final": True,
        "note": "test 평가는 이 라운드에서 한 번만 했다",
        "rows": len(test),
        "ensemble_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "results": {k: {"all": v} for k, v in results.items()},
    }
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / f"{name}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    (reports_dir / f"{name}.md").write_text(_markdown(name, report["results"]))
    return report


def _refuse_if_tested(model_dir: Path, reports_dir: Path, round_name: str, text: str) -> None:
    if not (reports_dir / f"ensemble_{round_name}_test.json").exists():
        return
    path = model_dir / ENSEMBLE_FILE
    if not path.exists() or path.read_text() != text:
        raise FileExistsError(f"{round_name}는 이미 test로 평가했는데 가중치·기준값이 달라졌다. 새 라운드 이름으로 조정한다")


def _markdown(title: str, results: dict[str, dict]) -> str:
    sets = list(next(iter(results.values())))
    lines = [f"# {title}", "", "Top-1 / Top-2 / 폴백 발동(분자/분모). 폴백이면 상위 2개는 가정의학과·내과", ""]
    lines += ["| 규칙 | " + " | ".join(f"{s} Top-1 | {s} Top-2 | {s} 폴백" for s in sets) + " |", "|" + "---|" * (1 + 3 * len(sets))]
    for name, by_set in results.items():
        cells = [f"{r[k]['n']}/{r[k]['of']}" for s in sets for r in [by_set[s]] for k in ("top1", "top2", "fallback")]
        lines.append("| " + " | ".join([name, *cells]) + " |")
    return "\n".join(lines) + "\n"
