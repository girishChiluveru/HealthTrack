import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from tests.conftest import ALLOWED_ORIGIN, build_settings


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


def test_preflight_allows_authenticated_json_post(client: TestClient) -> None:
    response = client.options(
        "/api/auth/login",
        headers={
            "Origin": ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization, content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN


@pytest.mark.parametrize("method", ["PATCH", "DELETE"])
def test_preflight_allows_entry_changes(client: TestClient, method: str) -> None:
    response = client.options(
        "/api/symptoms/00000000-0000-0000-0000-000000000000",
        headers={
            "Origin": ALLOWED_ORIGIN,
            "Access-Control-Request-Method": method,
            "Access-Control-Request-Headers": "authorization, content-type",
        },
    )

    assert response.status_code == 200


def test_cors_origins_are_parsed_from_comma_separated_value() -> None:
    settings = build_settings(cors_origins="http://localhost:5173, https://app.example ,")

    assert settings.cors_origins == ["http://localhost:5173", "https://app.example"]


@pytest.mark.parametrize("value", ["*", "http://localhost:5173,*"])
def test_wildcard_cors_origin_is_rejected(value: str) -> None:
    with pytest.raises(ValidationError, match="wildcard"):
        build_settings(cors_origins=value)
