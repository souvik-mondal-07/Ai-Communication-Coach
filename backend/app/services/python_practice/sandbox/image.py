"""
Minimal read-only runtime image for the code runner (Phase 26).

The runner chroots into a directory that contains ONLY what a bare CPython needs: the interpreter, the ELF loader chain, the
shared libraries it maps, and a copy of the standard library. There is no /etc, /home, /proc, /sys, no site-packages and none
of the application's files, so a submitted program has nothing of the host to read even before the other layers apply.

Built once per process into a private temporary directory (copies, not bind mounts of host directories) and removed at exit.
Everything copied is public interpreter/library files -- never application code, configuration or environment.
"""

from __future__ import annotations

import atexit
import os
import shutil
import struct
import subprocess
import sys
import sysconfig
import tempfile
import threading
from dataclasses import dataclass

# Standard-library modules the probe imports, so the shared libraries their extension modules need are copied too.
_PROBE_IMPORTS = (
    "json", "re", "math", "collections", "itertools", "functools", "heapq", "bisect", "string", "datetime", "decimal", "fractions",
    "statistics", "hashlib", "hmac", "secrets", "base64", "binascii", "csv", "io", "ipaddress", "urllib.parse", "pathlib", "logging",
    "dataclasses", "abc", "enum", "typing", "contextlib", "copy", "operator", "textwrap", "struct", "time", "random", "zlib", "uuid",
    "asyncio", "threading", "queue", "shlex", "traceback", "types", "weakref", "gc", "sys", "os", "signal", "array", "unicodedata", "select", "socket", "ctypes",
)
_SKIP_DIRS = {"test", "tests", "idlelib", "tkinter", "turtledemo", "ensurepip", "lib2to3", "distutils", "venv", "pydoc_data", "site-packages", "dist-packages", "idle_test"}
_SKIP_TOP = {"turtle.py", "pydoc.py", "this.py", "antigravity.py"}


class ImageError(RuntimeError):
    pass


@dataclass(frozen=True)
class RuntimeImage:
    root: str
    python: str  # absolute path of the interpreter INSIDE the image
    version: str


_lock = threading.Lock()
_image: RuntimeImage | None = None
_error: str | None = None


def _real_interpreter() -> str:
    exe = getattr(sys, "_base_executable", None) or sys.executable
    return os.path.realpath(exe)


def _elf_interpreter(path: str) -> str | None:
    """PT_INTERP of a 64-bit little-endian ELF (the dynamic loader path), or None for a static binary."""
    with open(path, "rb") as fh:
        head = fh.read(64)
        if head[:4] != b"\x7fELF" or head[4] != 2 or head[5] != 1:
            raise ImageError("only 64-bit little-endian ELF interpreters are supported")
        phoff, = struct.unpack_from("<Q", head, 32)
        phentsize, phnum = struct.unpack_from("<HH", head, 54)
        for i in range(phnum):
            fh.seek(phoff + i * phentsize)
            ph = fh.read(phentsize)
            p_type, _flags, p_offset, _va, _pa, p_filesz = struct.unpack_from("<IIQQQQ", ph, 0)
            if p_type == 3:
                fh.seek(p_offset)
                return fh.read(p_filesz).split(b"\0", 1)[0].decode()
    return None


def _materialise(root: str, path: str, _depth: int = 0) -> None:
    """Make `path` exist inside `root`: replicate each symlink component as a symlink and copy the final regular file."""
    if _depth > 12:
        raise ImageError("symlink chain too deep")
    parts = [p for p in path.split("/") if p]
    cur_host = "/"
    cur_img = root
    for i, part in enumerate(parts):
        cur_host = os.path.join(cur_host, part)
        cur_img = os.path.join(cur_img, part)
        last = i == len(parts) - 1
        if os.path.islink(cur_host):
            target = os.readlink(cur_host)
            if not os.path.lexists(cur_img):
                os.makedirs(os.path.dirname(cur_img), exist_ok=True)
                os.symlink(target, cur_img)
            resolved = target if target.startswith("/") else os.path.normpath(os.path.join(os.path.dirname(cur_host), target))
            rest = "/".join(parts[i + 1:])
            _materialise(root, resolved, _depth + 1)
            if rest:
                _materialise(root, os.path.join(resolved, rest), _depth + 1)
            return
        if last:
            if os.path.isdir(cur_host):
                os.makedirs(cur_img, exist_ok=True)
            elif not os.path.exists(cur_img):
                os.makedirs(os.path.dirname(cur_img), exist_ok=True)
                shutil.copy2(cur_host, cur_img)
        else:
            os.makedirs(cur_img, exist_ok=True)


def _materialise_soname_links(root: str, lib: str) -> None:
    """The loader asks for `libz.so.1`, but the maps list the real file `libz.so.1.3`: copy the symlinks that point at it."""
    real = os.path.realpath(lib)
    directory = os.path.dirname(lib)
    try:
        names = os.listdir(directory)
    except OSError:
        return
    for name in names:
        candidate = os.path.join(directory, name)
        if os.path.islink(candidate) and os.path.realpath(candidate) == real:
            _materialise(root, candidate)


def _ignore(directory: str, names: list[str]) -> list[str]:
    skip = [n for n in names if n in _SKIP_DIRS or (directory.rstrip("/") == _STDLIB and n in _SKIP_TOP)]
    return skip


_STDLIB = ""


def _copy_tree(root: str, host_dir: str) -> None:
    dest = os.path.join(root, host_dir.lstrip("/"))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.copytree(host_dir, dest, symlinks=True, ignore=_ignore, dirs_exist_ok=True)


def _probe_libraries(exe: str) -> list[str]:
    """Ask a bare interpreter which shared objects it maps after importing the usual stdlib modules (no ldd needed)."""
    code = (
        "import importlib\n"
        f"for m in {list(_PROBE_IMPORTS)!r}:\n"
        "    try: importlib.import_module(m)\n"
        "    except Exception: pass\n"
        "seen=set()\n"
        "for line in open('/proc/self/maps'):\n"
        "    p=line.split(None,5)\n"
        "    if len(p)==6 and p[5].startswith('/') and '.so' in p[5]: seen.add(p[5].strip())\n"
        "print('\\n'.join(sorted(seen)))\n"
    )
    out = subprocess.run([exe, "-S", "-s", "-c", code], capture_output=True, text=True, timeout=20, env={"PYTHONHASHSEED": "0"}, check=True)
    return [line for line in out.stdout.splitlines() if line.startswith("/")]


def _build() -> RuntimeImage:
    global _STDLIB
    if not sys.platform.startswith("linux"):
        raise ImageError("the code runner needs Linux")
    exe = _real_interpreter()
    stdlib = os.path.realpath(sysconfig.get_path("stdlib"))
    plat = os.path.realpath(sysconfig.get_path("platstdlib"))
    _STDLIB = stdlib
    root = tempfile.mkdtemp(prefix="pyprac-rt-")
    atexit.register(shutil.rmtree, root, True)
    os.chmod(root, 0o755)  # the unprivileged runner identity must be able to traverse it; it holds public interpreter files only
    try:
        _materialise(root, exe)
        loader = _elf_interpreter(exe)
        if loader:
            _materialise(root, loader)
        for lib in _probe_libraries(exe):
            _materialise(root, lib)
            _materialise_soname_links(root, lib)
        for d in {stdlib, plat}:
            _copy_tree(root, d)
        for top in ("lib", "lib64", "bin", "sbin"):  # merged-/usr systems: these are symlinks into /usr
            if os.path.islink("/" + top) and not os.path.lexists(os.path.join(root, top)):
                os.symlink(os.readlink("/" + top), os.path.join(root, top))
        for d in ("tmp", "work", "dev"):
            os.makedirs(os.path.join(root, d), exist_ok=True)
        if not os.path.isfile(os.path.join(root, exe.lstrip("/"))):
            raise ImageError("interpreter was not copied")
    except Exception:
        shutil.rmtree(root, ignore_errors=True)
        raise
    return RuntimeImage(root=root, python=exe, version=".".join(map(str, sys.version_info[:3])))


def get_image() -> RuntimeImage:
    """The process-wide runtime image (built on first use). Raises ImageError when it cannot be built."""
    global _image, _error
    with _lock:
        if _image is not None and os.path.isdir(_image.root):
            return _image
        if _error is not None:
            raise ImageError(_error)
        try:
            _image = _build()
        except ImageError as exc:
            _error = str(exc)
            raise
        except Exception as exc:  # noqa: BLE001
            _error = f"could not build the runtime image ({type(exc).__name__})"
            raise ImageError(_error) from exc
        return _image
