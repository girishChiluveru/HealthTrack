from fastapi import APIRouter, HTTPException, status

from app.api.deps import AppSettings, CurrentUser, DbSession
from app.schemas import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.security import create_access_token
from app.services.auth import EmailAlreadyRegisteredError, authenticate_user, register_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest, db: DbSession) -> UserResponse:
    try:
        user = register_user(db, data)
    except EmailAlreadyRegisteredError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        ) from None
    return UserResponse.model_validate(user)


@router.post("/login")
def login(data: LoginRequest, db: DbSession, settings: AppSettings) -> TokenResponse:
    user = authenticate_user(db, data.email, data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    return TokenResponse(access_token=create_access_token(user.id, settings))


@router.get("/me")
def read_current_user(user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(user)
