"""
Auth service.

Owns all reads/writes to the `users` collection and the logic for
registering and authenticating users. Routes call into this module instead
of touching PyMongo directly, so this is the single place that knows the
shape of a user document.
"""

from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from app.core.security import hash_password, verify_password
from app.db.collections import Collections
from app.models.user import UserDocument


class EmailAlreadyExistsError(Exception):
    """Raised when attempting to register an email that's already taken."""

    def __init__(self, email: str) -> None:
        self.email = email
        super().__init__(f"Email already registered: {email}")


def normalize_email(email: str) -> str:
    return email.strip().lower()


def ensure_indexes(db: Database) -> None:
    """
    Create required indexes. Idempotent — safe to call on every startup.

    The unique index on `email` is the real duplicate-email guarantee;
    application-level checks alone can't prevent a race between two
    concurrent registrations for the same address.
    """
    db[Collections.USERS].create_index("email", unique=True)
    db[Collections.USERS].create_index("created_at")


def create_user(db: Database, *, name: str, email: str, password: str) -> UserDocument:
    normalized_email = normalize_email(email)
    now = datetime.now(timezone.utc)
    document: UserDocument = {
        "name": name.strip(),
        "email": normalized_email,
        "password_hash": hash_password(password),
        "created_at": now,
        "updated_at": now,
        "is_active": True,
    }
    try:
        result = db[Collections.USERS].insert_one(document)
    except DuplicateKeyError as exc:
        raise EmailAlreadyExistsError(normalized_email) from exc

    document["_id"] = result.inserted_id
    return document


def get_user_by_email(db: Database, email: str) -> UserDocument | None:
    return db[Collections.USERS].find_one({"email": normalize_email(email)})


def get_user_by_id(db: Database, user_id: str) -> UserDocument | None:
    try:
        object_id = ObjectId(user_id)
    except (InvalidId, TypeError):
        return None
    return db[Collections.USERS].find_one({"_id": object_id})


def authenticate_user(db: Database, *, email: str, password: str) -> UserDocument | None:
    """
    Return the user document if the credentials are valid, otherwise None.

    Deliberately returns the same "invalid" result whether the email doesn't
    exist, the password is wrong, or the account is inactive — callers
    should surface one generic "Invalid email or password" error either way.
    """
    user = get_user_by_email(db, email)
    if user is None:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    if not user.get("is_active", True):
        return None
    return user


def to_public_user(user: UserDocument) -> dict:
    """Safe, external-facing representation of a user — never the password hash."""
    return {
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
    }
