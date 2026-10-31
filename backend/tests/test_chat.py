# 상담 채팅(backlog 14): WebSocket 방, 근로자 토큰, 잘못된 프레임, 데모 초기화, 접근 로그. 메모리·SQLite 두 저장소에 돌린다.

import json
import logging
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app import clock
from app.main import app
from app.routers import center
from app.store import CenterStore, MemoryStore
from app.store_sqlite import SqliteStore

MARKER = "MARKER-chat-do-not-log"
AT = datetime(2026, 10, 30, 14, 12, 0, tzinfo=clock.SEOUL)

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


@pytest.fixture(params=["memory", "sqlite"])
def client(request, tmp_path, monkeypatch):
    s: CenterStore = MemoryStore() if request.param == "memory" else SqliteStore(str(tmp_path / "center.db"))
    monkeypatch.setattr(center, "store", s)
    monkeypatch.setattr(clock, "now", lambda: AT)
    # `with`로 열어 두 연결이 같은 이벤트 루프에서 돈다.
    with TestClient(app) as c:
        yield c
    s.close()


def send_case(client: TestClient) -> tuple[str, str]:
    body = {
        "intake": INTAKE,
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
    return f"/api/center/cases/{case_id}/chat?{q}"


def close_code(client: TestClient, path: str) -> int:
    with client.websocket_connect(path) as ws, pytest.raises(WebSocketDisconnect) as exc:
        ws.receive_json()
    return exc.value.code


def test_worker_and_center_share_a_room(client):
    case_id, token = send_case(client)
    with client.websocket_connect(url(case_id, token=token)) as worker, client.websocket_connect(url(case_id, "center")) as staff:
        assert worker.receive_json() == {"type": "history", "messages": []}
        assert staff.receive_json() == {"type": "history", "messages": []}

        # 클라이언트가 보낸 id·from·at은 무시하고 서버 값을 쓴다.
        worker.send_json({"type": "message", "text": "  Tay tôi vẫn còn chảy máu ", "id": "m-99", "from": "center", "at": "2000-01-01"})
        expected = {
            "type": "message",
            "message": {"id": "m-1", "caseId": case_id, "from": "worker", "text": "Tay tôi vẫn còn chảy máu", "at": clock.iso_utc(AT)},
        }
        assert worker.receive_json() == expected
        assert staff.receive_json() == expected

        staff.send_json({"type": "message", "text": "지금 확인하겠습니다"})
        for ws in (worker, staff):
            m = ws.receive_json()["message"]
            assert (m["id"], m["from"], m["text"]) == ("m-2", "center", "지금 확인하겠습니다")


def test_reconnect_gets_history_in_order(client):
    case_id, token = send_case(client)
    with client.websocket_connect(url(case_id, token=token)) as ws:
        ws.receive_json()
        for text in ("하나", "둘"):
            ws.send_json({"type": "message", "text": text})
            ws.receive_json()

    with client.websocket_connect(url(case_id, "center")) as ws:
        history = ws.receive_json()
    assert history["type"] == "history"
    assert [(m["id"], m["text"]) for m in history["messages"]] == [("m-1", "하나"), ("m-2", "둘")]


def test_rooms_are_per_case(client):
    a, token_a = send_case(client)
    b, _ = send_case(client)
    with client.websocket_connect(url(a, token=token_a)) as wa, client.websocket_connect(url(b, "center")) as wb:
        wa.receive_json()
        wb.receive_json()
        wa.send_json({"type": "message", "text": "a"})
        wa.receive_json()
        wb.send_json({"type": "message", "text": "b"})
        # b 방에는 b 메시지만 온다(id도 사례마다 m-1부터).
        assert wb.receive_json()["message"] == {"id": "m-1", "caseId": b, "from": "center", "text": "b", "at": clock.iso_utc(AT)}


def test_unknown_case_is_4404(client):
    assert close_code(client, url("C-0", "center")) == 4404


def test_bad_role_or_token_is_4403(client):
    case_id, token = send_case(client)
    assert close_code(client, url(case_id)) == 4403
    assert close_code(client, url(case_id, token="wrong")) == 4403
    assert close_code(client, url(case_id, role="admin", token=token)) == 4403
    assert close_code(client, f"/api/center/cases/{case_id}/chat") == 4403
    # mock 사례에는 근로자 토큰이 없어 센터만 붙는다.
    assert close_code(client, url("C-1001", token="x")) == 4403
    with client.websocket_connect(url("C-1001", "center")) as ws:
        assert ws.receive_json() == {"type": "history", "messages": []}


@pytest.mark.parametrize(
    "frame",
    [
        {"type": "message", "text": ""},
        {"type": "message", "text": "   "},
        {"type": "message", "text": "x" * 1001},
        {"type": "message", "text": 3},
        {"type": "typing"},
        {"text": "hi"},
        "not json",
    ],
)
def test_invalid_frame_keeps_connection(client, frame):
    case_id, token = send_case(client)
    with client.websocket_connect(url(case_id, token=token)) as ws:
        ws.receive_json()
        ws.send_text(frame if isinstance(frame, str) else json.dumps(frame))
        assert ws.receive_json() == {"type": "error", "code": "invalid"}
        ws.send_bytes(b"\x00")
        assert ws.receive_json() == {"type": "error", "code": "invalid"}
        # 연결은 그대로라 다음 메시지가 간다. 1000자는 받는다.
        ws.send_json({"type": "message", "text": "x" * 1000})
        assert ws.receive_json()["message"]["id"] == "m-1"


def test_reset_closes_rooms_and_clears_history(client):
    case_id, token = send_case(client)
    with client.websocket_connect(url("C-1001", "center")) as ws:
        ws.receive_json()
        ws.send_json({"type": "message", "text": "남을까"})
        ws.receive_json()

        assert client.post("/api/center/reset").status_code == 204
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_json()
        assert exc.value.code == 4000

    with client.websocket_connect(url("C-1001", "center")) as ws:
        assert ws.receive_json() == {"type": "history", "messages": []}
    # live 사례도 지워졌으므로 그 토큰으로는 붙지 못한다.
    assert close_code(client, url(case_id, token=token)) == 4404


def test_access_log_has_no_token_or_text(client, caplog):
    caplog.set_level(logging.INFO, logger="app")
    case_id, token = send_case(client)
    with client.websocket_connect(url(case_id, token=token), headers={"X-Request-Id": "chat-req-1"}) as ws:
        ws.receive_json()
        ws.send_json({"type": "message", "text": MARKER})
        ws.receive_json()
    close_code(client, url(case_id, token="wrong"))

    lines = [r.getMessage() for r in caplog.records if r.name.startswith("app")]
    log = "\n".join(lines)
    assert MARKER not in log
    assert token not in log
    assert "token=" not in log
    assert any(line.startswith(f"WS /api/center/cases/{case_id}/chat 1000 ") and "request_id=chat-req-1" in line for line in lines)
    assert any(line.startswith(f"WS /api/center/cases/{case_id}/chat 4403 ") for line in lines)


def test_uvicorn_websocket_line_is_dropped(caplog):
    # 실제 서버(uvicorn)는 `"WebSocket <경로?쿼리>" [accepted]`를 uvicorn.error에 남긴다. 쿼리에 토큰이 있으므로 버린다.
    caplog.set_level(logging.INFO, logger="uvicorn.error")
    uvicorn_error = logging.getLogger("uvicorn.error")
    uvicorn_error.info('%s - "WebSocket %s" [accepted]', "127.0.0.1:5000", f"/api/center/cases/C-1/chat?role=worker&token={MARKER}")
    uvicorn_error.info("Application startup complete.")

    messages = [r.getMessage() for r in caplog.records if r.name == "uvicorn.error"]
    assert messages == ["Application startup complete."]
