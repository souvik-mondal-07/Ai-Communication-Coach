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
        mentor_context: dict | None = None,
    ) -> MentorChatResult:
        """
        Generate a mentor reply for `message`, given the requested `mode`
        and `level` and (optionally) prior conversation turns.

        `mentor_context` is the compact, Step 11 personal-profile context
        (see `app.services.progress.profile_service.build_mentor_context`) --
        strong/weak areas, recent focus, recommended focus. It is entirely
        optional: when omitted (or empty), the mentor behaves exactly as it
        did before Step 11. When present, it is appended to the system
        prompt as a short, clearly-labeled block so the model can
        personalize its explanations without ever seeing raw session data.

        Raises whatever `AIService.generate_response` raises
        (`AIConfigurationError` / `AITimeoutError` / `AIProviderError`) —
        the route is responsible for translating those into HTTP responses.
        """
        bounded_history = list(history or [])[-CONTEXT_WINDOW:]
        system_prompt = build_mentor_system_prompt(mode=mode, level=level)
        if mentor_context:
            system_prompt = f"{system_prompt}\n\n{_build_mentor_context_block(mentor_context)}"

        result = await self._ai_service.generate_response(
            user_message=message,
            history=bounded_history,
            system_prompt=system_prompt,
        )

        return MentorChatResult(response=result.text, mode=mode, level=level)


def _build_mentor_context_block(mentor_context: dict) -> str:
    """Small, clearly-labeled personalization block -- never raw session history."""
    strong = ", ".join(mentor_context.get("strong_areas") or []) or "none observed yet"
    weak = ", ".join(mentor_context.get("weak_areas") or []) or "none observed yet"
    recent = ", ".join(mentor_context.get("recent_focus") or []) or "none yet"
    recommended = ", ".join(mentor_context.get("recommended_focus") or []) or "none yet"
    level = mentor_context.get("technical_level", "beginner")
    return (
        "LEARNER CONTEXT (from this user's personal progress profile -- use it to "
        "personalize explanations, e.g. spend more time on weak areas and build on "
        "strong ones; never mention this block explicitly to the user):\n"
        f"- Current technical level: {level}\n"
        f"- Strong areas: {strong}\n"
        f"- Areas needing work: {weak}\n"
        f"- Recently practiced: {recent}\n"
        f"- Recommended next focus: {recommended}"
    )


# Module-level singleton, matching the project's existing pattern.
mentor_service = MentorService()
