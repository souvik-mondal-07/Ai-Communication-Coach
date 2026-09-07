"""
Cybersecurity practice endpoint tests.

Two styles of test double are used here:

1. `_FakePracticeService` — a full stand-in for the route-level tests
   (auth requirement, validation, error-code mapping) where we don't need
   real session/scoring logic.
2. A *real* `PracticeService`, constructed with a scripted fake `AIService`
   (`_ScriptedAIService`) instead of the real Gemini-backed one — used for
   the full functional flow (start -> answer -> complete -> history ->
   progress) and the cross-user ownership check, so the actual session
   persistence/ownership/scoring code runs for real, with no network calls.
"""

from __future__ import annotations

import json

import pytest

from app.core.dependencies import get_practice_service
from app.main import app
from app.services.ai.ai_service import AIResponse
from app.services.cybersecurity.learning_service import learning_service
from app.services.cybersecurity.practice_service import (
    AnswerEvaluationError,
    AnswerResult,
    PracticeGenerationError,
    PracticeService,
    QuestionNotFoundError,
    SessionForbiddenError,
    SessionNotFoundError,
)

VALID_PASSWORD = "correct-horse-battery-staple"


def _register_and_login(client, email="practice-user@example.com") -> str:
    client.post(
        "/api/v1/auth/register",
        json={"name": "Practice User", "email": email, "password": VALID_PASSWORD},
    )
    login = client.post(
        "/api/v1/auth/login", json={"email": email, "password": VALID_PASSWORD}
    )
    return login.json()["data"]["access_token"]


# --- Route-level fake for auth/validation/error-mapping tests ---------------


class _FakePracticeService:
    def __init__(self, *, start_error=None, answer_error=None):
        self.start_error = start_error
        self.answer_error = answer_error

    async def start_session(self, db, *, user_id, topic_slug, difficulty, question_count):
        if self.start_error is not None:
            raise self.start_error
        return {
            "session_id": "fake-session-id",
            "topic_slug": topic_slug,
            "topic_title": "Fake Topic",
            "difficulty": difficulty or "beginner",
            "questions": [{"question_id": "q1", "question": "Q?", "type": "short_answer", "options": None}],
        }

    async def submit_answer(self, db, *, user_id, session_id, question_id, answer):
        if self.answer_error is not None:
            raise self.answer_error
        return AnswerResult(score=90, correct=True, feedback="Nice.", ideal_answer="ideal", missing_points=[])

    def complete_session(self, db, *, user_id, session_id):
        return {
            "session_id": session_id, "score": 80, "questions_answered": 1, "correct_answers": 1,
            "topic_title": "Fake Topic", "category": "Networking", "weak_areas": [], "recommendations": [],
        }

    def get_history(self, db, *, user_id, page, limit):
        return {"sessions": [], "page": page, "limit": limit, "total": 0}

    def get_progress(self, db, *, user_id):
        return {"categories": [], "weak_categories": []}


@pytest.fixture()
def override_practice_service():
    def _install(fake):
        app.dependency_overrides[get_practice_service] = lambda: fake
        return fake

    yield _install
    app.dependency_overrides.pop(get_practice_service, None)


class TestAuthenticationRequired:
    def test_start_requires_auth(self, client, override_practice_service):
        override_practice_service(_FakePracticeService())
        response = client.post(
            "/api/v1/cybersecurity/practice/start",
            json={"topic_slug": "tcp-vs-udp"},
        )
        assert response.status_code == 401

    def test_answer_requires_auth(self, client, override_practice_service):
        override_practice_service(_FakePracticeService())
        response = client.post(
            "/api/v1/cybersecurity/practice/some-id/answer",
            json={"question_id": "q1", "answer": "TCP"},
        )
        assert response.status_code == 401

    def test_complete_requires_auth(self, client, override_practice_service):
        override_practice_service(_FakePracticeService())
        response = client.post("/api/v1/cybersecurity/practice/some-id/complete")
        assert response.status_code == 401

    def test_history_requires_auth(self, client, override_practice_service):
        override_practice_service(_FakePracticeService())
        response = client.get("/api/v1/cybersecurity/practice/history")
        assert response.status_code == 401


class TestValidation:
    def test_blank_topic_slug_is_rejected(self, client, override_practice_service):
        override_practice_service(_FakePracticeService())
        token = _register_and_login(client, email="validate-slug@example.com")
        response = client.post(
            "/api/v1/cybersecurity/practice/start",
            json={"topic_slug": ""},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    def test_question_count_too_low_is_rejected(self, client, override_practice_service):
        override_practice_service(_FakePracticeService())
        token = _register_and_login(client, email="validate-count-low@example.com")
        response = client.post(
            "/api/v1/cybersecurity/practice/start",
            json={"topic_slug": "tcp-vs-udp", "question_count": 0},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    def test_question_count_too_high_is_rejected(self, client, override_practice_service):
        override_practice_service(_FakePracticeService())
        token = _register_and_login(client, email="validate-count-high@example.com")
        response = client.post(
            "/api/v1/cybersecurity/practice/start",
            json={"topic_slug": "tcp-vs-udp", "question_count": 11},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    def test_blank_answer_is_rejected(self, client, override_practice_service):
        override_practice_service(_FakePracticeService())
        token = _register_and_login(client, email="validate-answer@example.com")
        response = client.post(
            "/api/v1/cybersecurity/practice/some-id/answer",
            json={"question_id": "q1", "answer": "   "},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422


class TestRealTopicNotFound:
    """Uses the real practice service (no override) — TopicNotFoundError is
    raised before any AI call happens, so this is safe without a fake AI."""

    def test_start_with_unknown_topic_returns_404(self, client):
        token = _register_and_login(client, email="unknown-topic-practice@example.com")
        response = client.post(
            "/api/v1/cybersecurity/practice/start",
            json={"topic_slug": "does-not-exist"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404
        assert response.json()["error_code"] == "TOPIC_NOT_FOUND"


class TestMockedErrorHandling:
    def test_generation_failure_returns_safe_error(self, client, override_practice_service):
        override_practice_service(_FakePracticeService(start_error=PracticeGenerationError("boom")))
        token = _register_and_login(client, email="gen-fail@example.com")
        response = client.post(
            "/api/v1/cybersecurity/practice/start",
            json={"topic_slug": "tcp-vs-udp"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 503
        assert response.json()["error_code"] == "AI_SERVICE_UNAVAILABLE"
        assert "boom" not in response.json()["message"]

    def test_evaluation_failure_returns_safe_error(self, client, override_practice_service):
        override_practice_service(_FakePracticeService(answer_error=AnswerEvaluationError("boom")))
        token = _register_and_login(client, email="eval-fail@example.com")
        response = client.post(
            "/api/v1/cybersecurity/practice/some-id/answer",
            json={"question_id": "q1", "answer": "TCP"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 503
        assert response.json()["error_code"] == "AI_SERVICE_UNAVAILABLE"

    def test_session_not_found_returns_404(self, client, override_practice_service):
        override_practice_service(_FakePracticeService(answer_error=SessionNotFoundError("x")))
        token = _register_and_login(client, email="session-404@example.com")
        response = client.post(
            "/api/v1/cybersecurity/practice/nope/answer",
            json={"question_id": "q1", "answer": "TCP"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404
        assert response.json()["error_code"] == "SESSION_NOT_FOUND"

    def test_session_forbidden_returns_403(self, client, override_practice_service):
        override_practice_service(_FakePracticeService(answer_error=SessionForbiddenError("x")))
        token = _register_and_login(client, email="session-403@example.com")
        response = client.post(
            "/api/v1/cybersecurity/practice/not-mine/answer",
            json={"question_id": "q1", "answer": "TCP"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403
        assert response.json()["error_code"] == "SESSION_FORBIDDEN"

    def test_question_not_found_returns_404(self, client, override_practice_service):
        override_practice_service(_FakePracticeService(answer_error=QuestionNotFoundError("x")))
        token = _register_and_login(client, email="question-404@example.com")
        response = client.post(
            "/api/v1/cybersecurity/practice/some-id/answer",
            json={"question_id": "not-real", "answer": "TCP"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404
        assert response.json()["error_code"] == "QUESTION_NOT_FOUND"


class TestHistoryAndProgress:
    def test_history_returns_paginated_shape(self, client, override_practice_service):
        override_practice_service(_FakePracticeService())
        token = _register_and_login(client, email="history-shape@example.com")
        response = client.get(
            "/api/v1/cybersecurity/practice/history?page=2&limit=5",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["page"] == 2 and data["limit"] == 5

    def test_history_limit_is_capped(self, client, override_practice_service):
        override_practice_service(_FakePracticeService())
        token = _register_and_login(client, email="history-cap@example.com")
        response = client.get(
            "/api/v1/cybersecurity/practice/history?limit=999",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422  # exceeds le=50


# --- Full real-service flow with a scripted (non-network) AI backend -------


class _ScriptedAIService:
    """Returns valid, schema-conformant JSON for generation/evaluation without any network call."""

    async def generate_response(self, *, user_message, system_prompt=None, history=None, **_):
        if "Generate ONE cybersecurity practice question" in user_message:
            if "Question type: multiple_choice" in user_message:
                payload = {
                    "question": "Which protocol is connection-oriented?",
                    "type": "multiple_choice",
                    "options": ["TCP", "UDP", "ICMP", "ARP"],
                    "correct_answer": "TCP",
                    "ideal_answer": None,
                    "explanation": "TCP establishes a connection via the three-way handshake.",
                }
            else:
                payload = {
                    "question": "Explain the TCP three-way handshake.",
                    "type": "short_answer",
                    "options": None,
                    "correct_answer": None,
                    "ideal_answer": "SYN, then SYN-ACK, then ACK establishes the connection.",
                    "explanation": "Confirms both directions can communicate before data flows.",
                }
            return AIResponse(text=json.dumps(payload), model="fake-model")

        payload = {
            "score": 85,
            "correct": True,
            "feedback": "Solid answer — you covered the key steps.",
            "missing_points": ["Could mention sequence numbers"],
        }
        return AIResponse(text=json.dumps(payload), model="fake-model")


@pytest.fixture()
def real_practice_service():
    """A real PracticeService wired to a scripted fake AI backend (no network calls)."""
    return PracticeService(ai_service_=_ScriptedAIService(), learning_service_=learning_service)


@pytest.fixture()
def with_real_practice_service(real_practice_service):
    app.dependency_overrides[get_practice_service] = lambda: real_practice_service
    yield real_practice_service
    app.dependency_overrides.pop(get_practice_service, None)


class TestFullPracticeFlow:
    def test_complete_flow_start_answer_complete_history(self, client, with_real_practice_service):
        token = _register_and_login(client, email="full-flow@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        start = client.post(
            "/api/v1/cybersecurity/practice/start",
            json={"topic_slug": "tcp-vs-udp", "question_count": 2},
            headers=headers,
        )
        assert start.status_code == 200
        start_data = start.json()["data"]
        session_id = start_data["session_id"]
        questions = start_data["questions"]
        assert len(questions) == 2
        # Public questions never include the answer key.
        for q in questions:
            assert "correct_answer" not in q
            assert "ideal_answer" not in q

        for q in questions:
            answer_value = "TCP" if q["type"] == "multiple_choice" else "It's SYN, SYN-ACK, ACK."
            answer_resp = client.post(
                f"/api/v1/cybersecurity/practice/{session_id}/answer",
                json={"question_id": q["question_id"], "answer": answer_value},
                headers=headers,
            )
            assert answer_resp.status_code == 200
            body = answer_resp.json()["data"]
            assert 0 <= body["score"] <= 100
            assert "feedback" in body

        complete = client.post(
            f"/api/v1/cybersecurity/practice/{session_id}/complete", headers=headers
        )
        assert complete.status_code == 200
        complete_data = complete.json()["data"]
        assert complete_data["questions_answered"] == 2
        assert complete_data["score"] > 0

        # Completing again is idempotent, not an error.
        complete_again = client.post(
            f"/api/v1/cybersecurity/practice/{session_id}/complete", headers=headers
        )
        assert complete_again.status_code == 200
        assert complete_again.json()["data"]["score"] == complete_data["score"]

        history = client.get("/api/v1/cybersecurity/practice/history", headers=headers)
        assert history.status_code == 200
        sessions = history.json()["data"]["sessions"]
        assert any(s["session_id"] == session_id for s in sessions)

        progress = client.get("/api/v1/cybersecurity/progress", headers=headers)
        assert progress.status_code == 200
        categories = progress.json()["data"]["categories"]
        assert any(c["category"] == "Networking" for c in categories)

    def test_multiple_choice_wrong_answer_scores_zero(self, client, with_real_practice_service):
        token = _register_and_login(client, email="mc-wrong@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        start = client.post(
            "/api/v1/cybersecurity/practice/start",
            json={"topic_slug": "tcp-vs-udp", "question_count": 1},
            headers=headers,
        )
        session_id = start.json()["data"]["session_id"]
        question = start.json()["data"]["questions"][0]

        response = client.post(
            f"/api/v1/cybersecurity/practice/{session_id}/answer",
            json={"question_id": question["question_id"], "answer": "UDP"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["data"]["score"] == 0
        assert response.json()["data"]["correct"] is False


class TestSessionOwnership:
    def test_user_cannot_access_another_users_session(self, client, with_real_practice_service):
        token_a = _register_and_login(client, email="owner-a@example.com")
        token_b = _register_and_login(client, email="owner-b@example.com")

        start = client.post(
            "/api/v1/cybersecurity/practice/start",
            json={"topic_slug": "tcp-vs-udp", "question_count": 1},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        session_id = start.json()["data"]["session_id"]
        question_id = start.json()["data"]["questions"][0]["question_id"]

        # User A can answer their own session.
        own_answer = client.post(
            f"/api/v1/cybersecurity/practice/{session_id}/answer",
            json={"question_id": question_id, "answer": "TCP"},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert own_answer.status_code == 200

        # User B must NOT be able to answer or complete User A's session.
        forbidden_answer = client.post(
            f"/api/v1/cybersecurity/practice/{session_id}/answer",
            json={"question_id": question_id, "answer": "TCP"},
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert forbidden_answer.status_code == 403
        assert forbidden_answer.json()["error_code"] == "SESSION_FORBIDDEN"

        forbidden_complete = client.post(
            f"/api/v1/cybersecurity/practice/{session_id}/complete",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert forbidden_complete.status_code == 403

        # User B's own history must not include User A's session.
        history_b = client.get(
            "/api/v1/cybersecurity/practice/history", headers={"Authorization": f"Bearer {token_b}"}
        )
        assert all(s["session_id"] != session_id for s in history_b.json()["data"]["sessions"])
