"""Auth flows against real PostgreSQL. Run with `pytest -m integration`."""

import logging

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.models import User, UserRole

pytestmark = pytest.mark.integration

PASSWORD = "correct-horse"


def register(client: TestClient, **overrides: object):
    body = {
        "name": "Test Patient",
        "email": "patient@example.com",
        "password": PASSWORD,
        "role": "patient",
    }
    return client.post("/api/auth/register", json=body | overrides)


def login(client: TestClient, email: str = "patient@example.com", password: str = PASSWORD):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def bearer(response) -> dict[str, str]:
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def find_user(db: Session, email: str) -> User:
    return db.scalars(select(User).where(User.email == email)).one()


def test_register_patient(db_client: TestClient, db_session: Session) -> None:
    response = register(db_client)

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "name", "email", "role", "timezone", "created_at"}
    assert body["role"] == "patient"
    assert body["timezone"] == "Asia/Kolkata"
    assert find_user(db_session, "patient@example.com").role == "patient"


def test_register_doctor_with_timezone(db_client: TestClient) -> None:
    response = register(
        db_client, email="doctor@example.com", role="doctor", timezone="Europe/London"
    )

    assert response.status_code == 201
    assert response.json()["role"] == "doctor"
    assert response.json()["timezone"] == "Europe/London"


def test_password_is_stored_only_as_an_argon2_hash(
    db_client: TestClient, db_session: Session
) -> None:
    response = register(db_client)

    stored = find_user(db_session, "patient@example.com")
    assert stored.password_hash.startswith("$argon2id$")
    assert PASSWORD not in stored.password_hash
    assert "password" not in response.text
    assert stored.password_hash not in response.text


def test_email_is_stored_lowercase(db_client: TestClient, db_session: Session) -> None:
    response = register(db_client, email="MixedCase@Example.COM")

    assert response.json()["email"] == "mixedcase@example.com"
    assert find_user(db_session, "mixedcase@example.com")


def test_duplicate_email_is_rejected_regardless_of_case(
    db_client: TestClient, db_session: Session
) -> None:
    register(db_client)

    response = register(db_client, email="PATIENT@example.com", role="doctor")

    assert response.status_code == 409
    assert response.json() == {"detail": "An account with this email already exists"}
    assert find_user(db_session, "patient@example.com").role == "patient"


def test_login_succeeds_and_token_loads_the_user(db_client: TestClient) -> None:
    register(db_client)

    response = login(db_client)

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    me = db_client.get("/api/auth/me", headers=bearer(response))
    assert me.status_code == 200
    assert me.json()["email"] == "patient@example.com"


def test_login_is_case_insensitive_for_email(db_client: TestClient) -> None:
    register(db_client)

    assert login(db_client, email="PATIENT@EXAMPLE.COM").status_code == 200


def test_wrong_password_and_unknown_email_look_identical(db_client: TestClient) -> None:
    register(db_client)

    wrong_password = login(db_client, password="wrong-password")
    unknown_email = login(db_client, email="nobody@example.com")

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json() == {"detail": "Invalid email or password"}


def test_short_password_at_login_is_a_normal_failure(db_client: TestClient) -> None:
    register(db_client)

    assert login(db_client, password="short").status_code == 401


def test_token_stops_working_when_user_is_removed(
    db_client: TestClient, db_session: Session
) -> None:
    register(db_client)
    headers = bearer(login(db_client))

    db_session.delete(find_user(db_session, "patient@example.com"))
    db_session.commit()

    assert db_client.get("/api/auth/me", headers=headers).status_code == 401


def test_role_comes_from_the_database_not_the_token(
    app: FastAPI, db_client: TestClient, db_session: Session
) -> None:
    @app.get("/api/test-doctor-only", dependencies=[Depends(require_role(UserRole.DOCTOR))])
    def doctor_only() -> dict[str, bool]:
        return {"ok": True}

    register(db_client)
    headers = bearer(login(db_client))
    assert db_client.get("/api/test-doctor-only", headers=headers).status_code == 403

    find_user(db_session, "patient@example.com").role = UserRole.DOCTOR
    db_session.commit()

    assert db_client.get("/api/test-doctor-only", headers=headers).status_code == 200


def test_passwords_and_tokens_are_not_logged(
    db_client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)

    register(db_client)
    response = login(db_client)
    db_client.get("/api/auth/me", headers=bearer(response))

    assert PASSWORD not in caplog.text
    assert response.json()["access_token"] not in caplog.text
