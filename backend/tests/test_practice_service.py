"""
Unit tests for PracticeService's own validation logic, isolated from the
route/DB layer — specifically that malformed/invalid AI-generated JSON is
rejected rather than trusted blindly.
"""

from __future__ import annotations

import asyncio
import json

import pytest

from app.services.ai.ai_service import AIResponse
from app.services.cybersecurity.practice_service import (
    PracticeGenerationError,
    PracticeService,
    _parse_json_object,
    _validate_generated_question,
)
from app.services.cybersecurity.learning_service import learning_service


class _FixedAIService:
    """Always returns the same canned text, regardless of prompt."""

    def __init__(self, text: str):
        self.text = text
        self.calls = 0

    async def generate_response(self, *, user_message, system_prompt=None, history=None, **_):
        self.calls += 1
        return AIResponse(text=self.text, model="fake-model")


def test_parse_json_object_strips_markdown_fences():
    fenced = '```json\n{"a": 1}\n```'
    assert _parse_json_object(fenced) == {"a": 1}


def test_parse_json_object_rejects_non_json():
    with pytest.raises(ValueError):
        _parse_json_object("this is not json at all")


def test_parse_json_object_rejects_json_array():
    with pytest.raises(ValueError):
        _parse_json_object("[1, 2, 3]")


def test_validate_generated_question_accepts_valid_multiple_choice():
    data = {
        "question": "Which protocol is connection-oriented?",
        "type": "multiple_choice",
        "options": ["TCP", "UDP", "ICMP", "ARP"],
        "correct_answer": "TCP",
        "ideal_answer": None,
        "explanation": "TCP uses a handshake.",
    }
    validated = _validate_generated_question(data, expected_type="multiple_choice")
    assert validated.correct_answer == "TCP"


def test_validate_generated_question_rejects_correct_answer_not_in_options():
    data = {
        "question": "Which protocol is connection-oriented?",
        "type": "multiple_choice",
        "options": ["TCP", "UDP", "ICMP", "ARP"],
        "correct_answer": "SCTP",  # not one of the options
        "ideal_answer": None,
        "explanation": "...",
    }
    with pytest.raises(ValueError):
        _validate_generated_question(data, expected_type="multiple_choice")

def test_validate_generated_question_rejects_missing_ideal_answer_for_short_answer():
    data = {
        "question": "Explain the handshake.",
        "type": "short_answer",
        "options": None,
        "correct_answer": None,
        "ideal_answer": None,  # required for short_answer
        "explanation": "...",
    }
    with pytest.raises(ValueError):
        _validate_generated_question(data, expected_type="short_answer")


def test_validate_generated_question_rejects_wrong_type_field():
    data = {
        "question": "Explain the handshake.",
        "type": "short_answer",
        "options": None,
        "correct_answer": None,
        "ideal_answer": "SYN, SYN-ACK, ACK.",
        "explanation": "...",
    }
    with pytest.raises(ValueError):
        _validate_generated_question(data, expected_type="multiple_choice")


def test_start_session_raises_generation_error_when_ai_returns_garbage():
    fake_ai = _FixedAIService("not valid json, sorry")
    service = PracticeService(ai_service_=fake_ai, learning_service_=learning_service)

    import mongomock

    db = mongomock.MongoClient()["test"]
    learning_service.ensure_indexes(db)
    learning_service.ensure_seeded(db)

    with pytest.raises(PracticeGenerationError):
        asyncio.run(
            service.start_session(
                db, user_id="000000000000000000000000", topic_slug="tcp-vs-udp",
                difficulty=None, question_count=1,
            )
        )

    # Retried once before giving up (MAX_GENERATION_ATTEMPTS = 2).
    assert fake_ai.calls == 2
