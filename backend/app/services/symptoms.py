import uuid
from collections.abc import Sequence
from datetime import UTC, date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import ValidationError
from sqlalchemy import Row, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import SymptomEntry
from app.schemas import (
    DateRangeFilters,
    SymptomEntryCreate,
    SymptomEntryUpdate,
    SymptomHistoryFilters,
    SymptomTrendFilters,
)
from app.symptom_names import symptom_key

REQUIRED_FIELD_MESSAGES = {
    "symptom_name": "Symptom name is required",
    "occurred_on": "Date is required",
    "severity": "Severity is required",
}


class SymptomValidationError(Exception):
    def __init__(self, errors: list[dict[str, Any]]) -> None:
        super().__init__("Symptom validation failed")
        self.errors = errors


def current_time() -> datetime:
    return datetime.now(UTC)


def today_in_timezone(timezone: str) -> date:
    return current_time().astimezone(ZoneInfo(timezone)).date()


def format_field_errors(exc: ValidationError) -> list[dict[str, Any]]:
    errors = []
    for error in exc.errors():
        field = ".".join(str(part) for part in error["loc"]) or "entry"
        if error["type"] == "missing":
            message = REQUIRED_FIELD_MESSAGES[field]
        else:
            message = error["msg"].removeprefix("Value error, ")
        errors.append({"field": field, "message": message})
    return errors


def validate_batch(raw_entries: Sequence[Any], today: date) -> list[SymptomEntryCreate]:
    """Validate every entry, and raise one error listing all the problems found."""
    entries = []
    errors = []
    for index, raw_entry in enumerate(raw_entries):
        try:
            entries.append(SymptomEntryCreate.model_validate(raw_entry, context={"today": today}))
        except ValidationError as exc:
            errors.extend({"entry": index, **error} for error in format_field_errors(exc))
    if errors:
        raise SymptomValidationError(errors)
    return entries


def validate_update(raw_update: dict[str, Any], today: date) -> SymptomEntryUpdate:
    try:
        update = SymptomEntryUpdate.model_validate(raw_update, context={"today": today})
    except ValidationError as exc:
        raise SymptomValidationError(format_field_errors(exc)) from exc
    if not update.model_fields_set:
        raise SymptomValidationError(
            [{"field": "body", "message": "Provide at least one field to update"}]
        )
    return update


def commit_or_rollback(db: Session) -> None:
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise


def save_entries(
    db: Session, patient_id: uuid.UUID, entries: Sequence[SymptomEntryCreate]
) -> list[SymptomEntry]:
    """Insert all entries in one transaction, so a failure saves none of them."""
    rows = [
        SymptomEntry(
            patient_id=patient_id,
            symptom_name=entry.symptom_name,
            symptom_key=symptom_key(entry.symptom_name),
            severity=entry.severity,
            occurred_on=entry.occurred_on,
            notes=entry.notes,
        )
        for entry in entries
    ]
    db.add_all(rows)
    commit_or_rollback(db)
    return rows


def get_owned_entry(db: Session, patient_id: uuid.UUID, entry_id: uuid.UUID) -> SymptomEntry | None:
    """Return the entry only if this patient owns it.

    Another patient's entry looks exactly like a missing one. The row lock makes a
    concurrent edit or delete wait, and then see the current state.
    """
    return db.scalar(
        select(SymptomEntry)
        .where(SymptomEntry.id == entry_id, SymptomEntry.patient_id == patient_id)
        .with_for_update()
    )


def update_entry(db: Session, entry: SymptomEntry, update: SymptomEntryUpdate) -> SymptomEntry:
    for field in update.model_fields_set:
        setattr(entry, field, getattr(update, field))
    if "symptom_name" in update.model_fields_set:
        entry.symptom_key = symptom_key(entry.symptom_name)
    commit_or_rollback(db)
    return entry


def delete_entry(db: Session, entry: SymptomEntry) -> None:
    db.delete(entry)
    commit_or_rollback(db)


def date_range_conditions(filters: DateRangeFilters) -> list:
    conditions = []
    if filters.start_date:
        conditions.append(SymptomEntry.occurred_on >= filters.start_date)
    if filters.end_date:
        conditions.append(SymptomEntry.occurred_on <= filters.end_date)
    return conditions


def list_entries(
    db: Session, patient_id: uuid.UUID, filters: SymptomHistoryFilters
) -> Sequence[SymptomEntry]:
    """Return the patient's entries, newest first.

    Entries in one batch share `created_at`, so `id` makes the order fully deterministic.
    """
    conditions = [SymptomEntry.patient_id == patient_id, *date_range_conditions(filters)]
    if filters.symptom:
        conditions.append(SymptomEntry.symptom_key == filters.symptom)
    return db.scalars(
        select(SymptomEntry)
        .where(*conditions)
        .order_by(
            SymptomEntry.occurred_on.desc(),
            SymptomEntry.created_at.desc(),
            SymptomEntry.id.desc(),
        )
    ).all()


def list_symptom_names(db: Session, patient_id: uuid.UUID) -> list[dict[str, str]]:
    """Return one row per symptom, with its latest spelling, most recently logged first."""
    latest = (
        select(
            SymptomEntry.symptom_key,
            SymptomEntry.symptom_name,
            SymptomEntry.occurred_on,
            SymptomEntry.created_at,
        )
        .where(SymptomEntry.patient_id == patient_id)
        .distinct(SymptomEntry.symptom_key)
        .order_by(
            SymptomEntry.symptom_key,
            SymptomEntry.occurred_on.desc(),
            SymptomEntry.created_at.desc(),
        )
        .subquery()
    )
    rows = db.execute(
        select(latest.c.symptom_key, latest.c.symptom_name).order_by(
            latest.c.occurred_on.desc(), latest.c.created_at.desc(), latest.c.symptom_key
        )
    )
    return [{"key": row.symptom_key, "name": row.symptom_name} for row in rows]


def daily_max_severity(
    db: Session, patient_id: uuid.UUID, filters: SymptomTrendFilters
) -> Sequence[Row]:
    """Aggregate in PostgreSQL: one row per day with entries, oldest first."""
    return db.execute(
        select(
            SymptomEntry.occurred_on.label("date"),
            func.max(SymptomEntry.severity).label("max_severity"),
            func.count().label("entry_count"),
        )
        .where(
            SymptomEntry.patient_id == patient_id,
            SymptomEntry.symptom_key == filters.symptom,
            *date_range_conditions(filters),
        )
        .group_by(SymptomEntry.occurred_on)
        .order_by(SymptomEntry.occurred_on)
    ).all()
