"""History, editing, deletion, and trends against real PostgreSQL.

Run with `pytest -m integration`.
"""

import logging
import uuid
from collections.abc import Callable
from datetime import UTC, date, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import SymptomEntry, User, UserRole
from app.schemas import SymptomEntryUpdate
from app.security import create_access_token
from app.services import symptoms
from app.services.symptoms import update_entry
from app.symptom_names import symptom_key

pytestmark = pytest.mark.integration

BASE = "/api/symptoms"
TRENDS = f"{BASE}/trends"


def make_user(db: Session, role: UserRole, timezone: str = "UTC") -> User:
    user = User(
        name="Test User",
        email=f"{uuid.uuid4()}@example.com",
        password_hash="$argon2id$placeholder",
        role=role,
        timezone=timezone,
    )
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def headers_for(settings: Settings) -> Callable[[User], dict[str, str]]:
    def build(user: User) -> dict[str, str]:
        return {"Authorization": f"Bearer {create_access_token(user.id, settings)}"}

    return build


@pytest.fixture
def patient(db_session: Session) -> User:
    return make_user(db_session, UserRole.PATIENT)


@pytest.fixture
def other_patient(db_session: Session) -> User:
    return make_user(db_session, UserRole.PATIENT)


@pytest.fixture
def doctor(db_session: Session) -> User:
    return make_user(db_session, UserRole.DOCTOR)


@pytest.fixture
def headers(patient: User, headers_for: Callable) -> dict[str, str]:
    return headers_for(patient)


@pytest.fixture
def add_entry(db_session: Session) -> Callable[..., SymptomEntry]:
    def add(
        user: User,
        name: str = "Headache",
        occurred_on: str = "2026-01-15",
        severity: int = 5,
        notes: str | None = None,
    ) -> SymptomEntry:
        entry = SymptomEntry(
            patient_id=user.id,
            symptom_name=name,
            symptom_key=symptom_key(name),
            occurred_on=date.fromisoformat(occurred_on),
            severity=severity,
            notes=notes,
        )
        db_session.add(entry)
        db_session.commit()
        return entry

    return add


def history(client: TestClient, headers: dict, **params: str) -> list[dict]:
    response = client.get(BASE, params=params, headers=headers)
    assert response.status_code == 200
    return response.json()["entries"]


def trend(client: TestClient, headers: dict, symptom: str = "headache", **params: str) -> list:
    response = client.get(TRENDS, params={"symptom": symptom, **params}, headers=headers)
    assert response.status_code == 200
    return [(p["date"], p["max_severity"]) for p in response.json()["points"]]


def count_entries(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(SymptomEntry))


# History


def test_empty_history_is_an_empty_list(db_client: TestClient, headers: dict) -> None:
    assert history(db_client, headers) == []


def test_history_lists_entries_newest_first(
    db_client: TestClient, patient: User, headers: dict, add_entry: Callable
) -> None:
    add_entry(patient, occurred_on="2026-01-10")
    add_entry(patient, occurred_on="2026-01-20", notes="Latest")
    add_entry(patient, occurred_on="2026-01-15")

    entries = history(db_client, headers)

    assert [entry["occurred_on"] for entry in entries] == [
        "2026-01-20",
        "2026-01-15",
        "2026-01-10",
    ]
    assert entries[0]["notes"] == "Latest"
    assert set(entries[0]) == {
        "id",
        "symptom_name",
        "symptom_key",
        "occurred_on",
        "severity",
        "notes",
        "created_at",
    }


def test_same_day_order_is_stable(
    db_client: TestClient, patient: User, headers: dict, add_entry: Callable
) -> None:
    for severity in range(1, 6):
        add_entry(patient, severity=severity)

    first = history(db_client, headers)

    assert len(first) == 5
    assert history(db_client, headers) == first


def test_symptom_filter_uses_the_normalized_key(
    db_client: TestClient, patient: User, headers: dict, add_entry: Callable
) -> None:
    add_entry(patient, name="Sore Throat")
    add_entry(patient, name="sore THROAT")
    add_entry(patient, name="Headache")

    entries = history(db_client, headers, symptom="  SORE   throat ")

    assert {entry["symptom_name"] for entry in entries} == {"Sore Throat", "sore THROAT"}


def test_blank_symptom_filter_is_ignored(
    db_client: TestClient, patient: User, headers: dict, add_entry: Callable
) -> None:
    add_entry(patient)

    assert len(history(db_client, headers, symptom="   ")) == 1


def test_filter_with_no_matches_is_an_empty_list(
    db_client: TestClient, patient: User, headers: dict, add_entry: Callable
) -> None:
    add_entry(patient)

    assert history(db_client, headers, symptom="nausea") == []


def test_date_filters_are_inclusive(
    db_client: TestClient, patient: User, headers: dict, add_entry: Callable
) -> None:
    for day in ("2026-01-09", "2026-01-10", "2026-01-15", "2026-01-20", "2026-01-21"):
        add_entry(patient, occurred_on=day)

    def dates(**params: str) -> list[str]:
        return [entry["occurred_on"] for entry in history(db_client, headers, **params)]

    assert dates(start_date="2026-01-10", end_date="2026-01-20") == [
        "2026-01-20",
        "2026-01-15",
        "2026-01-10",
    ]
    assert dates(start_date="2026-01-20") == ["2026-01-21", "2026-01-20"]
    assert dates(end_date="2026-01-10") == ["2026-01-10", "2026-01-09"]
    assert dates(start_date="2026-01-15", end_date="2026-01-15") == ["2026-01-15"]


@pytest.mark.parametrize("url", [BASE, TRENDS])
def test_reversed_date_range_is_rejected(db_client: TestClient, headers: dict, url: str) -> None:
    response = db_client.get(
        url,
        params={"symptom": "headache", "start_date": "2026-02-01", "end_date": "2026-01-01"},
        headers=headers,
    )

    assert response.status_code == 422
    assert response.json()["errors"] == [
        {"field": "end_date", "message": "End date must be on or after the start date"}
    ]


@pytest.mark.parametrize("value", ["01-02-2026", "2026-02-30", "1767225600", "yesterday"])
def test_malformed_filter_date_is_rejected(
    db_client: TestClient, headers: dict, value: str
) -> None:
    response = db_client.get(BASE, params={"start_date": value}, headers=headers)

    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "start_date"


def test_history_shows_only_the_patients_own_entries(
    db_client: TestClient,
    patient: User,
    other_patient: User,
    headers: dict,
    add_entry: Callable,
) -> None:
    mine = add_entry(patient)
    add_entry(other_patient, notes="Someone else")

    entries = history(db_client, headers)

    assert [entry["id"] for entry in entries] == [str(mine.id)]


def test_patient_id_query_parameter_is_rejected(
    db_client: TestClient, other_patient: User, headers: dict
) -> None:
    response = db_client.get(BASE, params={"patient_id": str(other_patient.id)}, headers=headers)

    assert response.status_code == 422


def test_symptom_names_are_distinct_with_the_latest_spelling_and_most_recent_first(
    db_client: TestClient,
    patient: User,
    other_patient: User,
    headers: dict,
    add_entry: Callable,
) -> None:
    add_entry(patient, name="headache", occurred_on="2026-01-01")
    add_entry(patient, name="Headache", occurred_on="2026-01-05")
    add_entry(patient, name="Nausea", occurred_on="2026-01-10")
    add_entry(other_patient, name="Private Symptom")

    response = db_client.get(f"{BASE}/names", headers=headers)

    assert response.json() == {
        "symptoms": [
            {"key": "nausea", "name": "Nausea"},
            {"key": "headache", "name": "Headache"},
        ]
    }


# Editing


@pytest.mark.parametrize(
    ("change", "field", "expected"),
    [
        ({"symptom_name": "Migraine"}, "symptom_name", "Migraine"),
        ({"occurred_on": "2026-01-01"}, "occurred_on", date(2026, 1, 1)),
        ({"severity": 9}, "severity", 9),
        ({"notes": "Updated"}, "notes", "Updated"),
    ],
)
def test_each_field_can_be_edited_alone(
    db_client: TestClient,
    db_session: Session,
    patient: User,
    headers: dict,
    add_entry: Callable,
    change: dict,
    field: str,
    expected: object,
) -> None:
    entry = add_entry(patient, notes="Original")
    original = {
        "symptom_name": "Headache",
        "occurred_on": date(2026, 1, 15),
        "severity": 5,
        "notes": "Original",
    }

    response = db_client.patch(f"{BASE}/{entry.id}", json=change, headers=headers)

    assert response.status_code == 200
    assert response.json()["id"] == str(entry.id)
    db_session.refresh(entry)
    for name, value in (original | {field: expected}).items():
        assert getattr(entry, name) == value


def test_editing_the_name_normalizes_it_and_recomputes_the_key(
    db_client: TestClient,
    db_session: Session,
    patient: User,
    headers: dict,
    add_entry: Callable,
) -> None:
    entry = add_entry(patient)

    response = db_client.patch(
        f"{BASE}/{entry.id}", json={"symptom_name": "  Sore   THROAT "}, headers=headers
    )

    assert response.json()["symptom_name"] == "Sore THROAT"
    db_session.refresh(entry)
    assert entry.symptom_key == "sore throat"


def test_editing_other_fields_keeps_the_key(
    db_client: TestClient,
    db_session: Session,
    patient: User,
    headers: dict,
    add_entry: Callable,
) -> None:
    entry = add_entry(patient, name="Sore Throat")

    db_client.patch(f"{BASE}/{entry.id}", json={"severity": 2}, headers=headers)

    db_session.refresh(entry)
    assert entry.symptom_key == "sore throat"


def test_notes_can_be_cleared_with_null(
    db_client: TestClient,
    db_session: Session,
    patient: User,
    headers: dict,
    add_entry: Callable,
) -> None:
    entry = add_entry(patient, notes="Remove me")

    response = db_client.patch(f"{BASE}/{entry.id}", json={"notes": None}, headers=headers)

    assert response.status_code == 200
    db_session.refresh(entry)
    assert entry.notes is None


@pytest.mark.parametrize(
    ("change", "field", "message"),
    [
        ({"severity": 0}, "severity", "Severity must be between 1 and 10"),
        ({"severity": 11}, "severity", "Severity must be between 1 and 10"),
        ({"severity": "4"}, "severity", "Severity must be a whole number"),
        ({"severity": 4.5}, "severity", "Severity must be a whole number"),
        ({"severity": None}, "severity", "Severity is required"),
        ({"symptom_name": "x"}, "symptom_name", "Symptom name must be between 2 and 60 characters"),
        ({"symptom_name": "   "}, "symptom_name", "Symptom name is required"),
        ({"symptom_name": None}, "symptom_name", "Symptom name is required"),
        ({"notes": "x" * 501}, "notes", "Notes must be at most 500 characters"),
        ({"occurred_on": "2999-01-01"}, "occurred_on", "Date cannot be in the future"),
        ({"occurred_on": "2026-02-30"}, "occurred_on", "Date must be a real calendar date"),
        ({"occurred_on": None}, "occurred_on", "Date is required"),
    ],
)
def test_invalid_edit_changes_nothing(
    db_client: TestClient,
    db_session: Session,
    patient: User,
    headers: dict,
    add_entry: Callable,
    change: dict,
    field: str,
    message: str,
) -> None:
    entry = add_entry(patient, notes="Original")

    response = db_client.patch(f"{BASE}/{entry.id}", json={"severity": 8} | change, headers=headers)

    assert response.status_code == 422
    assert response.json() == {
        "detail": "Validation failed",
        "errors": [{"field": field, "message": message}],
    }
    db_session.refresh(entry)
    assert (entry.severity, entry.symptom_name, entry.notes) == (5, "Headache", "Original")


def test_all_edit_errors_are_reported_together(
    db_client: TestClient, patient: User, headers: dict, add_entry: Callable
) -> None:
    entry = add_entry(patient)

    response = db_client.patch(
        f"{BASE}/{entry.id}", json={"severity": 11, "symptom_name": "x"}, headers=headers
    )

    assert {error["field"] for error in response.json()["errors"]} == {"severity", "symptom_name"}


def test_empty_edit_is_rejected(
    db_client: TestClient, patient: User, headers: dict, add_entry: Callable
) -> None:
    entry = add_entry(patient)

    response = db_client.patch(f"{BASE}/{entry.id}", json={}, headers=headers)

    assert response.status_code == 422
    assert response.json()["errors"][0]["message"] == "Provide at least one field to update"


@pytest.mark.parametrize("field", ["patient_id", "id", "symptom_key", "created_at"])
def test_protected_fields_cannot_be_edited(
    db_client: TestClient,
    db_session: Session,
    patient: User,
    other_patient: User,
    headers: dict,
    add_entry: Callable,
    field: str,
) -> None:
    entry = add_entry(patient)

    response = db_client.patch(
        f"{BASE}/{entry.id}", json={field: str(other_patient.id)}, headers=headers
    )

    assert response.status_code == 422
    db_session.refresh(entry)
    assert entry.patient_id == patient.id


def test_future_date_on_edit_uses_the_patients_timezone(
    db_client: TestClient,
    db_session: Session,
    headers_for: Callable,
    add_entry: Callable,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(symptoms, "current_time", lambda: datetime(2026, 3, 10, 12, 0, tzinfo=UTC))
    ahead = make_user(db_session, UserRole.PATIENT, timezone="Pacific/Auckland")
    behind = make_user(db_session, UserRole.PATIENT, timezone="Pacific/Honolulu")
    change = {"occurred_on": "2026-03-11"}

    allowed = db_client.patch(
        f"{BASE}/{add_entry(ahead).id}", json=change, headers=headers_for(ahead)
    )
    rejected = db_client.patch(
        f"{BASE}/{add_entry(behind).id}", json=change, headers=headers_for(behind)
    )

    assert allowed.status_code == 200
    assert rejected.status_code == 422


def test_failed_edit_leaves_the_entry_unchanged(
    db_session: Session, patient: User, add_entry: Callable
) -> None:
    entry = add_entry(patient, notes="Original")
    update = SymptomEntryUpdate.model_construct(
        _fields_set={"notes", "severity"}, notes="Changed", severity=99
    )

    with pytest.raises(IntegrityError):
        update_entry(db_session, entry, update)

    db_session.refresh(entry)
    assert (entry.severity, entry.notes) == (5, "Original")


def test_failed_edit_logs_no_health_data(
    db_client: TestClient,
    patient: User,
    headers: dict,
    add_entry: Callable,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    entry = add_entry(patient, name="Secret Symptom", notes="private detail")
    update = SymptomEntryUpdate.model_construct(_fields_set={"severity"}, severity=99)
    monkeypatch.setattr("app.api.symptoms.validate_update", lambda *args: update)

    with caplog.at_level(logging.DEBUG):
        response = db_client.patch(f"{BASE}/{entry.id}", json={"severity": 2}, headers=headers)

    assert response.status_code == 500
    assert "ck_symptom_entries_severity_range" in caplog.text
    assert "Secret Symptom" not in caplog.text
    assert "private detail" not in caplog.text


# Deletion


def test_delete_removes_only_that_entry(
    db_client: TestClient,
    db_session: Session,
    patient: User,
    headers: dict,
    add_entry: Callable,
) -> None:
    doomed = add_entry(patient)
    survivor = add_entry(patient)
    doomed_id = doomed.id

    response = db_client.delete(f"{BASE}/{doomed_id}", headers=headers)

    assert response.status_code == 204
    assert response.content == b""
    assert [entry["id"] for entry in history(db_client, headers)] == [str(survivor.id)]
    assert db_session.get(User, patient.id) is not None


def test_deleting_twice_gets_404(
    db_client: TestClient, patient: User, headers: dict, add_entry: Callable
) -> None:
    url = f"{BASE}/{add_entry(patient).id}"

    assert db_client.delete(url, headers=headers).status_code == 204
    assert db_client.delete(url, headers=headers).status_code == 404


# Access control


@pytest.mark.parametrize("method", ["patch", "delete"])
def test_nonexistent_entry_gets_404(db_client: TestClient, headers: dict, method: str) -> None:
    kwargs = {"json": {"severity": 2}} if method == "patch" else {}

    response = getattr(db_client, method)(f"{BASE}/{uuid.uuid4()}", headers=headers, **kwargs)

    assert response.status_code == 404
    assert response.json() == {"detail": "Not found"}


@pytest.mark.parametrize("method", ["patch", "delete"])
def test_another_patients_entry_looks_nonexistent(
    db_client: TestClient,
    db_session: Session,
    other_patient: User,
    headers: dict,
    add_entry: Callable,
    method: str,
) -> None:
    entry = add_entry(other_patient, notes="Private")
    kwargs = {"json": {"severity": 2}} if method == "patch" else {}

    response = getattr(db_client, method)(f"{BASE}/{entry.id}", headers=headers, **kwargs)

    assert response.status_code == 404
    assert response.json() == {"detail": "Not found"}
    db_session.refresh(entry)
    assert entry.severity == 5


def test_invalid_edit_of_another_patients_entry_still_gets_404(
    db_client: TestClient, other_patient: User, headers: dict, add_entry: Callable
) -> None:
    entry = add_entry(other_patient)

    response = db_client.patch(f"{BASE}/{entry.id}", json={"severity": 99}, headers=headers)

    assert response.status_code == 404


@pytest.fixture
def protected_requests(patient: User, add_entry: Callable) -> list[tuple[str, str, dict]]:
    url = f"{BASE}/{add_entry(patient).id}"
    return [
        ("GET", BASE, {}),
        ("GET", f"{BASE}/names", {}),
        ("GET", f"{TRENDS}?symptom=headache", {}),
        ("PATCH", url, {"json": {"severity": 2}}),
        ("DELETE", url, {}),
    ]


def test_every_route_requires_authentication(
    db_client: TestClient, db_session: Session, protected_requests: list
) -> None:
    for method, url, kwargs in protected_requests:
        assert db_client.request(method, url, **kwargs).status_code == 401, url
    assert count_entries(db_session) == 1


def test_doctors_get_403_on_every_route(
    db_client: TestClient,
    db_session: Session,
    doctor: User,
    headers_for: Callable,
    protected_requests: list,
) -> None:
    for method, url, kwargs in protected_requests:
        response = db_client.request(method, url, headers=headers_for(doctor), **kwargs)
        assert response.status_code == 403, url
    assert count_entries(db_session) == 1


# Trends


def test_trend_uses_the_daily_maximum(
    db_client: TestClient, patient: User, headers: dict, add_entry: Callable
) -> None:
    for severity in (2, 8, 5):
        add_entry(patient, occurred_on="2026-01-15", severity=severity)
    add_entry(patient, occurred_on="2026-01-16", severity=3)

    response = db_client.get(TRENDS, params={"symptom": "headache"}, headers=headers)

    assert response.json() == {
        "symptom_key": "headache",
        "points": [
            {"date": "2026-01-15", "max_severity": 8, "entry_count": 3},
            {"date": "2026-01-16", "max_severity": 3, "entry_count": 1},
        ],
    }


def test_days_without_entries_have_no_point(
    db_client: TestClient, patient: User, headers: dict, add_entry: Callable
) -> None:
    add_entry(patient, occurred_on="2026-01-01", severity=4)
    add_entry(patient, occurred_on="2026-01-31", severity=6)

    assert trend(db_client, headers) == [("2026-01-01", 4), ("2026-01-31", 6)]


def test_spellings_of_one_symptom_are_grouped_and_other_symptoms_are_excluded(
    db_client: TestClient, patient: User, headers: dict, add_entry: Callable
) -> None:
    add_entry(patient, name="Sore Throat", severity=3)
    add_entry(patient, name="sore   THROAT", severity=7)
    add_entry(patient, name="Headache", severity=10)

    assert trend(db_client, headers, symptom=" SORE THROAT ") == [("2026-01-15", 7)]


def test_trend_respects_the_date_range(
    db_client: TestClient, patient: User, headers: dict, add_entry: Callable
) -> None:
    for day, severity in (
        ("2026-01-09", 1),
        ("2026-01-10", 2),
        ("2026-01-20", 3),
        ("2026-01-21", 4),
    ):
        add_entry(patient, occurred_on=day, severity=severity)

    assert trend(db_client, headers, start_date="2026-01-10", end_date="2026-01-20") == [
        ("2026-01-10", 2),
        ("2026-01-20", 3),
    ]


def test_unknown_symptom_has_an_empty_trend(db_client: TestClient, headers: dict) -> None:
    assert trend(db_client, headers, symptom="nausea") == []


@pytest.mark.parametrize("params", [{}, {"symptom": "   "}])
def test_trend_requires_a_symptom(db_client: TestClient, headers: dict, params: dict) -> None:
    response = db_client.get(TRENDS, params=params, headers=headers)

    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "symptom"


def test_trend_excludes_other_patients(
    db_client: TestClient,
    patient: User,
    other_patient: User,
    headers: dict,
    add_entry: Callable,
) -> None:
    add_entry(patient, severity=3)
    add_entry(other_patient, severity=10)

    assert trend(db_client, headers) == [("2026-01-15", 3)]


def test_lowering_the_highest_entry_recalculates_the_maximum(
    db_client: TestClient, patient: User, headers: dict, add_entry: Callable
) -> None:
    add_entry(patient, severity=4)
    highest = add_entry(patient, severity=9)

    db_client.patch(f"{BASE}/{highest.id}", json={"severity": 2}, headers=headers)

    assert trend(db_client, headers) == [("2026-01-15", 4)]


def test_deleting_the_highest_entry_recalculates_the_maximum(
    db_client: TestClient, patient: User, headers: dict, add_entry: Callable
) -> None:
    add_entry(patient, severity=4)
    highest = add_entry(patient, severity=9)

    db_client.delete(f"{BASE}/{highest.id}", headers=headers)

    assert trend(db_client, headers) == [("2026-01-15", 4)]


def test_deleting_the_last_entry_of_a_day_removes_its_point(
    db_client: TestClient, patient: User, headers: dict, add_entry: Callable
) -> None:
    add_entry(patient, occurred_on="2026-01-14", severity=4)
    only = add_entry(patient, occurred_on="2026-01-15", severity=9)

    db_client.delete(f"{BASE}/{only.id}", headers=headers)

    assert trend(db_client, headers) == [("2026-01-14", 4)]


def test_moving_an_entry_to_another_date_updates_both_days(
    db_client: TestClient, patient: User, headers: dict, add_entry: Callable
) -> None:
    add_entry(patient, occurred_on="2026-01-15", severity=3)
    moved = add_entry(patient, occurred_on="2026-01-15", severity=9)
    add_entry(patient, occurred_on="2026-01-20", severity=5)

    db_client.patch(f"{BASE}/{moved.id}", json={"occurred_on": "2026-01-20"}, headers=headers)

    assert trend(db_client, headers) == [("2026-01-15", 3), ("2026-01-20", 9)]


def test_renaming_an_entry_moves_it_between_symptoms(
    db_client: TestClient, patient: User, headers: dict, add_entry: Callable
) -> None:
    add_entry(patient, name="Headache", severity=3)
    moved = add_entry(patient, name="Headache", severity=9)
    add_entry(patient, name="Migraine", severity=5)

    db_client.patch(f"{BASE}/{moved.id}", json={"symptom_name": "migraine"}, headers=headers)

    assert trend(db_client, headers, symptom="headache") == [("2026-01-15", 3)]
    assert trend(db_client, headers, symptom="migraine") == [("2026-01-15", 9)]


def test_renaming_the_only_entry_removes_the_old_symptom(
    db_client: TestClient, patient: User, headers: dict, add_entry: Callable
) -> None:
    entry = add_entry(patient, name="Headache")

    db_client.patch(f"{BASE}/{entry.id}", json={"symptom_name": "Migraine"}, headers=headers)

    names = db_client.get(f"{BASE}/names", headers=headers).json()["symptoms"]
    assert names == [{"key": "migraine", "name": "Migraine"}]


def test_history_and_edits_do_not_log_health_data(
    db_client: TestClient,
    patient: User,
    headers: dict,
    add_entry: Callable,
    caplog: pytest.LogCaptureFixture,
) -> None:
    entry = add_entry(patient, name="Secret Symptom", notes="private detail")

    with caplog.at_level(logging.DEBUG):
        history(db_client, headers, symptom="Secret Symptom")
        db_client.patch(f"{BASE}/{entry.id}", json={"notes": "new private"}, headers=headers)
        db_client.delete(f"{BASE}/{entry.id}", headers=headers)

    assert "Secret Symptom" not in caplog.text
    assert "private" not in caplog.text


def test_api_docs_describe_the_edit_body(app: FastAPI, client: TestClient) -> None:
    operation = client.get("/openapi.json").json()["paths"]["/api/symptoms/{entry_id}"]["patch"]

    schema = operation["requestBody"]["content"]["application/json"]["schema"]
    assert set(schema["properties"]) == {"symptom_name", "occurred_on", "severity", "notes"}
    assert "required" not in schema
