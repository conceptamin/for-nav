# 공통 오류 형식, X-Request-Id, 접근 로그. 요청 본문·쿼리 문자열·헤더가 로그에 남지 않는지 표식 문자열로 확인한다.

import logging

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers import worker

client = TestClient(app)

MARKER = "MARKER-7f3a-do-not-log"

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


@pytest.fixture(autouse=True)
def _capture(caplog):
    caplog.set_level(logging.DEBUG)


def server_log(caplog) -> str:
    """서버 쪽 로그만 모은다. 테스트 클라이언트(httpx)는 요청 URL을 자체 로그로 남기므로 뺀다."""
    fmt = logging.Formatter("%(name)s %(message)s")
    return "\n".join(fmt.format(r) for r in caplog.records if not r.name.startswith("httpx"))


def assert_error(r, status: int, code: str) -> dict:
    assert r.status_code == status
    body = r.json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message", "requestId"}
    assert body["error"]["code"] == code
    assert body["error"]["message"]
    assert body["error"]["requestId"] == r.headers["X-Request-Id"]
    return body["error"]


def test_success_has_request_id():
    r = client.get("/api/health")
    assert r.json() == {"ok": True}
    assert len(r.headers["X-Request-Id"]) == 32


def test_client_request_id_is_kept():
    r = client.get("/api/health", headers={"X-Request-Id": "front-123.a_b"})
    assert r.headers["X-Request-Id"] == "front-123.a_b"


def test_unsafe_request_id_is_replaced():
    r = client.get("/api/health", headers={"X-Request-Id": "a b<script>"})
    assert r.headers["X-Request-Id"] != "a b<script>"
    assert len(r.headers["X-Request-Id"]) == 32


def test_422_format_and_no_body_in_log(caplog):
    r = client.post("/api/triage", json={**INTAKE, "freeText": MARKER, "bodyParts": [MARKER], "language": MARKER})
    err = assert_error(r, 422, "VALIDATION")
    assert "body.bodyParts.0" in err["message"] and "body.language" in err["message"]
    assert MARKER not in r.text
    assert MARKER not in server_log(caplog)
    assert "POST /api/triage 422" in server_log(caplog)
    assert err["requestId"] in server_log(caplog)


def test_422_broken_json_not_logged(caplog):
    r = client.post("/api/triage", content=f'{{"freeText": "{MARKER}"', headers={"content-type": "application/json"})
    assert_error(r, 422, "VALIDATION")
    assert MARKER not in server_log(caplog)


def test_422_from_route_check():
    err = assert_error(client.get("/api/center/stats", params={"days": 7}), 422, "VALIDATION")
    assert "days" in err["message"]


def test_404_format():
    assert assert_error(client.get("/api/center/cases/C-0"), 404, "NOT_FOUND")["message"] == "사례 C-0를 찾을 수 없다"
    assert_error(client.patch("/api/center/cases/C-0", json={"status": "done"}), 404, "NOT_FOUND")
    assert_error(client.get("/api/nope"), 404, "NOT_FOUND")


def test_500_format_and_no_body_in_log(caplog, monkeypatch):
    def boom(intake):
        raise RuntimeError(f"failed on {intake.free_text}")

    monkeypatch.setattr(worker, "triage", boom)
    r = client.post("/api/triage", json={**INTAKE, "freeText": MARKER})
    err = assert_error(r, 500, "INTERNAL")
    assert MARKER not in r.text
    assert MARKER not in server_log(caplog)
    assert "RuntimeError" in server_log(caplog) and "boom" in server_log(caplog)
    assert "POST /api/triage 500" in server_log(caplog)
    assert err["requestId"] in server_log(caplog)


def test_access_log_has_no_query_or_headers(caplog):
    r = client.get("/api/center/cases", params={"status": "new", "since": "2026-10-01T00:00:00+09:00"}, headers={"X-Note": MARKER})
    assert r.status_code == 200
    lines = [rec.getMessage() for rec in caplog.records if rec.name == "app.access"]
    assert len(lines) == 1
    assert lines[0].startswith("GET /api/center/cases 200 ")
    assert lines[0].endswith(f"request_id={r.headers['X-Request-Id']}")
    assert "status=" not in server_log(caplog) and "since" not in server_log(caplog) and MARKER not in server_log(caplog)


def test_cors_exposes_request_id():
    r = client.get("/api/health", headers={"Origin": "http://localhost:5180"})
    assert r.headers["access-control-allow-origin"] == "http://localhost:5180"
    assert "X-Request-Id" in r.headers["access-control-expose-headers"]
