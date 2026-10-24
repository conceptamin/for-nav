"""계약 1장의 공통 오류 형식과 request_id."""

import re

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.llm import LLMUnavailableError
from app.main import create_app
from app.middleware import REQUEST_ID_HEADER

MARKER = "symptom-text-must-not-be-echoed-91ab"
REQUEST_ID = re.compile(r"^req-[0-9a-f]{32}$")


class Probe(BaseModel):
    consent: bool


def _app_with_probe_routes() -> FastAPI:
    app = create_app()

    @app.post("/api/v1/_probe/validate")
    async def validate(body: Probe) -> dict[str, bool]:
        return {"consent": body.consent}

    @app.get("/api/v1/_probe/crash")
    async def crash() -> None:
        raise RuntimeError(MARKER)

    @app.get("/api/v1/_probe/llm")
    async def llm() -> None:
        raise LLMUnavailableError

    return app


@pytest.fixture
def probe_client() -> TestClient:
    # 500 응답을 받기 위해 서버 예외를 테스트로 다시 올리지 않는다.
    return TestClient(_app_with_probe_routes(), raise_server_exceptions=False)


def _assert_error(response_json: object, code: str, request_id: str) -> None:
    assert isinstance(response_json, dict)
    assert set(response_json) == {"error"}
    error = response_json["error"]
    assert set(error) == {"code", "message", "request_id"}
    assert error["code"] == code
    assert error["request_id"] == request_id
    assert isinstance(error["message"], str) and error["message"]


def test_success_response_carries_request_id_header(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert REQUEST_ID.match(response.headers[REQUEST_ID_HEADER])


def test_request_ids_are_unique(client: TestClient) -> None:
    ids = {client.get("/api/v1/health").headers[REQUEST_ID_HEADER] for _ in range(5)}

    assert len(ids) == 5


def test_not_found_uses_error_format(client: TestClient) -> None:
    response = client.get(f"/api/v1/{MARKER}")

    assert response.status_code == 404
    _assert_error(response.json(), "NOT_FOUND", response.headers[REQUEST_ID_HEADER])
    assert MARKER not in response.text


def test_method_not_allowed_keeps_allow_header(client: TestClient) -> None:
    response = client.post("/api/v1/health", content=MARKER)

    assert response.status_code == 405
    assert response.headers["allow"] == "GET"
    _assert_error(response.json(), "METHOD_NOT_ALLOWED", response.headers[REQUEST_ID_HEADER])


@pytest.mark.parametrize(
    "body",
    [
        f'{{"consent": "{MARKER}"}}',
        f'{{"consent": true, "extra": "{MARKER}"',  # JSON 깨짐
        f'{{"other": "{MARKER}"}}',
    ],
    ids=["wrong-type", "broken-json", "missing-field"],
)
def test_validation_error_does_not_echo_input(probe_client: TestClient, body: str) -> None:
    response = probe_client.post(
        "/api/v1/_probe/validate", content=body, headers={"content-type": "application/json"}
    )

    assert response.status_code == 422
    _assert_error(response.json(), "VALIDATION_ERROR", response.headers[REQUEST_ID_HEADER])
    assert MARKER not in response.text


def test_unhandled_exception_is_500_without_details(probe_client: TestClient) -> None:
    response = probe_client.get("/api/v1/_probe/crash")

    assert response.status_code == 500
    _assert_error(response.json(), "INTERNAL_ERROR", response.headers[REQUEST_ID_HEADER])
    assert MARKER not in response.text
    assert "RuntimeError" not in response.text


def test_llm_unavailable_is_503(probe_client: TestClient) -> None:
    response = probe_client.get("/api/v1/_probe/llm")

    assert response.status_code == 503
    _assert_error(response.json(), "LLM_UNAVAILABLE", response.headers[REQUEST_ID_HEADER])
