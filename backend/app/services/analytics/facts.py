"""
Loads existing session documents and reduces them to compact in-memory "facts".

This is the only module that reads the database. Nothing is written back and
nothing is copied into a new collection: facts live for the duration of one
request. Reads are scoped to `user_id` (taken from the JWT by the route),
filtered to completed sessions inside the date range, and bounded to the
newest `MAX_SESSIONS_PER_SOURCE` per collection using the existing
(user_id, started_at) indexes.

Voice conversations are NOT read separately: they wrap Step 7/9/10 sessions
(`linked`), whose answers already carry the voice metrics. Reading both would
count every spoken answer twice.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from bson import ObjectId
from pymongo import DESCENDING
from pymongo.database import Database

from app.db.collections import Collections
from app.services.analytics import config
from app.services.analytics.answer_analytics import classify_length, structure_markers
from app.services.analytics.common import DateRange, as_utc
from app.services.cybersecurity.practice_results import session_category_entries
from app.services.interview.topics import TOPICS
from app.utils.text_analysis import count_words

_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


@dataclass
class Facts:
    interviews: list[dict] = field(default_factory=list)    # oldest -> newest
    pressure: list[dict] = field(default_factory=list)
    communication: list[dict] = field(default_factory=list)
    practice: list[dict] = field(default_factory=list)      # one row per (session, category)
    truncated: bool = False

    @property
    def total_sessions(self) -> int:
        return len(self.interviews) + len(self.pressure) + len(self.communication)


def _voice_sample(analysis: dict | None) -> dict | None:
    """Reduce a stored Step 8 `voice_analysis` to the few numbers analytics needs."""
    if not analysis:
        return None
    words = analysis.get("word_count")
    if not words:
        return None
    return {
        "words": words,
        "duration": analysis.get("duration_seconds"),
        "wpm": analysis.get("speaking_rate_wpm"),
        "fillers": analysis.get("total_filler_words"),
        "filler_rate": analysis.get("filler_rate_per_100_words"),
        "repeats": analysis.get("total_repeated_words"),
        "pauses": analysis.get("pause_count"),          # None => not measurable
        "long_pauses": analysis.get("long_pauses"),
        "avg_pause": analysis.get("average_pause_seconds"),
        "sentence_len": analysis.get("average_sentence_length"),
    }


def _answer_fact(record: dict, *, topic: str, is_follow_up: bool, main_technical: int | None) -> dict | None:
    tech = record.get("technical_evaluation")
    comm = record.get("communication_evaluation")
    if not record.get("answer") or not tech:
        return None
    kind = TOPICS[topic].kind if topic in TOPICS else "technical"
    voice = _voice_sample(record.get("voice_analysis")) if record.get("answer_input_type") == "voice" else None
    text_metrics = record.get("text_metrics") or {}
    words = (
        (record.get("voice_analysis") or {}).get("word_count")
        if voice else None
    ) or text_metrics.get("word_count") or count_words(record["answer"])
    return {
        "topic": topic,
        "kind": kind,
        "is_follow_up": is_follow_up,
        "technical": tech.get("technical_score"),
        "accuracy": tech.get("accuracy"),
        "completeness": tech.get("completeness"),
        "depth": tech.get("depth"),
        "communication": (comm or {}).get("communication_score"),
        "clarity": (comm or {}).get("clarity"),
        "grammar": (comm or {}).get("grammar"),
        "vocabulary": (comm or {}).get("vocabulary"),
        "structure": (comm or {}).get("structure"),
        "conciseness": (comm or {}).get("conciseness"),
        "words": words,
        "length": classify_length(words, kind),
        "markers": structure_markers(record["answer"], kind, words),
        "input": "voice" if voice else "text",
        "voice": voice,
        "main_technical": main_technical,
        "duration": record.get("response_duration_seconds"),
        "timed_out": bool(record.get("timed_out")),
    }


def _qa_session_fact(doc: dict, kind: str) -> dict | None:
    final = doc.get("final_evaluation") or {}
    if final.get("overall_score") is None:
        return None
    answers: list[dict] = []
    for q in doc.get("questions", []):
        main = _answer_fact(q, topic=q.get("topic", ""), is_follow_up=False, main_technical=None)
        if main:
            answers.append(main)
        main_score = main["technical"] if main else None
        for fu in q.get("follow_up_questions", []):
            fact = _answer_fact(fu, topic=q.get("topic", ""), is_follow_up=True, main_technical=main_score)
            if fact:
                answers.append(fact)
    planned = doc.get("question_count") or 0
    answered = final.get("answered_questions")
    return {
        "kind": kind,
        "at": as_utc(doc.get("completed_at") or doc.get("started_at")),
        "type": "pressure" if kind == "pressure" else doc.get("interview_type", "mixed"),
        "interview_type": doc.get("interview_type"),
        "difficulty": doc.get("difficulty"),
        "pressure_level": doc.get("pressure_level"),
        "overall": final.get("overall_score"),
        "technical": final.get("technical_score"),
        "communication": final.get("communication_score"),
        "pressure_handling": final.get("pressure_handling_score"),
        "response_control": final.get("response_control_score"),
        "topic_scores": final.get("topic_scores") or [],
        "completion": round(answered / planned, 2) if planned and answered is not None else None,
        "answers": answers,
    }


def _communication_fact(doc: dict) -> dict | None:
    ev = doc.get("evaluation") or {}
    if ev.get("overall_score") is None:
        return None
    messages = []
    for m in doc.get("messages", []):
        if m.get("role") != "user" or not m.get("content"):
            continue
        voice = _voice_sample(m.get("voice_analysis")) if m.get("input_type") == "voice" else None
        words = count_words(m["content"])
        messages.append({"words": words, "voice": voice, "input": "voice" if voice else "text"})
    return {
        "kind": "communication",
        "at": as_utc(doc.get("completed_at") or doc.get("started_at")),
        "mode": doc.get("mode"),
        "difficulty": doc.get("difficulty"),
        "overall": ev.get("overall_score"),
        "clarity": ev.get("clarity_score"),
        "grammar": ev.get("grammar_score"),
        "vocabulary": ev.get("vocabulary_score"),
        "professionalism": ev.get("professionalism_score"),
        "confidence": ev.get("confidence_score"),
        "relevance": ev.get("relevance_score"),
        "flow": ev.get("conversation_flow_score"),
        "voice_summary_conciseness": (ev.get("voice_summary") or {}).get("conciseness_score"),
        "messages": messages,
    }


def _query(user_id: str, window: DateRange) -> dict:
    query: dict = {"user_id": ObjectId(user_id), "status": "completed"}
    if window.start is not None:
        query["started_at"] = {"$gte": window.start, "$lte": window.end}
    else:
        query["started_at"] = {"$lte": window.end}
    return query


def _fetch(db: Database, collection: str, query: dict, projection: dict) -> tuple[list[dict], bool]:
    limit = config.MAX_SESSIONS_PER_SOURCE
    docs = list(db[collection].find(query, projection).sort("started_at", DESCENDING).limit(limit + 1))
    truncated = len(docs) > limit
    docs = docs[:limit]
    docs.reverse()   # oldest -> newest
    return docs, truncated


def load_facts(db: Database, *, user_id: str, window: DateRange) -> Facts:
    """Collect the user's completed-session facts for `window` (all reads are user-scoped)."""
    query = _query(user_id, window)
    out = Facts()

    docs, t1 = _fetch(db, Collections.INTERVIEW_SESSIONS, query, {
        "interview_type": 1, "difficulty": 1, "question_count": 1, "started_at": 1,
        "completed_at": 1, "final_evaluation": 1, "questions": 1,
    })
    out.interviews = [f for d in docs if (f := _qa_session_fact(d, "interview"))]

    docs, t2 = _fetch(db, Collections.PRESSURE_SESSIONS, query, {
        "interview_type": 1, "difficulty": 1, "pressure_level": 1, "question_count": 1,
        "started_at": 1, "completed_at": 1, "final_evaluation": 1, "questions": 1,
    })
    out.pressure = [f for d in docs if (f := _qa_session_fact(d, "pressure"))]

    docs, t3 = _fetch(db, Collections.COMMUNICATION_SESSIONS, query, {
        "mode": 1, "difficulty": 1, "started_at": 1, "completed_at": 1, "evaluation": 1, "messages": 1,
    })
    out.communication = [f for d in docs if (f := _communication_fact(d))]

    docs, t4 = _fetch(db, Collections.PRACTICE_SESSIONS, {**query, "score": {"$ne": None}}, {
        "category": 1, "score": 1, "questions_answered": 1, "correct_answers": 1, "difficulty": 1,
        "started_at": 1, "completed_at": 1, "topic_slug": 1, "category_results": 1,
    })
    for d in docs:
        at = as_utc(d.get("completed_at") or d.get("started_at"))
        for entry in session_category_entries(d):
            out.practice.append({**entry, "at": at, "difficulty": d.get("difficulty")})

    out.truncated = t1 or t2 or t3 or t4
    return out


def all_answers(sessions: list[dict]) -> list[dict]:
    return [a for s in sessions for a in s["answers"]]


def spoken_samples(facts: Facts) -> list[dict]:
    """Every spoken answer/message with its timestamp and whether it was under pressure."""
    samples: list[dict] = []
    for s in facts.interviews + facts.pressure:
        for a in s["answers"]:
            if a["voice"]:
                samples.append({**a["voice"], "at": s["at"], "pressure": s["kind"] == "pressure"})
    for s in facts.communication:
        for m in s["messages"]:
            if m["voice"]:
                samples.append({**m["voice"], "at": s["at"], "pressure": False})
    samples.sort(key=lambda x: x["at"] or _EPOCH)
    return samples
