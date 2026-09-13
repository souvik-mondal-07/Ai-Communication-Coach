"""
Communication service.

Owns the `communication_scenarios` catalog and all `communication_sessions`
reads/writes: session creation, ownership-checked lookups, and roleplay
chat. Built entirely on the existing, provider-agnostic `AIService` — never
a second Gemini client:

    communication.py (route) -> CommunicationService -> AIService -> GeminiClient -> Gemini
"""

from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ASCENDING, DESCENDING
from pymongo.database import Database

from app.db.collections import Collections
from app.models.communication import CommunicationScenarioDocument, CommunicationSessionDocument
from app.services.ai.ai_service import AIService, ConversationTurn, ai_service
from app.services.communication.prompts import build_roleplay_system_prompt
from app.services.communication.seed_data import STARTER_SCENARIOS

# Bounded context sent to the AI per request. All messages are still
# persisted in full; only what's *sent to Gemini* is capped.
CONTEXT_WINDOW = 20

SCENARIO_SUMMARY_PROJECTION = {
    "_id": 1,
    "title": 1,
    "slug": 1,
    "category": 1,
    "mode": 1,
    "difficulty": 1,
    "description": 1,
    "objective": 1,
    "skills_targeted": 1,
}


class CommunicationError(Exception):
    """Base class for all communication-service-level errors."""


class ScenarioNotFoundError(CommunicationError):
    pass


class SessionNotFoundError(CommunicationError):
    pass


class SessionForbiddenError(CommunicationError):
    """The session exists but doesn't belong to the requesting user."""


class SessionCompletedError(CommunicationError):
    """The session has already been completed and can't accept new messages."""


def _scenario_to_dict(scenario: CommunicationScenarioDocument) -> dict:
    return {
        "scenario_id": str(scenario["_id"]),
        "title": scenario["title"],
        "slug": scenario["slug"],
        "category": scenario["category"],
        "mode": scenario["mode"],
        "difficulty": scenario["difficulty"],
        "description": scenario["description"],
        "objective": scenario["objective"],
        "context": scenario["context"],
        "ai_role": scenario["ai_role"],
        "user_role": scenario["user_role"],
        "opening_message": scenario["opening_message"],
        "skills_targeted": scenario.get("skills_targeted", []),
        "tips": scenario.get("tips", []),
    }


class CommunicationService:
    """Communication coach: scenario catalog, sessions, ownership, roleplay chat."""

    def __init__(self, ai_service_: AIService = ai_service) -> None:
        self._ai_service = ai_service_

    def ensure_indexes(self, db: Database) -> None:
        """Create required indexes. Idempotent — safe to call on every startup."""
        scenarios = db[Collections.COMMUNICATION_SCENARIOS]
        scenarios.create_index("slug", unique=True)
        scenarios.create_index("category")
        scenarios.create_index("mode")
        scenarios.create_index("difficulty")

        sessions = db[Collections.COMMUNICATION_SESSIONS]
        sessions.create_index("user_id")
        sessions.create_index("scenario_id")
        sessions.create_index("started_at")
        sessions.create_index("status")

    def ensure_seeded(self, db: Database) -> None:
        """Upsert the starter scenario dataset by slug. Safe to call every startup."""
        collection = db[Collections.COMMUNICATION_SCENARIOS]
        now = datetime.now(timezone.utc)
        for scenario in STARTER_SCENARIOS:
            document = {**scenario, "created_at": now, "updated_at": now}
            collection.update_one(
                {"slug": scenario["slug"]}, {"$setOnInsert": document}, upsert=True
            )

    # --- Scenarios -------------------------------------------------------

    def list_scenarios(
        self,
        db: Database,
        *,
        category: str | None = None,
        mode: str | None = None,
        difficulty: str | None = None,
    ) -> list[dict]:
        query: dict = {}
        if category:
            query["category"] = category
        if mode:
            query["mode"] = mode
        if difficulty:
            query["difficulty"] = difficulty

        cursor = (
            db[Collections.COMMUNICATION_SCENARIOS]
            .find(query, SCENARIO_SUMMARY_PROJECTION)
            .sort([("category", ASCENDING), ("title", ASCENDING)])
        )
        return [
            {
                "scenario_id": str(doc["_id"]),
                "title": doc["title"],
                "slug": doc["slug"],
                "category": doc["category"],
                "mode": doc["mode"],
                "difficulty": doc["difficulty"],
                "description": doc["description"],
                "objective": doc["objective"],
                "skills_targeted": doc.get("skills_targeted", []),
            }
            for doc in cursor
        ]

    def get_scenario_by_slug(self, db: Database, slug: str) -> dict | None:
        doc = db[Collections.COMMUNICATION_SCENARIOS].find_one({"slug": slug})
        return _scenario_to_dict(doc) if doc else None

    def _get_scenario_by_id(
        self, db: Database, scenario_id: str
    ) -> CommunicationScenarioDocument:
        try:
            object_id = ObjectId(scenario_id)
        except (InvalidId, TypeError) as exc:
            raise ScenarioNotFoundError(scenario_id) from exc

        doc = db[Collections.COMMUNICATION_SCENARIOS].find_one({"_id": object_id})
        if doc is None:
            raise ScenarioNotFoundError(scenario_id)
        return doc

    # --- Sessions --------------------------------------------------------

    def start_session(
        self, db: Database, *, user_id: str, scenario_id: str, difficulty: str | None
    ) -> dict:
        scenario = self._get_scenario_by_id(db, scenario_id)
        effective_difficulty = difficulty or scenario["difficulty"]

        now = datetime.now(timezone.utc)
        document = {
            "user_id": ObjectId(user_id),
            "scenario_id": scenario["_id"],
            "scenario_title": scenario["title"],
            "category": scenario["category"],
            "mode": scenario["mode"],
            "difficulty": effective_difficulty,
            "ai_role": scenario["ai_role"],
            "user_role": scenario["user_role"],
            "objective": scenario["objective"],
            "status": "in_progress",
            "messages": [
                {
                    "role": "assistant",
                    "content": scenario["opening_message"],
                    "timestamp": now,
                }
            ],
            "evaluation": None,
            "started_at": now,
            "updated_at": now,
            "completed_at": None,
        }
        result = db[Collections.COMMUNICATION_SESSIONS].insert_one(document)

        return {
            "session_id": str(result.inserted_id),
            "scenario": _scenario_to_dict(scenario),
            "status": "in_progress",
        }

    def _get_owned_session(
        self, db: Database, *, session_id: str, user_id: str
    ) -> CommunicationSessionDocument:
        try:
            object_id = ObjectId(session_id)
        except (InvalidId, TypeError) as exc:
            raise SessionNotFoundError(session_id) from exc

        session = db[Collections.COMMUNICATION_SESSIONS].find_one({"_id": object_id})
        if session is None:
            raise SessionNotFoundError(session_id)
        if str(session["user_id"]) != user_id:
            raise SessionForbiddenError(session_id)
        return session

    def get_owned_session_for_completion(
        self, *, db: Database, session_id: str, user_id: str
    ) -> CommunicationSessionDocument:
        """Public wrapper so routes (e.g. the complete-session endpoint) can
        fetch an ownership-checked session without reaching into a private method."""
        return self._get_owned_session(db, session_id=session_id, user_id=user_id)

    @staticmethod
    def _to_summary(session: CommunicationSessionDocument) -> dict:
        evaluation = session.get("evaluation")
        return {
            "session_id": str(session["_id"]),
            "scenario_title": session["scenario_title"],
            "category": session["category"],
            "mode": session["mode"],
            "difficulty": session["difficulty"],
            "status": session["status"],
            "overall_score": evaluation["overall_score"] if evaluation else None,
            "started_at": session["started_at"].isoformat(),
            "completed_at": session["completed_at"].isoformat() if session.get("completed_at") else None,
        }

    def get_session(self, db: Database, *, user_id: str, session_id: str) -> dict:
        session = self._get_owned_session(db, session_id=session_id, user_id=user_id)
        summary = self._to_summary(session)
        return {
            **summary,
            "ai_role": session.get("ai_role", ""),
            "user_role": session.get("user_role", ""),
            "objective": session.get("objective", ""),
            "messages": [
                {
                    "role": m["role"],
                    "content": m["content"],
                    "timestamp": m["timestamp"].isoformat(),
                }
                for m in session.get("messages", [])
            ],
            "evaluation": session.get("evaluation"),
        }

    def list_sessions(self, db: Database, *, user_id: str, page: int, limit: int) -> dict:
        query = {"user_id": ObjectId(user_id)}
        collection = db[Collections.COMMUNICATION_SESSIONS]
        total = collection.count_documents(query)
        cursor = (
            collection.find(query)
            .sort("started_at", DESCENDING)
            .skip((page - 1) * limit)
            .limit(limit)
        )
        sessions = [self._to_summary(doc) for doc in cursor]
        return {"sessions": sessions, "page": page, "limit": limit, "total": total}

    # --- Roleplay chat -----------------------------------------------------

    async def send_message(
        self, db: Database, *, user_id: str, session_id: str, message: str
    ) -> dict:
        session = self._get_owned_session(db, session_id=session_id, user_id=user_id)

        if session["status"] == "completed":
            raise SessionCompletedError(session_id)

        history = [
            ConversationTurn(role=m["role"], content=m["content"])
            for m in session.get("messages", [])[-CONTEXT_WINDOW:]
        ]

        scenario = self._get_scenario_by_id(db, str(session["scenario_id"]))
        system_prompt = build_roleplay_system_prompt(
            mode=session["mode"],
            difficulty=session["difficulty"],
            ai_role=scenario["ai_role"],
            user_role=scenario["user_role"],
            context=scenario["context"],
            objective=scenario["objective"],
        )

        result = await self._ai_service.generate_response(
            user_message=message, history=history, system_prompt=system_prompt
        )

        now = datetime.now(timezone.utc)
        db[Collections.COMMUNICATION_SESSIONS].update_one(
            {"_id": session["_id"]},
            {
                "$push": {
                    "messages": {
                        "$each": [
                            {"role": "user", "content": message, "timestamp": now},
                            {"role": "assistant", "content": result.text, "timestamp": now},
                        ]
                    }
                },
                "$set": {"updated_at": now},
            },
        )

        # The assistant message is the last one pushed — its "index" (as a
        # simple, stable identifier) is len(existing messages) + 1.
        message_id = str(len(session.get("messages", [])) + 1)

        return {"reply": result.text, "session_id": session_id, "message_id": message_id}


# Module-level singleton, matching the project's existing pattern.
communication_service = CommunicationService()
