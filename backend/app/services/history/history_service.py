"""
History & Activity Center service (Step 15).

A read/aggregation layer over the session collections that already exist --
nothing is copied into a "history" collection, so history can never drift out
of sync with the sessions it describes:

    practice_sessions, ctf_sessions, communication_sessions,
    interview_sessions, pressure_sessions, voice_conversation_sessions

Mentor chats are *not* included: the AI Mentor is stateless and never stores
conversations (see `app.api.routes.mentor`), so there is nothing to show.
Adding a source later is one more entry in `_SOURCES`.

Listing
-------
Each source is queried with the user's filters pushed down to MongoDB, sorted
by its own start date (covered by the existing `(user_id, started_at)` /
`(user_id, created_at)` indexes) and limited to `page * limit` rows. Those
small, projected rows (never message/answer arrays) are merged and sliced.
That is a bounded k-way merge: no skip over large collections, no per-row
follow-up queries, and `total` comes from one `count_documents` per source.
`MAX_WINDOW` bounds how deep a merged page may reach; use search or the date
filter to narrow beyond it.

Detail
------
Opening an activity reuses each module's existing `get_session` serializer, so
what is exposed is exactly what that module already shows its owner (mid-
session feedback stays hidden, evaluator-internal fields stay internal).
Practice is the one module without such a serializer; `_practice_detail`
mirrors what the practice flow already reveals after an answer is submitted.

Ownership
---------
`user_id` always comes from the verified JWT. Every query is scoped with it, and
detail lookups match `_id` AND `user_id` together, so a session that belongs to
someone else is indistinguishable from one that does not exist (404 either way).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Literal

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ASCENDING, DESCENDING
from pymongo.database import Database

from app.db.collections import Collections
from app.schemas.history import (
    ActivityType,
    HistoryActivity,
    HistoryListResponse,
    HistorySummaryResponse,
    HistoryTypeCount,
)
from app.services.communication import communication_service as _communication_module
from app.services.communication.communication_service import (
    CommunicationService,
    communication_service,
)
from app.services.cybersecurity import ctf_service as _ctf_module
from app.services.cybersecurity.ctf_service import CtfService, ctf_service
from app.services.interview import interview_service as _interview_module
from app.services.interview.interview_service import InterviewService, interview_service
from app.services.interview.topics import INTERVIEW_TYPE_LABELS
from app.services.pressure import pressure_service as _pressure_module
from app.services.pressure.pressure_service import PressureService, pressure_service
from app.services.voice_conversation import session_manager as _voice_session_module
from app.services.voice_conversation.conversation_service import (
    VoiceConversationService,
    voice_conversation_service,
)
from app.services.voice_conversation.session_manager import MODE_LABELS as VOICE_MODE_LABELS

# Each module defines its own not-found / wrong-owner errors. History maps all of them to one
# ActivityNotFoundError so another user's ids can't be told apart from missing ones.
_MODULE_LOOKUP_ERRORS: tuple[type[Exception], ...] = tuple(
    err
    for module in (
        _communication_module,
        _ctf_module,
        _interview_module,
        _pressure_module,
        _voice_session_module,
    )
    for err in (module.SessionNotFoundError, module.SessionForbiddenError)
)

SortOrder = Literal["newest", "oldest"]

MAX_LIMIT = 50
# Upper bound for `page * limit` on a merged page (see module docstring).
MAX_WINDOW = 1_000
# A session left open overnight would report a meaningless "duration", so
# elapsed times above this are treated as unknown rather than shown.
MAX_ELAPSED_SECONDS = 6 * 60 * 60

_ACRONYMS = {"ctf": "CTF", "osint": "OSINT", "hr": "HR", "soc": "SOC", "siem": "SIEM"}
_STATUS = {
    "completed": "completed",
    "abandoned": "abandoned",
    "in_progress": "in_progress",
    "created": "in_progress",  # voice: not started yet
    "active": "in_progress",  # voice: in progress
}


# --- Errors ---------------------------------------------------------------------------------


class HistoryError(Exception):
    """Base class for history errors."""


class ActivityNotFoundError(HistoryError):
    """Missing, malformed id, or owned by another user -- deliberately indistinguishable."""


class PageOutOfRangeError(HistoryError):
    """The requested page reaches deeper than MAX_WINDOW allows."""


class InvalidDateRangeError(HistoryError):
    """start_date is after end_date."""


# --- Small helpers ----------------------------------------------------------------------------


def _utc(value: datetime | None) -> datetime | None:
    """MongoDB returns naive UTC datetimes; make them explicit so clients parse them correctly."""
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _naive_utc(value: datetime) -> datetime:
    """Datetimes are stored naive-UTC; convert query bounds to match."""
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _elapsed(start: datetime | None, end: datetime | None) -> int | None:
    start, end = _utc(start), _utc(end)
    if start is None or end is None:
        return None
    seconds = int((end - start).total_seconds())
    return seconds if 0 <= seconds <= MAX_ELAPSED_SECONDS else None


def _score(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return int(round(value))


def _status(value: object) -> str:
    return _STATUS.get(value, "in_progress") if isinstance(value, str) else "in_progress"


def _humanize(value: object) -> str | None:
    """'web_security' -> 'Web Security', 'ctf' -> 'CTF'. Leaves already-readable text alone."""
    if not isinstance(value, str) or not value.strip():
        return None
    words = re.split(r"[_\s-]+", value.strip())
    return " ".join(_ACRONYMS.get(w.lower(), w if w[:1].isupper() else w.capitalize()) for w in words)


def _join(*parts: str | None) -> str | None:
    text = " · ".join(p for p in parts if p)
    return text or None


def _nested(doc: dict, *path: str) -> object:
    current: object = doc
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


# --- Per-collection normalizers (docs are already projected to the fields used) -----------


def _practice(doc: dict) -> HistoryActivity:
    started, completed = _utc(doc["started_at"]), _utc(doc.get("completed_at"))
    status = _status(doc.get("status"))
    return HistoryActivity(
        id=str(doc["_id"]),
        type="cybersecurity_practice",
        type_label="Cybersecurity Practice",
        title=doc.get("topic_title") or "Cybersecurity practice",
        description=_join(doc.get("category"), _humanize(doc.get("difficulty"))),
        created_at=started,
        updated_at=completed,
        completed_at=completed,
        duration_seconds=_elapsed(started, completed),
        score=_score(doc.get("score")) if status == "completed" else None,
        status=status,
        metadata={
            "category": doc.get("category"),
            "difficulty": doc.get("difficulty"),
            "questions_answered": doc.get("questions_answered"),
            "correct_answers": doc.get("correct_answers"),
        },
    )


def _ctf(doc: dict) -> HistoryActivity:
    created, completed = _utc(doc["created_at"]), _utc(doc.get("completed_at"))
    return HistoryActivity(
        id=str(doc["_id"]),
        type="ctf",
        type_label="CTF & Labs",
        title=doc.get("title") or "CTF challenge",
        description=_join(doc.get("platform"), _humanize(doc.get("category"))),
        created_at=created,
        updated_at=_utc(doc.get("updated_at")),
        completed_at=completed,
        duration_seconds=_elapsed(created, completed),
        score=None,  # CTF sessions have no numeric score
        status=_status(doc.get("status")),
        metadata={
            "platform": doc.get("platform"),
            "category": doc.get("category"),
            "difficulty": doc.get("difficulty"),
            "hints_used": doc.get("hints_used", 0),
        },
    )


def _communication(doc: dict) -> HistoryActivity:
    started, completed = _utc(doc["started_at"]), _utc(doc.get("completed_at"))
    return HistoryActivity(
        id=str(doc["_id"]),
        type="communication",
        type_label="Communication",
        title=doc.get("scenario_title") or "Communication practice",
        description=_join(_humanize(doc.get("mode")), _humanize(doc.get("category"))),
        created_at=started,
        updated_at=_utc(doc.get("updated_at")),
        completed_at=completed,
        duration_seconds=_elapsed(started, completed),
        score=_score(_nested(doc, "evaluation", "overall_score")),
        status=_status(doc.get("status")),
        metadata={
            "mode": doc.get("mode"),
            "category": doc.get("category"),
            "difficulty": doc.get("difficulty"),
        },
    )


def _interview(doc: dict) -> HistoryActivity:
    started, completed = _utc(doc["started_at"]), _utc(doc.get("completed_at"))
    itype = doc.get("interview_type")
    label = INTERVIEW_TYPE_LABELS.get(itype, _humanize(itype) or "Cybersecurity")
    return HistoryActivity(
        id=str(doc["_id"]),
        type="interview",
        type_label="Interview",
        title=f"{label} Interview",
        description=_join(
            _humanize(doc.get("difficulty")),
            f"{_humanize(doc['mode'])} answers" if doc.get("mode") else None,
        ),
        created_at=started,
        updated_at=_utc(doc.get("updated_at")),
        completed_at=completed,
        duration_seconds=_elapsed(started, completed),
        score=_score(_nested(doc, "final_evaluation", "overall_score")),
        status=_status(doc.get("status")),
        metadata={
            "interview_type": itype,
            "difficulty": doc.get("difficulty"),
            "mode": doc.get("mode"),
            "question_count": doc.get("question_count"),
        },
    )


def _pressure(doc: dict) -> HistoryActivity:
    started, completed = _utc(doc["started_at"]), _utc(doc.get("completed_at"))
    level = doc.get("pressure_level")
    return HistoryActivity(
        id=str(doc["_id"]),
        type="pressure_training",
        type_label="Pressure Training",
        title=f"Pressure Training · Level {level}" if level else "Pressure Training",
        description=_join(_humanize(doc.get("mode")), _humanize(doc.get("difficulty"))),
        created_at=started,
        updated_at=_utc(doc.get("updated_at")),
        completed_at=completed,
        duration_seconds=_elapsed(started, completed),
        score=_score(_nested(doc, "final_evaluation", "overall_score")),
        status=_status(doc.get("status")),
        metadata={
            "pressure_level": level,
            "mode": doc.get("mode"),
            "interview_type": doc.get("interview_type"),
            "difficulty": doc.get("difficulty"),
            "question_count": doc.get("question_count"),
        },
    )


def _voice(doc: dict) -> HistoryActivity:
    started, ended = _utc(doc["started_at"]), _utc(doc.get("ended_at"))
    mode_label = VOICE_MODE_LABELS.get(doc.get("mode"), _humanize(doc.get("mode")) or "Voice conversation")
    summary = doc.get("summary") or {}
    # The summary's duration is measured when the conversation ends; fall back to start->end.
    recorded = summary.get("duration_seconds")
    duration = (
        int(recorded)
        if isinstance(recorded, (int, float)) and not isinstance(recorded, bool) and 0 <= recorded <= MAX_ELAPSED_SECONDS
        else _elapsed(started, ended)
    )
    return HistoryActivity(
        id=str(doc["_id"]),
        type="voice_conversation",
        type_label="Voice Conversation",
        title=doc.get("topic") or mode_label,
        description=_join(mode_label if doc.get("topic") else None, _humanize(doc.get("difficulty"))),
        created_at=started,
        updated_at=_utc(doc.get("last_activity_at")),
        completed_at=ended if _status(doc.get("status")) == "completed" else None,
        duration_seconds=duration,
        score=_score(_nested(summary, "evaluation", "overall_score")),
        status=_status(doc.get("status")),
        metadata={
            "mode": doc.get("mode"),
            "mode_label": mode_label,
            "difficulty": doc.get("difficulty"),
            "turn_count": doc.get("turn_count", 0),
            "answer_count": doc.get("user_turn_count", 0),
            "linked_session_kind": _nested(doc, "linked", "kind"),
        },
    )


@dataclass(frozen=True)
class _Source:
    type: ActivityType
    label: str
    collection: str
    date_field: str  # the field this activity is sorted/filtered by (indexed with user_id)
    search_fields: tuple[str, ...]
    keywords: tuple[str, ...]  # words from the displayed title that search should also match
    projection: dict
    normalize: Callable[[dict], HistoryActivity]


_COMMON = {"status": 1, "updated_at": 1, "completed_at": 1}

_SOURCES: tuple[_Source, ...] = (
    _Source(
        "cybersecurity_practice", "Cybersecurity Practice", Collections.PRACTICE_SESSIONS, "started_at",
        ("topic_title", "category", "topic_slug"), ("cybersecurity practice",),
        {"topic_title": 1, "category": 1, "difficulty": 1, "status": 1, "started_at": 1,
         "completed_at": 1, "score": 1, "questions_answered": 1, "correct_answers": 1},
        _practice,
    ),
    _Source(
        "ctf", "CTF & Labs", Collections.CTF_SESSIONS, "created_at",
        ("title", "category", "platform"), ("ctf labs", "lab"),
        {**_COMMON, "title": 1, "platform": 1, "category": 1, "difficulty": 1, "created_at": 1, "hints_used": 1},
        _ctf,
    ),
    _Source(
        "communication", "Communication", Collections.COMMUNICATION_SESSIONS, "started_at",
        ("scenario_title", "category", "mode"), ("communication",),
        {**_COMMON, "scenario_title": 1, "category": 1, "mode": 1, "difficulty": 1, "started_at": 1,
         "evaluation.overall_score": 1},
        _communication,
    ),
    _Source(
        "interview", "Interview", Collections.INTERVIEW_SESSIONS, "started_at",
        ("interview_type", "difficulty"), ("interview",),
        {**_COMMON, "interview_type": 1, "difficulty": 1, "mode": 1, "question_count": 1, "started_at": 1,
         "final_evaluation.overall_score": 1},
        _interview,
    ),
    _Source(
        "pressure_training", "Pressure Training", Collections.PRESSURE_SESSIONS, "started_at",
        ("interview_type", "mode", "difficulty"), ("pressure training",),
        {**_COMMON, "pressure_level": 1, "mode": 1, "interview_type": 1, "difficulty": 1, "question_count": 1,
         "started_at": 1, "final_evaluation.overall_score": 1},
        _pressure,
    ),
    _Source(
        "voice_conversation", "Voice Conversation", Collections.VOICE_CONVERSATION_SESSIONS, "started_at",
        ("topic", "mode", "linked.label"), ("voice conversation",),
        {"status": 1, "topic": 1, "mode": 1, "difficulty": 1, "started_at": 1, "ended_at": 1,
         "last_activity_at": 1, "turn_count": 1, "user_turn_count": 1, "linked.kind": 1,
         "summary.duration_seconds": 1, "summary.evaluation.overall_score": 1},
        _voice,
    ),
)
_SOURCE_BY_TYPE = {s.type: s for s in _SOURCES}


# --- Search ----------------------------------------------------------------------------------


def _search_pattern(term: str) -> str:
    """
    Safe, case-insensitive pattern: every token is regex-escaped (no user-supplied regex), and
    whitespace/underscore/hyphen are interchangeable so "blue team" finds "blue_team".
    """
    tokens = [re.escape(t) for t in re.split(r"[\s_-]+", term.strip()) if t]
    return r"[\s_-]+".join(tokens)


def _matches_keyword(term: str, keywords: tuple[str, ...]) -> bool:
    """
    Lets "interview" or "voice" find every session of that type even though the word is part
    of the displayed title rather than a stored field. Needs 3+ characters and must start a word.
    """
    needle = term.strip().lower()
    if len(needle) < 3:
        return False
    return any(kw.startswith(needle) or any(w.startswith(needle) for w in kw.split()) for kw in keywords)


# --- Service ---------------------------------------------------------------------------------


class HistoryService:
    def __init__(
        self,
        *,
        interviews: InterviewService = interview_service,
        pressure: PressureService = pressure_service,
        communication: CommunicationService = communication_service,
        ctf: CtfService = ctf_service,
        voice: VoiceConversationService = voice_conversation_service,
    ) -> None:
        self._interviews = interviews
        self._pressure = pressure
        self._communication = communication
        self._ctf = ctf
        self._voice = voice

    # --- Query building --------------------------------------------------------------------

    @staticmethod
    def _query(
        source: _Source,
        uid: ObjectId,
        *,
        search: str | None,
        start_date: datetime | None,
        end_date: datetime | None,
    ) -> dict:
        query: dict = {"user_id": uid}  # ownership: always first, always from the JWT
        if start_date or end_date:
            bounds: dict = {}
            if start_date:
                bounds["$gte"] = _naive_utc(start_date)
            if end_date:
                bounds["$lte"] = _naive_utc(end_date)
            query[source.date_field] = bounds
        term = (search or "").strip()
        if term:
            if not _matches_keyword(term, source.keywords):
                pattern = _search_pattern(term)
                query["$or"] = [
                    {field: {"$regex": pattern, "$options": "i"}} for field in source.search_fields
                ]
            # else: the term names this activity type, so every session of the type matches.
        return query

    # --- Summary ---------------------------------------------------------------------------

    def get_summary(self, db: Database, *, user_id: str) -> HistorySummaryResponse:
        """All-time counts per activity type (drives the overview tiles and which filters exist)."""
        uid = ObjectId(user_id)
        types = [
            HistoryTypeCount(
                type=s.type, label=s.label, count=db[s.collection].count_documents({"user_id": uid})
            )
            for s in _SOURCES
        ]
        return HistorySummaryResponse(total=sum(t.count for t in types), types=types)

    # --- List ------------------------------------------------------------------------------

    def list_activities(
        self,
        db: Database,
        *,
        user_id: str,
        activity_type: ActivityType | None = None,
        search: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        page: int = 1,
        limit: int = 20,
        sort: SortOrder = "newest",
    ) -> HistoryListResponse:
        if start_date and end_date and _naive_utc(start_date) > _naive_utc(end_date):
            raise InvalidDateRangeError()

        uid = ObjectId(user_id)
        sources = [_SOURCE_BY_TYPE[activity_type]] if activity_type else list(_SOURCES)
        queries = {
            s.type: self._query(s, uid, search=search, start_date=start_date, end_date=end_date)
            for s in sources
        }
        counts = {s.type: db[s.collection].count_documents(queries[s.type]) for s in sources}
        total = sum(counts.values())

        offset = (page - 1) * limit
        if offset >= total:
            return HistoryListResponse(items=[], page=page, limit=limit, total=total, has_next=False)

        window = offset + limit
        if window > MAX_WINDOW:
            raise PageOutOfRangeError()

        direction = DESCENDING if sort == "newest" else ASCENDING
        merged: list[HistoryActivity] = []
        for source in sources:
            if counts[source.type] == 0:
                continue
            cursor = (
                db[source.collection]
                .find(queries[source.type], source.projection)
                .sort([(source.date_field, direction), ("_id", direction)])
                .limit(window)
            )
            merged.extend(source.normalize(doc) for doc in cursor)

        merged.sort(key=lambda a: (a.created_at, a.id), reverse=(sort == "newest"))
        items = merged[offset:window]
        return HistoryListResponse(
            items=items, page=page, limit=limit, total=total, has_next=offset + len(items) < total
        )

    # --- Detail ----------------------------------------------------------------------------

    def get_detail(
        self, db: Database, *, user_id: str, activity_type: ActivityType, activity_id: str
    ) -> tuple[HistoryActivity, dict]:
        source = _SOURCE_BY_TYPE[activity_type]
        try:
            oid = ObjectId(activity_id)
        except (InvalidId, TypeError) as exc:
            raise ActivityNotFoundError(activity_id) from exc

        # Ownership is part of the query itself: someone else's id simply isn't found.
        owned = {"_id": oid, "user_id": ObjectId(user_id)}
        doc = db[source.collection].find_one(owned, source.projection)
        if doc is None:
            raise ActivityNotFoundError(activity_id)
        activity = source.normalize(doc)

        if activity_type == "cybersecurity_practice":
            full = db[source.collection].find_one(owned)
            if full is None:
                raise ActivityNotFoundError(activity_id)
            return activity, _practice_detail(full)

        getters = {
            "interview": self._interviews.get_session,
            "pressure_training": self._pressure.get_session,
            "communication": self._communication.get_session,
            "ctf": self._ctf.get_session,
            "voice_conversation": self._voice.get_session,
        }
        # These re-check ownership themselves; their own not-found/forbidden errors are
        # collapsed to the same 404 so another user's ids can't be probed.
        try:
            detail = getters[activity_type](db, user_id=user_id, session_id=activity_id)
        except _MODULE_LOOKUP_ERRORS as exc:
            raise ActivityNotFoundError(activity_id) from exc
        return activity, detail


def _practice_detail(session: dict) -> dict:
    """
    Practice sessions have no public serializer, so this one reveals only what the practice flow
    already shows after an answer is submitted. Unanswered questions expose just the question,
    so a session that is still in progress can't be used to read ahead at the answers.
    """
    answers = session.get("answers") or {}
    questions = []
    for q in session.get("questions", []):
        record = answers.get(q["question_id"])
        item = {
            "question_id": q["question_id"],
            "question": q["question"],
            "type": q.get("type"),
            "options": q.get("options"),
            "answered": record is not None,
            # Step 17 sessions only (None for Step 5): where the question sat and how much help was used.
            "topic_title": q.get("topic_title"),
            "difficulty": q.get("difficulty"),
        }
        if record is not None:
            item.update(
                answer=record.get("answer"),
                correct=record.get("correct"),
                score=record.get("score"),
                feedback=record.get("feedback"),
                missing_points=record.get("missing_points", []),
                ideal_answer=q.get("ideal_answer"),
                explanation=q.get("explanation"),
                ideal_steps=q.get("ideal_steps"),
                strengths=record.get("strengths", []),
                hints_used=record.get("hints_used", 0),
                revealed=bool(record.get("revealed")),
            )
        questions.append(item)

    return {
        "session_id": str(session["_id"]),
        "topic_slug": session.get("topic_slug"),
        "topic_title": session.get("topic_title"),
        "category": session.get("category"),
        "difficulty": session.get("difficulty"),
        "status": session.get("status"),
        "started_at": _utc(session.get("started_at")).isoformat() if session.get("started_at") else None,
        "completed_at": _utc(session.get("completed_at")).isoformat() if session.get("completed_at") else None,
        "score": session.get("score"),
        "question_count": len(session.get("questions", [])),
        "questions_answered": session.get("questions_answered"),
        "correct_answers": session.get("correct_answers"),
        "weak_areas": session.get("weak_areas", []),
        "recommendations": session.get("recommendations", []),
        "questions": questions,
        # Step 17 sessions only.
        "mode": session.get("mode"),
        "categories": session.get("categories") or [],
        "difficulty_mode": session.get("difficulty_mode"),
        "hints_used": session.get("hints_used_total"),
        "strong_areas": session.get("strong_areas") or [],
        "needs_work": session.get("needs_work") or [],
        "recommended_next": session.get("recommended_next"),
    }


history_service = HistoryService()
