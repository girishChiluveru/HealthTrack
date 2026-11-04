from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import DoctorAccess, SymptomEntry, User
from app.seed_demo import (
    DEMO_PASSWORD,
    DOCTOR,
    MAIN_PATIENT,
    MAIN_PATIENT_EXTRAS,
    MAIN_PATIENT_SEVERITIES,
    OTHER_PATIENT,
    require_local_database,
    seed,
)

TODAY = date(2026, 3, 30)


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+psycopg://u:p@127.0.0.1:5432/healthtrack",
        "postgresql+psycopg://u:p@localhost/healthtrack",
    ],
)
def test_local_databases_are_allowed(url: str) -> None:
    require_local_database(url)


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+psycopg://u:p@db.supabase.example:5432/postgres",
        "postgresql+psycopg://u:p@10.0.0.5/healthtrack",
        "postgresql+psycopg://u:p@localhost.attacker.example/healthtrack",
    ],
)
def test_other_databases_are_refused(url: str) -> None:
    with pytest.raises(SystemExit, match="Refusing to seed"):
        require_local_database(url)


def test_every_series_covers_the_same_days() -> None:
    assert {len(values) for values in MAIN_PATIENT_SEVERITIES.values()} == {30}


def test_extras_land_on_days_that_already_have_an_entry() -> None:
    for name, days_ago, _, _ in MAIN_PATIENT_EXTRAS:
        assert MAIN_PATIENT_SEVERITIES[name][29 - days_ago] != "-"


def test_daily_maximum_is_visible_in_the_plan() -> None:
    higher_than_extra = [
        int(MAIN_PATIENT_SEVERITIES[name][29 - days_ago]) > severity
        for name, days_ago, severity, _ in MAIN_PATIENT_EXTRAS
    ]
    assert any(higher_than_extra)


def count(db: Session, model: type, *conditions: object) -> int:
    return db.scalar(select(func.count()).select_from(model).where(*conditions))


def user_id(db: Session, email: str):
    return db.scalar(select(User.id).where(User.email == email))


@pytest.mark.integration
def test_seeding_twice_creates_no_duplicates(db_session: Session) -> None:
    first = seed(db_session, TODAY)
    second = seed(db_session, TODAY)

    assert first == second
    emails = [MAIN_PATIENT.email, OTHER_PATIENT.email, DOCTOR.email]
    assert count(db_session, User, User.email.in_(emails)) == 3
    patient_id = user_id(db_session, MAIN_PATIENT.email)
    entries = count(db_session, SymptomEntry, SymptomEntry.patient_id == patient_id)
    assert entries == first["main_entries"]
    assert count(db_session, DoctorAccess, DoctorAccess.patient_id == patient_id) == 1


@pytest.mark.integration
def test_seeding_restores_entries_changed_during_a_demo(db_session: Session) -> None:
    seed(db_session, TODAY)
    patient_id = user_id(db_session, MAIN_PATIENT.email)
    first_entry = db_session.scalar(
        select(SymptomEntry).where(SymptomEntry.patient_id == patient_id).limit(1)
    )
    db_session.delete(first_entry)
    db_session.commit()

    counts = seed(db_session, TODAY)

    entries = count(db_session, SymptomEntry, SymptomEntry.patient_id == patient_id)
    assert entries == counts["main_entries"]


@pytest.mark.integration
def test_seeding_leaves_other_accounts_alone(db_session: Session) -> None:
    other = User(
        name="Someone Else",
        email="someone@example.com",
        password_hash="unused",
        role="patient",
        timezone="UTC",
    )
    db_session.add(other)
    db_session.flush()
    db_session.add(
        SymptomEntry(
            patient_id=other.id,
            symptom_name="Cough",
            symptom_key="cough",
            severity=2,
            occurred_on=TODAY,
        )
    )
    db_session.commit()

    seed(db_session, TODAY)

    assert count(db_session, SymptomEntry, SymptomEntry.patient_id == other.id) == 1


@pytest.mark.integration
def test_seeded_data_has_gaps_same_day_entries_and_no_future_dates(db_session: Session) -> None:
    seed(db_session, TODAY)
    patient_id = user_id(db_session, MAIN_PATIENT.email)
    rows = db_session.execute(
        select(SymptomEntry.symptom_key, SymptomEntry.occurred_on, SymptomEntry.severity).where(
            SymptomEntry.patient_id == patient_id
        )
    ).all()

    assert max(row.occurred_on for row in rows) == TODAY
    assert min(row.occurred_on for row in rows) == TODAY - timedelta(days=29)
    headache_days = [row.occurred_on for row in rows if row.symptom_key == "headache"]
    assert len(headache_days) > len(set(headache_days))
    assert len(set(headache_days)) < 30


@pytest.mark.integration
def test_doctor_can_read_the_main_patient_only(db_client: TestClient, db_session: Session) -> None:
    seed(db_session, TODAY)
    login = db_client.post(
        "/api/auth/login", json={"email": DOCTOR.email, "password": DEMO_PASSWORD}
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    patients = db_client.get("/api/doctor/patients", headers=headers).json()["patients"]

    assert [patient["email"] for patient in patients] == [MAIN_PATIENT.email]
    other_id = user_id(db_session, OTHER_PATIENT.email)
    response = db_client.get(f"/api/doctor/patients/{other_id}/symptoms", headers=headers)
    assert response.status_code == 404
