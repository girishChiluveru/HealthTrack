import re
import uuid
from datetime import date, datetime
from functools import lru_cache
from typing import Annotated, Any
from zoneinfo import available_timezones

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    ValidationInfo,
    field_validator,
)

from app.models import UserRole
from app.symptom_names import normalize_symptom_name, symptom_key

DEFAULT_TIMEZONE = "Asia/Kolkata"
PASSWORD_MIN_LENGTH = 8
# Bounds the work an oversized password can cause during hashing.
PASSWORD_MAX_LENGTH = 128

SYMPTOM_NAME_MIN_LENGTH = 2
SYMPTOM_NAME_MAX_LENGTH = 60
NOTES_MAX_LENGTH = 500
SEVERITY_MIN = 1
SEVERITY_MAX = 10
BATCH_MIN_ENTRIES = 1
BATCH_MAX_ENTRIES = 20

ISO_DATE_PATTERN = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")

NormalizedEmail = Annotated[EmailStr, AfterValidator(str.lower)]


@lru_cache
def known_timezones() -> frozenset[str]:
    return frozenset(available_timezones())


def reject_unstorable_characters(value: str) -> str:
    # PostgreSQL text columns cannot store NUL, and lone surrogates cannot be encoded as UTF-8.
    try:
        value.encode()
    except UnicodeEncodeError:
        raise ValueError("Contains characters that cannot be stored") from None
    if "\x00" in value:
        raise ValueError("Contains characters that cannot be stored")
    return value


def parse_iso_date(value: Any) -> date:
    """Accept only YYYY-MM-DD. Pydantic's own parsing also allows timestamps and datetimes."""
    if not isinstance(value, str) or not ISO_DATE_PATTERN.fullmatch(value):
        raise ValueError("Date must be in YYYY-MM-DD format")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValueError("Date must be a real calendar date") from None


class RegisterRequest(BaseModel):
    name: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
        AfterValidator(reject_unstorable_characters),
    ]
    email: NormalizedEmail
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)
    role: UserRole
    # validate_default makes the validator below also run when the field is omitted.
    timezone: str | None = Field(default=None, validate_default=True)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str | None) -> str:
        if value is None:
            return DEFAULT_TIMEZONE
        if value not in known_timezones():
            raise ValueError("Must be a valid IANA timezone")
        return value


class LoginRequest(BaseModel):
    email: NormalizedEmail
    # No minimum: a short password is simply a wrong password, not a validation error.
    password: str = Field(max_length=PASSWORD_MAX_LENGTH)


class UserResponse(BaseModel):
    """Public view of a user. Fields are listed explicitly so the hash cannot leak."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: str
    role: UserRole
    timezone: str
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class SymptomEntryCreate(BaseModel):
    """One entry in a batch. Validate with `context={"today": <patient's date>}`.

    The field validators run before Pydantic's own, because its default coercion would
    accept values such as "4" for severity or a Unix timestamp for the date.
    """

    # Rejecting unknown fields means a supplied patient_id fails loudly, not silently.
    model_config = ConfigDict(extra="forbid")

    symptom_name: str
    occurred_on: date
    severity: int
    notes: str | None = None

    @field_validator("symptom_name", mode="before")
    @classmethod
    def validate_symptom_name(cls, value: Any) -> str:
        if value is None:
            raise ValueError("Symptom name is required")
        if not isinstance(value, str):
            raise ValueError("Symptom name must be text")
        name = normalize_symptom_name(reject_unstorable_characters(value))
        if not name:
            raise ValueError("Symptom name is required")
        if not SYMPTOM_NAME_MIN_LENGTH <= len(name) <= SYMPTOM_NAME_MAX_LENGTH:
            raise ValueError(
                f"Symptom name must be between {SYMPTOM_NAME_MIN_LENGTH} "
                f"and {SYMPTOM_NAME_MAX_LENGTH} characters"
            )
        return name

    @field_validator("occurred_on", mode="before")
    @classmethod
    def validate_occurred_on(cls, value: Any, info: ValidationInfo) -> date:
        if value is None:
            raise ValueError("Date is required")
        occurred_on = parse_iso_date(value)
        if occurred_on > info.context["today"]:
            raise ValueError("Date cannot be in the future")
        return occurred_on

    @field_validator("severity", mode="before")
    @classmethod
    def validate_severity(cls, value: Any) -> int:
        if value is None:
            raise ValueError("Severity is required")
        # An exact type check, because bool is a subclass of int.
        if type(value) is not int:
            raise ValueError("Severity must be a whole number")
        if not SEVERITY_MIN <= value <= SEVERITY_MAX:
            raise ValueError(f"Severity must be between {SEVERITY_MIN} and {SEVERITY_MAX}")
        return value

    @field_validator("notes", mode="before")
    @classmethod
    def validate_notes(cls, value: Any) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("Notes must be text")
        notes = reject_unstorable_characters(value).strip()
        if len(notes) > NOTES_MAX_LENGTH:
            raise ValueError(f"Notes must be at most {NOTES_MAX_LENGTH} characters")
        return notes or None


class SymptomEntryUpdate(SymptomEntryCreate):
    """A partial edit, validated like a new entry. Inherits every field validator.

    Fields left out keep their stored values, so callers must apply only `model_fields_set`.
    An explicit null is rejected for required fields, and clears `notes`.
    """

    symptom_name: str | None = None
    occurred_on: date | None = None
    severity: int | None = None


class SymptomBatchRequest(BaseModel):
    """Entries are checked later by `validate_batch`, not here.

    The future-date rule needs the patient's timezone, which is not known while FastAPI
    parses the body. Validating every entry in one later pass lets a single response report
    all errors together. The entry schema is declared here so the API docs still show it.
    """

    model_config = ConfigDict(extra="forbid")

    entries: list[Any] = Field(
        min_length=BATCH_MIN_ENTRIES,
        max_length=BATCH_MAX_ENTRIES,
        json_schema_extra={"items": SymptomEntryCreate.model_json_schema()},
    )

    @field_validator("entries", mode="before")
    @classmethod
    def validate_entry_count(cls, value: Any) -> Any:
        if isinstance(value, list) and not BATCH_MIN_ENTRIES <= len(value) <= BATCH_MAX_ENTRIES:
            raise ValueError(
                f"A batch must contain between {BATCH_MIN_ENTRIES} and {BATCH_MAX_ENTRIES} entries"
            )
        return value


class SymptomEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    symptom_name: str
    occurred_on: date
    severity: int
    notes: str | None
    created_at: datetime


class SymptomEntryListResponse(BaseModel):
    entries: list[SymptomEntryResponse]


class DateRangeFilters(BaseModel):
    # Rejecting unknown parameters means a supplied patient_id fails loudly, not silently.
    model_config = ConfigDict(extra="forbid")

    start_date: date | None = None
    end_date: date | None = None

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def validate_date_format(cls, value: Any) -> date | None:
        return None if value is None else parse_iso_date(value)

    @field_validator("end_date")
    @classmethod
    def validate_range_order(cls, value: date | None, info: ValidationInfo) -> date | None:
        start_date = info.data.get("start_date")
        if value and start_date and value < start_date:
            raise ValueError("End date must be on or after the start date")
        return value


class SymptomHistoryFilters(DateRangeFilters):
    symptom: str | None = None

    @field_validator("symptom")
    @classmethod
    def normalize_symptom_filter(cls, value: str | None) -> str | None:
        """Return the matching symptom key. A blank value means no filter."""
        if value is None:
            return None
        return symptom_key(reject_unstorable_characters(value)) or None


class SymptomTrendFilters(DateRangeFilters):
    symptom: str

    @field_validator("symptom")
    @classmethod
    def normalize_symptom_filter(cls, value: str) -> str:
        key = symptom_key(reject_unstorable_characters(value))
        if not key:
            raise ValueError("Symptom is required")
        return key


class SymptomName(BaseModel):
    key: str
    name: str


class SymptomNameListResponse(BaseModel):
    symptoms: list[SymptomName]


class TrendPoint(BaseModel):
    date: date
    max_severity: int
    entry_count: int


class SymptomTrendResponse(BaseModel):
    """One point per day that has entries, oldest first. Days without entries are absent."""

    symptom_key: str
    points: list[TrendPoint]
