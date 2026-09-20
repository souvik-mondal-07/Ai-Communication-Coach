"""
Reusable API response conventions.

Every endpoint should return a payload shaped like one of these two helpers
so the frontend can rely on a single, predictable envelope:

    { "success": true,  "message": "...", "data": {...} }
    { "success": false, "message": "...", "error_code": "..." }
"""

import json
import re
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


def parse_json_object(text: str) -> dict:
    """
    Parse a JSON object out of a model response, stripping markdown fences if
    present. Raises ValueError (incl. json.JSONDecodeError) on anything that
    isn't a JSON object.
    """
    cleaned = text.strip()
    fence_match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", cleaned, re.DOTALL)
    if fence_match:
        cleaned = fence_match.group(1).strip()
    parsed = json.loads(cleaned)
    if not isinstance(parsed, dict):
        raise ValueError("Expected a JSON object")
    return parsed
