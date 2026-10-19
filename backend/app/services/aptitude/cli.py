"""
Maintenance commands for the aptitude question bank (no database needed).

    python -m app.services.aptitude.cli validate    # exit 1 if any seed fails validation
    python -m app.services.aptitude.cli coverage    # per-subtopic question counts as a Markdown matrix

`validate` re-derives every machine-checkable answer independently, so run it after editing content.
"""

from __future__ import annotations

import sys
from collections import Counter

from app.services.aptitude.bank import build_valid_seed_bank
from app.services.aptitude.syllabus import MIN_QUESTIONS_PER_SUBTOPIC, TOPICS


def validate() -> int:
    valid, rejected = build_valid_seed_bank()
    methods = Counter(q["verification"]["method"] for q in valid)
    print(f"{len(valid)} valid, {len(rejected)} rejected")
    print("verification:", ", ".join(f"{k}={v}" for k, v in sorted(methods.items())))
    for r in rejected:
        print(f"REJECTED {r['question_id']}: {r['statement']} -> {r['problems']}")
    return 1 if rejected else 0


def coverage() -> int:
    valid, _ = build_valid_seed_bank()
    by_sub: dict[str, Counter] = {}
    for q in valid:
        c = by_sub.setdefault(q["subtopic_id"], Counter())
        c["total"] += 1
        c[q["difficulty"]] += 1
        c["manual"] += q["verification"]["method"] == "manual_review"
    print("| # | Topic / subtopic | Easy | Med | Hard | Total | Machine-verified | Status |")
    print("|---|---|---:|---:|---:|---:|---:|---|")
    grand = 0
    for t in TOPICS:
        total = sum(by_sub.get(s.id, Counter())["total"] for s in t.subtopics)
        grand += total
        print(f"| **{t.code}** | **{t.title}** | | | | **{total}** | | |")
        for s in t.subtopics:
            c = by_sub.get(s.id, Counter())
            n = c["total"]
            status = "implemented" if n >= MIN_QUESTIONS_PER_SUBTOPIC else ("partial" if n else "MISSING")
            print(f"| | {s.title} | {c['easy']} | {c['medium']} | {c['hard']} | {n} | {n - c['manual']}/{n} | {status} |")
    print(f"\nTotal: {grand} questions")
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    sys.exit({"validate": validate, "coverage": coverage}.get(cmd, lambda: (print(__doc__) or 2))())
