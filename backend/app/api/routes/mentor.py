"""
Mentor routes.

    POST /api/v1/mentor/chat

The first real user-facing AI feature: a mode/level-aware cybersecurity
mentor built on the generic AIService from Step 3. This route never talks
to Gemini directly — it only calls MentorService, which calls AIService.
"""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_current_user, get_mentor_service
from app.models.user import UserDocument
from app.schemas.mentor import MentorChatRequest
from app.services.ai.ai_service import (
    AIConfigurationError,
    AIProviderError,
    AITimeoutError,
    ConversationTurn,
)
from app.services.mentor.mentor_service import MentorService
from app.utils.helpers import success_response
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/mentor", tags=["mentor"])

_SERVICE_UNAVAILABLE = {
    "message": "AI service is temporarily unavailable.",
    "error_code": "AI_SERVICE_UNAVAILABLE",
}

_TIMEOUT = {
    "message": "AI request timed out. Please try again.",
    "error_code": "AI_TIMEOUT",
}


@router.post("/chat")
async def chat(
    payload: MentorChatRequest,
    current_user: UserDocument = Depends(get_current_user),
    service: MentorService = Depends(get_mentor_service),
) -> dict:
    user_id = str(current_user["_id"])
    history = [
        ConversationTurn(role=item.role, content=item.content)
        for item in payload.conversation_history
    ]

    # Metadata only — never the message content, which may contain
    # sensitive details the user is troubleshooting with.
    logger.info(
        "Mentor request started user_id=%s mode=%s level=%s history_len=%d",
        user_id,
        payload.mode,
        payload.level,
        len(history),
    )
    started = time.perf_counter()

    try:
        result = await service.chat(
            message=payload.message,
            mode=payload.mode,
            level=payload.level,
            history=history,
        )
    except AIConfigurationError:
        logger.error("Mentor request failed user_id=%s reason=configuration", user_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_SERVICE_UNAVAILABLE
        )
    except AITimeoutError:
        duration = time.perf_counter() - started
        logger.warning(
            "Mentor request timed out user_id=%s duration=%.2fs", user_id, duration
        )
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=_TIMEOUT)
    except AIProviderError:
        logger.error("Mentor request failed user_id=%s reason=provider_error", user_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_SERVICE_UNAVAILABLE
        )
    except Exception:
        # Anything unexpected: log the technical detail server-side only,
        # return a safe generic message to the client.
        logger.error(
            "Mentor request failed user_id=%s reason=unexpected", user_id, exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "An unexpected error occurred.",
                "error_code": "INTERNAL_SERVER_ERROR",
            },
        )

    duration = time.perf_counter() - started
    logger.info("Mentor request completed user_id=%s duration=%.2fs", user_id, duration)

    return success_response(
        message="Mentor response generated",
        data={"response": result.response, "mode": result.mode, "level": result.level},
    )
