# 통화와 자막 번역(backlog 16): 있음 알림, 시그널링 중계, 자막 번역·대체, 권한·닫힘 코드, 로그에 원문 없음.
# 자막 저장과 다시 보기(backlog 18): 연결 직후 history, 번역 전 자막 빼기, 끊긴 쪽 자막 skipped, 말한 순서, 데모 초기화.
# LLM은 FakeLLMClient로 바꾸고 외부 네트워크를 쓰지 않는다. 채팅과 같은 검사·토큰을 쓰므로 저장소는 메모리 하나로 돌린다.

import dataclasses
import json
import logging
from contextlib import contextmanager
from datetime import datetime

import pytest
from fakes import FakeLLMClient, provider_error
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app import clock
from app.chat import CallHub
from app.main import app
from app.routers import center
from app.store import MemoryStore
from app.templates.translate import LineOutput

MARKER = "MARKER-call-do-not-log"
INVALID = {"type": "error", "code": "invalid"}
AT = datetime(2026, 10, 30, 14, 12, 0, tzinfo=clock.SEOUL)
VI = "Tay tôi vẫn còn chảy máu"
KO = "손에서 아직 피가 납니다"


def intake(language: str) -> dict:
    return {
        "id": "in-test",
        "language": language,
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


def line(text: str) -> str:
    return LineOutput(text=text).model_dump_json()


@pytest.fixture
def open_client(monkeypatch):
    """LLM(가짜 또는 None)과 시간 제한을 골라 서버를 연다. `with`로 열어 두 연결이 같은 이벤트 루프에서 돈다."""
    monkeypatch.setattr(center, "store", MemoryStore())
    monkeypatch.setattr(clock, "now", lambda: AT)
    monkeypatch.setattr(app.state, "call", CallHub())

    @contextmanager
    def make(llm: FakeLLMClient | None = None, timeout_s: float = 10.0):
        monkeypatch.setattr("app.main.get_llm_client", lambda: llm)
        monkeypatch.setattr(center, "settings", dataclasses.replace(center.settings, llm_timeout_s=timeout_s))
        with TestClient(app) as c:
            yield c

    return make


def send_case(client: TestClient, language: str = "vi") -> tuple[str, str]:
    body = {
        "intake": intake(language),
        "emergencyFlag": False,
        "requestType": "booking",
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
    return f"/api/center/cases/{case_id}/call?{q}"


def greet(ws, role: str, peers: list[str]) -> list[dict]:
    """연결 직후 두 프레임(joined, history)을 확인하고 이전 자막 목록을 돌려준다."""
    assert ws.receive_json() == {"type": "joined", "role": role, "peers": peers}
    frame = ws.receive_json()
    assert frame["type"] == "history"
    return frame["captions"]


def wait_processed(ws) -> None:
    """앞서 보낸 프레임을 서버가 처리했을 때까지 기다린다. 프레임은 차례대로 처리되므로 잘못된 프레임의 응답이 오면 앞의 것도 끝났다."""
    ws.send_text("not json")
    assert ws.receive_json() == INVALID


@contextmanager
def pair(client: TestClient, case_id: str, token: str):
    """근로자가 먼저, 센터가 다음에 붙고 있음 알림까지 받은 두 연결."""
    with client.websocket_connect(url(case_id, token=token)) as worker:
        greet(worker, "worker", [])
        with client.websocket_connect(url(case_id, "center")) as staff:
            greet(staff, "center", ["worker"])
            assert worker.receive_json() == {"type": "peer", "role": "center", "present": True}
            yield worker, staff


def close_code(client: TestClient, path: str) -> int:
    with client.websocket_connect(path) as ws, pytest.raises(WebSocketDisconnect) as exc:
        ws.receive_json()
    return exc.value.code


def test_peer_presence(open_client):
    with open_client() as client:
        case_id, token = send_case(client)
        with client.websocket_connect(url(case_id, token=token)) as worker:
            greet(worker, "worker", [])
            with client.websocket_connect(url(case_id, "center")) as staff:
                greet(staff, "center", ["worker"])
                worker.receive_json()
            assert worker.receive_json() == {"type": "peer", "role": "center", "present": False}


def test_signal_goes_only_to_the_other_side(open_client):
    data = {"sdp": {"type": "offer", "sdp": "v=0\r\no=- 1 2 IN IP4 127.0.0.1\r\n"}}
    with open_client() as client:
        case_id, token = send_case(client)
        with pair(client, case_id, token) as (worker, staff):
            worker.send_json({"type": "signal", "data": data})
            assert staff.receive_json() == {"type": "signal", "from": "worker", "data": data}
            staff.send_json({"type": "signal", "data": {"candidate": {"candidate": "candidate:1 1 udp"}}})
            # 보낸 쪽은 자기 signal을 받지 않는다. 다음에 받는 것이 상대의 signal이다.
            assert worker.receive_json() == {"type": "signal", "from": "center", "data": {"candidate": {"candidate": "candidate:1 1 udp"}}}


@pytest.mark.parametrize(
    "frame",
    [
        "not json",
        json.dumps({"type": "message", "text": "hi"}),
        json.dumps({"type": "signal"}),
        json.dumps({"type": "signal", "data": "offer"}),
        json.dumps({"type": "signal", "data": {"sdp": "x" * (16 * 1024)}}),
        json.dumps({"type": "caption", "text": "   "}),
        json.dumps({"type": "caption", "text": "a" * 501}),
    ],
)
def test_invalid_frame_keeps_connection(open_client, frame):
    with open_client() as client:
        case_id, token = send_case(client)
        with pair(client, case_id, token) as (worker, staff):
            worker.send_text(frame)
            assert worker.receive_json() == INVALID
            worker.send_json({"type": "signal", "data": {"ok": True}})
            assert staff.receive_json() == {"type": "signal", "from": "worker", "data": {"ok": True}}


def test_worker_caption_is_translated_to_korean(open_client):
    fake = FakeLLMClient([line(KO)])
    with open_client(fake) as client:
        case_id, token = send_case(client)
        with pair(client, case_id, token) as (worker, staff):
            worker.send_json({"type": "caption", "text": f"  {VI} "})
            expected = {
                "type": "caption",
                "caption": {
                    "id": "c-1",
                    "from": "worker",
                    "text": VI,
                    "lang": "vi",
                    "translated": KO,
                    "translatedLang": "ko",
                    "translation": "ok",
                    "at": clock.iso_utc(AT),
                },
            }
            assert worker.receive_json() == expected
            assert staff.receive_json() == expected
    assert fake.prompts[0].user == VI
    assert "베트남어" in fake.prompts[0].system and "한국어" in fake.prompts[0].system


def test_center_caption_is_translated_to_case_language(open_client):
    fake = FakeLLMClient([line(VI)])
    with open_client(fake) as client:
        case_id, token = send_case(client)
        with pair(client, case_id, token) as (worker, staff):
            staff.send_json({"type": "caption", "text": KO})
            c = worker.receive_json()["caption"]
            assert (c["id"], c["from"], c["lang"], c["translated"], c["translatedLang"], c["translation"]) == (
                "c-1",
                "center",
                "ko",
                VI,
                "vi",
                "ok",
            )
            assert staff.receive_json()["caption"] == c
    assert fake.prompts[0].system.index("한국어") < fake.prompts[0].system.index("베트남어")


@pytest.mark.parametrize("llm", [None, FakeLLMClient([provider_error()])], ids=["no-llm", "llm-error"])
def test_caption_falls_back_to_original(open_client, llm):
    with open_client(llm) as client:
        case_id, token = send_case(client)
        with pair(client, case_id, token) as (worker, staff):
            worker.send_json({"type": "caption", "text": VI})
            c = staff.receive_json()["caption"]
            assert (c["text"], c["translated"], c["translation"]) == (VI, None, "skipped")
            worker.receive_json()


def test_korean_translation_failing_guard_is_rejected(open_client):
    fake = FakeLLMClient([line("손가락 골절입니다")])
    with open_client(fake) as client:
        case_id, token = send_case(client)
        with pair(client, case_id, token) as (worker, staff):
            worker.send_json({"type": "caption", "text": VI})
            c = staff.receive_json()["caption"]
            assert (c["text"], c["translated"], c["translation"]) == (VI, None, "rejected")


def test_korean_case_is_not_translated(open_client):
    fake = FakeLLMClient([])
    with open_client(fake) as client:
        case_id, token = send_case(client, "ko")
        with pair(client, case_id, token) as (worker, staff):
            worker.send_json({"type": "caption", "text": "손에서 피가 나요"})
            c = staff.receive_json()["caption"]
            assert (c["lang"], c["translatedLang"], c["translated"], c["translation"]) == ("ko", "ko", None, "skipped")
    assert fake.prompts == []


def test_signal_is_relayed_while_translation_waits(open_client):
    # 첫 자막의 LLM 호출은 시간 제한까지 멈춘다. 그동안 보낸 signal이 먼저 간다.
    fake = FakeLLMClient([None, line(KO)])
    with open_client(fake, timeout_s=0.5) as client:
        case_id, token = send_case(client)
        with pair(client, case_id, token) as (worker, staff):
            worker.send_json({"type": "caption", "text": VI})
            worker.send_json({"type": "signal", "data": {"candidate": "c"}})
            assert staff.receive_json() == {"type": "signal", "from": "worker", "data": {"candidate": "c"}}
            c = staff.receive_json()["caption"]
            assert (c["id"], c["translation"]) == ("c-1", "skipped")


def test_close_codes(open_client):
    with open_client() as client:
        case_id, token = send_case(client)
        assert close_code(client, url("C-0", "center")) == 4404
        assert close_code(client, url(case_id)) == 4403
        assert close_code(client, url(case_id, token="wrong")) == 4403
        assert close_code(client, url(case_id, role="admin", token=token)) == 4403
        with client.websocket_connect(url(case_id, "center")) as staff:
            greet(staff, "center", [])
            assert close_code(client, url(case_id, "center")) == 4409
            # 같은 역할 두 번째 연결이 거절돼도 첫 연결은 그대로다.
            with client.websocket_connect(url(case_id, token=token)) as worker:
                greet(worker, "worker", ["center"])


def test_reset_closes_calls(open_client):
    with open_client() as client:
        case_id, token = send_case(client)
        with pair(client, case_id, token) as (worker, staff):
            assert client.post("/api/center/reset").status_code == 204
            for ws in (worker, staff):
                with pytest.raises(WebSocketDisconnect) as exc:
                    ws.receive_json()
                assert exc.value.code == 4000


# ---------------------------------------------------------------------------
# 자막 저장과 다시 보기(backlog 18)
# ---------------------------------------------------------------------------
def test_history_is_empty_at_first(open_client):
    with open_client() as client:
        case_id, token = send_case(client)
        with client.websocket_connect(url(case_id, token=token)) as worker:
            assert greet(worker, "worker", []) == []


def test_translated_caption_is_in_history_of_new_connection(open_client):
    with open_client(FakeLLMClient([line(KO)])) as client:
        case_id, token = send_case(client)
        with pair(client, case_id, token) as (worker, staff):
            worker.send_json({"type": "caption", "text": VI})
            sent = staff.receive_json()["caption"]
            worker.receive_json()
        # 센터가 화면을 나갔다가(또는 새로고침) 다시 붙는다.
        with client.websocket_connect(url(case_id, "center")) as staff:
            history = greet(staff, "center", [])
    assert history == [sent]
    assert (sent["id"], sent["text"], sent["translated"], sent["translation"]) == ("c-1", VI, KO, "ok")


def test_caption_in_translation_is_sent_once_not_in_history(open_client):
    # 번역이 시간 제한까지 멈춘 동안 센터가 붙는다. history에는 없고, 번역이 끝나면 caption으로 한 번 받는다.
    with open_client(FakeLLMClient([None]), timeout_s=0.5) as client:
        case_id, token = send_case(client)
        with client.websocket_connect(url(case_id, token=token)) as worker:
            greet(worker, "worker", [])
            worker.send_json({"type": "caption", "text": VI})
            wait_processed(worker)
            with client.websocket_connect(url(case_id, "center")) as staff:
                assert greet(staff, "center", ["worker"]) == []
                c = staff.receive_json()["caption"]
                assert (c["id"], c["text"], c["translation"]) == ("c-1", VI, "skipped")
                worker.send_json({"type": "signal", "data": {"next": True}})
                assert staff.receive_json() == {"type": "signal", "from": "worker", "data": {"next": True}}


def test_speaker_leaving_mid_translation_keeps_caption_as_skipped(open_client):
    with open_client(FakeLLMClient([None])) as client:
        case_id, token = send_case(client)
        with client.websocket_connect(url(case_id, "center")) as staff:
            greet(staff, "center", [])
            with client.websocket_connect(url(case_id, token=token)) as worker:
                greet(worker, "worker", ["center"])
                staff.receive_json()
                worker.send_json({"type": "caption", "text": VI})
                wait_processed(worker)
            c = staff.receive_json()["caption"]
            assert (c["id"], c["from"], c["text"], c["translated"], c["translation"]) == ("c-1", "worker", VI, None, "skipped")
            assert staff.receive_json() == {"type": "peer", "role": "worker", "present": False}
        with client.websocket_connect(url(case_id, token=token)) as worker:
            assert greet(worker, "worker", []) == [c]


def test_history_keeps_spoken_order_when_translations_finish_reversed(open_client):
    # 첫 자막은 시간 제한까지 멈추고 둘째 자막이 먼저 번역된다.
    with open_client(FakeLLMClient([None, line(KO)]), timeout_s=0.5) as client:
        case_id, token = send_case(client)
        with pair(client, case_id, token) as (worker, staff):
            worker.send_json({"type": "caption", "text": VI})
            worker.send_json({"type": "caption", "text": "Đau quá"})
            assert [staff.receive_json()["caption"]["id"] for _ in range(2)] == ["c-2", "c-1"]
            for _ in range(2):
                worker.receive_json()
        with client.websocket_connect(url(case_id, "center")) as staff:
            history = greet(staff, "center", [])
    assert [(c["id"], c["text"], c["translation"]) for c in history] == [("c-1", VI, "skipped"), ("c-2", "Đau quá", "ok")]


def test_reset_clears_captions_and_numbering(open_client):
    with open_client() as client:
        case_id, token = send_case(client)
        with pair(client, case_id, token) as (worker, staff):
            worker.send_json({"type": "caption", "text": VI})
            assert staff.receive_json()["caption"]["id"] == "c-1"
            worker.receive_json()
        assert client.post("/api/center/reset").status_code == 204
        # 데모 초기화는 live 사례도 지우므로 새로 보낸 사례에서 본다. mock 사례로도 자막이 비었는지 본다.
        with client.websocket_connect(url("C-1001", "center")) as staff:
            assert greet(staff, "center", []) == []
        assert center.store.captions(case_id) == []
        case_id, token = send_case(client)
        with pair(client, case_id, token) as (worker, staff):
            worker.send_json({"type": "caption", "text": VI})
            assert staff.receive_json()["caption"]["id"] == "c-1"


def test_log_has_no_token_sdp_or_caption(open_client, caplog):
    caplog.set_level(logging.INFO, logger="app")
    fake = FakeLLMClient([line(KO)])
    with open_client(fake) as client:
        case_id, token = send_case(client)
        with pair(client, case_id, token) as (worker, staff):
            worker.send_json({"type": "signal", "data": {"sdp": f"v=0 {MARKER}-sdp"}})
            staff.receive_json()
            worker.send_json({"type": "caption", "text": f"{VI} {MARKER}-text"})
            staff.receive_json()
            worker.receive_json()
    lines = [r.getMessage() for r in caplog.records if r.name.startswith("app")]
    assert any(m.startswith(f"WS /api/center/cases/{case_id}/call ") for m in lines)
    assert "call caption translation=ok" in lines
    assert not [m for m in lines if MARKER in m or KO in m or VI in m or token in m or "?" in m]
