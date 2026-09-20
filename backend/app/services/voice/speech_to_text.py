"""
Speech-to-text service (local faster-whisper).

    audio file --> faster-whisper --> TranscriptionResult

* The Whisper model is **lazy-loaded once** and reused — never per request.
* Model / device / compute type come from the environment
  (`WHISPER_MODEL`, `WHISPER_DEVICE`, `WHISPER_COMPUTE_TYPE`). "auto" uses a
  GPU when one is available and otherwise runs on CPU; nothing here requires
  CUDA.
* `faster_whisper` is imported lazily, so the rest of the app (and text mode)
  starts fine even if it isn't installed or the model can't be loaded.
* Audio bytes and transcripts are never logged.

The service transcribes a file *path* (or file-like object). Validation and
temporary-file handling for uploads live in `voice_service`.
"""

from __future__ import annotations

import importlib.util
import os
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, BinaryIO

from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

AudioInput = str | os.PathLike[str] | BinaryIO


# --- Errors -----------------------------------------------------------------


class SpeechToTextError(Exception):
    """Base class for speech-to-text failures."""


class TranscriptionUnavailableError(SpeechToTextError):
    """faster-whisper isn't installed or the model couldn't be loaded."""


class MalformedAudioError(SpeechToTextError):
    """The audio couldn't be decoded (corrupt or unsupported content)."""


class AudioTooLongError(SpeechToTextError):
    """The recording is longer than the configured maximum."""


class TranscriptionFailedError(SpeechToTextError):
    """Transcription failed for a reason other than bad input."""


# --- Result types -----------------------------------------------------------


@dataclass(frozen=True)
class TranscribedWord:
    start: float
    end: float
    text: str


@dataclass(frozen=True)
class TranscribedSegment:
    start: float
    end: float
    text: str
    words: list[TranscribedWord] = field(default_factory=list)


@dataclass(frozen=True)
class TranscriptionResult:
    """Only what callers need — not Whisper's internal token/probability data."""

    text: str
    language: str | None
    duration_seconds: float
    segments: list[TranscribedSegment] = field(default_factory=list)


# --- Service ----------------------------------------------------------------


def _default_model_factory() -> Any:
    from faster_whisper import WhisperModel  # lazy: heavy import

    return WhisperModel(
        settings.whisper_model,
        device=settings.whisper_device,
        compute_type=settings.whisper_compute_type,
    )


def _is_decode_error(exc: BaseException) -> bool:
    """True if `exc` came from decoding the audio (PyAV), not from the model."""
    module = type(exc).__module__ or ""
    return module == "av" or module.startswith("av.")


class SpeechToTextService:
    """Reusable, lazily-initialised faster-whisper wrapper."""

    def __init__(self, model_factory: Callable[[], Any] | None = None) -> None:
        self._model_factory = model_factory or _default_model_factory
        self._model: Any | None = None
        self._load_lock = threading.Lock()
        # One transcription at a time: a Whisper model is memory/CPU heavy and
        # concurrent decodes on the same model just thrash.
        self._run_lock = threading.Lock()

    def is_available(self) -> bool:
        """Cheap check (no model load): is faster-whisper importable?"""
        if self._model is not None or self._model_factory is not _default_model_factory:
            return True
        return importlib.util.find_spec("faster_whisper") is not None

    def _get_model(self) -> Any:
        if self._model is not None:
            return self._model
        with self._load_lock:
            if self._model is None:
                logger.info(
                    "Loading Whisper model '%s' (device=%s, compute_type=%s)",
                    settings.whisper_model,
                    settings.whisper_device,
                    settings.whisper_compute_type,
                )
                try:
                    self._model = self._model_factory()
                except Exception as exc:  # noqa: BLE001 - surface as one clean error
                    logger.error("Whisper model could not be loaded: %s", type(exc).__name__)
                    raise TranscriptionUnavailableError(
                        "Speech recognition is unavailable right now."
                    ) from exc
        return self._model

    def warm_up(self) -> None:
        """Load the model now (downloads it on first run). Used by the setup script."""
        self._get_model()

    def transcribe_audio(self, audio_file: AudioInput) -> TranscriptionResult:
        """
        Transcribe `audio_file` (a path or binary file object) to text.

        Blocking and CPU-heavy: call from a worker thread in async code.
        Raises a `SpeechToTextError` subclass on failure.
        """
        model = self._get_model()
        source = str(audio_file) if isinstance(audio_file, (str, os.PathLike)) else audio_file
        language = settings.whisper_language.strip() or None

        with self._run_lock:
            try:
                segments_iter, info = model.transcribe(
                    source,
                    language=language,
                    word_timestamps=True,
                    vad_filter=True,
                    condition_on_previous_text=False,
                )
                duration = float(info.duration or 0.0)
                if duration > settings.voice_max_audio_seconds:
                    # Segments are lazy — refusing here skips the expensive part.
                    raise AudioTooLongError(
                        f"Recording is longer than {settings.voice_max_audio_seconds} seconds."
                    )
                raw_segments = list(segments_iter)
            except SpeechToTextError:
                raise
            except Exception as exc:  # noqa: BLE001
                # Only genuine decode failures (PyAV) are the caller's fault. Anything
                # else — including a ValueError from a bad WHISPER_LANGUAGE — is a
                # server-side problem and must not be blamed on the user's audio.
                if _is_decode_error(exc):
                    raise MalformedAudioError("The audio could not be decoded.") from exc
                logger.error("Transcription failed: %s", type(exc).__name__)
                raise TranscriptionFailedError("Transcription failed.") from exc

        segments: list[TranscribedSegment] = []
        for seg in raw_segments:
            words = [
                TranscribedWord(start=float(w.start), end=float(w.end), text=str(w.word))
                for w in (getattr(seg, "words", None) or [])
            ]
            segments.append(
                TranscribedSegment(
                    start=float(seg.start),
                    end=float(seg.end),
                    text=str(seg.text).strip(),
                    words=words,
                )
            )

        text = " ".join(s.text for s in segments if s.text).strip()
        return TranscriptionResult(
            text=text,
            language=getattr(info, "language", None),
            duration_seconds=round(duration, 2),
            segments=segments,
        )


# Module-level singleton, matching the project's existing pattern.
speech_to_text_service = SpeechToTextService()


def transcribe_audio(audio_file: AudioInput) -> TranscriptionResult:
    """Convenience wrapper: `transcribe_audio(audio_file) -> TranscriptionResult`."""
    return speech_to_text_service.transcribe_audio(audio_file)


__all__ = [
    "AudioTooLongError",
    "MalformedAudioError",
    "SpeechToTextError",
    "SpeechToTextService",
    "TranscribedSegment",
    "TranscribedWord",
    "TranscriptionFailedError",
    "TranscriptionResult",
    "TranscriptionUnavailableError",
    "speech_to_text_service",
    "transcribe_audio",
]

