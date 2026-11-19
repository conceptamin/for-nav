# 진료과 앙상블(backlog 08, 16): 모델 A·B 분포의 가중 평균 + 저확신 폴백. 가중 평균·상위 2개·폴백 함수는 predict.py에 있고(서빙과 같은 함수),
# 여기서는 가중치와 폴백 기준값을 고르고 평가한다.
# - 조정 셋(backlog 16): 진료과 검증셋(05의 안내 조합 29건) + 질환·증상 valid(Kaggle·DDXPlus). 18의 최종 평가용 조합은 넣지 않는다.
# - 고르는 기준: 출처(안내 조합, Kaggle valid, DDXPlus valid)마다 Top-2 적중률을 같은 비중으로 더한 값이 최대.
#   08은 적중 수를 그대로 더했지만(29 + 44건), 지금 valid는 DDXPlus가 375건이라 그대로 더하면 앱 입력에 가까운 안내 조합이 묻힌다.
#   출처 균형은 모델 A 학습 가중치와 같은 결정이다(사용자 결정 2026-11-19). 정수로 비교해 동점 처리가 흔들리지 않게 한다.
#   같으면 가중치가 0.5에 가까운 쪽, 그다음 폴백 기준값이 높은 쪽 — 적중을 잃지 않는 한 확신이 낮은 입력은 가정의학과·내과로 보낸다.
# - 같은 행으로 고르고 재면 낙관적이라, 한 행씩 빼고 나머지로 고른 값으로 뺀 행을 재는 leave-one-out 수치를 함께 적는다.
# - 최종은 질환·증상 test(출처별·버튼 수별)와 18의 최종 평가용 안내 조합을 한 번 평가한다. 최종 평가용 정답은 평가 명령이 읽어 넘긴다.
# - 버튼 수별 규칙(backlog 19, v6): 버튼(부위 + 증상) 2개 이하 / 3~4개 / 5개 이상마다 가중치·기준값을 따로 고른다. 앱 입력에 가까운
#   2개 이하에서는 모델 B가, 질환·증상 데이터처럼 버튼이 많으면 모델 A가 낫기 때문이다. 묶음마다 출처 균형 (Top-1 + Top-2) 적중 최대
#   (앱이 1순위를 먼저 보여 줘 Top-1도 센다. v5 조정 셋 2개 이하 묶음에서 Top-2가 가중치에 거의 무관하고 Top-1이 크게 갈리는 것을 본 뒤 정했다).

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
from fornav_modeling.predict import Rule, button_count, combine, ensemble_rules
from fornav_modeling.schema import DEPARTMENTS

WEIGHT_GRID = tuple(round(0.1 * i, 1) for i in range(11))  # 모델 A 가중치. B는 1 - A
THRESHOLD_GRID = (0.0, *(round(0.05 * i, 2) for i in range(3, 13)))  # 0.0 = 폴백 없음, 0.15~0.60
FALLBACK = ("family", "internal")
_FALLBACK_INDEX = [DEPARTMENTS.index(d) for d in FALLBACK]
INITIAL_WEIGHT = 0.5
ENSEMBLE_FILE = "ensemble.json"
COMPONENTS = {"dept_a": "v3", "dept_b": "v5"}  # 조정에 쓰는 학습 라운드. dept_b/v5는 backlog 19에서 병원 안내 조합을 더해 학습한 모델 B
TUNING_SOURCES = ("guide", *split.SOURCES)
BUTTON_RULE_BUCKETS = (2, 4, None)  # 버튼 수별 규칙의 max_buttons


def outcomes(p_a: np.ndarray, p_b: np.ndarray, y: np.ndarray, weight_a: float, threshold: float) -> dict[str, np.ndarray]:
    """행마다 Top-1·Top-2 적중과 폴백 여부. predict.top2와 같은 규칙(동점이면 DEPARTMENTS 순서, 폴백이면 상위 2개는 FALLBACK)."""
    proba = combine(p_a, p_b, weight_a)
    top = np.argsort(-proba, axis=1, kind="stable")[:, :2]
    fell = proba.max(axis=1) < threshold
    top[fell] = _FALLBACK_INDEX
    y = np.asarray(y)
    return {"top1": top[:, 0] == y, "top2": (top == y[:, None]).any(axis=1), "fallback": fell}


def grid_hits(p_a: np.ndarray, p_b: np.ndarray, y: np.ndarray) -> np.ndarray:
    """(가중치 수, 기준값 수, 행 수) Top-2 적중."""
    return np.array([[outcomes(p_a, p_b, y, w, t)["top2"] for t in THRESHOLD_GRID] for w in WEIGHT_GRID])


def balanced_scores(hits: np.ndarray, source: np.ndarray, keep: np.ndarray | None = None) -> np.ndarray:
    """격자 칸마다 출처별 Top-2 적중률의 합(같은 비중)을 정수로: Σ_s 적중_s × Π_{s'≠s} 행 수_s'. keep이 False인 행은 뺀다."""
    keep = np.ones(hits.shape[-1], dtype=bool) if keep is None else keep
    parts = [(hits[..., keep & (source == s)].sum(axis=-1).astype(object), int((keep & (source == s)).sum())) for s in np.unique(source)]
    parts = [(h, n) for h, n in parts if n]
    total = 0
    for i, (h, _) in enumerate(parts):
        others = 1
        for j, (_, n) in enumerate(parts):
            if j != i:
                others *= n
        total = total + h * others
    return total


def pick(scores: np.ndarray) -> tuple[float, float]:
    """점수 최대. 같으면 가중치가 0.5에 가까운 쪽, 그다음 기준값이 높은 쪽."""
    best = max((scores[i, j], -abs(w - INITIAL_WEIGHT), t, w) for i, w in enumerate(WEIGHT_GRID) for j, t in enumerate(THRESHOLD_GRID))
    return best[3], best[2]


def select(p_a: np.ndarray, p_b: np.ndarray, y: np.ndarray, source: np.ndarray) -> tuple[float, float]:
    return pick(balanced_scores(grid_hits(p_a, p_b, y), source))


def leave_one_out(p_a: np.ndarray, p_b: np.ndarray, y: np.ndarray, source: np.ndarray) -> dict[str, np.ndarray]:
    """행마다 그 행을 뺀 나머지로 고른 가중치·기준값으로 그 행을 잰다."""
    hits = grid_hits(p_a, p_b, y)
    rows = {"top1": [], "top2": [], "fallback": []}
    for i in range(len(y)):
        keep = np.arange(len(y)) != i
        w, t = pick(balanced_scores(hits, source, keep))
        one = outcomes(p_a[i : i + 1], p_b[i : i + 1], y[i : i + 1], w, t)
        for k in rows:
            rows[k].append(bool(one[k][0]))
    return {k: np.array(v) for k, v in rows.items()}


def rule_outcomes(p_a: np.ndarray, p_b: np.ndarray, y: np.ndarray, n_buttons: np.ndarray, rules: list[Rule]) -> dict[str, np.ndarray]:
    """행마다 버튼 수에 맞는 규칙(predict.ensemble_rule)으로 잰 Top-1·Top-2·폴백."""
    out = {k: np.zeros(len(y), dtype=bool) for k in ("top1", "top2", "fallback")}
    chosen = np.array([rules.index(next(r for r in rules if r[0] is None or n <= r[0])) for n in n_buttons])
    for i, (_, w, t) in enumerate(rules):
        m = chosen == i
        if m.any():
            for k, v in outcomes(p_a[m], p_b[m], y[m], w, t).items():
                out[k][m] = v
    return out


def select_by_buttons(p_a: np.ndarray, p_b: np.ndarray, y: np.ndarray, source: np.ndarray, n_buttons: np.ndarray) -> list[Rule]:
    """버튼 수 묶음마다 출처 균형 (Top-1 + Top-2) 적중이 최대인 (가중치, 기준값). 동점 규칙은 pick과 같다."""
    rules, low = [], 0
    for max_buttons in BUTTON_RULE_BUCKETS:
        m = (n_buttons >= low) & (n_buttons <= (max_buttons if max_buttons is not None else 10**6))
        w, t = pick(balanced_scores(_top12_hits(p_a[m], p_b[m], y[m]), source[m])) if m.any() else (INITIAL_WEIGHT, 0.0)
        rules.append((max_buttons, w, t))
        low = (max_buttons or 0) + 1
    return rules


def _top12_hits(p_a: np.ndarray, p_b: np.ndarray, y: np.ndarray) -> np.ndarray:
    """(가중치 수, 기준값 수, 행 수) Top-1 적중 + Top-2 적중(0~2)."""
    return np.array(
        [
            [(lambda o: o["top1"].astype(int) + o["top2"].astype(int))(outcomes(p_a, p_b, y, w, t)) for t in THRESHOLD_GRID]
            for w in WEIGHT_GRID
        ]
    )


def leave_one_out_by_buttons(p_a: np.ndarray, p_b: np.ndarray, y: np.ndarray, source: np.ndarray, n_buttons: np.ndarray) -> dict:
    """행마다 그 행을 뺀 나머지로 그 행의 버튼 수 묶음 규칙을 다시 골라 그 행을 잰다."""
    rows = {"top1": [], "top2": [], "fallback": []}
    bucket = [next(b for b in BUTTON_RULE_BUCKETS if b is None or n <= b) for n in n_buttons]
    hits = {}
    for b in BUTTON_RULE_BUCKETS:
        m = np.array([x == b for x in bucket])
        hits[b] = (m, _top12_hits(p_a[m], p_b[m], y[m]) if m.any() else None)
    for i in range(len(y)):
        m, h = hits[bucket[i]]
        idx = np.flatnonzero(m)
        keep = idx != i
        w, t = pick(balanced_scores(h, source[m], keep))
        one = outcomes(p_a[i : i + 1], p_b[i : i + 1], y[i : i + 1], w, t)
        for k in rows:
            rows[k].append(bool(one[k][0]))
    return {k: np.array(v) for k, v in rows.items()}


def summarize(result: dict[str, np.ndarray], mask: np.ndarray | None = None) -> dict:
    mask = np.ones(len(result["top2"]), dtype=bool) if mask is None else mask
    return {k: ratio(result[k][mask].sum(), mask.sum()) for k in ("top1", "top2", "fallback")}


# ---- 라운드 실행(scripts/tune_ensemble.py, scripts/evaluate.py --model ensemble) ----


def component_probas(models_dir: Path, rows: list[dict], components: dict[str, str] = COMPONENTS) -> tuple[np.ndarray, np.ndarray]:
    """입력 dict 목록 → (모델 A 분포, 모델 B 분포). 저장된 학습 라운드 모델을 읽는다."""
    a_dir, b_dir = models_dir / "dept_a" / components["dept_a"], models_dir / "dept_b" / components["dept_b"]
    model_a = dept_a.DeptA.from_files({f: (a_dir / f).read_text() for f in (dept_a.MODEL_FILE, dept_a.DEPARTMENTS_FILE)})
    weights_b = json.loads((b_dir / dept_b.WEIGHTS_FILE).read_text())
    X = featurize_many(rows)
    return model_a.predict_proba(X), dept_b.predict_from_weights(weights_b, X)


def tuning_rows(processed_dir: Path, splits_dir: Path, tables_dir: Path) -> tuple[list[dict], np.ndarray, np.ndarray, dict]:
    """(입력 dict, 정답 진료과 번호, 출처 — guide/kaggle/ddxplus, 행 묶음 마스크). 안내 조합 29건 + 질환·증상 valid."""
    ids, guide = dept.guide_set(tables_dir, splits_dir)
    valid = split.load_symptom_dev(processed_dir, splits_dir, "valid")
    rows = [dept.combo_intake(cid) for cid in ids] + valid.to_dict("records")
    y = np.concatenate(
        [
            [DEPARTMENTS.index(guide[cid].department) for cid in ids],
            dept_a.true_departments(valid["disease"], dept.read_disease_department(tables_dir)),
        ]
    ).astype(np.int64)
    source = np.concatenate([np.array(["guide"] * len(ids)), valid["source"].to_numpy()])
    pad = np.zeros(len(ids), dtype=bool)
    masks = {"all": np.ones(len(y), dtype=bool)}
    masks |= {f"{s}{'' if s == 'guide' else '_valid'}": source == s for s in TUNING_SOURCES}
    masks["guide_reviewed_yes"] = np.concatenate([[guide[cid].reviewed for cid in ids], np.zeros(len(valid), dtype=bool)])
    masks["guide_trauma"] = np.concatenate([[dept.is_trauma(cid) for cid in ids], np.zeros(len(valid), dtype=bool)])
    valid_masks = dept_a.row_masks(valid)
    masks |= {f"valid_{k}": np.concatenate([pad, m]) for k, m in valid_masks.items() if k.startswith("버튼")}
    return rows, y, source, masks


def tune_round(
    processed_dir: Path, splits_dir: Path, tables_dir: Path, models_dir: Path, reports_dir: Path, round_name: str, by_buttons: bool = False
) -> dict:
    rows, y, source, masks = tuning_rows(processed_dir, splits_dir, tables_dir)
    p_a, p_b = component_probas(models_dir, rows)
    n_buttons = np.array([button_count(r) for r in rows])
    hits = grid_hits(p_a, p_b, y)
    weight_a, threshold = pick(balanced_scores(hits, source))
    candidates = {
        "A 단독": [(None, 1.0, 0.0)],
        "B 단독": [(None, 0.0, 0.0)],
        "0.5 : 0.5, 폴백 없음": [(None, 0.5, 0.0)],
        f"가중치 하나(A {weight_a}, 폴백 기준 {threshold})": [(None, weight_a, threshold)],
    }
    if by_buttons:
        rules = select_by_buttons(p_a, p_b, y, source, n_buttons)
        candidates["선택(버튼 수별 " + ", ".join(f"≤{b or '∞'}: A {w}·{t}" for b, w, t in rules) + ")"] = rules
        loo = leave_one_out_by_buttons(p_a, p_b, y, source, n_buttons)
    else:
        candidates[f"선택(A {weight_a}, 폴백 기준 {threshold})"] = candidates.pop(f"가중치 하나(A {weight_a}, 폴백 기준 {threshold})")
        loo = leave_one_out(p_a, p_b, y, source)
    results = {
        name: {m: summarize(rule_outcomes(p_a, p_b, y, n_buttons, r), mask) for m, mask in masks.items()} for name, r in candidates.items()
    }
    counts = {s: int((source == s).sum()) for s in TUNING_SOURCES}
    grid = {
        f"{w}": {f"{t}": {s: int(hits[i, j][source == s].sum()) for s in TUNING_SOURCES} for j, t in enumerate(THRESHOLD_GRID)}
        for i, w in enumerate(WEIGHT_GRID)
    }
    if by_buttons:
        params = {
            "by_buttons": [{"max_buttons": b, "weight_a": w, "weight_b": round(1 - w, 1), "fallback_threshold": t} for b, w, t in rules],
            "button_count": "부위 + 증상 버튼 수",
        }
    else:
        params = {"weight_a": weight_a, "weight_b": round(1 - weight_a, 1), "fallback_threshold": threshold}
    params |= {"fallback": list(FALLBACK), "components": {name: f"{name}/{r}" for name, r in COMPONENTS.items()}}
    text = json.dumps(params, ensure_ascii=False, indent=1) + "\n"
    _refuse_if_tested(models_dir / "ensemble" / round_name, reports_dir, round_name, text)
    _, guide = dept.guide_set(tables_dir, splits_dir)
    report = {
        "round": round_name,
        "params": params,
        "rule": (
            f"조정 셋(안내 조합 {counts['guide']} + Kaggle valid {counts['kaggle']} + DDXPlus valid {counts['ddxplus']}). "
            + (
                f"버튼 수 묶음(≤{', ≤'.join(str(b) for b in BUTTON_RULE_BUCKETS[:-1])}, 나머지)마다 출처 균형 (Top-1 + Top-2) 적중 최대. "
                if by_buttons
                else "출처마다 Top-2 적중률을 같은 비중으로 더한 값 최대. "
            )
            + "같으면 A 가중치가 0.5에 가까운 쪽, 그다음 폴백 기준값이 높은 쪽"
        ),
        "grid": {"weights": list(WEIGHT_GRID), "thresholds": list(THRESHOLD_GRID), "top2_hits_by_source": grid, "rows_by_source": counts},
        "rows": {m: int(mask.sum()) for m, mask in masks.items()},
        "results": results,
        "leave_one_out": {m: summarize(loo, mask) for m, mask in masks.items()},
        "guide_reviewed": {"yes": sum(a.reviewed for a in guide.values()), "of": len(guide)},
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


def evaluate_test_round(
    test: pd.DataFrame,
    models_dir: Path,
    tables_dir: Path,
    reports_dir: Path,
    round_name: str,
    final_guide: tuple[list[str], dict[str, dept.GuideAnswer]] | None = None,
) -> dict:
    """선택한 가중치·기준값으로 test(출처별·버튼 수별)와 최종 평가용 안내 조합을 한 번 평가해 '최종'으로 기록한다.
    A·B 단독도 같은 행으로 함께 적는다. final_guide는 평가 명령(scripts/evaluate.py)이 고정 해시를 확인하고 읽어 넘긴다."""
    name = f"ensemble_{round_name}_test"
    if (reports_dir / f"{name}.json").exists():
        raise FileExistsError(f"{name}.json이 이미 있다. test 평가는 라운드마다 한 번만 한다. 조정했다면 새 라운드로 기록한다")
    text = (models_dir / "ensemble" / round_name / ENSEMBLE_FILE).read_text()
    params = json.loads(text)
    components = {k: v.split("/")[1] for k, v in params["components"].items()}
    rows = test.to_dict("records")
    y = dept_a.true_departments(test["disease"], dept.read_disease_department(tables_dir))
    masks = {f"test_{k}": m for k, m in dept_a.row_masks(test).items()}
    if final_guide is not None:
        ids, answers = final_guide
        rows += [dept.combo_intake(cid) for cid in ids]
        y = np.concatenate([y, [DEPARTMENTS.index(answers[cid].department) for cid in ids]]).astype(np.int64)
        masks = {k: np.concatenate([m, np.zeros(len(ids), dtype=bool)]) for k, m in masks.items()}
        guide_mask = np.concatenate([np.zeros(len(test), dtype=bool), np.ones(len(ids), dtype=bool)])
        trauma = np.concatenate([np.zeros(len(test), dtype=bool), [dept.is_trauma(cid) for cid in ids]])
        masks |= {"final_guide": guide_mask, "final_guide_trauma": trauma}
    p_a, p_b = component_probas(models_dir, rows, components)
    n_buttons = np.array([button_count(r) for r in rows])
    chosen = ensemble_rules(params)
    label = (
        f"앙상블(A {params['weight_a']}, 폴백 기준 {params['fallback_threshold']}) — 최종"
        if "by_buttons" not in params
        else "앙상블(버튼 수별 " + ", ".join(f"≤{b or '∞'}: A {w}·{t}" for b, w, t in chosen) + ") — 최종"
    )
    rules = {label: chosen, "A 단독": [(None, 1.0, 0.0)], "B 단독": [(None, 0.0, 0.0)]}
    results = {
        rule: {m: summarize(rule_outcomes(p_a, p_b, y, n_buttons, r), mask) for m, mask in masks.items() if mask.any()}
        for rule, r in rules.items()
    }
    report = {
        "round": round_name,
        "final": True,
        "note": "test 평가는 이 라운드에서 한 번만 했다",
        "rows": {m: int(mask.sum()) for m, mask in masks.items()},
        "ensemble_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "components": params["components"],
        "results": results,
    }
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / f"{name}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    (reports_dir / f"{name}.md").write_text(_markdown(name, report["results"]))
    return report


def compare_b_settings(
    processed_dir: Path, splits_dir: Path, tables_dir: Path, models_dir: Path, reports_dir: Path, names: list[str]
) -> dict:
    """모델 B 설정 후보마다 B를 학습해 조정 셋에서 앙상블 가중치·폴백 기준값을 고르고, 출처별 Top-1·Top-2와 leave-one-out을 잰다(backlog 19).
    고르는 기준은 leave-one-out 출처 균형 Top-2(정수 비교). 같으면 후보 목록 앞쪽(단순한 설정)."""
    rows, y, source, masks = tuning_rows(processed_dir, splits_dir, tables_dir)
    a_dir = models_dir / "dept_a" / COMPONENTS["dept_a"]
    model_a = dept_a.DeptA.from_files({f: (a_dir / f).read_text() for f in (dept_a.MODEL_FILE, dept_a.DEPARTMENTS_FILE)})
    X = featurize_many(rows)
    p_a = model_a.predict_proba(X)
    valid_ids, _ = dept.guide_set(tables_dir, splits_dir)
    train_table, _ = dept_b.split_table(dept.read_button_department(tables_dir), valid_ids, dept.held_test_ids(splits_dir))
    guide = dept.guide_train_table(tables_dir, splits_dir)
    shown = {k: masks[k] for k in ("guide", "kaggle_valid", "ddxplus_valid", "guide_trauma")}
    out = {}
    for name in names:
        setting = dept_b.CANDIDATES[name]
        model, hyper = dept_b.fit_setting(train_table, setting, guide if setting.guide else None)
        p_b = model.predict_proba(X)
        weight_a, threshold = select(p_a, p_b, y, source)
        loo = leave_one_out(p_a, p_b, y, source)
        out[name] = {
            "hyperparams": {k: hyper[k] for k in ("hidden", "l2", "epochs", "train_rows")},
            "weight_a": weight_a,
            "fallback_threshold": threshold,
            "b_alone": {m: summarize(outcomes(p_a, p_b, y, 0.0, 0.0), mask) for m, mask in shown.items()},
            "selected": {m: summarize(outcomes(p_a, p_b, y, weight_a, threshold), mask) for m, mask in shown.items()},
            "leave_one_out": {m: summarize(loo, mask) for m, mask in shown.items()},
            "loo_balanced_top2": float(balanced_scores(loo["top2"][None, None, :], source)[0, 0]),
        }
    chosen = max(names, key=lambda n: (out[n]["loo_balanced_top2"], -names.index(n)))
    report = {"candidates": out, "chosen": chosen, "guide_train_keys": len(guide), "rule": compare_b_settings.__doc__}
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "dept_b_compare.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    lines = ["# dept_b_compare", "", "칸: Top-1 · Top-2(분자/분모). 앙상블은 후보마다 조정 셋에서 고른 가중치·기준값", ""]
    lines += ["| 후보 | 가중치 A·기준 | " + " | ".join(f"{m} B 단독 | {m} 앙상블 | {m} LOO" for m in shown) + " |"]
    lines += ["|" + "---|" * (2 + 3 * len(shown))]
    for name, r in out.items():
        cells = []
        for m in shown:
            cells += [
                " · ".join(f"{r[k][m][x]['n']}/{r[k][m][x]['of']}" for x in ("top1", "top2"))
                for k in ("b_alone", "selected", "leave_one_out")
            ]
        lines.append(
            f"| {name}{' (선택)' if name == chosen else ''} | {r['weight_a']}·{r['fallback_threshold']} | " + " | ".join(cells) + " |"
        )
    (reports_dir / "dept_b_compare.md").write_text("\n".join(lines) + "\n")
    return report


def _refuse_if_tested(model_dir: Path, reports_dir: Path, round_name: str, text: str) -> None:
    if not (reports_dir / f"ensemble_{round_name}_test.json").exists():
        return
    path = model_dir / ENSEMBLE_FILE
    if not path.exists() or path.read_text() != text:
        raise FileExistsError(f"{round_name}는 이미 test로 평가했는데 가중치·기준값이 달라졌다. 새 라운드 이름으로 조정한다")


def _markdown(title: str, results: dict[str, dict]) -> str:
    """행 = 평가셋, 열 = 규칙. 칸은 Top-1 · Top-2 · 폴백(분자/분모)."""
    rules = list(results)
    sets = list(dict.fromkeys(s for by_set in results.values() for s in by_set))
    lines = [f"# {title}", "", "칸: Top-1 · Top-2 · 폴백 발동(분자/분모). 폴백이면 상위 2개는 가정의학과·내과", ""]
    lines += ["| 평가셋 | " + " | ".join(rules) + " |", "|" + "---|" * (1 + len(rules))]
    for s in sets:
        cells = []
        for rule in rules:
            r = results[rule].get(s)
            cells.append("-" if r is None else " · ".join(f"{r[k]['n']}/{r[k]['of']}" for k in ("top1", "top2", "fallback")))
        lines.append("| " + " | ".join([s, *cells]) + " |")
    return "\n".join(lines) + "\n"
