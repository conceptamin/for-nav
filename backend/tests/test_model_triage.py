# 응급도·진료과 모델 연결(backlog 06): 규칙이 먼저, 모델 응급도가 보조 점수 자리를 대신, 막연한 분기만 모델 진료과.
# 모델은 가짜 함수로 바꾸고 modeling 코드·아티팩트를 읽지 않는다.

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.model import load_model
from app.routers.worker import triage_model
from app.rules.triage import MODEL_THRESHOLD, model_score, rule_department
from app.schemas import Intake, ModelPrediction
from app.settings import load_settings
from app.vocab import BODY_PARTS, SYMPTOMS

BASE = {
    "id": "in-test",
    "language": "vi",
    "bodyParts": ["hand"],
    "symptoms": ["cut", "bleeding"],
    "freeText": "",
    "onset": None,
    "workRelated": None,
    "workType": None,
    "industry": None,
    "district": None,
    "createdAt": "2026-10-26T01:00:00.000Z",
}
CHEST_PAIN = {**BASE, "bodyParts": ["chest"], "symptoms": ["pain"]}
ABDOMEN_PAIN = {**BASE, "bodyParts": ["abdomen"], "symptoms": ["pain"]}
TRIAGE_CASES = json.loads((Path(__file__).parent / "fixtures" / "parity.json").read_text())["triage"]


def prediction(acuity: str = "outpatient", top2: tuple[str, str] = ("internal", "family")) -> ModelPrediction:
    return ModelPrediction(
        acuity=acuity,
        acuity_proba={"emergency": 0.9 if acuity == "emergency" else 0.01, "today": 0.05, "outpatient": 0.04},
        department_proba={top2[0]: 0.6, top2[1]: 0.3, "occ": 0.1},
        shap=[{"feature": "symptom_pain", "value": 1.0, "contribution": 0.42}],
        department_top2=list(top2),
        department_fallback=False,
    )


def post(model, body: dict) -> dict:
    app.dependency_overrides[triage_model] = lambda: model
    try:
        return TestClient(app).post("/api/triage", json=body).json()
    finally:
        app.dependency_overrides.clear()


def test_rule_emergency_wins_over_model():
    out = post(lambda i: prediction("outpatient"), CHEST_PAIN)

    assert (out["emergency"], out["byRule"], out["byModel"]) == (True, True, False)
    assert out["reasons"] == ["chest"]
    assert out["model"]["acuity"] == "outpatient"


def test_model_emergency_without_rule_is_emergency():
    out = post(lambda i: prediction("emergency"), BASE)

    assert (out["emergency"], out["byRule"], out["byModel"]) == (True, False, True)
    assert out["reasons"] == ["riskScore"]


def test_model_replaces_score_but_model_score_is_kept():
    # 보조 점수 3점(머리·어지러움·구토)이라도 모델이 비응급이면 byModel은 false다. modelScore 값은 그대로 보인다.
    body = {**BASE, "bodyParts": ["head"], "symptoms": ["dizzy", "nausea"]}
    assert model_score(Intake.model_validate(body)) >= MODEL_THRESHOLD
    out = post(lambda i: prediction("today"), body)

    assert (out["emergency"], out["byModel"], out["modelScore"]) == (False, False, 3)


def test_model_output_fields():
    out = post(lambda i: prediction("today"), BASE)

    assert set(out["model"]) == {"acuity", "acuityProba", "departmentProba", "shap"}
    assert out["model"]["shap"] == [{"feature": "symptom_pain", "value": 1.0, "contribution": 0.42}]


def test_model_gets_intake_with_acuity_inputs():
    seen: list[Intake] = []
    post(lambda i: seen.append(i) or prediction(), {**BASE, "painScore": 7, "mental": "verbal"})

    [intake] = seen
    assert intake.model_dump()["pain_score"] == 7
    assert intake.model_dump()["mental"] == "verbal"


def test_explicit_rule_department_is_kept():
    # 손·베인 상처·출혈은 규칙표가 외과로 정한다.
    out = post(lambda i: prediction(top2=("derm", "family")), BASE)
    assert out["department"] == {"primary": "surgery", "alt": "ortho"}


def test_generic_branch_uses_model_department():
    # 배·통증은 내과 묶음(막연한 분기)이라 모델 상위 2개를 쓴다.
    out = post(lambda i: prediction(top2=("family", "occ")), ABDOMEN_PAIN)
    assert out["department"] == {"primary": "family", "alt": "occ"}


def test_generic_branch_without_model_is_rule_table():
    assert post(None, ABDOMEN_PAIN)["department"] == {"primary": "internal", "alt": "family"}


def test_missing_inputs_have_no_department_even_with_model():
    out = post(lambda i: prediction(), {**BASE, "symptoms": []})
    assert out["department"] is None
    assert out["missing"] == ["symptoms"]


def test_predict_error_falls_back_to_rules(caplog):
    def boom(intake):
        raise RuntimeError(f"bad input {intake.free_text}")

    body = {**BASE, "freeText": "MARKER-123"}
    out = post(boom, body)

    assert out == post(None, body)
    assert "model" not in out
    assert "MARKER-123" not in caplog.text
    assert "model predict failed=RuntimeError" in caplog.text


@pytest.mark.parametrize("case", TRIAGE_CASES[::10], ids=[f"triage-{n}" for n in range(0, len(TRIAGE_CASES), 10)])
def test_without_model_route_matches_parity(case):
    # MODEL_DIR이 빈 기본 상태에서 /api/triage는 프론트 규칙과 같고 model 키가 없다.
    assert post(None, case["input"]) == case["output"]


def test_generic_branches_are_internal_bundle_and_default():
    generic = {(p, s): rule_department([p], [s])[0].model_dump() for p in BODY_PARTS for s in SYMPTOMS if rule_department([p], [s])[1]}
    assert {(d["primary"], d["alt"]) for d in generic.values()} == {("internal", "family")}
    # 기본값(family/internal)은 부위가 있으면 닿지 않는다.
    assert rule_department([], [])[0].model_dump() == {"primary": "family", "alt": "internal"}
    assert rule_department([], [])[1] is True


def test_empty_model_dir_loads_nothing():
    assert load_model("") is None


def test_model_dir_must_exist(tmp_path: Path):
    assert load_settings({"MODEL_DIR": str(tmp_path)}).model_dir == str(tmp_path)
    with pytest.raises(ValueError, match="MODEL_DIR"):
        load_settings({"MODEL_DIR": str(tmp_path / "nope")})


def test_lifespan_loads_model_once(monkeypatch: pytest.MonkeyPatch):
    calls: list[str] = []

    def fake_load(model_dir: str):
        calls.append(model_dir)
        return lambda i: prediction("emergency")

    monkeypatch.setattr("app.main.load_model", fake_load)
    with TestClient(app) as c:
        assert c.post("/api/triage", json=BASE).json()["byModel"] is True
        assert c.post("/api/triage", json=BASE).json()["byModel"] is True
    assert len(calls) == 1
