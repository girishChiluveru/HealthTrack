import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from tests.conftest import ALLOWED_ORIGIN


def build_settings(cors_origins: str) -> Settings:
    return Settings(
        _env_file=None,
        database_url="postgresql+psycopg://unused:unused@127.0.0.1:1/unused",
        cors_origins=cors_origins,
    )


def test_allowed_origin_receives_cors_header(client: TestClient) -> None:
    response = client.get("/api/health", headers={"Origin": ALLOWED_ORIGIN})

    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN


def test_unlisted_origin_receives_no_cors_header(client: TestClient) -> None:
    response = client.get("/api/health", headers={"Origin": "https://evil.example"})

    assert "access-control-allow-origin" not in response.headers


def test_preflight_from_unlisted_origin_is_rejected(client: TestClient) -> None:
    response = client.options(
        "/api/health",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"},
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_cors_origins_are_parsed_from_comma_separated_value() -> None:
    settings = build_settings("http://localhost:5173, https://app.example ,")

    assert settings.cors_origins == ["http://localhost:5173", "https://app.example"]


@pytest.mark.parametrize("value", ["*", "http://localhost:5173,*"])
def test_wildcard_cors_origin_is_rejected(value: str) -> None:
    with pytest.raises(ValidationError, match="wildcard"):
        build_settings(value)
