# 상담 채팅(backlog 14): WebSocket 방, 근로자 토큰, 잘못된 프레임, 데모 초기화, 접근 로그, 읽음(backlog 28). 메모리·SQLite 두 저장소에 돌린다.
# 메시지 번역(backlog 30)은 LLM을 FakeLLMClient로 바꾸고 외부 네트워크를 쓰지 않는다.

import json
import logging
from datetime import datetime

import pytest
from fakes import FakeLLMClient, provider_error
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app import clock
from app.llm_limit import LLMLimiter
from app.main import app
from app.routers import center
from app.store import CenterStore, MemoryStore
from app.store_sqlite import SqliteStore
from app.templates.translate import LineOutput

MARKER = "MARKER-chat-do-not-log"
AT = datetime(2026, 10, 30, 14, 12, 0, tzinfo=clock.SEOUL)
EMPTY_HISTORY = {"type": "history", "messages": [], "read": {"worker": None, "center": None}}

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
        assert worker.receive_json() == EMPTY_HISTORY
        assert staff.receive_json() == EMPTY_HISTORY

        # 클라이언트가 보낸 id·from·at은 무시하고 서버 값을 쓴다.
        worker.send_json({"type": "message", "text": "  Tay tôi vẫn còn chảy máu ", "id": "m-99", "from": "center", "at": "2000-01-01"})
        expected = {
            "type": "message",
            "message": {
                "id": "m-1",
                "caseId": case_id,
                "from": "worker",
                "text": "Tay tôi vẫn còn chảy máu",
                # LLM이 없으면 번역하지 않고 원문만 보낸다(backlog 30)
                "lang": "vi",
                "translated": None,
                "translatedLang": "ko",
                "translation": "skipped",
                "at": clock.iso_utc(AT),
            },
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
        m = wb.receive_json()["message"]
        assert (m["id"], m["caseId"], m["from"], m["text"]) == ("m-1", b, "center", "b")


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
        assert ws.receive_json() == EMPTY_HISTORY


@pytest.mark.parametrize(
    "frame",
    [
        {"type": "message", "text": ""},
        {"type": "message", "text": "   "},
        {"type": "message", "text": "x" * 1001},
        {"type": "message", "text": 3},
        {"type": "typing"},
        {"type": "read"},
        {"type": "read", "upTo": "m-0"},
        {"type": "read", "upTo": "c-1"},
        {"type": "read", "upTo": 1},
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


def test_read_goes_to_the_room_and_comes_back_in_history(client):
    case_id, token = send_case(client)
    with client.websocket_connect(url(case_id, token=token)) as worker, client.websocket_connect(url(case_id, "center")) as staff:
        worker.receive_json()
        staff.receive_json()
        for text in ("하나", "둘"):
            worker.send_json({"type": "message", "text": text})
            worker.receive_json()
            staff.receive_json()

        staff.send_json({"type": "read", "upTo": "m-2"})
        expected = {"type": "read", "role": "center", "upTo": "m-2"}
        assert staff.receive_json() == expected
        assert worker.receive_json() == expected

        # 뒤로 가는 값·같은 값은 저장도 방송도 하지 않는다. 다음 프레임이 바로 온다
        staff.send_json({"type": "read", "upTo": "m-1"})
        staff.send_json({"type": "read", "upTo": "m-2"})
        staff.send_json({"type": "message", "text": "셋"})
        assert staff.receive_json()["message"]["id"] == "m-3"
        assert worker.receive_json()["message"]["id"] == "m-3"

        worker.send_json({"type": "read", "upTo": "m-3"})
        assert staff.receive_json() == {"type": "read", "role": "worker", "upTo": "m-3"}

    with client.websocket_connect(url(case_id, "center")) as ws:
        assert ws.receive_json()["read"] == {"worker": "m-3", "center": "m-2"}


def test_read_of_missing_message_is_invalid(client):
    case_id, token = send_case(client)
    with client.websocket_connect(url(case_id, token=token)) as ws:
        ws.receive_json()
        ws.send_json({"type": "read", "upTo": "m-1"})
        assert ws.receive_json() == {"type": "error", "code": "invalid"}
        ws.send_json({"type": "message", "text": "하나"})
        ws.receive_json()
        ws.send_json({"type": "read", "upTo": "m-2"})
        assert ws.receive_json() == {"type": "error", "code": "invalid"}
        ws.send_json({"type": "read", "upTo": "m-1"})
        assert ws.receive_json() == {"type": "read", "role": "worker", "upTo": "m-1"}


def test_read_marks_survive_sqlite_reopen(tmp_path):
    path = str(tmp_path / "center.db")
    s = SqliteStore(path)
    assert s.mark_read("C-1", "center", 2)
    assert not s.mark_read("C-1", "center", 1)
    s.close()
    s = SqliteStore(path)
    assert s.read_marks("C-1") == {"worker": None, "center": "m-2"}
    s.reset()
    assert s.read_marks("C-1") == {"worker": None, "center": None}
    s.close()


def test_reset_closes_rooms_and_clears_history(client):
    case_id, token = send_case(client)
    with client.websocket_connect(url("C-1001", "center")) as ws:
        ws.receive_json()
        ws.send_json({"type": "message", "text": "남을까"})
        ws.receive_json()
        ws.send_json({"type": "read", "upTo": "m-1"})
        ws.receive_json()

        assert client.post("/api/center/reset").status_code == 204
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_json()
        assert exc.value.code == 4000

    with client.websocket_connect(url("C-1001", "center")) as ws:
        assert ws.receive_json() == EMPTY_HISTORY
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


# ---------------------------------------------------------------------------
# 근로자가 자기 요청의 상태와 센터 메시지 수를 읽기(backlog 27)
# ---------------------------------------------------------------------------
def my_cases(client: TestClient, *refs: tuple[str, str]) -> list[dict]:
    r = client.post("/api/center/my-cases", json={"cases": [{"id": i, "token": t} for i, t in refs]})
    assert r.status_code == 200
    return r.json()


def test_my_cases_counts_center_messages_only(client):
    case_id, token = send_case(client)
    assert my_cases(client, (case_id, token)) == [{"id": case_id, "status": "new", "centerMessages": 0, "lastCenterAt": None}]

    with client.websocket_connect(url(case_id, token=token)) as worker, client.websocket_connect(url(case_id, "center")) as staff:
        worker.receive_json()
        staff.receive_json()
        worker.send_json({"type": "message", "text": "도와주세요"})
        worker.receive_json()
        staff.receive_json()
        for text in ("확인했습니다", "내일 연락드릴게요"):
            staff.send_json({"type": "message", "text": text})
            worker.receive_json()
            staff.receive_json()

    assert client.patch(f"/api/center/cases/{case_id}", json={"status": "progress"}).status_code == 200
    assert my_cases(client, (case_id, token)) == [
        {"id": case_id, "status": "progress", "centerMessages": 2, "lastCenterAt": clock.iso_utc(AT)}
    ]


def test_my_cases_drops_wrong_token_and_unknown_case(client):
    a, token_a = send_case(client)
    b, token_b = send_case(client)
    out = my_cases(client, (a, "wrong"), ("C-0", token_a), ("C-1001", "x"), (b, token_b))
    # 틀린 토큰·없는 사례·토큰 없는 mock 사례는 403·404 없이 빠진다.
    assert [x["id"] for x in out] == [b]


def test_my_cases_after_reset_is_empty(client):
    case_id, token = send_case(client)
    assert client.post("/api/center/reset").status_code == 204
    assert my_cases(client, (case_id, token)) == []


@pytest.mark.parametrize(
    "body",
    [
        {"cases": []},
        {"cases": [{"id": f"C-{n}", "token": "t"} for n in range(21)]},
        {"cases": [{"id": "C-1"}]},
        {"cases": [{"id": "", "token": "t"}]},
        {},
    ],
)
def test_my_cases_bad_body_is_422(client, body):
    assert client.post("/api/center/my-cases", json=body).status_code == 422


def test_my_cases_log_has_no_token(client, caplog):
    caplog.set_level(logging.INFO, logger="app")
    case_id, token = send_case(client)
    my_cases(client, (case_id, token))
    assert token not in "\n".join(r.getMessage() for r in caplog.records)


# ---------------------------------------------------------------------------
# 메시지 번역(backlog 30): 근로자 → 한국어, 센터 → 사례 언어. 실패하면 원문만 보낸다.
# ---------------------------------------------------------------------------
VI = "Tay tôi vẫn còn chảy máu"
KO = "손에서 아직 피가 납니다"


def reply(text: str) -> str:
    return LineOutput(text=text).model_dump_json()


@pytest.fixture(params=["memory", "sqlite"])
def open_llm_client(request, tmp_path, monkeypatch):
    """가짜 LLM을 붙여 서버를 연다. 호출 제한은 끈다(backlog 20은 test_llm_limit.py가 본다)."""
    s: CenterStore = MemoryStore() if request.param == "memory" else SqliteStore(str(tmp_path / "center.db"))
    monkeypatch.setattr(center, "store", s)
    monkeypatch.setattr(clock, "now", lambda: AT)
    monkeypatch.setattr(app.state, "llm_limiter", LLMLimiter())

    def make(llm: FakeLLMClient | None):
        monkeypatch.setattr("app.main.get_llm_client", lambda: llm)
        return TestClient(app)

    yield make
    s.close()


def translation_of(m: dict) -> tuple:
    return (m["text"], m["lang"], m["translated"], m["translatedLang"], m["translation"])


def test_messages_are_translated_both_ways(open_llm_client):
    fake = FakeLLMClient([reply(KO), reply("Bạn bị chảy máu từ khi nào?")])
    with open_llm_client(fake) as client:
        case_id, token = send_case(client)
        with client.websocket_connect(url(case_id, token=token)) as worker, client.websocket_connect(url(case_id, "center")) as staff:
            worker.receive_json()
            staff.receive_json()

            worker.send_json({"type": "message", "text": VI})
            for ws in (worker, staff):
                assert translation_of(ws.receive_json()["message"]) == (VI, "vi", KO, "ko", "ok")

            staff.send_json({"type": "message", "text": "언제부터 피가 났나요?"})
            for ws in (worker, staff):
                assert translation_of(ws.receive_json()["message"]) == (
                    "언제부터 피가 났나요?",
                    "ko",
                    "Bạn bị chảy máu từ khi nào?",
                    "vi",
                    "ok",
                )

        # 다시 붙어도 번역이 그대로 있다
        with client.websocket_connect(url(case_id, "center")) as ws:
            history = ws.receive_json()["messages"]
    assert [(m["id"], m["translated"]) for m in history] == [("m-1", KO), ("m-2", "Bạn bị chảy máu từ khi nào?")]
    # 근로자 메시지는 베트남어 → 한국어, 센터 메시지는 한국어 → 베트남어로 부탁했다
    assert [p.user for p in fake.prompts] == [VI, "언제부터 피가 났나요?"]
    assert "Translate from 베트남어 into 한국어" in fake.prompts[0].system
    assert "Translate from 한국어 into 베트남어" in fake.prompts[1].system


# 가짜 LLM은 응답을 꺼내 쓰므로 저장소마다 새로 만든다.
@pytest.mark.parametrize(
    ("make_llm", "status"),
    [
        (lambda: None, "skipped"),
        (lambda: FakeLLMClient([provider_error()]), "skipped"),
        (lambda: FakeLLMClient([reply("손가락 골절입니다")]), "rejected"),
    ],
    ids=["no-llm", "llm-error", "guard"],
)
def test_failed_translation_sends_original(open_llm_client, make_llm, status):
    with open_llm_client(make_llm()) as client:
        case_id, token = send_case(client)
        with client.websocket_connect(url(case_id, token=token)) as ws:
            ws.receive_json()
            ws.send_json({"type": "message", "text": VI})
            assert translation_of(ws.receive_json()["message"]) == (VI, "vi", None, "ko", status)


def test_translation_log_has_no_text(open_llm_client, caplog):
    caplog.set_level(logging.INFO, logger="app")
    translated = "로그에 남으면 안 되는 번역문입니다"
    with open_llm_client(FakeLLMClient([reply(translated)])) as client:
        case_id, token = send_case(client)
        with client.websocket_connect(url(case_id, token=token)) as ws:
            ws.receive_json()
            ws.send_json({"type": "message", "text": MARKER})
            assert ws.receive_json()["message"]["translation"] == "ok"

    log = "\n".join(r.getMessage() for r in caplog.records if r.name.startswith("app"))
    assert MARKER not in log
    assert translated not in log
    assert "chat translation=ok" in log
