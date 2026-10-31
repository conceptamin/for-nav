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


# 앱용 웹 빌드 호스트별 서빙(backlog 22). STATIC_DIR은 frontend, APP_STATIC_DIR은 app-front 빌드다.
APP_INDEX = "<!doctype html><title>for nav app</title>"


@pytest.fixture
def two_builds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    web, app_web = tmp_path / "web", tmp_path / "app"
    for root, index, asset in ((web, INDEX, "web.js"), (app_web, APP_INDEX, "app.js")):
        (root / "assets").mkdir(parents=True)
        (root / "index.html").write_text(index)
        (root / "assets" / asset).write_text(asset)
    (tmp_path / "secret.txt").write_text("secret")
    patched = dataclasses.replace(app_settings.settings, static_dir=str(web), app_static_dir=str(app_web), app_hosts=("app.for-nav.com",))
    monkeypatch.setattr(app_settings, "settings", patched)
    main = importlib.reload(importlib.import_module("app.main"))
    yield TestClient(main.app)
    monkeypatch.undo()
    importlib.reload(main)


@pytest.mark.parametrize("host", ["app.for-nav.com", "APP.For-Nav.com", "app.for-nav.com:443"])
@pytest.mark.parametrize("path", ["/", "/intake", "/__host"])
def test_app_host_gets_app_build(two_builds: TestClient, host: str, path: str):
    r = two_builds.get(path, headers={"host": host})
    assert r.status_code == 200
    assert r.text == APP_INDEX


@pytest.mark.parametrize("host", ["www.for-nav.com", "for-nav.com", "localhost:8000", "app.for-nav.com.evil.test"])
def test_other_hosts_get_default_build(two_builds: TestClient, host: str):
    r = two_builds.get("/center", headers={"host": host})
    assert r.status_code == 200
    assert r.text == INDEX


def test_assets_come_from_the_chosen_build(two_builds: TestClient):
    app_host, www = {"host": "app.for-nav.com"}, {"host": "www.for-nav.com"}
    assert two_builds.get("/assets/app.js", headers=app_host).text == "app.js"
    assert two_builds.get("/assets/web.js", headers=app_host).status_code == 404
    assert two_builds.get("/assets/web.js", headers=www).text == "web.js"
    assert two_builds.get("/assets/app.js", headers=www).status_code == 404


@pytest.mark.parametrize("host", ["app.for-nav.com", "www.for-nav.com"])
def test_both_builds_keep_api_first_and_stay_inside(two_builds: TestClient, host: str):
    assert two_builds.get("/api/health", headers={"host": host}).json() == {"ok": True}
    assert two_builds.get("/api/nope", headers={"host": host}).status_code == 404
    r = two_builds.get("/%2e%2e/secret.txt", headers={"host": host})
    assert r.status_code == 404
    assert "secret" not in r.text


def test_app_static_settings(tmp_path: Path):
    web, app_web = tmp_path / "web", tmp_path / "app"
    web.mkdir()
    app_web.mkdir()
    (web / "index.html").write_text(INDEX)
    with pytest.raises(ValueError, match="APP_STATIC_DIR"):
        load_settings({"STATIC_DIR": str(web), "APP_STATIC_DIR": str(app_web), "APP_HOSTS": "app.for-nav.com"})
    (app_web / "index.html").write_text(APP_INDEX)
    s = load_settings({"STATIC_DIR": str(web), "APP_STATIC_DIR": str(app_web), "APP_HOSTS": " App.For-Nav.com , "})
    assert (s.app_static_dir, s.app_hosts) == (str(app_web), ("app.for-nav.com",))
    with pytest.raises(ValueError, match="함께"):
        load_settings({"STATIC_DIR": str(web), "APP_STATIC_DIR": str(app_web)})
    with pytest.raises(ValueError, match="함께"):
        load_settings({"STATIC_DIR": str(web), "APP_HOSTS": "app.for-nav.com"})
    with pytest.raises(ValueError, match="STATIC_DIR도"):
        load_settings({"APP_STATIC_DIR": str(app_web), "APP_HOSTS": "app.for-nav.com"})
    # 둘 다 없으면 지금과 같다
    assert load_settings({"STATIC_DIR": str(web)}).app_hosts == ()
