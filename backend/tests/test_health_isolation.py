"""health가 DB·파일·외부 네트워크·환경 변수 없이 응답하는지 확인한다."""

import builtins
import os
import socket
from collections.abc import Coroutine
from typing import Any, NoReturn

import pytest
from fastapi.testclient import TestClient

from app.api.health import get_health

SECRET = "health-must-not-echo-this-7f3a"


def _forbidden(*args: object, **kwargs: object) -> NoReturn:
    raise AssertionError("health 처리 중 금지된 I/O를 시도했다")


class _ForbiddenEnviron(dict[str, str]):
    def __getitem__(self, key: str) -> NoReturn:
        _forbidden()

    def get(self, *args: object, **kwargs: object) -> NoReturn:
        _forbidden()


def _forbid_io(monkeypatch: pytest.MonkeyPatch) -> None:
    # DB 드라이버·HTTP 클라이언트·설정 로더가 모두 거치는 진입점을 막는다.
    monkeypatch.setattr(builtins, "open", _forbidden)
    monkeypatch.setattr(os, "open", _forbidden)
    monkeypatch.setattr(socket.socket, "connect", _forbidden)
    monkeypatch.setattr(socket, "create_connection", _forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", _forbidden)
    monkeypatch.setattr(os, "getenv", _forbidden)
    monkeypatch.setattr(os, "environ", _ForbiddenEnviron())


def _run_without_suspending(coro: Coroutine[Any, Any, dict[str, str]]) -> dict[str, str]:
    # 이벤트 루프 없이 실행한다. 대기 지점(I/O)이 있으면 한 번에 끝나지 않는다.
    try:
        coro.send(None)
    except StopIteration as stop:
        result: dict[str, str] = stop.value
        return result
    coro.close()
    raise AssertionError("health handler가 대기했다")


def test_handler_runs_without_io(monkeypatch: pytest.MonkeyPatch) -> None:
    _forbid_io(monkeypatch)

    assert _run_without_suspending(get_health()) == {"status": "ok"}


def test_health_request_does_not_touch_io_or_leak_env(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # 내부 정보가 응답에 섞이면 드러나도록 같은 값을 환경 변수에 둔다.
    for name in ("FORNAV_API_HOST", "FORNAV_API_PORT", "FORNAV_TOKEN", "DATABASE_URL"):
        monkeypatch.setenv(name, SECRET)
    # 첫 요청에서 Pydantic이 응답 직렬화기를 만들며 플러그인 설정을 1회 읽는다. 예열 후 막는다.
    assert client.get("/api/v1/health").status_code == 200
    _forbid_io(monkeypatch)

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert SECRET not in response.text
    assert os.getcwd() not in response.text
