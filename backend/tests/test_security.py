import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from pydantic import ValidationError

from app.config import Settings
from app.security import (
    InvalidTokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from tests.conftest import build_settings


def test_password_hash_is_argon2_and_not_plaintext() -> None:
    password_hash = hash_password("correct horse battery")

    assert password_hash.startswith("$argon2id$")
    assert "correct horse battery" not in password_hash


def test_password_hashes_are_salted() -> None:
    assert hash_password("same-password") != hash_password("same-password")


def test_verify_password() -> None:
    password_hash = hash_password("correct horse battery")

    assert verify_password("correct horse battery", password_hash)
    assert not verify_password("wrong password", password_hash)


def test_verify_password_rejects_a_corrupt_hash() -> None:
    assert not verify_password("anything", "not-an-argon2-hash")


def test_token_round_trip_and_sixty_minute_lifetime(settings: Settings) -> None:
    user_id = uuid.uuid4()

    token = create_access_token(user_id, settings)

    payload = jwt.decode(
        token, settings.jwt_secret.get_secret_value(), algorithms=[settings.jwt_algorithm]
    )
    assert set(payload) == {"sub", "exp"}
    assert decode_access_token(token, settings) == user_id
    lifetime = datetime.fromtimestamp(payload["exp"], UTC) - datetime.now(UTC)
    assert timedelta(minutes=59) < lifetime <= timedelta(minutes=60)


def test_token_signed_with_another_secret_is_rejected(settings: Settings) -> None:
    other = build_settings(jwt_secret="another-secret-that-is-at-least-32-characters")

    with pytest.raises(InvalidTokenError):
        decode_access_token(create_access_token(uuid.uuid4(), other), settings)


def test_short_jwt_secret_is_rejected() -> None:
    with pytest.raises(ValidationError):
        build_settings(jwt_secret="too-short")


def test_non_hmac_jwt_algorithm_is_rejected() -> None:
    with pytest.raises(ValidationError):
        build_settings(jwt_algorithm="none")
