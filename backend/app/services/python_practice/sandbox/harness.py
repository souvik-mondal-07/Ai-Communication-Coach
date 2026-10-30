"""
In-sandbox test harness (Phase 26). Standard library only; no imports from the application.

It runs INSIDE the isolated runner (see launcher.py). It reads `cases.json` and `solution.py` from /work, runs the submitted code
on each case and streams one result line per case to stdout. It never receives expected outputs: grading happens in the
parent process by comparing these raw outputs with server-side expected data, so nothing the submitted code does can read the
answer key.

Modes
  function   call `entry(*args, **kwargs)`
  class      construct `entry(*ctor)` then call methods in order (`ops`), collecting each return value
  stdio      run the whole program with the case's stdin text and capture what it prints

`to_jsonable` is also imported by the parent to canonicalise expected values with exactly the same rules.
"""

from __future__ import annotations

import builtins
import io
import json
import math
import signal
import sys
import time
import traceback

SENTINEL = "@@R@@"
MAX_STDOUT_PER_CASE = 4000
MAX_ITEMS = 20000


class _Budget:
    def __init__(self) -> None:
        self.items = 0


def to_jsonable(value, _depth: int = 0, _budget: _Budget | None = None):
    """Map any Python value onto tagged JSON so type-sensitive comparisons survive the round trip."""
    budget = _budget or _Budget()
    budget.items += 1
    if budget.items > MAX_ITEMS or _depth > 25:
        return {"__repr__": "<too large or too deep>"}
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, int):
        return value if abs(value) < 10**15 else {"__int__": str(value)}
    if isinstance(value, float):
        if math.isnan(value):
            return {"__float__": "nan"}
        if math.isinf(value):
            return {"__float__": "inf" if value > 0 else "-inf"}
        return value
    if isinstance(value, (list, tuple)):
        tag = "__tuple__" if isinstance(value, tuple) else None
        items = [to_jsonable(v, _depth + 1, budget) for v in value]
        return {tag: items} if tag else items
    if isinstance(value, (set, frozenset)):
        items = [to_jsonable(v, _depth + 1, budget) for v in value]
        return {"__set__": sorted(items, key=lambda x: json.dumps(x, sort_keys=True))}
    if isinstance(value, dict):
        if all(isinstance(k, str) for k in value) and not any(k.startswith("__") and k.endswith("__") for k in value):
            return {k: to_jsonable(v, _depth + 1, budget) for k, v in value.items()}
        return {"__dict__": [[to_jsonable(k, _depth + 1, budget), to_jsonable(v, _depth + 1, budget)] for k, v in value.items()]}
    if isinstance(value, (bytes, bytearray)):
        return {"__bytes__": bytes(value).hex()}
    if isinstance(value, complex):
        return {"__repr__": repr(value)}
    return {"__repr__": f"<{type(value).__name__}>"}


class _CaseTimeout(BaseException):
    pass


def _alarm(_signum, _frame):
    raise _CaseTimeout()


def _short(text: str, n: int = 200) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[: n - 1] + "…"


def _where(exc: BaseException) -> int | None:
    line = None
    for frame in traceback.extract_tb(exc.__traceback__):
        if frame.filename == "<solution>":
            line = frame.lineno
    return line


class _Capture(io.StringIO):
    def __init__(self) -> None:
        super().__init__()
        self.truncated = False

    def write(self, s):  # type: ignore[override]
        room = MAX_STDOUT_PER_CASE - self.tell()
        if room <= 0:
            self.truncated = True
            return len(s)
        if len(s) > room:
            self.truncated = True
            s = s[:room]
        return super().write(s)


def _emit(real_out, payload: dict) -> None:
    real_out.write(SENTINEL + json.dumps(payload, separators=(",", ":")) + "\n")
    real_out.flush()


def _run_case(call, per_case: float, stdin_text: str | None):
    cap = _Capture()
    real_in, real_out_, real_err = sys.stdin, sys.stdout, sys.stderr
    started = time.perf_counter()
    result: dict = {}
    sys.stdout = cap
    sys.stderr = io.StringIO()
    if stdin_text is not None:
        sys.stdin = io.StringIO(stdin_text)
    signal.setitimer(signal.ITIMER_REAL, per_case)
    try:
        value = call()
        result = {"status": "ok", "value": to_jsonable(value)}
    except _CaseTimeout:
        result = {"status": "timeout"}
    except SystemExit as exc:
        result = {"status": "ok", "value": None, "exit": _short(exc.code if exc.code is not None else 0, 40)}
    except BaseException as exc:  # noqa: BLE001 - the submitted code may raise anything
        result = {"status": "error", "error_type": type(exc).__name__, "error_msg": _short(exc), "line": _where(exc)}
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        sys.stdout, sys.stdin, sys.stderr = real_out_, real_in, real_err
    result["stdout"] = cap.getvalue()
    result["stdout_truncated"] = cap.truncated
    result["ms"] = int((time.perf_counter() - started) * 1000)
    return result


def main() -> int:
    real_out = sys.stdout
    with open("/work/cases.json", encoding="utf-8") as fh:
        spec = json.load(fh)
    with open("/work/solution.py", encoding="utf-8") as fh:
        source = fh.read()
    signal.signal(signal.SIGALRM, _alarm)
    sys.setrecursionlimit(spec.get("recursion_limit", 1500))
    mode = spec["mode"]
    per_case = float(spec.get("per_case_seconds", 1.5))
    ns: dict = {"__name__": "solution" if mode != "stdio" else "__main__", "__builtins__": builtins}

    try:
        code = compile(source, "<solution>", "exec", dont_inherit=True)  # never inherit this file's __future__ flags
    except SyntaxError as exc:
        _emit(real_out, {"setup": "compile_error", "error_type": "SyntaxError", "error_msg": _short(exc.msg or "invalid syntax"), "line": exc.lineno})
        return 0

    if mode != "stdio":
        cap = _Capture()
        sys.stdout = cap
        signal.setitimer(signal.ITIMER_REAL, per_case)
        try:
            exec(code, ns)  # noqa: S102 - this is the sandbox; the submitted code is the whole point
            err = None
        except _CaseTimeout:
            err = {"setup": "import_timeout", "error_type": "TimeoutError", "error_msg": "Top-level code took too long.", "line": None}
        except BaseException as exc:  # noqa: BLE001
            err = {"setup": "import_error", "error_type": type(exc).__name__, "error_msg": _short(exc), "line": _where(exc)}
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            sys.stdout = real_out
        if err:
            _emit(real_out, err)
            return 0
        entry = ns.get(spec["entry"])
        if entry is None or not callable(entry):
            _emit(real_out, {"setup": "missing_entry", "error_type": "NameError", "error_msg": f"Define `{spec['entry']}` exactly as the problem states.", "line": None})
            return 0

    for case in spec["cases"]:
        if mode == "function":
            args, kwargs = case.get("args", []), case.get("kwargs", {})
            res = _run_case(lambda: entry(*args, **kwargs), per_case, None)
        elif mode == "class":
            def call(case=case):
                obj = entry(*case.get("ctor", []))
                out = []
                for name, a in case["ops"]:
                    out.append(getattr(obj, name)(*a))
                return out
            res = _run_case(call, per_case, None)
        else:
            def call(case=case):
                fresh = {"__name__": "__main__", "__builtins__": builtins}
                exec(code, fresh)  # noqa: S102
            res = _run_case(call, per_case, case.get("stdin", ""))
        res["id"] = case["id"]
        _emit(real_out, res)
    return 0


if __name__ == "__main__":
    sys.exit(main())
