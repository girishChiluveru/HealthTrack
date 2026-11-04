from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.api.deps import DbSession, PatientUser
from app.schemas import SymptomBatchRequest, SymptomBatchResponse, SymptomEntryResponse
from app.services.symptoms import (
    BatchValidationError,
    save_entries,
    today_in_timezone,
    validate_batch,
)

router = APIRouter(prefix="/symptoms", tags=["symptoms"])


@router.post(
    "/batch",
    status_code=status.HTTP_201_CREATED,
    response_model=SymptomBatchResponse,
)
def create_symptom_batch(data: SymptomBatchRequest, user: PatientUser, db: DbSession):
    """Save 1–20 entries for the authenticated patient, or none if any entry is invalid."""
    try:
        entries = validate_batch(data.entries, today_in_timezone(user.timezone))
    except BatchValidationError as exc:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": "Validation failed", "errors": exc.errors},
        )

    rows = save_entries(db, user.id, entries)
    return SymptomBatchResponse(entries=[SymptomEntryResponse.model_validate(row) for row in rows])
