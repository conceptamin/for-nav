# 경로별 응답 형태·상태 코드. 값의 세부 일치는 test_parity.py가 맡는다.

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app import clock
from app.data.mock import StatRecord
from app.main import app
from app.store import store

client = TestClient(app)

INTAKE = {
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


@pytest.fixture(autouse=True)
def _reset_store():
    store.reset()
    yield
    store.reset()


def test_health():
    assert client.get("/api/health").json() == {"ok": True}


def test_meta():
    assert client.get("/api/meta").json() == {
        "infoDate": "2026-10-24",
        "centerHours": {"openHour": 9, "closeHour": 18, "workdays": [1, 2, 3, 4, 5]},
    }


def test_triage_readme_examples():
    r = client.post("/api/triage", json=INTAKE)
    assert r.status_code == 200
    assert r.json() == {
        "emergency": False,
        "reasons": [],
        "byRule": False,
        "byModel": False,
        "modelScore": 2,
        "department": {"primary": "surgery", "alt": "ortho"},
        "missing": [],
    }
    chest = client.post("/api/triage", json={**INTAKE, "bodyParts": ["chest"], "symptoms": ["pain"]}).json()
    assert chest == {
        "emergency": True,
        "reasons": ["chest"],
        "byRule": True,
        "byModel": False,
        "modelScore": 0,
        "department": {"primary": "internal", "alt": "family"},
        "missing": [],
    }


def test_invalid_enum_is_422():
    assert client.post("/api/triage", json={**INTAKE, "bodyParts": ["tail"]}).status_code == 422
    assert client.post("/api/triage", json={**INTAKE, "language": "de"}).status_code == 422


def test_extract_fills_empty_fields():
    body = {"intake": {**INTAKE, "bodyParts": [], "symptoms": [], "freeText": "Ngón tay bị kẹp vào máy dập, bị sưng."}}
    out = client.post("/api/extract", json=body).json()
    assert out["extraction"] == {
        "bodyParts": ["hand"],
        "symptoms": ["swelling"],
        "onset": None,
        "workRelated": "yes",
        "workType": "machine",
    }
    assert out["intake"]["bodyParts"] == ["hand"]
    assert out["filled"] is True


def test_extract_keeps_button_input():
    body = {"intake": {**INTAKE, "freeText": "nothing useful"}}
    out = client.post("/api/extract", json=body).json()
    assert out["intake"]["bodyParts"] == ["hand"]
    assert out["filled"] is False


# 응급도 모델 입력(backlog 10) -----------------------------------------------------

ACUITY_INPUTS = {"ageGroup": "45to64", "sex": "female", "injury": True, "painScore": 7, "mental": "alert"}


def test_acuity_inputs_are_optional_and_absent_when_unset():
    # 새 키가 없는 요청의 응답은 지금과 같다(프론트 타입·동기화 테스트와 맞는다)
    out = client.post("/api/extract", json={"intake": INTAKE}).json()
    assert out["intake"] == INTAKE
    assert client.post("/api/triage", json=INTAKE).json() == client.post("/api/triage", json={**INTAKE, "ageGroup": None}).json()


def test_acuity_inputs_round_trip():
    r = client.post("/api/extract", json={"intake": {**INTAKE, **ACUITY_INPUTS}})
    assert r.status_code == 200
    assert r.json()["intake"] == {**INTAKE, **ACUITY_INPUTS}
    # 규칙은 아직 이 값을 쓰지 않는다(모델 연결은 backlog 06)
    assert client.post("/api/triage", json={**INTAKE, **ACUITY_INPUTS}).json() == client.post("/api/triage", json=INTAKE).json()


@pytest.mark.parametrize(
    "bad",
    [
        {"painScore": 11},
        {"painScore": -1},
        {"painScore": "3"},
        {"painScore": 2.5},
        {"ageGroup": "child"},
        {"mental": "asleep"},
        {"sex": "x"},
        {"injury": "yes"},
    ],
)
def test_acuity_inputs_out_of_range_are_422(bad):
    assert client.post("/api/triage", json={**INTAKE, **bad}).status_code == 422


def test_acuity_enums_match_model_features():
    # 순서가 모델 피처 값이다. modeling/src/fornav_modeling/features/buttons.py의 MENTALS·AGE_GROUPS·SEXES와 같아야 한다
    from typing import get_args

    from app import vocab

    assert get_args(vocab.AgeGroup) == ("under30", "30to44", "45to64", "65plus")
    assert get_args(vocab.Sex) == ("female", "male")
    assert get_args(vocab.Mental) == ("alert", "verbal", "pain", "unresponsive")


def test_route_readme_example():
    out = client.post("/api/route", json={"workRelated": "unknown", "insurance": "no", "ulsan90": "yes"}).json()
    assert out == {
        "infoDate": "2026-10-24",
        "alsoIndustrial": True,
        "path": "ulsanSupport",
        "institutions": [{"id": "center", "phone": None}, {"id": "ulsan", "phone": None}],
        "docs": ["arc", "receipts"],
    }


def test_visit_helper_shape():
    out = client.post("/api/visit-helper", json={"intake": INTAKE, "department": "surgery", "firstVisit": True, "lang": "vi"}).json()
    assert set(out) == {"desk", "call", "llmSlots"}
    assert out["llmSlots"] == []
    assert out["desk"]["firstVisit"] is True
    assert out["desk"]["lines"][0]["native"] == "Tôi đến lần đầu."
    assert [f["id"] for f in out["call"]["faq"]] == ["first", "when", "where", "insurance", "help"]


def test_clinician_report_shape():
    body = {"intake": {**INTAKE, "freeText": "Bị cắt tay"}, "included": ["symptoms", "note"], "profile": None, "meds": ""}
    out = client.post("/api/report/clinician", json=body).json()
    assert out["id"].startswith("rp-")
    assert out["createdAt"].endswith("Z")
    assert [r["field"] for r in out["rows"]] == ["symptoms", "note"]
    assert out["rows"][1]["valueKo"] == "Bị cắt tay (원문, 번역 미연결)"
    assert out["llmSlots"] == []


def test_center_summary():
    body = {
        "intake": INTAKE,
        "emergencyFlag": False,
        "requestType": "booking",
        "coverage": None,
        "insurance": "no",
        "contactMethod": "zalo",
    }
    out = client.post("/api/report/center", json=body).json()
    assert out["ko"].startswith("베트남어 사용 근로자.")
    assert "연락 희망: Zalo." in out["ko"]


def test_mock_cases_listed_latest_first():
    cases = client.get("/api/center/cases").json()
    assert len(cases) == 24
    assert {c["id"] for c in cases} == {f"C-{n}" for n in range(1001, 1025)}
    created = [c["createdAt"] for c in cases]
    assert created == sorted(created, reverse=True)
    assert not any(c["live"] for c in cases)


def _send(**over):
    body = {
        "intake": {**INTAKE, "workRelated": "yes"},
        "emergencyFlag": False,
        "requestType": "booking",
        "coverage": None,
        "insurance": "no",
        "contactMethod": "zalo",
        "contact": " 010-0000-0000 ",
        "consentedItems": ["증상", "부위"],
        **over,
    }
    return client.post("/api/center/cases", json=body)


def test_send_case_flow():
    r = _send()
    assert r.status_code == 201
    out = r.json()
    case = out["case"]
    assert case["live"] is True
    assert case["status"] == "new"
    assert case["urgency"] == "high"
    assert case["urgencyReasons"] == ["업무 중 발생", "건강보험증 없음"]
    assert case["contact"] == "010-0000-0000"
    assert case["id"].startswith("C-")
    assert len(out["nextOpenDate"]) == 10

    listed = client.get("/api/center/cases").json()
    assert len(listed) == 25
    assert listed[0]["id"] == case["id"]
    assert client.get(f"/api/center/cases/{case['id']}").json() == case


def test_server_rebuilds_summary():
    case = _send(summaryKo="클라이언트가 보낸 요약").json()["case"]
    assert case["summaryKo"].startswith("베트남어 사용 근로자.")


def test_same_millisecond_ids_get_suffix(monkeypatch):
    fixed = datetime(2026, 10, 26, 10, 0, 0, 123000, tzinfo=clock.SEOUL)
    monkeypatch.setattr(clock, "now", lambda: fixed)
    first = _send().json()["case"]["id"]
    second = _send().json()["case"]["id"]
    assert second == f"{first}-2"


def test_since_filter():
    case = _send().json()["case"]
    assert [c["id"] for c in client.get("/api/center/cases", params={"since": "2000-01-01T00:00:00Z", "status": "new"}).json()][0] == case[
        "id"
    ]
    assert client.get("/api/center/cases", params={"since": case["createdAt"]}).json() == []


def test_patch_status_and_reset():
    r = client.patch("/api/center/cases/C-1024", json={"status": "done"})
    assert r.status_code == 200
    assert r.json()["status"] == "done"
    assert client.get("/api/center/cases/C-1024").json()["status"] == "done"
    assert client.patch("/api/center/cases/C-1024", json={"status": "closed"}).status_code == 422

    _send()
    assert client.post("/api/center/reset").status_code == 204
    cases = client.get("/api/center/cases").json()
    assert len(cases) == 24
    assert next(c for c in cases if c["id"] == "C-1024")["status"] == "new"


def test_unknown_case_is_404():
    assert client.get("/api/center/cases/C-0").status_code == 404
    assert client.patch("/api/center/cases/C-0", json={"status": "done"}).status_code == 404


def test_stats_shape():
    out = client.get("/api/center/stats", params={"days": 180}).json()
    assert out["total"] == 420
    assert [c["key"] for c in out["byIndustry"]] == ["shipbuilding", "autoparts", "chemical", "construction", "other"]
    assert [c["key"] for c in out["byLanguage"]] == ["vi", "en"]
    assert [c["key"] for c in out["byInsurance"]] == ["yes", "no", "unknown"]
    assert sum(c["n"] for c in out["byAfterHours"]) == 420
    assert 0 <= out["afterHoursRate"] <= 1
    assert client.get("/api/center/stats", params={"days": 7}).status_code == 422


def test_stats_hides_small_cells(monkeypatch):
    now = clock.now()
    rec = StatRecord(
        date=now,
        district="jung",
        industry="chemical",
        language="vi",
        insurance="no",
        after_hours=True,
        request_type="booking",
        work_related="yes",
    )
    monkeypatch.setattr(store, "stat_records", [rec] * 6 + [StatRecord(**{**rec.__dict__, "industry": "other"})])
    out = client.get("/api/center/stats", params={"days": 30}).json()
    assert out["total"] == 7
    assert {c["key"]: c["n"] for c in out["byIndustry"]} == {
        "shipbuilding": None,
        "autoparts": None,
        "chemical": 6,
        "construction": None,
        "other": None,
    }

    out = client.get("/api/center/stats", params={"days": 30, "district": "nam"}).json()
    assert out["total"] is None
    assert out["afterHoursRate"] is None
    assert all(c["n"] is None for c in out["byIndustry"])
