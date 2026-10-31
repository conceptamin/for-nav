# 진료과 모델 연결(backlog 06): 규칙표가 먼저, 막연한 분기만 모델 진료과. 응급 여부는 판정하지 않는다(backlog 26).
# 모델은 가짜 함수로 바꾸고 modeling 코드·아티팩트를 읽지 않는다.

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.model import load_model
from app.routers.worker import triage_model
from app.rules.triage import rule_department
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


def prediction(top2: tuple[str, str] = ("internal", "family")) -> ModelPrediction:
    return ModelPrediction(
        department_proba={top2[0]: 0.6, top2[1]: 0.3, "occ": 0.1},
        department_top2=list(top2),
        department_fallback=False,
    )


def post(model, body: dict) -> dict:
    app.dependency_overrides[triage_model] = lambda: model
    try:
        return TestClient(app).post("/api/triage", json=body).json()
    finally:
        app.dependency_overrides.clear()


def test_response_has_no_emergency_fields():
    out = post(lambda i: prediction(), CHEST_PAIN)

    assert set(out) == {"department", "missing", "model"}
    assert set(out["model"]) == {"departmentProba"}


def test_modeling_acuity_output_is_ignored():
    # modeling 15 전의 predict()는 acuity·acuityProba·shap도 돌려준다. 읽지 않고 버린다(검증 실패로 모델을 잃지 않는다).
    raw = {
        "acuity": "emergency",
        "acuityProba": {"emergency": 0.9, "today": 0.05, "outpatient": 0.05},
        "departmentProba": {"family": 0.6, "occ": 0.4},
        "departmentTop2": ["family", "occ"],
        "departmentFallback": False,
        "shap": [{"feature": "symptom_pain", "value": 1.0, "contribution": 0.42}],
    }
    out = post(lambda i: ModelPrediction.model_validate(raw), ABDOMEN_PAIN)

    assert out["department"] == {"primary": "family", "alt": "occ"}
    assert set(out["model"]) == {"departmentProba"}


def test_old_acuity_inputs_are_ignored():
    # 예전 프론트가 보내던 응급도 입력은 422가 아니라 무시된다. 손상 여부는 모델에 그대로 간다.
    seen: list[Intake] = []
    post(
        lambda i: seen.append(i) or prediction(),
        {**BASE, "painScore": 7, "mental": "verbal", "ageGroup": "45to64", "sex": "female", "injury": True},
    )

    [intake] = seen
    assert intake.model_dump() == {**Intake.model_validate(BASE).model_dump(), "injury": True}


def test_explicit_rule_department_is_kept():
    # 손·베인 상처·출혈은 규칙표가 외과로 정한다.
    out = post(lambda i: prediction(top2=("derm", "family")), BASE)
    assert out["department"] == {"primary": "surgery", "alt": "ortho"}


def test_generic_branch_uses_model_department():
    # 배·통증은 내과 묶음(막연한 분기)이라 모델 상위 2개를 쓴다.
    out = post(lambda i: prediction(top2=("family", "occ")), ABDOMEN_PAIN)
    assert out["department"] == {"primary": "family", "alt": "occ"}


@pytest.mark.parametrize("body", [CHEST_PAIN, {**BASE, "bodyParts": ["whole"], "symptoms": ["breath"]}], ids=["chest-pain", "breath"])
def test_fixed_combo_keeps_rule_department(body):
    # 가슴·통증, 숨참은 내과 묶음 분기지만 규칙표로 고정한다(모델은 실제로 ortho를 먼저 낸다, backlog 06·26).
    out = post(lambda i: prediction(top2=("ortho", "internal")), body)
    assert out["department"] == {"primary": "internal", "alt": "family"}


def test_generic_branch_without_model_is_rule_table():
    assert post(None, ABDOMEN_PAIN)["department"] == {"primary": "internal", "alt": "family"}


def test_missing_inputs_have_no_department_even_with_model():
    out = post(lambda i: prediction(), {**BASE, "symptoms": []})
    assert out["department"] is None
    assert out["missing"] == ["symptoms"]


def test_predict_error_falls_back_to_rule_table(caplog):
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
    # MODEL_DIR이 빈 기본 상태에서 /api/triage는 프론트 규칙표와 같고 model 키가 없다.
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
        return lambda i: prediction(("family", "occ"))

    monkeypatch.setattr("app.main.load_model", fake_load)
    with TestClient(app) as c:
        assert c.post("/api/triage", json=ABDOMEN_PAIN).json()["department"] == {"primary": "family", "alt": "occ"}
        assert c.post("/api/triage", json=ABDOMEN_PAIN).json()["department"] == {"primary": "family", "alt": "occ"}
    assert len(calls) == 1
