"""
Mentor service.

Turns a mentor chat request (message + mode + level + history) into a call
to the shared, provider-agnostic `AIService`, using mode/level-specific
mentor prompts. This is the only place that knows how mentor mode/level map
onto prompt content — the route stays thin, and `AIService`/`GeminiClient`
stay completely generic:

    mentor.py (route) -> MentorService.chat() -> AIService.generate_response() -> GeminiClient -> Gemini
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.ai.ai_service import AIService, ConversationTurn, ai_service
from app.services.ai.prompts import build_mentor_system_prompt

# Bound the AI request even if a client sends a longer (still schema-valid)
# history — only the most recent turns are actually relevant context, and
# this keeps requests to Gemini from growing unbounded over a long session.
CONTEXT_WINDOW = 20


@dataclass(frozen=True)
class MentorChatResult:
    response: str
    mode: str
    level: str


class MentorService:
    """Mentor-specific orchestration on top of the generic AIService."""

    def __init__(self, ai_service_: AIService = ai_service) -> None:
        self._ai_service = ai_service_

    async def chat(
        self,
        *,
        message: str,
        mode: str,
        level: str,
        history: list[ConversationTurn] | None = None,
    ) -> MentorChatResult:
        """
        Generate a mentor reply for `message`, given the requested `mode`
        and `level` and (optionally) prior conversation turns.

        Raises whatever `AIService.generate_response` raises
        (`AIConfigurationError` / `AITimeoutError` / `AIProviderError`) —
        the route is responsible for translating those into HTTP responses.
        """
        bounded_history = list(history or [])[-CONTEXT_WINDOW:]
        system_prompt = build_mentor_system_prompt(mode=mode, level=level)

        result = await self._ai_service.generate_response(
            user_message=message,
            history=bounded_history,
            system_prompt=system_prompt,
        )

        return MentorChatResult(response=result.text, mode=mode, level=level)


# Module-level singleton, matching the project's existing pattern.
mentor_service = MentorService()
