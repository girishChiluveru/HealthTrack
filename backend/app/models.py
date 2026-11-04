import uuid
from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(StrEnum):
    PATIENT = "patient"
    DOCTOR = "doctor"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('patient', 'doctor')", name="role_valid"),
        CheckConstraint("email = lower(email)", name="email_lowercase"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text)
    email: Mapped[str] = mapped_column(Text, unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(Text)
    timezone: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    symptom_entries: Mapped[list["SymptomEntry"]] = relationship(back_populates="patient")
    grants_given: Mapped[list["DoctorAccess"]] = relationship(
        back_populates="patient", foreign_keys="DoctorAccess.patient_id"
    )
    grants_received: Mapped[list["DoctorAccess"]] = relationship(
        back_populates="doctor", foreign_keys="DoctorAccess.doctor_id"
    )


class SymptomEntry(Base):
    __tablename__ = "symptom_entries"
    __table_args__ = (
        CheckConstraint("severity BETWEEN 1 AND 10", name="severity_range"),
        CheckConstraint("char_length(symptom_name) BETWEEN 2 AND 60", name="symptom_name_length"),
        CheckConstraint("char_length(notes) <= 500", name="notes_length"),
        Index("ix_symptom_entries_patient_id_occurred_on", "patient_id", "occurred_on"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    symptom_name: Mapped[str] = mapped_column(Text)
    symptom_key: Mapped[str] = mapped_column(Text)
    severity: Mapped[int]
    occurred_on: Mapped[date] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    patient: Mapped[User] = relationship(back_populates="symptom_entries")


class DoctorAccess(Base):
    """One grant. Revoking closes the row and re-granting inserts a new one."""

    __tablename__ = "doctor_access"
    __table_args__ = (
        CheckConstraint("patient_id <> doctor_id", name="no_self_grant"),
        CheckConstraint(
            "revoked_at IS NULL OR revoked_at >= granted_at", name="revoked_after_granted"
        ),
        Index(
            "uq_doctor_access_active_grant",
            "patient_id",
            "doctor_id",
            unique=True,
            postgresql_where=text("revoked_at IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    doctor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Set with func.now(), not the application clock. granted_at comes from the database
    # clock, so any skew could put an immediate revocation before the grant.
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    patient: Mapped[User] = relationship(back_populates="grants_given", foreign_keys=[patient_id])
    doctor: Mapped[User] = relationship(back_populates="grants_received", foreign_keys=[doctor_id])
