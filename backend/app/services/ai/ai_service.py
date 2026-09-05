"""
AI service.

The single entry point every feature (mentor chat, and later interview /
communication / CTF modules) should use to get an AI-generated response.
Callers never talk to Gemini directly — only to this module — so the
provider can change later without touching route or feature code:

    Feature code -> AIService.generate_response() -> GeminiClient -> Gemini API
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.services.ai.gemini import (
    GeminiClient,
    GeminiConfigurationError,
    GeminiMessage,
    GeminiRequestError,
    GeminiTimeoutError,
    gemini_client,
)
from app.services.ai.prompts import MENTOR_SYSTEM_PROMPT

Role = Literal["user", "assistant"]

# Reasonable ceiling so one request can't balloon into an enormous prompt.
MAX_HISTORY_MESSAGES = 40


class AIServiceError(Exception):
    """Base class for all AI-service-level errors (provider-agnostic)."""


class AIConfigurationError(AIServiceError):
    """The AI provider isn't configured (e.g. missing API key)."""


class AITimeoutError(AIServiceError):
    """The AI provider didn't respond within the configured timeout."""


class AIProviderError(AIServiceError):
    """The AI provider returned an error or an unusable response."""


@dataclass(frozen=True)
class ConversationTurn:
    role: Role
    content: str


@dataclass(frozen=True)
class AIResponse:
    text: str
    model: str


def _to_gemini_role(role: Role) -> str:
    # Gemini uses "model" where this app's public API uses "assistant".
    return "model" if role == "assistant" else "user"


class AIService:
    """Provider-agnostic AI facade. Currently backed by Gemini."""

    def __init__(self, client: GeminiClient = gemini_client) -> None:
        self._client = client

    async def generate_response(
        self,
        *,
        user_message: str,
        history: list[ConversationTurn] | None = None,
        system_prompt: str = MENTOR_SYSTEM_PROMPT,
    ) -> AIResponse:
        """
        Generate a mentor response for `user_message`, optionally continuing
        a prior conversation given in `history`.

        Raises `AIConfigurationError`, `AITimeoutError`, or `AIProviderError`
        on failure — callers should catch these, not provider-specific
        exceptions.
        """
        turns = list(history or [])[-MAX_HISTORY_MESSAGES:]
        messages = [
            GeminiMessage(role=_to_gemini_role(turn.role), text=turn.content)
            for turn in turns
        ]
        messages.append(GeminiMessage(role="user", text=user_message))

        try:
            result = await self._client.generate(
                system_instruction=system_prompt, messages=messages
            )
        except GeminiConfigurationError as exc:
            raise AIConfigurationError(str(exc)) from exc
        except GeminiTimeoutError as exc:
            raise AITimeoutError(str(exc)) from exc
        except GeminiRequestError as exc:
            raise AIProviderError(str(exc)) from exc

        return AIResponse(text=result.text, model=result.model)


# Module-level singleton, matching the project's existing pattern.
ai_service = AIService()
