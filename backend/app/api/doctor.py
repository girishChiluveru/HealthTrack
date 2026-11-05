import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import DbSession, DoctorUser
from app.api.records import history_response, names_response, trend_response
from app.authorization import require_patient_records_access
from app.schemas import (
    SharedPatient,
    SharedPatientListResponse,
    SymptomHistoryFilters,
    SymptomHistoryResponse,
    SymptomNameListResponse,
    SymptomTrendFilters,
    SymptomTrendResponse,
)
from app.services.sharing import list_shared_patients

# Read-only by design: this router must never gain a route that changes patient records.
router = APIRouter(prefix="/doctor", tags=["doctor"])


def require_shared_patient(patient_id: uuid.UUID, doctor: DoctorUser, db: DbSession) -> uuid.UUID:
    """Check for an active grant on every request, so a revocation applies immediately."""
    require_patient_records_access(db, doctor, patient_id)
    return patient_id


SharedPatientId = Annotated[uuid.UUID, Depends(require_shared_patient)]


@router.get("/patients")
def read_shared_patients(doctor: DoctorUser, db: DbSession) -> SharedPatientListResponse:
    """List the patients who currently share their records with this doctor."""
    rows = list_shared_patients(db, doctor.id)
    return SharedPatientListResponse(
        patients=[SharedPatient.model_validate(row, from_attributes=True) for row in rows]
    )


@router.get("/patients/{patient_id}/symptoms")
def read_patient_history(
    patient_id: SharedPatientId,
    filters: Annotated[SymptomHistoryFilters, Query()],
    db: DbSession,
) -> SymptomHistoryResponse:
    return history_response(db, patient_id, filters)


@router.get("/patients/{patient_id}/symptoms/names")
def read_patient_symptom_names(
    patient_id: SharedPatientId, db: DbSession
) -> SymptomNameListResponse:
    return names_response(db, patient_id)


@router.get("/patients/{patient_id}/symptoms/trends")
def read_patient_trend(
    patient_id: SharedPatientId,
    filters: Annotated[SymptomTrendFilters, Query()],
    db: DbSession,
) -> SymptomTrendResponse:
    return trend_response(db, patient_id, filters)
