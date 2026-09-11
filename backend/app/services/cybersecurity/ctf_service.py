"""
CTF service.

Owns all reads/writes to the `ctf_sessions` collection: session creation,
ownership-checked lookups, mentor chat, progressive hint generation, and
completion. Built entirely on the existing, provider-agnostic `AIService` —
never a second Gemini client:

    ctf.py (route) -> CtfService -> AIService -> GeminiClient -> Gemini
"""

from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import DESCENDING
from pymongo.database import Database

from app.db.collections import Collections
from app.models.ctf import CtfSessionDocument
from app.services.ai.ai_service import AIService, ConversationTurn, ai_service
from app.services.ai.prompts import build_ctf_challenge_context, build_ctf_system_prompt

# Bounded context sent to the AI per request — mirrors the approach used by
# MentorService.CONTEXT_WINDOW. All messages are still persisted in full;
# only what's *sent to Gemini* is capped.
CONTEXT_WINDOW = 20

# Hints must be requested in order unless the caller explicitly sets
# force=True — "solution" has no prerequisite, matching the spec's
# "allow requesting the solution directly if the person explicitly wants it".
_HINT_ORDER = ["hint_1", "hint_2", "hint_3"]


class CtfError(Exception):
    """Base class for all CTF-service-level errors."""


class SessionNotFoundError(CtfError):
    pass


class SessionForbiddenError(CtfError):
    """The session exists but doesn't belong to the requesting user."""


class HintLockedError(CtfError):
    """The requested hint level was skipped without an explicit force flag."""


class CtfService:
    """CTF & practical lab mentor: session persistence, chat, hints, completion."""

    def __init__(self, ai_service_: AIService = ai_service) -> None:
        self._ai_service = ai_service_

    def ensure_indexes(self, db: Database) -> None:
        """Create required indexes. Idempotent — safe to call on every startup."""
        collection = db[Collections.CTF_SESSIONS]
        collection.create_index("user_id")
        collection.create_index("created_at")
        collection.create_index("status")

    # --- Session lifecycle ---------------------------------------------------

    def create_session(self, db: Database, *, user_id: str, payload) -> dict:
        now = datetime.now(timezone.utc)
        document = {
            "user_id": ObjectId(user_id),
            "platform": payload.platform,
            "category": payload.category,
            "difficulty": payload.difficulty,
            "title": payload.title,
            "description": payload.description,
            "user_notes": payload.user_notes or "",
            "status": "in_progress",
            "messages": [],
            "hint_history": [],
            "hints_used": 0,
            "flag": None,
            "created_at": now,
            "updated_at": now,
            "completed_at": None,
        }
        result = db[Collections.CTF_SESSIONS].insert_one(document)
        return {"session_id": str(result.inserted_id), "status": "in_progress"}

    def _get_owned_session(
        self, db: Database, *, session_id: str, user_id: str
    ) -> CtfSessionDocument:
        try:
            object_id = ObjectId(session_id)
        except (InvalidId, TypeError) as exc:
            raise SessionNotFoundError(session_id) from exc

        session = db[Collections.CTF_SESSIONS].find_one({"_id": object_id})
        if session is None:
            raise SessionNotFoundError(session_id)
        if str(session["user_id"]) != user_id:
            raise SessionForbiddenError(session_id)
        return session

    @staticmethod
    def _to_summary(session: CtfSessionDocument) -> dict:
        return {
            "session_id": str(session["_id"]),
            "platform": session["platform"],
            "category": session["category"],
            "difficulty": session["difficulty"],
            "title": session["title"],
            "status": session["status"],
            "hints_used": session.get("hints_used", 0),
            "created_at": session["created_at"].isoformat(),
            "updated_at": session["updated_at"].isoformat(),
            "completed_at": session["completed_at"].isoformat() if session.get("completed_at") else None,
        }

    def get_session(self, db: Database, *, user_id: str, session_id: str) -> dict:
        session = self._get_owned_session(db, session_id=session_id, user_id=user_id)
        summary = self._to_summary(session)
        return {
            **summary,
            "description": session["description"],
            "user_notes": session.get("user_notes", ""),
            "messages": [
                {
                    "role": m["role"],
                    "content": m["content"],
                    "created_at": m["created_at"].isoformat(),
                }
                for m in session.get("messages", [])
            ],
            "hints": [
                {
                    "level": h["level"],
                    "content": h["content"],
                    "requested_at": h["requested_at"].isoformat(),
                }
                for h in session.get("hint_history", [])
            ],
        }

    def list_sessions(self, db: Database, *, user_id: str, page: int, limit: int) -> dict:
        query = {"user_id": ObjectId(user_id)}
        collection = db[Collections.CTF_SESSIONS]
        total = collection.count_documents(query)
        cursor = (
            collection.find(query)
            .sort("created_at", DESCENDING)
            .skip((page - 1) * limit)
            .limit(limit)
        )
        sessions = [self._to_summary(doc) for doc in cursor]
        return {"sessions": sessions, "page": page, "limit": limit, "total": total}

    # --- Chat ------------------------------------------------------------

    def _context_prompt(self, session: CtfSessionDocument) -> str:
        return build_ctf_challenge_context(
            platform=session["platform"],
            category=session["category"],
            difficulty=session["difficulty"],
            title=session["title"],
            description=session["description"],
            user_notes=session.get("user_notes", ""),
        )

    async def chat(self, db: Database, *, user_id: str, session_id: str, message: str) -> str:
        session = self._get_owned_session(db, session_id=session_id, user_id=user_id)

        history = [
            ConversationTurn(role=m["role"], content=m["content"])
            for m in session.get("messages", [])[-CONTEXT_WINDOW:]
        ]

        system_prompt = build_ctf_system_prompt(challenge_context=self._context_prompt(session))
        result = await self._ai_service.generate_response(
            user_message=message, history=history, system_prompt=system_prompt
        )

        now = datetime.now(timezone.utc)
        db[Collections.CTF_SESSIONS].update_one(
            {"_id": session["_id"]},
            {
                "$push": {
                    "messages": {
                        "$each": [
                            {"role": "user", "content": message, "created_at": now},
                            {"role": "assistant", "content": result.text, "created_at": now},
                        ]
                    }
                },
                "$set": {"updated_at": now},
            },
        )
        return result.text

    # --- Hints -------------------------------------------------------------

    async def get_hint(
        self, db: Database, *, user_id: str, session_id: str, level: str, force: bool = False
    ) -> dict:
        session = self._get_owned_session(db, session_id=session_id, user_id=user_id)

        existing = next(
            (h for h in session.get("hint_history", []) if h["level"] == level), None
        )
        if existing is not None:
            # Persisted already — never regenerate a different answer for
            # the same level.
            return {
                "level": level,
                "content": existing["content"],
                "hints_used": session.get("hints_used", 0),
            }

        if level in _HINT_ORDER and not force:
            required_index = _HINT_ORDER.index(level)
            obtained_levels = {h["level"] for h in session.get("hint_history", [])}
            for earlier_level in _HINT_ORDER[:required_index]:
                if earlier_level not in obtained_levels:
                    raise HintLockedError(level)

        system_prompt = build_ctf_system_prompt(
            challenge_context=self._context_prompt(session), hint_level=level
        )
        prompt_message = (
            "Provide the full solution now."
            if level == "solution"
            else f"Provide {level.replace('_', ' ')} for this challenge."
        )
        result = await self._ai_service.generate_response(
            user_message=prompt_message, system_prompt=system_prompt
        )

        now = datetime.now(timezone.utc)
        hint_entry = {"level": level, "content": result.text, "requested_at": now}
        db[Collections.CTF_SESSIONS].update_one(
            {"_id": session["_id"]},
            {
                "$push": {"hint_history": hint_entry},
                "$inc": {"hints_used": 1},
                "$set": {"updated_at": now},
            },
        )

        return {
            "level": level,
            "content": result.text,
            "hints_used": session.get("hints_used", 0) + 1,
        }

    # --- Completion ----------------------------------------------------------

    def complete_session(
        self, db: Database, *, user_id: str, session_id: str, flag: str | None
    ) -> dict:
        session = self._get_owned_session(db, session_id=session_id, user_id=user_id)

        if session["status"] == "completed":
            # Idempotent — completing again just confirms the existing state.
            return {"status": "completed"}

        now = datetime.now(timezone.utc)
        update: dict = {"status": "completed", "completed_at": now, "updated_at": now}
        if flag:
            update["flag"] = flag

        db[Collections.CTF_SESSIONS].update_one({"_id": session["_id"]}, {"$set": update})
        return {"status": "completed"}


# Module-level singleton, matching the project's existing pattern.
ctf_service = CtfService()
