# 센터 직원 로그인(backlog 17): 코드 메일, 확인, 세션 쿠키, 보내기 제한, 센터 경로·채팅·통화 보호, 로그에 남지 않는 값.
# 메모리·SQLite 두 저장소에 돌린다. 메일은 FakeMailer, 시각은 clock.now를 바꿔 고정한다.

import logging
from dataclasses import replace
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app import clock
from app.main import app
from app.routers import auth as auth_router
from app.routers import center
from app.settings import settings
from app.store import CenterStore, MemoryStore
from app.store_sqlite import SqliteStore
from tests.fakes import FakeMailer

AT = datetime(2026, 10, 31, 10, 0, 0, tzinfo=clock.SEOUL)
STAFF = "staff@example.org"
BASE = "https://testserver"

INTAKE = {
    "id": "in-test",
    "language": "vi",
    "bodyParts": ["hand"],
    "symptoms": ["cut"],
    "freeText": "",
    "onset": None,
    "workRelated": None,
    "workType": None,
    "industry": None,
    "district": None,
    "createdAt": "2026-10-26T01:00:00.000Z",
}
NEW_CASE = {
    "intake": INTAKE,
    "emergencyFlag": False,
    "requestType": "booking",
    "coverage": None,
    "insurance": "yes",
    "contactMethod": None,
    "contact": None,
    "consentedItems": [],
}


class Clock:
    def __init__(self) -> None:
        self.now = AT

    def advance(self, **kw: float) -> None:
        self.now += timedelta(**kw)


@pytest.fixture
def clk(monkeypatch) -> Clock:
    c = Clock()
    monkeypatch.setattr(clock, "now", lambda: c.now)
    return c


@pytest.fixture(params=["memory", "sqlite"])
def store(request, tmp_path, monkeypatch):
    s: CenterStore = MemoryStore() if request.param == "memory" else SqliteStore(str(tmp_path / "center.db"))
    s.add_staff(STAFF, AT)
    monkeypatch.setattr(center, "store", s)
    monkeypatch.setattr(auth_router, "store", s)
    yield s
    s.close()


@pytest.fixture
def mailer(monkeypatch) -> FakeMailer:
    m = FakeMailer()
    monkeypatch.setattr(app.state, "mail", m)
    return m


def use_settings(monkeypatch, **kw) -> None:
    s = replace(settings, **kw)
    monkeypatch.setattr(center, "settings", s)
    monkeypatch.setattr(auth_router, "settings", s)


@pytest.fixture
def client(store, mailer, clk, monkeypatch):
    use_settings(monkeypatch, center_auth="email", db_path="center.db")
    with TestClient(app, base_url=BASE) as c:
        yield c


def login(client: TestClient, mailer: FakeMailer, email: str = STAFF) -> str:
    assert client.post("/api/auth/code", json={"email": email}).status_code == 202
    r = client.post("/api/auth/verify", json={"email": email, "code": mailer.last_code()})
    assert r.status_code == 200
    return r.cookies["fornav_center"]


def close_code(client: TestClient, path: str, headers: dict[str, str] | None = None) -> int:
    with client.websocket_connect(path, headers=headers or {}) as ws, pytest.raises(WebSocketDisconnect) as exc:
        ws.receive_json()
    return exc.value.code


# ---------------------------------------------------------------------------
# 코드 메일과 확인
# ---------------------------------------------------------------------------
def test_unregistered_email_gets_same_answer_and_no_mail(client, mailer):
    r = client.post("/api/auth/code", json={"email": "who@example.org"})
    assert r.status_code == 202
    assert mailer.sent == []


def test_registered_email_gets_six_digit_code(client, mailer):
    r = client.post("/api/auth/code", json={"email": "  Staff@Example.ORG "})
    assert r.status_code == 202
    [(to, subject, text)] = mailer.sent
    assert (to, subject) == (STAFF, "for-nav 센터 로그인 코드")
    assert len(mailer.last_code()) == 6 and "10분" in text


@pytest.mark.parametrize("body", [{"email": "not-an-email"}, {"email": ""}, {}])
def test_bad_email_is_422(client, body):
    assert client.post("/api/auth/code", json=body).status_code == 422


def test_verify_sets_session_cookie(client, mailer):
    client.post("/api/auth/code", json={"email": STAFF})
    r = client.post("/api/auth/verify", json={"email": STAFF, "code": mailer.last_code()})
    assert r.status_code == 200
    assert r.json() == {"required": True, "email": STAFF}
    cookie = r.headers["set-cookie"]
    for part in ("fornav_center=", "HttpOnly", "Max-Age=2592000", "Path=/", "SameSite=lax", "Secure"):
        assert part in cookie
    assert client.get("/api/auth/me").json() == {"required": True, "email": STAFF}


def test_cookie_without_secure_for_local_http(store, mailer, clk, monkeypatch):
    use_settings(monkeypatch, center_auth="email", db_path="center.db", center_cookie_secure=False)
    with TestClient(app) as c:
        c.post("/api/auth/code", json={"email": STAFF})
        r = c.post("/api/auth/verify", json={"email": STAFF, "code": mailer.last_code()})
    assert r.status_code == 200
    assert "Secure" not in r.headers["set-cookie"]


def test_wrong_code_five_times_kills_code(client, mailer):
    client.post("/api/auth/code", json={"email": STAFF})
    code = mailer.last_code()
    wrong = "000000" if code != "000000" else "111111"
    for _ in range(5):
        assert client.post("/api/auth/verify", json={"email": STAFF, "code": wrong}).status_code == 401
    r = client.post("/api/auth/verify", json={"email": STAFF, "code": code})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "UNAUTHORIZED"


def test_code_expires_after_ten_minutes(client, mailer, clk):
    client.post("/api/auth/code", json={"email": STAFF})
    clk.advance(minutes=10)
    assert client.post("/api/auth/verify", json={"email": STAFF, "code": mailer.last_code()}).status_code == 401


def test_new_code_replaces_old_one(client, mailer, clk):
    client.post("/api/auth/code", json={"email": STAFF})
    old = mailer.last_code()
    clk.advance(seconds=61)
    client.post("/api/auth/code", json={"email": STAFF})
    new = mailer.last_code()
    if old != new:
        assert client.post("/api/auth/verify", json={"email": STAFF, "code": old}).status_code == 401
    assert client.post("/api/auth/verify", json={"email": STAFF, "code": new}).status_code == 200


def test_code_works_once(client, mailer):
    client.post("/api/auth/code", json={"email": STAFF})
    code = mailer.last_code()
    assert client.post("/api/auth/verify", json={"email": STAFF, "code": code}).status_code == 200
    assert client.post("/api/auth/verify", json={"email": STAFF, "code": code}).status_code == 401


# ---------------------------------------------------------------------------
# 보내기 제한
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("email", [STAFF, "who@example.org"])
def test_resend_within_60s_is_429_for_any_email(client, clk, email):
    assert client.post("/api/auth/code", json={"email": email}).status_code == 202
    clk.advance(seconds=59)
    r = client.post("/api/auth/code", json={"email": email})
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "RATE_LIMITED"


def test_six_requests_in_an_hour_is_429(client, clk):
    for _ in range(5):
        assert client.post("/api/auth/code", json={"email": STAFF}).status_code == 202
        clk.advance(seconds=61)
    assert client.post("/api/auth/code", json={"email": STAFF}).status_code == 429
    clk.advance(minutes=60)
    assert client.post("/api/auth/code", json={"email": STAFF}).status_code == 202


def test_global_limit_counts_sent_mail_only(client, store, mailer):
    others = [f"s{i}@example.org" for i in range(30)]
    for email in others:
        store.add_staff(email, AT)
        assert client.post("/api/auth/code", json={"email": email}).status_code == 202
    assert len(mailer.sent) == 30
    # 31번째 실제 발송은 막힌다. 등록되지 않은 이메일은 메일을 보내지 않으므로 같은 202다.
    assert client.post("/api/auth/code", json={"email": STAFF}).status_code == 429
    assert client.post("/api/auth/code", json={"email": "who@example.org"}).status_code == 202


def test_mail_failure_still_202_and_logs_no_email(client, monkeypatch, caplog):
    monkeypatch.setattr(app.state, "mail", FakeMailer(fail=True))
    with caplog.at_level(logging.INFO):
        r = client.post("/api/auth/code", json={"email": STAFF})
    assert r.status_code == 202
    assert "로그인 코드 메일 실패 HTTP 500" in caplog.text
    assert STAFF not in caplog.text


# ---------------------------------------------------------------------------
# 세션
# ---------------------------------------------------------------------------
def test_logout_ends_session(client, mailer):
    token = login(client, mailer)
    r = client.post("/api/auth/logout")
    assert r.status_code == 204
    assert 'fornav_center=""' in r.headers["set-cookie"] or "Max-Age=0" in r.headers["set-cookie"]
    client.cookies.set("fornav_center", token)
    assert client.get("/api/auth/me").json() == {"required": True, "email": None}
    assert client.get("/api/center/cases").status_code == 401


def test_logout_without_session_is_204(client):
    assert client.post("/api/auth/logout").status_code == 204


def test_session_expires_after_30_days(client, mailer, clk):
    login(client, mailer)
    clk.advance(days=29, hours=23)
    assert client.get("/api/center/cases").status_code == 200
    clk.advance(hours=1)
    assert client.get("/api/center/cases").status_code == 401


def test_removed_staff_is_logged_out(client, mailer, store):
    login(client, mailer)
    assert store.remove_staff(STAFF)
    assert client.get("/api/center/cases").status_code == 401
    assert client.get("/api/auth/me").json()["email"] is None


def test_reset_keeps_session(client, mailer):
    login(client, mailer)
    assert client.post("/api/center/reset").status_code == 204
    assert client.get("/api/center/cases").status_code == 200


# ---------------------------------------------------------------------------
# 센터 경로
# ---------------------------------------------------------------------------
CENTER_READ_WRITE = [
    ("get", "/api/center/cases", None),
    ("get", "/api/center/cases/C-1001", None),
    ("patch", "/api/center/cases/C-1001", {"status": "progress"}),
    ("post", "/api/center/reset", None),
    ("get", "/api/center/stats", None),
]


@pytest.mark.parametrize(("method", "path", "body"), CENTER_READ_WRITE)
def test_center_routes_need_session(client, mailer, method, path, body):
    r = client.request(method, path, json=body)
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "UNAUTHORIZED"
    login(client, mailer)
    assert client.request(method, path, json=body).status_code in (200, 204)


def test_worker_can_send_case_without_session(client):
    r = client.post("/api/center/cases", json=NEW_CASE)
    assert r.status_code == 201
    assert r.json()["chatToken"]


# ---------------------------------------------------------------------------
# 채팅·통화 role=center
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("kind", ["chat", "call"])
def test_center_socket_needs_session(client, mailer, kind):
    path = f"/api/center/cases/C-1001/{kind}?role=center"
    assert close_code(client, path) == 4401
    token = login(client, mailer)
    with client.websocket_connect(path, headers={"cookie": f"fornav_center={token}", "origin": BASE}) as ws:
        assert ws.receive_json()["type"] in ("history", "joined")


@pytest.mark.parametrize("kind", ["chat", "call"])
def test_center_socket_from_other_site_is_4403(client, mailer, kind):
    token = login(client, mailer)
    headers = {"cookie": f"fornav_center={token}", "origin": "https://evil.example"}
    assert close_code(client, f"/api/center/cases/C-1001/{kind}?role=center", headers) == 4403


def test_worker_socket_still_uses_token_only(client):
    out = client.post("/api/center/cases", json=NEW_CASE).json()
    case_id, token = out["case"]["id"], out["chatToken"]
    with client.websocket_connect(f"/api/center/cases/{case_id}/chat?role=worker&token={token}") as ws:
        assert ws.receive_json()["type"] == "history"
    assert close_code(client, f"/api/center/cases/{case_id}/chat?role=worker&token=wrong") == 4403


# ---------------------------------------------------------------------------
# 로그인을 끈 서버(기본값)
# ---------------------------------------------------------------------------
def test_auth_off_keeps_center_open(store, mailer, clk):
    with TestClient(app) as c:
        assert c.get("/api/auth/me").json() == {"required": False, "email": None}
        assert c.post("/api/auth/code", json={"email": STAFF}).status_code == 404
        assert c.post("/api/auth/verify", json={"email": STAFF, "code": "123456"}).status_code == 404
        assert c.get("/api/center/cases").status_code == 200
        with c.websocket_connect("/api/center/cases/C-1001/chat?role=center") as ws:
            assert ws.receive_json()["type"] == "history"
    assert mailer.sent == []


# ---------------------------------------------------------------------------
# 로그
# ---------------------------------------------------------------------------
def test_logs_have_no_email_code_or_token(client, mailer, caplog):
    with caplog.at_level(logging.INFO):
        token = login(client, mailer)
        client.get("/api/center/cases")
        with client.websocket_connect("/api/center/cases/C-1001/chat?role=center", headers={"cookie": f"fornav_center={token}"}) as ws:
            ws.receive_json()
        client.post("/api/auth/logout")
    assert "/api/auth/verify" in caplog.text
    for secret in (STAFF, mailer.last_code(), token):
        assert secret not in caplog.text


# ---------------------------------------------------------------------------
# 직원 관리 명령줄(scripts/staff.py)
# ---------------------------------------------------------------------------
def test_staff_cli(tmp_path, monkeypatch, capsys):
    from scripts import staff

    path = str(tmp_path / "center.db")
    monkeypatch.setattr(staff, "settings", replace(settings, db_path=path))
    assert staff.main(["add", " New@Example.ORG "]) == 0
    assert staff.main(["add", "new@example.org"]) == 0
    assert staff.main(["add", "not-an-email"]) == 2
    assert staff.main(["list"]) == 0
    assert staff.main(["remove", "new@example.org"]) == 0
    assert staff.main(["remove", "new@example.org"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out == ["추가했다", "이미 있다", "new@example.org", "지웠다(세션도 끝났다)", "없는 이메일이다"]


def test_staff_cli_needs_db_path(monkeypatch):
    from scripts import staff

    monkeypatch.setattr(staff, "settings", replace(settings, db_path=""))
    assert staff.main(["list"]) == 2
