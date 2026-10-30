"""
Code-submission grading (Phase 26): turns raw sandbox output into per-test verdicts on the server.

Trust model: the sandbox only ever receives the submitted source and test INPUTS. Expected values, hidden-test labels and the reference
solution stay in this process. Hidden tests report only pass/fail and a coarse reason -- never their input, expected value, printed
output or error text -- so a failing hidden case cannot be used to read the answer key.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.services.python_practice import compare
from app.services.python_practice.sandbox import runner

MAX_VISIBLE_MESSAGE = 220
VERDICT_TEXT = {
    "accepted": "All tests passed.",
    "wrong_answer": "Some tests failed.",
    "runtime_error": "Your code raised an error.",
    "timeout": "Your code took too long (time limit exceeded).",
    "compile_error": "Your code could not be compiled or loaded.",
    "output_limit": "Your code printed too much output.",
    "runner_error": "The code runner failed. Try again.",
}


@dataclass
class TestOutcome:
    id: int
    label: str
    visible: bool
    passed: bool
    status: str  # passed | failed | error | timeout | not_run
    message: str | None = None
    stdout: str | None = None
    ms: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "label": self.label if self.visible else f"Hidden test {self.id}", "visible": self.visible, "passed": self.passed, "status": self.status,
                "message": self.message, "stdout": self.stdout, "ms": self.ms}


@dataclass
class Grade:
    verdict: str
    passed: int
    total: int
    outcomes: list[TestOutcome] = field(default_factory=list)
    message: str = ""
    setup_error: dict[str, Any] | None = None
    wall_ms: int = 0

    @property
    def accepted(self) -> bool:
        return self.verdict == "accepted"

    def to_dict(self) -> dict[str, Any]:
        return {"verdict": self.verdict, "message": self.message, "passed": self.passed, "total": self.total, "accepted": self.accepted,
                "tests": [o.to_dict() for o in self.outcomes], "setup_error": self.setup_error, "wall_ms": self.wall_ms}


def _runner_spec(spec: dict, tests: list[dict]) -> dict[str, Any]:
    cases = []
    for t in tests:
        if spec["mode"] == "function":
            cases.append({"id": t["id"], "args": t.get("args", []), "kwargs": t.get("kwargs", {})})
        elif spec["mode"] == "class":
            cases.append({"id": t["id"], "ctor": t.get("ctor", []), "ops": t.get("ops", [])})
        else:
            cases.append({"id": t["id"], "stdin": t.get("stdin") or ""})
    return {"mode": spec["mode"], "entry": spec["entry"], "cases": cases, "per_case_seconds": runner.PER_CASE_SECONDS}


def _matches(spec: dict, test: dict, result: dict) -> bool:
    actual = result.get("stdout") if spec["mode"] == "stdio" else result.get("value")
    if spec["compare"] == "validator":
        checker = compare.VALIDATORS.get(spec.get("validator") or "")
        if checker is None:
            return False
        try:
            return bool(checker({"args": test.get("args", []), "kwargs": test.get("kwargs", {})}, actual))
        except Exception:  # noqa: BLE001 - a validator must never crash grading; failing closed is correct
            return False
    return compare.values_match(actual, test["expected"], spec["compare"], spec.get("tolerance"), bool(spec.get("strict_types")))


def _hint_for(actual: Any, expected: Any) -> str:
    if actual is None and expected is not None:
        return " Your function returned None: did you forget `return`?"
    return ""


def grade(spec: dict, source: str, *, visible_only: bool) -> Grade:
    """Run `source` on the visible tests (a trial run) or on every test (a submission)."""
    tests = [t for t in spec["tests"] if t["visible"] or not visible_only]
    try:
        raw = runner.run(source, _runner_spec(spec, tests))
    except runner.RunnerBusy:
        return Grade("runner_error", 0, len(tests), message="The code runner is busy. Try again in a few seconds.")
    except runner.RunnerUnavailable as exc:
        return Grade("runner_error", 0, len(tests), message=str(exc))
    except ValueError:
        return Grade("runner_error", 0, len(tests), message="That submission is too large to run.")
    outcomes: list[TestOutcome] = []
    if raw.termination == "setup_failed":
        return Grade("runner_error", 0, len(tests), message="The code runner could not start. Try again.", wall_ms=raw.wall_ms)
    if raw.setup is not None:
        err = {"type": raw.setup.get("error_type"), "message": str(raw.setup.get("error_msg", ""))[:MAX_VISIBLE_MESSAGE], "line": raw.setup.get("line")}
        for t in tests:
            outcomes.append(TestOutcome(t["id"], t["label"], t["visible"], False, "error"))
        verdict = "compile_error" if raw.setup.get("setup") in ("compile_error", "missing_entry", "import_error") else "runtime_error"
        return Grade(verdict, 0, len(tests), outcomes, VERDICT_TEXT[verdict], err, raw.wall_ms)
    for t in tests:
        res = raw.results.get(t["id"])
        if res is None:
            outcomes.append(TestOutcome(t["id"], t["label"], t["visible"], False, "timeout" if raw.termination in ("timeout", "output_limit", "killed") else "not_run"))
            continue
        status = res.get("status")
        vis = t["visible"]
        out = TestOutcome(t["id"], t["label"], vis, False, "failed", ms=res.get("ms"))
        if vis and res.get("stdout"):
            out.stdout = str(res["stdout"])[:500]
        if status == "ok" and _matches(spec, t, res):
            out.passed, out.status = True, "passed"
        elif status == "ok":
            if vis:
                actual = res.get("stdout") if spec["mode"] == "stdio" else res.get("value")
                out.message = (f"Input: {t.get('input_repr', '')}\nExpected: {compare.describe(t['expected'])}\nGot: {compare.describe(actual)}" + _hint_for(actual, t["expected"]))[:MAX_VISIBLE_MESSAGE * 3]
        elif status == "timeout":
            out.status = "timeout"
        else:
            out.status = "error"
            if vis:
                where = f" (line {res['line']})" if res.get("line") else ""
                out.message = f"{res.get('error_type')}: {res.get('error_msg')}{where}"[:MAX_VISIBLE_MESSAGE]
        outcomes.append(out)
    passed = sum(1 for o in outcomes if o.passed)
    if passed == len(outcomes):
        verdict = "accepted"
    elif raw.termination == "output_limit":
        verdict = "output_limit"
    elif any(o.status == "timeout" for o in outcomes):
        verdict = "timeout"
    elif any(o.status == "error" for o in outcomes):
        verdict = "runtime_error"
    else:
        verdict = "wrong_answer"
    return Grade(verdict, passed, len(outcomes), outcomes, VERDICT_TEXT[verdict], None, raw.wall_ms)
