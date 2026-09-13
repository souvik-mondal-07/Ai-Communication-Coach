"""
Evaluation service.

Handles completing a communication session: builds a transcript, asks the
existing `AIService` to grade it, validates the returned JSON before
trusting any of it, persists the result, and marks the session completed.
Kept separate from `communication_service` (which owns the live roleplay
chat) so evaluation logic — prompt, parsing, validation — has one place to
live, per Step 7's requested structure.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from pydantic import BaseModel, Field, ValidationError
from pymongo.database import Database

from app.db.collections import Collections
from app.models.communication import CommunicationSessionDocument
from app.services.ai.ai_service import AIService, AIServiceError, ai_service
from app.services.communication.prompts import (
    COMMUNICATION_EVALUATION_PROMPT,
    build_evaluation_user_prompt,
)


class EvaluationError(Exception):
    """Gemini failed, or never returned validatable evaluation data."""


class _BetterResponse(BaseModel):
    original: str = Field(min_length=1, max_length=2000)
    improved: str = Field(min_length=1, max_length=2000)
    why: str = Field(default="", max_length=1000)


class _GeneratedEvaluation(BaseModel):
    """
    Internal-only schema validating the AI's raw evaluation JSON before
    it's trusted or persisted. Not part of the public API contract — see
    `app.schemas.communication.EvaluationOut` for that.
    """

    overall_score: int = Field(ge=0, le=100)
    clarity_score: int = Field(ge=0, le=100)
    grammar_score: int = Field(ge=0, le=100)
    vocabulary_score: int = Field(ge=0, le=100)
    professionalism_score: int = Field(ge=0, le=100)
    confidence_score: int = Field(ge=0, le=100)
    relevance_score: int = Field(ge=0, le=100)
    conversation_flow_score: int = Field(ge=0, le=100)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    better_responses: list[_BetterResponse] = Field(default_factory=list)
    summary: str = Field(min_length=1, max_length=2000)


def _parse_json_object(text: str) -> dict:
    """Parse a JSON object out of a model response, stripping markdown fences if present."""
    cleaned = text.strip()
    fence_match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", cleaned, re.DOTALL)
    if fence_match:
        cleaned = fence_match.group(1).strip()

    parsed = json.loads(cleaned)  # raises ValueError (json.JSONDecodeError) on bad input
    if not isinstance(parsed, dict):
        raise ValueError("Expected a JSON object")
    return parsed


def _build_transcript(session: CommunicationSessionDocument) -> str:
    lines = []
    for message in session.get("messages", []):
        speaker = "Learner" if message["role"] == "user" else "AI character"
        lines.append(f"{speaker}: {message['content']}")
    return "\n".join(lines)


class EvaluationService:
    """Evaluates a completed communication session using the existing AIService."""

    def __init__(self, ai_service_: AIService = ai_service) -> None:
        self._ai_service = ai_service_

    async def evaluate_session(self, db: Database, *, session: CommunicationSessionDocument) -> dict:
        """
        Generate, validate, and persist an evaluation for `session`, and
        mark it completed. Raises `EvaluationError` if the AI provider
        fails or never returns valid, schema-conformant JSON.
        """
        transcript = _build_transcript(session)
        user_prompt = build_evaluation_user_prompt(
            scenario_title=session["scenario_title"],
            ai_role="the AI character",
            user_role="the learner",
            objective="realistic conversation practice",
            transcript=transcript,
        )

        try:
            result = await self._ai_service.generate_response(
                user_message=user_prompt, system_prompt=COMMUNICATION_EVALUATION_PROMPT
            )
            data = _parse_json_object(result.text)
            validated = _GeneratedEvaluation.model_validate(data)
        except AIServiceError as exc:
            raise EvaluationError("AI provider failed to evaluate the conversation.") from exc
        except (ValueError, ValidationError) as exc:
            raise EvaluationError("AI returned an unusable evaluation.") from exc

        evaluation = validated.model_dump()

        now = datetime.now(timezone.utc)
        db[Collections.COMMUNICATION_SESSIONS].update_one(
            {"_id": session["_id"]},
            {
                "$set": {
                    "status": "completed",
                    "completed_at": now,
                    "updated_at": now,
                    "evaluation": evaluation,
                }
            },
        )

        return evaluation


# Module-level singleton, matching the project's existing pattern.
evaluation_service = EvaluationService()
