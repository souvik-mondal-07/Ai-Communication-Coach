"""
Reusable API response conventions.

Every endpoint should return a payload shaped like one of these two helpers
so the frontend can rely on a single, predictable envelope:

    { "success": true,  "message": "...", "data": {...} }
    { "success": false, "message": "...", "error_code": "..." }
"""

from typing import Any


def success_response(message: str = "OK", data: Any = None) -> dict:
    return {
        "success": True,
        "message": message,
        "data": data,
    }


def error_response(message: str, error_code: str) -> dict:
    return {
        "success": False,
        "message": message,
        "error_code": error_code,
    }
