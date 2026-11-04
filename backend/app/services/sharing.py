import uuid
from collections.abc import Sequence

from sqlalchemy import Row, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models import DoctorAccess, User, UserRole
from app.services.symptoms import commit_or_rollback

ACTIVE_GRANT_INDEX = "uq_doctor_access_active_grant"


def find_doctor_by_email(db: Session, email: str) -> User | None:
    """Match exactly, and only doctor accounts, so patients cannot be discovered this way."""
    return db.scalar(select(User).where(User.email == email, User.role == UserRole.DOCTOR))


def get_active_grant(
    db: Session, patient_id: uuid.UUID, doctor_id: uuid.UUID
) -> DoctorAccess | None:
    return db.scalar(
        select(DoctorAccess).where(
            DoctorAccess.patient_id == patient_id,
            DoctorAccess.doctor_id == doctor_id,
            DoctorAccess.revoked_at.is_(None),
        )
    )


def grant_access(db: Session, patient_id: uuid.UUID, doctor: User) -> tuple[DoctorAccess, bool]:
    """Return the active grant for this pair, and whether this call created it."""
    existing = get_active_grant(db, patient_id, doctor.id)
    if existing:
        return existing, False

    grant = DoctorAccess(patient_id=patient_id, doctor_id=doctor.id)
    db.add(grant)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        # Two simultaneous requests: the unique index let the other one win.
        if getattr(exc.orig.diag, "constraint_name", None) != ACTIVE_GRANT_INDEX:
            raise
        return get_active_grant(db, patient_id, doctor.id), False
    return grant, True


def list_active_grants(db: Session, patient_id: uuid.UUID) -> Sequence[DoctorAccess]:
    return db.scalars(
        select(DoctorAccess)
        .options(joinedload(DoctorAccess.doctor))
        .where(DoctorAccess.patient_id == patient_id, DoctorAccess.revoked_at.is_(None))
        .order_by(DoctorAccess.granted_at.desc(), DoctorAccess.id)
    ).all()


def revoke_access(db: Session, patient_id: uuid.UUID, grant_id: uuid.UUID) -> bool:
    """Close the patient's active grant. The row stays, so re-granting adds a new one."""
    grant = db.scalar(
        select(DoctorAccess)
        .where(
            DoctorAccess.id == grant_id,
            DoctorAccess.patient_id == patient_id,
            DoctorAccess.revoked_at.is_(None),
        )
        .with_for_update()
    )
    if grant is None:
        return False
    # The database clock, because granted_at uses it and clocks can differ.
    grant.revoked_at = func.now()
    commit_or_rollback(db)
    return True


def list_shared_patients(db: Session, doctor_id: uuid.UUID) -> Sequence[Row]:
    return db.execute(
        select(User.id, User.name, User.email, DoctorAccess.granted_at)
        .join(DoctorAccess, DoctorAccess.patient_id == User.id)
        .where(DoctorAccess.doctor_id == doctor_id, DoctorAccess.revoked_at.is_(None))
        .order_by(User.name, User.id)
    ).all()
