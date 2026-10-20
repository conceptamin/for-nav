import pytest
from fastapi.testclient import TestClient


def test_health_returns_json_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize("path", ["/api/v1/unknown", "/api/v1/health/extra", "/api/v1/"])
def test_undefined_api_path_is_json_404(client: TestClient, path: str) -> None:
    response = client.get(path)

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/json"
    assert "<html" not in response.text.lower()


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/docs/oauth2-redirect"])
def test_interactive_docs_are_not_served(client: TestClient, path: str) -> None:
    response = client.get(path)

    assert response.status_code == 404
    assert "swagger" not in response.text.lower()
    assert "redoc" not in response.text.lower()


def test_health_rejects_other_methods(client: TestClient) -> None:
    assert client.post("/api/v1/health").status_code == 405
