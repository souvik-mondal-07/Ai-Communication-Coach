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
from pymongo import ReturnDocument
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from app.core.security import hash_password, verify_password
from app.db.collections import Collections
from app.models.user import UserDocument


# Verified against when the email is unknown, so "no such account" costs the same Argon2
# work as "wrong password" and response time can't be used to discover registered emails.
_DUMMY_PASSWORD_HASH = hash_password("timing-equalisation-placeholder")


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
        verify_password(password, _DUMMY_PASSWORD_HASH)  # result intentionally discarded
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


# --------------------------------------------------------------------------- Step 14
def update_user_fields(
    db: Database, user_id: ObjectId, fields: dict
) -> UserDocument | None:
    """
    `$set` the given fields on exactly one user, selected by the authenticated
    user's own `_id`, and return the updated document.

    Callers pass keys that were validated against an explicit allow-list
    (see `profile_service`); `updated_at` is always refreshed here. Dotted keys
    such as "profile.bio" work on users created before Step 14 because MongoDB
    creates the missing sub-document.
    """
    return db[Collections.USERS].find_one_and_update(
        {"_id": user_id},
        {"$set": {**fields, "updated_at": datetime.now(timezone.utc)}},
        return_document=ReturnDocument.AFTER,
    )


# An account that already changed its password under the earlier timestamp-based revocation
# (`password_changed_at` set, no `token_version`) is treated as having changed it once.
LEGACY_PASSWORD_CHANGED_VERSION = 1


def effective_token_version(user: UserDocument) -> int:
    """
    The version a token must carry to be valid for this user — the single place that interprets
    the stored fields, used by token validation and by login.

    A stored `token_version` always wins. A record from the earlier build has only
    `password_changed_at`; reading its missing `token_version` as 0 would make tokens that build
    had revoked (which carry no `tv`, i.e. version 0) valid again, so such an account counts as
    having changed its password once. Accounts with neither field have never changed it: 0.
    """
    version = user.get("token_version")
    if isinstance(version, int) and not isinstance(version, bool):
        return version
    return LEGACY_PASSWORD_CHANGED_VERSION if user.get("password_changed_at") is not None else 0


def migrate_legacy_token_versions(db: Database, user_id: ObjectId | None = None) -> int:
    """
    Persist `effective_token_version` for records written by the earlier build.

    Idempotent and safe to run concurrently or repeatedly: the update is conditional on the
    field still being absent, only touches accounts that really have a password-change
    timestamp, and never lowers or rewrites an existing `token_version`. Returns how many
    accounts were updated. Pass `user_id` to migrate a single account.
    """
    query: dict = {"token_version": {"$exists": False}, "password_changed_at": {"$ne": None}}
    if user_id is not None:
        query["_id"] = user_id
    result = db[Collections.USERS].update_many(
        query, {"$set": {"token_version": LEGACY_PASSWORD_CHANGED_VERSION}}
    )
    return result.modified_count


def update_password(db: Database, user_id: ObjectId, new_password: str) -> int:
    """
    Hash with the shared Argon2 hasher and store. The plaintext is never persisted or logged.

    In the same atomic update the user's `token_version` is incremented, which invalidates
    every access token issued before this moment (see `core.dependencies.get_current_user`),
    so a stolen token stops working as soon as the owner changes their password. Returns the
    new version so the caller can issue a fresh token for the current device.
    """
    # A record from the earlier build has no `token_version`; incrementing the missing field
    # would restart at 1 and could reuse a version a live token already carries.
    migrate_legacy_token_versions(db, user_id)
    updated = db[Collections.USERS].find_one_and_update(
        {"_id": user_id},
        {
            "$set": {"password_hash": hash_password(new_password), "updated_at": datetime.now(timezone.utc)},
            "$inc": {"token_version": 1},
        },
        return_document=ReturnDocument.AFTER,
    )
    return int(updated.get("token_version", 0)) if updated else 0
