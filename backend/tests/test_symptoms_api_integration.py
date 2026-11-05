"""Symptom batches against real PostgreSQL. Run with `pytest -m integration`."""

import logging
import uuid
from collections.abc import Callable, Iterator
from datetime import UTC, date, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import SymptomEntry, User, UserRole
from app.schemas import SymptomEntryCreate
from app.security import create_access_token
from app.services import symptoms
from app.services.symptoms import save_entries

pytestmark = pytest.mark.integration

URL = "/api/symptoms/batch"


def make_user(db: Session, role: UserRole, timezone: str = "UTC") -> User:
    user = User(
        name="Test User",
        email=f"{uuid.uuid4()}@example.com",
        password_hash="$argon2id$placeholder",
        role=role,
        timezone=timezone,
    )
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def headers_for(settings: Settings) -> Callable[[User], dict[str, str]]:
    def build(user: User) -> dict[str, str]:
        return {"Authorization": f"Bearer {create_access_token(user.id, settings)}"}

    return build


@pytest.fixture
def patient(db_session: Session) -> User:
    return make_user(db_session, UserRole.PATIENT)


@pytest.fixture
def patient_headers(patient: User, headers_for: Callable) -> dict[str, str]:
    return headers_for(patient)


def entry(**overrides: object) -> dict:
    values = {"symptom_name": "Headache", "occurred_on": "2026-01-15", "severity": 5}
    return values | overrides


def rows_for(db: Session, user: User) -> list[SymptomEntry]:
    statement = select(SymptomEntry).where(SymptomEntry.patient_id == user.id)
    return list(db.scalars(statement))


def count_rows(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(SymptomEntry))


def test_single_entry_is_saved(
    db_client: TestClient, db_session: Session, patient: User, patient_headers: dict
) -> None:
    response = db_client.post(
        URL, json={"entries": [entry(notes="After lunch")]}, headers=patient_headers
    )

    assert response.status_code == 201
    [created] = response.json()["entries"]
    assert set(created) == {
        "id",
        "symptom_name",
        "symptom_key",
        "occurred_on",
        "severity",
        "notes",
        "created_at",
    }
    assert created["symptom_name"] == "Headache"
    assert created["occurred_on"] == "2026-01-15"
    assert created["severity"] == 5
    assert created["notes"] == "After lunch"

    [row] = rows_for(db_session, patient)
    assert str(row.id) == created["id"]
    assert row.patient_id == patient.id
    assert row.occurred_on == date(2026, 1, 15)
    assert row.created_at.tzinfo is not None


def test_multiple_entries_are_saved_in_order(
    db_client: TestClient, db_session: Session, patient: User, patient_headers: dict
) -> None:
    names = [f"Symptom {number}" for number in range(20)]

    response = db_client.post(
        URL, json={"entries": [entry(symptom_name=name) for name in names]}, headers=patient_headers
    )

    assert response.status_code == 201
    assert [item["symptom_name"] for item in response.json()["entries"]] == names
    assert len(rows_for(db_session, patient)) == 20


def test_name_is_normalized_and_key_is_lowercase(
    db_client: TestClient, db_session: Session, patient: User, patient_headers: dict
) -> None:
    response = db_client.post(
        URL, json={"entries": [entry(symptom_name="  Sore    THROAT ")]}, headers=patient_headers
    )

    assert response.json()["entries"][0]["symptom_name"] == "Sore THROAT"
    [row] = rows_for(db_session, patient)
    assert row.symptom_name == "Sore THROAT"
    assert row.symptom_key == "sore throat"


def test_same_symptom_can_be_logged_twice_on_one_day(
    db_client: TestClient, db_session: Session, patient: User, patient_headers: dict
) -> None:
    body = {"entries": [entry(severity=3), entry(symptom_name=" HEADACHE ", severity=8)]}

    assert db_client.post(URL, json=body, headers=patient_headers).status_code == 201
    assert db_client.post(URL, json=body, headers=patient_headers).status_code == 201

    rows = rows_for(db_session, patient)
    assert len(rows) == 4
    assert {row.symptom_key for row in rows} == {"headache"}


def test_mixed_validity_batch_saves_nothing(
    db_client: TestClient, db_session: Session, patient_headers: dict
) -> None:
    body = {"entries": [entry(), entry(severity=11), entry(), entry(occurred_on="bad")]}

    response = db_client.post(URL, json=body, headers=patient_headers)

    assert response.status_code == 422
    assert response.json() == {
        "detail": "Validation failed",
        "errors": [
            {"entry": 1, "field": "severity", "message": "Severity must be between 1 and 10"},
            {"entry": 3, "field": "occurred_on", "message": "Date must be in YYYY-MM-DD format"},
        ],
    }
    assert count_rows(db_session) == 0


def test_validation_errors_do_not_echo_notes(db_client: TestClient, patient_headers: dict) -> None:
    body = {"entries": [entry(severity=0, notes="private detail")]}

    response = db_client.post(URL, json=body, headers=patient_headers)

    assert response.status_code == 422
    assert "private detail" not in response.text


@pytest.fixture
def frozen_time(monkeypatch: pytest.MonkeyPatch) -> None:
    """12:00 UTC: already 11 March in Auckland, still 10 March in Honolulu."""
    monkeypatch.setattr(symptoms, "current_time", lambda: datetime(2026, 3, 10, 12, 0, tzinfo=UTC))


def test_patient_ahead_of_utc_can_log_their_today(
    db_client: TestClient, db_session: Session, headers_for: Callable, frozen_time: None
) -> None:
    patient = make_user(db_session, UserRole.PATIENT, timezone="Pacific/Auckland")

    response = db_client.post(
        URL, json={"entries": [entry(occurred_on="2026-03-11")]}, headers=headers_for(patient)
    )

    assert response.status_code == 201


def test_patient_behind_utc_cannot_log_tomorrow(
    db_client: TestClient, db_session: Session, headers_for: Callable, frozen_time: None
) -> None:
    patient = make_user(db_session, UserRole.PATIENT, timezone="Pacific/Honolulu")

    response = db_client.post(
        URL, json={"entries": [entry(occurred_on="2026-03-11")]}, headers=headers_for(patient)
    )

    assert response.status_code == 422
    assert response.json()["errors"] == [
        {"entry": 0, "field": "occurred_on", "message": "Date cannot be in the future"}
    ]
    assert count_rows(db_session) == 0


def test_unauthenticated_request_saves_nothing(db_client: TestClient, db_session: Session) -> None:
    assert db_client.post(URL, json={"entries": [entry()]}).status_code == 401
    assert count_rows(db_session) == 0


def test_doctor_gets_403_and_saves_nothing(
    db_client: TestClient, db_session: Session, headers_for: Callable
) -> None:
    doctor = make_user(db_session, UserRole.DOCTOR)

    response = db_client.post(URL, json={"entries": [entry()]}, headers=headers_for(doctor))

    assert response.status_code == 403
    assert count_rows(db_session) == 0


def test_patient_id_in_an_entry_is_rejected(
    db_client: TestClient, db_session: Session, patient_headers: dict
) -> None:
    victim = make_user(db_session, UserRole.PATIENT)

    response = db_client.post(
        URL, json={"entries": [entry(patient_id=str(victim.id))]}, headers=patient_headers
    )

    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "patient_id"
    assert count_rows(db_session) == 0


def test_patient_id_beside_the_entries_is_rejected(
    db_client: TestClient, db_session: Session, patient_headers: dict
) -> None:
    victim = make_user(db_session, UserRole.PATIENT)

    response = db_client.post(
        URL, json={"patient_id": str(victim.id), "entries": [entry()]}, headers=patient_headers
    )

    assert response.status_code == 422
    assert count_rows(db_session) == 0


def test_entries_belong_only_to_the_authenticated_patient(
    db_client: TestClient, db_session: Session, patient: User, patient_headers: dict
) -> None:
    other = make_user(db_session, UserRole.PATIENT)

    db_client.post(URL, json={"entries": [entry()]}, headers=patient_headers)

    assert len(rows_for(db_session, patient)) == 1
    assert rows_for(db_session, other) == []


def valid_then_invalid() -> list[SymptomEntryCreate]:
    """Entries that pass validation but fail in the database, on the second row."""
    good = SymptomEntryCreate.model_construct(
        symptom_name="Headache", occurred_on=date(2026, 1, 15), severity=5, notes=None
    )
    bad = SymptomEntryCreate.model_construct(
        symptom_name="Nausea", occurred_on=date(2026, 1, 15), severity=99, notes="private detail"
    )
    return [good, bad]


@pytest.fixture
def committed_patient(test_engine: Engine) -> Iterator[User]:
    """A real committed user, for tests that must not run inside the test transaction."""
    with Session(test_engine, expire_on_commit=False) as session:
        user = make_user(session, UserRole.PATIENT)
    yield user
    with Session(test_engine) as session:
        session.execute(delete(SymptomEntry).where(SymptomEntry.patient_id == user.id))
        session.execute(delete(User).where(User.id == user.id))
        session.commit()


def test_database_failure_rolls_back_the_whole_batch(
    test_engine: Engine, committed_patient: User
) -> None:
    with Session(test_engine) as session:
        with pytest.raises(IntegrityError):
            save_entries(session, committed_patient.id, valid_then_invalid())

    with Session(test_engine) as session:
        assert rows_for(session, committed_patient) == []


def test_database_failure_returns_a_safe_500_and_logs_no_health_data(
    app: FastAPI,
    db_client: TestClient,
    db_session: Session,
    patient_headers: dict,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr("app.api.symptoms.validate_batch", lambda *args: valid_then_invalid())

    with caplog.at_level(logging.DEBUG):
        response = db_client.post(URL, json={"entries": [entry()]}, headers=patient_headers)

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert count_rows(db_session) == 0
    assert "ck_symptom_entries_severity_range" in caplog.text
    assert "private detail" not in caplog.text
    assert "Nausea" not in caplog.text


def test_saved_entries_are_not_logged(
    db_client: TestClient, patient_headers: dict, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.DEBUG):
        db_client.post(
            URL,
            json={"entries": [entry(symptom_name="Secret Symptom", notes="private detail")]},
            headers=patient_headers,
        )

    assert "Secret Symptom" not in caplog.text
    assert "private detail" not in caplog.text
