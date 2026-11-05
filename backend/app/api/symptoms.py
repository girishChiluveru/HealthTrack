import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.api.deps import DbSession, InsightProviderDep, PatientUser
from app.api.records import history_response, names_response, trend_response
from app.models import SymptomEntry
from app.schemas import (
    InsightResponse,
    InsightSummary,
    SymptomBatchRequest,
    SymptomEntryListResponse,
    SymptomEntryResponse,
    SymptomEntryUpdate,
    SymptomHistoryFilters,
    SymptomHistoryResponse,
    SymptomNameListResponse,
    SymptomRecordFilters,
    SymptomTrendFilters,
    SymptomTrendResponse,
)
from app.services.insights import (
    MIN_LOGGED_DAYS,
    compute_figures,
    generate_text,
    insight_period,
    provider_facts,
)
from app.services.symptoms import (
    SymptomValidationError,
    delete_entry,
    get_owned_entry,
    save_entries,
    today_in_timezone,
    update_entry,
    validate_batch,
    validate_update,
)

router = APIRouter(prefix="/symptoms", tags=["symptoms"])


def validation_failed(exc: SymptomValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": "Validation failed", "errors": exc.errors},
    )


def require_owned_entry(entry_id: uuid.UUID, user: PatientUser, db: DbSession) -> SymptomEntry:
    entry = get_owned_entry(db, user.id, entry_id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return entry


OwnedEntry = Annotated[SymptomEntry, Depends(require_owned_entry)]


@router.get("")
def read_symptom_history(
    filters: Annotated[SymptomHistoryFilters, Query()], user: PatientUser, db: DbSession
) -> SymptomHistoryResponse:
    """List one page of the patient's entries, newest occurrence first."""
    return history_response(db, user.id, filters)


@router.get("/names")
def read_symptom_names(user: PatientUser, db: DbSession) -> SymptomNameListResponse:
    """List the patient's distinct symptoms, most recently logged first."""
    return names_response(db, user.id)


@router.get("/trends")
def read_symptom_trend(
    filters: Annotated[SymptomTrendFilters, Query()], user: PatientUser, db: DbSession
) -> SymptomTrendResponse:
    """Return the daily maximum severity of one symptom, with no points for empty days."""
    return trend_response(db, user.id, filters)


@router.post("/insights")
def create_symptom_insights(
    filters: SymptomRecordFilters, user: PatientUser, db: DbSession, provider: InsightProviderDep
) -> InsightResponse:
    """Summarize the patient's figures, with AI text only when a provider is configured."""
    start, end = insight_period(filters, today_in_timezone(user.timezone))
    figures, logged_days, omitted = compute_figures(db, user.id, filters, start, end)
    # Returns the connection, so a slow provider does not hold one for the whole wait.
    db.rollback()

    def respond(status: str, summary: InsightSummary | None = None) -> InsightResponse:
        return InsightResponse(
            status=status,
            start_date=start,
            end_date=end,
            symptoms=figures,
            omitted_symptom_count=omitted,
            summary=summary,
        )

    if logged_days < MIN_LOGGED_DAYS:
        return respond("insufficient_data")
    if provider is None:
        return respond("not_configured")
    text = generate_text(provider, provider_facts(figures, start, end))
    if text is None:
        return respond("unavailable")
    return respond("ok", InsightSummary(**text.model_dump()))


@router.post(
    "/batch",
    status_code=status.HTTP_201_CREATED,
    response_model=SymptomEntryListResponse,
)
def create_symptom_batch(data: SymptomBatchRequest, user: PatientUser, db: DbSession):
    """Save 1–20 entries for the authenticated patient, or none if any entry is invalid."""
    try:
        entries = validate_batch(data.entries, today_in_timezone(user.timezone))
    except SymptomValidationError as exc:
        return validation_failed(exc)

    rows = save_entries(db, user.id, entries)
    return SymptomEntryListResponse(
        entries=[SymptomEntryResponse.model_validate(row) for row in rows]
    )


@router.patch(
    "/{entry_id}",
    response_model=SymptomEntryResponse,
    # The body is validated in the handler, so the date rule can use the patient's timezone.
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {"application/json": {"schema": SymptomEntryUpdate.model_json_schema()}},
        }
    },
)
def update_symptom_entry(data: dict[str, Any], entry: OwnedEntry, user: PatientUser, db: DbSession):
    """Change only the supplied fields of one of the patient's entries."""
    try:
        update = validate_update(data, today_in_timezone(user.timezone))
    except SymptomValidationError as exc:
        return validation_failed(exc)

    return SymptomEntryResponse.model_validate(update_entry(db, entry, update))


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_symptom_entry(entry: OwnedEntry, db: DbSession) -> None:
    """Permanently delete one of the patient's entries."""
    delete_entry(db, entry)
