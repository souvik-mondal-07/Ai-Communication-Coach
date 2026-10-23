"""
TEST/CLI-ONLY runner for TRUSTED, repository-owned seed code.

This is not an execution service for user submissions.
On POSIX, child processes receive CPU, address-space and file-size limits.
On Windows, the child has a wall-clock timeout and this runner applies a
best-effort 1 MiB quota to writes made through builtins.open. That is not a
complete OS sandbox: trusted seed code only; never run user-submitted code.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

if os.name == "posix":
    import resource
else:
    resource = None

_RUNNER = r"""
import builtins
import json
import sys

# Windows has no resource.RLIMIT_FSIZE. For this trusted-seed verifier, limit
# writes made through builtins.open so oversized writes are rejected. This is
# NOT a sandbox for arbitrary Python; code can bypass this wrapper with OS APIs.
_MAX_FILE_SIZE = 1024 * 1024
_real_open = builtins.open


class _LimitedWriter:
    def __init__(self, file_obj, max_size):
        self._file = file_obj
        self._max_size = max_size
        try:
            self._written = self._file.tell()
        except (OSError, AttributeError):
            self._written = 0

    def write(self, data):
        size = len(data.encode("utf-8")) if isinstance(data, str) else len(data)
        if self._written + size > self._max_size:
            raise OSError("file size quota exceeded")
        result = self._file.write(data)
        self._written += size
        return result

    def writelines(self, lines):
        for line in lines:
            self.write(line)

    def __getattr__(self, name):
        return getattr(self._file, name)

    def __enter__(self):
        self._file.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb):
        return self._file.__exit__(exc_type, exc, tb)


def _limited_open(file, mode="r", *args, **kwargs):
    obj = _real_open(file, mode, *args, **kwargs)
    if any(flag in mode for flag in ("w", "a", "x", "+")):
        return _LimitedWriter(obj, _MAX_FILE_SIZE)
    return obj


builtins.open = _limited_open

data = json.loads(sys.stdin.read())
ns = {}
exec(compile(data["source"], "<seed>", "exec"), ns)
out = {}
for case in data["calls"]:
    try:
        res = ns[data["function"]](*case)
        out_value = json.loads(json.dumps(res, allow_nan=True))
        out[len(out)] = {"ok": True, "value": out_value}
    except BaseException as exc:
        out[len(out)] = {"ok": False, "error": type(exc).__name__}
print(json.dumps(out))
"""


def _limits():
    """Apply POSIX resource limits to the child process."""
    if resource is None:
        return
    resource.setrlimit(resource.RLIMIT_CPU, (3, 3))
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_FSIZE, (1024 * 1024, 1024 * 1024))


def _run_python(args, *, input=None, timeout=5.0, cwd=None):
    kwargs = {
        "input": input,
        "capture_output": True,
        "text": True,
        "timeout": timeout,
        "cwd": cwd,
        "env": {},
    }
    if os.name == "posix":
        kwargs["preexec_fn"] = _limits
    return subprocess.run(args, **kwargs)


def run_calls(source: str, function: str, calls: list[list], timeout: float = 5.0) -> list[dict]:
    """Run a trusted reference function for each supplied argument list."""
    payload = json.dumps({"source": source, "function": function, "calls": calls})
    with tempfile.TemporaryDirectory() as tmp:
        try:
            proc = _run_python(
                [sys.executable, "-I", "-c", _RUNNER],
                input=payload,
                timeout=timeout,
                cwd=tmp,
            )
        except subprocess.TimeoutExpired:
            return [{"ok": False, "error": "Timeout"} for _ in calls]

    if proc.returncode != 0 or not proc.stdout.strip():
        stderr_lines = proc.stderr.strip().splitlines()
        error = stderr_lines[-1][:120] if stderr_lines else "crash"
        return [{"ok": False, "error": error} for _ in calls]
    try:
        parsed = json.loads(proc.stdout)
        return [parsed[str(i)] for i in range(len(calls))]
    except (json.JSONDecodeError, KeyError, TypeError):
        return [{"ok": False, "error": "Invalid runner output"} for _ in calls]


def check_solution(spec: dict) -> list[str]:
    """Run a coding spec's reference solution against its test cases."""
    tests = spec["test_cases"]
    results = run_calls(spec["reference_solution"], spec["function_name"], [t["args"] for t in tests])
    failures = []
    for t, r in zip(tests, results):
        if not r["ok"]:
            failures.append(f"{t['label']}: raised {r['error']}")
        elif r["value"] != t["expected"]:
            failures.append(f"{t['label']}: expected {t['expected']!r}, got {r['value']!r}")
    return failures


def _splice(code: str, replacement: str) -> str:
    out = []
    for line in code.split("\n"):
        if line.rstrip().endswith("# <<<"):
            indent = line[: len(line) - len(line.lstrip())]
            out.append(indent + replacement)
        else:
            out.append(line)
    return "\n".join(out)


def check_line_question(q: dict) -> list[str]:
    """Verify fill-line/fix-bug options against their expected test cases."""
    chk = q["verification"]["line_check"]
    problems = []
    for idx, option in enumerate(q["options"]):
        results = run_calls(
            _splice(q["code"], option), chk["function"], [t[0] for t in chk["tests"]], timeout=4.0
        )
        passed = len(results) == len(chk["tests"]) and all(
            r["ok"] and r["value"] == t[1] for r, t in zip(results, chk["tests"])
        )
        if idx == q["correct_index"] and not passed:
            problems.append(f"correct option does not pass the tests: {option!r}")
        if idx != q["correct_index"] and passed:
            problems.append(f"wrong option also passes the tests: {option!r}")
    return problems


def check_snippet(q: dict) -> str | None:
    """Run a trusted output-prediction snippet and compare its stdout."""
    try:
        proc = _run_python(
            [sys.executable, "-I", "-c", q["code"]], timeout=5, cwd=tempfile.gettempdir()
        )
    except subprocess.TimeoutExpired:
        return "timeout"
    if proc.returncode != 0:
        stderr_lines = proc.stderr.strip().splitlines()
        return f"crash: {stderr_lines[-1] if stderr_lines else '?'}"
    got = proc.stdout.rstrip("\n")
    expected = q["verification"]["expected"].rstrip("\n")
    return None if got.strip() == expected.strip() else f"printed {got!r}, declared {expected!r}"
