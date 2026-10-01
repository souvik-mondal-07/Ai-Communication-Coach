"""
Voice conversation routes (Step 13).

    POST /api/v1/voice-conversation/sessions
    GET  /api/v1/voice-conversation/sessions
    GET  /api/v1/voice-conversation/sessions/{session_id}
    POST /api/v1/voice-conversation/sessions/{session_id}/start
    POST /api/v1/voice-conversation/sessions/{session_id}/transcribe  multipart, field "audio" -> transcript only
    POST /api/v1/voice-conversation/sessions/{session_id}/respond     JSON {transcript, expected_turn, ...} -> AI turn
    POST /api/v1/voice-conversation/sessions/{session_id}/end
    GET  /api/v1/voice-conversation/audio/{token}                   short-lived AI speech
    GET  /api/v1/voice-conversation/config

All routes require authentication and the owner is always the JWT user. The
routes only handle HTTP concerns (auth, upload size pre-check, error
mapping); everything else lives in `VoiceConversationService`. Internal
errors, provider messages and stack traces are never returned.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pymongo.database import Database
from starlette.datastructures import UploadFile

from app.core.config import settings
from app.core.dependencies import get_current_user, get_db, get_voice_conversation_service
from app.models.user import UserDocument
from app.schemas.voice_conversation import CreateVoiceSessionRequest, ProcessTranscriptRequest
from app.services.voice.speech_to_text import (
    AudioTooLongError,
    MalformedAudioError,
    SpeechToTextError,
    TranscriptionUnavailableError,
)
from app.services.voice.voice_service import (
    AudioTooLargeError,
    AudioValidationError,
    EmptyAudioError,
    NoSpeechDetectedError,
    UnsupportedAudioError,
    read_upload_limited,
)
from app.services.voice_conversation.conversation_service import (
    EMPTY_TRANSCRIPT_MESSAGE,
    ConversationAIError,
    ConversationConfigError,
    ConversationStateError,
    EmptyTranscriptError,
    RecordingTooLongError,
    SessionBusyError,
    SessionForbiddenError,
    SessionNotActiveError,
    SessionNotFoundError,
    TurnMismatchError,
    VoiceConversationService,
)
from app.utils.helpers import success_response
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/voice-conversation", tags=["voice-conversation"])

MAX_HISTORY_LIMIT = 50
_MULTIPART_OVERHEAD_BYTES = 64 * 1024


def _err(code: int, message: str, error_code: str) -> HTTPException:
    return HTTPException(status_code=code, detail={"message": message, "error_code": error_code})


_NOT_FOUND = _err(404, "Voice conversation not found.", "SESSION_NOT_FOUND")
_FORBIDDEN = _err(403, "You don't have access to this voice conversation.", "SESSION_FORBIDDEN")
_NOT_ACTIVE = _err(409, "This conversation is not active.", "SESSION_NOT_ACTIVE")
_BUSY = _err(409, "Your previous answer is still being processed.", "SESSION_BUSY")
_AI_DOWN = _err(
    503, "The AI mentor is temporarily unavailable. Your answer wasn't lost — please try again.", "AI_SERVICE_UNAVAILABLE"
)
_UNEXPECTED = _err(500, "An unexpected error occurred.", "INTERNAL_SERVER_ERROR")


def _map_session_errors(exc: Exception, user_id: str, action: str) -> HTTPException:
    """Shared mapping for errors every session endpoint can raise."""
    if isinstance(exc, SessionNotFoundError):
        return _NOT_FOUND
    if isinstance(exc, SessionForbiddenError):
        return _FORBIDDEN
    if isinstance(exc, SessionNotActiveError):
        return _NOT_ACTIVE
    if isinstance(exc, SessionBusyError):
        return _BUSY
    if isinstance(exc, TurnMismatchError):
        return _err(409, "This answer is out of date. Please refresh the conversation.", "TURN_MISMATCH")
    if isinstance(exc, ConversationConfigError):
        return _err(404, "The requested scenario was not found.", "SCENARIO_NOT_FOUND")
    if isinstance(exc, ConversationStateError):
        return _err(409, "This conversation can no longer continue.", "SESSION_NOT_ACTIVE")
    if isinstance(exc, ConversationAIError):
        logger.error("Voice conversation AI failure action=%s user_id=%s", action, user_id)
        return _AI_DOWN
    logger.error("Unexpected voice conversation error action=%s user_id=%s", action, user_id, exc_info=exc)
    return _UNEXPECTED


_SESSION_ERRORS = (
    SessionNotFoundError, SessionForbiddenError, SessionNotActiveError, SessionBusyError, TurnMismatchError,
    ConversationConfigError, ConversationStateError, ConversationAIError,
)


@router.get("/config")
def get_config(
    current_user: UserDocument = Depends(get_current_user),
    service: VoiceConversationService = Depends(get_voice_conversation_service),
) -> dict:
    return success_response(message="Voice conversation configuration", data=service.get_config())


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
def create_session(
    payload: CreateVoiceSessionRequest,
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: VoiceConversationService = Depends(get_voice_conversation_service),
) -> dict:
    user_id = str(current_user["_id"])
    try:
        session = service.create_session(db, user_id=user_id, request=payload)
    except _SESSION_ERRORS as exc:
        raise _map_session_errors(exc, user_id, "create")
    return success_response(message="Voice conversation created", data={"session": session})


@router.get("/sessions")
def list_sessions(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=MAX_HISTORY_LIMIT),
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: VoiceConversationService = Depends(get_voice_conversation_service),
) -> dict:
    result = service.list_sessions(db, user_id=str(current_user["_id"]), page=page, limit=limit)
    return success_response(message="Voice conversations retrieved", data=result)


@router.get("/sessions/{session_id}")
def get_session(
    session_id: str,
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: VoiceConversationService = Depends(get_voice_conversation_service),
) -> dict:
    user_id = str(current_user["_id"])
    try:
        session = service.get_session(db, user_id=user_id, session_id=session_id)
    except _SESSION_ERRORS as exc:
        raise _map_session_errors(exc, user_id, "get")
    return success_response(message="Voice conversation retrieved", data={"session": session})


@router.post("/sessions/{session_id}/start")
async def start_session(
    session_id: str,
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: VoiceConversationService = Depends(get_voice_conversation_service),
) -> dict:
    user_id = str(current_user["_id"])
    try:
        result = await service.start_session(db, user_id=user_id, session_id=session_id)
    except _SESSION_ERRORS as exc:
        raise _map_session_errors(exc, user_id, "start")
    except Exception as exc:  # noqa: BLE001 - never leak internals
        raise _map_session_errors(exc, user_id, "start")
    return success_response(message="Voice conversation started", data=result)


def _map_stt_errors(exc: Exception, user_id: str) -> HTTPException:
    """Audio validation and speech-to-text failures (only `/transcribe` can raise these)."""
    if isinstance(exc, EmptyAudioError):
        return _err(400, "The recording is empty. Please try again.", "EMPTY_AUDIO")
    if isinstance(exc, AudioTooLargeError):
        return _err(413, "Audio file is too large.", "AUDIO_TOO_LARGE")
    if isinstance(exc, UnsupportedAudioError):
        return _err(415, "Unsupported audio format.", "UNSUPPORTED_AUDIO")
    if isinstance(exc, AudioValidationError):
        return _err(400, "Invalid audio upload.", "BAD_REQUEST")
    if isinstance(exc, MalformedAudioError):
        return _err(422, "The recording could not be read. Please try recording again.", "AUDIO_UNREADABLE")
    if isinstance(exc, (AudioTooLongError, RecordingTooLongError)):
        return _err(
            422,
            f"Please keep each answer under {settings.voice_max_recording_seconds} seconds.",
            "AUDIO_TOO_LONG",
        )
    if isinstance(exc, NoSpeechDetectedError):
        # Normally absorbed by the service (empty transcript); kept as a safe fallback.
        return _err(422, EMPTY_TRANSCRIPT_MESSAGE, "NO_SPEECH_DETECTED")
    if isinstance(exc, TranscriptionUnavailableError):
        logger.error("Speech-to-text unavailable user_id=%s", user_id)
        return _err(503, "Speech recognition is unavailable right now.", "STT_UNAVAILABLE")
    if isinstance(exc, SpeechToTextError):
        logger.error("Speech-to-text failed user_id=%s", user_id)
        return _err(503, "Speech recognition failed. Please try again.", "STT_FAILED")
    return _map_session_errors(exc, user_id, "transcribe")


@router.post(
    "/sessions/{session_id}/transcribe",
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "required": ["audio"],
                        "properties": {
                            "audio": {"type": "string", "format": "binary"},
                            "expected_turn": {"type": "integer"},
                        },
                    }
                }
            },
        }
    },
)
async def transcribe(
    session_id: str,
    request: Request,
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: VoiceConversationService = Depends(get_voice_conversation_service),
) -> dict:
    """Speech-to-text only: returns the transcript. No AI, no TTS, nothing is saved."""
    user_id = str(current_user["_id"])

    # No `File(...)` parameter: FastAPI would buffer the whole body before auth ran.
    max_bytes = settings.voice_max_audio_bytes
    declared_length = request.headers.get("content-length")
    if declared_length is None:
        raise _err(status.HTTP_411_LENGTH_REQUIRED, "Content-Length is required.", "LENGTH_REQUIRED")
    try:
        too_big = int(declared_length) > max_bytes + _MULTIPART_OVERHEAD_BYTES
    except ValueError:
        raise _err(status.HTTP_400_BAD_REQUEST, "Invalid Content-Length.", "BAD_REQUEST")
    if too_big:
        raise _err(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Audio file is too large.", "AUDIO_TOO_LARGE")

    try:
        async with request.form(max_files=1, max_fields=5) as form:
            upload = form.get("audio")
            if not isinstance(upload, UploadFile):
                raise _err(422, "An audio file is required in the 'audio' field.", "AUDIO_REQUIRED")
            data = await read_upload_limited(upload, max_bytes)
            content_type = upload.content_type
            expected_turn = _int_field(form.get("expected_turn"))
    except HTTPException:
        raise
    except AudioTooLargeError:
        raise _err(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Audio file is too large.", "AUDIO_TOO_LARGE")
    except Exception:
        raise _err(status.HTTP_400_BAD_REQUEST, "Could not read the uploaded audio.", "BAD_REQUEST")

    try:
        result = await service.transcribe_audio(
            db,
            user_id=user_id,
            session_id=session_id,
            audio=data,
            content_type=content_type,
            expected_turn=expected_turn,
        )
    except Exception as exc:  # noqa: BLE001 - mapped to a clean, generic error
        raise _map_stt_errors(exc, user_id)

    return success_response(message="Answer transcribed", data=result)


@router.post("/sessions/{session_id}/respond")
async def respond(
    session_id: str,
    payload: ProcessTranscriptRequest,
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: VoiceConversationService = Depends(get_voice_conversation_service),
) -> dict:
    """
    One transcribed answer -> the AI's reply (+ speech). JSON, no audio: also the
    "Retry response" path, which must never trigger speech-to-text again.
    """
    user_id = str(current_user["_id"])
    try:
        result = await service.process_transcript(db, user_id=user_id, session_id=session_id, request=payload)
    except EmptyTranscriptError:
        raise _err(422, EMPTY_TRANSCRIPT_MESSAGE, "EMPTY_TRANSCRIPT")
    except RecordingTooLongError:
        raise _err(
            422,
            f"Please keep each answer under {settings.voice_max_recording_seconds} seconds.",
            "AUDIO_TOO_LONG",
        )
    except Exception as exc:  # noqa: BLE001 - mapped to a clean, generic error
        raise _map_session_errors(exc, user_id, "respond")

    return success_response(message="Turn processed", data=result)


@router.post("/sessions/{session_id}/end")
async def end_session(
    session_id: str,
    db: Database = Depends(get_db),
    current_user: UserDocument = Depends(get_current_user),
    service: VoiceConversationService = Depends(get_voice_conversation_service),
) -> dict:
    user_id = str(current_user["_id"])
    try:
        result = await service.end_session(db, user_id=user_id, session_id=session_id)
    except Exception as exc:  # noqa: BLE001
        raise _map_session_errors(exc, user_id, "end")
    return success_response(message="Voice conversation ended", data=result)


@router.get("/audio/{token}")
def get_audio(
    token: str,
    current_user: UserDocument = Depends(get_current_user),
    service: VoiceConversationService = Depends(get_voice_conversation_service),
) -> Response:
    """AI speech for one turn. Bound to the requesting user, short-lived, never cached."""
    audio = service.get_audio(user_id=str(current_user["_id"]), token=token)
    if audio is None:
        raise _err(404, "This audio is no longer available.", "AUDIO_NOT_FOUND")
    return Response(content=audio.data, media_type=audio.media_type, headers={"Cache-Control": "no-store"})


def _int_field(value: object) -> int | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = int(value)
    except ValueError:
        return None
    return parsed if 0 <= parsed <= 10_000 else None
