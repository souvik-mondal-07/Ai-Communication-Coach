"""
Maintainer command: validate the DSA seed bank AND execute every reference solution, fill-the-line option set and output snippet.

    cd backend && python -m tools.verify_dsa_bank

Exits non-zero on any problem. Runs only repository-owned seed code, in the isolated runner; never user submissions.
"""

from __future__ import annotations

import sys

from app.services.dsa import bank
from tools import dsa_seed_runner as runner


def verify() -> int:
    valid, rejected = bank.build_valid_seed_bank()
    problems = [f"REJECTED {r['question_id']}: {r['problems']}" for r in rejected]
    solutions = lines = snippets = 0
    for q in valid:
        ver = q.get("verification") or {}
        if q["interaction"] == "code":
            solutions += 1
            problems += [f"{q['coding']['function_name']}: {m}" for m in runner.check_solution(q["coding"])]
        elif "line_check" in ver:
            lines += 1
            problems += [f"{q['statement'][:50]}: {m}" for m in runner.check_line_question(q)]
        elif ver.get("method") == "snippet":
            snippets += 1
            msg = runner.check_snippet(q)
            if msg:
                problems.append(f"{q['statement'][:50]}: {msg}")
    print(f"validated={len(valid)} rejected={len(rejected)} | executed: solutions={solutions} line-questions={lines} snippets={snippets}")
    for p in problems:
        print("PROBLEM:", p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(verify())
