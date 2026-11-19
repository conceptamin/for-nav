# 서빙 아티팩트 내보내기(backlog 08): models/{dept_a,dept_b,ensemble}/<predict.VERSION>/.
# - 모델 파일은 학습 라운드(SOURCE_ROUNDS)에서 바이트 그대로 옮긴다(재학습하지 않는다). 응급도 모델은 지웠다(backlog 15).
# - metadata.json: 모델 버전, 원본 라운드, 학습 데이터 sha256, seed, 가중치·폴백 기준, 피처·라벨 순서, 검증·최종 측정값, 생성 시각,
#   파일별 sha256(predict.py가 불러올 때 확인한다). 측정값은 reports/의 JSON에서 옮기고, 최종(test) 리포트가 없으면 멈춘다.
# - 불러올 때 코드를 실행하는 형식은 쓰지 않는다(LightGBM 텍스트, JSON).
# - v3(backlog 16): 모델 A는 Kaggle+DDXPlus를 벡터 단위로 나눈 train으로 다시 학습했고(dept_a/v3), 모델 B는 다시 학습하지 않아
#   v2와 같은 가중치(dept_b/v0)다. 최종 수치는 새 test와 18의 최종 평가용 안내 조합을 한 번 평가한 ensemble_v3_test에서 옮긴다.
# - v4(backlog 13): 모델 A는 v3 그대로(dept_a/v3), 모델 B는 보정·보강한 표에서 최종 평가 조합을 빼고 다시 학습했다(dept_b/v4).
#   앙상블은 다시 조정했고(ensemble/v4), 최종 수치는 ensemble_v4_test에서 옮긴다.

import hashlib
import json
from pathlib import Path

from fornav_modeling.predict import VERSION
from fornav_modeling.schema import DEPARTMENTS

SOURCE_ROUNDS = {"dept_a": "v3", "dept_b": "v4"}
ENSEMBLE_ROUND = "v4"
COPIED = {"dept_a": ("model.txt", "departments.json"), "dept_b": ("weights.json",)}


class ExportError(RuntimeError):
    pass


def export_all(models_dir: Path, reports_dir: Path, created_at: str) -> dict[str, dict]:
    """세 아티팩트를 쓰고 {이름: metadata}를 돌려준다. created_at은 ISO 8601 문자열(명령이 넘긴다)."""
    reports = {key: _read_json(reports_dir / f"{name}.json") for key, name in report_names().items()}
    out = {}
    for name, files in COPIED.items():
        source = models_dir / name / SOURCE_ROUNDS[name]
        meta = _read_json(source / "metadata.json")
        texts = {f: (source / f).read_text() for f in files}
        if any(_sha(texts[f]) != meta["files"][f] for f in texts):
            raise ExportError(f"{source}의 모델 파일이 metadata.json 해시와 다르다")
        serving = _BUILDERS[name](meta, reports) | {"created_at": created_at}
        out[name] = _write(models_dir / name / VERSION, texts, serving)
    text = (models_dir / "ensemble" / ENSEMBLE_ROUND / "ensemble.json").read_text()
    if _sha(text) != reports["ensemble_test"]["ensemble_sha256"]:
        raise ExportError("ensemble.json이 test로 평가한 것과 다르다. tune_ensemble → evaluate --model ensemble 순서로 다시 한다")
    ensemble_meta = _ensemble_meta(json.loads(text), reports, out) | {"created_at": created_at}
    out["ensemble"] = _write(models_dir / "ensemble" / VERSION, {"ensemble.json": text}, ensemble_meta)
    return out


def report_names() -> dict[str, str]:
    """리포트 열쇠(dept_a, dept_a_test, …) → 파일 이름(dept_a_v3, dept_a_v3_test, …). 모델 B의 test 수치는 앙상블 test의 B 단독이다
    (모델 B는 질환·증상 데이터로 학습하지 않아 따로 test 평가하지 않는다)."""
    rounds = SOURCE_ROUNDS | {"ensemble": ENSEMBLE_ROUND}
    names = {f"{name}{suffix}": f"{name}_{r}{suffix}" for name, r in rounds.items() for suffix in ("", "_test")}
    del names["dept_b_test"]
    return names


def _dept_a_meta(meta: dict, reports: dict) -> dict:
    results = reports["dept_a"]["results"]
    return {
        "model_version": f"dept_a/{VERSION}",
        "source": f"dept_a/{SOURCE_ROUNDS['dept_a']}",
        **{k: meta[k] for k in ("seed", "lightgbm_params", "num_rounds", "data", "feature_names", "labels", "output")},
        "metrics": {
            "valid": {k: _topk(v) for k, v in results["valid"].items()},
            "valid_guide": _topk(results["guide"]["all"]),
            "final_test": {k: _topk(v) | {"final": True} for k, v in reports["dept_a_test"]["department"].items()},
            "final_guide": _final(reports["ensemble_test"], "A 단독", "final_guide"),
        },
    }


def _dept_b_meta(meta: dict, reports: dict) -> dict:
    results = reports["dept_b"]["results"]
    return {
        "model_version": f"dept_b/{VERSION}",
        "source": f"dept_b/{SOURCE_ROUNDS['dept_b']}",
        **{k: meta[k] for k in ("seed", "setting", "architecture", "hyperparams", "data", "feature_names", "input_features", "labels")},
        "table_changes": "외상 보정 규칙과 빈 조합 채우기(backlog 13). 최종 평가용 조합과 같은 표 행은 학습에서 뺐다",
        "metrics": {
            "valid_guide": _topk(results["guide"]["all"]),
            "valid_symptom": {k: _topk(v) for k, v in results["symptom_valid"].items()},
            "valid_guide_trauma": _topk(results["guide"]["trauma"]),
            "held_out_table_kl_mean": results["held_out_table"]["kl_mean"],
            "final_test": _final(reports["ensemble_test"], "B 단독"),
            "final_guide": _final(reports["ensemble_test"], "B 단독", "final_guide"),
        },
    }


def _ensemble_meta(params: dict, reports: dict, components: dict[str, dict]) -> dict:
    tuning = reports["ensemble"]
    chosen = next(k for k in tuning["results"] if k.startswith("선택"))
    final = next(k for k in reports["ensemble_test"]["results"] if k.endswith("최종"))
    return {
        "model_version": f"ensemble/{VERSION}",
        "source": f"ensemble/{ENSEMBLE_ROUND}",
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
            "final_test": {k: v | {"final": True} for k, v in reports["ensemble_test"]["results"][final].items()},
        },
    }


_BUILDERS = {"dept_a": _dept_a_meta, "dept_b": _dept_b_meta}


def _final(test_report: dict, rule: str, prefix: str = "test_") -> dict:
    """앙상블 test 리포트에서 한 규칙(A 단독, B 단독)의 평가셋별 Top-1·Top-2."""
    by_set = test_report["results"][rule]
    return {k: _topk(v) | {"final": True} for k, v in by_set.items() if k.startswith(prefix)}


def _topk(m: dict) -> dict:
    return {"top1": m["top1"], "top2": m["top2"]}


def _write(model_dir: Path, texts: dict[str, str], metadata: dict) -> dict:
    model_dir.mkdir(parents=True, exist_ok=True)
    for name, text in texts.items():
        (model_dir / name).write_text(text)
    return _write_metadata(model_dir, metadata | {"files": {name: _sha(text) for name, text in texts.items()}})


def _write_metadata(model_dir: Path, metadata: dict) -> dict:
    if metadata.get("labels") != list(DEPARTMENTS):
        raise ExportError(f"{model_dir}의 라벨 순서가 열거값과 다르다")
    (model_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    return metadata


def _read_json(path: Path) -> dict:
    if not path.exists():
        raise ExportError(f"{path}가 없다. 학습·조정·test 평가를 먼저 한다")
    return json.loads(path.read_text())


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()
