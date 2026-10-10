"""
User document shape.

MongoDB is accessed directly via PyMongo (no ODM), so this module documents
the shape of a `users` document rather than mapping to it automatically.
See `app.services.auth.auth_service` for the code that reads/writes these
documents, and `app.schemas.auth` for the request/response shapes exposed
over the API.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, NotRequired, TypedDict

from bson import ObjectId


class UserDocument(TypedDict):
    """Shape of a document in the `users` collection."""

    _id: ObjectId
    name: str
    email: str
    password_hash: str
    created_at: datetime
    updated_at: datetime
    is_active: bool
    # Step 14 — optional so documents created before Step 14 stay valid. Missing
    # values are filled with safe defaults when read (see profile_service).
    # The display name stays in the existing top-level `name` field.
    profile: NotRequired[dict[str, Any]]
    preferences: NotRequired[dict[str, Any]]
    # Incremented on password change; access tokens carry the version they were issued for
    # and are rejected once it no longer matches (absent = 0).
    token_version: NotRequired[int]
    # Legacy: written by an earlier build that revoked tokens by timestamp. No longer written;
    # only read, to migrate such accounts to `token_version` (auth_service.effective_token_version).
    password_changed_at: NotRequired[datetime | None]
