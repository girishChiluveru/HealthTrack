"""Record access rules, against real PostgreSQL. Run with `pytest -m integration`."""

import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.authorization import can_access_patient_records, require_patient_records_access
from app.models import DoctorAccess, User, UserRole

pytestmark = pytest.mark.integration


def make_user(db: Session, role: UserRole) -> User:
    user = User(
        name="Test User",
        email=f"{uuid.uuid4()}@example.com",
        password_hash="$argon2id$placeholder",
        role=role,
        timezone="Asia/Kolkata",
    )
    db.add(user)
    db.flush()
    return user


@pytest.fixture
def patient(db_session: Session) -> User:
    return make_user(db_session, UserRole.PATIENT)


@pytest.fixture
def doctor(db_session: Session) -> User:
    return make_user(db_session, UserRole.DOCTOR)


def grant(db: Session, patient: User, doctor: User) -> DoctorAccess:
    access = DoctorAccess(patient_id=patient.id, doctor_id=doctor.id)
    db.add(access)
    db.flush()
    return access


def test_patient_can_access_own_records(db_session: Session, patient: User) -> None:
    assert can_access_patient_records(db_session, patient, patient.id)


def test_patient_cannot_access_another_patient(db_session: Session, patient: User) -> None:
    other = make_user(db_session, UserRole.PATIENT)

    assert not can_access_patient_records(db_session, patient, other.id)


def test_doctor_without_grant_has_no_access(
    db_session: Session, patient: User, doctor: User
) -> None:
    assert not can_access_patient_records(db_session, doctor, patient.id)


def test_doctor_with_active_grant_has_access(
    db_session: Session, patient: User, doctor: User
) -> None:
    grant(db_session, patient, doctor)

    assert can_access_patient_records(db_session, doctor, patient.id)


def test_grant_for_one_patient_does_not_cover_another(
    db_session: Session, patient: User, doctor: User
) -> None:
    other = make_user(db_session, UserRole.PATIENT)
    grant(db_session, patient, doctor)

    assert not can_access_patient_records(db_session, doctor, other.id)


def test_access_ends_when_grant_is_revoked(
    db_session: Session, patient: User, doctor: User
) -> None:
    access = grant(db_session, patient, doctor)

    access.revoked_at = func.now()
    db_session.flush()

    assert not can_access_patient_records(db_session, doctor, patient.id)


def test_denied_access_raises_404(db_session: Session, patient: User, doctor: User) -> None:
    with pytest.raises(HTTPException) as caught:
        require_patient_records_access(db_session, doctor, patient.id)

    assert caught.value.status_code == 404


def test_allowed_access_does_not_raise(db_session: Session, patient: User) -> None:
    require_patient_records_access(db_session, patient, patient.id)
