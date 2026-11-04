import logging

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.health import router as health_router
from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title="HealthTrack API")

    # Registered before CORSMiddleware so that it runs inside it. A global exception
    # handler would run outside CORS, and browsers would report a 500 as a network error.
    @app.middleware("http")
    async def handle_unexpected_errors(request: Request, call_next) -> Response:
        try:
            return await call_next(request)
        except Exception:
            logger.exception("Unhandled error on %s %s", request.method, request.url.path)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Internal server error"},
            )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET"],
    )

    app.include_router(health_router, prefix="/api")
    return app
