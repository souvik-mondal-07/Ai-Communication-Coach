"""
Independent re-verification of the Python practice bank (Phase 26). Used by `python -m tools.verify_python_bank` and by the tests.

It RUNS the seeds in the isolated code runner (the same sandbox users' code goes through; seeds are never executed in the API process):
  * output / trace questions: the snippet must print exactly the stored answer (or raise exactly the stored exception);
  * coding / debug / complete questions: the reference source must pass every test, and a debug or completion starter must FAIL at least one.
With `write=True` it records the results in `content/verified.json`, keyed by question id and bound to a hash of the content that was run,
so editing a snippet silently un-verifies it until this tool is run again. Requires a working runner (Linux).
"""

from __future__ import annotations

import json
import sys
from typing import Any

from app.services.python_practice import compare, grader
from app.services.python_practice.content import all_seed_questions
from app.services.python_practice.content.build import MANIFEST_PATH, exec_hash
from app.services.python_practice.sandbox import runner


def run_snippet(code: str) -> dict[str, Any]:
    raw = runner.run(code, {"mode": "stdio", "entry": "x", "cases": [{"id": 0, "stdin": ""}], "per_case_seconds": 3}, 8)
    if raw.termination == "setup_failed":
        raise runner.RunnerUnavailable(raw.detail or "setup failed")
    if raw.setup is not None:
        return {"status": "error", "error_type": raw.setup.get("error_type"), "stdout": ""}
    return raw.results.get(0, {"status": "timeout", "stdout": ""})


def verify_all(write: bool = False) -> dict[str, Any]:
    if not runner.capabilities()["available"]:
        raise runner.RunnerUnavailable(runner.capabilities()["reason"] or "runner unavailable")
    manifest: dict[str, Any] = {}
    failures: list[str] = []
    checked = {"execution": 0, "reference": 0, "starters": 0}
    for doc in all_seed_questions():
        ver = doc.get("verification") or {}
        qid = doc["question_id"]
        if ver.get("method") == "execution":
            checked["execution"] += 1
            res = run_snippet(doc["code"])
            exc, want = ver.get("expected_exception"), ver.get("expected_stdout")
            if exc:
                ok = res.get("status") == "error" and res.get("error_type") == exc
            else:
                ok = res.get("status") == "ok" and compare.normalize_text(res.get("stdout", "")) == compare.normalize_text(want or "")
            rec = {"hash": exec_hash(doc["code"], want, exc), "ok": bool(ok), "python": ".".join(map(str, sys.version_info[:3])),
                   "observed": (f"raises {res.get('error_type')}" if res.get("status") == "error" else res.get("stdout", ""))[:400]}
            manifest[qid] = rec
            if not ok:
                failures.append(f"{qid} ({doc['statement'][:50]}): expected {exc or repr(want)}, observed {rec['observed']!r}")
        elif ver.get("method") == "reference" and doc.get("spec"):
            checked["reference"] += 1
            spec = doc["spec"]
            ref = grader.grade(spec, spec["reference_source"], visible_only=False)
            rec = {"reference_passes": ref.accepted}
            if not ref.accepted:
                failures.append(f"{qid} ({doc['title']}): reference solution failed in the runner: {ref.verdict} {ref.passed}/{ref.total}")
            if doc["format"] in ("debug", "complete"):
                checked["starters"] += 1
                starter = grader.grade(spec, spec["starter"], visible_only=False)
                rec.update({"starter_fails": not starter.accepted, "starter_hash": ver.get("starter_hash")})
                if starter.accepted:
                    failures.append(f"{qid} ({doc['title']}): the buggy/incomplete starter already passes every test")
            manifest[qid] = rec
    if write and not failures:
        MANIFEST_PATH.write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return {"checked": checked, "failures": failures, "written": bool(write and not failures), "manifest_entries": len(manifest)}
