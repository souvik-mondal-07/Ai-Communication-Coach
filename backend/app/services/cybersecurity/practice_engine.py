"""
Advanced practice engine -- pure logic (Step 17).

Everything here is deterministic and free of I/O (no MongoDB, no Gemini), so it
is cheap to test and nothing in this module can trigger an AI call:

* session configuration limits and the mode / question-type vocabulary
* planning: which categories/topics/question types a session covers, using the
  Step 16 personalization output (never hard-coded weaknesses)
* gradual adaptive difficulty (never a jump from a single answer)
* hint penalty and the weighted overall score
* validation of untrusted, AI-generated question / evaluation JSON
* turning a finished session into a summary + per-category results

`PracticeService` (practice_service.py) wires these to MongoDB and the existing
`AIService`.
"""

from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.services.cybersecurity.practice_results import MIXED_CATEGORY
from app.services.personalization.recommendation_service import (
    LEVELS,
    choose_difficulty,
    interest_categories,
)
from app.services.progress.aggregation_service import (
    STRONG_SCORE_THRESHOLD,
    WEAK_SCORE_THRESHOLD,
)
from app.utils.helpers import parse_json_object  # noqa: F401 - re-exported: the project's one JSON-object parser

# --- Vocabulary & limits -------------------------------------------------------

DIFFICULTY_CHOICES = (*LEVELS, "adaptive")
MODES = ("personalized", "topic", "random", "weakness", "scenario", "troubleshooting", "interview")
QUESTION_TYPES = ("multiple_choice", "short_answer", "scenario", "troubleshooting", "command")
TYPE_CHOICES = ("mixed", *QUESTION_TYPES)
FREE_TEXT_TYPES = frozenset({"short_answer", "scenario", "troubleshooting", "command"})

MIN_QUESTIONS = 1
MAX_QUESTIONS = 10
DEFAULT_QUESTIONS = 5
MIN_TIME_LIMIT_MINUTES = 5
MAX_TIME_LIMIT_MINUTES = 60
MAX_HINTS = 3
# Answers sent just after the timer hits zero (the client auto-submits the draft
# it was holding) are still accepted for this long, so nothing typed is lost.
ANSWER_GRACE_SECONDS = 45

PASS_THRESHOLD = WEAK_SCORE_THRESHOLD  # >= 60 counts as "correct / strong enough"
STRONG_THRESHOLD = STRONG_SCORE_THRESHOLD

# Categories where a "which command would you use" task is meaningful, and the
# one category where a troubleshooting walk-through isn't. Everything else
# supports multiple choice, short answer and scenario questions.
COMMAND_CATEGORIES = frozenset(
    {"Linux", "Windows", "Networking", "Security Tools", "Penetration Testing",
     "Active Directory", "Digital Forensics", "Web Security"}
)
NO_TROUBLESHOOTING_CATEGORIES = frozenset({"Threat Intelligence"})

# Order used when "mixed" is selected; unsupported types are skipped per category.
MIXED_ROTATION = ("multiple_choice", "scenario", "short_answer", "troubleshooting", "command")
PERSONALIZED_ROTATION = ("scenario", "multiple_choice", "short_answer", "troubleshooting", "command")

# Beginner-friendly order used only when a user has no profile / history to personalize from.
FALLBACK_CATEGORY_ORDER = (
    "Cybersecurity Fundamentals", "Networking", "Linux", "Web Security", "SOC",
    "SIEM", "Incident Response", "Windows", "Cryptography", "Digital Forensics",
)

# What each mode means; served to the UI by the config endpoint (no AI involved).
#   category: "none" (engine decides) | "optional" | "required"
#   fixed_type: the mode implies this question type
MODE_INFO = (
    {"id": "personalized", "label": "Personalized", "category": "none", "fixed_type": None,
     "description": "Built from your profile, goals, strengths, weaknesses and recent practice."},
    {"id": "topic", "label": "Topic", "category": "required", "fixed_type": None,
     "description": "Practice one cybersecurity category."},
    {"id": "random", "label": "Random", "category": "none", "fixed_type": None,
     "description": "A varied mix of categories, favouring ones you haven't seen lately."},
    {"id": "weakness", "label": "My Weaknesses", "category": "none", "fixed_type": None,
     "description": "Focus on the areas where your results are weakest."},
    {"id": "scenario", "label": "Scenario", "category": "optional", "fixed_type": "scenario",
     "description": "Realistic situations: what would you investigate or do?"},
    {"id": "troubleshooting", "label": "Troubleshooting", "category": "optional",
     "fixed_type": "troubleshooting",
     "description": "A problem to diagnose: walk through your investigation."},
    {"id": "interview", "label": "Interview-style", "category": "optional", "fixed_type": None,
     "description": "Cybersecurity questions phrased the way an interviewer would ask them."},
)
MODE_LABELS = {m["id"]: m["label"] for m in MODE_INFO}

# --- Scoring -------------------------------------------------------------------

# Overall score = weighted mean of the four evaluated dimensions. The model's own
# "overall" is never trusted: it is recomputed here so scoring is consistent.
DIMENSION_WEIGHTS = {"technical": 0.35, "completeness": 0.25, "reasoning": 0.25, "practicality": 0.15}

# Gentle, capped multiplier per hint used. The goal is learning, not punishment.
HINT_MULTIPLIERS = {0: 1.00, 1: 0.95, 2: 0.88, 3: 0.80}


def apply_hint_penalty(raw_score: int, hints_used: int) -> int:
    multiplier = HINT_MULTIPLIERS[max(0, min(MAX_HINTS, hints_used))]
    return max(0, min(100, round(raw_score * multiplier)))


def overall_from_dimensions(scores: dict[str, int]) -> int:
    total = sum(scores[name] * weight for name, weight in DIMENSION_WEIGHTS.items())
    return max(0, min(100, round(total)))


# --- Difficulty ----------------------------------------------------------------


def step_level(level: str, delta: int) -> str:
    return LEVELS[max(0, min(len(LEVELS) - 1, LEVELS.index(level) + delta))]


def adjust_difficulty(base: str, recent_scores: list[int]) -> str:
    """
    Gradual in-session adaptation, never more than ONE level from `base`:

    * two strong answers in a row, or three steadily improving ones -> one level up
    * two weak answers in a row -> one level down (reinforce fundamentals)
    * anything else (including a single result either way) -> stay at `base`
    """
    if base not in LEVELS:
        base = "beginner"
    if len(recent_scores) >= 2:
        last_two = recent_scores[-2:]
        if all(s >= STRONG_THRESHOLD for s in last_two):
            return step_level(base, +1)
        if all(s < PASS_THRESHOLD for s in last_two):
            return step_level(base, -1)
    if len(recent_scores) >= 3:
        a, b, c = recent_scores[-3:]
        if a < b < c and c >= 70:
            return step_level(base, +1)
    return base


def difficulty_for_category(difficulty: str, category: str, personalization: dict | None) -> str:
    """Fixed levels are honoured as-is; `adaptive` starts from Step 16's `choose_difficulty`."""
    if difficulty in LEVELS:
        return difficulty
    pers = personalization or {}
    rows = {r["topic"]: r for r in pers.get("topic_performance", [])}
    level, _ = choose_difficulty(
        preference="adaptive", experience_level=pers.get("user_level"), row=rows.get(category)
    )
    return level


# --- Planning ------------------------------------------------------------------


class PlanError(ValueError):
    """The requested configuration can't be satisfied (maps to a 422)."""


def supported_types(category: str) -> list[str]:
    types = ["multiple_choice", "short_answer", "scenario"]
    if category not in NO_TROUBLESHOOTING_CATEGORIES:
        types.append("troubleshooting")
    if category in COMMAND_CATEGORIES:
        types.append("command")
    return types


@dataclass
class Plan:
    slots: list[dict[str, Any]]
    categories: list[str]
    focus: list[dict[str, str]] = field(default_factory=list)  # [{category, reason}]
    note: str | None = None
    effective_mode: str = "topic"
    effective_type: str = "mixed"


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _personalized_candidates(pers: dict | None) -> list[tuple[str, str]]:
    """(category, reason) in priority order: weaknesses, recommendations, interests/career."""
    out: list[tuple[str, str]] = []
    if not pers:
        return out
    for w in pers.get("weaknesses", []):
        out.append((w["topic"], f"Weak area (average {w['average_score']}/100) -- reinforcing it."))
    for topic in pers.get("recommended_topics", []):
        out.append((topic, "Recommended for you based on your profile and recent practice."))
    fits = interest_categories(
        {
            "career_goal": pers.get("career_goal") or "",
            "cybersecurity_interests": pers.get("interests", []),
            "learning_goals": [],
        }
    )
    for category, why in fits.items():
        out.append((category, why))
    first: dict[str, str] = {}
    for category, reason in out:
        first.setdefault(category, reason)
    return list(first.items())


def _spread(categories: list[str], n: int) -> list[str]:
    """Interleave `n` questions over the leading categories (>= 2 questions per category)."""
    distinct = max(1, min(len(categories), n // 2))
    chosen = categories[:distinct]
    return [chosen[i % distinct] for i in range(n)]


def _pick_topic(topics: list[dict], used: set[str], recent: set[str], rng: random.Random) -> dict:
    """Prefer topics not used in this session, then ones not seen recently; random among ties."""
    ranked = sorted(topics, key=lambda t: (t["slug"] in used, t["slug"] in recent, rng.random()))
    return ranked[0]


def _type_for(requested: str, mode: str, category: str, cursor: int) -> str:
    if requested != "mixed":
        return requested
    rotation = PERSONALIZED_ROTATION if mode in ("personalized", "weakness") else MIXED_ROTATION
    allowed = supported_types(category)
    for offset in range(len(rotation)):
        candidate = rotation[(cursor + offset) % len(rotation)]
        if candidate in allowed:
            return candidate
    return "short_answer"


def plan_session(
    *,
    mode: str,
    category: str | None,
    topic_slug: str | None,
    question_type: str,
    question_count: int,
    difficulty: str,
    catalog: list[dict],
    personalization: dict | None,
    recent_slugs: set[str],
    recent_categories: list[str],
    rng: random.Random | None = None,
) -> Plan:
    """
    Decide, before any AI call, what the session covers: one slot per question with its
    category, catalogue topic, question type and starting difficulty.
    """
    rng = rng or random.Random()
    if mode not in MODES:
        raise PlanError(f"Unknown practice mode: {mode!r}")
    if difficulty not in DIFFICULTY_CHOICES:
        raise PlanError(f"Unknown difficulty: {difficulty!r}")
    if question_type not in TYPE_CHOICES:
        raise PlanError(f"Unknown question type: {question_type!r}")
    if not MIN_QUESTIONS <= question_count <= MAX_QUESTIONS:
        raise PlanError(f"Question count must be between {MIN_QUESTIONS} and {MAX_QUESTIONS}.")

    by_category: dict[str, list[dict]] = {}
    for topic in catalog:
        by_category.setdefault(topic["category"], []).append(topic)
    if not by_category:
        raise PlanError("No practice topics are available.")
    available = sorted(by_category)

    # The mode can fix the question type ("Scenario Practice" is scenario questions).
    effective_type = {"scenario": "scenario", "troubleshooting": "troubleshooting"}.get(mode, question_type)
    style = "interview" if mode == "interview" else None
    if mode == "interview" and effective_type == "mixed":
        effective_type = "short_answer"

    effective_mode = mode
    note: str | None = None
    reasons: dict[str, str] = {}
    pinned_slug: str | None = None

    if topic_slug:
        match = next((t for t in catalog if t["slug"] == topic_slug), None)
        if match is None:
            raise PlanError("That topic isn't available for practice.")
        category, pinned_slug = match["category"], topic_slug

    if mode == "topic" or (category and mode not in ("personalized", "weakness", "random")):
        if not category:
            raise PlanError("Choose a category (or topic) for topic practice.")
        if category not in by_category:
            raise PlanError(f"{category!r} isn't available for practice.")
        candidates = [category]
        reasons[category] = "Topic you chose."
    elif mode == "random":
        pool = available[:]
        rng.shuffle(pool)
        # Recently practiced categories go last so a random run feels fresh.
        pool.sort(key=lambda c: c in recent_categories[:3])
        candidates = pool
        reasons = {c: "Random pick." for c in pool}
    else:
        if mode == "weakness":
            weak = [(w["topic"], f"Weak area (average {w['average_score']}/100) -- reinforcing it.")
                    for w in (personalization or {}).get("weaknesses", [])]
            if weak:
                pairs = weak
            else:
                pairs = _personalized_candidates(personalization)
                effective_mode = "personalized"
                note = ("No weak areas have been identified yet, so this session follows your "
                        "recommended focus instead.")
        else:
            pairs = _personalized_candidates(personalization)
        pairs = [(c, r) for c, r in pairs if c in by_category]
        if not pairs:
            fallback = [c for c in FALLBACK_CATEGORY_ORDER if c in by_category] or available
            pairs = [(c, "Core concepts to build a foundation.") for c in fallback]
        candidates = _dedupe([c for c, _ in pairs])
        reasons = dict(pairs)

    if effective_type == "troubleshooting":
        candidates = [c for c in candidates if c not in NO_TROUBLESHOOTING_CATEGORIES]
    elif effective_type == "command":
        candidates = [c for c in candidates if c in COMMAND_CATEGORIES]
    if not candidates:
        raise PlanError(
            f"{effective_type.replace('_', ' ').title()} questions aren't available for that selection."
        )

    sequence = _spread(candidates, question_count)
    used: set[str] = set()
    slots = []
    for index, cat in enumerate(sequence):
        topics = by_category[cat]
        if pinned_slug:
            topics = [t for t in topics if t["slug"] == pinned_slug]
        topic = _pick_topic(topics, used, recent_slugs, rng)
        used.add(topic["slug"])
        slots.append(
            {
                "index": index,
                "category": cat,
                "topic_slug": topic["slug"],
                "topic_title": topic["title"],
                "type": _type_for(effective_type, mode, cat, index),
                "style": style,
                "base_difficulty": difficulty_for_category(difficulty, cat, personalization),
            }
        )

    categories = _dedupe(sequence)
    return Plan(
        slots=slots,
        categories=categories,
        focus=[{"category": c, "reason": reasons.get(c, "")} for c in categories],
        note=note,
        effective_mode=effective_mode,
        effective_type=effective_type,
    )


# --- Validation of untrusted AI output -----------------------------------------


class GeneratedQuestion(BaseModel):
    question: str = Field(min_length=1, max_length=1500)
    type: str
    options: list[str] | None = None
    correct_answer: str | None = None
    ideal_answer: str | None = None
    ideal_steps: list[str] | None = None
    expected_concepts: list[str] = Field(default_factory=list)
    explanation: str = Field(min_length=1, max_length=2000)
    hints: list[str] = Field(default_factory=list)

    @field_validator("expected_concepts", "hints", mode="before")
    @classmethod
    def _none_to_list(cls, value):
        return [] if value is None else value


def _clean_list(items: list[str] | None, *, max_items: int, max_len: int) -> list[str]:
    return [i.strip()[:max_len] for i in (items or []) if isinstance(i, str) and i.strip()][:max_items]


def validate_generated_question(data: dict, *, expected_type: str) -> dict:
    """
    Validate + normalise one generated question. Raises ValueError/ValidationError on
    anything unusable so the caller can retry. Returns a plain dict ready to store.
    """
    q = GeneratedQuestion.model_validate(data)
    if q.type != expected_type:
        raise ValueError(f"Expected question type {expected_type!r}, got {q.type!r}")

    hints = _clean_list(q.hints, max_items=MAX_HINTS, max_len=500)
    if len(hints) < MAX_HINTS:
        raise ValueError("Question needs three progressive hints")

    out: dict[str, Any] = {
        "question": q.question.strip(),
        "type": q.type,
        "options": None,
        "correct_answer": None,
        "ideal_answer": None,
        "ideal_steps": None,
        "expected_concepts": _clean_list(q.expected_concepts, max_items=10, max_len=120),
        "explanation": q.explanation.strip(),
        "hints": hints,
    }

    if q.type == "multiple_choice":
        options = _clean_list(q.options, max_items=6, max_len=300)
        if len(set(options)) < 2:
            raise ValueError("Multiple-choice question needs at least 2 distinct options")
        if not q.correct_answer or q.correct_answer.strip() not in options:
            raise ValueError("correct_answer must exactly match one of the options")
        out["options"], out["correct_answer"] = options, q.correct_answer.strip()
    elif q.type in ("short_answer", "command"):
        if not (q.ideal_answer or "").strip():
            raise ValueError(f"{q.type} question needs a non-empty ideal_answer")
        if not out["expected_concepts"]:
            raise ValueError("Free-text question needs expected_concepts")
        out["ideal_answer"] = q.ideal_answer.strip()[:2000]
    elif q.type in ("scenario", "troubleshooting"):
        steps = _clean_list(q.ideal_steps, max_items=10, max_len=400)
        if len(steps) < 3:
            raise ValueError(f"{q.type} question needs at least 3 ideal_steps")
        if not out["expected_concepts"]:
            raise ValueError("Free-text question needs expected_concepts")
        out["ideal_steps"] = steps
        out["ideal_answer"] = format_steps(steps)
    else:
        raise ValueError(f"Unsupported question type: {q.type!r}")
    return out


def format_steps(steps: list[str]) -> str:
    return "\n".join(f"{i}. {s}" for i, s in enumerate(steps, start=1))


class GeneratedEvaluation(BaseModel):
    technical_score: int = Field(ge=0, le=100)
    completeness_score: int = Field(ge=0, le=100)
    reasoning_score: int = Field(ge=0, le=100)
    practicality_score: int = Field(ge=0, le=100)
    strengths: list[str] = Field(default_factory=list)
    missing_points: list[str] = Field(default_factory=list)
    feedback: str = Field(min_length=1, max_length=1500)
    improvement: str | None = Field(default=None, max_length=600)

    @field_validator("strengths", "missing_points", mode="before")
    @classmethod
    def _none_to_list(cls, value):
        return [] if value is None else value


def validate_generated_evaluation(data: dict) -> dict:
    """Validate an AI evaluation and compute the overall score server-side."""
    ev = GeneratedEvaluation.model_validate(data)
    dimensions = {
        "technical": ev.technical_score,
        "completeness": ev.completeness_score,
        "reasoning": ev.reasoning_score,
        "practicality": ev.practicality_score,
    }
    overall = overall_from_dimensions(dimensions)
    return {
        "dimension_scores": {**dimensions, "overall": overall},
        "raw_score": overall,
        "correct": overall >= PASS_THRESHOLD,
        "feedback": ev.feedback.strip(),
        "strengths": _clean_list(ev.strengths, max_items=5, max_len=300),
        "missing_points": _clean_list(ev.missing_points, max_items=6, max_len=300),
        "improvement": (ev.improvement or "").strip() or None,
    }


# --- Session outcome -------------------------------------------------------------


def _mean(values: list[int]) -> int:
    return round(sum(values) / len(values))


def summarize_session(session: dict) -> dict:
    """
    Turn a session's questions + answers into its outcome. `score` is None when nothing was
    answered (no evidence either way), otherwise the mean of per-question final scores.
    """
    answers: dict = session.get("answers") or {}
    questions: list[dict] = session.get("questions") or []
    answered = [(q, answers[q["question_id"]]) for q in questions if q["question_id"] in answers]
    scores = [a["score"] for _, a in answered]

    by_topic: dict[str, dict] = {}
    by_category: dict[str, dict] = {}
    for q, a in answered:
        t = by_topic.setdefault(q["topic_slug"], {"title": q["topic_title"], "scores": []})
        t["scores"].append(a["score"])
        c = by_category.setdefault(
            q["category"], {"scores": [], "correct": 0, "topic_slugs": []}
        )
        c["scores"].append(a["score"])
        c["correct"] += 1 if a.get("correct") else 0
        if q["topic_slug"] not in c["topic_slugs"]:
            c["topic_slugs"].append(q["topic_slug"])

    topic_avgs = sorted(
        ((v["title"], _mean(v["scores"])) for v in by_topic.values()), key=lambda x: -x[1]
    )
    strong_areas = [title for title, avg in topic_avgs if avg >= STRONG_THRESHOLD]
    needs_work = [title for title, avg in reversed(topic_avgs) if avg < PASS_THRESHOLD]

    multi = len(by_category) > 1
    category_results = []
    for name, c in by_category.items():
        # Several-category sessions only credit a category that had real evidence (>= 2 answers).
        if multi and len(c["scores"]) < 2:
            continue
        category_results.append(
            {
                "category": name,
                "score": _mean(c["scores"]),
                "questions_answered": len(c["scores"]),
                "correct_answers": c["correct"],
                "topic_slugs": c["topic_slugs"],
            }
        )

    levels = [q["difficulty"] for q in questions if q.get("difficulty") in LEVELS]
    modal = Counter(levels).most_common(1)[0][0] if levels else None

    return {
        "score": _mean(scores) if scores else None,
        "questions_total": len(session.get("plan") or questions),
        "questions_answered": len(answered),
        "correct_answers": sum(1 for _, a in answered if a.get("correct")),
        "needs_improvement": sum(1 for _, a in answered if not a.get("correct")),
        "hints_used": sum((a.get("hints_used") or 0) for _, a in answered),
        "revealed": sum(1 for _, a in answered if a.get("revealed")),
        "strong_areas": strong_areas,
        "needs_work": needs_work,
        "category_results": category_results,
        "categories": list(by_category),
        "topic_slugs": list(by_topic),
        "modal_difficulty": modal,
        "weak_categories": [r["category"] for r in category_results if r["score"] < PASS_THRESHOLD],
        "label_category": (list(by_category)[0] if len(by_category) == 1 else MIXED_CATEGORY)
        if by_category
        else None,
    }

