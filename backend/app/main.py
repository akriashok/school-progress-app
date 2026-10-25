from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.v1 import academics, auth, exams, imports, misc, people, results, school
from app.core.config import get_settings
from app.core.errors import install_error_handlers
from app.core.logging import configure_logging, request_context


def create_app() -> FastAPI:
    settings = get_settings()  # fails fast on unsafe production config
    configure_logging(json_logs=not settings.is_dev)

    app = FastAPI(
        title="VidyaTrack API",
        version="1.0.0",
        description="School Progress App: marks, results, report cards and dashboards. "
        "All school data is scoped by the school in the access token.",
        openapi_url="/api/v1/openapi.json",
        docs_url="/docs",
        redoc_url=None,
    )
    install_error_handlers(app)
    app.add_middleware(BaseHTTPMiddleware, dispatch=request_context)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )

    api = APIRouter(prefix="/api/v1")
    for module in (auth, school, academics, people, exams, results, imports):
        api.include_router(module.router)
    api.include_router(school.public)
    api.include_router(results.dash)
    api.include_router(misc.router)
    api.include_router(misc.admin)
    app.include_router(api)

    @app.get("/health", tags=["ops"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
