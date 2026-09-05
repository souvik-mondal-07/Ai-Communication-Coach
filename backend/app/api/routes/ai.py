"""
AI routes.

    POST /api/v1/ai/chat

This is the reusable AI engine's test endpoint. Feature-specific chat UIs
(the full Mentor page, interview simulator, etc.) are built in later steps
on top of the same `AIService` this route already uses.
"""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_ai_service, get_current_user
from app.models.user import UserDocument
from app.schemas.ai import ChatRequest
from app.services.ai.ai_service import (
    AIConfigurationError,
    AIProviderError,
    AIService,
    AITimeoutError,
    ConversationTurn,
)
from app.utils.helpers import success_response
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])

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
    payload: ChatRequest,
    current_user: UserDocument = Depends(get_current_user),
    service: AIService = Depends(get_ai_service),
) -> dict:
    user_id = str(current_user["_id"])
    history = [
        ConversationTurn(role=item.role, content=item.content)
        for item in payload.conversation_history
    ]

    # Metadata only — never the message content, tokens, or any secret.
    logger.info(
        "AI request started user_id=%s history_len=%d", user_id, len(history)
    )
    started = time.perf_counter()

    try:
        result = await service.generate_response(
            user_message=payload.message, history=history
        )
    except AIConfigurationError:
        logger.error("AI request failed user_id=%s reason=configuration", user_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_SERVICE_UNAVAILABLE
        )
    except AITimeoutError:
        duration = time.perf_counter() - started
        logger.warning(
            "AI request timed out user_id=%s duration=%.2fs", user_id, duration
        )
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=_TIMEOUT
        )
    except AIProviderError:
        logger.error("AI request failed user_id=%s reason=provider_error", user_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=_SERVICE_UNAVAILABLE
        )
    except Exception:
        # Anything unexpected: log the technical detail server-side only,
        # return a safe generic message to the client.
        logger.error("AI request failed user_id=%s reason=unexpected", user_id, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "An unexpected error occurred.",
                "error_code": "INTERNAL_SERVER_ERROR",
            },
        )

    duration = time.perf_counter() - started
    logger.info(
        "AI request completed user_id=%s duration=%.2fs", user_id, duration
    )

    return success_response(
        message="AI response generated", data={"response": result.text}
    )
