# 서빙 아티팩트 내보내기(backlog 08): models/{acuity,dept_a,dept_b,ensemble}/v1/.
# - 모델 파일은 v0을 바이트 그대로 옮긴다(재학습하지 않는다). 응급도는 서빙 모델인 LightGBM만 옮기고 비교용 로지스틱은 뺀다.
# - metadata.json: 모델 버전, 원본 라운드, 학습 데이터 sha256, seed, 임계값·가중치·폴백 기준, 피처·라벨 순서, 검증·최종 측정값, 생성 시각,
#   파일별 sha256(predict.py가 불러올 때 확인한다). 측정값은 reports/의 JSON에서 옮기고, 최종(test) 리포트가 없으면 멈춘다.
# - 불러올 때 코드를 실행하는 형식은 쓰지 않는다(LightGBM 텍스트, JSON).

import hashlib
import json
from pathlib import Path

from fornav_modeling.predict import ACUITIES, UNKNOWN_RULE, VERSION
from fornav_modeling.schema import DEPARTMENTS

SOURCE_ROUND = "v0"
COPIED = {"acuity": ("model.txt",), "dept_a": ("model.txt", "departments.json"), "dept_b": ("weights.json",)}


class ExportError(RuntimeError):
    pass


def export_all(models_dir: Path, reports_dir: Path, created_at: str) -> dict[str, dict]:
    """네 아티팩트를 쓰고 {이름: metadata}를 돌려준다. created_at은 ISO 8601 문자열(명령이 넘긴다)."""
    reports = {name: _read_json(reports_dir / f"{name}.json") for name in _REPORTS}
    out = {}
    for name in COPIED:
        source = models_dir / name / SOURCE_ROUND
        meta = _read_json(source / "metadata.json")
        texts = {f: (source / f).read_text() for f in COPIED[name]}
        if any(_sha(texts[f]) != meta["files"][f] for f in texts):
            raise ExportError(f"{source}의 모델 파일이 metadata.json 해시와 다르다")
        out[name] = _write(models_dir / name / VERSION, texts, _BUILDERS[name](meta, reports) | {"created_at": created_at})
    ensemble_dir = models_dir / "ensemble" / VERSION
    text = (ensemble_dir / "ensemble.json").read_text()
    if _sha(text) != reports["ensemble_v1_test"]["ensemble_sha256"]:
        raise ExportError("ensemble.json이 test로 평가한 것과 다르다. tune_ensemble → evaluate --model ensemble 순서로 다시 한다")
    out["ensemble"] = _write(
        ensemble_dir, {"ensemble.json": text}, _ensemble_meta(json.loads(text), reports, out) | {"created_at": created_at}
    )
    return out


_REPORTS = ("acuity_v0", "acuity_v0_test", "dept_a_v0", "dept_a_v0_test", "dept_b_v0", "dept_b_v0_test", "ensemble_v1", "ensemble_v1_test")


def _acuity_meta(meta: dict, reports: dict) -> dict:
    lgbm = reports["acuity_v0"]["models"]["lightgbm"]
    test = reports["acuity_v0_test"]["models"]["lightgbm"]
    return {
        "model_version": f"acuity/{VERSION}",
        "source": f"acuity/{SOURCE_ROUND}",
        "model": "LightGBM multiclass(텍스트). 비교용 로지스틱 회귀는 서빙하지 않아 옮기지 않았다",
        "seed": meta["seed"],
        "lightgbm_params": meta["lightgbm_params"],
        "num_rounds": meta["num_rounds"],
        "data": meta["data"],
        "feature_names": meta["feature_names"],
        "labels": meta["labels"],
        "threshold": lgbm["threshold"]["threshold"],
        "threshold_rule": lgbm["threshold"]["rule"],
        "decision_rule": meta["decision_rule"],
        "unknown_inputs": UNKNOWN_RULE,
        "metrics": {
            "valid": _acuity_metrics(lgbm["valid"]["threshold"]),
            "final_test": _acuity_metrics(test["threshold_rule"]) | {"final": True},
        },
    }


def _acuity_metrics(m: dict) -> dict:
    return {
        "emergency_recall": m["per_class"]["emergency"]["recall"],
        "emergency_precision": m["per_class"]["emergency"]["precision"],
        "accuracy": m["accuracy"],
        "per_class": m["per_class"],
    }


def _dept_a_meta(meta: dict, reports: dict) -> dict:
    results = reports["dept_a_v0"]["results"]
    return {
        "model_version": f"dept_a/{VERSION}",
        "source": f"dept_a/{SOURCE_ROUND}",
        **{k: meta[k] for k in ("seed", "lightgbm_params", "num_rounds", "data", "feature_names", "labels", "output")},
        "metrics": {
            "valid_kaggle": _topk(results["valid"]["department"]),
            "valid_guide": _topk(results["guide"]["all"]),
            "final_test_kaggle": _topk(reports["dept_a_v0_test"]["department"]) | {"final": True},
        },
    }


def _dept_b_meta(meta: dict, reports: dict) -> dict:
    results = reports["dept_b_v0"]["results"]
    return {
        "model_version": f"dept_b/{VERSION}",
        "source": f"dept_b/{SOURCE_ROUND}",
        **{k: meta[k] for k in ("seed", "architecture", "hyperparams", "data", "feature_names", "input_features", "labels")},
        "metrics": {
            "valid_guide": _topk(results["guide"]["all"]),
            "valid_guide_trauma": _topk(results["guide"]["trauma"]),
            "held_out_table_kl_mean": results["held_out_table"]["kl_mean"],
            "final_test_kaggle": _topk(reports["dept_b_v0_test"]["department"]) | {"final": True},
        },
    }


def _ensemble_meta(params: dict, reports: dict, components: dict[str, dict]) -> dict:
    tuning = reports["ensemble_v1"]
    chosen = next(k for k in tuning["results"] if k.startswith("선택"))
    final = next(k for k in reports["ensemble_v1_test"]["results"] if k.endswith("최종"))
    return {
        "model_version": f"ensemble/{VERSION}",
        "components": {
            name: {"version": components[name]["model_version"], "files": components[name]["files"]} for name in ("dept_a", "dept_b")
        },
        "tuned_with": params["components"],
        "weight_a": params["weight_a"],
        "weight_b": params["weight_b"],
        "fallback_threshold": params["fallback_threshold"],
        "fallback": params["fallback"],
        "fallback_rule": "앙상블 분포의 최대 확률 < fallback_threshold이면 상위 2개를 fallback(가정의학과, 내과)으로 바꾼다",
        "selection_rule": tuning["rule"],
        "labels": list(DEPARTMENTS),
        "metrics": {
            "tuning": tuning["results"][chosen],
            "tuning_leave_one_out": tuning["leave_one_out"],
            "final_test_kaggle": reports["ensemble_v1_test"]["results"][final]["all"] | {"final": True},
        },
    }


_BUILDERS = {"acuity": _acuity_meta, "dept_a": _dept_a_meta, "dept_b": _dept_b_meta}


def _topk(m: dict) -> dict:
    return {"top1": m["top1"], "top2": m["top2"]}


def _write(model_dir: Path, texts: dict[str, str], metadata: dict) -> dict:
    model_dir.mkdir(parents=True, exist_ok=True)
    for name, text in texts.items():
        (model_dir / name).write_text(text)
    metadata = metadata | {"files": {name: _sha(text) for name, text in texts.items()}}
    if metadata.get("labels") not in (list(ACUITIES), list(DEPARTMENTS)):
        raise ExportError(f"{model_dir}의 라벨 순서가 열거값과 다르다")
    (model_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    return metadata


def _read_json(path: Path) -> dict:
    if not path.exists():
        raise ExportError(f"{path}가 없다. 학습·조정·test 평가를 먼저 한다")
    return json.loads(path.read_text())


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()
