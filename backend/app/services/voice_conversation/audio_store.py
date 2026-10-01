"""
Short-lived, in-memory store for generated AI speech.

The frontend cannot put an `Authorization` header on a bare `<audio src>`, so
the reply carries an opaque, unguessable token instead of raw bytes in the
JSON. The browser fetches the clip once through the authenticated API client.

* Audio never touches the filesystem or MongoDB.
* A token is bound to the user it was issued to; another user's token (or a
  guessed one) simply looks like "not found".
* Clips expire after `VOICE_AUDIO_URL_TTL_SECONDS` and the store is bounded
  in both entry count and total bytes (oldest clips are evicted first).

Known limitation: the store lives in one process's memory. With several
uvicorn workers, a clip must be fetched from the worker that made it — run a
single worker, use sticky routing, or swap this class for a shared cache.
"""

from __future__ import annotations

import secrets
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass

from app.core.config import settings

_MAX_ENTRIES = 64
_MAX_TOTAL_BYTES = 64 * 1024 * 1024


@dataclass(frozen=True)
class StoredAudio:
    data: bytes
    media_type: str


@dataclass
class _Entry:
    user_id: str
    audio: StoredAudio
    expires_at: float


class AudioStore:
    def __init__(
        self,
        *,
        ttl_seconds: float | None = None,
        max_entries: int = _MAX_ENTRIES,
        max_total_bytes: int = _MAX_TOTAL_BYTES,
        clock=time.monotonic,
    ) -> None:
        self._ttl_override = ttl_seconds
        self._max_entries = max_entries
        self._max_total_bytes = max_total_bytes
        self._clock = clock
        self._entries: OrderedDict[str, _Entry] = OrderedDict()
        self._total_bytes = 0
        self._lock = threading.Lock()

    @property
    def _ttl(self) -> float:
        # Read at call time so a changed setting takes effect without a restart.
        if self._ttl_override is not None:
            return self._ttl_override
        return float(settings.voice_audio_url_ttl_seconds)

    def _drop(self, token: str) -> None:
        entry = self._entries.pop(token, None)
        if entry is not None:
            self._total_bytes -= len(entry.audio.data)

    def _purge_expired(self) -> None:
        now = self._clock()
        for token in [t for t, e in self._entries.items() if e.expires_at <= now]:
            self._drop(token)

    def put(self, user_id: str, data: bytes, media_type: str) -> str:
        """Store a clip for `user_id` and return its opaque token."""
        token = secrets.token_urlsafe(24)
        with self._lock:
            self._purge_expired()
            self._entries[token] = _Entry(
                user_id=user_id,
                audio=StoredAudio(data=data, media_type=media_type),
                expires_at=self._clock() + self._ttl,
            )
            self._total_bytes += len(data)
            while self._entries and (
                len(self._entries) > self._max_entries or self._total_bytes > self._max_total_bytes
            ):
                self._drop(next(iter(self._entries)))  # oldest first
        return token

    def get(self, user_id: str, token: str) -> StoredAudio | None:
        """The clip for `token` if it exists, is unexpired, and belongs to `user_id`."""
        with self._lock:
            self._purge_expired()
            entry = self._entries.get(token)
            if entry is None or not secrets.compare_digest(entry.user_id, user_id):
                return None
            return entry.audio

    def __len__(self) -> int:
        with self._lock:
            self._purge_expired()
            return len(self._entries)


audio_store = AudioStore()
