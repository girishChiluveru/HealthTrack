from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database import check_database_connection, get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Report that the API process is running. Does not touch the database."""
    return {"status": "ok", "service": "healthtrack-api"}


@router.get("/health/db")
def database_health(db: Annotated[Session, Depends(get_db)], response: Response) -> dict[str, str]:
    """Report whether the API can reach the database."""
    if check_database_connection(db):
        return {"status": "ok", "database": "connected"}
    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "error", "database": "unavailable"}
