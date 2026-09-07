"""
Practice service.

Orchestrates the cybersecurity practice flow on top of the existing,
provider-agnostic `AIService` (never a second Gemini client): generating
questions, scoring/evaluating answers, and persisting sessions to
`practice_sessions`. AI-generated JSON is always validated before it's
trusted or returned to a client.

    cybersecurity.py (route) -> PracticeService -> AIService -> GeminiClient -> Gemini
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from pydantic import BaseModel, Field, ValidationError
from pymongo import ASCENDING, DESCENDING
from pymongo.database import Database

from app.db.collections import Collections
from app.models.cybersecurity import PracticeSessionDocument
from app.services.ai.ai_service import AIService, AIServiceError, ai_service
from app.services.ai.prompts import (
    ANSWER_EVALUATION_SYSTEM_PROMPT,
    QUESTION_GENERATION_SYSTEM_PROMPT,
    build_answer_evaluation_prompt,
    build_question_generation_prompt,
)
from app.services.cybersecurity.learning_service import LearningService, learning_service
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Score thresholds used to classify a session/category as weak, developing,
# or strong. Kept as simple module constants rather than a config system.
WEAK_THRESHOLD = 60
STRONG_THRESHOLD = 80

MAX_GENERATION_ATTEMPTS = 2
DEFAULT_QUESTION_TYPES = ["multiple_choice", "short_answer"]


# --- Errors ------------------------------------------------------------------


class PracticeError(Exception):
    """Base class for all practice-service-level errors."""


class TopicNotFoundError(PracticeError):
    pass


class PracticeGenerationError(PracticeError):
    """Gemini failed, or never returned validatable question data."""


class SessionNotFoundError(PracticeError):
    pass


class SessionForbiddenError(PracticeError):
    """The session exists but doesn't belong to the requesting user."""


class QuestionNotFoundError(PracticeError):
    pass


class AnswerEvaluationError(PracticeError):
    """Gemini failed, or never returned validatable evaluation data."""


# --- Internal schemas for validating AI-generated JSON ------------------------
# These are intentionally private to this module — they validate untrusted
# model output, they are not part of the public API contract.


class _GeneratedQuestion(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    type: str
    options: list[str] | None = None
    correct_answer: str | None = None
    ideal_answer: str | None = None
    explanation: str = Field(min_length=1, max_length=2000)


class _GeneratedEvaluation(BaseModel):
    score: int = Field(ge=0, le=100)
    correct: bool
    feedback: str = Field(min_length=1, max_length=2000)
    missing_points: list[str] = Field(default_factory=list)


def _parse_json_object(text: str) -> dict:
    """
    Parse a JSON object out of a model response, defensively stripping
    markdown code fences if the model added them despite instructions not to.
    """
    cleaned = text.strip()
    fence_match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", cleaned, re.DOTALL)
    if fence_match:
        cleaned = fence_match.group(1).strip()

    parsed = json.loads(cleaned)  # raises ValueError (json.JSONDecodeError) on bad input
    if not isinstance(parsed, dict):
        raise ValueError("Expected a JSON object")
    return parsed


def _validate_generated_question(data: dict, *, expected_type: str) -> _GeneratedQuestion:
    validated = _GeneratedQuestion.model_validate(data)

    if validated.type != expected_type:
        raise ValueError(f"Expected question type {expected_type!r}, got {validated.type!r}")

    if validated.type == "multiple_choice":
        options = validated.options or []
        cleaned_options = [opt.strip() for opt in options if opt and opt.strip()]
        if len(set(cleaned_options)) < 2:
            raise ValueError("Multiple-choice question needs at least 2 distinct options")
        if not validated.correct_answer or validated.correct_answer.strip() not in cleaned_options:
            raise ValueError("correct_answer must exactly match one of the options")
    elif validated.type == "short_answer":
        if not validated.ideal_answer or not validated.ideal_answer.strip():
            raise ValueError("short_answer question needs a non-empty ideal_answer")
    else:
        raise ValueError(f"Unsupported question type: {validated.type!r}")

    return validated


@dataclass(frozen=True)
class PracticeQuestion:
    """Internal representation of one generated question, including the answer key."""

    question_id: str
    question: str
    type: str
    options: list[str] | None
    correct_answer: str | None
    ideal_answer: str | None
    explanation: str

    def to_public_dict(self) -> dict:
        """Client-safe representation — never the answer key."""
        return {
            "question_id": self.question_id,
            "question": self.question,
            "type": self.type,
            "options": self.options,
        }


@dataclass(frozen=True)
class AnswerResult:
    score: int
    correct: bool
    feedback: str
    ideal_answer: str | None
    missing_points: list[str] = field(default_factory=list)


class PracticeService:
    """Cybersecurity practice orchestration: generation, scoring, persistence."""

    def __init__(
        self,
        ai_service_: AIService = ai_service,
        learning_service_: LearningService = learning_service,
    ) -> None:
        self._ai_service = ai_service_
        self._learning_service = learning_service_

    def ensure_indexes(self, db: Database) -> None:
        """Create required indexes. Idempotent — safe to call on every startup."""
        collection = db[Collections.PRACTICE_SESSIONS]
        collection.create_index("user_id")
        collection.create_index("started_at")
        collection.create_index("topic_slug")

    # --- Question generation -------------------------------------------------

    async def _generate_one_question(
        self, *, topic_title: str, topic_description: str, learning_objectives: list[str],
        difficulty: str, question_type: str,
    ) -> PracticeQuestion:
        prompt = build_question_generation_prompt(
            topic_title=topic_title,
            topic_description=topic_description,
            learning_objectives=learning_objectives,
            difficulty=difficulty,
            question_type=question_type,
        )

        last_error: Exception | None = None
        for attempt in range(1, MAX_GENERATION_ATTEMPTS + 1):
            try:
                result = await self._ai_service.generate_response(
                    user_message=prompt, system_prompt=QUESTION_GENERATION_SYSTEM_PROMPT
                )
                data = _parse_json_object(result.text)
                validated = _validate_generated_question(data, expected_type=question_type)
                return PracticeQuestion(
                    question_id=uuid.uuid4().hex,
                    question=validated.question.strip(),
                    type=validated.type,
                    options=(
                        [opt.strip() for opt in validated.options if opt and opt.strip()]
                        if validated.options
                        else None
                    ),
                    correct_answer=(validated.correct_answer or "").strip() or None,
                    ideal_answer=(validated.ideal_answer or "").strip() or None,
                    explanation=validated.explanation.strip(),
                )
            except AIServiceError as exc:
                # Provider-level failure (config/timeout/provider error) —
                # not worth retrying, the same call will likely fail again.
                logger.error("Question generation failed: %s", type(exc).__name__)
                raise PracticeGenerationError("AI provider failed to generate a question.") from exc
            except (ValueError, ValidationError) as exc:
                last_error = exc
                logger.warning(
                    "Invalid generated question on attempt %d/%d: %s",
                    attempt, MAX_GENERATION_ATTEMPTS, type(exc).__name__,
                )
                continue

        raise PracticeGenerationError("Could not generate a valid question.") from last_error

    async def start_session(
        self,
        db: Database,
        *,
        user_id: str,
        topic_slug: str,
        difficulty: str | None,
        question_count: int,
    ) -> dict:
        topic = self._learning_service.get_topic_by_slug(db, topic_slug)
        if topic is None:
            raise TopicNotFoundError(topic_slug)

        effective_difficulty = difficulty or topic["difficulty"]

        questions: list[PracticeQuestion] = []
        seen_question_text: set[str] = set()
        for i in range(question_count):
            question_type = DEFAULT_QUESTION_TYPES[i % len(DEFAULT_QUESTION_TYPES)]
            # Avoid an exact-duplicate question within the same session; a
            # couple of retries is enough without risking a long stall.
            for _ in range(2):
                question = await self._generate_one_question(
                    topic_title=topic["title"],
                    topic_description=topic["description"],
                    learning_objectives=topic.get("learning_objectives", []),
                    difficulty=effective_difficulty,
                    question_type=question_type,
                )
                normalized = question.question.strip().lower()
                if normalized not in seen_question_text:
                    break
            seen_question_text.add(question.question.strip().lower())
            questions.append(question)

        now = datetime.now(timezone.utc)
        session_doc: dict = {
            "user_id": ObjectId(user_id),
            "topic_slug": topic["slug"],
            "topic_title": topic["title"],
            "category": topic["category"],
            "difficulty": effective_difficulty,
            "started_at": now,
            "completed_at": None,
            "status": "in_progress",
            "questions": [
                {
                    "question_id": q.question_id,
                    "question": q.question,
                    "type": q.type,
                    "options": q.options,
                    "correct_answer": q.correct_answer,
                    "ideal_answer": q.ideal_answer,
                    "explanation": q.explanation,
                }
                for q in questions
            ],
            "answers": {},
            "score": None,
            "questions_answered": None,
            "correct_answers": None,
            "weak_areas": [],
            "recommendations": [],
        }
        result = db[Collections.PRACTICE_SESSIONS].insert_one(session_doc)

        return {
            "session_id": str(result.inserted_id),
            "topic_slug": topic["slug"],
            "topic_title": topic["title"],
            "difficulty": effective_difficulty,
            "questions": [q.to_public_dict() for q in questions],
        }

    # --- Session ownership -----------------------------------------------------

    def _get_owned_session(
        self, db: Database, *, session_id: str, user_id: str
    ) -> PracticeSessionDocument:
        try:
            object_id = ObjectId(session_id)
        except (InvalidId, TypeError) as exc:
            raise SessionNotFoundError(session_id) from exc

        session = db[Collections.PRACTICE_SESSIONS].find_one({"_id": object_id})
        if session is None:
            raise SessionNotFoundError(session_id)

        if str(session["user_id"]) != user_id:
            raise SessionForbiddenError(session_id)

        return session

    # --- Answer submission -------------------------------------------------

    async def submit_answer(
        self, db: Database, *, user_id: str, session_id: str, question_id: str, answer: str
    ) -> AnswerResult:
        session = self._get_owned_session(db, session_id=session_id, user_id=user_id)

        question = next(
            (q for q in session["questions"] if q["question_id"] == question_id), None
        )
        if question is None:
            raise QuestionNotFoundError(question_id)

        if question["type"] == "multiple_choice":
            correct_answer = (question.get("correct_answer") or "").strip().lower()
            is_correct = answer.strip().lower() == correct_answer
            score = 100 if is_correct else 0
            feedback = (
                "Correct!"
                if is_correct
                else f"Not quite — the correct answer is: {question.get('correct_answer')}"
            )
            missing_points: list[str] = []
        else:
            prompt = build_answer_evaluation_prompt(
                question=question["question"],
                ideal_answer=question.get("ideal_answer") or "",
                user_answer=answer,
            )
            try:
                result = await self._ai_service.generate_response(
                    user_message=prompt, system_prompt=ANSWER_EVALUATION_SYSTEM_PROMPT
                )
                data = _parse_json_object(result.text)
                validated = _GeneratedEvaluation.model_validate(data)
            except AIServiceError as exc:
                logger.error("Answer evaluation failed: %s", type(exc).__name__)
                raise AnswerEvaluationError("AI provider failed to evaluate the answer.") from exc
            except (ValueError, ValidationError) as exc:
                logger.warning("Invalid evaluation data: %s", type(exc).__name__)
                raise AnswerEvaluationError("AI returned an unusable evaluation.") from exc

            score = max(0, min(100, validated.score))
            is_correct = validated.correct
            feedback = validated.feedback.strip()
            missing_points = [p.strip() for p in validated.missing_points if p and p.strip()]

        answer_record = {
            "answer": answer,
            "score": score,
            "correct": is_correct,
            "feedback": feedback,
            "missing_points": missing_points,
            "answered_at": datetime.now(timezone.utc),
        }

        # Keyed by question_id and $set (not $push) — resubmitting an answer
        # overwrites rather than duplicating.
        db[Collections.PRACTICE_SESSIONS].update_one(
            {"_id": session["_id"]}, {"$set": {f"answers.{question_id}": answer_record}}
        )

        return AnswerResult(
            score=score,
            correct=is_correct,
            feedback=feedback,
            ideal_answer=question.get("ideal_answer"),
            missing_points=missing_points,
        )

    # --- Completion ----------------------------------------------------------

    def _build_complete_result(self, session: PracticeSessionDocument) -> dict:
        return {
            "session_id": str(session["_id"]),
            "score": session.get("score") or 0,
            "questions_answered": session.get("questions_answered") or 0,
            "correct_answers": session.get("correct_answers") or 0,
            "topic_title": session["topic_title"],
            "category": session["category"],
            "weak_areas": session.get("weak_areas", []),
            "recommendations": session.get("recommendations", []),
        }

    def complete_session(self, db: Database, *, user_id: str, session_id: str) -> dict:
        session = self._get_owned_session(db, session_id=session_id, user_id=user_id)

        # Idempotent: completing an already-completed session just returns
        # the previously computed result rather than recomputing/erroring.
        if session.get("status") == "completed":
            return self._build_complete_result(session)

        answers: dict = session.get("answers", {})
        questions = session["questions"]
        answered_scores = [
            answers[q["question_id"]]["score"]
            for q in questions
            if q["question_id"] in answers
        ]
        questions_answered = len(answered_scores)
        correct_answers = sum(
            1
            for q in questions
            if q["question_id"] in answers and answers[q["question_id"]]["correct"]
        )
        overall_score = round(sum(answered_scores) / questions_answered) if questions_answered else 0

        weak_areas = [session["category"]] if overall_score < WEAK_THRESHOLD else []
        recommendations = (
            [f"Review {session['topic_title']} and try this practice again."]
            if weak_areas
            else []
        )

        now = datetime.now(timezone.utc)
        db[Collections.PRACTICE_SESSIONS].update_one(
            {"_id": session["_id"]},
            {
                "$set": {
                    "status": "completed",
                    "completed_at": now,
                    "score": overall_score,
                    "questions_answered": questions_answered,
                    "correct_answers": correct_answers,
                    "weak_areas": weak_areas,
                    "recommendations": recommendations,
                }
            },
        )

        session = dict(session)
        session.update(
            {
                "score": overall_score,
                "questions_answered": questions_answered,
                "correct_answers": correct_answers,
                "weak_areas": weak_areas,
                "recommendations": recommendations,
            }
        )
        return self._build_complete_result(session)

    # --- History & progress ----------------------------------------------------

    def get_history(self, db: Database, *, user_id: str, page: int, limit: int) -> dict:
        query = {"user_id": ObjectId(user_id)}
        collection = db[Collections.PRACTICE_SESSIONS]
        total = collection.count_documents(query)

        cursor = (
            collection.find(query)
            .sort("started_at", DESCENDING)
            .skip((page - 1) * limit)
            .limit(limit)
        )

        sessions = [
            {
                "session_id": str(doc["_id"]),
                "topic_slug": doc["topic_slug"],
                "topic_title": doc["topic_title"],
                "category": doc["category"],
                "difficulty": doc["difficulty"],
                "status": doc["status"],
                "score": doc.get("score"),
                "questions_answered": doc.get("questions_answered") or len(doc.get("answers", {})),
                "started_at": doc["started_at"].isoformat(),
                "completed_at": doc["completed_at"].isoformat() if doc.get("completed_at") else None,
            }
            for doc in cursor
        ]

        return {"sessions": sessions, "page": page, "limit": limit, "total": total}

    def get_progress(self, db: Database, *, user_id: str) -> dict:
        """
        Basic per-category progress computed from completed sessions —
        not the full progress dashboard (that's a later step).
        """
        pipeline = [
            {"$match": {"user_id": ObjectId(user_id), "status": "completed"}},
            {
                "$group": {
                    "_id": "$category",
                    "average_score": {"$avg": "$score"},
                    "attempts": {"$sum": 1},
                }
            },
            {"$sort": {"_id": ASCENDING}},
        ]
        rows = list(db[Collections.PRACTICE_SESSIONS].aggregate(pipeline))

        categories = []
        weak_categories = []
        for row in rows:
            average_score = round(row["average_score"] or 0)
            if average_score < WEAK_THRESHOLD:
                status = "weak"
                weak_categories.append(row["_id"])
            elif average_score < STRONG_THRESHOLD:
                status = "developing"
            else:
                status = "strong"

            categories.append(
                {
                    "category": row["_id"],
                    "average_score": average_score,
                    "attempts": row["attempts"],
                    "status": status,
                }
            )

        return {"categories": categories, "weak_categories": weak_categories}


# Module-level singleton, matching the project's existing pattern.
practice_service = PracticeService()
