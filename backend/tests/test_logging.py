"""로그에는 경로·상태 코드·소요 시간·request_id만 남고 본문·쿼리·예외 메시지는 남지 않는다."""

import logging

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.main import create_app
from app.middleware import REQUEST_ID_HEADER

MARKER = "chest-pain-synthetic-must-not-be-logged-3e7f"


class Probe(BaseModel):
    text: str
    consent: bool


@pytest.fixture
def logged_client(caplog: pytest.LogCaptureFixture) -> TestClient:
    caplog.set_level(logging.DEBUG)
    app = create_app()

    @app.post("/api/v1/_probe/echo")
    async def echo(body: Probe) -> dict[str, int]:
        return {"length": len(body.text)}

    @app.post("/api/v1/_probe/crash")
    async def crash(body: Probe) -> None:
        raise ValueError(body.text)

    return TestClient(app, raise_server_exceptions=False)


def _server_log(caplog: pytest.LogCaptureFixture) -> str:
    # httpx 로그는 테스트 클라이언트가 보낸 URL이므로 서버 로그가 아니다.
    return "\n".join(r.getMessage() for r in caplog.records if not r.name.startswith("httpx"))


def _access_messages(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [r.getMessage() for r in caplog.records if r.name == "app.access"]


@pytest.mark.parametrize(
    ("method", "path", "status"),
    [
        ("POST", "/api/v1/_probe/echo", 200),
        ("POST", "/api/v1/_probe/crash", 500),
        ("POST", "/api/v1/health", 405),
    ],
)
def test_body_and_query_are_not_logged(
    logged_client: TestClient,
    caplog: pytest.LogCaptureFixture,
    method: str,
    path: str,
    status: int,
) -> None:
    response = logged_client.request(
        method,
        path,
        params={"q": MARKER},
        json={"text": MARKER, "consent": True},
    )

    assert response.status_code == status
    [message] = _access_messages(caplog)
    request_id = response.headers[REQUEST_ID_HEADER]
    assert message.startswith(f"path={path!r} status={status} duration_ms=")
    assert message.endswith(f" request_id={request_id}")
    assert MARKER not in _server_log(caplog)


def test_validation_failure_is_not_logged_with_input(
    logged_client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    response = logged_client.post("/api/v1/_probe/echo", json={"text": MARKER, "consent": MARKER})

    assert response.status_code == 422
    assert MARKER not in _server_log(caplog)


def test_unhandled_exception_logs_only_type(
    logged_client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    response = logged_client.post("/api/v1/_probe/crash", json={"text": MARKER, "consent": True})

    request_id = response.headers[REQUEST_ID_HEADER]
    errors = [r for r in caplog.records if r.name == "app.error"]
    assert [r.getMessage() for r in errors] == [f"unhandled=ValueError request_id={request_id}"]
    assert all(r.exc_info is None for r in caplog.records)
    assert MARKER not in _server_log(caplog)
