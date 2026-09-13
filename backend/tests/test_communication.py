"""
Communication coach tests.

Uses a scripted fake AI service (no network calls) wired into real
CommunicationService/EvaluationService instances, so session/ownership/
persistence/evaluation logic all runs for real.
"""

from __future__ import annotations

import json

import pytest

from app.core.dependencies import get_communication_service, get_evaluation_service
from app.main import app
from app.services.ai.ai_service import AIResponse
from app.services.communication.communication_service import CommunicationService
from app.services.communication.evaluation_service import EvaluationService

VALID_PASSWORD = "correct-horse-battery-staple"


def _register_and_login(client, email="comm-user@example.com") -> str:
    client.post(
        "/api/v1/auth/register",
        json={"name": "Comm User", "email": email, "password": VALID_PASSWORD},
    )
    login = client.post(
        "/api/v1/auth/login", json={"email": email, "password": VALID_PASSWORD}
    )
    return login.json()["data"]["access_token"]


class _ScriptedAIService:
    """Returns deterministic, distinguishable text/JSON — no network calls."""

    async def generate_response(self, *, user_message, system_prompt=None, history=None, **_):
        prompt = system_prompt or ""
        if "communication coach evaluating" in prompt:
            payload = {
                "overall_score": 78,
                "clarity_score": 82,
                "grammar_score": 74,
                "vocabulary_score": 76,
                "professionalism_score": 80,
                "confidence_score": 72,
                "relevance_score": 85,
                "conversation_flow_score": 76,
                "strengths": ["You asked relevant questions."],
                "weaknesses": ["Some sentences were grammatically incomplete."],
                "improvements": ["Use shorter sentences."],
                "better_responses": [
                    {
                        "original": "Can you tell me how you got internship?",
                        "improved": "Could you tell me how you got your internship?",
                        "why": "Clearer grammar and more specific.",
                    }
                ],
                "summary": "Clear communication with room to improve grammar.",
            }
            return AIResponse(text=json.dumps(payload), model="fake-model")

        return AIResponse(text=f"ROLEPLAY_REPLY to: {user_message[:50]}", model="fake-model")


@pytest.fixture()
def with_comm_services():
    fake_ai = _ScriptedAIService()
    comm_service = CommunicationService(ai_service_=fake_ai)
    eval_service = EvaluationService(ai_service_=fake_ai)
    app.dependency_overrides[get_communication_service] = lambda: comm_service
    app.dependency_overrides[get_evaluation_service] = lambda: eval_service
    yield comm_service, eval_service
    app.dependency_overrides.pop(get_communication_service, None)
    app.dependency_overrides.pop(get_evaluation_service, None)


class TestScenarios:
    def test_requires_authentication(self, client, with_comm_services):
        response = client.get("/api/v1/communication/scenarios")
        assert response.status_code == 401

    def test_lists_starter_scenarios(self, client, with_comm_services):
        token = _register_and_login(client)
        response = client.get(
            "/api/v1/communication/scenarios", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        scenarios = response.json()["data"]["scenarios"]
        assert len(scenarios) >= 16

    def test_filter_by_category(self, client, with_comm_services):
        token = _register_and_login(client, email="filter-category@example.com")
        response = client.get(
            "/api/v1/communication/scenarios?category=seniors",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        scenarios = response.json()["data"]["scenarios"]
        assert len(scenarios) > 0
        assert all(s["category"] == "seniors" for s in scenarios)

    def test_filter_by_mode_and_difficulty(self, client, with_comm_services):
        token = _register_and_login(client, email="filter-mode@example.com")
        response = client.get(
            "/api/v1/communication/scenarios?mode=professional&difficulty=beginner",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        scenarios = response.json()["data"]["scenarios"]
        assert all(s["mode"] == "professional" and s["difficulty"] == "beginner" for s in scenarios)

    def test_get_scenario_by_slug(self, client, with_comm_services):
        token = _register_and_login(client, email="scenario-detail@example.com")
        response = client.get(
            "/api/v1/communication/scenarios/ask-senior-cybersecurity-career",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        scenario = response.json()["data"]["scenario"]
        assert scenario["slug"] == "ask-senior-cybersecurity-career"
        assert "opening_message" in scenario
        assert "ai_role" in scenario

    def test_unknown_scenario_returns_404(self, client, with_comm_services):
        token = _register_and_login(client, email="unknown-scenario@example.com")
        response = client.get(
            "/api/v1/communication/scenarios/does-not-exist",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404
        assert response.json()["error_code"] == "SCENARIO_NOT_FOUND"


def _get_scenario_id(client, token, slug="ask-senior-cybersecurity-career") -> str:
    response = client.get(
        f"/api/v1/communication/scenarios/{slug}", headers={"Authorization": f"Bearer {token}"}
    )
    return response.json()["data"]["scenario"]["scenario_id"]


class TestStartSession:
    def test_requires_authentication(self, client, with_comm_services):
        response = client.post("/api/v1/communication/sessions", json={"scenario_id": "x"})
        assert response.status_code == 401

    def test_start_session_returns_opening_message(self, client, with_comm_services):
        token = _register_and_login(client, email="start-session@example.com")
        scenario_id = _get_scenario_id(client, token)

        response = client.post(
            "/api/v1/communication/sessions",
            json={"scenario_id": scenario_id},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["status"] == "in_progress"
        assert "session_id" in data
        assert data["scenario"]["scenario_id"] == scenario_id

    def test_invalid_scenario_returns_404(self, client, with_comm_services):
        token = _register_and_login(client, email="invalid-scenario@example.com")
        response = client.post(
            "/api/v1/communication/sessions",
            json={"scenario_id": "000000000000000000000000"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404
        assert response.json()["error_code"] == "SCENARIO_NOT_FOUND"


class TestMessaging:
    def _start_session(self, client, token) -> str:
        scenario_id = _get_scenario_id(client, token)
        response = client.post(
            "/api/v1/communication/sessions",
            json={"scenario_id": scenario_id},
            headers={"Authorization": f"Bearer {token}"},
        )
        return response.json()["data"]["session_id"]

    def test_send_message_requires_authentication(self, client, with_comm_services):
        response = client.post(
            "/api/v1/communication/sessions/some-id/message", json={"message": "hi"}
        )
        assert response.status_code == 401

    def test_empty_message_is_rejected(self, client, with_comm_services):
        token = _register_and_login(client, email="empty-message@example.com")
        session_id = self._start_session(client, token)

        response = client.post(
            f"/api/v1/communication/sessions/{session_id}/message",
            json={"message": "   "},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    def test_send_message_stores_and_returns_reply(self, client, with_comm_services):
        token = _register_and_login(client, email="send-message@example.com")
        session_id = self._start_session(client, token)

        response = client.post(
            f"/api/v1/communication/sessions/{session_id}/message",
            json={"message": "Hi, can you tell me how you got your internship?"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert "ROLEPLAY_REPLY" in response.json()["data"]["reply"]

        detail = client.get(
            f"/api/v1/communication/sessions/{session_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        messages = detail.json()["data"]["messages"]
        # Opening message + user message + assistant reply.
        assert len(messages) == 3
        assert messages[0]["role"] == "assistant"
        assert messages[1]["role"] == "user"
        assert messages[2]["role"] == "assistant"

    def test_message_to_completed_session_is_rejected(self, client, with_comm_services):
        token = _register_and_login(client, email="completed-session-message@example.com")
        session_id = self._start_session(client, token)

        client.post(
            f"/api/v1/communication/sessions/{session_id}/complete",
            headers={"Authorization": f"Bearer {token}"},
        )

        response = client.post(
            f"/api/v1/communication/sessions/{session_id}/message",
            json={"message": "Are you still there?"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 409
        assert response.json()["error_code"] == "SESSION_COMPLETED"


class TestOwnership:
    def _start_session(self, client, token) -> str:
        scenario_id = _get_scenario_id(client, token)
        response = client.post(
            "/api/v1/communication/sessions",
            json={"scenario_id": scenario_id},
            headers={"Authorization": f"Bearer {token}"},
        )
        return response.json()["data"]["session_id"]

    def test_owner_can_access_own_session(self, client, with_comm_services):
        token = _register_and_login(client, email="owner-a@example.com")
        session_id = self._start_session(client, token)

        response = client.get(
            f"/api/v1/communication/sessions/{session_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

    def test_other_user_cannot_access_session(self, client, with_comm_services):
        token_a = _register_and_login(client, email="comm-owner-a@example.com")
        token_b = _register_and_login(client, email="comm-owner-b@example.com")
        session_id = self._start_session(client, token_a)

        response = client.get(
            f"/api/v1/communication/sessions/{session_id}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert response.status_code == 403
        assert response.json()["error_code"] == "SESSION_FORBIDDEN"

    def test_other_user_cannot_message_session(self, client, with_comm_services):
        token_a = _register_and_login(client, email="comm-msg-owner-a@example.com")
        token_b = _register_and_login(client, email="comm-msg-owner-b@example.com")
        session_id = self._start_session(client, token_a)

        response = client.post(
            f"/api/v1/communication/sessions/{session_id}/message",
            json={"message": "hi"},
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert response.status_code == 403

    def test_other_user_cannot_complete_session(self, client, with_comm_services):
        token_a = _register_and_login(client, email="comm-complete-owner-a@example.com")
        token_b = _register_and_login(client, email="comm-complete-owner-b@example.com")
        session_id = self._start_session(client, token_a)

        response = client.post(
            f"/api/v1/communication/sessions/{session_id}/complete",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert response.status_code == 403

    def test_history_lists_only_own_sessions(self, client, with_comm_services):
        token_a = _register_and_login(client, email="comm-history-a@example.com")
        token_b = _register_and_login(client, email="comm-history-b@example.com")
        session_id_a = self._start_session(client, token_a)

        history_b = client.get(
            "/api/v1/communication/sessions", headers={"Authorization": f"Bearer {token_b}"}
        )
        assert all(s["session_id"] != session_id_a for s in history_b.json()["data"]["sessions"])


class TestEvaluation:
    def _start_session(self, client, token) -> str:
        scenario_id = _get_scenario_id(client, token)
        response = client.post(
            "/api/v1/communication/sessions",
            json={"scenario_id": scenario_id},
            headers={"Authorization": f"Bearer {token}"},
        )
        return response.json()["data"]["session_id"]

    def test_complete_requires_authentication(self, client, with_comm_services):
        response = client.post("/api/v1/communication/sessions/some-id/complete")
        assert response.status_code == 401

    def test_complete_returns_valid_evaluation(self, client, with_comm_services):
        token = _register_and_login(client, email="evaluate@example.com")
        session_id = self._start_session(client, token)
        client.post(
            f"/api/v1/communication/sessions/{session_id}/message",
            json={"message": "Hi! Can you tell me how you got your internship?"},
            headers={"Authorization": f"Bearer {token}"},
        )

        response = client.post(
            f"/api/v1/communication/sessions/{session_id}/complete",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        evaluation = response.json()["data"]["evaluation"]
        assert 0 <= evaluation["overall_score"] <= 100
        assert "summary" in evaluation
        assert len(evaluation["better_responses"]) >= 1

    def test_completing_twice_is_idempotent(self, client, with_comm_services):
        token = _register_and_login(client, email="evaluate-twice@example.com")
        session_id = self._start_session(client, token)

        first = client.post(
            f"/api/v1/communication/sessions/{session_id}/complete",
            headers={"Authorization": f"Bearer {token}"},
        )
        second = client.post(
            f"/api/v1/communication/sessions/{session_id}/complete",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["data"]["evaluation"] == second.json()["data"]["evaluation"]

    def test_malformed_ai_evaluation_is_handled_safely(self, client):
        class _BrokenAIService:
            async def generate_response(self, *, user_message, system_prompt=None, history=None, **_):
                if system_prompt and "communication coach evaluating" in system_prompt:
                    return AIResponse(text="this is not valid json", model="fake-model")
                return AIResponse(text="ROLEPLAY_REPLY", model="fake-model")

        broken_ai = _BrokenAIService()
        comm_service = CommunicationService(ai_service_=broken_ai)
        eval_service = EvaluationService(ai_service_=broken_ai)
        app.dependency_overrides[get_communication_service] = lambda: comm_service
        app.dependency_overrides[get_evaluation_service] = lambda: eval_service
        try:
            token = _register_and_login(client, email="broken-eval@example.com")
            session_id = self._start_session(client, token)

            response = client.post(
                f"/api/v1/communication/sessions/{session_id}/complete",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 503
            body = response.json()
            assert body["error_code"] == "AI_SERVICE_UNAVAILABLE"
            assert "not valid json" not in body["message"]
        finally:
            app.dependency_overrides.pop(get_communication_service, None)
            app.dependency_overrides.pop(get_evaluation_service, None)


class TestHistoryPagination:
    def _start_session(self, client, token) -> str:
        scenario_id = _get_scenario_id(client, token)
        response = client.post(
            "/api/v1/communication/sessions",
            json={"scenario_id": scenario_id},
            headers={"Authorization": f"Bearer {token}"},
        )
        return response.json()["data"]["session_id"]

    def test_pagination_shape(self, client, with_comm_services):
        token = _register_and_login(client, email="comm-pagination@example.com")
        for _ in range(3):
            self._start_session(client, token)

        response = client.get(
            "/api/v1/communication/sessions?page=1&limit=2",
            headers={"Authorization": f"Bearer {token}"},
        )
        data = response.json()["data"]
        assert data["page"] == 1
        assert data["limit"] == 2
        assert len(data["sessions"]) == 2
        assert data["total"] == 3
