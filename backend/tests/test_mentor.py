"""
Mentor chat endpoint tests.

No real Gemini calls are made. The mentor service is swapped out for a fake
via `app.dependency_overrides[get_mentor_service]`.
"""

from __future__ import annotations

import pytest

from app.core.dependencies import get_mentor_service
from app.main import app
from app.services.ai.ai_service import (
    AIConfigurationError,
    AIProviderError,
    AITimeoutError,
)
from app.services.mentor.mentor_service import MentorChatResult

VALID_PASSWORD = "correct-horse-battery-staple"


def _register_and_login(client, email="mentor-user@example.com") -> str:
    client.post(
        "/api/v1/auth/register",
        json={"name": "Mentor User", "email": email, "password": VALID_PASSWORD},
    )
    login = client.post(
        "/api/v1/auth/login", json={"email": email, "password": VALID_PASSWORD}
    )
    return login.json()["data"]["access_token"]


class _FakeMentorService:
    """Stands in for MentorService in tests — never touches the network."""

    def __init__(self, *, response: str | None = None, error: Exception | None = None):
        self.response = response
        self.error = error
        self.last_call: dict | None = None

    async def chat(self, *, message, mode, level, history=None):
        self.last_call = {
            "message": message,
            "mode": mode,
            "level": level,
            "history": history,
        }
        if self.error is not None:
            raise self.error
        return MentorChatResult(response=self.response or "Mocked mentor reply.", mode=mode, level=level)


@pytest.fixture()
def override_mentor_service():
    def _install(fake: _FakeMentorService):
        app.dependency_overrides[get_mentor_service] = lambda: fake
        return fake

    yield _install
    app.dependency_overrides.pop(get_mentor_service, None)


class TestAuthenticationRequired:
    def test_chat_without_token_is_denied(self, client):
        response = client.post("/api/v1/mentor/chat", json={"message": "What is XSS?"})
        assert response.status_code == 401
        assert response.json()["error_code"] == "UNAUTHORIZED"


class TestValidation:
    def test_empty_message_is_rejected(self, client, override_mentor_service):
        override_mentor_service(_FakeMentorService(response="unused"))
        token = _register_and_login(client)

        response = client.post(
            "/api/v1/mentor/chat",
            json={"message": ""},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422
        assert response.json()["error_code"] == "VALIDATION_ERROR"

    def test_oversized_message_is_rejected(self, client, override_mentor_service):
        override_mentor_service(_FakeMentorService(response="unused"))
        token = _register_and_login(client)

        response = client.post(
            "/api/v1/mentor/chat",
            json={"message": "x" * 10_001},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    def test_invalid_mode_is_rejected(self, client, override_mentor_service):
        override_mentor_service(_FakeMentorService(response="unused"))
        token = _register_and_login(client)

        response = client.post(
            "/api/v1/mentor/chat",
            json={"message": "Teach me networking", "mode": "not-a-real-mode"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422
        assert response.json()["error_code"] == "VALIDATION_ERROR"

    def test_invalid_level_is_rejected(self, client, override_mentor_service):
        override_mentor_service(_FakeMentorService(response="unused"))
        token = _register_and_login(client)

        response = client.post(
            "/api/v1/mentor/chat",
            json={"message": "Teach me networking", "level": "expert"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    def test_invalid_history_role_is_rejected(self, client, override_mentor_service):
        override_mentor_service(_FakeMentorService(response="unused"))
        token = _register_and_login(client)

        response = client.post(
            "/api/v1/mentor/chat",
            json={
                "message": "Explain it again",
                "conversation_history": [{"role": "system", "content": "not allowed"}],
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    def test_excessively_large_history_is_rejected(self, client, override_mentor_service):
        override_mentor_service(_FakeMentorService(response="unused"))
        token = _register_and_login(client)

        history = [{"role": "user", "content": "hi"} for _ in range(101)]
        response = client.post(
            "/api/v1/mentor/chat",
            json={"message": "hello", "conversation_history": history},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422


class TestModesAndLevels:
    @pytest.mark.parametrize("mode", ["learn", "explain", "practice", "troubleshoot"])
    def test_each_mode_is_accepted(self, client, override_mentor_service, mode):
        fake = override_mentor_service(_FakeMentorService(response="ok"))
        token = _register_and_login(client, email=f"mode-{mode}@example.com")

        response = client.post(
            "/api/v1/mentor/chat",
            json={"message": "What is XSS?", "mode": mode},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["mode"] == mode
        assert fake.last_call["mode"] == mode

    @pytest.mark.parametrize("level", ["beginner", "intermediate", "advanced"])
    def test_each_level_is_accepted(self, client, override_mentor_service, level):
        fake = override_mentor_service(_FakeMentorService(response="ok"))
        token = _register_and_login(client, email=f"level-{level}@example.com")

        response = client.post(
            "/api/v1/mentor/chat",
            json={"message": "What is XSS?", "level": level},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["level"] == level
        assert fake.last_call["level"] == level

    def test_defaults_are_learn_and_intermediate(self, client, override_mentor_service):
        fake = override_mentor_service(_FakeMentorService(response="ok"))
        token = _register_and_login(client, email="defaults@example.com")

        response = client.post(
            "/api/v1/mentor/chat",
            json={"message": "What is XSS?"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert fake.last_call["mode"] == "learn"
        assert fake.last_call["level"] == "intermediate"


class TestConversationContext:
    def test_history_is_passed_to_mentor_service(self, client, override_mentor_service):
        fake = override_mentor_service(_FakeMentorService(response="ok"))
        token = _register_and_login(client, email="history@example.com")

        response = client.post(
            "/api/v1/mentor/chat",
            json={
                "message": "Why is SYN important?",
                "conversation_history": [
                    {"role": "user", "content": "Explain TCP three way handshake"},
                    {"role": "assistant", "content": "The TCP three way handshake..."},
                ],
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert len(fake.last_call["history"]) == 2
        assert fake.last_call["history"][0].role == "user"
        assert fake.last_call["history"][0].content == "Explain TCP three way handshake"
        assert fake.last_call["history"][1].role == "assistant"


class TestContextWindowLimit:
    """
    The *route* forwards everything schema-valid to MentorService — bounding
    to the last N turns is MentorService's job (see test_mentor_service.py
    for that behavior in isolation). This confirms the route doesn't
    pre-truncate before the service ever sees the full history.
    """

    def test_route_forwards_full_valid_history_to_service(self, client, override_mentor_service):
        fake = override_mentor_service(_FakeMentorService(response="ok"))
        token = _register_and_login(client, email="context-window@example.com")

        history = [{"role": "user", "content": f"message {i}"} for i in range(30)]
        response = client.post(
            "/api/v1/mentor/chat",
            json={"message": "latest question", "conversation_history": history},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert len(fake.last_call["history"]) == 30


class TestChatFailureHandling:
    def test_configuration_error_returns_safe_error(self, client, override_mentor_service):
        override_mentor_service(_FakeMentorService(error=AIConfigurationError("no api key")))
        token = _register_and_login(client, email="mentor-config-fail@example.com")

        response = client.post(
            "/api/v1/mentor/chat",
            json={"message": "Hello"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 503
        body = response.json()
        assert body["error_code"] == "AI_SERVICE_UNAVAILABLE"
        assert "api key" not in body["message"].lower()

    def test_provider_failure_returns_safe_error(self, client, override_mentor_service):
        override_mentor_service(_FakeMentorService(error=AIProviderError("upstream exploded")))
        token = _register_and_login(client, email="mentor-provider-fail@example.com")

        response = client.post(
            "/api/v1/mentor/chat",
            json={"message": "Hello"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 503
        assert "upstream exploded" not in response.json()["message"]

    def test_timeout_returns_safe_error(self, client, override_mentor_service):
        override_mentor_service(_FakeMentorService(error=AITimeoutError("timed out")))
        token = _register_and_login(client, email="mentor-timeout-fail@example.com")

        response = client.post(
            "/api/v1/mentor/chat",
            json={"message": "Hello"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 504
        assert response.json()["error_code"] == "AI_TIMEOUT"
