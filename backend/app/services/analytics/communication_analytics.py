"""
Communication analytics: dimension scores, answer structure, answer length and
evidence-gated recurring weaknesses.

Dimension sources (all already stored):
* interview/pressure answers: clarity, grammar, vocabulary, structure, conciseness
* communication sessions: clarity, grammar, vocabulary, confidence, relevance,
  professionalism, flow
Conciseness and structure exist only for interview/pressure answers; confidence only
for communication sessions. A dimension with no source is None, never filled in.
"""

from __future__ import annotations

from collections import Counter, defaultdict

from app.services.analytics import config
from app.services.analytics.answer_analytics import LENGTH_LABELS
from app.services.analytics.common import mean, score_band
from app.services.analytics.facts import Facts, all_answers, spoken_samples

WEAKNESS_LABELS = {
    "filler_words": "High filler-word usage",
    "long_pauses": "Long pauses while speaking",
    "repeated_words": "Repeated words",
    "weak_structure": "Answers lack a clear structure",
    "answers_too_short": "Answers are often too short",
    "answers_too_long": "Answers are often too long",
    "shallow_technical_explanation": "Technical explanations lack depth",
    "low_confidence": "Low confidence scores",
}


def dimension_scores(facts: Facts) -> dict:
    answers = all_answers(facts.interviews + facts.pressure)
    comm = facts.communication

    def both(key: str, comm_key: str | None = None):
        return mean([a[key] for a in answers] + [c[comm_key or key] for c in comm])

    dims = {
        "clarity": both("clarity"),
        "grammar": both("grammar"),
        "vocabulary": both("vocabulary"),
        "structure": mean(a["structure"] for a in answers),
        "conciseness": mean(a["conciseness"] for a in answers),
        "confidence": mean(c["confidence"] for c in comm),
        "relevance": mean(c["relevance"] for c in comm),
        "professionalism": mean(c["professionalism"] for c in comm),
    }
    return {
        "dimensions": [
            {"key": k, "score": v, "band": score_band(v)} for k, v in dims.items() if v is not None
        ],
        "samples": {"answers": len(answers), "communication_sessions": len(comm)},
    }


def structure_report(facts: Facts) -> dict:
    """AI structure score plus keyword-marker coverage, split by question kind."""
    answers = all_answers(facts.interviews + facts.pressure)
    by_kind: dict[str, list[dict]] = defaultdict(list)
    for a in answers:
        by_kind[a["kind"]].append(a)
    rows = []
    for kind, items in by_kind.items():
        marked = [a for a in items if a["markers"]]
        stage_hits: Counter = Counter()
        for a in marked:
            for stage, present in a["markers"]["stages"].items():
                stage_hits[stage] += int(present)
        rows.append({
            "kind": kind,
            "answers": len(items),
            "structure_score": mean(a["structure"] for a in items),
            "assessed_answers": len(marked),
            "marker_coverage": mean((a["markers"]["coverage"] for a in marked), digits=2),
            "stage_rates": {s: round(h / len(marked), 2) for s, h in stage_hits.items()} if marked else {},
        })
    rows.sort(key=lambda r: r["kind"])
    return {"by_kind": rows, "note": "Marker coverage is an indicative keyword check, not a grade."}


def length_report(facts: Facts) -> dict:
    answers = all_answers(facts.interviews + facts.pressure)
    if not answers:
        return {"available": False, "answers": 0}
    words = [a["words"] for a in answers]
    dist = Counter(a["length"] for a in answers)
    by_kind: dict[str, dict] = {}
    for kind in {a["kind"] for a in answers}:
        k = [a for a in answers if a["kind"] == kind]
        d = Counter(a["length"] for a in k)
        by_kind[kind] = {"answers": len(k), "average_words": round(sum(a["words"] for a in k) / len(k)),
                         **{label: d.get(label, 0) for label in LENGTH_LABELS}}
    durations = [a["voice"]["duration"] for a in answers if a["voice"] and a["voice"].get("duration")]
    return {
        "available": True,
        "answers": len(answers),
        "average_words": round(sum(words) / len(words)),
        "min_words": min(words),
        "max_words": max(words),
        "average_duration_seconds": mean(durations, digits=1) if durations else None,
        "distribution": {label: dist.get(label, 0) for label in LENGTH_LABELS},
        "by_question_kind": by_kind,
        "note": "Length bands differ per question kind (behavioural, technical, scenario).",
    }


def _rule(name: str) -> dict:
    return config.WEAKNESS_RULES[name]


def _severity(rate: float) -> str:
    return "high" if rate >= 0.75 else "medium" if rate >= 0.6 else "low"


def detect_weaknesses(facts: Facts) -> list[dict]:
    """
    Recurring communication weaknesses. A weakness is reported only when it has at
    least `min_samples` measurements and occurs in at least `min_rate` of them.
    """
    answers = all_answers(facts.interviews + facts.pressure)
    spoken = spoken_samples(facts)
    found: list[dict] = []

    def consider(key: str, samples: int, hits: int, evidence: str) -> None:
        rule = _rule(key)
        if samples < rule["min_samples"]:
            return
        rate = hits / samples
        if rate >= rule["min_rate"]:
            found.append({"id": key, "label": WEAKNESS_LABELS[key], "samples": samples, "occurrences": hits,
                          "rate": round(rate, 2), "severity": _severity(rate), "evidence": evidence})

    r = _rule("filler_words")
    with_filler = [s for s in spoken if s.get("filler_rate") is not None]
    hits = sum(1 for s in with_filler if s["filler_rate"] >= r["filler_per_100_words"])
    consider("filler_words", len(with_filler), hits,
             f"{hits} of {len(with_filler)} spoken answers had {r['filler_per_100_words']:g}+ filler words per 100 words.")

    pausable = [s for s in spoken if s.get("long_pauses") is not None]
    hits = sum(1 for s in pausable if s["long_pauses"] > 0)
    consider("long_pauses", len(pausable), hits, f"{hits} of {len(pausable)} spoken answers had a long pause.")

    r = _rule("repeated_words")
    rep = [s for s in spoken if s.get("repeats") is not None]
    hits = sum(1 for s in rep if s["repeats"] >= r["min_repeats"])
    consider("repeated_words", len(rep), hits, f"{hits} of {len(rep)} spoken answers repeated words.")

    r = _rule("weak_structure")
    scored = [a for a in answers if a["structure"] is not None and not a["is_follow_up"]]
    hits = sum(1 for a in scored if a["structure"] < r["score_below"])
    consider("weak_structure", len(scored), hits,
             f"{hits} of {len(scored)} answers scored below {r['score_below']} for structure.")

    main = [a for a in answers if not a["is_follow_up"]]
    short = sum(1 for a in main if a["length"] == "too_short")
    consider("answers_too_short", len(main), short, f"{short} of {len(main)} answers were shorter than expected for their question type.")
    long_ = sum(1 for a in main if a["length"] in ("long", "very_long"))
    consider("answers_too_long", len(main), long_, f"{long_} of {len(main)} answers were longer than expected for their question type.")

    r = _rule("shallow_technical_explanation")
    tech_answers = [a for a in main if a["kind"] != "behavioral" and a["depth"] is not None and a["completeness"] is not None]
    hits = sum(1 for a in tech_answers if (a["depth"] + a["completeness"]) / 2 < r["score_below"])
    consider("shallow_technical_explanation", len(tech_answers), hits,
             f"{hits} of {len(tech_answers)} technical answers scored below {r['score_below']} for depth and completeness.")

    r = _rule("low_confidence")
    conf = [c["confidence"] for c in facts.communication if c["confidence"] is not None]
    hits = sum(1 for c in conf if c < r["score_below"])
    consider("low_confidence", len(conf), hits,
             f"{hits} of {len(conf)} communication sessions scored below {r['score_below']} for confidence.")

    found.sort(key=lambda w: (-{"high": 2, "medium": 1, "low": 0}[w["severity"]], -w["rate"]))
    return found[: config.MAX_LIST_ITEMS]


def communication_report(facts: Facts) -> dict:
    return {
        **dimension_scores(facts),
        "structure": structure_report(facts),
        "length": length_report(facts),
        "weaknesses": detect_weaknesses(facts),
        "communication_sessions": {
            "count": len(facts.communication),
            "overall_score": mean(c["overall"] for c in facts.communication),
            "confidence_score": mean(c["confidence"] for c in facts.communication),
        },
    }
