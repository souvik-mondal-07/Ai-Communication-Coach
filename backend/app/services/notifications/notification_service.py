"""
Notification storage (Step 19): CRUD, ownership, deduplication, daily cap, expiry.

Every method takes ``user_id`` from the authenticated JWT and puts it in the query,
so a user can only ever see or change their own notifications; a foreign or
malformed id is indistinguishable from a missing one (``NotificationNotFoundError``).
There is deliberately no public "create notification" API: notifications are only
created by server-side code (reminders, daily-practice completion).

Deduplication: each notification has a ``dedupe_key`` that encodes its intended
period (e.g. ``daily_practice:2026-10-07``). A unique index on (user_id, dedupe_key)
makes "one reminder per period" a database guarantee, even under concurrent requests.
"""

from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import DESCENDING
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from app.db.collections import Collections
from app.schemas.notification import (
    ALLOWED_ACTION_TARGETS,
    NotificationPriority,
    NotificationType,
)

MAX_LIMIT = 50
MAX_TITLE, MAX_MESSAGE = 120, 400


class NotificationNotFoundError(Exception):
    pass


class InvalidNotificationError(ValueError):
    pass


class InvalidDateRangeError(ValueError):
    pass


class PageOutOfRangeError(ValueError):
    pass


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _out(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "type": doc["type"],
        "priority": doc.get("priority", "medium"),
        "title": doc["title"],
        "message": doc["message"],
        "action": doc.get("action"),
        "is_read": bool(doc.get("is_read")),
        "created_at": _utc(doc["created_at"]),
        "read_at": _utc(doc["read_at"]) if doc.get("read_at") else None,
        "expires_at": _utc(doc["expires_at"]) if doc.get("expires_at") else None,
    }


def _oid(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError) as exc:
        raise NotificationNotFoundError(value) from exc


def _not_expired(now: datetime) -> dict:
    # Naive UTC, to match what pymongo stores/returns.
    naive = _utc(now).replace(tzinfo=None)
    return {"$or": [{"expires_at": None}, {"expires_at": {"$gt": naive}}]}


class NotificationService:
    def ensure_indexes(self, db: Database) -> None:
        c = db[Collections.NOTIFICATIONS]
        c.create_index([("user_id", 1), ("dedupe_key", 1)], unique=True)
        c.create_index([("user_id", 1), ("created_at", -1)])
        c.create_index([("user_id", 1), ("is_read", 1)])
        # MongoDB removes expired notifications itself (TTL monitor runs about every minute).
        # Reads also filter on expires_at, so expired items disappear immediately regardless.
        c.create_index("expires_at", expireAfterSeconds=0)

    # ------------------------------------------------------------------ create
    def create_if_absent(
        self, db: Database, *, user_id: str, type: NotificationType, priority: NotificationPriority,
        title: str, message: str, action_target: str | None, dedupe_key: str,
        expires_at: datetime | None, now: datetime | None = None,
    ) -> dict | None:
        """Insert unless one with the same ``dedupe_key`` already exists. Returns the new notification or None."""
        if not isinstance(type, NotificationType):
            raise InvalidNotificationError("Unknown notification type.")
        if action_target is not None and action_target not in ALLOWED_ACTION_TARGETS:
            raise InvalidNotificationError("Notification action target is not an allowed route.")
        now = _utc(now or datetime.now(timezone.utc))
        doc = {
            "user_id": ObjectId(user_id),
            "type": type.value,
            "priority": priority.value,
            "title": title[:MAX_TITLE],
            "message": message[:MAX_MESSAGE],
            "action": {"type": "route", "target": action_target} if action_target else None,
            "is_read": False,
            "created_at": now.replace(tzinfo=None),
            "read_at": None,
            "expires_at": _utc(expires_at).replace(tzinfo=None) if expires_at else None,
            "dedupe_key": dedupe_key,
        }
        try:
            result = db[Collections.NOTIFICATIONS].insert_one(doc)
        except DuplicateKeyError:
            return None
        doc["_id"] = result.inserted_id
        return _out(doc)

    def exists(self, db: Database, *, user_id: str, dedupe_key: str) -> bool:
        return db[Collections.NOTIFICATIONS].count_documents(
            {"user_id": ObjectId(user_id), "dedupe_key": dedupe_key}, limit=1
        ) > 0

    def count_created_between(self, db: Database, *, user_id: str, start: datetime, end: datetime) -> int:
        return db[Collections.NOTIFICATIONS].count_documents({
            "user_id": ObjectId(user_id),
            "created_at": {"$gte": _utc(start).replace(tzinfo=None), "$lt": _utc(end).replace(tzinfo=None)},
        })

    # ------------------------------------------------------------------ read
    def list(
        self, db: Database, *, user_id: str, read: str = "all", type: NotificationType | None = None,
        start_date: datetime | None = None, end_date: datetime | None = None,
        page: int = 1, limit: int = 20, now: datetime | None = None,
    ) -> dict:
        if start_date and end_date and _utc(start_date) > _utc(end_date):
            raise InvalidDateRangeError("start_date must not be after end_date.")
        now = now or datetime.now(timezone.utc)
        query: dict = {"user_id": ObjectId(user_id), **_not_expired(now)}
        if read == "unread":
            query["is_read"] = False
        elif read == "read":
            query["is_read"] = True
        if type:
            query["type"] = type.value
        created: dict = {}
        if start_date:
            created["$gte"] = _utc(start_date).replace(tzinfo=None)
        if end_date:
            created["$lte"] = _utc(end_date).replace(tzinfo=None)
        if created:
            query["created_at"] = created

        collection = db[Collections.NOTIFICATIONS]
        total = collection.count_documents(query)
        if page > 1 and (page - 1) * limit >= total:
            raise PageOutOfRangeError(f"Page {page} is out of range.")
        docs = collection.find(query).sort([("created_at", DESCENDING), ("_id", DESCENDING)]) \
            .skip((page - 1) * limit).limit(limit)
        return {
            "items": [_out(d) for d in docs],
            "page": page, "limit": limit, "total": total,
            "has_next": page * limit < total,
            "unread_count": self.unread_count(db, user_id=user_id, now=now),
        }

    def unread_count(self, db: Database, *, user_id: str, now: datetime | None = None) -> int:
        return db[Collections.NOTIFICATIONS].count_documents(
            {"user_id": ObjectId(user_id), "is_read": False, **_not_expired(now or datetime.now(timezone.utc))}
        )

    # ------------------------------------------------------------------ update / delete
    def mark_read(self, db: Database, *, user_id: str, notification_id: str, now: datetime | None = None) -> dict:
        now = _utc(now or datetime.now(timezone.utc))
        oid = _oid(notification_id)
        collection = db[Collections.NOTIFICATIONS]
        query = {"_id": oid, "user_id": ObjectId(user_id)}
        doc = collection.find_one(query)
        if doc is None:
            raise NotificationNotFoundError(notification_id)
        if not doc.get("is_read"):
            collection.update_one({**query, "is_read": False},
                                  {"$set": {"is_read": True, "read_at": now.replace(tzinfo=None)}})
            doc = collection.find_one(query)
        return _out(doc)

    def mark_all_read(self, db: Database, *, user_id: str, now: datetime | None = None) -> int:
        now = _utc(now or datetime.now(timezone.utc))
        result = db[Collections.NOTIFICATIONS].update_many(
            {"user_id": ObjectId(user_id), "is_read": False},
            {"$set": {"is_read": True, "read_at": now.replace(tzinfo=None)}},
        )
        return result.modified_count

    def delete(self, db: Database, *, user_id: str, notification_id: str) -> None:
        result = db[Collections.NOTIFICATIONS].delete_one({"_id": _oid(notification_id), "user_id": ObjectId(user_id)})
        if result.deleted_count == 0:
            raise NotificationNotFoundError(notification_id)


notification_service = NotificationService()
