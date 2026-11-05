import json
import logging
from datetime import date
from threading import BoundedSemaphore

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_insight_provider
from app.schemas import SymptomRecordFilters
from app.services.insights import (
    PROVIDERS,
    ChatInsightProvider,
    InsightProviderError,
    InsightText,
    build_insight_provider,
    direction_of,
    generate_text,
    insight_period,
    provider_facts,
    remove_blocked,
)
from app.services.symptoms import today_in_timezone
from tests.conftest import build_settings, register_and_login


class FakeProvider:
    def __init__(self, result: InsightText | Exception) -> None:
        self.result = result
        self.calls: list[dict] = []

    def generate(self, facts: dict) -> InsightText:
        self.calls.append(facts)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


GOOD_TEXT = InsightText(
    observations=["Headache was your most severe symptom."],
    general_wellness=["A regular sleep routine can help you feel your best."],
)


def chat_reply(content: str | None, finish_reason: str = "stop") -> dict:
    return {"choices": [{"finish_reason": finish_reason, "message": {"content": content}}]}


def provider_for(handler, name: str = "groq") -> ChatInsightProvider:
    return ChatInsightProvider(
        PROVIDERS[name], "test-key", "test-model", 1.0, httpx.MockTransport(handler)
    )


def replying(status: int, body: dict) -> ChatInsightProvider:
    return provider_for(lambda request: httpx.Response(status, json=body))


def test_no_key_means_no_provider() -> None:
    assert build_insight_provider(build_settings()) is None


def test_blank_key_means_no_provider() -> None:
    assert build_insight_provider(build_settings(ai_api_key="  ")) is None


@pytest.mark.parametrize("name", ["groq", "openrouter"])
def test_a_key_builds_the_chosen_provider_with_its_default_model(name: str) -> None:
    provider = build_insight_provider(build_settings(ai_api_key="k", ai_provider=name))
    assert provider.spec is PROVIDERS[name]
    assert provider.model == PROVIDERS[name].default_model


def test_the_model_can_be_overridden() -> None:
    provider = build_insight_provider(build_settings(ai_api_key="k", ai_model="m"))
    assert provider.model == "m"


def test_an_unknown_provider_is_rejected() -> None:
    with pytest.raises(ValueError, match="ai_provider"):
        build_settings(ai_provider="other")


def test_the_key_never_appears_in_settings_output() -> None:
    assert "secret-value" not in repr(build_settings(ai_api_key="secret-value"))


def test_default_period_is_the_last_thirty_days() -> None:
    start, end = insight_period(SymptomRecordFilters(), date(2026, 3, 30))
    assert (start, end) == (date(2026, 3, 1), date(2026, 3, 30))


def test_period_follows_the_selected_dates() -> None:
    filters = SymptomRecordFilters(start_date="2026-01-01", end_date="2026-02-01")
    assert insight_period(filters, date(2026, 3, 30)) == (date(2026, 1, 1), date(2026, 2, 1))


@pytest.mark.parametrize(
    ("earlier", "later", "expected"),
    [
        ([2, 3], [6, 7], "higher"),
        ([7, 6], [2, 3], "lower"),
        ([4, 5], [4, 5], "steady"),
        ([4], [4, 5], "not enough data"),
        ([], [4, 5], "not enough data"),
    ],
)
def test_direction(earlier: list[int], later: list[int], expected: str) -> None:
    assert direction_of(earlier, later) == expected


@pytest.mark.parametrize(
    "text",
    [
        "This may be a sign of a migraine.",
        "These could be signs of poor circulation.",
        "Severity indicating a worsening condition.",
        "You might have an infection.",
        "Consider taking ibuprofen.",
        "Take 200 mg before bed.",
        "A doctor could diagnose this.",
        "Your medication may need changing.",
    ],
)
def test_medical_claims_are_dropped(text: str) -> None:
    assert remove_blocked([text]) == []


@pytest.mark.parametrize(
    "text",
    [
        "You have logged headache on 12 days.",
        "Recorded severity was lower in the later half.",
        "Keeping a regular sleep routine can help you feel rested.",
    ],
)
def test_plain_observations_are_kept(text: str) -> None:
    assert remove_blocked([text]) == [text]


def test_a_patients_own_symptom_name_is_allowed() -> None:
    text = "Your migraine was recorded as higher in the later half."
    assert remove_blocked([text], ["Migraine"]) == [text]


def test_a_symptom_name_does_not_excuse_other_claims() -> None:
    assert remove_blocked(["Your fatigue may be a sign of anaemia."], ["Fatigue"]) == []


def test_malformed_replies_do_not_escape_as_crashes() -> None:
    for body in ([], "text", {"choices": [None]}, {"choices": {}}):
        with pytest.raises(InsightProviderError):
            provider_for(lambda request, b=body: httpx.Response(200, json=b)).generate({})


def test_too_many_requests_at_once_get_no_text(monkeypatch: pytest.MonkeyPatch) -> None:
    busy = BoundedSemaphore(1)
    busy.acquire()
    monkeypatch.setattr("app.services.insights.PROVIDER_SLOTS", busy)
    provider = FakeProvider(GOOD_TEXT)
    assert generate_text(provider, {}) is None
    assert provider.calls == []


def test_a_very_early_end_date_does_not_overflow() -> None:
    filters = SymptomRecordFilters(end_date="0001-01-05")
    assert insight_period(filters, date(2026, 3, 30))[0] == date.min


def test_the_timeout_cannot_exceed_the_browser_limit() -> None:
    with pytest.raises(ValueError, match="ai_timeout_seconds"):
        build_settings(ai_timeout_seconds=60)


def test_provider_failure_gives_no_text() -> None:
    assert generate_text(FakeProvider(InsightProviderError("timeout")), {}) is None


def test_text_with_only_blocked_observations_is_not_shown() -> None:
    text = InsightText(observations=["You might have arthritis."], general_wellness=["Rest."])
    assert generate_text(FakeProvider(text), {}) is None


def test_blocked_wellness_tips_are_removed_but_observations_stay() -> None:
    text = InsightText(observations=["Fatigue was lower."], general_wellness=["Take aspirin."])
    assert generate_text(FakeProvider(text), {}).general_wellness == []


def test_groq_request_and_reply() -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["Authorization"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200, json=chat_reply('{"observations": ["One."], "general_wellness": ["Two."]}')
        )

    assert provider_for(handler).generate({"symptoms": []}).observations == ["One."]
    assert seen["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert seen["auth"] == "Bearer test-key"
    assert seen["body"]["model"] == "test-model"
    assert seen["body"]["response_format"]["json_schema"]["strict"] is True
    assert "max_completion_tokens" in seen["body"]


def test_openrouter_request_excludes_hosts_that_collect_data() -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200, json=chat_reply('{"observations": ["One."], "general_wellness": []}')
        )

    provider_for(handler, "openrouter").generate({})
    assert seen["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert seen["body"]["provider"] == {"data_collection": "deny", "require_parameters": True}
    assert "max_tokens" in seen["body"]


@pytest.mark.parametrize("finish_reason", ["length", "content_filter", "error"])
def test_incomplete_answers_are_rejected(finish_reason: str) -> None:
    with pytest.raises(InsightProviderError, match="incomplete_answer"):
        replying(200, chat_reply("{}", finish_reason)).generate({})


def test_an_error_inside_a_200_is_rejected() -> None:
    with pytest.raises(InsightProviderError, match="incomplete_answer"):
        replying(200, {"error": {"code": 502, "message": "Private symptom"}}).generate({})


@pytest.mark.parametrize("content", ["not json", '{"observations": []}', None])
def test_malformed_output_is_rejected(content: str | None) -> None:
    with pytest.raises(InsightProviderError, match="invalid_output"):
        replying(200, chat_reply(content)).generate({})


@pytest.mark.parametrize("status", [401, 429, 500, 503])
def test_error_statuses_keep_only_the_code(status: int) -> None:
    with pytest.raises(InsightProviderError, match=f"status {status}") as error:
        replying(status, {"error": {"message": "Private symptom"}}).generate({})
    assert "Private symptom" not in str(error.value)


def test_timeouts_become_provider_errors() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("Private symptom", request=request)

    with pytest.raises(InsightProviderError, match="ReadTimeout") as error:
        provider_for(handler).generate({"symptoms": [{"name": "Private symptom"}]})
    assert "Private symptom" not in str(error.value)


def log_entries(client: TestClient, headers: dict[str, str], days: int, name="Headache") -> str:
    today = today_in_timezone("Asia/Kolkata")
    entries = [
        {
            "symptom_name": name,
            "occurred_on": date.fromordinal(today.toordinal() - day).isoformat(),
            "severity": 3 + day % 4,
            "notes": "PRIVATE NOTE",
        }
        for day in range(days)
    ]
    assert client.post("/api/symptoms/batch", json={"entries": entries}, headers=headers).is_success
    return today.isoformat()


def use_provider(app: FastAPI, provider: object) -> None:
    app.dependency_overrides[get_insight_provider] = lambda: provider


@pytest.mark.integration
def test_insights_need_a_patient(db_client: TestClient) -> None:
    assert db_client.post("/api/symptoms/insights", json={}).status_code == 401
    headers = register_and_login(db_client, "doctor@example.com", "doctor")
    assert db_client.post("/api/symptoms/insights", json={}, headers=headers).status_code == 403


@pytest.mark.integration
def test_too_little_data_makes_no_provider_call(
    db_client: TestClient, app: FastAPI, db_session: Session
) -> None:
    provider = FakeProvider(GOOD_TEXT)
    use_provider(app, provider)
    headers = register_and_login(db_client, "few@example.com")
    log_entries(db_client, headers, 2)

    body = db_client.post("/api/symptoms/insights", json={}, headers=headers).json()

    assert body["status"] == "insufficient_data"
    assert body["summary"] is None
    assert provider.calls == []


@pytest.mark.integration
def test_without_a_provider_figures_are_still_returned(
    db_client: TestClient, app: FastAPI, db_session: Session
) -> None:
    use_provider(app, None)
    headers = register_and_login(db_client, "none@example.com")
    log_entries(db_client, headers, 6)

    body = db_client.post("/api/symptoms/insights", json={}, headers=headers).json()

    assert body["status"] == "not_configured"
    assert body["summary"] is None
    assert body["symptoms"][0]["name"] == "Headache"
    assert body["symptoms"][0]["days_logged"] == 6


@pytest.mark.integration
def test_provider_receives_figures_only(
    db_client: TestClient, app: FastAPI, db_session: Session
) -> None:
    provider = FakeProvider(GOOD_TEXT)
    use_provider(app, provider)
    headers = register_and_login(db_client, "private@example.com")
    today = log_entries(db_client, headers, 6)

    body = db_client.post("/api/symptoms/insights", json={}, headers=headers).json()

    assert body["status"] == "ok"
    assert body["summary"]["observations"] == GOOD_TEXT.observations
    sent = str(provider.calls[0])
    assert "PRIVATE NOTE" not in sent
    assert "private@example.com" not in sent
    assert "Asha Rao" not in sent
    assert today not in sent
    assert set(provider.calls[0]) == {"period_days", "symptoms"}


@pytest.mark.integration
def test_provider_failure_keeps_the_figures(
    db_client: TestClient, app: FastAPI, db_session: Session, caplog: pytest.LogCaptureFixture
) -> None:
    use_provider(app, FakeProvider(InsightProviderError("APITimeoutError")))
    headers = register_and_login(db_client, "down@example.com")
    log_entries(db_client, headers, 6, name="Secret symptom")

    with caplog.at_level(logging.WARNING):
        response = db_client.post("/api/symptoms/insights", json={}, headers=headers)

    assert response.status_code == 200
    assert response.json()["status"] == "unavailable"
    assert response.json()["symptoms"][0]["entry_count"] == 6
    assert "Secret symptom" not in caplog.text


@pytest.mark.integration
def test_filters_limit_what_is_summarized(
    db_client: TestClient, app: FastAPI, db_session: Session
) -> None:
    provider = FakeProvider(GOOD_TEXT)
    use_provider(app, provider)
    headers = register_and_login(db_client, "filter@example.com")
    log_entries(db_client, headers, 6, name="Headache")
    log_entries(db_client, headers, 6, name="Fatigue")

    body = db_client.post(
        "/api/symptoms/insights", json={"symptom": "fatigue"}, headers=headers
    ).json()

    assert [item["name"] for item in body["symptoms"]] == ["Fatigue"]


@pytest.mark.integration
def test_another_patients_entries_are_never_included(
    db_client: TestClient, app: FastAPI, db_session: Session
) -> None:
    use_provider(app, None)
    first = register_and_login(db_client, "first@example.com")
    second = register_and_login(db_client, "second@example.com")
    log_entries(db_client, first, 6, name="Headache")
    log_entries(db_client, second, 6, name="Fatigue")

    body = db_client.post("/api/symptoms/insights", json={}, headers=second).json()

    assert [item["name"] for item in body["symptoms"]] == ["Fatigue"]


@pytest.mark.integration
def test_invalid_ranges_are_rejected(db_client: TestClient, db_session: Session) -> None:
    headers = register_and_login(db_client, "range@example.com")
    response = db_client.post(
        "/api/symptoms/insights",
        json={"start_date": "2026-02-01", "end_date": "2026-01-01"},
        headers=headers,
    )
    assert response.status_code == 422


def test_facts_contain_no_dates() -> None:
    facts = provider_facts([], date(2026, 1, 1), date(2026, 1, 30))
    assert facts == {"period_days": 30, "symptoms": []}
