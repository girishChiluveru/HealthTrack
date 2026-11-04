"""Bearer-token and role checks, with the database mocked."""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.deps import require_role
from app.config import Settings
from app.models import User, UserRole
from app.security import create_access_token


def make_user(role: UserRole = UserRole.PATIENT) -> User:
    return User(
        id=uuid.uuid4(),
        name="Test User",
        email="user@example.com",
        password_hash="$argon2id$never-exposed",
        role=role,
        timezone="Asia/Kolkata",
        created_at=datetime.now(UTC),
    )


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def sign(settings: Settings, claims: dict) -> str:
    return jwt.encode(claims, settings.jwt_secret.get_secret_value(), algorithm="HS256")


def assert_unauthorized(response) -> None:
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}
    assert response.headers["www-authenticate"] == "Bearer"


def test_valid_token_loads_user_without_exposing_hash(
    client: TestClient, mock_db: MagicMock, settings: Settings
) -> None:
    user = make_user()
    mock_db.get.return_value = user

    response = client.get("/api/auth/me", headers=bearer(create_access_token(user.id, settings)))

    assert response.status_code == 200
    assert response.json()["email"] == "user@example.com"
    assert set(response.json()) == {"id", "name", "email", "role", "timezone", "created_at"}
    assert "argon2" not in response.text
    mock_db.get.assert_called_once_with(User, user.id)


def test_missing_token_is_rejected(client: TestClient, mock_db: MagicMock) -> None:
    assert_unauthorized(client.get("/api/auth/me"))


def test_non_bearer_scheme_is_rejected(client: TestClient, mock_db: MagicMock) -> None:
    assert_unauthorized(client.get("/api/auth/me", headers={"Authorization": "Basic abc"}))


@pytest.mark.parametrize("token", ["not-a-jwt", "a.b.c", ""])
def test_malformed_token_is_rejected(client: TestClient, mock_db: MagicMock, token: str) -> None:
    assert_unauthorized(client.get("/api/auth/me", headers=bearer(token)))


def test_expired_token_is_rejected(
    client: TestClient, mock_db: MagicMock, settings: Settings
) -> None:
    mock_db.get.return_value = make_user()
    token = sign(
        settings, {"sub": str(uuid.uuid4()), "exp": datetime.now(UTC) - timedelta(seconds=1)}
    )

    assert_unauthorized(client.get("/api/auth/me", headers=bearer(token)))
    mock_db.get.assert_not_called()


def test_tampered_token_is_rejected(
    client: TestClient, mock_db: MagicMock, settings: Settings
) -> None:
    mock_db.get.return_value = make_user()
    header, payload, signature = create_access_token(uuid.uuid4(), settings).split(".")
    flipped = ("A" if signature[0] != "A" else "B") + signature[1:]

    assert_unauthorized(client.get("/api/auth/me", headers=bearer(f"{header}.{payload}.{flipped}")))


def test_unsigned_token_is_rejected(client: TestClient, mock_db: MagicMock) -> None:
    mock_db.get.return_value = make_user()
    claims = {"sub": str(uuid.uuid4()), "exp": datetime.now(UTC) + timedelta(hours=1)}
    token = jwt.encode(claims, key=None, algorithm="none")

    assert_unauthorized(client.get("/api/auth/me", headers=bearer(token)))


@pytest.mark.parametrize(
    "claims",
    [
        {"sub": "not-a-uuid", "exp": datetime.now(UTC) + timedelta(hours=1)},
        {"exp": datetime.now(UTC) + timedelta(hours=1)},
        {"sub": str(uuid.uuid4())},
    ],
    ids=["non-uuid-subject", "no-subject", "no-expiry"],
)
def test_token_with_bad_claims_is_rejected(
    client: TestClient, mock_db: MagicMock, settings: Settings, claims: dict
) -> None:
    mock_db.get.return_value = make_user()

    assert_unauthorized(client.get("/api/auth/me", headers=bearer(sign(settings, claims))))


def test_token_for_a_user_no_longer_in_the_database_is_rejected(
    client: TestClient, mock_db: MagicMock, settings: Settings
) -> None:
    mock_db.get.return_value = None
    token = create_access_token(uuid.uuid4(), settings)

    assert_unauthorized(client.get("/api/auth/me", headers=bearer(token)))


@pytest.fixture
def doctor_only_route(app: FastAPI) -> str:
    path = "/api/test-doctor-only"

    @app.get(path, dependencies=[Depends(require_role(UserRole.DOCTOR))])
    def doctor_only() -> dict[str, bool]:
        return {"ok": True}

    return path


def test_required_role_is_allowed(
    client: TestClient, mock_db: MagicMock, settings: Settings, doctor_only_route: str
) -> None:
    user = make_user(UserRole.DOCTOR)
    mock_db.get.return_value = user

    response = client.get(doctor_only_route, headers=bearer(create_access_token(user.id, settings)))

    assert response.status_code == 200


def test_wrong_role_gets_403(
    client: TestClient, mock_db: MagicMock, settings: Settings, doctor_only_route: str
) -> None:
    user = make_user(UserRole.PATIENT)
    mock_db.get.return_value = user

    response = client.get(doctor_only_route, headers=bearer(create_access_token(user.id, settings)))

    assert response.status_code == 403
    assert response.json() == {"detail": "Forbidden"}


def test_role_check_without_token_gets_401(
    client: TestClient, mock_db: MagicMock, doctor_only_route: str
) -> None:
    assert_unauthorized(client.get(doctor_only_route))
