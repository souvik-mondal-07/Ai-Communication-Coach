"""
Maintainer CLI for the DBMS & SQL question bank (no database needed).

    python -m app.services.dbms_sql.cli coverage   # markdown coverage report, derived from the validated seed bank

To also re-run every SQL reference, recompute MongoDB results with an independent engine and probe the sandbox's security
controls, run `python -m tools.verify_dbms_bank`.
"""

from __future__ import annotations

import sys
from collections import Counter, defaultdict

from app.services.dbms_sql import bank, sandbox
from app.services.dbms_sql.syllabus import MIN_QUESTIONS_PER_TOPIC, UNITS

MACHINE = ("reference_checked", "sql_checked", "sql_output_checked")
LABELS = {"reference_checked": "reference computation", "sql_checked": "SQL engine + Python oracle", "sql_output_checked": "SQL engine + Python oracle/declared value",
          "manual_review": "manual review (no machine check)"}


def coverage_markdown() -> str:
    valid, rejected = bank.build_valid_seed_bank()
    by_topic: dict[str, list[dict]] = defaultdict(list)
    for q in valid:
        by_topic[q["topic_id"]].append(q)
    machine = sum(1 for q in valid if q["review_status"] in MACHINE)
    caps = sandbox.capabilities()
    lines = [
        "# DBMS & SQL Interview Lab: syllabus coverage report", "",
        f"Generated from the validated seed bank: **{len(valid)} questions**, {len(rejected)} rejected. A topic is *ready* with at least {MIN_QUESTIONS_PER_TOPIC} questions; "
        "depth beyond that minimum is stated, not implied.", "",
        f"SQL practice engine: {caps['engine']} {caps['version']} (read-only; window functions: {caps['window_functions']}; RIGHT/FULL JOIN: {caps['right_full_join']}).", "",
        f"**Verification:** {machine} questions are machine-verified (reference computation, or SQL engine plus an independent Python oracle). "
        f"{len(valid) - machine} are manual-review definition questions with a written justification but NO executable check; they need subject-expert sign-off.", "",
    ]
    for title, key in (("Questions by format", "format"), ("Questions by interaction", "interaction"), ("Questions by difficulty", "difficulty"), ("Questions by dialect", "dialect"), ("Verification method", "review_status")):
        counts = Counter(q[key] for q in valid)
        lines += [f"| {title} | Count |", "|---|---:|", *[f"| {LABELS.get(k, k)} | {v} |" for k, v in sorted(counts.items(), key=lambda kv: -kv[1])], ""]
    gaps: list[str] = []
    for u in UNITS:
        total = sum(len(by_topic[t.id]) for t in u.topics)
        lines += [f"## Unit {u.code}: {u.title} ({total} questions)", "", "| Topic | Total | E/M/H | Formats | Interactions | Machine-verified | Status |", "|---|---:|:-:|---|---|---:|---|"]
        for t in u.topics:
            qs = by_topic[t.id]
            d = Counter(q["difficulty"] for q in qs)
            f = ", ".join(f"{k} {v}" for k, v in sorted(Counter(q["format"] for q in qs).items()))
            i = ", ".join(f"{k} {v}" for k, v in sorted(Counter(q["interaction"] for q in qs).items()))
            mv = sum(1 for q in qs if q["review_status"] in MACHINE)
            lines.append(f"| {t.title} | {len(qs)} | {d['easy']}/{d['medium']}/{d['hard']} | {f} | {i} | {mv} | {bank.status_for(len(qs))} |")
            missing = [x for x in ("easy", "medium", "hard") if not d[x]]
            if len(qs) < MIN_QUESTIONS_PER_TOPIC:
                gaps.append(f"{t.title}: only {len(qs)} question(s).")
            elif missing:
                gaps.append(f"{t.title}: no {'/'.join(missing)} question yet.")
        lines.append("")
    lines += ["## Remaining gaps", ""]
    lines += [f"- {g}" for g in gaps] if gaps else ["- No topic is below the minimum, and every topic has all three difficulty levels."]
    thin = sorted(((len(by_topic[t.id]), t.title) for u in UNITS for t in u.topics))[:8]
    lines += ["", "Thinnest topics (candidates for the next content expansion): " + "; ".join(f"{t} ({n})" for n, t in thin) + ".", ""]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "coverage"
    if cmd == "coverage":
        print(coverage_markdown())
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
