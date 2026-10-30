"""
Sandbox launcher (Phase 26). Runs as a standalone script: `python -I -S launcher.py`, with a JSON job on stdin.

It is deliberately self-contained (standard library + ctypes only) and imports nothing from the application.

What it builds before the submitted program starts, in order:

  1. a NEW USER NAMESPACE mapping a single id to the launcher's own (unprivileged) identity -- no host privilege is gained, and
     the launcher is never root on the host (the supervisor drops root to `nobody` first if the API itself runs as root);
  2. new MOUNT, PID, NETWORK, IPC and UTS namespaces: a private view of the filesystem, a process table in which the program is
     PID 1 (killing it kills everything it started), and a network namespace with no interfaces at all (no external access);
  3. a private filesystem: the read-only runtime image (interpreter + stdlib only) with small size-capped tmpfs mounts for /tmp,
     /work and /dev, then `chroot` into it -- no application files, secrets, /etc, /home or /proc exist in that view;
  4. resource limits (CPU seconds, address space, processes, open files, file size, core dumps);
  5. every capability dropped (bounding, ambient, effective, permitted, inheritable), `no_new_privs`, and a seccomp filter that
     blocks namespace creation, mounting, ptrace, BPF, keyrings and similar, so the program cannot rebuild privileges;
  6. `exec` of the interpreter on the harness with an empty, fixed environment and stdin from /dev/null.

If any step fails the launcher exits with status 70 and a one-line reason: it fails CLOSED and never runs the program unconfined.
Exit statuses: 0..n program status; 70 setup failed; 124 wall-clock limit hit; 128+N killed by signal N.
"""

from __future__ import annotations

import ctypes
import errno
import json
import os
import platform
import resource
import signal
import struct
import sys
import time

SETUP_FAILED = 70
TIMEOUT = 124

MS_RDONLY, MS_NOSUID, MS_NODEV, MS_NOEXEC = 1, 2, 4, 8
MS_REMOUNT, MS_BIND, MS_REC, MS_PRIVATE = 32, 4096, 16384, 1 << 18

PR_SET_PDEATHSIG, PR_CAPBSET_DROP, PR_SET_NO_NEW_PRIVS, PR_CAP_AMBIENT, PR_SET_SECCOMP = 1, 24, 38, 47, 22
PR_CAP_AMBIENT_CLEAR_ALL = 4
SECCOMP_MODE_FILTER = 2

_libc = ctypes.CDLL(None, use_errno=True)
_libc.syscall.restype = ctypes.c_long


class SetupError(Exception):
    pass


def _check(rc: int, what: str) -> None:
    if rc != 0:
        raise SetupError(f"{what}: {os.strerror(ctypes.get_errno())}")


def _mount(source: str | None, target: str, fstype: str | None, flags: int, data: str | None = None) -> None:
    rc = _libc.mount(source.encode() if source else None, target.encode(), fstype.encode() if fstype else None, ctypes.c_ulong(flags), data.encode() if data else None)
    _check(rc, f"mount {target}")


# --- seccomp ----------------------------------------------------------------------------------------------------------------

_ARCH = {"x86_64": 0xC000003E, "aarch64": 0xC00000B7}
# syscall numbers (x86_64, aarch64) denied with EPERM. The program has no capabilities anyway; this removes the kernel attack
# surface that unprivileged user namespaces would otherwise expose (nested namespaces, mounts, ptrace, bpf, keyrings, ...).
_DENY = {
    "unshare": (272, 97), "setns": (308, 268), "mount": (165, 40), "umount2": (166, 39), "pivot_root": (155, 41), "chroot": (161, 51),
    "ptrace": (101, 117), "process_vm_readv": (310, 270), "process_vm_writev": (311, 271), "kexec_load": (246, 104), "init_module": (175, 105),
    "finit_module": (313, 273), "delete_module": (176, 106), "bpf": (321, 280), "perf_event_open": (298, 241), "userfaultfd": (323, 282),
    "keyctl": (250, 219), "add_key": (248, 217), "request_key": (249, 218), "open_by_handle_at": (304, 265), "name_to_handle_at": (303, 264),
    "reboot": (169, 142), "swapon": (167, 224), "swapoff": (168, 225), "mount_setattr": (442, 442), "move_mount": (429, 429), "open_tree": (428, 428),
    "fsopen": (430, 430), "fsmount": (432, 432), "fspick": (433, 433), "sethostname": (170, 161), "setdomainname": (171, 162), "acct": (163, 89),
    "personality": (135, 92), "iopl": (172, -1), "ioperm": (173, -1), "modify_ldt": (154, -1), "quotactl": (179, 60), "lookup_dcookie": (212, 18),
    "io_uring_setup": (425, 425), "io_uring_enter": (426, 426), "io_uring_register": (427, 427), "pidfd_getfd": (438, 438),
}
_CLONE_NS_FLAGS = 0x7E020000  # CLONE_NEWNS|NEWCGROUP|NEWUTS|NEWIPC|NEWUSER|NEWPID|NEWNET (+ NEWTIME bit)
_NR_CLONE = {"x86_64": 56, "aarch64": 220}
_NR_CLONE3 = {"x86_64": 435, "aarch64": 435}


def _bpf(code: int, jt: int, jf: int, k: int) -> bytes:
    return struct.pack("<HBBI", code, jt, jf, k)


def _install_seccomp() -> bool:
    arch = platform.machine()
    if arch not in _ARCH:
        return False
    idx = 0 if arch == "x86_64" else 1
    deny = sorted({nums[idx] for nums in _DENY.values() if nums[idx] >= 0})
    EPERM = 1
    ALLOW, KILL = 0x7FFF0000, 0x80000000
    ERRNO = lambda e: 0x00050000 | e  # noqa: E731
    LD_W_ABS, JEQ_K, JSET_K, RET_K = 0x20, 0x15, 0x45, 0x06
    prog: list[bytes] = [
        _bpf(LD_W_ABS, 0, 0, 4),  # seccomp_data.arch
        _bpf(JEQ_K, 1, 0, _ARCH[arch]),
        _bpf(RET_K, 0, 0, KILL),
        _bpf(LD_W_ABS, 0, 0, 0),  # seccomp_data.nr
    ]
    # clone(): refuse any namespace flag in args[0]; clone3(): ENOSYS so libc falls back to clone().
    prog += [
        _bpf(JEQ_K, 0, 3, _NR_CLONE[arch]),
        _bpf(LD_W_ABS, 0, 0, 16),  # args[0] (low 32 bits)
        _bpf(JSET_K, 0, 1, _CLONE_NS_FLAGS),
        _bpf(RET_K, 0, 0, ERRNO(EPERM)),
    ]
    prog.append(_bpf(LD_W_ABS, 0, 0, 0))
    prog += [_bpf(JEQ_K, 0, 1, _NR_CLONE3[arch]), _bpf(RET_K, 0, 0, ERRNO(38))]
    prog.append(_bpf(LD_W_ABS, 0, 0, 0))
    for nr in deny:
        prog += [_bpf(JEQ_K, 0, 1, nr), _bpf(RET_K, 0, 0, ERRNO(EPERM))]
    prog.append(_bpf(RET_K, 0, 0, ALLOW))
    blob = b"".join(prog)
    buf = ctypes.create_string_buffer(blob, len(blob))

    class SockFprog(ctypes.Structure):
        _fields_ = [("len", ctypes.c_ushort), ("filter", ctypes.c_void_p)]

    fprog = SockFprog(len(prog), ctypes.cast(buf, ctypes.c_void_p).value)
    rc = _libc.prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, ctypes.byref(fprog), 0, 0)
    _check(rc, "seccomp")
    return True


# --- capabilities -------------------------------------------------------------------------------------------------------------

_SYS_CAPSET = {"x86_64": 126, "aarch64": 91}


def _drop_capabilities() -> None:
    for cap in range(0, 64):
        if _libc.prctl(PR_CAPBSET_DROP, cap, 0, 0, 0) != 0:
            if ctypes.get_errno() == errno.EINVAL:
                break
            raise SetupError(f"capbset_drop {cap}: {os.strerror(ctypes.get_errno())}")
    _libc.prctl(PR_CAP_AMBIENT, PR_CAP_AMBIENT_CLEAR_ALL, 0, 0, 0)
    arch = platform.machine()
    if arch not in _SYS_CAPSET:
        raise SetupError("capset: unsupported architecture")
    header = struct.pack("<Ii", 0x20080522, 0)
    data = struct.pack("<6I", 0, 0, 0, 0, 0, 0)  # effective, permitted, inheritable for two 32-bit words, all zero
    hb, db = ctypes.create_string_buffer(header, len(header)), ctypes.create_string_buffer(data, len(data))
    _check(_libc.syscall(_SYS_CAPSET[arch], hb, db), "capset")


# --- setup ----------------------------------------------------------------------------------------------------------------------


def _write(path: str, text: str) -> None:
    with open(path, "w") as fh:
        fh.write(text)


def _enter_namespaces() -> None:
    uid, gid = os.getuid(), os.getgid()
    try:
        os.unshare(os.CLONE_NEWUSER)
    except OSError as exc:
        raise SetupError(f"user namespace: {os.strerror(exc.errno)}") from exc
    try:
        _write("/proc/self/setgroups", "deny")
        _write("/proc/self/uid_map", f"0 {uid} 1")
        _write("/proc/self/gid_map", f"0 {gid} 1")
    except OSError as exc:
        raise SetupError(f"id mapping: {os.strerror(exc.errno)}") from exc
    try:
        os.unshare(os.CLONE_NEWNS | os.CLONE_NEWPID | os.CLONE_NEWNET | os.CLONE_NEWIPC | os.CLONE_NEWUTS)
    except OSError as exc:
        raise SetupError(f"namespaces: {os.strerror(exc.errno)}") from exc


def _build_root(image: str, files: dict[str, str], limits: dict) -> None:
    _mount(None, "/", None, MS_REC | MS_PRIVATE)
    _mount(image, image, None, MS_BIND | MS_REC)
    _mount(None, image, None, MS_REMOUNT | MS_BIND | MS_RDONLY | MS_NOSUID | MS_NODEV)
    _mount("tmpfs", f"{image}/tmp", "tmpfs", MS_NOSUID | MS_NODEV | MS_NOEXEC, f"size={limits['tmp_bytes']},nr_inodes=128,mode=1777")
    _mount("tmpfs", f"{image}/work", "tmpfs", MS_NOSUID | MS_NODEV | MS_NOEXEC, "size=1048576,nr_inodes=32,mode=0755")
    _mount("tmpfs", f"{image}/dev", "tmpfs", MS_NOSUID | MS_NOEXEC, "size=4096,nr_inodes=8,mode=0755")
    for name in ("null", "urandom", "zero"):
        target = f"{image}/dev/{name}"
        open(target, "w").close()
        _mount(f"/dev/{name}", target, None, MS_BIND)
    for name, text in files.items():
        if "/" in name or name.startswith("."):
            raise SetupError("bad file name")
        _write(f"{image}/work/{name}", text)
    _mount(None, f"{image}/work", None, MS_REMOUNT | MS_BIND | MS_RDONLY | MS_NOSUID | MS_NODEV | MS_NOEXEC)
    os.chroot(image)
    os.chdir("/work")


def _apply_limits(limits: dict) -> None:
    cpu = int(limits["cpu_seconds"])
    resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu + 1))
    resource.setrlimit(resource.RLIMIT_AS, (limits["memory_bytes"], limits["memory_bytes"]))
    resource.setrlimit(resource.RLIMIT_NPROC, (limits["processes"], limits["processes"]))
    resource.setrlimit(resource.RLIMIT_NOFILE, (limits["open_files"], limits["open_files"]))
    resource.setrlimit(resource.RLIMIT_FSIZE, (limits["file_bytes"], limits["file_bytes"]))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def _child(job: dict) -> None:
    """Runs as PID 1 of the new PID namespace. Never returns: it execs the interpreter or exits."""
    try:
        os.setsid()  # its own session/process group: a group-wide kill from inside cannot reach the launcher
        _build_root(job["image"], job["files"], job["limits"])
        _apply_limits(job["limits"])
        if _libc.prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0:
            raise SetupError("no_new_privs failed")
        _libc.prctl(PR_SET_PDEATHSIG, signal.SIGKILL, 0, 0, 0)
        seccomp = _install_seccomp() if job.get("seccomp", True) else False
        if job.get("require_seccomp") and not seccomp:
            raise SetupError("seccomp unavailable on this architecture")
        _drop_capabilities()
        devnull = os.open("/dev/null", os.O_RDONLY)
        os.dup2(devnull, 0)
        os.closerange(3, 1024)
    except SetupError as exc:
        os.write(2, f"SANDBOX_SETUP_FAILED: {exc}\n".encode())
        os._exit(SETUP_FAILED)
    except OSError as exc:
        os.write(2, f"SANDBOX_SETUP_FAILED: {os.strerror(exc.errno or 0)}\n".encode())
        os._exit(SETUP_FAILED)
    env = {"PYTHONHASHSEED": "0", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1", "LANG": "C.UTF-8", "HOME": "/tmp"}
    try:
        os.execve(job["python"], [job["python"], "-S", "-s", "-B", "-u", "/work/harness.py"], env)
    except OSError:
        os.write(2, b"SANDBOX_SETUP_FAILED: exec\n")
        os._exit(SETUP_FAILED)


def main() -> int:
    try:
        raw = sys.stdin.buffer.read(400_000)
        job = json.loads(raw)
    except Exception:  # noqa: BLE001
        sys.stderr.write("SANDBOX_SETUP_FAILED: bad job\n")
        return SETUP_FAILED
    try:
        _enter_namespaces()
    except SetupError as exc:
        sys.stderr.write(f"SANDBOX_SETUP_FAILED: {exc}\n")
        return SETUP_FAILED
    pid = os.fork()
    if pid == 0:
        _child(job)
        os._exit(SETUP_FAILED)  # unreachable
    deadline = time.monotonic() + float(job["limits"]["wall_seconds"])
    def _term(_s, _f):  # supervisor asked us to stop: take the whole PID namespace down with its init
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    signal.signal(signal.SIGTERM, _term)
    while True:
        try:
            done, status = os.waitpid(pid, os.WNOHANG)
        except ChildProcessError:
            return SETUP_FAILED
        if done:
            if os.WIFEXITED(status):
                return os.WEXITSTATUS(status)
            return 128 + os.WTERMSIG(status)
        if time.monotonic() > deadline:
            try:
                os.kill(pid, signal.SIGKILL)  # PID 1 of the namespace: the kernel kills every process in it
            except ProcessLookupError:
                pass
            os.waitpid(pid, 0)
            return TIMEOUT
        time.sleep(0.004)


if __name__ == "__main__":
    sys.exit(main())
