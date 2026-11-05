"""Responses shared by the patient and doctor routes, which read the same records."""

import uuid

from sqlalchemy.orm import Session

from app.schemas import (
    SymptomEntryResponse,
    SymptomHistoryFilters,
    SymptomHistoryResponse,
    SymptomName,
    SymptomNameListResponse,
    SymptomTrendFilters,
    SymptomTrendResponse,
    TrendPoint,
)
from app.services.symptoms import daily_max_severity, list_entries, list_symptom_names


def history_response(
    db: Session, patient_id: uuid.UUID, filters: SymptomHistoryFilters
) -> SymptomHistoryResponse:
    rows, total = list_entries(db, patient_id, filters)
    return SymptomHistoryResponse(
        entries=[SymptomEntryResponse.model_validate(row) for row in rows],
        total=total,
        page=filters.page,
        page_size=filters.page_size,
    )


def names_response(db: Session, patient_id: uuid.UUID) -> SymptomNameListResponse:
    return SymptomNameListResponse(
        symptoms=[SymptomName(**row) for row in list_symptom_names(db, patient_id)]
    )


def trend_response(
    db: Session, patient_id: uuid.UUID, filters: SymptomTrendFilters
) -> SymptomTrendResponse:
    rows = daily_max_severity(db, patient_id, filters)
    return SymptomTrendResponse(
        symptom_key=filters.symptom,
        points=[TrendPoint.model_validate(row, from_attributes=True) for row in rows],
    )
