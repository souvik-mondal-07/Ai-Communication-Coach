"""
Persistence for voice conversation sessions (`voice_conversation_sessions`).

One document per conversation:

    {
      user_id, mode, difficulty, topic, config,
      status: "created" | "active" | "completed" | "abandoned",
      linked: {kind, session_id} | None,   # the Step 9/10/7 session this wraps
      messages: [{role, text, timestamp, audio_available?, duration_seconds?, voice_analysis?}],
      turn_count, user_turn_count, assistant_turn_count,
      started_at, activated_at, last_activity_at, ended_at,
      summary, evaluation,
      processing_token, processing_since,  # per-session turn lock (internal)
    }

`turn_count` counts every spoken turn (AI + user); `user_turn_count` is the
number of answers the learner has given and is what the API reports as the
turn number.

Ownership: every lookup goes through `get_owned`, which compares the stored
`user_id` with the authenticated user's id. Nothing here ever trusts an id
supplied by the client.

Concurrency: a turn is processed under a lock taken with an atomic
compare-and-swap on `processing_token`, so two simultaneous (or duplicated)
submissions can never both run. Every write made during a turn is guarded by
the same token, so a request that lost the lock cannot write.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ASCENDING, DESCENDING
from pymongo.database import Database

from app.core.config import settings
from app.db.collections import Collections

# A lock older than this is treated as abandoned (e.g. the worker crashed).
# Kept above the longest realistic turn (STT + Gemini + TTS timeouts).
LOCK_STALE_SECONDS = 180

MODE_LABELS = {
    "general": "General Conversation",
    "cybersecurity": "Cybersecurity Q&A",
    "communication": "Communication Practice",
    "interview": "Cybersecurity Interview",
    "practice": "Topic Practice",
    "pressure": "Pressure Training",
}


# --- Errors ------------------------------------------------------------------


class VoiceConversationError(Exception):
    """Base class for voice-conversation service errors."""


class SessionNotFoundError(VoiceConversationError):
    pass


class SessionForbiddenError(VoiceConversationError):
    """The session exists but belongs to another user."""


class SessionNotActiveError(VoiceConversationError):
    """The session is not in a state that allows this action."""


class SessionBusyError(VoiceConversationError):
    """Another request is already processing a turn for this session."""


class TurnMismatchError(VoiceConversationError):
    """The client's view of the turn number is out of date (e.g. a retry)."""


# --- Helpers -------------------------------------------------------------------


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime) -> datetime:
    """MongoDB hands back naive UTC datetimes; make them explicit."""
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _iso(value: datetime | None) -> str | None:
    return as_utc(value).isoformat() if value else None


def _public_message(message: dict) -> dict:
    public = {
        "role": message["role"],
        "text": message["text"],
        "timestamp": _iso(message.get("timestamp")),
    }
    if message["role"] == "assistant":
        public["audio_available"] = bool(message.get("audio_available", False))
    else:
        public["duration_seconds"] = message.get("duration_seconds")
        public["voice_analysis"] = message.get("voice_analysis")
    return public


def public_session(doc: dict) -> dict:
    """Client-facing view. Never includes the lock token, profile context or raw ids of other users."""
    linked = doc.get("linked")
    return {
        "session_id": str(doc["_id"]),
        "mode": doc["mode"],
        "mode_label": MODE_LABELS.get(doc["mode"], doc["mode"]),
        "difficulty": doc["difficulty"],
        "topic": doc.get("topic"),
        "status": doc["status"],
        "started_at": _iso(doc["started_at"]),
        "last_activity_at": _iso(doc.get("last_activity_at")),
        "ended_at": _iso(doc.get("ended_at")),
        "turn_count": doc.get("turn_count", 0),
        "user_turn_count": doc.get("user_turn_count", 0),
        "assistant_turn_count": doc.get("assistant_turn_count", 0),
        "max_session_turns": settings.voice_conversation_max_session_turns,
        "linked_session": (
            {"kind": linked["kind"], "session_id": linked["session_id"], "label": linked.get("label")}
            if linked
            else None
        ),
        "messages": [_public_message(m) for m in doc.get("messages", [])],
        "summary": doc.get("summary"),
    }


def summary_row(doc: dict) -> dict:
    return {
        "session_id": str(doc["_id"]),
        "mode": doc["mode"],
        "mode_label": MODE_LABELS.get(doc["mode"], doc["mode"]),
        "difficulty": doc["difficulty"],
        "topic": doc.get("topic"),
        "status": doc["status"],
        "started_at": _iso(doc["started_at"]),
        "ended_at": _iso(doc.get("ended_at")),
        "turn_count": doc.get("turn_count", 0),
        "user_turn_count": doc.get("user_turn_count", 0),
    }


# --- Manager -------------------------------------------------------------------


class VoiceSessionManager:
    def ensure_indexes(self, db: Database) -> None:
        """
        Idempotent. Both indexes start with `user_id`, so plain per-user
        lookups are covered by them; a separate single-field `user_id` index
        would only duplicate that prefix.
        """
        sessions = db[Collections.VOICE_CONVERSATION_SESSIONS]
        sessions.create_index([("user_id", ASCENDING), ("started_at", DESCENDING)])
        sessions.create_index([("user_id", ASCENDING), ("status", ASCENDING)])

    # --- Create / read ---------------------------------------------------------

    def create(
        self,
        db: Database,
        *,
        user_id: str,
        mode: str,
        difficulty: str,
        topic: str | None,
        config: dict,
    ) -> dict:
        now = utcnow()
        document = {
            "user_id": ObjectId(user_id),
            "mode": mode,
            "difficulty": difficulty,
            "topic": topic,
            "config": config,
            "status": "created",
            "linked": None,
            "profile_context": None,
            "messages": [],
            "turn_count": 0,
            "user_turn_count": 0,
            "assistant_turn_count": 0,
            "started_at": now,
            "activated_at": None,
            "last_activity_at": now,
            "ended_at": None,
            "summary": None,
            "evaluation": None,
            "processing_token": None,
            "processing_since": None,
        }
        result = db[Collections.VOICE_CONVERSATION_SESSIONS].insert_one(document)
        document["_id"] = result.inserted_id
        return document

    def get_owned(self, db: Database, *, session_id: str, user_id: str) -> dict:
        try:
            object_id = ObjectId(session_id)
        except (InvalidId, TypeError) as exc:
            raise SessionNotFoundError(session_id) from exc
        session = db[Collections.VOICE_CONVERSATION_SESSIONS].find_one({"_id": object_id})
        if session is None:
            raise SessionNotFoundError(session_id)
        if str(session["user_id"]) != user_id:
            raise SessionForbiddenError(session_id)
        return session

    def list_sessions(self, db: Database, *, user_id: str, page: int, limit: int) -> tuple[list[dict], int]:
        query = {"user_id": ObjectId(user_id)}  # the caller's own sessions only
        collection = db[Collections.VOICE_CONVERSATION_SESSIONS]
        total = collection.count_documents(query)
        cursor = (
            collection.find(query, {"messages": 0})
            .sort("started_at", DESCENDING)
            .skip((page - 1) * limit)
            .limit(limit)
        )
        return list(cursor), total

    # --- Turn lock -----------------------------------------------------------------

    def acquire_lock(self, db: Database, session: dict, *, allowed_statuses: tuple[str, ...]) -> str:
        """
        Take the per-session processing lock, or raise `SessionBusyError`.

        Compare-and-swap on the token we just read: if anything changed it in
        between, the update matches nothing and we back off instead of
        running a second turn.
        """
        now = utcnow()
        current = session.get("processing_token")
        since = session.get("processing_since")
        if current and since is not None and (now - as_utc(since)).total_seconds() < LOCK_STALE_SECONDS:
            raise SessionBusyError(str(session["_id"]))

        token = secrets.token_hex(16)
        result = db[Collections.VOICE_CONVERSATION_SESSIONS].update_one(
            {
                "_id": session["_id"],
                "user_id": session["user_id"],
                "status": {"$in": list(allowed_statuses)},
                "processing_token": current,
            },
            {"$set": {"processing_token": token, "processing_since": now}},
        )
        if result.matched_count == 0:
            raise SessionBusyError(str(session["_id"]))
        return token

    def release_lock(self, db: Database, session_id: ObjectId, token: str) -> None:
        db[Collections.VOICE_CONVERSATION_SESSIONS].update_one(
            {"_id": session_id, "processing_token": token},
            {"$set": {"processing_token": None, "processing_since": None}},
        )

    # --- Guarded writes (all require the lock token) -------------------------------------

    def _guarded_update(self, db: Database, session_id: ObjectId, token: str, update: dict) -> None:
        result = db[Collections.VOICE_CONVERSATION_SESSIONS].update_one(
            {"_id": session_id, "processing_token": token}, update
        )
        if result.matched_count == 0:
            # The lock was lost (stale-lock takeover): nothing was written.
            raise SessionBusyError(str(session_id))

    def activate(
        self,
        db: Database,
        session_id: ObjectId,
        token: str,
        *,
        opening_message: dict,
        linked: dict | None,
        profile_context: dict | None,
    ) -> None:
        now = utcnow()
        self._guarded_update(
            db,
            session_id,
            token,
            {
                "$set": {
                    "status": "active",
                    "activated_at": now,
                    "last_activity_at": now,
                    "linked": linked,
                    "profile_context": profile_context,
                    "assistant_turn_count": 1,
                    "turn_count": 1,
                },
                "$push": {"messages": opening_message},
            },
        )

    def append_exchange(
        self,
        db: Database,
        session_id: ObjectId,
        token: str,
        *,
        user_message: dict,
        assistant_message: dict,
    ) -> None:
        """Save one full exchange (the learner's answer and the AI's reply) in a single write."""
        self._guarded_update(
            db,
            session_id,
            token,
            {
                "$push": {"messages": {"$each": [user_message, assistant_message]}},
                "$inc": {"user_turn_count": 1, "assistant_turn_count": 1, "turn_count": 2},
                "$set": {"last_activity_at": utcnow()},
            },
        )

    def finalize(
        self,
        db: Database,
        session_id: ObjectId,
        token: str,
        *,
        status: str,
        summary: dict,
        evaluation: dict | None,
    ) -> None:
        now = utcnow()
        self._guarded_update(
            db,
            session_id,
            token,
            {
                "$set": {
                    "status": status,
                    "ended_at": now,
                    "last_activity_at": now,
                    "summary": summary,
                    "evaluation": evaluation,
                }
            },
        )
