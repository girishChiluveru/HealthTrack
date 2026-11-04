import uuid

from fastapi import APIRouter, HTTPException, Response, status

from app.api.deps import DbSession, PatientUser
from app.models import DoctorAccess, User
from app.schemas import (
    AccessGrantListResponse,
    AccessGrantResponse,
    DoctorEmailRequest,
    DoctorSummary,
)
from app.services.sharing import (
    find_doctor_by_email,
    grant_access,
    list_active_grants,
    revoke_access,
)

router = APIRouter(prefix="/sharing", tags=["sharing"])


def require_doctor(data: DoctorEmailRequest, db: DbSession) -> User:
    doctor = find_doctor_by_email(db, data.email)
    if doctor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No doctor account was found for this email",
        )
    return doctor


def to_response(grant: DoctorAccess, doctor: User) -> AccessGrantResponse:
    return AccessGrantResponse(
        id=grant.id,
        doctor=DoctorSummary.model_validate(doctor),
        granted_at=grant.granted_at,
    )


@router.post("/lookup")
def look_up_doctor(data: DoctorEmailRequest, user: PatientUser, db: DbSession) -> DoctorSummary:
    """Show who an email belongs to, so the patient can confirm before sharing."""
    return DoctorSummary.model_validate(require_doctor(data, db))


@router.get("/grants")
def read_grants(user: PatientUser, db: DbSession) -> AccessGrantListResponse:
    """List the doctors who can currently see the patient's records."""
    grants = list_active_grants(db, user.id)
    return AccessGrantListResponse(grants=[to_response(grant, grant.doctor) for grant in grants])


@router.post("/grants", status_code=status.HTTP_201_CREATED)
def create_grant(
    data: DoctorEmailRequest, user: PatientUser, db: DbSession, response: Response
) -> AccessGrantResponse:
    """Share records with a doctor. Returns 200 and the existing grant if already shared."""
    doctor = require_doctor(data, db)
    grant, created = grant_access(db, user.id, doctor)
    if not created:
        response.status_code = status.HTTP_200_OK
    return to_response(grant, doctor)


@router.delete("/grants/{grant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_grant(grant_id: uuid.UUID, user: PatientUser, db: DbSession) -> None:
    """Stop sharing. The doctor loses access on their next request."""
    if not revoke_access(db, user.id, grant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
