"""
Answer-level heuristics: length banding and answer-structure markers.

Both are deterministic and run on text already stored in the session documents.
The text itself is never returned to the client -- only counts and labels.

Structure markers are *indicative*: simple keyword cues for the stages a good
answer to that kind of question usually contains. They are reported alongside
(not instead of) the AI structure score already stored per answer, and never
force one template onto every question.
"""

from __future__ import annotations

import re

from app.services.analytics import config

LENGTH_LABELS = ("too_short", "appropriate", "long", "very_long")

# Expected stages per question kind -> cue regexes (case-insensitive).
_STAGES: dict[str, dict[str, str]] = {
    "technical": {
        "definition": r"\b(is a|is an|is the|refers to|means|stands for|is defined as|is used to|is when)\b",
        "explanation": r"\b(because|works by|which means|this allows|allows|ensures|therefore|in order to|so that|the reason)\b",
        "example": r"\b(for example|for instance|e\.g\.|such as|imagine|consider|like when)\b",
        "practical_relevance": r"\b(in practice|in real|real[- ]world|in production|best practice|organi[sz]ations?|typically|commonly|i have used|i used|i would use)\b",
    },
    "scenario": {
        "situation": r"\b(scenario|alert|incident|detected|suspicious|noticed|first,? i|if i (see|saw|receive|get))\b",
        "investigation": r"\b(investigat\w*|analy[sz]\w*|check\w*|review\w*|logs?|identify|verify|triage|determine|scope)\b",
        "action": r"\b(contain\w*|isolat\w*|block\w*|remediat\w*|disabl\w*|reset|patch\w*|escalat\w*|mitigat\w*|eradicat\w*|revok\w*)\b",
        "result": r"\b(outcome|resolved|recover\w*|restor\w*|post-incident|lessons?|document\w*|report\w*|prevent\w*|monitor\w*)\b",
    },
    "behavioral": {
        "situation": r"\b(when i|at (my|the)|during|in my (project|course|lab|internship|studies)|once|last (year|semester)|there was a)\b",
        "action": r"\bi (decided|built|created|led|worked|started|asked|organi[sz]ed|tried|took|made|wrote|implemented|set up)\b|\bmy role\b|\bi was responsible\b",
        "result": r"\b(as a result|resulted|outcome|achieved|completed|improved|finished|successful|feedback|grade)\b",
        "learning": r"\b(learn(ed|t)|realis\w*|realiz\w*|takeaway|next time|since then|going forward|now i)\b",
    },
}
_COMPILED = {
    kind: {stage: re.compile(pattern, re.IGNORECASE) for stage, pattern in stages.items()}
    for kind, stages in _STAGES.items()
}
MIN_WORDS_FOR_STRUCTURE = 25   # shorter answers are "too short to assess", not "unstructured"


def classify_length(words: int, kind: str) -> str:
    short_below, long_above, very_long_above = config.LENGTH_BANDS.get(kind, config.DEFAULT_LENGTH_BAND)
    if words < short_below:
        return "too_short"
    if words > very_long_above:
        return "very_long"
    if words > long_above:
        return "long"
    return "appropriate"


def structure_markers(text: str | None, kind: str, words: int) -> dict | None:
    """Which expected stages the answer shows; None when the answer is too short to judge."""
    stages = _COMPILED.get(kind)
    if not text or stages is None or words < MIN_WORDS_FOR_STRUCTURE:
        return None
    present = {stage: bool(rx.search(text)) for stage, rx in stages.items()}
    return {"kind": kind, "stages": present, "coverage": round(sum(present.values()) / len(present), 2)}
