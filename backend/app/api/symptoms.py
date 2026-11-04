import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.api.deps import DbSession, PatientUser
from app.models import SymptomEntry
from app.schemas import (
    SymptomBatchRequest,
    SymptomEntryListResponse,
    SymptomEntryResponse,
    SymptomEntryUpdate,
    SymptomHistoryFilters,
    SymptomName,
    SymptomNameListResponse,
    SymptomTrendFilters,
    SymptomTrendResponse,
    TrendPoint,
)
from app.services.symptoms import (
    SymptomValidationError,
    daily_max_severity,
    delete_entry,
    get_owned_entry,
    list_entries,
    list_symptom_names,
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
) -> SymptomEntryListResponse:
    """List the patient's entries, newest occurrence first."""
    rows = list_entries(db, user.id, filters)
    return SymptomEntryListResponse(
        entries=[SymptomEntryResponse.model_validate(row) for row in rows]
    )


@router.get("/names")
def read_symptom_names(user: PatientUser, db: DbSession) -> SymptomNameListResponse:
    """List the patient's distinct symptoms, most recently logged first."""
    return SymptomNameListResponse(
        symptoms=[SymptomName(**row) for row in list_symptom_names(db, user.id)]
    )


@router.get("/trends")
def read_symptom_trend(
    filters: Annotated[SymptomTrendFilters, Query()], user: PatientUser, db: DbSession
) -> SymptomTrendResponse:
    """Return the daily maximum severity of one symptom, with no points for empty days."""
    rows = daily_max_severity(db, user.id, filters)
    return SymptomTrendResponse(
        symptom_key=filters.symptom,
        points=[TrendPoint.model_validate(row, from_attributes=True) for row in rows],
    )


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
