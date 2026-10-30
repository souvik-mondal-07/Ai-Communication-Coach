"""
Supervisor for the isolated Python runner (Phase 26).

It is the only code in the application that executes submitted Python, and it never does so in the API process: it starts
`launcher.py` as a separate OS process (see that file for the isolation layers) and reads back raw per-case outputs.

Defence in depth added here, on the supervisor side:
  * the child gets an EMPTY environment (no JWT secret, database URI, API keys) and cwd `/`; fds are closed; stdin is the job pipe;
  * if the API itself runs as root the launcher is started as `nobody`, so the sandbox identity is never root on the host;
  * a wall-clock deadline and a cap on bytes read from the child, enforced by killing its whole process group;
  * a global concurrency cap, so a burst of submissions queues briefly and is then refused instead of exhausting the host;
  * FAIL-CLOSED: `capabilities()` runs a self-test (a hostile probe program) once per process. If any isolation property cannot
    be demonstrated, `available` is False and no submitted code is ever run. On non-Linux hosts it is always False.

Expected outputs and reference solutions are never sent into the sandbox; only inputs and the submitted source go in.
"""

from __future__ import annotations

import json
import logging
import os
import select
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services.python_practice.sandbox import image as runtime_image

logger = logging.getLogger(__name__)

_DIR = Path(__file__).resolve().parent
SENTINEL = "@@R@@"

# --- Limits (constants, not user-configurable) ---------------------------------------------------------------------------------
MAX_SOURCE_CHARS = 10_000
MAX_CASES_PER_RUN = 60
MAX_OUTPUT_BYTES = 400_000
CPU_SECONDS = 4
MEMORY_BYTES = 384 * 1024 * 1024
MAX_PROCESSES = 12
MAX_OPEN_FILES = 48
MAX_FILE_BYTES = 262_144
TMP_BYTES = 2 * 1024 * 1024
PER_CASE_SECONDS = 1.5
MAX_CONCURRENT_RUNS = 2
QUEUE_WAIT_SECONDS = 4.0
SETUP_FAILED = 70
TIMEOUT_STATUS = 124

ISOLATION_LAYERS = (
    "Separate OS process (never in the API process); empty environment, cwd /, inherited descriptors closed",
    "Unprivileged identity: user namespace with a single mapped id (root is dropped to 'nobody' first); every capability dropped; no_new_privs",
    "Private mount namespace + chroot into a read-only runtime image containing only the interpreter and standard library",
    "No application files, /etc, /home, /proc or /sys inside the sandbox; /tmp is a 2 MB tmpfs; /work is read-only",
    "Network namespace with no interfaces: no external or loopback network access",
    "PID namespace: the program is PID 1, so killing it kills every process it started",
    "Resource limits: CPU time, address space, process count, open files, file size, no core dumps",
    "seccomp filter blocking namespace creation, mount, ptrace, bpf, keyrings and similar",
    "Wall-clock deadline, output byte cap, source size cap, and a global concurrency cap",
)


class RunnerUnavailable(Exception):
    pass


class RunnerBusy(Exception):
    pass


@dataclass
class RawRun:
    """What came back from one sandbox run. Never contains expected values."""

    setup: dict[str, Any] | None = None  # compile_error / import_error / missing_entry / ...
    results: dict[int, dict[str, Any]] = field(default_factory=dict)
    termination: str = "completed"  # completed | timeout | output_limit | killed | setup_failed
    wall_ms: int = 0
    detail: str | None = None


_launcher_source: str | None = None
_harness_source: str | None = None
_semaphore = threading.BoundedSemaphore(MAX_CONCURRENT_RUNS)
_state_lock = threading.Lock()
_state: dict[str, Any] | None = None


def _sources() -> tuple[str, str]:
    global _launcher_source, _harness_source
    if _launcher_source is None:
        _launcher_source = (_DIR / "launcher.py").read_text(encoding="utf-8")
        _harness_source = (_DIR / "harness.py").read_text(encoding="utf-8")
    return _launcher_source, _harness_source  # type: ignore[return-value]


def _limits(wall_seconds: float) -> dict[str, Any]:
    return {"cpu_seconds": CPU_SECONDS, "memory_bytes": MEMORY_BYTES, "processes": MAX_PROCESSES, "open_files": MAX_OPEN_FILES,
            "file_bytes": MAX_FILE_BYTES, "tmp_bytes": TMP_BYTES, "wall_seconds": wall_seconds}


def _kill_group(proc: subprocess.Popen) -> None:
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(proc.pid, sig)
        except (ProcessLookupError, PermissionError):
            pass
        if sig == signal.SIGTERM:
            try:
                proc.wait(timeout=0.4)
                return
            except subprocess.TimeoutExpired:
                continue


def _spawn(job: dict[str, Any], wall_seconds: float) -> RawRun:
    launcher, _ = _sources()
    kwargs: dict[str, Any] = {}
    if os.geteuid() == 0:
        kwargs.update(user=65534, group=65534, extra_groups=[])
    started = time.monotonic()
    proc = subprocess.Popen(
        [sys.executable, "-I", "-S", "-c", launcher],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env={}, cwd="/", close_fds=True, start_new_session=True, **kwargs,
    )
    run = RawRun()
    out_buf = bytearray()
    err_buf = bytearray()
    try:
        assert proc.stdin is not None and proc.stdout is not None and proc.stderr is not None
        try:
            proc.stdin.write(json.dumps(job).encode())
            proc.stdin.close()
        except BrokenPipeError:
            pass
        deadline = started + wall_seconds + 2.0  # the launcher enforces `wall_seconds`; this is the backstop
        fds = {proc.stdout.fileno(): out_buf, proc.stderr.fileno(): err_buf}
        open_fds = set(fds)
        while open_fds:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                run.termination = "timeout"
                _kill_group(proc)
                break
            ready, _, _ = select.select(list(open_fds), [], [], min(remaining, 0.25))
            for fd in ready:
                chunk = os.read(fd, 65536)
                if not chunk:
                    open_fds.discard(fd)
                    continue
                fds[fd].extend(chunk)
                if len(out_buf) + len(err_buf) > MAX_OUTPUT_BYTES:
                    run.termination = "output_limit"
                    _kill_group(proc)
                    open_fds.clear()
                    break
        try:
            code = proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            _kill_group(proc)
            code = proc.wait(timeout=2)
    finally:
        if proc.poll() is None:
            _kill_group(proc)
        for stream in (proc.stdout, proc.stderr):
            try:
                if stream:
                    stream.close()
            except OSError:
                pass
    run.wall_ms = int((time.monotonic() - started) * 1000)
    if run.termination == "completed":
        if code == SETUP_FAILED:
            run.termination = "setup_failed"
            run.detail = (err_buf.decode("utf-8", "replace").strip().splitlines() or ["setup failed"])[-1][:200]
        elif code == TIMEOUT_STATUS:
            run.termination = "timeout"
        elif code not in (0,):
            run.termination = "killed"
            run.detail = f"exit status {code}"
    for line in out_buf.decode("utf-8", "replace").splitlines():
        if not line.startswith(SENTINEL):
            continue
        try:
            item = json.loads(line[len(SENTINEL):])
        except ValueError:
            continue
        if "setup" in item:
            run.setup = item
        elif isinstance(item.get("id"), int):
            run.results[item["id"]] = item
    return run


def _execute(source: str, spec: dict[str, Any], wall_seconds: float) -> RawRun:
    img = runtime_image.get_image()
    _, harness = _sources()
    job = {
        "image": img.root, "python": img.python, "limits": _limits(wall_seconds), "seccomp": True,
        "files": {"harness.py": harness, "solution.py": source, "cases.json": json.dumps(spec)},
    }
    return _spawn(job, wall_seconds)


# --- Self-test -----------------------------------------------------------------------------------------------------------------

_PROBE = '''
def probe():
    import os, socket, ctypes, struct, time
    out = {}
    def can(fn):
        try:
            fn(); return True
        except BaseException:
            return False
    out["env_keys"] = sorted(os.environ)
    out["root_listing"] = sorted(os.listdir("/"))
    out["read_etc"] = can(lambda: open("/etc/passwd").read())
    out["read_proc"] = can(lambda: os.listdir("/proc"))
    out["read_home"] = can(lambda: os.listdir("/home"))
    out["write_work"] = can(lambda: open("/work/x", "w"))
    out["write_lib"] = can(lambda: open("/usr/x", "w"))
    out["write_tmp"] = can(lambda: open("/tmp/x", "w").write("a"))
    out["net_ip"] = can(lambda: socket.create_connection(("1.1.1.1", 53), timeout=1))
    out["net_loop"] = can(lambda: socket.create_connection(("127.0.0.1", 9), timeout=1))
    out["dns"] = can(lambda: socket.gethostbyname("example.com"))
    out["unshare"] = can(lambda: os.unshare(os.CLONE_NEWUSER))
    libc = ctypes.CDLL(None, use_errno=True)
    out["mount"] = libc.mount(b"x", b"/tmp", b"tmpfs", 0, None) == 0
    out["chroot"] = can(lambda: os.chroot("/tmp"))
    hdr = ctypes.create_string_buffer(struct.pack("<Ii", 0x20080522, 0), 8)
    dat = ctypes.create_string_buffer(24)
    libc.syscall(125, hdr, dat)
    out["caps"] = list(struct.unpack("<6I", dat.raw))
    out["alloc_2gb"] = can(lambda: bytearray(2 * 1024 ** 3))
    kids = []
    for _ in range(60):
        try:
            pid = os.fork()
        except OSError:
            break
        if pid == 0:
            time.sleep(2); os._exit(0)
        kids.append(pid)
    out["forks"] = len(kids)
    out["pid"] = os.getpid()
    return out
'''

_ALLOWED_ENV = {"PYTHONHASHSEED", "PYTHONDONTWRITEBYTECODE", "PYTHONIOENCODING", "PYTHONUTF8", "LANG", "HOME"}
_FORBIDDEN_ROOT = {"home", "root", "etc", "var", "proc", "sys", "run", "opt", "srv", "mnt", "media", "boot", "usr/local"}


def _evaluate_probe(raw: RawRun) -> list[str]:
    problems: list[str] = []
    if raw.termination == "setup_failed":
        return [f"the sandbox could not be created ({raw.detail or 'unknown reason'})"]
    if raw.setup is not None or 0 not in raw.results or raw.results[0].get("status") != "ok":
        return ["the probe program did not run inside the sandbox"]
    v = raw.results[0]["value"]
    if not set(v["env_keys"]) <= _ALLOWED_ENV:
        problems.append("unexpected environment variables are visible")
    if set(v["root_listing"]) & _FORBIDDEN_ROOT:
        problems.append("host directories are visible")
    for key, label in (("read_etc", "/etc is readable"), ("read_proc", "/proc is readable"), ("read_home", "/home is readable"),
                       ("write_work", "/work is writable"), ("write_lib", "the runtime image is writable"), ("net_ip", "outbound network works"),
                       ("net_loop", "loopback network works"), ("dns", "name resolution works"), ("unshare", "namespaces can be created"),
                       ("mount", "mounting is possible"), ("chroot", "chroot is possible"), ("alloc_2gb", "the memory limit is not enforced")):
        if v.get(key):
            problems.append(label)
    if not v.get("write_tmp"):
        problems.append("/tmp is not writable")
    if any(v["caps"][:6]):
        problems.append("capabilities remain")
    if v["forks"] >= 40:
        problems.append("the process limit is not enforced")
    return problems


def capabilities(force: bool = False) -> dict[str, Any]:
    """Whether submitted code can be run, and why not. The self-test runs once per process; failures never raise."""
    global _state
    with _state_lock:
        if _state is not None and not force:
            return _state
        state: dict[str, Any] = {"available": False, "reason": None, "platform": sys.platform, "python_version": ".".join(map(str, sys.version_info[:3])),
                                 "layers": list(ISOLATION_LAYERS), "limits": {"wall_seconds": 6, "cpu_seconds": CPU_SECONDS, "memory_mb": MEMORY_BYTES // 2**20,
                                 "processes": MAX_PROCESSES, "source_chars": MAX_SOURCE_CHARS, "output_bytes": MAX_OUTPUT_BYTES, "per_case_seconds": PER_CASE_SECONDS}}
        if not settings.python_runner_enabled:
            state["reason"] = "Code execution is switched off by the administrator (PYTHON_RUNNER_ENABLED=false)."
        elif not sys.platform.startswith("linux"):
            state["reason"] = "Code execution needs Linux namespaces and is not available on this operating system."
        else:
            try:
                raw = _execute(_PROBE, {"mode": "function", "entry": "probe", "cases": [{"id": 0, "args": []}], "per_case_seconds": 4}, 8)
                problems = _evaluate_probe(raw)
                if problems:
                    state["reason"] = "Isolation could not be verified on this host: " + "; ".join(problems) + "."
                else:
                    state["available"] = True
            except runtime_image.ImageError as exc:
                state["reason"] = f"The runtime image could not be built ({exc})."
            except Exception as exc:  # noqa: BLE001
                logger.warning("Python runner self-test failed", exc_info=True)
                state["reason"] = f"The runner self-test failed ({type(exc).__name__})."
        if not state["available"]:
            logger.warning("Python code runner DISABLED: %s", state["reason"])
        _state = state
        return state


def reset_for_tests() -> None:
    global _state
    with _state_lock:
        _state = None


def run(source: str, spec: dict[str, Any], wall_seconds: float = 6.0) -> RawRun:
    """Run `source` against `spec` (mode, entry, cases[id,...]). Raises RunnerUnavailable / RunnerBusy; never runs unverified."""
    if not capabilities()["available"]:
        raise RunnerUnavailable(capabilities()["reason"] or "The code runner is unavailable.")
    if len(source) > MAX_SOURCE_CHARS:
        raise ValueError("source too large")
    if len(spec.get("cases", [])) > MAX_CASES_PER_RUN:
        raise ValueError("too many cases")
    if not _semaphore.acquire(timeout=QUEUE_WAIT_SECONDS):
        raise RunnerBusy("The code runner is busy. Try again in a few seconds.")
    try:
        return _execute(source, spec, wall_seconds)
    finally:
        _semaphore.release()
