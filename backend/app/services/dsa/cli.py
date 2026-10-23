"""
Maintainer CLI for the DSA question bank (no database needed).

    python -m app.services.dsa.cli coverage   # markdown coverage matrix, derived from the validated seed bank

To also EXECUTE the seed solutions, fill-the-line options and output snippets, run `python -m tools.verify_dsa_bank`
(it lives outside `app/` because the deployed application contains no code-execution capability at all).
"""

from __future__ import annotations

import sys
from collections import Counter, defaultdict

from app.services.dsa import bank
from app.services.dsa.syllabus import MIN_QUESTIONS_PER_SUBTOPIC, TOPICS

FORMATS = ("conceptual", "scenario", "output", "trace", "complexity", "coding")


def _method(q: dict) -> str:
    ver = q.get("verification") or {}
    if "line_check" in ver:
        return "line options executed"
    return {"reference": "reference computation", "snippet": "snippet executed", "tests": "solution+tests executed", "manual_review": "manual review"}.get(ver.get("method"), "unverified")


def coverage_markdown() -> str:
    valid, rejected = bank.build_valid_seed_bank()
    by_sub: dict[str, list[dict]] = defaultdict(list)
    for q in valid:
        by_sub[q["subtopic_id"]].append(q)
    lines = ["# DSA question bank: coverage matrix", "", f"Generated from the validated seed bank: **{len(valid)} questions**, {len(rejected)} rejected. "
             f"A subtopic is *Ready* with at least {MIN_QUESTIONS_PER_SUBTOPIC} questions. Depth beyond that minimum is stated, not implied.", ""]
    fmt = Counter(q["format"] for q in valid)
    lines += ["| Format | Questions |", "|---|---:|", *[f"| {f} | {fmt[f]} |" for f in FORMATS], ""]
    meth = Counter(_method(q) for q in valid)
    lines += ["| Verification method | Questions |", "|---|---:|", *[f"| {k} | {v} |" for k, v in sorted(meth.items(), key=lambda kv: -kv[1])], ""]
    for t in TOPICS:
        total = sum(len(by_sub[s.id]) for s in t.subtopics)
        lines += [f"## {t.code}. {t.title} ({total} questions)", "", "| Subtopic | Total | E/M/H | Concept | Scenario | Output | Trace | Complexity | Coding | Auto-graded | Status |", "|---|---:|:-:|--:|--:|--:|--:|--:|--:|--:|---|"]
        for s in t.subtopics:
            qs = by_sub[s.id]
            f = Counter(q["format"] for q in qs)
            d = Counter(q["difficulty"] for q in qs)
            graded = sum(1 for q in qs if q["interaction"] == "mcq")
            status = bank.status_for(len(qs))
            lines.append(f"| {s.title} | {len(qs)} | {d['easy']}/{d['medium']}/{d['hard']} | {f['conceptual']} | {f['scenario']} | {f['output']} | {f['trace']} | {f['complexity']} | {f['coding']} | {graded} | {status} |")
        lines += ["", "Syllabus lines → subtopics:", ""]
        lines += [f"- {i.text} → {', '.join(i.subtopic_ids)} ({sum(len(by_sub[x]) for x in i.subtopic_ids)} questions)" for i in t.items]
        lines.append("")
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
