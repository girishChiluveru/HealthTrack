import uuid
from datetime import datetime
from functools import lru_cache
from typing import Annotated
from zoneinfo import available_timezones

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    field_validator,
)

from app.models import UserRole

DEFAULT_TIMEZONE = "Asia/Kolkata"
PASSWORD_MIN_LENGTH = 8
# Bounds the work an oversized password can cause during hashing.
PASSWORD_MAX_LENGTH = 128

NormalizedEmail = Annotated[EmailStr, AfterValidator(str.lower)]


@lru_cache
def known_timezones() -> frozenset[str]:
    return frozenset(available_timezones())


def reject_nul_characters(value: str) -> str:
    # PostgreSQL text columns cannot store NUL.
    if "\x00" in value:
        raise ValueError("Must not contain NUL characters")
    return value


class RegisterRequest(BaseModel):
    name: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
        AfterValidator(reject_nul_characters),
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
