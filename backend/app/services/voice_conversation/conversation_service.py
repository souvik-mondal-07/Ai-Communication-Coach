"""
Voice conversation service (Step 13).

One spoken turn is two separate, individually retryable operations, reusing
the existing services for every heavy step:

    1. transcribe_audio(...)
         audio ──► VoiceService (Step 8: validate, temp file, Whisper, cleanup)
               ──► transcript (+ measured duration / pause metrics)

    2. process_transcript(...)
         transcript ──► ConversationEngine ──► Gemini / Step 9 / 10 / 7 (by mode)
                    ──► VoiceService (Step 8: TTS)
                    ──► short-lived audio token + structured JSON reply

Speech-to-text therefore runs exactly once per recording. If the AI step
fails, the client keeps the transcript it already has and calls
`process_transcript` again with the same text -- no audio is re-sent and
Whisper does not run again.

This is still turn-based (record → transcribe → generate → synthesize → play),
not full-duplex streaming. The engine is text-in/text-out, so a streaming
layer could later replace either step without touching the modes.

Failure behaviour: a turn is saved only after every step that matters
succeeded, in one guarded write. `transcribe_audio` never writes to the
session. If the AI or a linked Step 9/10/7 service fails inside
`process_transcript`, the session is unchanged and the same transcript can be
submitted again. An empty/whitespace transcript is rejected before the AI,
TTS or the session lock are touched. TTS is best-effort: if speech can't be
produced the turn still succeeds and the reply is returned as text (with an
`audio_error` code).

Duplicate protection: both operations take the per-session lock and check
`expected_turn`, so a second submission for the same turn is refused (409)
instead of creating a second AI turn.

Privacy: uploaded audio lives in a private temp file only while it is
transcribed (Step 8) and is deleted immediately. Generated speech is held in
memory for a short time. Neither audio nor transcripts are ever logged.
"""

from __future__ import annotations

import math
from statistics import mean

from pymongo.database import Database

from app.core.config import settings
from app.schemas.voice_conversation import CreateVoiceSessionRequest, ProcessTranscriptRequest
from app.services.communication.analysis_service import aggregate_voice_analyses, analyze_transcript
from app.services.progress.progress_service import ProgressService, progress_service
from app.services.voice.text_to_speech import TTSNotConfiguredError
from app.services.voice.voice_service import NoSpeechDetectedError, VoiceService, voice_service
from app.services.voice_conversation.audio_store import AudioStore, StoredAudio, audio_store
from app.services.voice_conversation.conversation_engine import (
    ConversationAIError,
    ConversationConfigError,
    ConversationEngine,
    ConversationStateError,
)
from app.services.voice_conversation.prompts import FREEFORM_MODES
from app.services.voice_conversation.session_manager import (
    MODE_LABELS,
    SessionBusyError,
    SessionForbiddenError,
    SessionNotActiveError,
    SessionNotFoundError,
    TurnMismatchError,
    VoiceConversationError,
    VoiceSessionManager,
    as_utc,
    public_session,
    summary_row,
    utcnow,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

__all__ = [
    "ConversationAIError",
    "ConversationConfigError",
    "ConversationStateError",
    "EMPTY_TRANSCRIPT_MESSAGE",
    "EmptyTranscriptError",
    "RecordingTooLongError",
    "SessionBusyError",
    "SessionForbiddenError",
    "SessionNotActiveError",
    "SessionNotFoundError",
    "TurnMismatchError",
    "VoiceConversationError",
    "VoiceConversationService",
    "build_summary",
    "compact_evaluation",
    "voice_conversation_service",
]

_MAX_RESPONSE_SECONDS = 3_600.0

_EVAL_SCORES = (
    "overall_score", "technical_score", "communication_score", "pressure_handling_score",
    "response_control_score", "clarity_score", "grammar_score", "vocabulary_score",
    "professionalism_score", "confidence_score", "relevance_score", "conversation_flow_score",
)
_EVAL_LISTS = ("strengths", "weaknesses", "areas_to_improve", "improvements", "recommendations")


# Shown to the learner whenever speech-to-text produced nothing usable.
EMPTY_TRANSCRIPT_MESSAGE = "I couldn't hear a clear response. Please try again."


class RecordingTooLongError(VoiceConversationError):
    """The spoken answer is longer than VOICE_MAX_RECORDING_SECONDS."""


class EmptyTranscriptError(VoiceConversationError):
    """The transcript is missing or only whitespace; it must never reach the AI."""


def is_blank_transcript(value: object) -> bool:
    """True for None, non-strings, the empty string and whitespace-only text (spaces, newlines, tabs)."""
    return not isinstance(value, str) or not value.strip()


# --- Summary -------------------------------------------------------------------------


def compact_evaluation(evaluation: dict | None) -> dict | None:
    """
    The headline parts of a Step 9/10/7 evaluation (scores, strengths, gaps,
    summary) — only what the evaluation actually contains. The full evaluation
    stays with the linked session; nothing is recomputed or duplicated.
    """
    if not evaluation:
        return None
    compact: dict = {}
    for key in _EVAL_SCORES:
        if isinstance(evaluation.get(key), (int, float)) and not isinstance(evaluation.get(key), bool):
            compact[key] = evaluation[key]
    for key in _EVAL_LISTS:
        value = evaluation.get(key)
        if isinstance(value, list) and value:
            compact[key] = [item for item in value if isinstance(item, str)][:8]
    if isinstance(evaluation.get("summary"), str) and evaluation["summary"].strip():
        compact["summary"] = evaluation["summary"].strip()
    return compact or None


def build_summary(session: dict, *, evaluation: dict | None, evaluation_error: bool = False) -> dict:
    """Final session summary. Every figure is measured or taken from an existing evaluation."""
    user_messages = [m for m in session.get("messages", []) if m["role"] == "user"]
    analyses = [m["voice_analysis"] for m in user_messages if m.get("voice_analysis")]
    durations = [m["duration_seconds"] for m in user_messages if m.get("duration_seconds")]
    word_counts = [a["word_count"] for a in analyses if a.get("word_count") is not None]

    started = as_utc(session.get("activated_at") or session["started_at"])
    duration = max(0, int((utcnow() - started).total_seconds()))

    compact = compact_evaluation(evaluation)
    strengths = compact.get("strengths", []) if compact else []
    improve: list[str] = []
    if compact:
        improve = (
            compact.get("areas_to_improve") or compact.get("weaknesses") or compact.get("improvements") or []
        )

    return {
        "mode": session["mode"],
        "mode_label": MODE_LABELS.get(session["mode"], session["mode"]),
        "difficulty": session["difficulty"],
        "topic": session.get("topic"),
        "turns": session.get("user_turn_count", 0),
        "assistant_turns": session.get("assistant_turn_count", 0),
        # Wall-clock length of the session (includes thinking time and AI speech).
        "duration_seconds": duration,
        "average_response_duration_seconds": round(mean(durations), 1) if durations else None,
        "average_response_words": round(mean(word_counts), 1) if word_counts else None,
        # Only present when at least one spoken answer was analysed.
        "speaking_metrics": aggregate_voice_analyses(analyses),
        "evaluation": compact,
        "evaluation_available": compact is not None,
        "evaluation_error": evaluation_error,
        "strengths": strengths,
        "areas_to_improve": improve,
    }


def _clean_response_seconds(value: float | None) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if not math.isfinite(value) or value < 0 or value > _MAX_RESPONSE_SECONDS:
        return None
    return float(value)


# --- Service -----------------------------------------------------------------------------


class VoiceConversationService:
    def __init__(
        self,
        *,
        voice: VoiceService | None = None,
        engine: ConversationEngine | None = None,
        sessions: VoiceSessionManager | None = None,
        audio: AudioStore | None = None,
        progress: ProgressService | None = None,
    ) -> None:
        # Everything defaults to the app's existing singletons — no second STT/TTS/Gemini client.
        self._voice = voice or voice_service
        self._engine = engine or ConversationEngine()
        self._sessions = sessions or VoiceSessionManager()
        self._audio = audio or audio_store
        self._progress = progress or progress_service

    def ensure_indexes(self, db: Database) -> None:
        self._sessions.ensure_indexes(db)

    # --- Config ---------------------------------------------------------------------------

    def get_config(self) -> dict:
        """Public, non-secret limits and capabilities for the client."""
        capabilities = self._voice.capabilities()
        return {
            "stt_available": capabilities["stt_available"],
            "tts_available": capabilities["tts_available"],
            "max_recording_seconds": settings.voice_max_recording_seconds,
            "max_audio_bytes": settings.voice_max_audio_bytes,
            "max_session_turns": settings.voice_conversation_max_session_turns,
            "auto_play": settings.voice_auto_play,
            "modes": list(MODE_LABELS.keys()),
        }

    # --- Sessions ---------------------------------------------------------------------------

    def create_session(self, db: Database, *, user_id: str, request: CreateVoiceSessionRequest) -> dict:
        config = self._engine.build_config(
            request.mode,
            interview_type=request.interview_type,
            question_count=request.question_count,
            pressure_level=request.pressure_level,
            scenario_slug=request.scenario_slug,
        )
        self._engine.validate_config(db, request.mode, config)
        document = self._sessions.create(
            db,
            user_id=user_id,
            mode=request.mode,
            difficulty=request.difficulty,
            topic=request.topic,
            config=config,
        )
        logger.info("Voice conversation created user_id=%s session_id=%s mode=%s", user_id, document["_id"], request.mode)
        return public_session(document)

    def get_session(self, db: Database, *, user_id: str, session_id: str) -> dict:
        return public_session(self._sessions.get_owned(db, session_id=session_id, user_id=user_id))

    def list_sessions(self, db: Database, *, user_id: str, page: int, limit: int) -> dict:
        rows, total = self._sessions.list_sessions(db, user_id=user_id, page=page, limit=limit)
        return {"sessions": [summary_row(r) for r in rows], "page": page, "limit": limit, "total": total}

    # --- Speech ---------------------------------------------------------------------------------

    async def _speak(self, user_id: str, text: str) -> tuple[str | None, str | None]:
        """Best-effort TTS. Returns (audio_url, error_code); never raises."""
        try:
            audio = await self._voice.synthesize(text)
        except TTSNotConfiguredError:
            return None, "TTS_NOT_CONFIGURED"
        except Exception as exc:  # noqa: BLE001 - a failed voice must never fail the turn
            logger.warning("Voice conversation TTS failed user_id=%s: %s", user_id, type(exc).__name__)
            return None, "TTS_FAILED"
        token = self._audio.put(user_id, audio.data, audio.media_type)
        return f"{settings.api_v1_prefix}/voice-conversation/audio/{token}", None

    def get_audio(self, *, user_id: str, token: str) -> StoredAudio | None:
        return self._audio.get(user_id, token)

    # --- Start -------------------------------------------------------------------------------------

    async def start_session(self, db: Database, *, user_id: str, session_id: str) -> dict:
        """
        Begin the conversation: the AI produces and speaks its opening prompt.
        Calling this on an already-active session resumes it (returns the
        current AI prompt) instead of starting over or creating a new session.
        """
        session = self._sessions.get_owned(db, session_id=session_id, user_id=user_id)
        if session["status"] not in ("created", "active"):
            raise SessionNotActiveError(session_id)

        token = self._sessions.acquire_lock(db, session, allowed_statuses=("created", "active"))
        try:
            session = self._sessions.get_owned(db, session_id=session_id, user_id=user_id)
            if session["status"] not in ("created", "active"):
                raise SessionNotActiveError(session_id)

            info: dict = {}
            resumed = session["status"] == "active" and bool(session.get("messages"))
            if resumed:
                prompt = next(m for m in reversed(session["messages"]) if m["role"] == "assistant")
                text = prompt["text"]
            else:
                profile_context = None
                if self._engine.uses_profile_context(session["mode"]):
                    # Compact Step 11 context (never the full profile); None when there is nothing to use.
                    profile_context = self._progress.get_mentor_context(db, user_id=user_id)
                driver = self._engine.driver_for(session["mode"])
                started = await driver.start(db, session=session, user_id=user_id, profile_context=profile_context)
                text, info = started.text, started.info

            audio_url, audio_error = await self._speak(user_id, text)

            if not resumed:
                self._sessions.activate(
                    db,
                    session["_id"],
                    token,
                    opening_message={
                        "role": "assistant",
                        "text": text,
                        "timestamp": utcnow(),
                        "audio_available": audio_url is not None,
                    },
                    linked=started.linked,
                    profile_context=profile_context,
                )
            logger.info(
                "Voice conversation %s user_id=%s session_id=%s mode=%s",
                "resumed" if resumed else "started", user_id, session_id, session["mode"],
            )
        finally:
            self._sessions.release_lock(db, session["_id"], token)

        fresh = self._sessions.get_owned(db, session_id=session_id, user_id=user_id)
        return {
            "session": public_session(fresh),
            "ai_response": text,
            "audio_url": audio_url,
            "audio_error": audio_error,
            "turn_number": fresh.get("user_turn_count", 0),
            "conversation_complete": False,
            "resumed": resumed,
            "mode_info": info,
        }

    # --- Transcribe (audio -> transcript; no AI, no TTS, nothing saved) ----------------------------------

    async def transcribe_audio(
        self,
        db: Database,
        *,
        user_id: str,
        session_id: str,
        audio: bytes,
        content_type: str | None,
        expected_turn: int | None = None,
    ) -> dict:
        """
        Turn one recording into text. Runs Step 8 speech-to-text exactly once.

        Never calls the AI or TTS and never modifies the session. A recording
        with no recognisable speech is *not* an error: it returns
        `transcript == ""` and `is_empty == True`, and the client asks the
        learner to try again. Bad audio and STT failures raise the Step 8
        exceptions; session problems raise the session errors.
        """
        session = self._sessions.get_owned(db, session_id=session_id, user_id=user_id)
        if session["status"] != "active":
            raise SessionNotActiveError(session_id)
        if expected_turn is not None and expected_turn != session.get("user_turn_count", 0):
            raise TurnMismatchError(session_id)

        # The lock makes a duplicated upload of the same recording fail fast (SESSION_BUSY)
        # *before* a second Whisper run starts. It is released as soon as STT is done.
        token = self._sessions.acquire_lock(db, session, allowed_statuses=("active",))
        try:
            session = self._sessions.get_owned(db, session_id=session_id, user_id=user_id)
            if session["status"] != "active":
                raise SessionNotActiveError(session_id)
            if expected_turn is not None and expected_turn != session.get("user_turn_count", 0):
                raise TurnMismatchError(session_id)

            # Step 8: validate, temp-file, Whisper, cleanup (try/finally inside VoiceService).
            try:
                outcome = await self._voice.transcribe(audio, content_type)
            except NoSpeechDetectedError:
                return self._empty_transcription()
            if outcome.duration_seconds > settings.voice_max_recording_seconds:
                raise RecordingTooLongError(session_id)
        finally:
            self._sessions.release_lock(db, session["_id"], token)

        if is_blank_transcript(outcome.text):
            return self._empty_transcription()

        logger.info("Voice answer transcribed user_id=%s session_id=%s", user_id, session_id)
        return {
            "transcript": outcome.text.strip(),
            "is_empty": False,
            "duration_seconds": outcome.duration_seconds or None,
            "language": outcome.language,
            "pause_metrics": outcome.pause_metrics,
        }

    @staticmethod
    def _empty_transcription() -> dict:
        return {"transcript": "", "is_empty": True, "duration_seconds": None, "language": None, "pause_metrics": None}

    # --- Process transcript (transcript -> AI -> TTS; saves the turn) ----------------------------------

    async def process_transcript(
        self,
        db: Database,
        *,
        user_id: str,
        session_id: str,
        request: ProcessTranscriptRequest,
    ) -> dict:
        """
        Run one answer through the conversation engine and speak the reply.

        Takes text, never audio, so it is also the retry path: calling it
        again with the same transcript after an AI failure repeats only the
        AI/TTS work. Raises `EmptyTranscriptError` for blank text (before the
        session lock, the AI and TTS), `ConversationAIError` for AI failures,
        and the session errors from `session_manager`. On any failure
        nothing is saved.
        """
        transcript = request.transcript
        expected_turn = request.expected_turn

        # Ownership first, so a blank body can't be used to probe other users' session ids.
        session = self._sessions.get_owned(db, session_id=session_id, user_id=user_id)
        if is_blank_transcript(transcript):
            raise EmptyTranscriptError(session_id)  # nothing below (lock, AI, TTS) runs
        if session["status"] != "active":
            raise SessionNotActiveError(session_id)
        if expected_turn != session.get("user_turn_count", 0):
            raise TurnMismatchError(session_id)

        token = self._sessions.acquire_lock(db, session, allowed_statuses=("active",))
        try:
            # State may have moved between the first read and taking the lock.
            session = self._sessions.get_owned(db, session_id=session_id, user_id=user_id)
            if session["status"] != "active":
                raise SessionNotActiveError(session_id)
            if expected_turn != session.get("user_turn_count", 0):
                raise TurnMismatchError(session_id)

            duration = request.duration_seconds if request.duration_seconds and request.duration_seconds > 0 else None
            if duration is not None and duration > settings.voice_max_recording_seconds:
                raise RecordingTooLongError(session_id)
            pause_metrics = request.pause_metrics.model_dump() if request.pause_metrics else None
            audio_meta = None
            if duration is not None:
                audio_meta = {"duration_seconds": duration, "language": request.language, "pause_metrics": pause_metrics}

            driver = self._engine.driver_for(session["mode"])
            turn = await driver.respond(
                db,
                session=session,
                user_id=user_id,
                transcript=transcript,
                audio_meta=audio_meta,
                response_seconds=(
                    _clean_response_seconds(request.response_seconds) if session["mode"] == "pressure" else None
                ),
            )

            # Deterministic Step 8 metrics for this spoken answer (None fields when not measurable).
            voice_analysis = analyze_transcript(
                transcript,
                duration_seconds=duration,
                pause_metrics=pause_metrics,
                language=request.language,
            )
            audio_url, audio_error = await self._speak(user_id, turn.text)

            now = utcnow()
            self._sessions.append_exchange(
                db,
                session["_id"],
                token,
                user_message={
                    "role": "user",
                    "text": transcript,
                    "timestamp": now,
                    "input_type": "voice",
                    "duration_seconds": duration,
                    "voice_analysis": voice_analysis,
                },
                assistant_message={
                    "role": "assistant",
                    "text": turn.text,
                    "timestamp": utcnow(),
                    "audio_available": audio_url is not None,
                },
            )

            fresh = self._sessions.get_owned(db, session_id=session_id, user_id=user_id)
            complete = turn.complete or fresh["user_turn_count"] >= settings.voice_conversation_max_session_turns
            summary = None
            if complete:
                summary = await self._finalize(db, fresh, token)

            logger.info(
                "Voice turn processed user_id=%s session_id=%s mode=%s turn=%d complete=%s",
                user_id, session_id, session["mode"], fresh["user_turn_count"], complete,
            )
        finally:
            self._sessions.release_lock(db, session["_id"], token)

        return {
            "user_transcript": transcript,
            "user_voice_analysis": voice_analysis,
            "ai_response": turn.text,
            "audio_url": audio_url,
            "audio_error": audio_error,
            "turn_number": fresh["user_turn_count"],
            "conversation_complete": complete,
            "summary": summary,
            "mode_info": turn.info,
        }

    # --- End ------------------------------------------------------------------------------------------------

    async def _finalize(self, db: Database, session: dict, token: str) -> dict:
        """Evaluate (via the mode's existing engine), summarise and close. Caller holds the lock."""
        driver = self._engine.driver_for(session["mode"])
        evaluation = None
        evaluation_error = False
        try:
            finished = await driver.finish(db, session=session, user_id=str(session["user_id"]))
            evaluation = finished.evaluation
        except ConversationAIError:
            # Ending must not fail because the AI is down: close the session and say the evaluation is missing.
            evaluation_error = True
            logger.warning("Voice conversation evaluation failed session_id=%s mode=%s", session["_id"], session["mode"])

        summary = build_summary(session, evaluation=evaluation, evaluation_error=evaluation_error)
        status = "completed" if session.get("user_turn_count", 0) > 0 else "abandoned"
        self._sessions.finalize(
            db,
            session["_id"],
            token,
            status=status,
            summary=summary,
            evaluation=summary["evaluation"],
        )
        return summary

    async def end_session(self, db: Database, *, user_id: str, session_id: str) -> dict:
        """End a conversation. Idempotent: ending a finished session returns its stored summary."""
        session = self._sessions.get_owned(db, session_id=session_id, user_id=user_id)
        if session["status"] in ("completed", "abandoned"):
            return {"session": public_session(session), "summary": session.get("summary")}

        token = self._sessions.acquire_lock(db, session, allowed_statuses=("created", "active"))
        try:
            session = self._sessions.get_owned(db, session_id=session_id, user_id=user_id)
            if session["status"] not in ("completed", "abandoned"):
                await self._finalize(db, session, token)
        finally:
            self._sessions.release_lock(db, session["_id"], token)

        fresh = self._sessions.get_owned(db, session_id=session_id, user_id=user_id)
        logger.info("Voice conversation ended user_id=%s session_id=%s status=%s", user_id, session_id, fresh["status"])
        return {"session": public_session(fresh), "summary": fresh.get("summary")}


# Module-level singleton, matching the project's existing pattern.
voice_conversation_service = VoiceConversationService()

# Free-form modes are the only ones that use Step 11 context; re-exported for tests/docs.
FREEFORM_VOICE_MODES = FREEFORM_MODES
