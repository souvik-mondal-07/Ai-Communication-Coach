"""
Voice service.

Coordinates the voice pipeline for the communication coach:

    audio bytes -> validation -> temp file -> STT -> transcript (+ metrics)

and text -> TTS. The routes stay thin; the transcript is *returned to the
user* rather than auto-sent, so they can edit/discard it before it becomes a
communication message (sent through the existing Step 7 message endpoint).

Privacy: audio is written to a temporary file only for the duration of the
transcription and deleted immediately afterwards. Audio and transcripts are
never logged.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Protocol

from app.core.config import settings
from app.services.communication.analysis_service import calculate_pause_metrics
from app.services.voice.speech_to_text import (
    SpeechToTextService,
    TranscriptionResult,
    speech_to_text_service,
)
from app.services.voice.text_to_speech import (
    SynthesizedAudio,
    TextToSpeechService,
    text_to_speech_service,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

# --- Errors -----------------------------------------------------------------


class AudioValidationError(Exception):
    """Base class for rejected uploads (all are the caller's fault)."""


class EmptyAudioError(AudioValidationError):
    pass


class AudioTooLargeError(AudioValidationError):
    pass


class UnsupportedAudioError(AudioValidationError):
    pass


class NoSpeechDetectedError(Exception):
    """Audio decoded fine but contained no recognisable speech."""


# --- Validation -------------------------------------------------------------

# Declared types we accept. `application/octet-stream` is allowed because a
# Blob without a type uploads that way — but the *content* must still sniff as
# audio, so the header is never what we rely on.
ALLOWED_CONTENT_TYPES = frozenset(
    {
        "audio/webm", "video/webm", "audio/ogg", "application/ogg",
        "audio/wav", "audio/x-wav", "audio/wave", "audio/vnd.wave",
        "audio/mpeg", "audio/mp3", "audio/mp4", "audio/x-m4a", "audio/m4a",
        "audio/aac", "audio/flac", "audio/x-flac", "application/octet-stream",
    }
)


def sniff_audio_format(head: bytes) -> str | None:
    """
    Identify an audio container from its leading bytes and return a safe file
    suffix, or None if it doesn't look like supported audio. We never trust
    the client's filename or Content-Type for this.
    """
    if head[:4] == b"\x1a\x45\xdf\xa3":
        return ".webm"  # WebM / Matroska (Chrome, Firefox MediaRecorder)
    if head[:4] == b"OggS":
        return ".ogg"
    if head[:4] == b"RIFF" and head[8:12] == b"WAVE":
        return ".wav"
    if head[:4] == b"fLaC":
        return ".flac"
    if head[4:8] == b"ftyp":
        return ".m4a"  # MP4 / M4A (Safari MediaRecorder)
    if head[:3] == b"ID3":
        return ".mp3"
    if len(head) >= 2 and head[0] == 0xFF and (head[1] & 0xE0) == 0xE0:
        return ".aac" if (head[1] & 0x06) == 0 else ".mp3"  # ADTS AAC vs MP3 frame sync
    return None


class _Readable(Protocol):
    async def read(self, size: int = -1) -> bytes: ...


async def read_upload_limited(upload: _Readable, max_bytes: int | None = None) -> bytes:
    """Read an upload in chunks, refusing to buffer more than the size limit."""
    limit = max_bytes if max_bytes is not None else settings.voice_max_audio_bytes
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await upload.read(64 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise AudioTooLargeError("Audio file is too large.")
        chunks.append(chunk)
    return b"".join(chunks)


def validate_audio(data: bytes, content_type: str | None) -> str:
    """Validate an in-memory upload. Returns the safe temp-file suffix."""
    if not data:
        raise EmptyAudioError("The audio file is empty.")
    if len(data) > settings.voice_max_audio_bytes:
        raise AudioTooLargeError("Audio file is too large.")

    declared = (content_type or "").split(";")[0].strip().lower()
    if declared and declared not in ALLOWED_CONTENT_TYPES:
        raise UnsupportedAudioError("Unsupported audio type.")

    suffix = sniff_audio_format(data[:16])
    if suffix is None:
        raise UnsupportedAudioError("The file is not recognised audio.")
    return suffix


@contextmanager
def _temporary_audio_file(data: bytes, suffix: str) -> Iterator[str]:
    """Write `data` to a private temp file and *always* delete it afterwards."""
    directory = settings.voice_temp_dir or None
    if directory:
        os.makedirs(directory, mode=0o700, exist_ok=True)
    fd, path = tempfile.mkstemp(prefix="voice-", suffix=suffix, dir=directory)  # mode 0600
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        yield path
    finally:
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass
        except OSError:
            logger.warning("Could not delete a temporary audio file")


# --- Service ----------------------------------------------------------------


@dataclass(frozen=True)
class TranscriptionOutcome:
    text: str
    language: str | None
    duration_seconds: float
    pause_metrics: dict | None


def _pause_metrics_for(result: TranscriptionResult) -> dict | None:
    """Prefer word-level timing; fall back to (coarser) segment timing."""
    words = [(w.start, w.end) for seg in result.segments for w in seg.words]
    if len(words) >= 2:
        return calculate_pause_metrics(words, granularity="word")
    segments = [(seg.start, seg.end) for seg in result.segments]
    return calculate_pause_metrics(segments, granularity="segment")


class VoiceService:
    """Facade over speech-to-text and text-to-speech."""

    def __init__(
        self,
        stt: SpeechToTextService = speech_to_text_service,
        tts: TextToSpeechService = text_to_speech_service,
    ) -> None:
        self._stt = stt
        self._tts = tts

    def capabilities(self) -> dict:
        return {
            "stt_available": self._stt.is_available(),
            "tts_available": self._tts.is_configured(),
            "max_audio_seconds": settings.voice_max_audio_seconds,
            "max_audio_bytes": settings.voice_max_audio_bytes,
        }

    def _transcribe_sync(self, data: bytes, suffix: str) -> TranscriptionResult:
        with _temporary_audio_file(data, suffix) as path:
            return self._stt.transcribe_audio(path)

    async def transcribe(self, data: bytes, content_type: str | None) -> TranscriptionOutcome:
        """
        Validate and transcribe an uploaded recording.

        Raises `AudioValidationError` subclasses for bad uploads,
        `NoSpeechDetectedError` for silence, and `SpeechToTextError`
        subclasses for recognition failures.
        """
        suffix = validate_audio(data, content_type)
        # Whisper is blocking and CPU-heavy: keep it off the event loop.
        result = await asyncio.to_thread(self._transcribe_sync, data, suffix)

        text = result.text.strip()
        if not text:
            raise NoSpeechDetectedError("No speech was detected in the recording.")

        return TranscriptionOutcome(
            text=text,
            language=result.language,
            duration_seconds=result.duration_seconds,
            pause_metrics=_pause_metrics_for(result),
        )

    async def synthesize(self, text: str) -> SynthesizedAudio:
        return await self._tts.synthesize_speech(text)


# Module-level singleton, matching the project's existing pattern.
voice_service = VoiceService()
