"""
Gemini client.

The only module in the codebase that talks to the Gemini API. All
SDK-specific details (client construction, request shape, error types,
timeout mechanics) live here; `ai_service.py` depends on this module's
small interface, not on the `google-genai` SDK directly.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types

from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class GeminiConfigurationError(Exception):
    """Raised when Gemini isn't configured correctly (e.g. missing API key)."""


class GeminiTimeoutError(Exception):
    """Raised when a Gemini request doesn't complete within the configured timeout."""


class GeminiRequestError(Exception):
    """Raised when Gemini returns an error, or an unexpected/empty response."""


@dataclass(frozen=True)
class GeminiMessage:
    """One turn of conversation in Gemini's terms: role is 'user' or 'model'."""

    role: str
    text: str


@dataclass(frozen=True)
class GeminiResponse:
    text: str
    model: str


def _redact(message: str) -> str:
    """
    Strip the configured API key out of a message before it's logged.
    Defensive measure — the SDK shouldn't echo the key, but never trust that.
    """
    api_key = settings.gemini_api_key
    if api_key and api_key in message:
        return message.replace(api_key, "[REDACTED]")
    return message


class GeminiClient:
    """Thin, app-facing wrapper around the official `google-genai` SDK."""

    def __init__(self) -> None:
        self._client: genai.Client | None = None

    def _get_client(self) -> genai.Client:
        if not settings.gemini_api_key:
            raise GeminiConfigurationError("Gemini API key is not configured.")

        if self._client is None:
            self._client = genai.Client(api_key=settings.gemini_api_key)

        return self._client

    async def generate(
        self, *, system_instruction: str, messages: list[GeminiMessage]
    ) -> GeminiResponse:
        """
        Send a system instruction plus a conversation to Gemini and return
        the generated text.

        Always raises one of this module's own exceptions on failure
        (`GeminiConfigurationError`, `GeminiTimeoutError`, or
        `GeminiRequestError`) — never a raw SDK exception, and never a
        message containing the API key.
        """
        client = self._get_client()

        contents = [
            genai_types.Content(
                role=message.role,
                parts=[genai_types.Part.from_text(text=message.text)],
            )
            for message in messages
        ]
        config = genai_types.GenerateContentConfig(system_instruction=system_instruction)

        try:
            response = await asyncio.wait_for(
                client.aio.models.generate_content(
                    model=settings.gemini_model,
                    contents=contents,
                    config=config,
                ),
                timeout=settings.gemini_timeout_seconds,
            )
        except TimeoutError as exc:
            raise GeminiTimeoutError("Gemini request timed out.") from exc
        except genai_errors.APIError as exc:
            # Covers ClientError/ServerError. Log a short, redacted summary
            # only — never propagate the raw provider exception to the caller.
            logger.error("Gemini API error: %s", _redact(str(exc))[:300])
            raise GeminiRequestError("Gemini API request failed.") from exc
        except Exception as exc:  # noqa: BLE001 - translate anything unexpected too
            logger.error("Unexpected Gemini client error: %s", _redact(str(exc))[:300])
            raise GeminiRequestError("Gemini API request failed.") from exc

        text = getattr(response, "text", None)
        if not text:
            raise GeminiRequestError("Gemini returned an empty response.")

        return GeminiResponse(text=text, model=settings.gemini_model)


# Module-level singleton, matching the project's existing pattern
# (e.g. `settings`, `mongodb`) — one client reused across requests.
gemini_client = GeminiClient()
