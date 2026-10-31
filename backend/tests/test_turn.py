# 통화 TURN 자격 증명(backlog 31): ice-servers 경로의 권한 검사(통화 WebSocket과 같다), TURN off·실패 시 빈 목록,
# Cloudflare 요청 모양과 응답 거르기(53번 포트·모르는 필드), 설정 검사, 로그에 키·자격 증명 없음.
# Cloudflare는 httpx.MockTransport로 바꾸고 외부 네트워크를 쓰지 않는다.

import asyncio
import dataclasses
import json
import logging

import httpx
import pytest
from fakes import FakeTurnIssuer
from fastapi.testclient import TestClient

from app.main import app
from app.routers import center
from app.settings import load_settings
from app.store import MemoryStore
from app.turn import CloudflareTurn, TurnError, clean_ice_servers, make_turn_issuer

SECRET = "SECRET-turn-token-do-not-log"
CREDENTIAL = "CREDENTIAL-do-not-log"
TURN = [
    {"urls": ["stun:stun.cloudflare.com:3478"]},
    {
        "urls": ["turn:turn.cloudflare.com:3478?transport=udp", "turns:turn.cloudflare.com:443?transport=tcp"],
        "username": "u1",
        "credential": CREDENTIAL,
    },
]


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(center, "store", MemoryStore())
    with TestClient(app) as c:
        yield c


def send_case(client: TestClient) -> tuple[str, str]:
    body = {
        "intake": {
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
        },
        "requestTypes": ["booking"],
        "coverage": None,
        "insurance": "yes",
        "contactMethod": None,
        "contact": None,
        "consentedItems": [],
    }
    out = client.post("/api/center/cases", json=body).json()
    return out["case"]["id"], out["chatToken"]


def url(case_id: str, role: str = "worker", token: str = "") -> str:
    q = f"role={role}" + (f"&token={token}" if token else "")
    return f"/api/center/cases/{case_id}/call/ice-servers?{q}"


def test_turn_off_gives_empty_list(client, monkeypatch):
    monkeypatch.setattr(app.state, "turn", None)
    case_id, token = send_case(client)
    r = client.get(url(case_id, token=token))
    assert r.status_code == 200
    assert r.json() == {"iceServers": []}


def test_worker_and_center_get_servers(client, monkeypatch):
    issuer = FakeTurnIssuer(TURN)
    monkeypatch.setattr(app.state, "turn", issuer)
    case_id, token = send_case(client)
    r = client.get(url(case_id, token=token))
    assert r.json() == {"iceServers": TURN}
    assert r.headers["cache-control"] == "no-store"
    # CENTER_AUTH=off(테스트 기본값)이면 센터는 역할만으로 받는다(통화 WebSocket과 같다)
    assert client.get(url(case_id, "center")).json() == {"iceServers": TURN}
    # 부를 때마다 새로 받는다
    assert issuer.calls == 2


def test_stun_item_has_no_credential_keys(client, monkeypatch):
    monkeypatch.setattr(app.state, "turn", FakeTurnIssuer(TURN))
    case_id, token = send_case(client)
    stun = client.get(url(case_id, token=token)).json()["iceServers"][0]
    assert stun == {"urls": ["stun:stun.cloudflare.com:3478"]}


def test_denied_like_call_socket(client, monkeypatch):
    issuer = FakeTurnIssuer(TURN)
    monkeypatch.setattr(app.state, "turn", issuer)
    case_id, token = send_case(client)
    assert client.get(url("C-00000", token=token)).status_code == 404
    assert client.get(url(case_id, token="wrong")).status_code == 403
    assert client.get(url(case_id)).status_code == 403
    assert client.get(url(case_id, "someone", token=token)).status_code == 403
    # 거절된 요청으로는 자격 증명을 만들지 않는다
    assert issuer.calls == 0


def test_center_needs_session_when_auth_on(client, monkeypatch):
    monkeypatch.setattr(app.state, "turn", FakeTurnIssuer(TURN))
    case_id, _ = send_case(client)
    monkeypatch.setattr(center, "settings", dataclasses.replace(center.settings, center_auth="email"))
    assert client.get(url(case_id, "center")).status_code == 401


def test_issue_failure_gives_empty_list(client, monkeypatch, caplog):
    monkeypatch.setattr(app.state, "turn", FakeTurnIssuer(TURN, fail="http_503"))
    case_id, token = send_case(client)
    with caplog.at_level(logging.WARNING):
        r = client.get(url(case_id, token=token))
    assert r.json() == {"iceServers": []}
    assert "turn issue failed: http_503" in caplog.text
    assert token not in caplog.text


def cloudflare(handler) -> CloudflareTurn:
    return CloudflareTurn("key-1", SECRET, 3600, transport=httpx.MockTransport(handler))


def test_cloudflare_request_and_filter():
    seen: list[httpx.Request] = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        servers = [*TURN, {"urls": ["turn:turn.cloudflare.com:53?transport=udp"], "username": "u1", "credential": CREDENTIAL}]
        return httpx.Response(201, json={"iceServers": servers})

    out = asyncio.run(cloudflare(handler).issue())
    assert out == TURN
    req = seen[0]
    assert req.method == "POST"
    assert str(req.url) == "https://rtc.live.cloudflare.com/v1/turn/keys/key-1/credentials/generate-ice-servers"
    assert req.headers["authorization"] == f"Bearer {SECRET}"
    assert json.loads(req.content) == {"ttl": 3600}


@pytest.mark.parametrize(
    ("response", "kind"),
    [
        (httpx.Response(401, json={}), "http_401"),
        (httpx.Response(201, text="not json"), "bad_response"),
        (httpx.Response(201, json={"iceServers": "x"}), "bad_response"),
        (httpx.Response(201, json={"iceServers": [{"urls": ["turn:turn.cloudflare.com:53"]}]}), "bad_response"),
    ],
)
def test_cloudflare_errors(response, kind):
    with pytest.raises(TurnError) as e:
        asyncio.run(cloudflare(lambda req: response).issue())
    assert e.value.kind == kind
    assert SECRET not in str(e.value)


def test_cloudflare_network_error():
    def handler(req):
        raise httpx.ConnectTimeout("boom", request=req)

    with pytest.raises(TurnError) as e:
        asyncio.run(cloudflare(handler).issue())
    assert e.value.kind == "ConnectTimeout"


def test_clean_keeps_only_browser_fields():
    raw = {
        "iceServers": [
            {"urls": "stun:a:3478", "extra": 1},
            {"urls": ["turn:b:3478"], "username": "u", "credential": "c", "credentialType": "password"},
        ]
    }
    assert clean_ice_servers(raw) == [{"urls": ["stun:a:3478"]}, {"urls": ["turn:b:3478"], "username": "u", "credential": "c"}]


def test_settings_and_issuer(caplog):
    s = load_settings({})
    assert (s.turn, s.turn_ttl_s) == ("off", 14400)
    assert make_turn_issuer(s) is None
    with pytest.raises(ValueError):
        load_settings({"TURN": "coturn"})
    with pytest.raises(ValueError):
        load_settings({"TURN_TTL_S": "0"})
    on = load_settings({"TURN": "cloudflare", "TURN_KEY_ID": "key-1", "TURN_API_TOKEN": SECRET, "TURN_TTL_S": "600"})
    assert SECRET not in repr(on)
    assert isinstance(make_turn_issuer(on), CloudflareTurn)
    with caplog.at_level(logging.WARNING):
        assert make_turn_issuer(load_settings({"TURN": "cloudflare", "TURN_KEY_ID": "key-1"})) is None
    assert "turn off" in caplog.text
