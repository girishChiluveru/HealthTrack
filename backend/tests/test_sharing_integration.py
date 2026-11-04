"""Doctor sharing against real PostgreSQL. Run with `pytest -m integration`."""

import logging
import uuid
from collections.abc import Callable
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import DoctorAccess, SymptomEntry, User, UserRole
from app.security import create_access_token
from app.symptom_names import symptom_key

pytestmark = pytest.mark.integration

LOOKUP = "/api/sharing/lookup"
GRANTS = "/api/sharing/grants"
PATIENTS = "/api/doctor/patients"
NOT_FOUND = {"detail": "Not found"}
NO_DOCTOR = {"detail": "No doctor account was found for this email"}


def make_user(db: Session, role: UserRole, name: str = "Test User") -> User:
    user = User(
        name=name,
        email=f"{uuid.uuid4()}@example.com",
        password_hash="$argon2id$placeholder",
        role=role,
        timezone="UTC",
    )
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def auth(settings: Settings) -> Callable[[User], dict[str, str]]:
    def build(user: User) -> dict[str, str]:
        return {"Authorization": f"Bearer {create_access_token(user.id, settings)}"}

    return build


@pytest.fixture
def patient(db_session: Session) -> User:
    return make_user(db_session, UserRole.PATIENT, "Pat Patient")


@pytest.fixture
def other_patient(db_session: Session) -> User:
    return make_user(db_session, UserRole.PATIENT, "Other Patient")


@pytest.fixture
def doctor(db_session: Session) -> User:
    return make_user(db_session, UserRole.DOCTOR, "Dr Test")


@pytest.fixture
def other_doctor(db_session: Session) -> User:
    return make_user(db_session, UserRole.DOCTOR, "Dr Other")


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


@pytest.fixture
def share(db_client: TestClient, auth: Callable) -> Callable[[User, User], dict]:
    def create(from_patient: User, to_doctor: User) -> dict:
        response = db_client.post(
            GRANTS, json={"email": to_doctor.email}, headers=auth(from_patient)
        )
        assert response.status_code in (200, 201)
        return response.json()

    return create


def grant_rows(db: Session, patient: User, doctor: User) -> list[DoctorAccess]:
    statement = select(DoctorAccess).where(
        DoctorAccess.patient_id == patient.id, DoctorAccess.doctor_id == doctor.id
    )
    return list(db.scalars(statement))


# Lookup


def test_lookup_returns_only_the_doctors_name_and_email(
    db_client: TestClient, patient: User, doctor: User, auth: Callable
) -> None:
    response = db_client.post(LOOKUP, json={"email": doctor.email}, headers=auth(patient))

    assert response.status_code == 200
    assert response.json() == {"name": "Dr Test", "email": doctor.email}


def test_lookup_normalizes_the_email(
    db_client: TestClient, patient: User, doctor: User, auth: Callable
) -> None:
    response = db_client.post(LOOKUP, json={"email": doctor.email.upper()}, headers=auth(patient))

    assert response.status_code == 200


def test_unknown_email_and_patient_email_look_identical(
    db_client: TestClient, patient: User, other_patient: User, auth: Callable
) -> None:
    unknown = db_client.post(LOOKUP, json={"email": "no@example.com"}, headers=auth(patient))
    a_patient = db_client.post(LOOKUP, json={"email": other_patient.email}, headers=auth(patient))

    assert unknown.status_code == a_patient.status_code == 404
    assert unknown.json() == a_patient.json() == NO_DOCTOR


def test_lookup_rejects_a_malformed_email(
    db_client: TestClient, patient: User, auth: Callable
) -> None:
    response = db_client.post(LOOKUP, json={"email": "not-an-email"}, headers=auth(patient))

    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "email"


def test_lookup_creates_no_grant(
    db_client: TestClient, db_session: Session, patient: User, doctor: User, auth: Callable
) -> None:
    db_client.post(LOOKUP, json={"email": doctor.email}, headers=auth(patient))

    assert grant_rows(db_session, patient, doctor) == []


# Granting


def test_grant_is_created_for_the_authenticated_patient(
    db_client: TestClient, db_session: Session, patient: User, doctor: User, auth: Callable
) -> None:
    response = db_client.post(GRANTS, json={"email": doctor.email}, headers=auth(patient))

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "doctor", "granted_at"}
    assert body["doctor"] == {"name": "Dr Test", "email": doctor.email}
    [row] = grant_rows(db_session, patient, doctor)
    assert str(row.id) == body["id"]
    assert row.revoked_at is None


def test_granting_twice_returns_the_existing_grant(
    db_client: TestClient, db_session: Session, patient: User, doctor: User, auth: Callable
) -> None:
    first = db_client.post(GRANTS, json={"email": doctor.email}, headers=auth(patient))
    second = db_client.post(GRANTS, json={"email": doctor.email}, headers=auth(patient))

    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert len(grant_rows(db_session, patient, doctor)) == 1


def test_cannot_grant_to_a_patient_or_unknown_email(
    db_client: TestClient,
    db_session: Session,
    patient: User,
    other_patient: User,
    auth: Callable,
) -> None:
    for email in (other_patient.email, "no@example.com"):
        response = db_client.post(GRANTS, json={"email": email}, headers=auth(patient))
        assert response.status_code == 404
        assert response.json() == NO_DOCTOR
    assert db_session.scalar(select(func.count()).select_from(DoctorAccess)) == 0


@pytest.mark.parametrize("field", ["patient_id", "doctor_id"])
def test_client_supplied_ids_are_rejected(
    db_client: TestClient,
    db_session: Session,
    patient: User,
    other_patient: User,
    doctor: User,
    auth: Callable,
    field: str,
) -> None:
    body = {"email": doctor.email, field: str(other_patient.id)}

    response = db_client.post(GRANTS, json=body, headers=auth(patient))

    assert response.status_code == 422
    assert db_session.scalar(select(func.count()).select_from(DoctorAccess)) == 0


def test_grant_list_shows_only_my_active_doctors(
    db_client: TestClient,
    patient: User,
    other_patient: User,
    doctor: User,
    other_doctor: User,
    auth: Callable,
    share: Callable,
) -> None:
    kept = share(patient, doctor)
    revoked = share(patient, other_doctor)
    share(other_patient, other_doctor)
    db_client.delete(f"{GRANTS}/{revoked['id']}", headers=auth(patient))

    response = db_client.get(GRANTS, headers=auth(patient))

    assert [grant["id"] for grant in response.json()["grants"]] == [kept["id"]]


# Revoking


def test_revoke_closes_the_grant_and_keeps_the_row(
    db_client: TestClient,
    db_session: Session,
    patient: User,
    doctor: User,
    auth: Callable,
    share: Callable,
) -> None:
    grant = share(patient, doctor)

    response = db_client.delete(f"{GRANTS}/{grant['id']}", headers=auth(patient))

    assert response.status_code == 204
    [row] = grant_rows(db_session, patient, doctor)
    db_session.refresh(row)
    assert row.revoked_at is not None
    assert row.revoked_at >= row.granted_at


def test_revoking_twice_gets_404(
    db_client: TestClient, patient: User, doctor: User, auth: Callable, share: Callable
) -> None:
    url = f"{GRANTS}/{share(patient, doctor)['id']}"

    assert db_client.delete(url, headers=auth(patient)).status_code == 204
    assert db_client.delete(url, headers=auth(patient)).status_code == 404


def test_cannot_revoke_another_patients_grant(
    db_client: TestClient,
    db_session: Session,
    patient: User,
    other_patient: User,
    doctor: User,
    auth: Callable,
    share: Callable,
) -> None:
    grant = share(patient, doctor)

    response = db_client.delete(f"{GRANTS}/{grant['id']}", headers=auth(other_patient))

    assert response.status_code == 404
    assert response.json() == NOT_FOUND
    [row] = grant_rows(db_session, patient, doctor)
    assert row.revoked_at is None


def test_regrant_adds_a_new_row_and_keeps_the_earlier_one(
    db_client: TestClient,
    db_session: Session,
    patient: User,
    doctor: User,
    auth: Callable,
    share: Callable,
) -> None:
    first = share(patient, doctor)
    db_client.delete(f"{GRANTS}/{first['id']}", headers=auth(patient))

    second = share(patient, doctor)

    assert second["id"] != first["id"]
    rows = grant_rows(db_session, patient, doctor)
    assert len(rows) == 2
    assert sum(row.revoked_at is None for row in rows) == 1


# Doctor access


def test_doctor_lists_only_active_shared_patients(
    db_client: TestClient,
    patient: User,
    other_patient: User,
    doctor: User,
    other_doctor: User,
    auth: Callable,
    share: Callable,
) -> None:
    share(patient, doctor)
    share(other_patient, other_doctor)

    response = db_client.get(PATIENTS, headers=auth(doctor))

    [shared] = response.json()["patients"]
    assert set(shared) == {"id", "name", "email", "granted_at"}
    assert shared["id"] == str(patient.id)
    assert shared["name"] == "Pat Patient"


def test_doctor_with_no_patients_gets_an_empty_list(
    db_client: TestClient, doctor: User, auth: Callable
) -> None:
    assert db_client.get(PATIENTS, headers=auth(doctor)).json() == {"patients": []}


def test_doctor_reads_past_and_later_entries_of_a_shared_patient(
    db_client: TestClient,
    patient: User,
    doctor: User,
    auth: Callable,
    share: Callable,
    add_entry: Callable,
) -> None:
    add_entry(patient, occurred_on="2026-01-01", notes="Before sharing")
    share(patient, doctor)
    add_entry(patient, occurred_on="2026-02-01", notes="After sharing")

    response = db_client.get(f"{PATIENTS}/{patient.id}/symptoms", headers=auth(doctor))

    assert response.status_code == 200
    assert [entry["notes"] for entry in response.json()["entries"]] == [
        "After sharing",
        "Before sharing",
    ]


def test_doctor_can_filter_and_read_names_and_trends(
    db_client: TestClient,
    patient: User,
    doctor: User,
    auth: Callable,
    share: Callable,
    add_entry: Callable,
) -> None:
    add_entry(patient, severity=3)
    add_entry(patient, severity=8)
    add_entry(patient, name="Nausea", occurred_on="2026-02-01")
    share(patient, doctor)
    base = f"{PATIENTS}/{patient.id}/symptoms"
    headers = auth(doctor)

    filtered = db_client.get(base, params={"symptom": "headache"}, headers=headers)
    names = db_client.get(f"{base}/names", headers=headers)
    trend = db_client.get(f"{base}/trends", params={"symptom": "headache"}, headers=headers)

    assert len(filtered.json()["entries"]) == 2
    assert [name["key"] for name in names.json()["symptoms"]] == ["nausea", "headache"]
    assert trend.json() == {
        "symptom_key": "headache",
        "points": [{"date": "2026-01-15", "max_severity": 8, "entry_count": 2}],
    }


READ_PATHS = ["symptoms", "symptoms/names", "symptoms/trends?symptom=headache"]


@pytest.mark.parametrize("path", READ_PATHS)
def test_doctor_without_a_grant_gets_404(
    db_client: TestClient,
    patient: User,
    doctor: User,
    auth: Callable,
    add_entry: Callable,
    path: str,
) -> None:
    add_entry(patient, notes="Private")

    response = db_client.get(f"{PATIENTS}/{patient.id}/{path}", headers=auth(doctor))

    assert response.status_code == 404
    assert response.json() == NOT_FOUND


@pytest.mark.parametrize("path", READ_PATHS)
def test_nonexistent_patient_looks_the_same_as_an_unshared_one(
    db_client: TestClient, doctor: User, auth: Callable, path: str
) -> None:
    response = db_client.get(f"{PATIENTS}/{uuid.uuid4()}/{path}", headers=auth(doctor))

    assert response.status_code == 404
    assert response.json() == NOT_FOUND


@pytest.mark.parametrize("path", READ_PATHS)
def test_access_ends_immediately_on_revocation(
    db_client: TestClient,
    patient: User,
    doctor: User,
    auth: Callable,
    share: Callable,
    path: str,
) -> None:
    grant = share(patient, doctor)
    url = f"{PATIENTS}/{patient.id}/{path}"
    assert db_client.get(url, headers=auth(doctor)).status_code == 200

    db_client.delete(f"{GRANTS}/{grant['id']}", headers=auth(patient))

    assert db_client.get(url, headers=auth(doctor)).status_code == 404
    assert db_client.get(PATIENTS, headers=auth(doctor)).json() == {"patients": []}


def test_existing_doctor_token_cannot_outlive_a_revocation(
    db_client: TestClient, patient: User, doctor: User, auth: Callable, share: Callable
) -> None:
    grant = share(patient, doctor)
    token_issued_while_shared = auth(doctor)

    db_client.delete(f"{GRANTS}/{grant['id']}", headers=auth(patient))

    response = db_client.get(f"{PATIENTS}/{patient.id}/symptoms", headers=token_issued_while_shared)
    assert response.status_code == 404


def test_regrant_restores_access(
    db_client: TestClient, patient: User, doctor: User, auth: Callable, share: Callable
) -> None:
    db_client.delete(f"{GRANTS}/{share(patient, doctor)['id']}", headers=auth(patient))

    share(patient, doctor)

    assert db_client.get(f"{PATIENTS}/{patient.id}/symptoms", headers=auth(doctor)).is_success


def test_grant_for_one_doctor_does_not_cover_another(
    db_client: TestClient,
    patient: User,
    doctor: User,
    other_doctor: User,
    auth: Callable,
    share: Callable,
) -> None:
    share(patient, doctor)

    response = db_client.get(f"{PATIENTS}/{patient.id}/symptoms", headers=auth(other_doctor))

    assert response.status_code == 404


def test_grant_from_one_patient_does_not_cover_another(
    db_client: TestClient,
    patient: User,
    other_patient: User,
    doctor: User,
    auth: Callable,
    share: Callable,
    add_entry: Callable,
) -> None:
    add_entry(other_patient, notes="Private")
    share(patient, doctor)

    response = db_client.get(f"{PATIENTS}/{other_patient.id}/symptoms", headers=auth(doctor))

    assert response.status_code == 404


def test_doctor_with_a_grant_still_cannot_change_records(
    db_client: TestClient,
    db_session: Session,
    patient: User,
    doctor: User,
    auth: Callable,
    share: Callable,
    add_entry: Callable,
) -> None:
    entry = add_entry(patient)
    share(patient, doctor)
    headers = auth(doctor)
    url = f"/api/symptoms/{entry.id}"
    new_entry = {"symptom_name": "Cough", "occurred_on": "2026-01-15", "severity": 5}

    responses = [
        db_client.patch(url, json={"severity": 1}, headers=headers),
        db_client.delete(url, headers=headers),
        db_client.post("/api/symptoms/batch", json={"entries": [new_entry]}, headers=headers),
    ]

    assert [response.status_code for response in responses] == [403, 403, 403]
    db_session.refresh(entry)
    assert entry.severity == 5


def test_doctor_api_is_read_only(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]

    doctor_paths = {path: item for path, item in paths.items() if path.startswith(PATIENTS)}

    assert len(doctor_paths) == 4
    assert all(set(item) == {"get"} for item in doctor_paths.values())


# Roles and authentication


def test_every_route_requires_authentication(db_client: TestClient, patient: User) -> None:
    grant_id = uuid.uuid4()
    requests = [
        ("POST", LOOKUP),
        ("GET", GRANTS),
        ("POST", GRANTS),
        ("DELETE", f"{GRANTS}/{grant_id}"),
        ("GET", PATIENTS),
        ("GET", f"{PATIENTS}/{patient.id}/symptoms"),
        ("GET", f"{PATIENTS}/{patient.id}/symptoms/names"),
        ("GET", f"{PATIENTS}/{patient.id}/symptoms/trends?symptom=x"),
    ]

    for method, url in requests:
        kwargs = {"json": {"email": "a@example.com"}} if method == "POST" else {}
        assert db_client.request(method, url, **kwargs).status_code == 401, url


def test_doctors_cannot_use_patient_sharing_routes(
    db_client: TestClient, doctor: User, other_doctor: User, auth: Callable
) -> None:
    headers = auth(doctor)
    body = {"email": other_doctor.email}

    assert db_client.post(LOOKUP, json=body, headers=headers).status_code == 403
    assert db_client.get(GRANTS, headers=headers).status_code == 403
    assert db_client.post(GRANTS, json=body, headers=headers).status_code == 403
    assert db_client.delete(f"{GRANTS}/{uuid.uuid4()}", headers=headers).status_code == 403


@pytest.mark.parametrize("path", ["", "/{id}/symptoms", "/{id}/symptoms/names"])
def test_patients_cannot_use_doctor_routes_even_for_themselves(
    db_client: TestClient, patient: User, auth: Callable, path: str
) -> None:
    url = PATIENTS + path.replace("{id}", str(patient.id))

    assert db_client.get(url, headers=auth(patient)).status_code == 403


def test_sharing_logs_no_personal_data(
    db_client: TestClient,
    patient: User,
    doctor: User,
    auth: Callable,
    share: Callable,
    add_entry: Callable,
    caplog: pytest.LogCaptureFixture,
) -> None:
    add_entry(patient, name="Secret Symptom", notes="private detail")

    with caplog.at_level(logging.DEBUG):
        db_client.post(LOOKUP, json={"email": doctor.email}, headers=auth(patient))
        share(patient, doctor)
        db_client.get(f"{PATIENTS}/{patient.id}/symptoms", headers=auth(doctor))

    assert doctor.email not in caplog.text
    assert "Secret Symptom" not in caplog.text
    assert "private detail" not in caplog.text
