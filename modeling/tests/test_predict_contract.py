# predict()의 출력이 TriageResult.model 자리에 넣을 형태인지, 커밋된 서빙 묶음(predict.VERSION)만으로 동작하는지(backlog 08, 10).
# 학습 코드를 import하지 않는지, 아티팩트를 읽을 때 pickle을 쓰지 않는지, 앙상블이 정한 대로인지도 본다. 응급도 출력은 지웠다(backlog 15).

import ast
import json
import pickle
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import numpy as np
import pytest

from fornav_modeling import predict as P
from fornav_modeling.features.buttons import featurize_many
from fornav_modeling.models import dept_a, dept_b
from fornav_modeling.schema import DEPARTMENTS

MODELING = Path(__file__).resolve().parents[1]
BASE = {"id": "t1", "language": "en", "created_at": "2026-10-28T09:00:00Z"}
EXAMPLES = {
    "internal": BASE | {"body_parts": ["abdomen"], "symptoms": ["pain", "nausea", "fever"]},
    "trauma": BASE | {"body_parts": ["hand"], "symptoms": ["cut", "bleeding"], "injury": True, "work_related": "yes"},
    "teeth": BASE | {"body_parts": ["teeth"], "symptoms": ["pain", "swelling"]},
    "empty": BASE,
    "injury": BASE | {"body_parts": ["leg"], "symptoms": ["swelling"], "injury": True},
}
KEYS = {"departmentProba", "departmentTop2", "departmentFallback"}


@pytest.mark.parametrize("name", list(EXAMPLES))
def test_output_contract(name):
    out = P.predict(EXAMPLES[name])
    assert set(out) == KEYS
    assert list(out["departmentProba"]) == list(DEPARTMENTS) and sum(out["departmentProba"].values()) == pytest.approx(1.0)
    assert all(isinstance(v, float) and v >= 0 for v in out["departmentProba"].values())
    top = out["departmentTop2"]
    assert len(top) == 2 and len(set(top)) == 2 and set(top) <= set(DEPARTMENTS)
    assert isinstance(out["departmentFallback"], bool)
    json.dumps(out)  # 그대로 응답 JSON에 넣을 수 있다


def test_acuity_artifacts_are_not_needed(tmp_path):
    # 응급도 모델(models/acuity)이 없어도 서빙 묶음이 열린다(backlog 15)
    shutil.copytree(MODELING / "models", tmp_path / "models")
    assert not (tmp_path / "models" / "acuity").exists()
    assert P.predict(EXAMPLES["trauma"], models_dir=tmp_path / "models") == P.predict(EXAMPLES["trauma"])


def test_removed_acuity_inputs_do_not_change_department():
    # 백엔드는 이 넷을 더 보내지 않는다(backend 26). 모델 A는 이 피처를 쓰지 않으므로 값이 있어도 결과가 같다
    old = {"pain_score": 9, "mental": "verbal", "age_group": "65plus", "sex": "female"}
    assert P.predict(EXAMPLES["internal"] | old) == P.predict(EXAMPLES["internal"])


def test_no_pickle_in_src():
    offenders = [
        p.relative_to(MODELING).as_posix()
        for p in (MODELING / "src").rglob("*.py")
        if "pickle" in p.read_text() or "joblib" in p.read_text()
    ]
    assert offenders == []


def test_loading_artifacts_never_unpickles(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("pickle로 읽으려 했다")

    monkeypatch.setattr(pickle, "load", refuse)
    monkeypatch.setattr(pickle, "loads", refuse)
    P.load_artifacts.cache_clear()
    try:
        P.predict(EXAMPLES["trauma"])
    finally:
        P.load_artifacts.cache_clear()


def test_predict_does_not_import_training_code():
    code = "import sys; from fornav_modeling.predict import predict; predict({'id': 'x', 'language': 'en', 'created_at': 't'}); print('\\n'.join(m for m in sys.modules if m.startswith('fornav_modeling')))"
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True, cwd=MODELING, env={"PYTHONPATH": str(MODELING / "src")}
    )
    loaded = set(result.stdout.split())
    assert loaded <= {
        "fornav_modeling",
        "fornav_modeling.predict",
        "fornav_modeling.features",
        "fornav_modeling.features.buttons",
        "fornav_modeling.schema",
    }


def test_serving_imports_only_declared_dependencies():
    # 백엔드는 [project] dependencies만 설치한다(backlog 11). predict가 따라 들어가는 모듈의 외부 import가 거기에 다 있어야 한다
    declared = {
        re.split(r"[=<>~!\[ ]", d)[0].replace("-", "_")
        for d in tomllib.loads((MODELING / "pyproject.toml").read_text())["project"]["dependencies"]
    }
    src = MODELING / "src" / "fornav_modeling"
    files = [src / "predict.py", src / "features" / "buttons.py", src / "schema.py"]
    imported = set()
    for path in files:
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Import):
                imported |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                imported.add(node.module.split(".")[0])
    third_party = imported - set(sys.stdlib_module_names) - {"fornav_modeling"}
    assert third_party <= declared, third_party - declared
    assert declared == {"lightgbm", "numpy"}  # 학습 의존성(pandas, scikit-learn …)은 train 그룹에 둔다


def test_tampered_artifact_is_refused(tmp_path):
    shutil.copytree(MODELING / "models", tmp_path / "models")
    path = tmp_path / "models" / "ensemble" / P.VERSION / "ensemble.json"
    path.write_text(path.read_text().replace('"weight_a": 0.5', '"weight_a": 0.9'))
    with pytest.raises(P.ArtifactError):
        P.predict(EXAMPLES["teeth"], models_dir=tmp_path / "models")


# 진료과 앙상블 -----------------------------------------------------------------


def test_department_proba_is_weighted_mean_of_saved_models():
    a = P.load_artifacts(str(P.MODELS_DIR))
    root = MODELING / "models"
    model_a = dept_a.DeptA.from_files(
        {f: (root / "dept_a" / P.VERSION / f).read_text() for f in (dept_a.MODEL_FILE, dept_a.DEPARTMENTS_FILE)}
    )
    weights_b = json.loads((root / "dept_b" / P.VERSION / dept_b.WEIGHTS_FILE).read_text())
    for intake in EXAMPLES.values():
        X = featurize_many([intake])
        expected = a["weight_a"] * model_a.predict_proba(X)[0] + (1 - a["weight_a"]) * dept_b.predict_from_weights(weights_b, X)[0]
        assert np.allclose(list(P.predict(intake)["departmentProba"].values()), expected / expected.sum())


def test_top2_and_fallback():
    p = np.array([0.05] * 6 + [0.3, 0.2, 0.0, 0.0])
    assert P.top2(p, 0.25, ("family", "internal")) == (["dental", "neuro"], False)
    assert P.top2(p, 0.35, ("family", "internal")) == (["family", "internal"], True)
    tie = np.full(len(DEPARTMENTS), 0.1)
    assert P.top2(tie, 0.0, ("family", "internal")) == (["ortho", "surgery"], False)  # 동점은 DEPARTMENTS 순서


# metadata.json ----------------------------------------------------------------

REQUIRED = {
    "dept_a": {"model_version", "seed", "data", "feature_names", "labels", "metrics", "created_at", "files"},
    "dept_b": {
        "model_version",
        "seed",
        "data",
        "hyperparams",
        "feature_names",
        "input_features",
        "labels",
        "metrics",
        "created_at",
        "files",
    },
    "ensemble": {
        "model_version",
        "components",
        "weight_a",
        "weight_b",
        "fallback_threshold",
        "fallback",
        "labels",
        "metrics",
        "created_at",
        "files",
    },
}


@pytest.mark.parametrize("name", list(REQUIRED))
def test_v1_metadata_has_required_fields(name):
    meta = json.loads((MODELING / "models" / name / P.VERSION / "metadata.json").read_text())
    assert REQUIRED[name] <= set(meta)
    assert meta["model_version"] == f"{name}/{P.VERSION}"
    final = [k for k in meta["metrics"] if k.startswith("final")]
    assert final and all(meta["metrics"][k]["final"] is True for k in final)
