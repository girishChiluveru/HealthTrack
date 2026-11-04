"""Database constraints, against real PostgreSQL. Run with `pytest -m integration`."""

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import DoctorAccess, SymptomEntry, User, UserRole

pytestmark = pytest.mark.integration


def make_user(db: Session, role: UserRole, **overrides: object) -> User:
    values = {
        "name": "Test User",
        "email": f"{uuid.uuid4()}@example.com",
        "password_hash": "$argon2id$placeholder",
        "role": role,
        "timezone": "Asia/Kolkata",
    }
    user = User(**(values | overrides))
    db.add(user)
    db.flush()
    return user


@pytest.fixture
def patient(db_session: Session) -> User:
    return make_user(db_session, UserRole.PATIENT)


@pytest.fixture
def doctor(db_session: Session) -> User:
    return make_user(db_session, UserRole.DOCTOR)


def make_entry(patient: User, **overrides: object) -> SymptomEntry:
    values = {
        "patient_id": patient.id,
        "symptom_name": "Headache",
        "symptom_key": "headache",
        "severity": 5,
        "occurred_on": date(2026, 1, 15),
    }
    return SymptomEntry(**(values | overrides))


def assert_violates(db: Session, constraint: str, row: object) -> None:
    with pytest.raises(IntegrityError) as caught, db.begin_nested():
        db.add(row)
        db.flush()
    assert caught.value.orig.diag.constraint_name == constraint


@pytest.mark.parametrize("severity", [1, 10])
def test_severity_bounds_are_accepted(db_session: Session, patient: User, severity: int) -> None:
    db_session.add(make_entry(patient, severity=severity))
    db_session.flush()


@pytest.mark.parametrize("severity", [0, 11, -1])
def test_severity_out_of_range_is_rejected(
    db_session: Session, patient: User, severity: int
) -> None:
    assert_violates(
        db_session, "ck_symptom_entries_severity_range", make_entry(patient, severity=severity)
    )


@pytest.mark.parametrize("name", ["x", "x" * 61])
def test_symptom_name_length_is_enforced(db_session: Session, patient: User, name: str) -> None:
    assert_violates(
        db_session, "ck_symptom_entries_symptom_name_length", make_entry(patient, symptom_name=name)
    )


def test_notes_limit_is_enforced(db_session: Session, patient: User) -> None:
    db_session.add(make_entry(patient, notes="x" * 500))
    db_session.flush()

    assert_violates(
        db_session, "ck_symptom_entries_notes_length", make_entry(patient, notes="x" * 501)
    )


def test_notes_are_optional(db_session: Session, patient: User) -> None:
    entry = make_entry(patient, notes=None)
    db_session.add(entry)
    db_session.flush()
    db_session.refresh(entry)

    assert entry.notes is None
    assert entry.created_at.tzinfo is not None


def test_entry_needs_an_existing_patient(db_session: Session, patient: User) -> None:
    assert_violates(
        db_session,
        "fk_symptom_entries_patient_id_users",
        make_entry(patient, patient_id=uuid.uuid4()),
    )


def test_invalid_role_is_rejected(db_session: Session) -> None:
    user = User(
        name="Test User",
        email="admin@example.com",
        password_hash="$argon2id$placeholder",
        role="admin",
        timezone="Asia/Kolkata",
    )

    assert_violates(db_session, "ck_users_role_valid", user)


def test_uppercase_email_is_rejected(db_session: Session) -> None:
    user = User(
        name="Test User",
        email="Upper@example.com",
        password_hash="$argon2id$placeholder",
        role=UserRole.PATIENT,
        timezone="Asia/Kolkata",
    )

    assert_violates(db_session, "ck_users_email_lowercase", user)


def test_duplicate_email_is_rejected(db_session: Session) -> None:
    make_user(db_session, UserRole.PATIENT, email="same@example.com")
    duplicate = User(
        name="Other User",
        email="same@example.com",
        password_hash="$argon2id$placeholder",
        role=UserRole.DOCTOR,
        timezone="Asia/Kolkata",
    )

    assert_violates(db_session, "uq_users_email", duplicate)


def test_second_active_grant_for_a_pair_is_rejected(
    db_session: Session, patient: User, doctor: User
) -> None:
    db_session.add(DoctorAccess(patient_id=patient.id, doctor_id=doctor.id))
    db_session.flush()

    assert_violates(
        db_session,
        "uq_doctor_access_active_grant",
        DoctorAccess(patient_id=patient.id, doctor_id=doctor.id),
    )


def test_regrant_after_revoke_keeps_the_earlier_row(
    db_session: Session, patient: User, doctor: User
) -> None:
    first = DoctorAccess(patient_id=patient.id, doctor_id=doctor.id)
    db_session.add(first)
    db_session.flush()
    db_session.refresh(first)

    first.revoked_at = first.granted_at + timedelta(minutes=1)
    db_session.flush()
    db_session.add(DoctorAccess(patient_id=patient.id, doctor_id=doctor.id))
    db_session.flush()
    db_session.refresh(patient)

    assert len(patient.grants_given) == 2


def test_same_doctor_can_have_active_grants_from_different_patients(
    db_session: Session, patient: User, doctor: User
) -> None:
    other_patient = make_user(db_session, UserRole.PATIENT)

    db_session.add(DoctorAccess(patient_id=patient.id, doctor_id=doctor.id))
    db_session.add(DoctorAccess(patient_id=other_patient.id, doctor_id=doctor.id))
    db_session.flush()


def test_self_grant_is_rejected(db_session: Session, doctor: User) -> None:
    assert_violates(
        db_session,
        "ck_doctor_access_no_self_grant",
        DoctorAccess(patient_id=doctor.id, doctor_id=doctor.id),
    )


def test_revocation_before_grant_is_rejected(
    db_session: Session, patient: User, doctor: User
) -> None:
    now = datetime.now(UTC)

    assert_violates(
        db_session,
        "ck_doctor_access_revoked_after_granted",
        DoctorAccess(
            patient_id=patient.id,
            doctor_id=doctor.id,
            granted_at=now,
            revoked_at=now - timedelta(seconds=1),
        ),
    )
