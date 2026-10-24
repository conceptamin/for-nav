from typing import Any

import pytest
import uvicorn
from fastapi import FastAPI

import app.__main__ as entrypoint
from app.logs import LOG_CONFIG
from app.settings import HOST_ENV, PORT_ENV


def test_run_command_uses_single_worker_and_own_access_log(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[Any, dict[str, Any]]] = []
    monkeypatch.setattr(uvicorn, "run", lambda app, **kw: calls.append((app, kw)))
    monkeypatch.delenv(HOST_ENV, raising=False)
    monkeypatch.delenv(PORT_ENV, raising=False)

    entrypoint.main()

    [(app, kwargs)] = calls
    assert isinstance(app, FastAPI)
    assert kwargs == {
        "host": "127.0.0.1",
        "port": 8000,
        "workers": 1,
        "reload": False,
        "access_log": False,
        "log_config": LOG_CONFIG,
    }


def test_run_command_exits_on_invalid_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(PORT_ENV, "not-a-port")
    monkeypatch.setattr(uvicorn, "run", pytest.fail)

    with pytest.raises(SystemExit, match="설정 오류"):
        entrypoint.main()
