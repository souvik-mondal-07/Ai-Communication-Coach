"""
Placeholder auth routes.

Registration, login, and JWT-based session endpoints are implemented in a
later step. This router is mounted with no routes yet so the API structure
(`/api/v1/auth/...`) is already in place.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["auth"])
