from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from tests.conftest import ALLOWED_ORIGIN


def test_unexpected_error_returns_generic_response(app: FastAPI, client: TestClient) -> None:
    @app.get("/api/test-failure")
    def fail() -> None:
        raise RuntimeError("password=super-secret")

    response = client.get("/api/test-failure", headers={"Origin": ALLOWED_ORIGIN})

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert "super-secret" not in response.text
    assert "Traceback" not in response.text
    # Without this header a browser would report a network failure instead of the 500.
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN


def test_settings_repr_hides_secrets(settings: Settings) -> None:
    assert "unused:unused" not in repr(settings)
    assert settings.jwt_secret.get_secret_value() not in repr(settings)
