"""
Pressure & Nervousness Training session orchestration.

Owns the `pressure_sessions` collection and the training loop:

    start -> ask (with a pressure condition) -> answer -> evaluate
           -> [interruption | rapid follow-up | next question] -> ...
           -> final evaluation

    pressure route -> PressureService -+-> PressureEngine (conditions/timing)
                                        +-> existing QuestionService ---------+
                                        +-> existing InterviewEvaluationService +-> existing AIService -> Gemini
                                        +-> Step 8 analysis (voice AND text)
                                        +-> PressureEvaluationService (final report)

This module does NOT create a second Gemini client, a second question bank,
or a second interview engine -- question wording, follow-up generation and
answer scoring all go through the exact same Step 9 services used by the
interview simulator. The only new logic here is *which* pressure condition
to apply next (time limit, topic switch, harder question, interruption) --
see `pressure_engine.py` -- and turning those into a session document.

Design notes mirror `interview_service.py`:

* All AI work for a response happens before anything is saved.
* Writes are guarded by a `version` counter against double-submits.
* Technical/communication evaluations are hidden while a session is active
  (a real interviewer doesn't grade you mid-interview); pressure indicators
  (speaking rate, filler words, response time) are always shown, since they
  are process observations, not judgments.
"""

from __future__ import annotations

import random
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import DESCENDING
from pymongo.database import Database

from app.db.collections import Collections
from app.services.ai.ai_service import AIService, ai_service
from app.services.communication.analysis_service import analyze_transcript
from app.services.interview.evaluation_service import InterviewEvaluationService, question_scores
from app.services.interview.question_service import (
    QuestionGenerationError,
    QuestionService,
    plan_questions,
)
from app.services.interview.topics import topic_label
from app.services.pressure import pressure_engine
from app.services.pressure.evaluation_service import PressureEvaluationService
from app.services.pressure.pressure_config import get_pressure_config
from app.utils.logger import get_logger

logger = get_logger(__name__)

SELF_REPORT_LABELS = ("easy", "manageable", "challenging", "very_difficult")


# --- Errors ------------------------------------------------------------------


class PressureError(Exception):
    """Base class for pressure-service-level errors."""


class SessionNotFoundError(PressureError):
    pass


class SessionForbiddenError(PressureError):
    """The session exists but belongs to another user."""


class SessionNotActiveError(PressureError):
    """The session is completed/abandoned and can't accept responses."""


class AnswerConflictError(PressureError):
    """The session changed while the response was being processed (e.g. double submit)."""


# --- Helpers -------------------------------------------------------------------


def _pending(session: dict) -> tuple[int, int | None] | None:
    """(question index, follow-up index or None) of the prompt awaiting a response."""
    for qi, question in enumerate(session["questions"]):
        if question.get("answer") is None:
            return qi, None
        for fi, follow_up in enumerate(question.get("follow_up_questions", [])):
            if follow_up.get("answer") is None:
                return qi, fi
    return None


def _blank_record(input_type: str = "text") -> dict:
    return {
        "answer": None,
        "answer_input_type": input_type,
        "answered_at": None,
        "response_duration_seconds": None,
        "timed_out": False,
        "voice_analysis": None,
        "text_metrics": None,
        "technical_evaluation": None,
        "communication_evaluation": None,
        "improved_answer": None,
        "internal": {},
    }


def _new_question(
    number: int, text: str, *, topic: str, focus: str, condition: dict, now: datetime
) -> dict:
    return {
        "question_number": number,
        "question": text,
        "topic": topic,
        "focus": focus,
        "condition": condition,
        "asked_at": now,
        "follow_up_questions": [],
        **_blank_record(),
    }


def _new_follow_up(text: str, *, kind: str, now: datetime) -> dict:
    return {"question": text, "kind": kind, "asked_at": now, **_blank_record()}


def _public_record(record: dict, *, hide_evaluation: bool) -> dict:
    return {
        "answer": record.get("answer"),
        "answer_input_type": record.get("answer_input_type", "text"),
        "response_duration_seconds": record.get("response_duration_seconds"),
        "timed_out": record.get("timed_out", False),
        "pressure_indicators": record.get("voice_analysis") or record.get("text_metrics"),
        "technical_evaluation": None if hide_evaluation else record.get("technical_evaluation"),
        "communication_evaluation": None if hide_evaluation else record.get("communication_evaluation"),
        "improved_answer": None if hide_evaluation else record.get("improved_answer"),
    }


def _public_session(session: dict) -> dict:
    active = session["status"] == "in_progress"
    hide = active  # a pressure interviewer doesn't reveal scores mid-session

    questions = []
    for q in session["questions"]:
        tech, comm = question_scores(q)
        questions.append(
            {
                "question_number": q["question_number"],
                "question": q["question"],
                "topic": q["topic"],
                "topic_label": topic_label(q["topic"]),
                "condition": q.get("condition"),
                **_public_record(q, hide_evaluation=hide),
                "technical_score": None if hide else tech,
                "communication_score": None if hide else comm,
                "follow_up_questions": [
                    {"question": fu["question"], "kind": fu.get("kind", "technical"), **_public_record(fu, hide_evaluation=hide)}
                    for fu in q.get("follow_up_questions", [])
                ],
            }
        )

    pending = _pending(session) if active else None
    current_prompt = None
    if pending is not None:
        qi, fi = pending
        q = session["questions"][qi]
        follow_up = q["follow_up_questions"][fi] if fi is not None else None
        current_prompt = {
            "question_number": q["question_number"],
            "question": q["question"] if follow_up is None else follow_up["question"],
            "topic": q["topic"],
            "topic_label": topic_label(q["topic"]),
            "is_follow_up": fi is not None,
            "follow_up_kind": follow_up.get("kind") if follow_up else None,
            "time_limit_seconds": (q.get("condition") or {}).get("time_limit_seconds"),
        }

    answered = sum(1 for q in session["questions"] if q.get("answer") is not None)
    return {
        "session_id": str(session["_id"]),
        "pressure_level": session["pressure_level"],
        "mode": session["mode"],
        "interview_type": session["interview_type"],
        "difficulty": session["difficulty"],
        "input_mode": session["input_mode"],
        "question_count": session["question_count"],
        "current_question_number": session["current_question_number"],
        "answered_count": answered,
        "status": session["status"],
        "started_at": session["started_at"].isoformat(),
        "completed_at": session["completed_at"].isoformat() if session.get("completed_at") else None,
        "current_prompt": current_prompt,
        "questions": questions,
        "self_reported_difficulty": session.get("self_reported_difficulty"),
        "self_report_note": session.get("self_report_note"),
        "final_evaluation": session.get("final_evaluation"),
    }


def _summary(session: dict) -> dict:
    final = session.get("final_evaluation") or {}
    return {
        "session_id": str(session["_id"]),
        "pressure_level": session["pressure_level"],
        "mode": session["mode"],
        "difficulty": session["difficulty"],
        "question_count": session["question_count"],
        "answered_count": sum(1 for q in session["questions"] if q.get("answer") is not None),
        "status": session["status"],
        "overall_score": final.get("overall_score"),
        "pressure_handling_score": final.get("pressure_handling_score"),
        "self_reported_difficulty": session.get("self_reported_difficulty"),
        "started_at": session["started_at"].isoformat(),
        "completed_at": session["completed_at"].isoformat() if session.get("completed_at") else None,
    }


class PressureService:
    """Pressure & nervousness training: sessions, ownership, and the ask/answer loop."""

    def __init__(
        self,
        ai_service_: AIService = ai_service,
        question_service_: QuestionService | None = None,
        interview_evaluation_service_: InterviewEvaluationService | None = None,
        pressure_evaluation_service_: PressureEvaluationService | None = None,
    ) -> None:
        # All AI calls go through the one existing AIService -- no second Gemini client.
        self._questions = question_service_ or QuestionService(ai_service_)
        self._interview_eval = interview_evaluation_service_ or InterviewEvaluationService(ai_service_)
        self._pressure_eval = pressure_evaluation_service_ or PressureEvaluationService(self._interview_eval)

    def ensure_indexes(self, db: Database) -> None:
        """Create required indexes. Idempotent -- safe to call on every startup."""
        sessions = db[Collections.PRESSURE_SESSIONS]
        sessions.create_index("user_id")
        sessions.create_index("started_at")
        sessions.create_index("status")
        sessions.create_index("pressure_level")
        sessions.create_index([("user_id", 1), ("started_at", -1)])

    # --- Sessions -----------------------------------------------------------------

    async def start_session(
        self,
        db: Database,
        *,
        user_id: str,
        pressure_level: int,
        mode: str,
        interview_type: str,
        difficulty: str,
        question_count: int,
        input_mode: str,
        rng: random.Random | None = None,
    ) -> dict:
        config = get_pressure_config(pressure_level)
        rng = rng or random.Random()
        plan = plan_questions(interview_type, question_count, rng)

        first_plan = pressure_engine.plan_next_question(
            config=config,
            interview_type=interview_type,
            difficulty=difficulty,
            planned_topic=plan[0]["topic"],
            planned_focus=plan[0]["focus"],
            rng=rng,
        )

        # Generate the first question *before* inserting, so an AI failure
        # never leaves an empty session behind.
        first_question = await self._questions.generate_question(
            interview_type=interview_type,
            difficulty=first_plan.difficulty,
            mode=input_mode,
            question_number=1,
            total_questions=question_count,
            topic=first_plan.topic,
            focus=first_plan.focus,
            previous_questions=[],
            recent_answers=[],
            technical_scores=[],
        )

        now = datetime.now(timezone.utc)
        condition = {
            "type": first_plan.condition_type,
            "time_limit_seconds": first_plan.time_limit_seconds,
            "topic_switched": first_plan.topic_switched,
            "difficulty_bumped": first_plan.difficulty_bumped,
        }
        document = {
            "user_id": ObjectId(user_id),
            "pressure_level": pressure_level,
            "mode": mode,
            "interview_type": interview_type,
            "difficulty": difficulty,
            "input_mode": input_mode,
            "question_count": question_count,
            "current_question_number": 1,
            "status": "in_progress",
            "version": 0,
            "config": config.as_document(),
            "topic_plan": plan,
            "questions": [
                _new_question(1, first_question, topic=first_plan.topic, focus=first_plan.focus, condition=condition, now=now)
            ],
            "self_reported_difficulty": None,
            "self_report_note": None,
            "final_evaluation": None,
            "started_at": now,
            "updated_at": now,
            "completed_at": None,
            "abandoned_at": None,
        }
        result = db[Collections.PRESSURE_SESSIONS].insert_one(document)
        document["_id"] = result.inserted_id
        public = _public_session(document)
        return {
            "session_id": public["session_id"],
            "pressure_level": pressure_level,
            "question_number": 1,
            "question": first_question,
            "topic_label": topic_label(first_plan.topic),
            "time_limit_seconds": first_plan.time_limit_seconds,
            "status": "in_progress",
            "session": public,
        }

    def _get_owned_session(self, db: Database, *, session_id: str, user_id: str) -> dict:
        try:
            object_id = ObjectId(session_id)
        except (InvalidId, TypeError) as exc:
            raise SessionNotFoundError(session_id) from exc
        session = db[Collections.PRESSURE_SESSIONS].find_one({"_id": object_id})
        if session is None:
            raise SessionNotFoundError(session_id)
        if str(session["user_id"]) != user_id:
            raise SessionForbiddenError(session_id)
        return session

    def get_session(self, db: Database, *, user_id: str, session_id: str) -> dict:
        return _public_session(self._get_owned_session(db, session_id=session_id, user_id=user_id))

    def list_sessions(self, db: Database, *, user_id: str, page: int, limit: int) -> dict:
        query = {"user_id": ObjectId(user_id)}
        collection = db[Collections.PRESSURE_SESSIONS]
        total = collection.count_documents(query)
        cursor = (
            collection.find(query)
            .sort("started_at", DESCENDING)
            .skip((page - 1) * limit)
            .limit(limit)
        )
        return {
            "sessions": [_summary(doc) for doc in cursor],
            "page": page,
            "limit": limit,
            "total": total,
        }

    # --- Responding -----------------------------------------------------------------

    async def submit_response(
        self,
        db: Database,
        *,
        user_id: str,
        session_id: str,
        answer: str,
        input_type: str = "text",
        audio_metadata: dict | None = None,
        transcript_edited: bool = False,
        response_duration_seconds: float | None = None,
        timed_out: bool = False,
    ) -> dict:
        session = self._get_owned_session(db, session_id=session_id, user_id=user_id)
        if session["status"] != "in_progress":
            raise SessionNotActiveError(session_id)
        pending = _pending(session)
        if pending is None:
            raise SessionNotActiveError(session_id)

        qi, fi = pending
        questions = [dict(q, follow_up_questions=[dict(f) for f in q.get("follow_up_questions", [])]) for q in session["questions"]]
        question = questions[qi]
        record = question["follow_up_questions"][fi] if fi is not None else question

        now = datetime.now(timezone.utc)
        # Timer security: the server measures elapsed time from when the prompt
        # was asked; a client-reported duration is never trusted on its own.
        asked_at = record["asked_at"]
        if asked_at.tzinfo is None:
            asked_at = asked_at.replace(tzinfo=timezone.utc)
        server_elapsed = (now - asked_at).total_seconds()
        duration = server_elapsed if response_duration_seconds is None else min(response_duration_seconds, server_elapsed + 5)

        # An empty answer is only accepted when the timer genuinely expired --
        # the user's (lack of) response is never silently discarded either way.
        effective_answer = answer.strip() or ("(No answer was given before time expired.)" if timed_out else answer)

        text_metrics = None
        voice_analysis = None
        if input_type == "voice":
            metadata = audio_metadata or {}
            voice_analysis = analyze_transcript(
                effective_answer,
                duration_seconds=metadata.get("duration_seconds"),
                pause_metrics=metadata.get("pause_metrics"),
                language=metadata.get("language"),
                transcript_edited=transcript_edited,
            )
        elif effective_answer.strip():
            # Text mode still gets deterministic, text-based communication
            # indicators (filler words, sentence structure) -- no audio needed.
            text_metrics = analyze_transcript(effective_answer)

        topic = question["topic"]
        evaluation = await self._interview_eval.evaluate_answer(
            difficulty=session["difficulty"],
            topic=topic,
            question=record["question"],
            answer=effective_answer,
            input_type=input_type,
            voice_analysis=voice_analysis,
        )

        record.update(
            {
                "answer": effective_answer,
                "answer_input_type": input_type,
                "answered_at": now,
                "response_duration_seconds": round(duration, 1) if duration is not None else None,
                "timed_out": timed_out,
                "voice_analysis": voice_analysis,
                "text_metrics": text_metrics,
                "technical_evaluation": evaluation.technical,
                "communication_evaluation": evaluation.communication,
                "improved_answer": evaluation.improved_answer,
                "internal": evaluation.internal,
            }
        )

        config = get_pressure_config(session["pressure_level"])
        rng = random.Random()
        interruptions_used = sum(
            1 for f in question["follow_up_questions"] if f.get("kind") == "interruption"
        )
        used_follow_up_texts = [f["question"] for f in question["follow_up_questions"] if f.get("kind") == "rapid"]

        next_prompt_text: str | None = None
        next_prompt_kind: str | None = None
        next_condition: dict | None = None

        answering_follow_up = fi is not None
        follow_ups_for_question = len(question["follow_up_questions"])
        # Cap follow-ups/interruptions per question so a question can never chain
        # indefinitely -- after this many, the session always moves on.
        if follow_ups_for_question < pressure_engine.MAX_FOLLOW_UPS_PER_QUESTION:
            if not answering_follow_up:
                interruption_line = pressure_engine.roll_interruption(
                    config=config, question_number=question["question_number"], interruptions_used=interruptions_used, rng=rng
                )
                if interruption_line:
                    next_prompt_text, next_prompt_kind = interruption_line, "interruption"

            if next_prompt_text is None:
                rapid = pressure_engine.roll_rapid_follow_up(config=config, used_follow_ups=used_follow_up_texts, rng=rng)
                if rapid:
                    next_prompt_text, next_prompt_kind = rapid, "rapid"

        next_question_text: str | None = None
        if next_prompt_text is None and len(questions) < session["question_count"]:
            next_index = len(questions)
            plan_entry = session["topic_plan"][next_index]
            next_plan = pressure_engine.plan_next_question(
                config=config,
                interview_type=session["interview_type"],
                difficulty=session["difficulty"],
                planned_topic=plan_entry["topic"],
                planned_focus=plan_entry["focus"],
                rng=rng,
            )
            scores = [s for s in (question_scores(q)[0] for q in questions) if s is not None]
            all_questions_text = [q["question"] for q in questions]
            recent = [(q["question"], q["answer"]) for q in questions[-2:] if q.get("answer")]
            try:
                next_question_text = await self._questions.generate_question(
                    interview_type=session["interview_type"],
                    difficulty=next_plan.difficulty,
                    mode=session["input_mode"],
                    question_number=next_index + 1,
                    total_questions=session["question_count"],
                    topic=next_plan.topic,
                    focus=next_plan.focus,
                    previous_questions=all_questions_text,
                    recent_answers=recent,
                    technical_scores=scores,
                )
            except QuestionGenerationError:
                raise  # nothing was saved yet -- caller returns a clean 503
            next_condition = {
                "type": next_plan.condition_type,
                "time_limit_seconds": next_plan.time_limit_seconds,
                "topic_switched": next_plan.topic_switched,
                "difficulty_bumped": next_plan.difficulty_bumped,
            }
            questions.append(
                _new_question(
                    next_index + 1, next_question_text, topic=next_plan.topic, focus=next_plan.focus,
                    condition=next_condition, now=now,
                )
            )
        elif next_prompt_text is not None:
            question["follow_up_questions"].append(_new_follow_up(next_prompt_text, kind=next_prompt_kind, now=now))

        finished = next_prompt_text is None and next_question_text is None
        current_number = question["question_number"] if next_prompt_text else (
            questions[-1]["question_number"]
        )

        updated = db[Collections.PRESSURE_SESSIONS].update_one(
            {"_id": session["_id"], "version": session["version"], "status": "in_progress"},
            {
                "$set": {"questions": questions, "current_question_number": current_number, "updated_at": now},
                "$inc": {"version": 1},
            },
        )
        if updated.matched_count == 0:
            raise AnswerConflictError(session_id)

        final_evaluation = None
        if finished:
            completed = await self.complete_session(db, user_id=user_id, session_id=session_id)
            final_evaluation = completed["final_evaluation"]

        fresh = self._get_owned_session(db, session_id=session_id, user_id=user_id)
        return {
            "pressure_indicators": voice_analysis or text_metrics,
            "next_prompt": next_prompt_text or next_question_text,
            "next_prompt_kind": next_prompt_kind or ("question" if next_question_text else None),
            "next_condition": next_condition,
            "question_number": current_number,
            "is_follow_up": next_prompt_text is not None,
            "session_complete": finished,
            "final_evaluation": final_evaluation,
            "session": _public_session(fresh),
        }

    # --- Self-report ------------------------------------------------------------------

    def submit_self_report(
        self, db: Database, *, user_id: str, session_id: str, difficulty: str, note: str | None
    ) -> dict:
        if difficulty not in SELF_REPORT_LABELS:
            raise ValueError(f"Invalid self-reported difficulty: {difficulty}")
        session = self._get_owned_session(db, session_id=session_id, user_id=user_id)
        now = datetime.now(timezone.utc)
        db[Collections.PRESSURE_SESSIONS].update_one(
            {"_id": session["_id"]},
            {"$set": {"self_reported_difficulty": difficulty, "self_report_note": (note or "").strip()[:1000] or None, "updated_at": now}},
        )
        return self.get_session(db, user_id=user_id, session_id=session_id)

    # --- Completion -----------------------------------------------------------------

    def _learning_topics(self, db: Database) -> list[dict]:
        try:
            return [
                {"slug": t["slug"], "title": t["title"], "category": t.get("category")}
                for t in db[Collections.CYBERSECURITY_TOPICS].find({}, {"slug": 1, "title": 1, "category": 1})
            ]
        except Exception:  # noqa: BLE001 - recommendations still work without slugs
            logger.warning("Could not load learning topics for recommendations", exc_info=True)
            return []

    async def complete_session(self, db: Database, *, user_id: str, session_id: str) -> dict:
        """End a session (all questions answered, or ended early) and build the final evaluation. Idempotent."""
        session = self._get_owned_session(db, session_id=session_id, user_id=user_id)
        if session["status"] != "in_progress":
            return {"session_id": session_id, "status": session["status"], "final_evaluation": session.get("final_evaluation")}

        now = datetime.now(timezone.utc)
        answered = [q for q in session["questions"] if question_scores(q)[0] is not None]
        if not answered:
            db[Collections.PRESSURE_SESSIONS].update_one(
                {"_id": session["_id"], "version": session["version"], "status": "in_progress"},
                {"$set": {"status": "abandoned", "abandoned_at": now, "updated_at": now}, "$inc": {"version": 1}},
            )
            return {"session_id": session_id, "status": "abandoned", "final_evaluation": None}

        final = await self._pressure_eval.build_final_evaluation(db, session, learning_topics=self._learning_topics(db))
        updated = db[Collections.PRESSURE_SESSIONS].update_one(
            {"_id": session["_id"], "version": session["version"], "status": "in_progress"},
            {
                "$set": {"status": "completed", "completed_at": now, "updated_at": now, "final_evaluation": final},
                "$inc": {"version": 1},
            },
        )
        if updated.matched_count == 0:
            fresh = self._get_owned_session(db, session_id=session_id, user_id=user_id)
            return {"session_id": session_id, "status": fresh["status"], "final_evaluation": fresh.get("final_evaluation")}
        return {"session_id": session_id, "status": "completed", "final_evaluation": final}


pressure_service = PressureService()
