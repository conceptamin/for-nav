# 경로별 응답 형태·상태 코드. 값의 세부 일치는 test_parity.py가 맡는다.

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app import clock
from app.data.mock import StatRecord
from app.main import app
from app.routers import center
from app.store import CenterStore, MemoryStore, store
from app.store_sqlite import SqliteStore
from app.vocab import LANGS

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


@pytest.fixture(params=["memory", "sqlite"])
def center_store(request, tmp_path, monkeypatch):
    """센터 경로 테스트를 메모리·SQLite 두 저장소에 돌린다(backlog 07)."""
    s: CenterStore = MemoryStore() if request.param == "memory" else SqliteStore(str(tmp_path / "center.db"))
    monkeypatch.setattr(center, "store", s)
    yield s
    s.close()


# 센터 경로 테스트에 붙인다.
both_stores = pytest.mark.usefixtures("center_store")


def test_health():
    assert client.get("/api/health").json() == {"ok": True}


def test_meta():
    assert client.get("/api/meta").json() == {
        "infoDate": "2026-10-24",
        "centerHours": {"openHour": 9, "closeHour": 18, "workdays": [0, 1, 2, 3, 4]},
    }


def test_auth_me_default_off():
    # 센터 직원 로그인(backlog 17)은 기본으로 꺼져 있다. 자세한 경로 테스트는 test_auth.py
    r = client.get("/api/auth/me")
    assert r.status_code == 200
    assert r.json() == {"required": False, "email": None}
    assert client.post("/api/auth/code", json={"email": "a@b.co"}).status_code == 404
    assert client.post("/api/auth/logout").status_code == 204


def test_worker_auth_me_default_off():
    # 근로자 Google 로그인(backlog 21)은 기본으로 꺼져 있다. 자세한 경로 테스트는 test_worker_auth.py
    r = client.get("/api/auth/worker/me")
    assert r.status_code == 200
    assert r.json() == {"required": False, "account": None}
    assert client.post("/api/auth/worker/google", json={"credential": "x"}).status_code == 404
    assert client.post("/api/auth/worker/logout").status_code == 204


def test_triage_readme_examples():
    r = client.post("/api/triage", json=INTAKE)
    assert r.status_code == 200
    assert r.json() == {"department": {"primary": "surgery", "alt": "ortho"}, "missing": []}
    # 가슴 통증도 응급 판정 없이 진료과만 돌려준다(backlog 26)
    chest = client.post("/api/triage", json={**INTAKE, "bodyParts": ["chest"], "symptoms": ["pain"]}).json()
    assert chest == {"department": {"primary": "internal", "alt": "family"}, "missing": []}


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


# 손상 여부(진료과 모델 B 입력, backlog 10)와 지운 응급도 입력(backlog 26) ---------------------------


def test_injury_is_optional_and_absent_when_unset():
    out = client.post("/api/extract", json={"intake": INTAKE}).json()
    assert out["intake"] == INTAKE
    assert client.post("/api/extract", json={"intake": {**INTAKE, "injury": True}}).json()["intake"] == {**INTAKE, "injury": True}


def test_removed_acuity_inputs_are_ignored():
    # 예전 프론트가 보내던 키는 422가 아니라 무시되고 응답에도 없다
    old = {"ageGroup": "45to64", "sex": "female", "painScore": 7, "mental": "alert"}
    assert client.post("/api/extract", json={"intake": {**INTAKE, **old}}).json()["intake"] == INTAKE
    assert client.post("/api/triage", json={**INTAKE, **old}).json() == client.post("/api/triage", json=INTAKE).json()


def test_injury_must_be_bool():
    assert client.post("/api/triage", json={**INTAKE, "injury": "yes"}).status_code == 422


def test_route_readme_example():
    out = client.post("/api/route", json={"workRelated": "unknown", "insurance": "no", "ulsan90": "yes"}).json()
    assert out == {
        "infoDate": "2026-10-24",
        "alsoIndustrial": True,
        "path": "ulsanSupport",
        "institutions": [{"id": "center", "phone": "1577-2818"}, {"id": "ulsan", "phone": "052-235-7100"}],
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
        "requestTypes": ["booking"],
        "coverage": None,
        "insurance": "no",
        "contactMethod": "zalo",
    }
    out = client.post("/api/report/center", json=body).json()
    assert out["ko"].startswith("베트남어 사용 근로자.")
    assert "연락 희망: Zalo." in out["ko"]


def test_center_summary_lists_every_request_type():
    body = {
        "intake": INTAKE,
        "requestTypes": ["booking", "interpret"],
        "coverage": None,
        "insurance": "no",
        "contactMethod": None,
    }
    out = client.post("/api/report/center", json=body).json()
    assert "요청 유형: 예약 지원, 통번역." in out["ko"]
    assert out["native"].endswith("Hỗ trợ đặt lịch, Phiên dịch.")


def test_center_summary_needs_a_request_type():
    body = {"intake": INTAKE, "requestTypes": [], "coverage": None, "insurance": "no", "contactMethod": None}
    assert client.post("/api/report/center", json=body).status_code == 422


@both_stores
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
        "requestTypes": ["booking"],
        "coverage": None,
        "insurance": "no",
        "contactMethod": "zalo",
        "contact": " 010-0000-0000 ",
        "consentedItems": ["증상", "부위"],
        **over,
    }
    return client.post("/api/center/cases", json=body)


@both_stores
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
    # 분야는 접수 규칙으로, 조치·연계 기관은 비어 있다(frontend backlog 41)
    assert (case["category"], case["actions"], case["referredTo"]) == ("medical", [], [])
    assert len(out["nextOpenDate"]) == 10

    # 채팅 토큰(backlog 14)은 전송 응답에만 있고 센터 목록·상세에는 없다.
    assert len(out["chatToken"]) >= 32
    assert "chatToken" not in case

    listed = client.get("/api/center/cases").json()
    assert len(listed) == 25
    assert listed[0]["id"] == case["id"]
    assert client.get(f"/api/center/cases/{case['id']}").json() == case
    assert out["chatToken"] not in client.get("/api/center/cases").text


@both_stores
def test_server_rebuilds_summary():
    case = _send(summaryKo="클라이언트가 보낸 요약").json()["case"]
    assert case["summaryKo"].startswith("베트남어 사용 근로자.")


@both_stores
def test_same_millisecond_ids_get_suffix(monkeypatch):
    fixed = datetime(2026, 10, 26, 10, 0, 0, 123000, tzinfo=clock.SEOUL)
    monkeypatch.setattr(clock, "now", lambda: fixed)
    first = _send().json()["case"]["id"]
    second = _send().json()["case"]["id"]
    assert second == f"{first}-2"


@both_stores
def test_since_filter():
    case = _send().json()["case"]
    assert [c["id"] for c in client.get("/api/center/cases", params={"since": "2000-01-01T00:00:00Z", "status": "new"}).json()][0] == case[
        "id"
    ]
    assert client.get("/api/center/cases", params={"since": case["createdAt"]}).json() == []


@both_stores
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


@both_stores
def test_send_case_default_category():
    assert _send(requestTypes=["policy"]).json()["case"]["category"] == "insurance"
    assert _send(requestTypes=["policy", "interpret"]).json()["case"]["category"] == "medical"
    cost = client.post("/api/route", json={"workRelated": "no", "insurance": "no", "ulsan90": "yes"}).json()
    assert cost["path"] == "ulsanSupport"
    r = _send(coverage=cost)
    assert r.status_code == 201, r.text
    assert r.json()["case"]["category"] == "cost"


@both_stores
def test_patch_category_and_actions():
    """PATCH는 보낸 필드만 바꾼다. 상태만 보내는 옛 요청도 그대로 된다(frontend backlog 41)."""
    r = client.patch("/api/center/cases/C-1024", json={"category": "insurance", "actions": ["referral", "info"]})
    assert r.status_code == 200
    assert (r.json()["category"], r.json()["actions"], r.json()["referredTo"]) == ("insurance", ["info", "referral"], [])
    r = client.patch("/api/center/cases/C-1024", json={"referredTo": ["nhis"]})
    assert (r.status_code, r.json()["referredTo"]) == (200, ["nhis"])
    r = client.patch("/api/center/cases/C-1024", json={"status": "progress"})
    assert r.status_code == 200
    got = client.get("/api/center/cases/C-1024").json()
    assert (got["status"], got["category"], got["actions"], got["referredTo"]) == ("progress", "insurance", ["info", "referral"], ["nhis"])
    # 연계를 빼면 기관도 비운다
    r = client.patch("/api/center/cases/C-1024", json={"actions": ["info"], "referredTo": []})
    assert (r.status_code, r.json()["referredTo"]) == (200, [])


@both_stores
@pytest.mark.parametrize(
    "body",
    [
        {},
        {"status": None},
        {"category": "legal"},
        {"actions": ["call"]},
        {"actions": ["info", "info"]},
        {"actions": ["referral"], "referredTo": ["nhis", "nhis"]},
        {"referredTo": ["nhis"]},
        {"actions": ["info"], "referredTo": ["nhis"]},
    ],
)
def test_patch_rejects_bad_body(body):
    assert client.patch("/api/center/cases/C-1023", json=body).status_code == 422


@both_stores
def test_push_devices_shape():
    # 근로자 앱 푸시 기기 등록·해제(backlog 28). 발송은 tests/test_push.py가 본다
    out = _send().json()
    body = {"deviceToken": "fcm-token", "platform": "android", "notice": "센터에서 새 소식이 있습니다"}
    refs = [{"id": out["case"]["id"], "token": out["chatToken"]}, {"id": "C-0", "token": "x"}]
    r = client.post("/api/center/push-devices", json={**body, "cases": refs})
    assert r.status_code == 200
    assert r.json() == {"cases": [out["case"]["id"]]}
    assert client.post("/api/center/push-devices", json={**body, "cases": []}).status_code == 422
    r = client.post("/api/center/push-devices/remove", json={"deviceToken": "fcm-token"})
    assert (r.status_code, r.content) == (204, b"")


@both_stores
def test_unknown_case_is_404():
    assert client.get("/api/center/cases/C-0").status_code == 404
    assert client.patch("/api/center/cases/C-0", json={"status": "done"}).status_code == 404


@both_stores
def test_send_case_nationality():
    """국적은 두 글자 대문자만 받고, 보내지 않으면 null이다(frontend backlog 42)."""
    assert _send().json()["case"]["nationality"] is None
    case = _send(nationality="KR").json()["case"]
    assert case["nationality"] == "KR"
    assert client.get(f"/api/center/cases/{case['id']}").json()["nationality"] == "KR"
    for bad in ["kr", "KOR", "Korea", "K", ""]:
        assert _send(nationality=bad).status_code == 422, bad


def test_stats_report_cells(monkeypatch):
    """월별 6칸(오래된 달부터, 8~10월 봉우리), 분야·국적 칸. 서버 시각과 원천을 고정한다."""
    fixed = datetime(2026, 10, 26, 10, 0, tzinfo=clock.SEOUL)
    monkeypatch.setattr(clock, "now", lambda: fixed)
    monkeypatch.setattr(center, "store", MemoryStore(fixed))
    out = client.get("/api/center/stats", params={"days": 30}).json()
    months = {c["key"]: c["n"] for c in out["byMonth"]}
    assert list(months) == ["2026-05", "2026-06", "2026-07", "2026-08", "2026-09", "2026-10"]
    # 기간을 30일로 좁혀도 월별은 최근 6개월 전체이고, 합은 원천 329건
    assert sum(months.values()) == 329
    assert min(months["2026-08"], months["2026-09"], months["2026-10"]) > max(months["2026-05"], months["2026-06"], months["2026-07"])

    out = client.get("/api/center/stats", params={"days": 180}).json()
    assert [c["key"] for c in out["byCategory"]] == ["medical", "insurance", "cost"]
    nat = out["byNationality"]
    assert nat[0]["key"] == "ID"
    counts = [c["n"] for c in nat if c["n"] is not None]
    assert counts == sorted(counts, reverse=True)
    # 5건 미만 국적은 가리고 끝에 온다
    assert {c["key"] for c in nat if c["n"] is None} >= {"KG", "TL", "TJ", "MA"}
    assert all(c["n"] is None for c in nat[nat.index(next(c for c in nat if c["n"] is None)) :])
    # 언어는 국적의 모국어: 카자흐어·우즈베크어도 센다
    langs = {c["key"]: c["n"] for c in out["byLanguage"]}
    assert langs["kk"] and langs["uz"] and langs["ru"]


def test_stats_counts_russian_language(monkeypatch, center_store):
    """러시아어 레코드는 byLanguage의 ru 칸에 센다(20개 언어 전부를 센다)."""
    now = clock.now()
    rec = StatRecord(
        date=now,
        district="dong",
        industry="other",
        language="ru",
        insurance="yes",
        after_hours=False,
        request_type="interpret",
        work_related="no",
        category="medical",
        nationality=None,
    )
    monkeypatch.setattr(center_store, "stat_records", [rec] * 5)
    out = client.get("/api/center/stats", params={"days": 30}).json()
    assert {c["key"]: c["n"] for c in out["byLanguage"]}["ru"] == 5
    assert out["byNationality"] == [{"key": "unknown", "n": 5}]


@both_stores
def test_stats_shape():
    out = client.get("/api/center/stats", params={"days": 180}).json()
    # 통계 원천 329건은 최근 6개월에 걸쳐 있어 180일 밖으로 나가는 날이 몇 건 있을 수 있다
    assert 300 <= out["total"] <= 329
    assert [c["key"] for c in out["byIndustry"]] == ["shipbuilding", "autoparts", "chemical", "construction", "other"]
    assert [c["key"] for c in out["byLanguage"]] == LANGS
    assert [c["key"] for c in out["byInsurance"]] == ["yes", "no", "unknown"]
    assert sum(c["n"] for c in out["byAfterHours"]) == out["total"]
    assert 0 <= out["afterHoursRate"] <= 1
    assert client.get("/api/center/stats", params={"days": 7}).status_code == 422


def test_stats_hides_small_cells(monkeypatch, center_store):
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
        category="insurance",
        nationality="VN",
    )
    monkeypatch.setattr(center_store, "stat_records", [rec] * 6 + [StatRecord(**{**rec.__dict__, "industry": "other"})])
    out = client.get("/api/center/stats", params={"days": 30}).json()
    assert out["total"] == 7
    assert {c["key"]: c["n"] for c in out["byIndustry"]} == {
        "shipbuilding": None,
        "autoparts": None,
        "chemical": 6,
        "construction": None,
        "other": None,
    }

    assert {c["key"]: c["n"] for c in out["byCategory"]} == {"medical": None, "insurance": 7, "cost": None}
    assert out["byNationality"] == [{"key": "VN", "n": 7}]

    out = client.get("/api/center/stats", params={"days": 30, "district": "nam"}).json()
    assert out["total"] is None
    assert out["afterHoursRate"] is None
    assert all(c["n"] is None for c in out["byIndustry"])
