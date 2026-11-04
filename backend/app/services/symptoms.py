import uuid
from collections.abc import Sequence
from datetime import UTC, date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import SymptomEntry
from app.schemas import SymptomEntryCreate
from app.symptom_names import symptom_key

REQUIRED_FIELD_MESSAGES = {
    "symptom_name": "Symptom name is required",
    "occurred_on": "Date is required",
    "severity": "Severity is required",
}


class BatchValidationError(Exception):
    def __init__(self, errors: list[dict[str, Any]]) -> None:
        super().__init__("Batch validation failed")
        self.errors = errors


def current_time() -> datetime:
    return datetime.now(UTC)


def today_in_timezone(timezone: str) -> date:
    return current_time().astimezone(ZoneInfo(timezone)).date()


def format_entry_errors(index: int, exc: ValidationError) -> list[dict[str, Any]]:
    errors = []
    for error in exc.errors():
        field = ".".join(str(part) for part in error["loc"]) or "entry"
        if error["type"] == "missing":
            message = REQUIRED_FIELD_MESSAGES[field]
        else:
            message = error["msg"].removeprefix("Value error, ")
        errors.append({"entry": index, "field": field, "message": message})
    return errors


def validate_batch(raw_entries: Sequence[Any], today: date) -> list[SymptomEntryCreate]:
    """Validate every entry, and raise one error listing all the problems found."""
    entries = []
    errors = []
    for index, raw_entry in enumerate(raw_entries):
        try:
            entries.append(SymptomEntryCreate.model_validate(raw_entry, context={"today": today}))
        except ValidationError as exc:
            errors.extend(format_entry_errors(index, exc))
    if errors:
        raise BatchValidationError(errors)
    return entries


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
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    return rows
