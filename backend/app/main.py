import logging

from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.auth import router as auth_router
from app.api.doctor import router as doctor_router
from app.api.health import router as health_router
from app.api.sharing import router as sharing_router
from app.api.symptoms import router as symptoms_router
from app.config import Settings, get_settings
from app.log_filters import install_log_filters
from app.services.insights import build_insight_provider

logger = logging.getLogger(__name__)


def constraint_name(exc: SQLAlchemyError) -> str | None:
    diagnostics = getattr(getattr(exc, "orig", None), "diag", None)
    return getattr(diagnostics, "constraint_name", None)


def format_validation_errors(exc: RequestValidationError) -> list[dict[str, str]]:
    """Build field errors. FastAPI's default echoes the input, which can be a password."""
    errors = []
    for error in exc.errors():
        location = [str(part) for part in error["loc"] if part not in ("body", "query", "path")]
        errors.append(
            {
                "field": ".".join(location) or "body",
                "message": error["msg"].removeprefix("Value error, "),
            }
        )
    return errors


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    install_log_filters()
    app = FastAPI(title="HealthTrack API")
    app.state.settings = settings
    app.state.insight_provider = build_insight_provider(settings)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": "Validation failed", "errors": format_validation_errors(exc)},
        )

    # Registered before CORSMiddleware so that it runs inside it. A global exception
    # handler would run outside CORS, and browsers would report a 500 as a network error.
    @app.middleware("http")
    async def handle_unexpected_errors(request: Request, call_next) -> Response:
        try:
            return await call_next(request)
        except SQLAlchemyError as exc:
            # No traceback: PostgreSQL error text can quote the failing row, and with it
            # symptom names and notes. The constraint name is enough to investigate.
            logger.error(
                "Database error on %s %s: %s (constraint: %s)",
                request.method,
                request.url.path,
                type(exc).__name__,
                constraint_name(exc),
            )
        except Exception:
            logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    app.include_router(health_router, prefix="/api")
    app.include_router(auth_router, prefix="/api")
    app.include_router(symptoms_router, prefix="/api")
    app.include_router(sharing_router, prefix="/api")
    app.include_router(doctor_router, prefix="/api")
    return app
