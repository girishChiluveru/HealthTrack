"""Request validation for the auth endpoints. No database is reached."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.schemas import RegisterRequest

VALID_REGISTRATION = {
    "name": "Test Patient",
    "email": "patient@example.com",
    "password": "correct-horse",
    "role": "patient",
}


def registration(**overrides: object) -> dict:
    return VALID_REGISTRATION | overrides


def error_fields(response) -> set[str]:
    return {error["field"] for error in response.json()["errors"]}


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"password": "seven77"}, "password"),
        ({"password": "x" * 129}, "password"),
        ({"email": "not-an-email"}, "email"),
        ({"role": "admin"}, "role"),
        ({"name": "   "}, "name"),
        ({"name": "x" * 101}, "name"),
        ({"name": "nul\x00byte"}, "name"),
        ({"timezone": "Mars/Olympus"}, "timezone"),
        ({"timezone": "asia/kolkata"}, "timezone"),
        ({"timezone": ""}, "timezone"),
        ({"timezone": "../../etc/passwd"}, "timezone"),
    ],
)
def test_invalid_registration_identifies_the_field(
    client: TestClient, mock_db: MagicMock, overrides: dict, field: str
) -> None:
    response = client.post("/api/auth/register", json=registration(**overrides))

    assert response.status_code == 422
    assert response.json()["detail"] == "Validation failed"
    assert error_fields(response) == {field}
    mock_db.commit.assert_not_called()


@pytest.mark.parametrize("field", ["name", "email", "password", "role"])
def test_missing_field_is_reported(client: TestClient, mock_db: MagicMock, field: str) -> None:
    body = {key: value for key, value in VALID_REGISTRATION.items() if key != field}

    response = client.post("/api/auth/register", json=body)

    assert response.status_code == 422
    assert error_fields(response) == {field}


def test_validation_errors_never_echo_the_submitted_password(
    client: TestClient, mock_db: MagicMock
) -> None:
    response = client.post("/api/auth/register", json=registration(password="s3cret!"))

    assert response.status_code == 422
    assert "s3cret!" not in response.text


def test_malformed_json_is_a_validation_error(client: TestClient, mock_db: MagicMock) -> None:
    response = client.post(
        "/api/auth/login", content="{not json", headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Validation failed"


def test_timezone_defaults_when_omitted_or_null() -> None:
    assert RegisterRequest(**registration()).timezone == "Asia/Kolkata"
    assert RegisterRequest(**registration(timezone=None)).timezone == "Asia/Kolkata"


def test_valid_timezone_is_kept() -> None:
    assert RegisterRequest(**registration(timezone="Pacific/Auckland")).timezone == (
        "Pacific/Auckland"
    )


def test_email_is_lowercased_and_name_trimmed() -> None:
    data = RegisterRequest(**registration(email="MixedCase@Example.COM", name="  Asha  "))

    assert data.email == "mixedcase@example.com"
    assert data.name == "Asha"


def test_eight_character_password_is_accepted() -> None:
    assert RegisterRequest(**registration(password="12345678")).password == "12345678"
