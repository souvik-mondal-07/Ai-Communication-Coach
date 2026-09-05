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
from typing import TypedDict

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
