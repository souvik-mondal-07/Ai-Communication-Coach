"""
Small in-process sliding-window rate limiter (Phase 23).

Used for the aptitude endpoints that create or mutate sessions. State lives in this process's
memory, which is honest and sufficient for a single-instance deployment; behind several workers
each keeps its own window (so the effective limit is per worker). Replace `_hits` with a shared
store (e.g. Redis) if you scale out.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException, status

from app.core.dependencies import get_current_user

_lock = threading.Lock()
_hits: dict[str, deque[float]] = defaultdict(deque)
_MAX_KEYS = 20_000


def reset_rate_limits() -> None:
    with _lock:
        _hits.clear()


def check_rate_limit(key: str, limit: int, window_seconds: int) -> None:
    now = time.monotonic()
    with _lock:
        if len(_hits) > _MAX_KEYS:  # bound memory: drop idle keys
            for k in [k for k, q in _hits.items() if not q or now - q[-1] > window_seconds]:
                _hits.pop(k, None)
        q = _hits[key]
        while q and now - q[0] > window_seconds:
            q.popleft()
        if len(q) >= limit:
            retry = max(1, int(window_seconds - (now - q[0])))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={"message": f"Too many requests. Try again in {retry} seconds.", "error_code": "RATE_LIMITED"},
                headers={"Retry-After": str(retry)},
            )
        q.append(now)


def rate_limited(name: str, limit: int, window_seconds: int):
    """Dependency factory: limit per authenticated user (never per client-supplied id)."""

    def dependency(current_user=Depends(get_current_user)) -> None:
        check_rate_limit(f"{name}:{current_user['_id']}", limit, window_seconds)

    return dependency
