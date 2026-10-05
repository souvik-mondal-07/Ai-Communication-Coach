"""
Per-category view of a completed practice session (Step 17).

Step 5 sessions cover exactly one topic, so a session's `category`/`score`
were the whole story. Step 17 sessions can span several categories (random,
personalized and weakness practice), so a completed advanced session also
stores `category_results`: one entry per category with the score for *that
category's* questions.

Progress (Step 11), personalization (Step 16) and the practice progress view
all read through `session_category_entries`, so a score is always credited to
the category it was earned in -- and Step 5 sessions (no `category_results`)
keep behaving exactly as before.

Pure functions only: no database access, no AI.
"""

from __future__ import annotations

from typing import Any

# Sessions that cover more than one category are labelled with this on
# `category` (it is display text only; consumers read `category_results`).
MIXED_CATEGORY = "Mixed"


def session_category_entries(doc: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Per-category result rows for one completed session, each shaped:

        {"category", "score", "questions_answered", "correct_answers", "topic_slugs"}

    Sessions without a score (e.g. completed with nothing answered) yield no
    rows -- they carry no evidence either way.
    """
    results = doc.get("category_results")
    if isinstance(results, list) and results:
        return [
            {
                "category": r["category"],
                "score": r["score"],
                "questions_answered": r.get("questions_answered") or 0,
                "correct_answers": r.get("correct_answers") or 0,
                "topic_slugs": list(r.get("topic_slugs") or []),
            }
            for r in results
            if r.get("category") and r.get("score") is not None
        ]

    category = doc.get("category")
    score = doc.get("score")
    if not category or score is None or category == MIXED_CATEGORY:
        return []
    slug = doc.get("topic_slug")
    return [
        {
            "category": category,
            "score": score,
            "questions_answered": doc.get("questions_answered") or 0,
            "correct_answers": doc.get("correct_answers") or 0,
            "topic_slugs": [slug] if slug else [],
        }
    ]
