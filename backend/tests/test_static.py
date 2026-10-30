# 프론트 정적 파일 같은 출처 서빙(backlog 08). STATIC_DIR을 임시 폴더로 바꿔 app.main을 다시 불러온다.

import dataclasses
import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.settings as app_settings
from app.main import app as default_app
from app.settings import load_settings

INDEX = "<!doctype html><title>for nav</title>"


@pytest.fixture
def served(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    (tmp_path / "index.html").write_text(INDEX)
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app.js").write_text("console.log(1)")
    (tmp_path.parent / "secret.txt").write_text("secret")
    monkeypatch.setattr(app_settings, "settings", dataclasses.replace(app_settings.settings, static_dir=str(tmp_path)))
    main = importlib.reload(importlib.import_module("app.main"))
    yield TestClient(main.app)
    monkeypatch.undo()
    importlib.reload(main)


@pytest.mark.parametrize("path", ["/", "/center", "/center/cases/C-1001", "/없는경로"])
def test_front_routes_return_index(served: TestClient, path: str):
    r = served.get(path)
    assert r.status_code == 200
    assert r.text == INDEX
    assert r.headers["content-type"].startswith("text/html")


def test_existing_file_is_served(served: TestClient):
    r = served.get("/assets/app.js")
    assert r.status_code == 200
    assert r.text == "console.log(1)"


def test_missing_asset_is_404_not_index(served: TestClient):
    r = served.get("/assets/missing.js")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "NOT_FOUND"


def test_api_wins_over_static(served: TestClient):
    assert served.get("/api/health").json() == {"ok": True}
    assert len(served.get("/api/center/cases").json()) == 24


@pytest.mark.parametrize("path", ["/api", "/api/nope"])
def test_unknown_api_path_is_json_404(served: TestClient, path: str):
    r = served.get(path)
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "NOT_FOUND"


def test_cannot_read_outside_static_dir(served: TestClient):
    # 클라이언트는 %2e%2e를 그대로 보내고 서버는 ../secret.txt로 받는다.
    r = served.get("/%2e%2e/secret.txt")
    assert r.status_code == 404
    assert "secret" not in r.text


def test_without_static_dir_root_is_404():
    client = TestClient(default_app)
    assert client.get("/").status_code == 404
    assert client.get("/api/health").json() == {"ok": True}


def test_static_dir_needs_index(tmp_path: Path):
    with pytest.raises(ValueError, match="STATIC_DIR"):
        load_settings({"STATIC_DIR": str(tmp_path)})
    (tmp_path / "index.html").write_text(INDEX)
    assert load_settings({"STATIC_DIR": str(tmp_path)}).static_dir == str(tmp_path)
