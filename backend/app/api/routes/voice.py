"""
Voice routes (Step 8).

    GET  /api/v1/voice/capabilities
    POST /api/v1/voice/transcribe     multipart/form-data, field "audio"
    POST /api/v1/voice/synthesize     JSON {"text": "..."} -> audio

All routes require authentication. The route only handles HTTP concerns
(auth, size pre-check, error mapping); validation, temp files, STT and TTS
live in `VoiceService`. Audio and transcripts are never logged.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from starlette.datastructures import UploadFile

from app.core.config import settings
from app.core.dependencies import get_current_user, get_voice_service
from app.models.user import UserDocument
from app.schemas.voice import SynthesizeRequest
from app.services.voice.speech_to_text import (
    AudioTooLongError,
    MalformedAudioError,
    SpeechToTextError,
    TranscriptionUnavailableError,
)
from app.services.voice.text_to_speech import TTSError, TTSNotConfiguredError
from app.services.voice.voice_service import (
    AudioTooLargeError,
    AudioValidationError,
    EmptyAudioError,
    NoSpeechDetectedError,
    UnsupportedAudioError,
    VoiceService,
    read_upload_limited,
)
from app.utils.helpers import success_response
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/voice", tags=["voice"])

# Multipart framing (boundaries, headers) adds a little on top of the file.
_MULTIPART_OVERHEAD_BYTES = 64 * 1024


def _err(code: int, message: str, error_code: str) -> HTTPException:
    return HTTPException(status_code=code, detail={"message": message, "error_code": error_code})


@router.get("/capabilities")
def get_capabilities(
    current_user: UserDocument = Depends(get_current_user),
    service: VoiceService = Depends(get_voice_service),
) -> dict:
    """Public, non-secret description of which voice features are available."""
    return success_response(message="Voice capabilities", data=service.capabilities())


@router.post(
    "/transcribe",
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "required": ["audio"],
                        "properties": {"audio": {"type": "string", "format": "binary"}},
                    }
                }
            },
        }
    },
)
async def transcribe(
    request: Request,
    current_user: UserDocument = Depends(get_current_user),
    service: VoiceService = Depends(get_voice_service),
) -> dict:
    # Deliberately no `File(...)` parameter: FastAPI would parse (buffer) the
    # whole body *before* running the auth dependency. Reading the form here
    # means an unauthenticated request is rejected without being buffered.
    max_bytes = settings.voice_max_audio_bytes
    declared_length = request.headers.get("content-length")
    if declared_length is None:
        raise _err(status.HTTP_411_LENGTH_REQUIRED, "Content-Length is required.", "LENGTH_REQUIRED")
    try:
        if int(declared_length) > max_bytes + _MULTIPART_OVERHEAD_BYTES:
            raise _err(
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                "Audio file is too large.",
                "AUDIO_TOO_LARGE",
            )
    except ValueError:
        raise _err(status.HTTP_400_BAD_REQUEST, "Invalid Content-Length.", "BAD_REQUEST")

    try:
        async with request.form(max_files=1, max_fields=5) as form:
            upload = form.get("audio")
            if not isinstance(upload, UploadFile):
                raise _err(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "An audio file is required in the 'audio' field.",
                    "AUDIO_REQUIRED",
                )
            data = await read_upload_limited(upload, max_bytes)
            content_type = upload.content_type
    except HTTPException:
        raise
    except AudioTooLargeError:
        raise _err(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Audio file is too large.", "AUDIO_TOO_LARGE")
    except Exception:
        # Malformed multipart body etc.
        raise _err(status.HTTP_400_BAD_REQUEST, "Could not read the uploaded audio.", "BAD_REQUEST")

    user_id = str(current_user["_id"])
    try:
        outcome = await service.transcribe(data, content_type)
    except EmptyAudioError:
        raise _err(status.HTTP_400_BAD_REQUEST, "The recording is empty. Please try again.", "EMPTY_AUDIO")
    except AudioTooLargeError:
        raise _err(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Audio file is too large.", "AUDIO_TOO_LARGE")
    except UnsupportedAudioError:
        raise _err(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "Unsupported audio format.",
            "UNSUPPORTED_AUDIO",
        )
    except AudioValidationError:
        raise _err(status.HTTP_400_BAD_REQUEST, "Invalid audio upload.", "BAD_REQUEST")
    except MalformedAudioError:
        raise _err(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "The recording could not be read. Please try recording again.",
            "AUDIO_UNREADABLE",
        )
    except AudioTooLongError:
        raise _err(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Recording is longer than {settings.voice_max_audio_seconds} seconds.",
            "AUDIO_TOO_LONG",
        )
    except NoSpeechDetectedError:
        raise _err(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "No speech was detected. Please try again.",
            "NO_SPEECH_DETECTED",
        )
    except TranscriptionUnavailableError:
        logger.error("Speech-to-text unavailable user_id=%s", user_id)
        raise _err(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Speech recognition is unavailable right now. You can still type your response.",
            "STT_UNAVAILABLE",
        )
    except SpeechToTextError:
        logger.error("Speech-to-text failed user_id=%s", user_id)
        raise _err(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Speech recognition failed. Please try again or type your response.",
            "STT_FAILED",
        )

    # Metadata only — never the transcript.
    logger.info(
        "Transcribed audio user_id=%s bytes=%d duration=%.1fs", user_id, len(data), outcome.duration_seconds
    )
    return success_response(
        message="Audio transcribed",
        data={
            "text": outcome.text,
            "language": outcome.language,
            "duration_seconds": outcome.duration_seconds,
            "pause_metrics": outcome.pause_metrics,
        },
    )


@router.post("/synthesize")
async def synthesize(
    payload: SynthesizeRequest,
    current_user: UserDocument = Depends(get_current_user),
    service: VoiceService = Depends(get_voice_service),
) -> Response:
    try:
        audio = await service.synthesize(payload.text)
    except TTSNotConfiguredError:
        raise _err(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Text-to-speech is not configured.",
            "TTS_NOT_CONFIGURED",
        )
    except TTSError:
        logger.error("Text-to-speech failed user_id=%s", str(current_user["_id"]))
        raise _err(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Text-to-speech is temporarily unavailable.",
            "TTS_FAILED",
        )

    # Generated audio is returned once and not stored; no-store keeps
    # intermediaries/browsers from caching a spoken reply.
    return Response(
        content=audio.data,
        media_type=audio.media_type,
        headers={"Cache-Control": "no-store"},
    )
