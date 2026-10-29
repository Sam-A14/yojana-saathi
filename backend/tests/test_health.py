from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app

client = TestClient(app)


def test_health_returns_status_and_version() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": get_settings().app_version}


def test_cors_allows_configured_frontend_origin() -> None:
    origin = get_settings().frontend_url
    response = client.get("/health", headers={"Origin": origin})

    assert response.headers["access-control-allow-origin"] == origin


def test_cors_rejects_other_origins() -> None:
    response = client.get("/health", headers={"Origin": "https://evil.example"})

    assert "access-control-allow-origin" not in response.headers
