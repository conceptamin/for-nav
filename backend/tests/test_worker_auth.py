# 근로자 Google 로그인(backlog 21): ID 토큰 확인, 근로자 세션 쿠키, 센터 요청 보호, 센터 세션과의 분리, 로그에 남지 않는 값.
# 경로 테스트는 메모리·SQLite 두 저장소에 돌린다. 검증은 FakeVerifier, 시각은 clock.now를 바꿔 고정한다.
# GoogleVerifier는 테스트에서 만든 서명 키와 가짜 공개 키 응답으로 네트워크 없이 확인한다.

import json
import logging
import re
import time
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from fastapi.testclient import TestClient
from google.auth import crypt, jwt

from app import auth, clock
from app.google_id import GoogleIdError, GoogleVerifier
from app.main import app
from app.routers import auth as auth_router
from app.routers import center
from app.settings import settings
from app.store import CenterStore, MemoryStore
from app.store_sqlite import SqliteStore
from tests.fakes import FakeVerifier
from tests.test_auth import AT, NEW_CASE, STAFF, Clock

BASE = "https://testserver"
TOKEN_A = "id-token-a"
TOKEN_B = "id-token-b"
SUB_A = "109876543210987654321"
SUB_B = "100000000000000000001"


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
def verifier(monkeypatch) -> FakeVerifier:
    v = FakeVerifier({TOKEN_A: SUB_A, TOKEN_B: SUB_B})
    monkeypatch.setattr(app.state, "google_id", v)
    return v


def use_settings(monkeypatch, **kw) -> None:
    s = replace(settings, **kw)
    monkeypatch.setattr(center, "settings", s)
    monkeypatch.setattr(auth_router, "settings", s)


@pytest.fixture
def client(store, verifier, clk, monkeypatch):
    use_settings(monkeypatch, worker_auth="google", google_client_id="client-id.apps.googleusercontent.com", db_path="center.db")
    with TestClient(app, base_url=BASE) as c:
        yield c


def login(client: TestClient, credential: str = TOKEN_A) -> dict:
    r = client.post("/api/auth/worker/google", json={"credential": credential})
    assert r.status_code == 200
    return r.json()


# ---------------------------------------------------------------------------
# 로그인과 세션
# ---------------------------------------------------------------------------
def test_good_token_sets_worker_cookie(client):
    r = client.post("/api/auth/worker/google", json={"credential": TOKEN_A})
    assert r.status_code == 200
    body = r.json()
    assert body["required"] is True
    assert re.fullmatch(r"[0-9a-f]{32}", body["account"])
    cookie = r.headers["set-cookie"]
    assert cookie.startswith("fornav_worker=")
    for part in ("HttpOnly", "SameSite=lax", "Max-Age=2592000", "Path=/", "Secure"):
        assert part.lower() in cookie.lower()
    assert client.get("/api/auth/worker/me").json() == body


def test_account_key_is_stable_per_sub(client):
    a1 = login(client, TOKEN_A)["account"]
    a2 = login(client, TOKEN_A)["account"]
    b = login(client, TOKEN_B)["account"]
    assert a1 == a2 == auth.account_key(SUB_A)
    assert b != a1
    assert SUB_A not in a1


def test_cookie_without_secure_for_local_http(store, verifier, clk, monkeypatch):
    use_settings(monkeypatch, worker_auth="google", google_client_id="x", db_path="center.db", center_cookie_secure=False)
    with TestClient(app, base_url=BASE) as c:
        r = c.post("/api/auth/worker/google", json={"credential": TOKEN_A})
    assert "secure" not in r.headers["set-cookie"].lower()


def test_bad_token_is_401_without_cookie(client, verifier):
    r = client.post("/api/auth/worker/google", json={"credential": "not-a-google-token"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "UNAUTHORIZED"
    assert "set-cookie" not in r.headers
    assert verifier.seen == ["not-a-google-token"]


@pytest.mark.parametrize("body", [{}, {"credential": ""}, {"credential": "   "}, {"credential": "x" * 4097}])
def test_bad_body_is_422(client, verifier, body):
    assert client.post("/api/auth/worker/google", json=body).status_code == 422
    assert verifier.seen == []


def test_me_without_session(client):
    assert client.get("/api/auth/worker/me").json() == {"required": True, "account": None}


def test_logout_ends_session(client):
    login(client)
    token = client.cookies["fornav_worker"]
    r = client.post("/api/auth/worker/logout")
    assert r.status_code == 204
    assert "fornav_worker" in r.headers["set-cookie"]
    client.cookies.set("fornav_worker", token)
    assert client.get("/api/auth/worker/me").json() == {"required": True, "account": None}


def test_logout_without_session_is_204(client):
    assert client.post("/api/auth/worker/logout").status_code == 204


def test_session_expires_after_30_days(client, clk):
    login(client)
    clk.advance(days=30, seconds=-1)
    assert client.get("/api/auth/worker/me").json()["account"] is not None
    clk.advance(seconds=1)
    assert client.get("/api/auth/worker/me").json()["account"] is None


def test_store_keeps_only_hashes(client, store):
    login(client)
    token = client.cookies["fornav_worker"]
    # 쿠키 값 그대로는 찾을 수 없고 해시로만 찾는다
    assert store.worker_account(token, clock.now()) is None
    assert store.worker_account(auth.hash_secret(token), clock.now()) == auth.account_key(SUB_A)


def test_reset_keeps_worker_sessions(client, store):
    account = login(client)["account"]
    store.reset()
    assert client.get("/api/auth/worker/me").json()["account"] == account


# ---------------------------------------------------------------------------
# 경로 보호
# ---------------------------------------------------------------------------
def test_center_request_needs_worker_session(client):
    assert client.post("/api/center/cases", json=NEW_CASE).status_code == 401
    login(client)
    assert client.post("/api/center/cases", json=NEW_CASE).status_code == 201


def test_guidance_paths_stay_open(client):
    # 응급 판정·안내는 로그인에 묶지 않는다(backlog 21 결정 6). 쿠키 없이 지금과 같은 응답이다
    intake = NEW_CASE["intake"]
    assert client.post("/api/extract", json={"intake": intake}).status_code == 200
    assert client.post("/api/triage", json=intake).status_code == 200
    assert client.post("/api/route", json={"workRelated": "yes", "insurance": "yes"}).status_code == 200
    assert client.post("/api/report/center", json=NEW_CASE).status_code == 200
    helper = {"intake": intake, "department": "surgery", "firstVisit": True, "lang": "vi"}
    assert client.post("/api/visit-helper", json=helper).status_code == 200


def test_center_cookie_does_not_open_worker_paths_and_back(client, store, monkeypatch):
    use_settings(monkeypatch, worker_auth="google", google_client_id="x", db_path="center.db", center_auth="email")
    center_token = "center-session-token"
    store.add_session(auth.hash_secret(center_token), STAFF, AT, AT + timedelta(days=30))
    client.cookies.set("fornav_center", center_token)
    assert client.get("/api/center/cases").status_code == 200
    assert client.post("/api/center/cases", json=NEW_CASE).status_code == 401
    assert client.get("/api/auth/worker/me").json()["account"] is None

    client.cookies.clear()
    login(client)
    assert client.get("/api/center/cases").status_code == 401
    assert client.get("/api/auth/me").json()["email"] is None


# ---------------------------------------------------------------------------
# 꺼져 있을 때(기본값)
# ---------------------------------------------------------------------------
def test_off_by_default(store, verifier, clk):
    with TestClient(app, base_url=BASE) as c:
        assert c.get("/api/auth/worker/me").json() == {"required": False, "account": None}
        assert c.post("/api/auth/worker/google", json={"credential": TOKEN_A}).status_code == 404
        assert c.post("/api/center/cases", json=NEW_CASE).status_code == 201
    assert verifier.seen == []


# ---------------------------------------------------------------------------
# 로그
# ---------------------------------------------------------------------------
def test_logs_have_no_token_sub_or_account(client, caplog):
    with caplog.at_level(logging.DEBUG):
        r = client.post("/api/auth/worker/google", json={"credential": "bad-token-value"})
        assert r.status_code == 401
        account = login(client)["account"]
        token = client.cookies["fornav_worker"]
        client.get("/api/auth/worker/me")
        client.post("/api/center/cases", json=NEW_CASE)
        client.post("/api/auth/worker/logout")
    assert "Google 로그인 확인 실패 ValueError" in caplog.text
    for secret in ("bad-token-value", TOKEN_A, SUB_A, account, token):
        assert secret not in caplog.text


# ---------------------------------------------------------------------------
# GoogleVerifier: 테스트에서 만든 서명 키와 가짜 공개 키 응답(네트워크 없음)
# ---------------------------------------------------------------------------
CLIENT_ID = "client-id.apps.googleusercontent.com"
KID = "test-key"


@pytest.fixture(scope="module")
def keypair() -> tuple[bytes, bytes]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test")])
    now = datetime.now(UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(1)
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    private_pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    return private_pem, cert.public_bytes(serialization.Encoding.PEM)


def certs_transport(cert_pem: bytes, status: int = 200):
    def transport(url: str, method: str = "GET", **kw):
        return SimpleNamespace(status=status, data=json.dumps({KID: cert_pem.decode()}).encode(), headers={})

    return transport


def sign(private_pem: bytes, **claims) -> str:
    now = int(time.time())
    payload = {"iss": "https://accounts.google.com", "aud": CLIENT_ID, "sub": SUB_A, "iat": now, "exp": now + 3600, **claims}
    signer = crypt.RSASigner.from_string(private_pem, key_id=KID)
    return jwt.encode(signer, payload).decode()


def test_verifier_accepts_good_token(keypair):
    private_pem, cert_pem = keypair
    v = GoogleVerifier(CLIENT_ID, certs_transport(cert_pem))
    assert v.verify(sign(private_pem)) == SUB_A
    assert v.verify(sign(private_pem, iss="accounts.google.com")) == SUB_A


@pytest.mark.parametrize(
    "claims",
    [
        {"aud": "other-client.apps.googleusercontent.com"},
        {"iss": "https://evil.example.com"},
        {"iat": int(time.time()) - 7200, "exp": int(time.time()) - 3600},
        {"sub": ""},
    ],
)
def test_verifier_rejects_bad_claims(keypair, claims):
    private_pem, cert_pem = keypair
    v = GoogleVerifier(CLIENT_ID, certs_transport(cert_pem))
    with pytest.raises(GoogleIdError):
        v.verify(sign(private_pem, **claims))


def test_verifier_rejects_other_signer(keypair):
    _, cert_pem = keypair
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    other_pem = other.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    v = GoogleVerifier(CLIENT_ID, certs_transport(cert_pem))
    with pytest.raises(GoogleIdError):
        v.verify(sign(other_pem))


@pytest.mark.parametrize("credential", ["not-a-jwt", "a.b.c"])
def test_verifier_rejects_garbage(keypair, credential):
    _, cert_pem = keypair
    with pytest.raises(GoogleIdError):
        GoogleVerifier(CLIENT_ID, certs_transport(cert_pem)).verify(credential)


def test_verifier_fails_when_certs_unreachable(keypair):
    private_pem, cert_pem = keypair
    v = GoogleVerifier(CLIENT_ID, certs_transport(cert_pem, status=503))
    with pytest.raises(GoogleIdError):
        v.verify(sign(private_pem))
