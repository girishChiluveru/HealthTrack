from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from tests.conftest import register_and_login

pytestmark = pytest.mark.integration

DAY = date(2026, 1, 1)


def log_days(client: TestClient, headers: dict[str, str], name: str, count: int) -> None:
    for offset in range(0, count, 20):
        entries = [
            {
                "symptom_name": name,
                "occurred_on": (DAY + timedelta(days=day)).isoformat(),
                "severity": 1 + day % 10,
            }
            for day in range(offset, min(offset + 20, count))
        ]
        response = client.post("/api/symptoms/batch", json={"entries": entries}, headers=headers)
        assert response.status_code == 201


def test_default_page_holds_twenty_five_entries_and_the_total(db_client: TestClient) -> None:
    headers = register_and_login(db_client, "default@example.com")
    log_days(db_client, headers, "Headache", 30)

    body = db_client.get("/api/symptoms", headers=headers).json()

    assert len(body["entries"]) == 25
    assert (body["total"], body["page"], body["page_size"]) == (30, 1, 25)


def test_pages_do_not_overlap_and_stay_newest_first(db_client: TestClient) -> None:
    headers = register_and_login(db_client, "pages@example.com")
    log_days(db_client, headers, "Headache", 7)

    seen = []
    for page in (1, 2, 3):
        response = db_client.get(f"/api/symptoms?page={page}&page_size=3", headers=headers)
        seen.extend(entry["occurred_on"] for entry in response.json()["entries"])

    assert len(seen) == len(set(seen)) == 7
    assert seen == sorted(seen, reverse=True)


def test_entries_on_the_same_day_keep_a_stable_order_across_pages(db_client: TestClient) -> None:
    headers = register_and_login(db_client, "sameday@example.com")
    entries = [
        {"symptom_name": f"Symptom {n}", "occurred_on": DAY.isoformat(), "severity": 3}
        for n in range(9)
    ]
    db_client.post("/api/symptoms/batch", json={"entries": entries}, headers=headers)

    pages = [
        db_client.get(f"/api/symptoms?page={page}&page_size=3", headers=headers).json()["entries"]
        for page in (1, 2, 3)
    ]

    assert len({entry["id"] for page in pages for entry in page}) == 9


def test_total_counts_only_matching_entries(db_client: TestClient) -> None:
    headers = register_and_login(db_client, "filters@example.com")
    log_days(db_client, headers, "Headache", 10)
    log_days(db_client, headers, "Fatigue", 4)

    by_symptom = db_client.get("/api/symptoms?symptom=fatigue&page_size=2", headers=headers).json()
    by_date = db_client.get(
        "/api/symptoms?start_date=2026-01-09&page_size=2", headers=headers
    ).json()

    assert by_symptom["total"] == 4
    assert len(by_symptom["entries"]) == 2
    assert by_date["total"] == 2


def test_a_page_past_the_end_is_empty_but_reports_the_total(db_client: TestClient) -> None:
    headers = register_and_login(db_client, "past@example.com")
    log_days(db_client, headers, "Headache", 3)

    body = db_client.get("/api/symptoms?page=9", headers=headers).json()

    assert body["entries"] == []
    assert body["total"] == 3


@pytest.mark.parametrize(
    "query", ["page=0", "page=-1", "page=abc", "page_size=0", "page_size=101", "page=999999999999"]
)
def test_invalid_paging_is_rejected(db_client: TestClient, query: str) -> None:
    headers = register_and_login(db_client, f"invalid-{abs(hash(query))}@example.com")
    assert db_client.get(f"/api/symptoms?{query}", headers=headers).status_code == 422


def test_trends_are_not_limited_by_paging(db_client: TestClient) -> None:
    headers = register_and_login(db_client, "trend@example.com")
    log_days(db_client, headers, "Headache", 40)

    body = db_client.get("/api/symptoms/trends?symptom=headache", headers=headers).json()

    assert len(body["points"]) == 40


def test_each_patient_counts_only_their_own_entries(db_client: TestClient) -> None:
    first = register_and_login(db_client, "owner-a@example.com")
    second = register_and_login(db_client, "owner-b@example.com")
    log_days(db_client, first, "Headache", 5)

    assert db_client.get("/api/symptoms", headers=second).json()["total"] == 0


def test_doctors_page_through_shared_records_and_lose_them_on_revocation(
    db_client: TestClient,
) -> None:
    patient = register_and_login(db_client, "shared@example.com")
    doctor = register_and_login(db_client, "pager@example.com", "doctor")
    log_days(db_client, patient, "Headache", 5)
    grant = db_client.post(
        "/api/sharing/grants", json={"email": "pager@example.com"}, headers=patient
    ).json()
    patient_id = db_client.get("/api/doctor/patients", headers=doctor).json()["patients"][0]["id"]
    url = f"/api/doctor/patients/{patient_id}/symptoms?page=2&page_size=2"

    body = db_client.get(url, headers=doctor).json()
    assert (len(body["entries"]), body["total"], body["page"]) == (2, 5, 2)

    db_client.delete(f"/api/sharing/grants/{grant['id']}", headers=patient)
    assert db_client.get(url, headers=doctor).status_code == 404
