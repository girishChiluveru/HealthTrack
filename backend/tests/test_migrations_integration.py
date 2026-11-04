"""Migrations against a fresh PostgreSQL database. Run with `pytest -m integration`."""

import pytest
from alembic import command
from sqlalchemy import create_engine, inspect

from tests.conftest import alembic_config, temporary_database

pytestmark = pytest.mark.integration

PRODUCT_TABLES = {"users", "symptom_entries", "doctor_access"}


def table_names(url) -> set[str]:
    engine = create_engine(url)
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_upgrade_downgrade_and_reupgrade_on_a_fresh_database() -> None:
    with temporary_database("healthtrack_migration_test") as url:
        config = alembic_config(url)

        command.upgrade(config, "head")
        assert PRODUCT_TABLES <= table_names(url)

        command.downgrade(config, "base")
        assert table_names(url) == {"alembic_version"}

        command.upgrade(config, "head")
        assert PRODUCT_TABLES <= table_names(url)


def test_models_match_the_migrated_schema() -> None:
    with temporary_database("healthtrack_migration_test") as url:
        config = alembic_config(url)
        command.upgrade(config, "head")

        command.check(config)


def test_migration_creates_the_expected_indexes() -> None:
    with temporary_database("healthtrack_migration_test") as url:
        command.upgrade(alembic_config(url), "head")
        engine = create_engine(url)
        inspector = inspect(engine)

        entry_indexes = {index["name"] for index in inspector.get_indexes("symptom_entries")}
        grant_index = next(
            index
            for index in inspector.get_indexes("doctor_access")
            if index["name"] == "uq_doctor_access_active_grant"
        )
        engine.dispose()

    assert "ix_symptom_entries_patient_id_occurred_on" in entry_indexes
    assert grant_index["unique"]
    assert grant_index["dialect_options"]["postgresql_where"] == "(revoked_at IS NULL)"
