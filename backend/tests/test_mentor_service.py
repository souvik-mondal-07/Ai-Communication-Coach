"""
Unit tests for MentorService's own logic, isolated from the route layer.
"""

from __future__ import annotations

import asyncio

from app.services.ai.ai_service import AIResponse, ConversationTurn
from app.services.mentor.mentor_service import CONTEXT_WINDOW, MentorService


class _FakeAIService:
    """Captures what MentorService actually forwards to AIService.generate_response."""

    def __init__(self) -> None:
        self.last_history: list[ConversationTurn] | None = None
        self.last_system_prompt: str | None = None

    async def generate_response(self, *, user_message, history=None, system_prompt=None, **_):
        self.last_history = list(history or [])
        self.last_system_prompt = system_prompt
        return AIResponse(text="ok", model="fake-model")


def test_history_longer_than_context_window_is_truncated():
    fake_ai = _FakeAIService()
    service = MentorService(ai_service_=fake_ai)  # type: ignore[arg-type]

    long_history = [ConversationTurn(role="user", content=f"turn {i}") for i in range(50)]

    asyncio.run(
        service.chat(message="latest question", mode="learn", level="intermediate", history=long_history)
    )

    assert fake_ai.last_history is not None
    assert len(fake_ai.last_history) == CONTEXT_WINDOW
    # The *most recent* turns are kept, not the oldest.
    assert fake_ai.last_history[-1].content == "turn 49"
    assert fake_ai.last_history[0].content == f"turn {50 - CONTEXT_WINDOW}"


def test_short_history_is_passed_through_unchanged():
    fake_ai = _FakeAIService()
    service = MentorService(ai_service_=fake_ai)  # type: ignore[arg-type]

    short_history = [ConversationTurn(role="user", content="hi")]

    asyncio.run(
        service.chat(message="question", mode="explain", level="beginner", history=short_history)
    )

    assert fake_ai.last_history is not None
    assert len(fake_ai.last_history) == 1


def test_mode_and_level_shape_the_system_prompt():
    fake_ai = _FakeAIService()
    service = MentorService(ai_service_=fake_ai)  # type: ignore[arg-type]

    asyncio.run(service.chat(message="q", mode="practice", level="advanced"))

    assert fake_ai.last_system_prompt is not None
    assert "PRACTICE" in fake_ai.last_system_prompt
    assert "ADVANCED" in fake_ai.last_system_prompt
