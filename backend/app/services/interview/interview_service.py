"""
Interview session orchestration.

Owns the `interview_sessions` collection (one document per interview, with
questions, answers and evaluations embedded) and the interview loop:

    start -> ask -> answer -> evaluate -> [follow-up | next question] -> ... -> final evaluation

    interview route -> InterviewService -+-> QuestionService ----+
                                         +-> EvaluationService --+-> existing AIService -> Gemini
                                         +-> Step 8 analysis (spoken answers)

Design notes:

* **No half-writes.** All AI work for an answer (evaluation, then a follow-up
  or the next question) happens *before* anything is saved, and it is saved
  in one guarded update. If the AI fails the caller gets a clean error, the
  answer is not consumed, and the user can simply resubmit.
* **Concurrency.** Writes are guarded by a `version` counter, so a
  double-submit can't record one answer twice.
* **No leakage.** While an interview is active, evaluations are hidden from
  every response unless the user enabled `reveal_feedback`. Internal notes
  (e.g. what the evaluator wanted to probe) are never returned.
"""

from __future__ import annotations

import copy
import random
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import DESCENDING
from pymongo.database import Database

from app.db.collections import Collections
from app.services.ai.ai_service import AIService, AIServiceError, ai_service
from app.services.communication.analysis_service import analyze_transcript
from app.services.interview.evaluation_service import (
    InterviewEvaluationService,
    question_scores,
)
from app.services.interview.question_service import (
    QuestionGenerationError,
    QuestionService,
    plan_questions,
)
from app.services.interview.topics import topic_label
from app.utils.logger import get_logger

logger = get_logger(__name__)

# --- Follow-up guardrails -------------------------------------------------------
# The evaluator *suggests* whether a probe is worthwhile; these rules decide
# whether one is *allowed*, so follow-ups can never happen after every answer.

MAX_FOLLOW_UPS_PER_QUESTION = {"beginner": 1, "intermediate": 1, "advanced": 2}
# Share of the interview's question count that may be follow-ups, per difficulty.
FOLLOW_UP_BUDGET_RATIO = {"beginner": 0.3, "intermediate": 0.4, "advanced": 0.5}
# Below this there is nothing to build a follow-up on.
FOLLOW_UP_MIN_TECHNICAL_SCORE = 25


def decide_follow_up(
    *,
    difficulty: str,
    question_count: int,
    technical_score: int,
    ai_suggested: bool,
    follow_ups_for_question: int,
    total_follow_ups: int,
    previous_question_had_follow_up: bool,
    answering_follow_up: bool,
) -> bool:
    """Whether to ask a follow-up now. Pure and deterministic given its inputs."""
    if not ai_suggested:
        return False
    if technical_score < FOLLOW_UP_MIN_TECHNICAL_SCORE:
        return False
    if follow_ups_for_question >= MAX_FOLLOW_UPS_PER_QUESTION[difficulty]:
        return False
    budget = max(1, int(question_count * FOLLOW_UP_BUDGET_RATIO[difficulty]))
    if total_follow_ups >= budget:
        return False
    # Don't probe two questions in a row (except in advanced, "chained" interviews).
    if (
        difficulty != "advanced"
        and not answering_follow_up
        and previous_question_had_follow_up
    ):
        return False
    return True


# --- Errors --------------------------------------------------------------------


class InterviewError(Exception):
    """Base class for interview-service-level errors."""


class SessionNotFoundError(InterviewError):
    pass


class SessionForbiddenError(InterviewError):
    """The session exists but belongs to another user."""


class SessionNotActiveError(InterviewError):
    """The interview is completed/abandoned and can't accept answers."""


class AnswerConflictError(InterviewError):
    """The session changed while the answer was being processed (e.g. double submit)."""


# --- Helpers -------------------------------------------------------------------


def _pending(session: dict) -> tuple[int, int | None] | None:
    """(question index, follow-up index or None) of the prompt awaiting an answer."""
    for qi, question in enumerate(session["questions"]):
        if question.get("answer") is None:
            return qi, None
        for fi, follow_up in enumerate(question.get("follow_up_questions", [])):
            if follow_up.get("answer") is None:
                return qi, fi
    return None


def _new_question(number: int, text: str, plan_entry: dict, now: datetime) -> dict:
    return {
        "question_number": number,
        "question": text,
        "topic": plan_entry["topic"],
        "focus": plan_entry["focus"],
        "asked_at": now,
        "answer": None,
        "answer_input_type": "text",
        "answered_at": None,
        "voice_analysis": None,
        "technical_evaluation": None,
        "communication_evaluation": None,
        "improved_answer": None,
        "internal": {},
        "follow_up_questions": [],
    }


def _public_record(record: dict, *, hide_evaluation: bool) -> dict:
    return {
        "answer": record.get("answer"),
        "answer_input_type": record.get("answer_input_type", "text"),
        "voice_analysis": record.get("voice_analysis"),
        "technical_evaluation": None if hide_evaluation else record.get("technical_evaluation"),
        "communication_evaluation": None if hide_evaluation else record.get("communication_evaluation"),
        "improved_answer": None if hide_evaluation else record.get("improved_answer"),
    }


def _public_session(session: dict) -> dict:
    """
    The client-facing view of a session. While the interview is active and the
    user hasn't asked to see feedback, evaluations are withheld entirely — even
    from GET — so nothing can be peeked at mid-interview.
    """
    active = session["status"] == "in_progress"
    hide = active and not session.get("reveal_feedback", False)

    questions = []
    for q in session["questions"]:
        tech, comm = question_scores(q)
        questions.append(
            {
                "question_number": q["question_number"],
                "question": q["question"],
                "topic": q["topic"],
                "topic_label": topic_label(q["topic"]),
                **_public_record(q, hide_evaluation=hide),
                "technical_score": None if hide else tech,
                "communication_score": None if hide else comm,
                "follow_up_questions": [
                    {"question": fu["question"], **_public_record(fu, hide_evaluation=hide)}
                    for fu in q.get("follow_up_questions", [])
                ],
            }
        )

    pending = _pending(session) if active else None
    current_prompt = None
    if pending is not None:
        qi, fi = pending
        q = session["questions"][qi]
        current_prompt = {
            "question_number": q["question_number"],
            "question": q["question"] if fi is None else q["follow_up_questions"][fi]["question"],
            "topic": q["topic"],
            "topic_label": topic_label(q["topic"]),
            "is_follow_up": fi is not None,
            "follow_up_index": fi,
        }

    answered = sum(1 for q in session["questions"] if q.get("answer") is not None)
    return {
        "session_id": str(session["_id"]),
        "interview_type": session["interview_type"],
        "difficulty": session["difficulty"],
        "mode": session["mode"],
        "question_count": session["question_count"],
        "current_question_number": session["current_question_number"],
        "answered_count": answered,
        "status": session["status"],
        "reveal_feedback": session.get("reveal_feedback", False),
        "started_at": session["started_at"].isoformat(),
        "completed_at": session["completed_at"].isoformat() if session.get("completed_at") else None,
        "current_prompt": current_prompt,
        "questions": questions,
        "final_evaluation": session.get("final_evaluation"),
    }


def _summary(session: dict) -> dict:
    final = session.get("final_evaluation") or {}
    return {
        "session_id": str(session["_id"]),
        "interview_type": session["interview_type"],
        "difficulty": session["difficulty"],
        "mode": session["mode"],
        "question_count": session["question_count"],
        "answered_count": sum(1 for q in session["questions"] if q.get("answer") is not None),
        "status": session["status"],
        "overall_score": final.get("overall_score"),
        "technical_score": final.get("technical_score"),
        "communication_score": final.get("communication_score"),
        "started_at": session["started_at"].isoformat(),
        "completed_at": session["completed_at"].isoformat() if session.get("completed_at") else None,
    }


# --- Service -------------------------------------------------------------------


class InterviewService:
    """Interview simulator: sessions, ownership, and the ask/answer/evaluate loop."""

    def __init__(
        self,
        ai_service_: AIService = ai_service,
        question_service_: QuestionService | None = None,
        evaluation_service_: InterviewEvaluationService | None = None,
    ) -> None:
        # Both sub-services share the one existing AIService — no second Gemini client.
        self._questions = question_service_ or QuestionService(ai_service_)
        self._evaluation = evaluation_service_ or InterviewEvaluationService(ai_service_)

    def ensure_indexes(self, db: Database) -> None:
        """Create required indexes. Idempotent — safe to call on every startup."""
        sessions = db[Collections.INTERVIEW_SESSIONS]
        sessions.create_index("user_id")
        sessions.create_index("status")
        sessions.create_index("started_at")
        sessions.create_index("interview_type")
        sessions.create_index("difficulty")
        # The history query: one user's interviews, newest first.
        sessions.create_index([("user_id", 1), ("started_at", -1)])

    # --- Sessions -----------------------------------------------------------------

    async def start_session(
        self,
        db: Database,
        *,
        user_id: str,
        interview_type: str,
        difficulty: str,
        question_count: int,
        mode: str,
        reveal_feedback: bool = False,
        rng: random.Random | None = None,
    ) -> dict:
        plan = plan_questions(interview_type, question_count, rng)

        # Generate the first question *before* inserting, so an AI failure
        # never leaves an empty session behind.
        first_question = await self._questions.generate_question(
            interview_type=interview_type,
            difficulty=difficulty,
            mode=mode,
            question_number=1,
            total_questions=question_count,
            topic=plan[0]["topic"],
            focus=plan[0]["focus"],
            previous_questions=[],
            recent_answers=[],
            technical_scores=[],
        )

        now = datetime.now(timezone.utc)
        document = {
            "user_id": ObjectId(user_id),
            "interview_type": interview_type,
            "difficulty": difficulty,
            "mode": mode,
            "question_count": question_count,
            "current_question_number": 1,
            "status": "in_progress",
            "reveal_feedback": reveal_feedback,
            "topic_plan": plan,
            "version": 0,
            "questions": [_new_question(1, first_question, plan[0], now)],
            "final_evaluation": None,
            "started_at": now,
            "updated_at": now,
            "completed_at": None,
            "abandoned_at": None,
        }
        result = db[Collections.INTERVIEW_SESSIONS].insert_one(document)
        document["_id"] = result.inserted_id
        public = _public_session(document)
        return {
            "session_id": public["session_id"],
            "question_number": 1,
            "question": first_question,
            "topic_label": topic_label(plan[0]["topic"]),
            "interview_type": interview_type,
            "difficulty": difficulty,
            "mode": mode,
            "question_count": question_count,
            "reveal_feedback": reveal_feedback,
            "status": "in_progress",
            "session": public,
        }

    def _get_owned_session(self, db: Database, *, session_id: str, user_id: str) -> dict:
        try:
            object_id = ObjectId(session_id)
        except (InvalidId, TypeError) as exc:
            raise SessionNotFoundError(session_id) from exc
        session = db[Collections.INTERVIEW_SESSIONS].find_one({"_id": object_id})
        if session is None:
            raise SessionNotFoundError(session_id)
        if str(session["user_id"]) != user_id:
            raise SessionForbiddenError(session_id)
        return session

    def get_session(self, db: Database, *, user_id: str, session_id: str) -> dict:
        return _public_session(self._get_owned_session(db, session_id=session_id, user_id=user_id))

    def list_sessions(self, db: Database, *, user_id: str, page: int, limit: int) -> dict:
        query = {"user_id": ObjectId(user_id)}  # the caller's own sessions only
        collection = db[Collections.INTERVIEW_SESSIONS]
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

    # --- Answering ----------------------------------------------------------------

    async def submit_answer(
        self,
        db: Database,
        *,
        user_id: str,
        session_id: str,
        answer: str,
        input_type: str = "text",
        audio_metadata: dict | None = None,
        transcript_edited: bool = False,
    ) -> dict:
        session = self._get_owned_session(db, session_id=session_id, user_id=user_id)
        if session["status"] != "in_progress":
            raise SessionNotActiveError(session_id)
        pending = _pending(session)
        if pending is None:
            raise SessionNotActiveError(session_id)

        qi, fi = pending
        questions = copy.deepcopy(session["questions"])
        question = questions[qi]
        answering_follow_up = fi is not None
        record = question["follow_up_questions"][fi] if answering_follow_up else question

        # Spoken answers reuse the Step 8 analysis (deterministic; audio is never stored).
        voice_analysis = None
        if input_type == "voice":
            metadata = audio_metadata or {}
            voice_analysis = analyze_transcript(
                answer,
                duration_seconds=metadata.get("duration_seconds"),
                pause_metrics=metadata.get("pause_metrics"),
                language=metadata.get("language"),
                transcript_edited=transcript_edited,
            )

        # ---- All AI work first: nothing below is saved until it succeeds. ----
        evaluation = await self._evaluation.evaluate_answer(
            difficulty=session["difficulty"],
            topic=question["topic"],
            question=record["question"],
            answer=answer,
            input_type=input_type,
            voice_analysis=voice_analysis,
        )

        now = datetime.now(timezone.utc)
        record.update(
            {
                "answer": answer,
                "answer_input_type": input_type,
                "answered_at": now,
                "voice_analysis": voice_analysis,
                "technical_evaluation": evaluation.technical,
                "communication_evaluation": evaluation.communication,
                "improved_answer": evaluation.improved_answer,
                "internal": evaluation.internal,
            }
        )

        all_questions_text = [q["question"] for q in questions] + [
            fu["question"] for q in questions for fu in q["follow_up_questions"]
        ]
        total_follow_ups = sum(len(q["follow_up_questions"]) for q in questions)
        previous_had_follow_up = qi > 0 and bool(questions[qi - 1]["follow_up_questions"])

        follow_up_text: str | None = None
        if decide_follow_up(
            difficulty=session["difficulty"],
            question_count=session["question_count"],
            technical_score=evaluation.technical["technical_score"],
            ai_suggested=bool(evaluation.internal.get("follow_up_suggested")),
            follow_ups_for_question=len(question["follow_up_questions"]),
            total_follow_ups=total_follow_ups,
            previous_question_had_follow_up=previous_had_follow_up,
            answering_follow_up=answering_follow_up,
        ):
            try:
                follow_up_text = await self._questions.generate_follow_up(
                    interview_type=session["interview_type"],
                    difficulty=session["difficulty"],
                    mode=session["mode"],
                    topic=question["topic"],
                    question=question["question"],
                    answer=answer,
                    focus=evaluation.internal.get("follow_up_focus", ""),
                    previous_follow_ups=[fu["question"] for fu in question["follow_up_questions"]],
                    all_previous_questions=all_questions_text,
                )
            except (QuestionGenerationError, AIServiceError):
                # A follow-up is optional: skip it rather than fail the answer.
                logger.warning("Follow-up generation failed; continuing without one")

        next_question_text: str | None = None
        if follow_up_text:
            question["follow_up_questions"].append(
                {
                    "question": follow_up_text,
                    "asked_at": now,
                    "answer": None,
                    "answer_input_type": "text",
                    "answered_at": None,
                    "voice_analysis": None,
                    "technical_evaluation": None,
                    "communication_evaluation": None,
                    "improved_answer": None,
                    "internal": {},
                }
            )
        elif len(questions) < session["question_count"]:
            next_index = len(questions)
            plan_entry = session["topic_plan"][next_index]
            scores = [
                s for s in (question_scores(q)[0] for q in questions) if s is not None
            ]
            recent = [
                (q["question"], q["answer"]) for q in questions[-2:] if q.get("answer")
            ]
            next_question_text = await self._questions.generate_question(
                interview_type=session["interview_type"],
                difficulty=session["difficulty"],
                mode=session["mode"],
                question_number=next_index + 1,
                total_questions=session["question_count"],
                topic=plan_entry["topic"],
                focus=plan_entry["focus"],
                previous_questions=all_questions_text,
                recent_answers=recent,
                technical_scores=scores,
            )
            questions.append(_new_question(next_index + 1, next_question_text, plan_entry, now))

        finished = follow_up_text is None and next_question_text is None
        current_number = question["question_number"] if follow_up_text else (
            questions[-1]["question_number"]
        )

        updated = db[Collections.INTERVIEW_SESSIONS].update_one(
            {"_id": session["_id"], "version": session["version"], "status": "in_progress"},
            {
                "$set": {
                    "questions": questions,
                    "current_question_number": current_number,
                    "updated_at": now,
                },
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
        reveal = fresh.get("reveal_feedback", False)
        return {
            "evaluation": {
                "technical_score": evaluation.technical["technical_score"],
                "communication_score": evaluation.communication["communication_score"],
                "feedback": evaluation.technical["feedback"],
                "communication_feedback": evaluation.communication["feedback"],
            }
            if reveal
            else None,
            "next_question": follow_up_text or next_question_text,
            "question_number": current_number,
            "is_follow_up": follow_up_text is not None,
            "interview_complete": finished,
            "final_evaluation": final_evaluation,
            "session": _public_session(fresh),
        }

    # --- Completion -----------------------------------------------------------------

    def _learning_topics(self, db: Database) -> list[dict]:
        """Read-only lookup of Step 5 learning topics, to ground recommendations."""
        try:
            return [
                {"slug": t["slug"], "title": t["title"], "category": t.get("category")}
                for t in db[Collections.CYBERSECURITY_TOPICS].find(
                    {}, {"slug": 1, "title": 1, "category": 1}
                )
            ]
        except Exception:  # noqa: BLE001 - recommendations still work without slugs
            logger.warning("Could not load learning topics for recommendations", exc_info=True)
            return []

    async def complete_session(self, db: Database, *, user_id: str, session_id: str) -> dict:
        """
        End an interview (all questions answered, or the user ended it early)
        and generate the final evaluation. Idempotent. An interview with no
        answers has nothing to evaluate and is marked `abandoned`.
        """
        session = self._get_owned_session(db, session_id=session_id, user_id=user_id)
        if session["status"] != "in_progress":
            return {
                "session_id": session_id,
                "status": session["status"],
                "final_evaluation": session.get("final_evaluation"),
            }

        now = datetime.now(timezone.utc)
        answered = [q for q in session["questions"] if question_scores(q)[0] is not None]
        if not answered:
            db[Collections.INTERVIEW_SESSIONS].update_one(
                {"_id": session["_id"], "version": session["version"], "status": "in_progress"},
                {
                    "$set": {"status": "abandoned", "abandoned_at": now, "updated_at": now},
                    "$inc": {"version": 1},
                },
            )
            return {"session_id": session_id, "status": "abandoned", "final_evaluation": None}

        final = await self._evaluation.build_final_evaluation(
            session, learning_topics=self._learning_topics(db)
        )
        updated = db[Collections.INTERVIEW_SESSIONS].update_one(
            {"_id": session["_id"], "version": session["version"], "status": "in_progress"},
            {
                "$set": {
                    "status": "completed",
                    "completed_at": now,
                    "updated_at": now,
                    "final_evaluation": final,
                },
                "$inc": {"version": 1},
            },
        )
        if updated.matched_count == 0:
            # Someone else completed it first — return whatever is stored.
            fresh = self._get_owned_session(db, session_id=session_id, user_id=user_id)
            return {
                "session_id": session_id,
                "status": fresh["status"],
                "final_evaluation": fresh.get("final_evaluation"),
            }
        return {"session_id": session_id, "status": "completed", "final_evaluation": final}


interview_service = InterviewService()
