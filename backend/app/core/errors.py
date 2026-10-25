"""Error shape: { "error": { "code", "message", "details" } }."""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("app.errors")


class AppError(Exception):
    status_code = 400
    code = "BAD_REQUEST"

    def __init__(
        self, message: str, *, code: str | None = None, details: Any = None, status_code: int | None = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code


class NotFound(AppError):
    status_code = 404
    code = "NOT_FOUND"

    def __init__(self, entity: str = "Resource") -> None:
        super().__init__(f"{entity} not found")


class Forbidden(AppError):
    status_code = 403
    code = "FORBIDDEN"

    def __init__(self, message: str = "You do not have permission to do this", **kw: Any) -> None:
        super().__init__(message, **kw)


class Unauthorized(AppError):
    status_code = 401
    code = "UNAUTHORIZED"


class Conflict(AppError):
    status_code = 409
    code = "CONFLICT"


class ValidationFailed(AppError):
    status_code = 422
    code = "VALIDATION_ERROR"


class RateLimited(AppError):
    status_code = 429
    code = "RATE_LIMITED"


def _body(code: str, message: str, details: Any = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details}}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(_body(exc.code, exc.message, exc.details), status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {"loc": list(e.get("loc", [])), "message": e.get("msg"), "type": e.get("type")} for e in exc.errors()
        ]
        return JSONResponse(
            _body("VALIDATION_ERROR", "Request validation failed", jsonable_encoder(details)),
            status_code=422,
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED", 401: "UNAUTHORIZED", 403: "FORBIDDEN"}.get(
            exc.status_code, "HTTP_ERROR"
        )
        return JSONResponse(_body(code, str(exc.detail)), status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        # Log type + request id only; exception text can contain personal data.
        log.error(
            "unhandled_error type=%s request_id=%s", type(exc).__name__, getattr(request.state, "request_id", "-")
        )
        return JSONResponse(_body("INTERNAL_ERROR", "Something went wrong"), status_code=500)
