# 근로자 앱 푸시(backlog 28): 기기 등록·해제, 센터 채팅 글·상태 변경 때 발송, 60초 제한, 채팅을 보고 있으면 건너뛰기,
# 메시지 모양, 없는 토큰 지우기, 발송 실패가 응답을 바꾸지 않음, 30일 정리, PUSH=off, 로그에 남지 않는 값.
# 경로 테스트는 메모리·SQLite 두 저장소에 돌리고 가짜 발송기(FakePushSender)만 쓴다(네트워크 없음).
# FcmSender는 테스트에서 만든 서비스 계정 키와 가짜 전송(httpx.MockTransport)으로 요청 모양만 확인한다.

import asyncio
import base64
import json
import logging
from dataclasses import replace
from pathlib import Path

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from google.auth import crypt
from google.auth import jwt as google_jwt

from app import clock
from app.main import app
from app.push import (
    FCM_SCOPE,
    PUSH_TITLE,
    FcmSender,
    PushError,
    PushNotifier,
    load_service_account,
    make_push_sender,
)
from app.routers import center
from app.settings import load_settings, settings
from app.store import CenterStore, MemoryStore
from app.store_sqlite import SqliteStore
from tests.fakes import FakePushSender
from tests.test_auth import Clock
from tests.test_chat import send_case, url

NOTICE = "Có tin mới từ trung tâm"
DEVICE_A = "fcm-device-token-a:APA91b-MARKER-device-a"
DEVICE_B = "fcm-device-token-b:APA91b-MARKER-device-b"
MARKER = "MARKER-push-message-do-not-log"


@pytest.fixture
def clk(monkeypatch) -> Clock:
    c = Clock()
    monkeypatch.setattr(clock, "now", lambda: c.now)
    return c


@pytest.fixture(params=["memory", "sqlite"])
def store(request, tmp_path, monkeypatch):
    s: CenterStore = MemoryStore() if request.param == "memory" else SqliteStore(str(tmp_path / "center.db"))
    monkeypatch.setattr(center, "store", s)
    yield s
    s.close()


@pytest.fixture
def sender() -> FakePushSender:
    return FakePushSender()


@pytest.fixture
def notifier(sender, monkeypatch) -> PushNotifier:
    n = PushNotifier(sender)
    monkeypatch.setattr(app.state, "push", n)
    return n


@pytest.fixture
def client(store, notifier, clk):
    # `with`로 열어 백그라운드 발송이 같은 이벤트 루프에서 돈다.
    with TestClient(app) as c:
        yield c


def drain(client: TestClient) -> None:
    client.portal.call(app.state.push.drain)


def register(client: TestClient, device: str, *refs: tuple[str, str], notice: str = NOTICE, platform: str = "android") -> list[str]:
    body = {"deviceToken": device, "platform": platform, "notice": notice, "cases": [{"id": i, "token": t} for i, t in refs]}
    r = client.post("/api/center/push-devices", json=body)
    assert r.status_code == 200
    return r.json()["cases"]


def center_says(client: TestClient, case_id: str, text: str = "확인했습니다") -> dict:
    with client.websocket_connect(url(case_id, "center")) as ws:
        ws.receive_json()
        ws.send_json({"type": "message", "text": text})
        frame = ws.receive_json()
    drain(client)
    return frame


def patch_status(client: TestClient, case_id: str, status: str) -> dict:
    r = client.patch(f"/api/center/cases/{case_id}", json={"status": status})
    assert r.status_code == 200
    drain(client)
    return r.json()


# ---------------------------------------------------------------------------
# 등록·해제
# ---------------------------------------------------------------------------
def test_register_binds_only_owned_cases(client, store, clk):
    a, token_a = send_case(client)
    b, _ = send_case(client)
    # 틀린 토큰·없는 사례·토큰 없는 mock 사례는 오류 없이 빠지고, 같은 사례를 두 번 보내도 한 번만 묶인다
    assert register(client, DEVICE_A, (a, token_a), (b, "wrong"), ("C-0", token_a), ("C-1001", "x"), (a, token_a)) == [a]
    assert [(d.device_token, d.platform, d.notice) for d in store.push_devices(a, clk.now)] == [(DEVICE_A, "android", NOTICE)]
    assert store.push_devices(b, clk.now) == []

    # 다시 보내면 platform·notice·갱신 시각만 바뀐다
    clk.advance(minutes=5)
    assert register(client, DEVICE_A, (a, token_a), notice="새 소식", platform="ios") == [a]
    rows = store.push_devices(a, clk.now)
    assert [(d.device_token, d.platform, d.notice, d.updated_at) for d in rows] == [(DEVICE_A, "ios", "새 소식", clock.iso_utc(clk.now))]


def test_register_with_only_wrong_tokens_is_empty_200(client):
    a, _ = send_case(client)
    assert register(client, DEVICE_A, (a, "wrong"), ("C-0", "x")) == []


@pytest.mark.parametrize(
    "change",
    [
        {"cases": []},
        {"cases": [{"id": f"C-{n}", "token": "t"} for n in range(21)]},
        {"cases": [{"id": "C-1"}]},
        {"notice": "가" * 81},
        {"notice": ""},
        {"notice": "   "},
        {"notice": "센터에서\n새 소식"},
        {"notice": "센터\x07소식"},
        {"notice": "센터\x85소식"},
        {"platform": "web"},
        {"deviceToken": ""},
        {"deviceToken": "x" * 4097},
        {"notice": None},
    ],
)
def test_register_bad_body_is_422(client, change):
    body = {"deviceToken": DEVICE_A, "platform": "android", "notice": NOTICE, "cases": [{"id": "C-1", "token": "t"}], **change}
    assert client.post("/api/center/push-devices", json=body).status_code == 422


def test_register_accepts_limits(client):
    a, token_a = send_case(client)
    refs = [(a, token_a)] + [(f"C-{n}", "t") for n in range(19)]
    assert register(client, "x" * 4096, *refs, notice="가" * 80) == [a]


def test_remove_unbinds_every_case_of_the_device(client, store, clk):
    a, token_a = send_case(client)
    b, token_b = send_case(client)
    register(client, DEVICE_A, (a, token_a), (b, token_b))
    register(client, DEVICE_B, (a, token_a))

    assert client.post("/api/center/push-devices/remove", json={"deviceToken": DEVICE_A}).status_code == 204
    assert [d.device_token for d in store.push_devices(a, clk.now)] == [DEVICE_B]
    assert store.push_devices(b, clk.now) == []
    # 없는 토큰도 204
    assert client.post("/api/center/push-devices/remove", json={"deviceToken": "never-registered"}).status_code == 204
    assert client.post("/api/center/push-devices/remove", json={}).status_code == 422


def test_reset_clears_bindings(client, store, clk, sender):
    a, token_a = send_case(client)
    register(client, DEVICE_A, (a, token_a))
    assert client.post("/api/center/reset").status_code == 204
    assert store.push_devices(a, clk.now) == []
    # mock 사례에 다시 써도 묶인 기기가 없다
    center_says(client, "C-1001")
    assert sender.sent == []


def test_bindings_expire_30_days_after_last_registration(client, store, clk, sender):
    a, token_a = send_case(client)
    register(client, DEVICE_A, (a, token_a))
    clk.advance(days=29)
    register(client, DEVICE_A, (a, token_a))  # 앱을 다시 열면 다시 등록해 30일이 다시 시작된다
    clk.advance(days=29, hours=23)
    assert len(store.push_devices(a, clk.now)) == 1
    clk.advance(hours=1)
    center_says(client, a)
    assert sender.sent == []
    assert store.push_devices(a, clk.now) == []


# ---------------------------------------------------------------------------
# 발송 시점
# ---------------------------------------------------------------------------
def test_center_message_sends_once_per_device_worker_message_does_not(client, sender, monkeypatch):
    a, token_a = send_case(client)
    register(client, DEVICE_A, (a, token_a))
    register(client, DEVICE_B, (a, token_a), platform="ios")

    # 근로자 글은 보내지 않는다(근로자가 붙어 있어서가 아니라 보낸 사람이 근로자라서인지 보려고 접속 확인을 끈다)
    monkeypatch.setattr(app.state.chat, "has_worker", lambda case_id: False)
    with client.websocket_connect(url(a, token=token_a)) as ws:
        ws.receive_json()
        ws.send_json({"type": "message", "text": "도와주세요"})
        ws.receive_json()
    drain(client)
    assert sender.sent == []

    center_says(client, a)
    assert sorted((s["token"], s["platform"]) for s in sender.sent) == [(DEVICE_A, "android"), (DEVICE_B, "ios")]


def test_status_change_sends_same_status_does_not(client, sender, clk):
    a, token_a = send_case(client)
    register(client, DEVICE_A, (a, token_a))

    assert patch_status(client, a, "progress")["status"] == "progress"
    assert len(sender.sent) == 1
    clk.advance(seconds=61)
    patch_status(client, a, "progress")
    assert len(sender.sent) == 1
    patch_status(client, a, "done")
    assert len(sender.sent) == 2
    # 없는 사례는 지금처럼 404이고 보내지 않는다
    assert client.patch("/api/center/cases/C-0", json={"status": "done"}).status_code == 404


def test_second_event_within_60s_is_skipped(client, sender, clk):
    a, token_a = send_case(client)
    register(client, DEVICE_A, (a, token_a))

    center_says(client, a, "하나")
    clk.advance(seconds=30)
    center_says(client, a, "둘")
    clk.advance(seconds=29)
    patch_status(client, a, "progress")  # 상태 변경도 같은 사례 제한을 탄다
    assert len(sender.sent) == 1
    clk.advance(seconds=2)  # 첫 발송 뒤 61초
    center_says(client, a, "셋")
    assert len(sender.sent) == 2


def test_throttle_is_per_case(client, sender):
    a, token_a = send_case(client)
    b, token_b = send_case(client)
    register(client, DEVICE_A, (a, token_a), (b, token_b))
    center_says(client, a)
    center_says(client, b)
    assert [s["data"]["caseId"] for s in sender.sent] == [a, b]


def test_skipped_while_worker_is_in_the_chat(client, sender):
    a, token_a = send_case(client)
    register(client, DEVICE_A, (a, token_a))

    with client.websocket_connect(url(a, token=token_a)) as worker:
        worker.receive_json()
        center_says(client, a)
        worker.receive_json()
        assert client.patch(f"/api/center/cases/{a}", json={"status": "progress"}).status_code == 200
        drain(client)
    assert sender.sent == []

    # 근로자가 나간 뒤에는 보낸다(건너뛴 사건은 60초 제한을 세지 않는다)
    center_says(client, a)
    assert len(sender.sent) == 1


def test_message_has_only_title_notice_and_case_id(client, sender):
    a, token_a = send_case(client)
    register(client, DEVICE_A, (a, token_a))
    center_says(client, a, MARKER)

    assert sender.sent == [
        {
            "token": DEVICE_A,
            "platform": "android",
            "title": "for nav",
            "body": NOTICE,
            "data": {"kind": "center", "caseId": a},
            "collapse": a,
        }
    ]
    assert PUSH_TITLE == "for nav"
    assert MARKER not in json.dumps(sender.sent, ensure_ascii=False)
    patch_status(client, a, "done")
    assert "done" not in json.dumps(sender.sent)


# ---------------------------------------------------------------------------
# 실패
# ---------------------------------------------------------------------------
def test_unregistered_token_is_removed(client, store, clk, notifier):
    notifier.sender = FakePushSender(unregistered=[DEVICE_B])
    a, token_a = send_case(client)
    b, token_b = send_case(client)
    register(client, DEVICE_A, (a, token_a))
    register(client, DEVICE_B, (a, token_a), (b, token_b))

    center_says(client, a)
    assert [s["token"] for s in notifier.sender.sent] == [DEVICE_A]
    # 없는 토큰은 묶인 모든 사례에서 지운다
    assert [d.device_token for d in store.push_devices(a, clk.now)] == [DEVICE_A]
    assert store.push_devices(b, clk.now) == []

    clk.advance(seconds=61)
    attempts = len(notifier.sender.attempts)
    center_says(client, a)
    assert notifier.sender.attempts[attempts:] == [DEVICE_A]


@pytest.mark.parametrize(
    "fake", [FakePushSender(fail=PushError("HTTP 500")), FakePushSender(fail=RuntimeError("boom")), FakePushSender(hang=True)]
)
def test_failure_or_timeout_does_not_change_responses(client, store, clk, notifier, fake, caplog):
    caplog.set_level(logging.INFO, logger="app")
    notifier.sender = fake
    notifier.timeout_s = 0.05
    a, token_a = send_case(client)
    register(client, DEVICE_A, (a, token_a))

    frame = center_says(client, a)
    assert (frame["type"], frame["message"]["id"], frame["message"]["from"]) == ("message", "m-1", "center")
    clk.advance(seconds=61)
    assert patch_status(client, a, "progress")["status"] == "progress"
    # 실패한 토큰은 지우지 않는다(없는 토큰이라는 답이 아니다)
    assert len(store.push_devices(a, clk.now)) == 1
    kinds = [r.getMessage() for r in caplog.records if r.getMessage().startswith("push failed")]
    assert kinds and set(kinds) <= {"push failed kind=HTTP 500", "push failed kind=RuntimeError", "push failed kind=Timeout"}


# ---------------------------------------------------------------------------
# PUSH=off(기본)
# ---------------------------------------------------------------------------
def test_push_is_off_by_default():
    assert settings.push == "off"
    assert make_push_sender(load_settings({})) is None


def test_off_registers_but_sends_nothing(store, clk, monkeypatch):
    off = PushNotifier(make_push_sender(load_settings({})))
    monkeypatch.setattr(app.state, "push", off)
    with TestClient(app) as client:
        a, token_a = send_case(client)
        assert register(client, DEVICE_A, (a, token_a)) == [a]
        assert len(store.push_devices(a, clk.now)) == 1
        center_says(client, a)
        assert client.patch(f"/api/center/cases/{a}", json={"status": "done"}).status_code == 200
        assert off._tasks == set()
        assert client.post("/api/center/push-devices/remove", json={"deviceToken": DEVICE_A}).status_code == 204


# ---------------------------------------------------------------------------
# 로그
# ---------------------------------------------------------------------------
def test_logs_have_no_tokens_notice_or_message(client, notifier, caplog):
    caplog.set_level(logging.DEBUG)
    notifier.sender = FakePushSender(unregistered=[DEVICE_B])
    a, token_a = send_case(client)
    register(client, DEVICE_A, (a, token_a))
    register(client, DEVICE_B, (a, token_a))
    client.post(
        "/api/center/push-devices",
        json={"deviceToken": DEVICE_A, "platform": "x", "notice": NOTICE, "cases": [{"id": a, "token": token_a}]},
    )
    center_says(client, a, MARKER)
    client.post("/api/center/push-devices/remove", json={"deviceToken": DEVICE_A})

    assert "push failed kind=UNREGISTERED" in caplog.text
    for secret in (DEVICE_A, DEVICE_B, token_a, NOTICE, MARKER, "MARKER"):
        assert secret not in caplog.text


# ---------------------------------------------------------------------------
# 설정
# ---------------------------------------------------------------------------
def test_settings_read_push_env():
    s = load_settings({"PUSH": "fcm", "FCM_PROJECT_ID": " demo-proj ", "FCM_CREDENTIALS_FILE": " /keys/fcm.json "})
    assert (s.push, s.fcm_project_id, s.fcm_credentials_file) == ("fcm", "demo-proj", "/keys/fcm.json")
    with pytest.raises(ValueError, match="PUSH"):
        load_settings({"PUSH": "apns"})


@pytest.mark.parametrize("env", [{}, {"FCM_PROJECT_ID": "demo-proj"}, {"FCM_CREDENTIALS_FILE": "/nope.json"}])
def test_fcm_without_values_warns_once_and_is_off(env, caplog):
    caplog.set_level(logging.WARNING, logger="app.push")
    assert make_push_sender(replace(load_settings({"PUSH": "fcm"}), **_fields(env))) is None
    assert len(caplog.records) == 1 and caplog.records[0].getMessage().startswith("push off")


def _fields(env: dict) -> dict:
    return {"fcm_project_id": env.get("FCM_PROJECT_ID", ""), "fcm_credentials_file": env.get("FCM_CREDENTIALS_FILE", "")}


@pytest.mark.parametrize("content", [None, "not json", '{"type": "authorized_user"}', '{"type": "service_account", "client_email": "a@b"}'])
def test_unreadable_key_file_warns_once_and_is_off(tmp_path, content, caplog):
    caplog.set_level(logging.WARNING, logger="app.push")
    path = tmp_path / "fcm.json"
    if content is not None:
        path.write_text(content)
    s = load_settings({"PUSH": "fcm", "FCM_PROJECT_ID": "demo-proj", "FCM_CREDENTIALS_FILE": str(path)})
    assert make_push_sender(s) is None
    assert [r.getMessage().split(" ")[:2] for r in caplog.records] == [["push", "off:"]]
    assert str(path) not in caplog.text


def test_good_key_file_makes_fcm_sender(key_file):
    s = load_settings({"PUSH": "fcm", "FCM_PROJECT_ID": "demo-proj", "FCM_CREDENTIALS_FILE": str(key_file[0])})
    assert isinstance(make_push_sender(s), FcmSender)


# ---------------------------------------------------------------------------
# FcmSender: 테스트용 서비스 계정 키 + 가짜 전송(네트워크 없음)
# ---------------------------------------------------------------------------
TOKEN_URI = "https://oauth2.googleapis.com/token"
SEND_URL = "https://fcm.googleapis.com/v1/projects/demo-proj/messages:send"
SA_EMAIL = "fcm-sender@demo-proj.iam.gserviceaccount.com"


@pytest.fixture(scope="module")
def key_file(tmp_path_factory) -> tuple[Path, bytes]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    public_pem = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    info = {
        "type": "service_account",
        "project_id": "demo-proj",
        "private_key_id": "test-key-id",
        "private_key": private_pem.decode(),
        "client_email": SA_EMAIL,
        "token_uri": TOKEN_URI,
    }
    path = tmp_path_factory.mktemp("fcm") / "fcm.json"
    path.write_text(json.dumps(info))
    return path, public_pem


class FakeGoogle:
    """토큰 교환과 FCM 발송을 흉내 낸다. 받은 요청을 쌓고, `send_reply`로 FCM 응답을 바꾼다."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.tokens = 0
        self.send_reply = httpx.Response(200, json={"name": "projects/demo-proj/messages/1"})
        self.token_reply: httpx.Response | None = None

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if str(request.url) == TOKEN_URI:
            if self.token_reply is not None:
                return self.token_reply
            self.tokens += 1
            return httpx.Response(200, json={"access_token": f"access-{self.tokens}", "expires_in": 3600, "token_type": "Bearer"})
        assert str(request.url) == SEND_URL
        return self.send_reply


def fcm_sender(key_file, google: FakeGoogle) -> FcmSender:
    return FcmSender("demo-proj", load_service_account(str(key_file[0])), transport=httpx.MockTransport(google))


def send(sender: FcmSender, device: str = DEVICE_A) -> None:
    asyncio.run(sender.send(device, "android", PUSH_TITLE, NOTICE, {"kind": "center", "caseId": "C-12345"}, "C-12345"))


def test_fcm_sender_request_shape(key_file, clk):
    google = FakeGoogle()
    sender = fcm_sender(key_file, google)
    send(sender)

    token_req, send_req = google.requests
    form = dict(httpx.QueryParams(token_req.content.decode()))
    assert form["grant_type"] == "urn:ietf:params:oauth:grant-type:jwt-bearer"
    # 서명은 테스트 키의 공개 키로 확인한다(시각은 고정한 clock이라 만료 검사는 하지 않는다)
    head, body, sig = form["assertion"].split(".")
    assert crypt.RSAVerifier.from_string(key_file[1]).verify(
        f"{head}.{body}".encode(), base64.urlsafe_b64decode(sig + "=" * (-len(sig) % 4))
    )
    claims = google_jwt.decode(form["assertion"], verify=False)
    assert (claims["iss"], claims["scope"], claims["aud"]) == (SA_EMAIL, FCM_SCOPE, TOKEN_URI)
    assert google_jwt.decode_header(form["assertion"])["kid"] == "test-key-id"
    assert claims["iat"] == int(clk.now.timestamp())

    assert send_req.method == "POST"
    assert send_req.headers["authorization"] == "Bearer access-1"
    assert json.loads(send_req.content) == {
        "message": {
            "token": DEVICE_A,
            "notification": {"title": "for nav", "body": NOTICE},
            "data": {"kind": "center", "caseId": "C-12345"},
            "android": {"collapse_key": "C-12345", "notification": {"tag": "C-12345"}},
            "apns": {"headers": {"apns-collapse-id": "C-12345"}},
        }
    }


def test_fcm_sender_caches_access_token_until_expiry(key_file, clk):
    google = FakeGoogle()
    sender = fcm_sender(key_file, google)
    send(sender)
    clk.advance(minutes=58)
    send(sender, DEVICE_B)
    assert google.tokens == 1
    # 만료 60초 전부터는 새로 받는다
    clk.advance(minutes=1, seconds=1)
    send(sender)
    assert google.tokens == 2
    assert google.requests[-1].headers["authorization"] == "Bearer access-2"


def _fcm_error(status: int, code: str, fcm_code: str | None = None) -> httpx.Response:
    details = [{"@type": "type.googleapis.com/google.firebase.fcm.v1.FcmError", "errorCode": fcm_code}] if fcm_code else []
    return httpx.Response(status, json={"error": {"code": status, "message": f"secret {DEVICE_A}", "status": code, "details": details}})


@pytest.mark.parametrize(
    ("reply", "kind"),
    [
        (_fcm_error(404, "NOT_FOUND", "UNREGISTERED"), "UNREGISTERED"),
        (_fcm_error(400, "INVALID_ARGUMENT", "INVALID_ARGUMENT"), "INVALID_ARGUMENT"),
        (_fcm_error(400, "INVALID_ARGUMENT"), "INVALID_ARGUMENT"),
        (_fcm_error(403, "PERMISSION_DENIED"), "PERMISSION_DENIED"),
        (httpx.Response(500, text="oops"), "HTTP 500"),
        (httpx.Response(503, json={"error": {"status": "not a kind!"}}), "HTTP 503"),
    ],
)
def test_fcm_sender_error_kinds(key_file, clk, reply, kind):
    google = FakeGoogle()
    google.send_reply = reply
    with pytest.raises(PushError) as exc:
        send(fcm_sender(key_file, google))
    assert exc.value.kind == kind
    assert DEVICE_A not in str(exc.value)


def test_fcm_sender_token_failure_and_network_error(key_file, clk):
    google = FakeGoogle()
    google.token_reply = httpx.Response(400, json={"error": "invalid_grant"})
    with pytest.raises(PushError) as exc:
        send(fcm_sender(key_file, google))
    assert exc.value.kind == "token HTTP 400"

    def offline(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no network", request=request)

    sender = FcmSender("demo-proj", load_service_account(str(key_file[0])), transport=httpx.MockTransport(offline))
    with pytest.raises(PushError) as exc:
        send(sender)
    assert exc.value.kind == "ConnectError"


def test_fcm_sender_drops_token_after_401(key_file, clk):
    google = FakeGoogle()
    sender = fcm_sender(key_file, google)
    send(sender)
    google.send_reply = _fcm_error(401, "UNAUTHENTICATED")
    with pytest.raises(PushError):
        send(sender)
    google.send_reply = httpx.Response(200, json={})
    send(sender)
    assert google.tokens == 2
