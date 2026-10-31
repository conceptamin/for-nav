# LLM 호출 제한(backlog 20): IP별 60초 창, 서버 전체 하루, 넘으면 대체 동작, 재시도 없음, IP 헤더는 루프백일 때만, 로그에 IP 없음.
# LLM은 FakeLLMClient로 바꾸고 외부 네트워크를 쓰지 않는다. 시각은 clock을 고정해 옮긴다.

import json
import logging
from datetime import datetime, timedelta

import pytest
from fakes import FakeLLMClient
from fastapi.testclient import TestClient
from starlette.requests import HTTPConnection
from test_call import KO, VI, line, pair, send_case

from app import clock
from app.chat import CallHub
from app.llm_limit import LLMLimiter, client_key
from app.main import app
from app.routers import center
from app.store import MemoryStore

AT = datetime(2026, 10, 31, 23, 59, 0, tzinfo=clock.SEOUL)
INTAKE = {
    "id": "in-test",
    "language": "vi",
    "bodyParts": [],
    "symptoms": [],
    "freeText": "Ngón tay bị kẹp vào máy dập, bị sưng.",
    "onset": None,
    "workRelated": None,
    "workType": None,
    "industry": None,
    "district": None,
    "createdAt": "2026-10-26T01:00:00.000Z",
}
LLM_OUT = json.dumps({"bodyParts": ["hand"], "symptoms": ["swelling"], "onset": "today", "workRelated": None, "workType": "machine"})
TRANSLATE_OUT = json.dumps({"ko": "프레스 기계에 손가락이 끼여서 부었습니다."}, ensure_ascii=False)
CLINICIAN = {"intake": INTAKE, "included": ["symptoms", "note"], "profile": None, "meds": ""}
TUNNEL = ("127.0.0.1", 50000)


@pytest.fixture
def limited(monkeypatch):
    """가짜 LLM과 제한값으로 앱 상태를 바꾸고, 옮길 수 있는 시각을 돌려준다."""
    now = {"t": AT}
    monkeypatch.setattr(clock, "now", lambda: now["t"])

    def make(llm: FakeLLMClient, per_min: int = 0, daily: int = 0, header: str = "") -> dict:
        monkeypatch.setattr(app.state, "llm", llm, raising=False)
        monkeypatch.setattr(app.state, "llm_limiter", LLMLimiter(per_min, daily, header))
        return now

    return make


def source(peer: str = "testclient", forwarded: str | None = None) -> str:
    headers = {"cf-connecting-ip": forwarded} if forwarded else {}
    client = TestClient(app, client=(peer, 50000))
    return client.post("/api/extract", json={"intake": INTAKE}, headers=headers).json()["source"]


def test_per_ip_limit_falls_back_to_keywords_and_recovers(limited):
    fake = FakeLLMClient([LLM_OUT] * 10)
    now = limited(fake, per_min=3)

    assert [source() for _ in range(4)] == ["llm", "llm", "llm", "keywords"]
    assert len(fake.prompts) == 3
    # 다른 IP는 따로 센다.
    assert source("10.0.0.2") == "llm"
    # 60초 창이 지나면 다시 부른다.
    now["t"] = AT + timedelta(seconds=61)
    assert source() == "llm"
    assert len(fake.prompts) == 5


def test_daily_limit_is_server_wide_and_resets_at_seoul_midnight(limited):
    fake = FakeLLMClient([LLM_OUT] * 10)
    now = limited(fake, daily=2)

    assert [source("10.0.0.1"), source("10.0.0.2"), source("10.0.0.3")] == ["llm", "llm", "keywords"]
    now["t"] = AT + timedelta(seconds=30)
    assert source("10.0.0.4") == "keywords"
    # Asia/Seoul 자정(AT는 23:59)이 지나면 새 날이다.
    now["t"] = AT + timedelta(seconds=61)
    assert source("10.0.0.1") == "llm"
    assert len(fake.prompts) == 3


def test_translation_limited_midway_is_skipped_without_retry(limited, caplog):
    fake = FakeLLMClient([TRANSLATE_OUT])
    limited(fake, per_min=1)

    with caplog.at_level(logging.INFO):
        res = TestClient(app).post("/api/report/clinician", json=CLINICIAN)

    assert res.status_code == 200
    assert res.json()["translation"] == {"status": "skipped"}
    # 번역 1번은 불렀고, 역번역은 막혀 다시 시도하지 않는다.
    assert len(fake.prompts) == 1
    attempts = [r.getMessage() for r in caplog.records if r.getMessage().startswith("llm attempt=")]
    assert attempts == ["llm attempt=1/2 failed=LLMError/limited"]


def test_forwarded_ip_counts_only_from_loopback(limited):
    fake = FakeLLMClient([LLM_OUT] * 10)
    limited(fake, per_min=1, header="cf-connecting-ip")

    # 터널(루프백) 뒤의 두 사용자는 헤더 값으로 따로 센다.
    assert source(TUNNEL[0], "203.0.113.7") == "llm"
    assert source(TUNNEL[0], "203.0.113.8") == "llm"
    assert source(TUNNEL[0], "203.0.113.7") == "keywords"
    # 직접 붙은 클라이언트가 헤더를 꾸며도 상대 주소로 센다.
    assert source("10.0.0.9", "203.0.113.99") == "llm"
    assert source("10.0.0.9", "203.0.113.100") == "keywords"


@pytest.mark.parametrize(
    ("peer", "header", "sent", "key"),
    [
        ("127.0.0.1", "cf-connecting-ip", "203.0.113.7", "203.0.113.7"),
        ("::1", "cf-connecting-ip", "203.0.113.7", "203.0.113.7"),
        ("10.0.0.9", "cf-connecting-ip", "203.0.113.7", "10.0.0.9"),
        ("127.0.0.1", "", "203.0.113.7", "127.0.0.1"),
        ("127.0.0.1", "cf-connecting-ip", None, "127.0.0.1"),
    ],
    ids=["tunnel", "tunnel-v6", "spoofed", "header-off", "header-missing"],
)
def test_client_key(peer, header, sent, key):
    headers = [(b"cf-connecting-ip", sent.encode())] if sent else []
    conn = HTTPConnection({"type": "http", "client": (peer, 1), "headers": headers})
    assert client_key(conn, header) == key


def test_off_by_default_keeps_client_unwrapped(limited):
    fake = FakeLLMClient([LLM_OUT] * 5)
    limited(fake)

    conn = HTTPConnection({"type": "http", "client": TUNNEL, "headers": []})
    assert LLMLimiter().wrap(fake, conn) is fake
    assert [source() for _ in range(5)] == ["llm"] * 5


def test_log_has_scope_but_no_ip(limited, caplog):
    limited(FakeLLMClient([LLM_OUT]), per_min=1, header="cf-connecting-ip")

    with caplog.at_level(logging.INFO):
        source(TUNNEL[0], "203.0.113.7")
        source(TUNNEL[0], "203.0.113.7")

    text = caplog.text
    assert "llm limited scope=ip" in text
    assert "203.0.113.7" not in text


def test_call_caption_over_limit_is_sent_as_original(monkeypatch):
    fake = FakeLLMClient([line(KO)])
    monkeypatch.setattr(center, "store", MemoryStore())
    monkeypatch.setattr(clock, "now", lambda: AT)
    monkeypatch.setattr(app.state, "call", CallHub())
    monkeypatch.setattr(app.state, "llm_limiter", LLMLimiter(per_min=1))
    monkeypatch.setattr("app.main.get_llm_client", lambda: fake)

    with TestClient(app) as client:
        case_id, token = send_case(client)
        with pair(client, case_id, token) as (worker, staff):
            worker.send_json({"type": "caption", "text": VI})
            assert staff.receive_json()["caption"]["translation"] == "ok"
            worker.receive_json()
            worker.send_json({"type": "caption", "text": VI})
            c = staff.receive_json()["caption"]
            assert (c["text"], c["translated"], c["translation"]) == (VI, None, "skipped")
    assert len(fake.prompts) == 1
