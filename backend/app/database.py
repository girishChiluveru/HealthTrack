import logging
from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, MetaData, create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

logger = logging.getLogger(__name__)

CONNECT_TIMEOUT_SECONDS = 10


class Base(DeclarativeBase):
    """Base class for ORM models. Named constraints keep Alembic migrations predictable."""

    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


@lru_cache
def get_engine() -> Engine:
    """Create the engine on first use. It does not connect until a query runs."""
    return create_engine(
        get_settings().database_url.get_secret_value(),
        pool_pre_ping=True,
        # Hosted connection poolers allow few clients per project.
        max_overflow=5,
        # Keeps bound values, which will include health data, out of error messages.
        hide_parameters=True,
        connect_args={"connect_timeout": CONNECT_TIMEOUT_SECONDS},
    )


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def get_db() -> Iterator[Session]:
    with get_session_factory()() as session:
        yield session


def check_database_connection(db: Session) -> bool:
    """Return whether the database answers a trivial query."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        # Only the error type is logged: the message can include connection details.
        logger.warning("Database connectivity check failed: %s", type(exc).__name__)
        return False
    return True
