"""
Global exception handlers.

Registered on the FastAPI app in `main.py`. These guarantee every error
response — expected (HTTPException) or unexpected (any other exception) —
comes back in the same `{ success, message, error_code }` shape, and that
unexpected errors are logged server-side without leaking internals to the
client.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.utils.helpers import error_response
from app.utils.logger import get_logger

logger = get_logger(__name__)

_STATUS_TO_ERROR_CODE = {
    status.HTTP_400_BAD_REQUEST: "BAD_REQUEST",
    status.HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
    status.HTTP_403_FORBIDDEN: "FORBIDDEN",
    status.HTTP_404_NOT_FOUND: "NOT_FOUND",
    status.HTTP_409_CONFLICT: "CONFLICT",
    status.HTTP_422_UNPROCESSABLE_ENTITY: "VALIDATION_ERROR",
    status.HTTP_503_SERVICE_UNAVAILABLE: "SERVICE_UNAVAILABLE",
}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
        # Routes may raise HTTPException(detail={"message": ..., "error_code": ...})
        # for precise, domain-specific error codes (e.g. EMAIL_ALREADY_EXISTS).
        # Anything else falls back to a generic status-based mapping.
        if isinstance(exc.detail, dict) and "message" in exc.detail and "error_code" in exc.detail:
            content = error_response(exc.detail["message"], exc.detail["error_code"])
        else:
            error_code = _STATUS_TO_ERROR_CODE.get(exc.status_code, "HTTP_ERROR")
            content = error_response(str(exc.detail), error_code)

        return JSONResponse(
            status_code=exc.status_code,
            content=content,
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_response("Invalid request data.", "VALIDATION_ERROR"),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error("Unhandled error on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response(
                "An unexpected error occurred.", "INTERNAL_SERVER_ERROR"
            ),
        )
