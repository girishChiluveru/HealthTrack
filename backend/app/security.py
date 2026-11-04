import uuid
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.config import Settings

ACCESS_TOKEN_LIFETIME = timedelta(minutes=60)

password_hasher = PasswordHasher()

# Verified when an email is unknown, so that login takes about the same time either way.
DUMMY_PASSWORD_HASH = password_hasher.hash("healthtrack-timing-equalizer")


class InvalidTokenError(Exception):
    """The token is missing required claims, expired, or not correctly signed."""


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def create_access_token(user_id: uuid.UUID, settings: Settings) -> str:
    payload = {"sub": str(user_id), "exp": datetime.now(UTC) + ACCESS_TOKEN_LIFETIME}
    return jwt.encode(
        payload, settings.jwt_secret.get_secret_value(), algorithm=settings.jwt_algorithm
    )


def decode_access_token(token: str, settings: Settings) -> uuid.UUID:
    """Return the user ID from a valid token, or raise InvalidTokenError."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "exp"]},
        )
        return uuid.UUID(payload["sub"])
    except (jwt.InvalidTokenError, ValueError) as exc:
        raise InvalidTokenError from exc
