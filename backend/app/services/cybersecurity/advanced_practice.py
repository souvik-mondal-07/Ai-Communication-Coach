"""
Advanced practice sessions (Step 17), as a mixin for `PracticeService`.

It extends -- rather than replaces -- the Step 5 practice flow and reuses
everything already in place:

* the one `AIService` (Gemini 3.1 Flash-Lite) for question generation and
  free-text evaluation -- no second AI client
* the `practice_sessions` collection, its ownership checks, history and progress
* Step 16 personalization for planning, adaptive difficulty and "what next"

Gemini is called only when it has to be:

    open the practice page / config / session state / hints   -> no AI call
    start a session                                           -> 1 call (first question)
    next question                                             -> 1 call
    submit a free-text answer                                 -> 1 call (multiple choice: none)

Questions are generated one at a time so the difficulty can adapt to how the
learner is doing and a session abandoned half-way never pays for unused questions.
Hints are generated together with the question, so requesting one is free.

The mixin relies on `PracticeService` for `_ai_service`, `_learning_service`,
`_personalization`, `_rng` and `_get_owned_session` (it is not used on its own).
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from pydantic import ValidationError
from pymongo import DESCENDING, ReturnDocument
from pymongo.database import Database

from app.db.collections import Collections
from app.services.ai.ai_service import AIServiceError
from app.services.cybersecurity import practice_engine as engine
from app.services.cybersecurity.practice_prompts import (
    EVALUATION_SYSTEM_PROMPT,
    QUESTION_SYSTEM_PROMPT,
    build_evaluation_prompt,
    build_question_prompt,
)
from app.services.cybersecurity.practice_results import MIXED_CATEGORY
from app.services.cybersecurity.practice_types import (
    AnswerAlreadySubmittedError,
    AnswerEvaluationError,
    AnswerResult,
    HintLimitError,
    InvalidPracticeConfigError,
    PracticeGenerationError,
    QuestionNotFoundError,
    QuestionNotReadyError,
    SessionClosedError,
)
from app.services.personalization.personalization_service import invalidate_user
from app.utils.logger import get_logger

logger = get_logger(__name__)

MAX_GENERATION_ATTEMPTS = 2
MAX_AVOID_STEMS = 8
RECENT_SESSIONS_FOR_HISTORY = 5
# A claimed-but-never-finished evaluation (e.g. the server restarted mid-call) is reclaimable after this.
PENDING_TTL_SECONDS = 120


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _iso(value: datetime | None) -> str | None:
    value = _as_utc(value)
    return value.isoformat() if value else None


def _stem(text: str) -> str:
    return " ".join((text or "").split())[:120]


class AdvancedPracticeMixin:
    # ------------------------------------------------------------------ config
    def get_config(self, db: Database) -> dict:
        """
        What the practice UI can offer, derived from the live topic catalogue so only
        categories the engine can really support are exposed. No AI call.
        """
        topics = list(
            db[Collections.CYBERSECURITY_TOPICS].find(
                {"practice_enabled": True}, {"_id": 0, "slug": 1, "title": 1, "category": 1, "difficulty": 1}
            )
        )
        grouped: dict[str, list[dict]] = {}
        for t in topics:
            grouped.setdefault(t["category"], []).append(t)
        categories = [
            {
                "category": name,
                "question_types": engine.supported_types(name),
                "topics": [{"slug": t["slug"], "title": t["title"], "difficulty": t["difficulty"]}
                           for t in sorted(items, key=lambda t: t["title"])],
            }
            for name, items in sorted(grouped.items())
        ]
        return {
            "modes": [dict(m) for m in engine.MODE_INFO],
            "difficulties": list(engine.DIFFICULTY_CHOICES),
            "question_types": list(engine.TYPE_CHOICES),
            "categories": categories,
            "limits": {
                "min_questions": engine.MIN_QUESTIONS,
                "max_questions": engine.MAX_QUESTIONS,
                "default_questions": engine.DEFAULT_QUESTIONS,
                "min_time_limit_minutes": engine.MIN_TIME_LIMIT_MINUTES,
                "max_time_limit_minutes": engine.MAX_TIME_LIMIT_MINUTES,
                "max_hints": engine.MAX_HINTS,
            },
        }

    # ----------------------------------------------------------------- helpers
    def _load_user(self, db: Database, user_id: str) -> dict | None:
        return db[Collections.USERS].find_one({"_id": ObjectId(user_id)})

    def _personalization_snapshot(self, db: Database, user: dict | None) -> dict | None:
        """Step 16 personalization output. Never raises: practice must work without it."""
        if user is None:
            return None
        try:
            return self._personalization.compute(db, user=user)
        except Exception:  # noqa: BLE001
            logger.warning("Personalization unavailable for practice", exc_info=True)
            return None

    def _recent_history(self, db: Database, user_id: str) -> dict:
        """Slugs, categories (newest first) and question stems from the user's last few sessions."""
        docs = db[Collections.PRACTICE_SESSIONS].find(
            {"user_id": ObjectId(user_id)},
            {"topic_slug": 1, "category": 1, "questions.question": 1, "questions.topic_slug": 1,
             "questions.category": 1},
        ).sort("started_at", DESCENDING).limit(RECENT_SESSIONS_FOR_HISTORY)
        slugs: set[str] = set()
        categories: list[str] = []
        stems: list[str] = []
        for doc in docs:
            questions = doc.get("questions") or []
            if doc.get("topic_slug"):
                slugs.add(doc["topic_slug"])
            for q in questions:
                slug = q.get("topic_slug")
                if slug:
                    slugs.add(slug)
                cat = q.get("category") or doc.get("category")
                if cat and cat != MIXED_CATEGORY and cat not in categories:
                    categories.append(cat)
                if q.get("question") and len(stems) < MAX_AVOID_STEMS:
                    stems.append(_stem(q["question"]))
            cat = doc.get("category")
            if cat and cat != MIXED_CATEGORY and cat not in categories:
                categories.append(cat)
        return {"slugs": slugs, "categories": categories, "stems": stems}

    @staticmethod
    def _deadline(session: dict) -> datetime | None:
        limit = session.get("time_limit_seconds")
        started = _as_utc(session.get("started_at"))
        return started + timedelta(seconds=limit) if limit and started else None

    def _remaining_seconds(self, session: dict) -> int | None:
        deadline = self._deadline(session)
        if deadline is None:
            return None
        return max(0, int((deadline - datetime.now(timezone.utc)).total_seconds()))

    def _ensure_open(self, db: Database, session: dict, *, grace_seconds: int = 0) -> None:
        """Raise `SessionClosedError` unless the session accepts activity; saves a timed-out one."""
        if session.get("status") != "in_progress":
            raise SessionClosedError("This practice session is already complete.")
        deadline = self._deadline(session)
        if deadline and datetime.now(timezone.utc) > deadline + timedelta(seconds=grace_seconds):
            self._complete_advanced_session(db, session=session)
            raise SessionClosedError("Time is up. Your answers were saved.", expired=True)

    # ------------------------------------------------------- question building
    async def _generate_advanced_question(
        self, *, slot: dict, topic: dict, difficulty: str, learner: dict | None,
        focus_note: str | None, avoid_stems: list[str], seen: set[str],
    ) -> dict:
        prompt = build_question_prompt(
            topic_title=topic["title"],
            topic_description=topic.get("description", ""),
            learning_objectives=topic.get("learning_objectives", []),
            category=topic["category"],
            difficulty=difficulty,
            question_type=slot["type"],
            style=slot.get("style"),
            learner=learner,
            focus_note=focus_note,
            avoid_stems=avoid_stems,
        )
        last_error: Exception | None = None
        for attempt in range(1, MAX_GENERATION_ATTEMPTS + 1):
            try:
                result = await self._ai_service.generate_response(
                    user_message=prompt, system_prompt=QUESTION_SYSTEM_PROMPT
                )
                validated = engine.validate_generated_question(
                    engine.parse_json_object(result.text), expected_type=slot["type"]
                )
            except AIServiceError as exc:
                logger.error("Advanced question generation failed: %s", type(exc).__name__)
                raise PracticeGenerationError("AI provider failed to generate a question.") from exc
            except (ValueError, ValidationError) as exc:
                last_error = exc
                logger.warning(
                    "Invalid generated question on attempt %d/%d: %s",
                    attempt, MAX_GENERATION_ATTEMPTS, type(exc).__name__,
                )
                continue
            # Same question twice in one session: retry once, then accept (AI output can't be
            # guaranteed unique and a stalled session is worse than a near-duplicate).
            if validated["question"].lower() in seen and attempt < MAX_GENERATION_ATTEMPTS:
                continue
            return {
                **validated,
                "question_id": uuid.uuid4().hex,
                "index": slot["index"],
                "style": slot.get("style"),
                "topic_slug": topic["slug"],
                "topic_title": topic["title"],
                "category": topic["category"],
                "difficulty": difficulty,
                "generated_at": datetime.now(timezone.utc),
            }
        raise PracticeGenerationError("Could not generate a valid question.") from last_error

    @staticmethod
    def _learner_context(pers: dict | None) -> dict | None:
        if not pers:
            return None
        return {
            "user_level": pers.get("user_level"),
            "career_goal": pers.get("career_goal"),
            "interests": [i.replace("_", " ") for i in pers.get("interests", [])],
        }

    # ------------------------------------------------------------------- start
    async def start_advanced_session(
        self, db: Database, *, user_id: str, mode: str, category: str | None, topic_slug: str | None,
        difficulty: str, question_type: str, question_count: int, time_limit_minutes: int | None,
    ) -> dict:
        if time_limit_minutes is not None and not (
            engine.MIN_TIME_LIMIT_MINUTES <= time_limit_minutes <= engine.MAX_TIME_LIMIT_MINUTES
        ):
            raise InvalidPracticeConfigError(
                f"Time limit must be between {engine.MIN_TIME_LIMIT_MINUTES} and "
                f"{engine.MAX_TIME_LIMIT_MINUTES} minutes."
            )

        pers = self._personalization_snapshot(db, self._load_user(db, user_id))
        catalog = list(
            db[Collections.CYBERSECURITY_TOPICS].find(
                {"practice_enabled": True},
                {"_id": 0, "slug": 1, "title": 1, "category": 1, "difficulty": 1,
                 "description": 1, "learning_objectives": 1},
            )
        )
        recent = self._recent_history(db, user_id)
        try:
            plan = engine.plan_session(
                mode=mode, category=category, topic_slug=topic_slug, question_type=question_type,
                question_count=question_count, difficulty=difficulty, catalog=catalog,
                personalization=pers, recent_slugs=recent["slugs"],
                recent_categories=recent["categories"], rng=self._rng,
            )
        except engine.PlanError as exc:
            raise InvalidPracticeConfigError(str(exc)) from exc

        topics_by_slug = {t["slug"]: t for t in catalog}
        first = plan.slots[0]
        first_difficulty = first["base_difficulty"]
        focus_note = None
        if plan.effective_mode == "weakness":
            focus_note = "The learner is weak in this area; reinforce core concepts."
        question = await self._generate_advanced_question(
            slot=first, topic=topics_by_slug[first["topic_slug"]], difficulty=first_difficulty,
            learner=self._learner_context(pers), focus_note=focus_note,
            avoid_stems=recent["stems"], seen=set(),
        )

        titles = list(dict.fromkeys(s["topic_title"] for s in plan.slots))
        title = (
            titles[0] if len(titles) == 1
            else f"{engine.MODE_LABELS[plan.effective_mode]} practice: {', '.join(plan.categories[:3])}"
        )
        doc: dict = {
            "user_id": ObjectId(user_id),
            "mode": plan.effective_mode,
            "requested_mode": mode,
            "topic_slug": first["topic_slug"],  # primary topic (Step 5 field, used by history)
            "topic_title": title,
            "category": plan.categories[0] if len(plan.categories) == 1 else MIXED_CATEGORY,
            "categories": plan.categories,
            "difficulty": first_difficulty,  # always a concrete level; see difficulty_mode
            "difficulty_mode": "adaptive" if difficulty == "adaptive" else "fixed",
            "question_type": plan.effective_type,
            "started_at": datetime.now(timezone.utc),
            "completed_at": None,
            "status": "in_progress",
            "time_limit_seconds": time_limit_minutes * 60 if time_limit_minutes else None,
            "plan": plan.slots,
            "focus": plan.focus,
            "note": plan.note,
            "avoid_stems": recent["stems"][:MAX_AVOID_STEMS],
            "questions": [question],
            "answers": {},
            "hint_counts": {question["question_id"]: 0},
            "pending": {},
            "personalization": self._personalization_summary(pers),
            "score": None,
            "questions_answered": None,
            "correct_answers": None,
            "weak_areas": [],
            "recommendations": [],
        }
        doc["_id"] = db[Collections.PRACTICE_SESSIONS].insert_one(doc).inserted_id
        return self._public_session(doc)

    @staticmethod
    def _personalization_summary(pers: dict | None) -> dict | None:
        """Small snapshot kept on the session (what the plan was based on) -- never raw history."""
        if not pers:
            return None
        return {
            "user_level": pers.get("user_level"),
            "career_goal": pers.get("career_goal"),
            "data_status": pers.get("data_status"),
            "strengths": [s["topic"] for s in pers.get("strengths", [])][:3],
            "weaknesses": [w["topic"] for w in pers.get("weaknesses", [])][:3],
            "recommended_topics": list(pers.get("recommended_topics", []))[:3],
        }

    # ------------------------------------------------------------ public views
    def _result_dict(self, question: dict, record: dict) -> dict:
        raw = record.get("raw_score")
        return AnswerResult(
            score=record["score"],
            correct=record["correct"],
            feedback=record.get("feedback", ""),
            ideal_answer=question.get("ideal_answer"),
            missing_points=record.get("missing_points", []),
            raw_score=raw,
            hints_used=record.get("hints_used", 0),
            hint_penalty=(raw - record["score"]) if raw is not None else 0,
            dimension_scores=record.get("dimension_scores"),
            strengths=record.get("strengths", []),
            improvement=record.get("improvement"),
            explanation=question.get("explanation"),
            ideal_steps=question.get("ideal_steps"),
            revealed=bool(record.get("revealed")),
        ).to_public_dict()

    def _public_question(self, session: dict, q: dict, index: int) -> dict:
        """Client-safe question: the answer key, expected concepts and unrevealed hints stay server-side."""
        record = (session.get("answers") or {}).get(q["question_id"])
        hints_used = (session.get("hint_counts") or {}).get(q["question_id"], 0)
        hints = q.get("hints") or []
        return {
            "question_id": q["question_id"],
            "index": index,
            "question": q["question"],
            "type": q["type"],
            "options": q.get("options"),
            "topic_title": q.get("topic_title") or session.get("topic_title"),
            "category": q.get("category") or session.get("category"),
            "difficulty": q.get("difficulty") or session.get("difficulty"),
            "hints_available": len(hints),
            "hints_used": hints_used,
            "hints": hints[:hints_used],
            "answered": record is not None,
            "result": self._result_dict(q, record) if record is not None else None,
        }

    def _public_session(self, session: dict) -> dict:
        questions = session.get("questions") or []
        planned = len(session.get("plan") or []) or len(questions)
        in_progress = session.get("status") == "in_progress"
        answers = session.get("answers") or {}
        last_done = bool(questions) and questions[-1]["question_id"] in answers
        data = {
            "session_id": str(session["_id"]),
            "mode": session.get("mode") or "topic",
            "status": session.get("status"),
            "topic_slug": session.get("topic_slug"),
            "topic_title": session.get("topic_title"),
            "category": session.get("category"),
            "categories": session.get("categories") or [session.get("category")],
            "difficulty": session.get("difficulty"),
            "difficulty_mode": session.get("difficulty_mode") or "fixed",
            "question_type": session.get("question_type") or "mixed",
            "question_count": planned,
            "started_at": _iso(session.get("started_at")),
            "time_limit_seconds": session.get("time_limit_seconds"),
            "remaining_seconds": self._remaining_seconds(session) if in_progress else None,
            "note": session.get("note"),
            "focus": session.get("focus") or [],
            "questions": [self._public_question(session, q, i) for i, q in enumerate(questions)],
            "has_more_questions": in_progress and len(questions) < planned,
            "can_request_next": in_progress and len(questions) < planned and last_done,
            "summary": None,
        }
        if session.get("status") == "completed":
            data["summary"] = (
                self._build_advanced_result(session) if session.get("mode") else self._build_complete_result(session)
            )
        return data

    def get_session(self, db: Database, *, user_id: str, session_id: str) -> dict:
        """Full current state (also used to resume after a refresh). Saves a timed-out session. No AI call."""
        session = self._get_owned_session(db, session_id=session_id, user_id=user_id)
        if session.get("mode") and session.get("status") == "in_progress":
            deadline = self._deadline(session)
            if deadline and datetime.now(timezone.utc) > deadline + timedelta(seconds=engine.ANSWER_GRACE_SECONDS):
                self._complete_advanced_session(db, session=session)
                session = self._get_owned_session(db, session_id=session_id, user_id=user_id)
        elif not session.get("mode"):
            session = dict(session)
            session.setdefault("plan", session.get("questions"))
        return self._public_session(session)

    # -------------------------------------------------------------------- next
    async def next_question(self, db: Database, *, user_id: str, session_id: str) -> dict:
        session = self._get_owned_session(db, session_id=session_id, user_id=user_id)
        if not session.get("mode"):
            raise QuestionNotReadyError("This session has all its questions already.", code="NO_MORE_QUESTIONS")
        self._ensure_open(db, session)

        questions = session["questions"]
        plan = session["plan"]
        n = len(questions)
        if n >= len(plan):
            raise QuestionNotReadyError("There are no more questions in this session.", code="NO_MORE_QUESTIONS")
        answers = session.get("answers") or {}
        if questions[-1]["question_id"] not in answers:
            raise QuestionNotReadyError("Answer the current question first.", code="ANSWER_CURRENT_FIRST")

        slot = plan[n]
        scores = [answers[q["question_id"]]["score"] for q in questions if q["question_id"] in answers]
        base = slot["base_difficulty"]
        difficulty = (
            engine.adjust_difficulty(base, scores) if session.get("difficulty_mode") == "adaptive" else base
        )
        topic = self._learning_service.get_topic_by_slug(db, slot["topic_slug"])
        if topic is None:
            raise PracticeGenerationError("The topic for this question is no longer available.")

        focus_note = None
        if difficulty != base and engine.LEVELS.index(difficulty) < engine.LEVELS.index(base):
            focus_note = "The learner has struggled recently; reinforce fundamentals."
        elif session.get("mode") == "weakness":
            focus_note = "The learner is weak in this area; reinforce core concepts."

        seen = {q["question"].lower() for q in questions}
        stems = ([_stem(q["question"]) for q in reversed(questions)] + list(session.get("avoid_stems") or []))[
            :MAX_AVOID_STEMS
        ]
        question = await self._generate_advanced_question(
            slot=slot, topic=topic, difficulty=difficulty,
            learner=self._learner_context_from_session(session), focus_note=focus_note,
            avoid_stems=stems, seen=seen,
        )

        # Only one request wins the push for position `n` (double-clicks / retries are idempotent).
        pushed = db[Collections.PRACTICE_SESSIONS].update_one(
            {"_id": session["_id"], "status": "in_progress", f"questions.{n}": {"$exists": False}},
            {"$push": {"questions": question}, "$set": {f"hint_counts.{question['question_id']}": 0}},
        )
        fresh = self._get_owned_session(db, session_id=session_id, user_id=user_id)
        if pushed.matched_count == 0 and fresh.get("status") != "in_progress":
            raise SessionClosedError("This practice session is already complete.")
        public = self._public_session(fresh)
        return {"question": public["questions"][n], "state": public}

    @staticmethod
    def _learner_context_from_session(session: dict) -> dict | None:
        p = session.get("personalization")
        if not p:
            return None
        return {"user_level": p.get("user_level"), "career_goal": p.get("career_goal"), "interests": []}

    # ------------------------------------------------------------------- hints
    def request_hint(
        self, db: Database, *, user_id: str, session_id: str, question_id: str, reveal: bool = False
    ) -> dict:
        """
        Progressive help: Hint 1 -> Hint 2 -> Hint 3, then (`reveal=True`) the explanation. Never an
        unlimited stream: at most MAX_HINTS hints per question, and the explanation needs >= 1 hint first.
        Viewing the explanation ends the question with a score of 0. No AI call (hints are pre-generated).
        """
        session = self._get_owned_session(db, session_id=session_id, user_id=user_id)
        if not session.get("mode"):
            raise HintLimitError("Hints aren't available for this session.", code="HINTS_UNAVAILABLE")
        self._ensure_open(db, session)
        question = next((q for q in session["questions"] if q["question_id"] == question_id), None)
        if question is None:
            raise QuestionNotFoundError(question_id)
        if not question.get("hints"):
            raise HintLimitError("Hints aren't available for this question.", code="HINTS_UNAVAILABLE")

        qid = question_id
        count = (session.get("hint_counts") or {}).get(qid, 0)
        open_filter = {
            "_id": session["_id"], "status": "in_progress",
            f"answers.{qid}": {"$exists": False}, f"pending.{qid}": {"$exists": False},
        }
        collection = db[Collections.PRACTICE_SESSIONS]

        if reveal:
            if count < 1:
                raise HintLimitError(
                    "Request at least one hint before viewing the explanation.", code="HINT_REQUIRED"
                )
            record = {
                "answer": "", "score": 0, "raw_score": 0, "correct": False, "revealed": True,
                "hints_used": count, "feedback": (
                    "You viewed the explanation before answering, so this question counts as 0. "
                    "Review it, then try a similar one."
                ),
                "missing_points": [], "strengths": [], "improvement": None, "dimension_scores": None,
                "answered_at": datetime.now(timezone.utc),
            }
            res = collection.update_one(
                {**open_filter, f"hint_counts.{qid}": count}, {"$set": {f"answers.{qid}": record}}
            )
            if res.matched_count == 0:
                raise AnswerAlreadySubmittedError(qid)
            return {"kind": "explanation", "hints_used": count, "hints_remaining": 0,
                    "result": self._result_dict(question, record)}

        if count >= engine.MAX_HINTS:
            raise HintLimitError(
                "You've used all the hints for this question. You can view the explanation.",
                code="HINT_LIMIT_REACHED",
            )
        updated = collection.find_one_and_update(
            {**open_filter, f"hint_counts.{qid}": {"$lt": engine.MAX_HINTS}},
            {"$inc": {f"hint_counts.{qid}": 1}},
            return_document=ReturnDocument.AFTER,
        )
        if updated is None:
            latest = self._get_owned_session(db, session_id=session_id, user_id=user_id)
            if qid in (latest.get("answers") or {}) or qid in (latest.get("pending") or {}):
                raise AnswerAlreadySubmittedError(qid)
            raise HintLimitError("No more hints are available for this question.", code="HINT_LIMIT_REACHED")
        n = updated["hint_counts"][qid]
        return {
            "kind": "hint",
            "hint_number": n,
            "hint": question["hints"][n - 1],
            "hints_used": n,
            "hints_remaining": engine.MAX_HINTS - n,
            "max_score": round(100 * engine.HINT_MULTIPLIERS[n]),
        }

    # ----------------------------------------------------------------- answers
    async def _submit_advanced_answer(
        self, db: Database, *, session: dict, question: dict, answer: str
    ) -> AnswerResult:
        self._ensure_open(db, session, grace_seconds=engine.ANSWER_GRACE_SECONDS)
        qid = question["question_id"]
        collection = db[Collections.PRACTICE_SESSIONS]

        # Claim the question: exactly one in-flight/finished submission per question, which also
        # stops a double-click from paying for two Gemini evaluations. Hints freeze once claimed.
        stale = time.time() - PENDING_TTL_SECONDS
        claimed = collection.find_one_and_update(
            {
                "_id": session["_id"], "status": "in_progress", f"answers.{qid}": {"$exists": False},
                "$or": [{f"pending.{qid}": {"$exists": False}}, {f"pending.{qid}": {"$lt": stale}}],
            },
            {"$set": {f"pending.{qid}": time.time()}},
            return_document=ReturnDocument.AFTER,
        )
        if claimed is None:
            raise AnswerAlreadySubmittedError(qid)
        hints_used = (claimed.get("hint_counts") or {}).get(qid, 0)

        try:
            if question["type"] == "multiple_choice":
                correct_answer = (question.get("correct_answer") or "").strip()
                is_correct = answer.strip().lower() == correct_answer.lower()
                raw = 100 if is_correct else 0
                evaluation = {
                    "raw_score": raw, "correct": is_correct, "dimension_scores": None,
                    "feedback": "Correct!" if is_correct else f"Not quite — the correct answer is: {correct_answer}",
                    "strengths": [], "missing_points": [], "improvement": None,
                }
            else:
                evaluation = await self._evaluate_free_text(question, answer)
        except Exception:
            collection.update_one({"_id": session["_id"]}, {"$unset": {f"pending.{qid}": ""}})
            raise

        final = engine.apply_hint_penalty(evaluation["raw_score"], hints_used)
        record = {
            "answer": answer,
            "score": final,
            "raw_score": evaluation["raw_score"],
            "hints_used": hints_used,
            "correct": evaluation["correct"],
            "feedback": evaluation["feedback"],
            "strengths": evaluation["strengths"],
            "missing_points": evaluation["missing_points"],
            "improvement": evaluation["improvement"],
            "dimension_scores": evaluation["dimension_scores"],
            "revealed": False,
            "answered_at": datetime.now(timezone.utc),
        }
        saved = collection.update_one(
            {"_id": session["_id"], "status": "in_progress"},
            {"$set": {f"answers.{qid}": record}, "$unset": {f"pending.{qid}": ""}},
        )
        if saved.matched_count == 0:  # the session was completed while we were evaluating
            raise SessionClosedError("This practice session is already complete.")

        return AnswerResult(
            score=final, correct=evaluation["correct"], feedback=evaluation["feedback"],
            ideal_answer=question.get("ideal_answer"), missing_points=evaluation["missing_points"],
            raw_score=evaluation["raw_score"], hints_used=hints_used,
            hint_penalty=evaluation["raw_score"] - final, dimension_scores=evaluation["dimension_scores"],
            strengths=evaluation["strengths"], improvement=evaluation["improvement"],
            explanation=question.get("explanation"), ideal_steps=question.get("ideal_steps"),
        )

    async def _evaluate_free_text(self, question: dict, answer: str) -> dict:
        prompt = build_evaluation_prompt(
            question=question["question"],
            question_type=question["type"],
            difficulty=question.get("difficulty") or "intermediate",
            expected_concepts=question.get("expected_concepts") or [],
            reference=question.get("ideal_answer") or "",
            user_answer=answer,
        )
        try:
            result = await self._ai_service.generate_response(
                user_message=prompt, system_prompt=EVALUATION_SYSTEM_PROMPT
            )
            return engine.validate_generated_evaluation(engine.parse_json_object(result.text))
        except AIServiceError as exc:
            logger.error("Advanced answer evaluation failed: %s", type(exc).__name__)
            raise AnswerEvaluationError("AI provider failed to evaluate the answer.") from exc
        except (ValueError, ValidationError) as exc:
            logger.warning("Invalid evaluation data: %s", type(exc).__name__)
            raise AnswerEvaluationError("AI returned an unusable evaluation.") from exc

    # -------------------------------------------------------------- completion
    def _build_advanced_result(self, session: dict) -> dict:
        score = session.get("score")
        started, completed = _as_utc(session.get("started_at")), _as_utc(session.get("completed_at"))
        questions = session.get("questions") or []
        answers = session.get("answers") or {}
        outcome = engine.summarize_session(session)
        return {
            "session_id": str(session["_id"]),
            "mode": session.get("mode"),
            "score": score if score is not None else 0,
            "scored": score is not None,
            "questions_total": len(session.get("plan") or questions),
            "questions_answered": session.get("questions_answered") or 0,
            "correct_answers": session.get("correct_answers") or 0,
            "needs_improvement": outcome["needs_improvement"],
            "hints_used": session.get("hints_used_total", outcome["hints_used"]),
            "topic_title": session["topic_title"],
            "category": session["category"],
            "categories": session.get("categories") or [session["category"]],
            "difficulty": session.get("difficulty"),
            "difficulty_mode": session.get("difficulty_mode") or "fixed",
            "strong_areas": session.get("strong_areas", outcome["strong_areas"]),
            "needs_work": session.get("needs_work", outcome["needs_work"]),
            "weak_areas": session.get("weak_areas", []),
            "recommendations": session.get("recommendations", []),
            "recommended_next": session.get("recommended_next"),
            "duration_seconds": int((completed - started).total_seconds()) if started and completed else None,
            "timed_out": bool(session.get("timed_out")),
            "unanswered": max(0, len(session.get("plan") or questions) - len(answers)),
        }

    def _complete_advanced_session(self, db: Database, *, session: dict) -> dict:
        """Idempotent. Writes the same fields Step 5 does, so Progress/Personalization/History just work."""
        if session.get("status") == "completed":
            return self._build_advanced_result(session)

        outcome = engine.summarize_session(session)
        now = datetime.now(timezone.utc)
        deadline = self._deadline(session)
        recommendations = [f"Review {title} and try again." for title in outcome["needs_work"][:2]]
        fields = {
            "status": "completed",
            "completed_at": now,
            "score": outcome["score"],
            "questions_answered": outcome["questions_answered"],
            "correct_answers": outcome["correct_answers"],
            "weak_areas": outcome["weak_categories"],
            "recommendations": recommendations,
            "category_results": outcome["category_results"],
            "topic_slugs": outcome["topic_slugs"],
            "hints_used_total": outcome["hints_used"],
            "strong_areas": outcome["strong_areas"],
            "needs_work": outcome["needs_work"],
            "timed_out": bool(deadline and now > deadline),
        }
        if outcome["label_category"]:
            fields["category"] = outcome["label_category"]
            fields["categories"] = outcome["categories"]
        if session.get("difficulty_mode") == "adaptive" and outcome["modal_difficulty"]:
            fields["difficulty"] = outcome["modal_difficulty"]  # the level the session actually ran at

        collection = db[Collections.PRACTICE_SESSIONS]
        done = collection.update_one({"_id": session["_id"], "status": "in_progress"}, {"$set": fields})
        latest = collection.find_one({"_id": session["_id"]})
        if done.matched_count == 0:  # someone else completed it first
            return self._build_advanced_result(latest)

        user_id = str(session["user_id"])
        invalidate_user(user_id)  # the AI mentor's cached personalization is now stale
        recommended = self._recommend_next(db, user_id=user_id, outcome=outcome)
        collection.update_one({"_id": session["_id"]}, {"$set": {"recommended_next": recommended}})
        latest["recommended_next"] = recommended
        return self._build_advanced_result(latest)

    def _recommend_next(self, db: Database, *, user_id: str, outcome: dict) -> dict | None:
        """"What should I practice next?" -- Step 16's recommendation, never a separate engine."""
        user = self._load_user(db, user_id)
        if user is not None:
            try:
                recs = self._personalization.get_recommendations(db, user=user)["recommendations"]
                top = next((r for r in recs if r["type"] == "practice"), None)
                if top:
                    return {
                        "title": top["title"],
                        "topic": top["topic"],
                        "topic_slug": top.get("topic_slug"),
                        "difficulty": top.get("difficulty"),
                        "reasons": list(top.get("reasons", []))[:2],
                        "basis": top.get("basis"),
                        "source": "personalization",
                    }
            except Exception:  # noqa: BLE001
                logger.warning("Could not load personalized next step", exc_info=True)
        if outcome["needs_work"]:
            return {
                "title": f"Practice {outcome['needs_work'][0]} again",
                "topic": outcome["needs_work"][0], "topic_slug": None, "difficulty": None,
                "reasons": ["It was your weakest area in this session."], "basis": "session",
                "source": "session",
            }
        return None
