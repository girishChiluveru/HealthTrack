"""Symptom normalization and batch validation. No database is reached."""

from datetime import UTC, date, datetime
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.models import User, UserRole
from app.schemas import SymptomEntryCreate
from app.services import symptoms
from app.services.symptoms import BatchValidationError, today_in_timezone, validate_batch
from app.symptom_names import normalize_symptom_name, symptom_key

TODAY = date(2026, 3, 10)


def entry(**overrides: object) -> dict:
    values = {"symptom_name": "Headache", "occurred_on": "2026-03-09", "severity": 5}
    return values | overrides


def without(field: str) -> dict:
    return {key: value for key, value in entry().items() if key != field}


def errors_for(*raw_entries: object) -> list[dict]:
    with pytest.raises(BatchValidationError) as caught:
        validate_batch(raw_entries, TODAY)
    return caught.value.errors


def assert_single_error(raw_entry: object, field: str, message: str) -> None:
    assert errors_for(raw_entry) == [{"entry": 0, "field": field, "message": message}]


@pytest.mark.parametrize(
    ("raw", "normalized", "key"),
    [
        ("Headache", "Headache", "headache"),
        ("  Headache  ", "Headache", "headache"),
        ("Sore   Throat", "Sore Throat", "sore throat"),
        ("\tsore \n\n THROAT\t", "sore THROAT", "sore throat"),
        ("Sore  Throat", "Sore Throat", "sore throat"),
    ],
)
def test_normalization(raw: str, normalized: str, key: str) -> None:
    assert normalize_symptom_name(raw) == normalized
    assert symptom_key(raw) == key


def test_valid_entry_is_normalized() -> None:
    [result] = validate_batch([entry(symptom_name="  Sore   Throat ", notes="  mild  ")], TODAY)

    assert isinstance(result, SymptomEntryCreate)
    assert result.symptom_name == "Sore Throat"
    assert result.occurred_on == date(2026, 3, 9)
    assert result.notes == "mild"


@pytest.mark.parametrize("notes", [None, "", "   "])
def test_blank_notes_become_none(notes: str | None) -> None:
    assert validate_batch([entry(notes=notes)], TODAY)[0].notes is None


def test_notes_are_optional() -> None:
    assert validate_batch([entry()], TODAY)[0].notes is None


@pytest.mark.parametrize("name", ["ab", "x" * 60, f"  {'x' * 60}  ", "a  b"])
def test_name_length_limits_apply_after_normalization(name: str) -> None:
    assert validate_batch([entry(symptom_name=name)], TODAY)


@pytest.mark.parametrize(
    ("name", "message"),
    [
        ("", "Symptom name is required"),
        ("   ", "Symptom name is required"),
        (None, "Symptom name is required"),
        ("x", "Symptom name must be between 2 and 60 characters"),
        ("  x  ", "Symptom name must be between 2 and 60 characters"),
        ("x" * 61, "Symptom name must be between 2 and 60 characters"),
        (123, "Symptom name must be text"),
        ("nul\x00byte", "Contains characters that cannot be stored"),
        ("bad\ud800name", "Contains characters that cannot be stored"),
    ],
)
def test_invalid_symptom_name(name: object, message: str) -> None:
    assert_single_error(entry(symptom_name=name), "symptom_name", message)


def test_missing_symptom_name() -> None:
    assert_single_error(without("symptom_name"), "symptom_name", "Symptom name is required")


@pytest.mark.parametrize("severity", [1, 10])
def test_severity_boundaries_are_accepted(severity: int) -> None:
    assert validate_batch([entry(severity=severity)], TODAY)[0].severity == severity


@pytest.mark.parametrize("severity", [0, 11, -1, 10**30])
def test_severity_out_of_range(severity: int) -> None:
    assert_single_error(entry(severity=severity), "severity", "Severity must be between 1 and 10")


@pytest.mark.parametrize("severity", [4.5, 4.0, "4", True, [4]])
def test_severity_is_not_coerced(severity: object) -> None:
    assert_single_error(entry(severity=severity), "severity", "Severity must be a whole number")


def test_missing_severity() -> None:
    assert_single_error(without("severity"), "severity", "Severity is required")


def test_null_severity() -> None:
    assert_single_error(entry(severity=None), "severity", "Severity is required")


def test_missing_date() -> None:
    assert_single_error(without("occurred_on"), "occurred_on", "Date is required")


@pytest.mark.parametrize(
    "value",
    [
        "09-03-2026",
        "2026/03/09",
        "2026-3-9",
        "20260309",
        "2026-W11-1",
        "2026-03-09T00:00:00",
        "2026-03-09\n",
        "yesterday",
        "",
        1773014400,
        True,
    ],
)
def test_malformed_date(value: object) -> None:
    assert_single_error(
        entry(occurred_on=value), "occurred_on", "Date must be in YYYY-MM-DD format"
    )


@pytest.mark.parametrize("value", ["2026-02-30", "2026-13-01", "2025-02-29", "0000-01-01"])
def test_impossible_date(value: str) -> None:
    assert_single_error(
        entry(occurred_on=value), "occurred_on", "Date must be a real calendar date"
    )


def test_today_is_accepted_and_tomorrow_is_not() -> None:
    assert validate_batch([entry(occurred_on="2026-03-10")], TODAY)
    assert_single_error(
        entry(occurred_on="2026-03-11"), "occurred_on", "Date cannot be in the future"
    )


@pytest.mark.parametrize("value", ["1900-01-01", "0001-01-01"])
def test_there_is_no_lower_date_limit(value: str) -> None:
    assert validate_batch([entry(occurred_on=value)], TODAY)


def test_notes_limit() -> None:
    assert validate_batch([entry(notes="x" * 500)], TODAY)
    assert_single_error(entry(notes="x" * 501), "notes", "Notes must be at most 500 characters")


def test_notes_limit_applies_after_trimming() -> None:
    assert validate_batch([entry(notes=f"  {'x' * 500}  ")], TODAY)


@pytest.mark.parametrize("notes", ["nul\x00byte", "bad\ud800notes"])
def test_unstorable_notes_are_rejected(notes: str) -> None:
    assert_single_error(entry(notes=notes), "notes", "Contains characters that cannot be stored")


def test_notes_must_be_text() -> None:
    assert_single_error(entry(notes=5), "notes", "Notes must be text")


def test_unknown_fields_are_rejected() -> None:
    [error] = errors_for(entry(patient_id="00000000-0000-0000-0000-000000000000"))

    assert (error["entry"], error["field"]) == (0, "patient_id")


def test_entry_that_is_not_an_object_is_reported() -> None:
    [error] = errors_for("not-an-object")

    assert (error["entry"], error["field"]) == (0, "entry")


def test_all_errors_across_all_entries_are_reported_together() -> None:
    errors = errors_for(
        entry(),
        entry(severity=11, occurred_on="2026-03-11"),
        entry(symptom_name="x", notes="x" * 501),
        without("severity"),
    )

    assert {(error["entry"], error["field"]) for error in errors} == {
        (1, "severity"),
        (1, "occurred_on"),
        (2, "symptom_name"),
        (2, "notes"),
        (3, "severity"),
    }


@pytest.mark.parametrize(
    ("timezone", "expected"),
    [
        ("Pacific/Auckland", date(2026, 3, 11)),
        ("Asia/Kolkata", date(2026, 3, 11)),
        ("UTC", date(2026, 3, 10)),
        ("Pacific/Honolulu", date(2026, 3, 10)),
    ],
)
def test_today_depends_on_the_timezone(
    monkeypatch: pytest.MonkeyPatch, timezone: str, expected: date
) -> None:
    monkeypatch.setattr(symptoms, "current_time", lambda: datetime(2026, 3, 10, 20, 0, tzinfo=UTC))

    assert today_in_timezone(timezone) == expected


@pytest.mark.parametrize("count", [0, 21])
def test_batch_size_limits(
    app: FastAPI, client: TestClient, mock_db: MagicMock, count: int
) -> None:
    app.dependency_overrides[get_current_user] = lambda: User(role=UserRole.PATIENT)

    response = client.post("/api/symptoms/batch", json={"entries": [entry()] * count})

    assert response.status_code == 422
    assert response.json() == {
        "detail": "Validation failed",
        "errors": [
            {"field": "entries", "message": "A batch must contain between 1 and 20 entries"}
        ],
    }
    mock_db.commit.assert_not_called()


def test_unauthenticated_request_gets_401(client: TestClient, mock_db: MagicMock) -> None:
    response = client.post("/api/symptoms/batch", json={"entries": [entry()]})

    assert response.status_code == 401
    mock_db.commit.assert_not_called()


def test_invalid_token_gets_401(client: TestClient, mock_db: MagicMock) -> None:
    response = client.post(
        "/api/symptoms/batch",
        json={"entries": [entry()]},
        headers={"Authorization": "Bearer invalid"},
    )

    assert response.status_code == 401


def test_api_docs_describe_the_entry_fields(client: TestClient) -> None:
    schemas = client.get("/openapi.json").json()["components"]["schemas"]

    entries = schemas["SymptomBatchRequest"]["properties"]["entries"]
    assert (entries["minItems"], entries["maxItems"]) == (1, 20)
    assert set(entries["items"]["properties"]) == {
        "symptom_name",
        "occurred_on",
        "severity",
        "notes",
    }
    assert set(entries["items"]["required"]) == {"symptom_name", "occurred_on", "severity"}
