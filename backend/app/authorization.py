import uuid

from fastapi import HTTPException, status
from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.models import DoctorAccess, User, UserRole


def doctor_has_active_grant(db: Session, doctor_id: uuid.UUID, patient_id: uuid.UUID) -> bool:
    return bool(
        db.scalar(
            select(
                exists().where(
                    DoctorAccess.doctor_id == doctor_id,
                    DoctorAccess.patient_id == patient_id,
                    DoctorAccess.revoked_at.is_(None),
                )
            )
        )
    )


def can_access_patient_records(db: Session, user: User, patient_id: uuid.UUID) -> bool:
    """Patients can read only their own records; doctors need an active grant."""
    if user.role == UserRole.PATIENT:
        return user.id == patient_id
    if user.role == UserRole.DOCTOR:
        return doctor_has_active_grant(db, user.id, patient_id)
    return False


def require_patient_records_access(db: Session, user: User, patient_id: uuid.UUID) -> None:
    """Raise 404, not 403, so responses do not reveal which records exist."""
    if not can_access_patient_records(db, user, patient_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
