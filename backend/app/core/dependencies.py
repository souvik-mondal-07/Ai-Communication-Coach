"""
Shared FastAPI dependencies.

Step 1 only wires up database access. `get_current_user` is a placeholder
reserved for the authentication feature — routes that need it can already
import it, and it will start doing real work without changing call sites.
"""

from __future__ import annotations

from fastapi import HTTPException, status
from pymongo.database import Database

from app.db import mongodb


def get_db() -> Database:
    """
    FastAPI dependency that returns the MongoDB database, or a clean 503
    error if the database isn't connected — never a raw connection traceback.
    """
    try:
        return mongodb.get_database()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is currently unavailable.",
        ) from exc


def get_current_user() -> None:
    """
    Placeholder dependency for the future authentication feature.
    Not used by any route yet.
    """
    raise NotImplementedError("Authentication is not implemented yet.")
