"""Health check endpoint."""

from fastapi import APIRouter

from app.core.config import settings
from app.db import mongodb

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict:
    """
    Basic liveness check for the API.

    Includes MongoDB connection status so a broken local database is easy
    to spot without digging through logs.
    """
    return {
        "status": "ok",
        "service": "ai-cybersec-mentor",
        "database_connected": mongodb.is_connected(),
        "environment": settings.app_env,
    }
