from __future__ import annotations

from fastapi import HTTPException, status


def api_error(code: int, message: str, error_code: str) -> HTTPException:
    return HTTPException(status_code=code, detail={"message": message, "error_code": error_code})


def not_found(message: str = "Session not found.") -> HTTPException:
    return api_error(status.HTTP_404_NOT_FOUND, message, "NOT_FOUND")


def conflict(message: str, error_code: str) -> HTTPException:
    return api_error(status.HTTP_409_CONFLICT, message, error_code)


def invalid(message: str, error_code: str = "VALIDATION_ERROR") -> HTTPException:
    return api_error(status.HTTP_422_UNPROCESSABLE_ENTITY, message, error_code)
