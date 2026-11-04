from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import User
from app.schemas import RegisterRequest
from app.security import DUMMY_PASSWORD_HASH, hash_password, verify_password

EMAIL_UNIQUE_CONSTRAINT = "uq_users_email"


class EmailAlreadyRegisteredError(Exception):
    pass


def register_user(db: Session, data: RegisterRequest) -> User:
    user = User(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        role=data.role,
        timezone=data.timezone,
    )
    db.add(user)
    try:
        # Relying on the constraint also covers two simultaneous registrations.
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if getattr(exc.orig.diag, "constraint_name", None) == EMAIL_UNIQUE_CONSTRAINT:
            raise EmailAlreadyRegisteredError from exc
        raise
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = db.scalar(select(User).where(User.email == email))
    password_hash = user.password_hash if user else DUMMY_PASSWORD_HASH
    password_matches = verify_password(password, password_hash)
    return user if user and password_matches else None
