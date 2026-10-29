# 발표용 비교 실험(backlog 09): 버튼 피처만 쓴 응급도 모델 vs 버튼 + 활력징후 모델.
# 같은 train·valid 분할, 같은 LightGBM 설정·seed(models/acuity.py)로 학습하고 검증셋으로만 비교한다. test는 읽지 않는다.
# 버튼 전용 쪽은 응급도 v0 LightGBM과 같은 학습이다(같은 피처·설정·라운드 수 규칙). 결측은 v0처럼 NaN 그대로 LightGBM에 넘긴다.
# 서빙과 무관하다 — 모델을 내보내지 않고, predict.py는 이 모듈과 features/vitals.py를 import하지 않는다.

import json
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

from fornav_modeling.data import split
from fornav_modeling.data.download import sha256_file
from fornav_modeling.evaluate import classification_metrics, metrics_table
from fornav_modeling.features.buttons import FEATURE_NAMES, featurize_many
from fornav_modeling.features.vitals import VITAL_FEATURES, vitals_features
from fornav_modeling.labels.ktas import ACUITIES
from fornav_modeling.models import acuity

SETUPS: dict[str, tuple[str, ...]] = {"buttons": FEATURE_NAMES, "buttons_vitals": (*FEATURE_NAMES, *VITAL_FEATURES)}
LABELS = {"buttons": "Buttons only", "buttons_vitals": "Buttons + vitals"}  # 그림 글자(한글 글꼴에 기대지 않는다)
COLORS = {"buttons": "#2a78d6", "buttons_vitals": "#eb6834"}  # 범주 색 1·2번(dataviz 기본 팔레트)
SHAP_TOP_N = 8
REPORT_NAME = "experiment_vitals"


class BoosterModel:
    """acuity.out_of_fold_proba가 부르는 predict_proba만 있는 얇은 감싸개."""

    def __init__(self, booster: lgb.Booster):
        self.booster = booster

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return self.booster.predict(X)


def feature_matrix(rows: pd.DataFrame, setup: str) -> np.ndarray:
    """표준 테이블 행 → SETUPS[setup] 순서의 피처 행렬. 버튼 피처는 서빙과 같은 featurize, 활력징후는 뒤에 붙인다."""
    records = rows.to_dict("records")
    X = featurize_many(records)
    if setup == "buttons_vitals":
        X = np.hstack([X, np.array([vitals_features(r) for r in records], dtype=np.float64).reshape(len(records), len(VITAL_FEATURES))])
    return X


def train_lightgbm(X: np.ndarray, y: np.ndarray, feature_names: tuple[str, ...], num_rounds: int | None = None) -> lgb.Booster:
    """acuity.LGBM_PARAMS로 학습. num_rounds가 없으면 acuity와 같은 규칙(층화 5겹 교차검증 조기 종료)으로 정한다."""

    def dataset():
        return lgb.Dataset(X, label=y, feature_name=list(feature_names), free_raw_data=False)

    if num_rounds is None:
        cv = lgb.cv(
            acuity.LGBM_PARAMS,
            dataset(),
            num_boost_round=acuity.MAX_ROUNDS,
            folds=acuity.grouped_folds(y),
            callbacks=[lgb.early_stopping(acuity.EARLY_STOPPING_ROUNDS, verbose=False)],
        )
        num_rounds = len(cv["valid multi_logloss-mean"])
    return lgb.train(acuity.LGBM_PARAMS, dataset(), num_boost_round=num_rounds)


def shap_values(booster: lgb.Booster, X: np.ndarray) -> np.ndarray:
    """(행 수, 클래스 수, 피처 수) TreeSHAP 값(explain.shap_values와 같은 계산, 피처 수만 모델에서 읽는다)."""
    raw = booster.predict(X, pred_contrib=True)
    return raw.reshape(len(X), booster.num_model_per_iteration(), booster.num_feature() + 1)[:, :, :-1]


def shap_summary(booster: lgb.Booster, X: np.ndarray, feature_names: tuple[str, ...]) -> dict:
    """클래스별 평균 |SHAP| 상위 피처와, 전체 |SHAP| 중 활력징후 피처가 차지하는 몫."""
    mean_abs = np.abs(shap_values(booster, X)).mean(axis=0)  # (클래스 수, 피처 수)
    vital = np.array([name in VITAL_FEATURES for name in feature_names])
    summary = {}
    for k, label in enumerate(ACUITIES):
        order = sorted(range(len(feature_names)), key=lambda i: (-mean_abs[k, i], i))
        summary[label] = {
            "top": [{"feature": feature_names[i], "mean_abs_shap": round(float(mean_abs[k, i]), 4)} for i in order[:SHAP_TOP_N]],
            "vitals_share": round(float(mean_abs[k, vital].sum() / mean_abs[k].sum()), 4) if mean_abs[k].sum() else None,
        }
    return summary


def missing_counts(rows: pd.DataFrame) -> dict:
    """활력징후 열마다 [결측 행 수, 전체 행 수]. 원본 "측불"(측정 불가)과 빈칸이 결측이다."""
    return {name: [int(rows[name].isna().sum()), len(rows)] for name in VITAL_FEATURES}


def run(processed_dir: Path, splits_dir: Path, reports_dir: Path) -> dict:
    """두 설정을 학습하고 valid로 비교해 reports/experiment_vitals.{json,md}와 그림을 쓴다."""
    train, valid = (split.load_dev(processed_dir, splits_dir, name) for name in split.DEV_SPLITS)
    y_train, y_valid = acuity.encode_labels(train["acuity"]), acuity.encode_labels(valid["acuity"])
    y_dev = np.concatenate([y_train, y_valid])

    results = {}
    for setup, names in SETUPS.items():
        X_train, X_valid = feature_matrix(train, setup), feature_matrix(valid, setup)
        booster = train_lightgbm(X_train, y_train, names)
        num_rounds = booster.current_iteration()
        proba = booster.predict(X_valid)
        threshold = acuity.select_threshold(y_valid, proba[:, acuity.EMERGENCY])
        oof = acuity.out_of_fold_proba(
            lambda X, y, names=names, n=num_rounds: BoosterModel(train_lightgbm(X, y, names, n)), np.vstack([X_train, X_valid]), y_dev
        )["full"]
        results[setup] = {
            "feature_names": list(names),
            "num_rounds": num_rounds,
            "model_sha256": acuity.sha256_text(booster.model_to_string()),
            "threshold": threshold,
            "valid": {
                "argmax": classification_metrics(y_valid, acuity.decide(proba, None)),
                "threshold": classification_metrics(y_valid, acuity.decide(proba, threshold["threshold"])),
            },
            "cv_train_valid": {
                "argmax": classification_metrics(y_dev, acuity.decide(oof, None)),
                "threshold": classification_metrics(y_dev, acuity.decide(oof, threshold["threshold"])),
            },
            "shap_valid": shap_summary(booster, X_valid, names),
        }

    report = {
        "experiment": "backlog 09 — 버튼 피처 vs 버튼 + 활력징후(응급도 LightGBM)",
        "seed": acuity.SEED,
        "lightgbm_params": acuity.LGBM_PARAMS,
        "data": {
            "processed_sha256": sha256_file(processed_dir / split.PROCESSED_FILE),
            **{f"{name}_ids_sha256": sha256_file(split.split_path(splits_dir, name)) for name in split.DEV_SPLITS},
            "rows": {"train": len(train), "valid": len(valid)},
            "vitals_missing": {"train": missing_counts(train), "valid": missing_counts(valid)},
        },
        "missing_rule": "활력징후 결측(측정 불가·빈칸)은 NaN 그대로 LightGBM에 넘긴다(분기마다 결측 쪽 방향을 학습한다). 채우지 않는다",
        "threshold_rule": "설정마다 acuity.select_threshold로 valid에서 응급 재현율 ≥ 0.95 중 정밀도 최대. valid 지표는 임계값을 정한 데이터라 낙관적이다",
        "cv_note": "cv_train_valid는 train+valid 층화 5겹 교차검증 예측(라운드 수는 train에서 정한 값). 임계값은 valid로 정한 값을 그대로 쓴다",
        "test_used": False,
        "setups": results,
    }
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / f"{REPORT_NAME}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    (reports_dir / f"{REPORT_NAME}.md").write_text(render_markdown(report))
    write_figures(report, reports_dir / "figures")
    return report


def render_markdown(report: dict) -> str:
    setups = report["setups"]
    table = {
        f"{setup} {part} ({rule})": r[part][rule]
        for part in ("valid", "cv_train_valid")
        for setup, r in setups.items()
        for rule in ("argmax", "threshold")
    }
    lines = [
        f"# {REPORT_NAME}",
        "",
        "버튼 피처만 쓴 응급도 LightGBM과 버튼 + 활력징후 LightGBM. 같은 분할·seed·설정, 검증셋 비교(test 미사용). 서빙 모델과 무관하다.",
        "",
        metrics_table(table),
        "임계값(valid 응급 재현율 ≥ 95% 중 정밀도 최대)",
        "",
        "| 설정 | 임계값 | valid 응급 재현율 | valid 응급 예측 건수 | 학습 라운드 |",
        "|---|---|---|---|---|",
        *(
            f"| {setup} | {r['threshold']['threshold']:.4f} | {r['threshold']['recall'][0]}/{r['threshold']['recall'][1]} "
            f"| {r['threshold']['precision'][1]}/{report['data']['rows']['valid']} | {r['num_rounds']} |"
            for setup, r in setups.items()
        ),
        "",
        "활력징후 결측(분자/분모)",
        "",
        "| 피처 | train | valid |",
        "|---|---|---|",
        *(
            f"| {name} | {'/'.join(map(str, report['data']['vitals_missing']['train'][name]))} "
            f"| {'/'.join(map(str, report['data']['vitals_missing']['valid'][name]))} |"
            for name in VITAL_FEATURES
        ),
        "",
        "SHAP(valid, 클래스별 평균 |SHAP| 상위 피처, 원점수 단위)",
        "",
    ]
    for setup, r in setups.items():
        lines += [f"## {setup}", "", "| 클래스 | 활력징후 몫 | 상위 피처 |", "|---|---|---|"]
        for label, s in r["shap_valid"].items():
            share = "-" if s["vitals_share"] is None or setup == "buttons" else f"{s['vitals_share']:.1%}"
            top = ", ".join(f"{t['feature']} {t['mean_abs_shap']:.3f}" for t in s["top"])
            lines.append(f"| {label} | {share} | {top} |")
        lines.append("")
    lines += [
        "그림: `figures/experiment_vitals_confusion.png`(임계값 규칙 혼동행렬), `figures/experiment_vitals_recall.png`(클래스별 재현율)",
        "",
    ]
    return "\n".join(lines)


def write_figures(report: dict, figures_dir: Path) -> None:
    """혼동행렬 2개(한 그림에 나란히)와 클래스별 재현율 막대. valid, 임계값 규칙."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figures_dir.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.size": 10, "axes.edgecolor": "#52514e", "axes.labelcolor": "#0b0b0b", "text.color": "#0b0b0b"})
    setups = report["setups"]
    save = {"dpi": 150, "bbox_inches": "tight", "metadata": {"Software": None}}  # 버전 문자열을 빼 같은 입력이면 같은 파일

    fig, axes = plt.subplots(1, len(setups), figsize=(10, 4), constrained_layout=True)
    for k, (ax, (setup, r)) in enumerate(zip(axes, setups.items(), strict=True)):
        matrix = np.array(r["valid"]["threshold"]["confusion"]["matrix"])
        ax.imshow(matrix, cmap="Blues", vmin=0, vmax=matrix.sum(axis=1).max())
        for (i, j), n in np.ndenumerate(matrix):
            ax.text(
                j, i, f"{n}/{matrix[i].sum()}", ha="center", va="center", color="#ffffff" if n > matrix.sum(axis=1).max() / 2 else "#0b0b0b"
            )
        ax.set_xticks(range(len(ACUITIES)), ACUITIES)
        ax.set_yticks(range(len(ACUITIES)), ACUITIES if k == 0 else [])
        ax.set_xlabel("Predicted")
        if k == 0:
            ax.set_ylabel("True")
        ax.set_title(f"{LABELS[setup]} (valid, threshold rule)")
    fig.savefig(figures_dir / f"{REPORT_NAME}_confusion.png", **save)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4))
    width = 0.38
    for k, (setup, r) in enumerate(setups.items()):
        recalls = [r["valid"]["threshold"]["per_class"][a]["recall"] for a in ACUITIES]
        xs = np.arange(len(ACUITIES)) + (k - 0.5) * (width + 0.02)
        ax.bar(xs, [c["value"] for c in recalls], width, color=COLORS[setup], label=LABELS[setup])
        for x, c in zip(xs, recalls, strict=True):
            ax.text(x, c["value"] + 0.02, f"{c['n']}/{c['of']}", ha="center", va="bottom", fontsize=8, color="#52514e")
    ax.set_xticks(range(len(ACUITIES)), ACUITIES)
    ax.set_ylim(0, 1.1)
    ax.set_ylabel("Recall")
    ax.set_title("Recall by class (valid, threshold rule)")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="upper right")
    fig.savefig(figures_dir / f"{REPORT_NAME}_recall.png", **save)
    plt.close(fig)
