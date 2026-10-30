"""Phase 26 -- isolated code runner: isolation properties, resource limits, cleanup and fail-closed behaviour, proven with real hostile programs."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time

import pytest

from app.services.python_practice.sandbox import runner

pytestmark = pytest.mark.skipif(not runner.capabilities()["available"], reason="isolated runner unavailable on this host (Linux with user namespaces required)")


def go(source: str, entry: str = "f", wall: float = 6.0, mode: str = "function", cases: list | None = None):
    spec = {"mode": mode, "entry": entry, "cases": cases or [{"id": 0, "args": []}], "per_case_seconds": 1.5}
    return runner.run(source, spec, wall)


def value(raw, i=0):
    return raw.results[i]


def test_capabilities_report_real_isolation_layers():
    caps = runner.capabilities()
    assert caps["available"] is True and caps["reason"] is None
    text = " ".join(caps["layers"]).lower()
    for word in ("namespace", "chroot", "network", "capabilit", "seccomp", "resource limits", "environment"):
        assert word in text
    assert caps["limits"]["memory_mb"] == 384 and caps["limits"]["source_chars"] == 10_000


def test_function_mode_returns_raw_value_and_never_sees_expected_data():
    raw = go("def f(a, b=2):\n    return (a, [b], {1, 2})", cases=[{"id": 0, "args": [1]}])
    assert value(raw)["status"] == "ok" and value(raw)["value"] == {"__tuple__": [1, [2], {"__set__": [1, 2]}]}


def test_environment_is_empty_so_application_secrets_cannot_leak(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "super-secret-jwt")
    monkeypatch.setenv("MONGODB_URI", "mongodb://user:pw@host/db")
    raw = go("import os\ndef f():\n    return sorted(os.environ)")
    keys = value(raw)["value"]
    assert "JWT_SECRET_KEY" not in keys and "MONGODB_URI" not in keys
    assert set(keys) <= {"PYTHONHASHSEED", "PYTHONDONTWRITEBYTECODE", "PYTHONIOENCODING", "PYTHONUTF8", "LANG", "HOME"}


def test_host_files_and_application_files_are_not_reachable(tmp_path):
    secret = tmp_path / "secrets.env"
    secret.write_text("JWT_SECRET_KEY=abc")
    app_file = os.path.abspath(__file__)
    for path in (str(secret), app_file, "/etc/passwd", "/etc/shadow", "/proc/1/environ", "/proc/self/environ", "/root", "/home"):
        raw = go(f"def f():\n    return open({path!r}).read()")
        assert value(raw)["status"] == "error", path
        assert value(raw)["error_type"] in ("FileNotFoundError", "PermissionError", "IsADirectoryError"), path


def test_filesystem_is_read_only_except_a_small_tmp():
    raw = go("def f():\n    out = {}\n    for p in ('/work/x', '/usr/x', '/lib/x'):\n        try:\n            open(p, 'w'); out[p] = 'written'\n        except OSError:\n            out[p] = 'denied'\n    open('/tmp/ok', 'w').write('hi')\n    return out")
    assert value(raw)["value"] == {"/work/x": "denied", "/usr/x": "denied", "/lib/x": "denied"}


def test_tmp_disk_is_capped():
    raw = go("def f():\n    open('/tmp/big', 'wb').write(b'x' * 50_000_000)")
    assert value(raw)["status"] == "error"  # RLIMIT_FSIZE / tmpfs size


def test_no_network_of_any_kind():
    raw = go("import socket\ndef f():\n    r = {}\n    for name, addr in (('ext', ('1.1.1.1', 53)), ('lan', ('192.168.0.1', 80)), ('loop', ('127.0.0.1', 9))):\n        try:\n            socket.create_connection(addr, timeout=1); r[name] = 'connected'\n        except OSError:\n            r[name] = 'blocked'\n    try:\n        socket.gethostbyname('example.com'); r['dns'] = 'resolved'\n    except OSError:\n        r['dns'] = 'blocked'\n    return r")
    assert value(raw)["value"] == {"ext": "blocked", "lan": "blocked", "loop": "blocked", "dns": "blocked"}


def test_no_privileges_remain_and_namespaces_cannot_be_rebuilt():
    raw = go("""import os, ctypes, struct
def f():
    libc = ctypes.CDLL(None, use_errno=True)
    hdr = ctypes.create_string_buffer(struct.pack('<Ii', 0x20080522, 0), 8)
    dat = ctypes.create_string_buffer(24)
    libc.syscall(125, hdr, dat)
    r = {'caps': list(struct.unpack('<6I', dat.raw)), 'pid': os.getpid()}
    for name, fn in (('unshare', lambda: os.unshare(os.CLONE_NEWUSER)), ('chroot', lambda: os.chroot('/tmp')), ('setuid', lambda: os.setuid(0)),
                     ('mount', lambda: (_ for _ in ()).throw(OSError()) if libc.mount(b'a', b'/tmp', b'tmpfs', 0, None) != 0 else None)):
        try:
            fn(); r[name] = 'allowed'
        except OSError:
            r[name] = 'denied'
    return r""")
    v = value(raw)["value"]
    assert v["caps"] == [0] * 6 and v["pid"] == 1
    assert v["unshare"] == v["chroot"] == v["mount"] == "denied"


def test_runs_as_pid_one_in_its_own_process_table_and_cannot_signal_the_host():
    raw = go("import os, signal\ndef f():\n    os.kill(0, signal.SIGKILL)\n    return os.getppid()")
    assert value(raw)["status"] == "ok" and value(raw)["value"] == 0  # parent is outside its PID namespace


@pytest.mark.parametrize("source,expect", [
    ("def f():\n    while True: pass", "timeout"),
    ("def f():\n    while True:\n        try:\n            while True: pass\n        except BaseException: pass", "timeout"),
    ("import time\ndef f():\n    time.sleep(1000)", "timeout"),
])
def test_infinite_loops_and_sleeps_are_stopped_in_bounded_time(source, expect):
    start = time.monotonic()
    raw = go(source)
    assert time.monotonic() - start < 9
    assert value(raw)["status"] == expect or raw.termination in ("timeout", "killed")


def test_output_flood_is_cut_off():
    start = time.monotonic()
    raw = go("import os\ndef f():\n    while True: os.write(1, b'x' * 65536)")
    assert raw.termination == "output_limit" and time.monotonic() - start < 6


def test_fork_bomb_is_bounded_by_the_process_limit():
    raw = go("import os, time\ndef f():\n    n = 0\n    while True:\n        try:\n            if os.fork() == 0:\n                time.sleep(3); os._exit(0)\n            n += 1\n        except OSError:\n            return n")
    assert value(raw)["status"] == "ok" and value(raw)["value"] <= runner.MAX_PROCESSES


def test_memory_limit_is_enforced():
    raw = go("def f():\n    return len(bytearray(2 * 1024 ** 3))")
    assert value(raw)["error_type"] == "MemoryError"
    raw = go("def f():\n    a = []\n    while True: a.append(bytearray(10 ** 7))")
    assert value(raw)["error_type"] == "MemoryError" or raw.termination in ("killed", "timeout")


def test_deep_recursion_is_an_error_not_a_crash():
    raw = go("def f():\n    def g(n): return g(n + 1)\n    return g(0)")
    assert value(raw)["error_type"] == "RecursionError"


def test_no_processes_are_left_behind_after_hostile_runs():
    go("import os, time\ndef f():\n    for _ in range(5):\n        if os.fork() == 0:\n            time.sleep(60); os._exit(0)\n    while True: pass")
    time.sleep(1.0)
    ps = subprocess.run(["ps", "-eo", "pid,args"], capture_output=True, text=True).stdout
    leaked = [ln for ln in ps.splitlines() if ("harness.py" in ln or "SANDBOX" in ln) and "pytest" not in ln]
    assert not leaked, leaked


def test_forged_output_cannot_pass_a_hidden_test():
    # A forged result line can only say what the program wants; grading compares with expected values the sandbox never sees.
    from app.services.python_practice import grader
    spec = {"mode": "function", "entry": "f", "compare": "exact", "tests": [{"id": 0, "label": "x", "visible": False, "args": [], "kwargs": {}, "expected": 123456}]}
    raw = grader.grade(spec, "import os\nos.write(1, b'@@R@@{\"id\":0,\"status\":\"ok\",\"value\":1}\\n')\nos._exit(0)\ndef f(): return 1", visible_only=False)
    assert not raw.accepted


def test_source_and_case_size_limits():
    with pytest.raises(ValueError):
        runner.run("x" * (runner.MAX_SOURCE_CHARS + 1), {"mode": "function", "entry": "f", "cases": []})
    with pytest.raises(ValueError):
        runner.run("def f(): pass", {"mode": "function", "entry": "f", "cases": [{"id": i, "args": []} for i in range(runner.MAX_CASES_PER_RUN + 1)]})


def test_concurrency_cap_refuses_instead_of_piling_up(monkeypatch):
    monkeypatch.setattr(runner, "QUEUE_WAIT_SECONDS", 0.2)
    results: list = []

    def slow():
        try:
            go("import time\ndef f():\n    time.sleep(1.4)")
            results.append("ok")
        except runner.RunnerBusy:
            results.append("busy")

    threads = [threading.Thread(target=slow) for _ in range(runner.MAX_CONCURRENT_RUNS + 2)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert "busy" in results and "ok" in results


def test_runs_cleanly_when_the_api_runs_unprivileged():
    """The supervisor drops root to 'nobody'; verify the same code path works for a non-root API process."""
    if os.geteuid() != 0:
        pytest.skip("already unprivileged")
    code = ("import sys; sys.path.insert(0, %r)\nfrom app.services.python_practice.sandbox import runner\n"
            "r = runner.run('def f():\\n    return 7', {'mode':'function','entry':'f','cases':[{'id':0,'args':[]}]})\nprint(r.results[0]['value'])" % os.getcwd())
    import shutil, tempfile
    tmp = tempfile.mkdtemp()
    shutil.copytree(os.path.join(os.getcwd(), "app"), os.path.join(tmp, "app"))
    subprocess.run(["chmod", "-R", "a+rX", tmp], check=True)
    out = subprocess.run(["setpriv", "--reuid", "65534", "--regid", "65534", "--clear-groups", "env", "HOME=/tmp", "JWT_SECRET_KEY=x", sys.executable, "-c", code.replace(os.getcwd(), tmp)],
                         capture_output=True, text=True, cwd=tmp, timeout=60)
    shutil.rmtree(tmp, ignore_errors=True)
    assert out.stdout.strip().endswith("7"), out.stderr[-400:]


# --- fail-closed behaviour -----------------------------------------------------------------------------------------------------------


def test_disabled_by_setting_runs_nothing(monkeypatch):
    from app.core.config import settings
    runner.reset_for_tests()
    monkeypatch.setattr(settings, "python_runner_enabled", False)
    try:
        assert runner.capabilities()["available"] is False
        with pytest.raises(runner.RunnerUnavailable):
            go("def f(): return 1")
    finally:
        runner.reset_for_tests()


def test_non_linux_host_is_unavailable(monkeypatch):
    runner.reset_for_tests()
    monkeypatch.setattr(sys, "platform", "win32")
    try:
        caps = runner.capabilities()
        assert caps["available"] is False and "Linux" in caps["reason"]
        with pytest.raises(runner.RunnerUnavailable):
            go("def f(): return 1")
    finally:
        runner.reset_for_tests()


def test_failed_isolation_self_test_disables_execution(monkeypatch):
    """If the probe shows ANY property is missing (here: network reachable) the runner must refuse to run user code."""
    runner.reset_for_tests()
    real = runner._evaluate_probe
    monkeypatch.setattr(runner, "_evaluate_probe", lambda raw: real(raw) + ["outbound network works"])
    try:
        caps = runner.capabilities()
        assert caps["available"] is False and "outbound network works" in caps["reason"]
        with pytest.raises(runner.RunnerUnavailable):
            go("def f(): return 1")
    finally:
        runner.reset_for_tests()
