"""
AI chat endpoint tests.

No real Gemini calls are made. `service` is swapped out for a fake via
`app.dependency_overrides[get_ai_service]`, so these tests exercise the
route/service wiring and error handling in isolation from the network.
"""

from __future__ import annotations

import pytest

from app.core.dependencies import get_ai_service
from app.main import app
from app.services.ai.ai_service import (
    AIConfigurationError,
    AIProviderError,
    AIResponse,
    AITimeoutError,
    ConversationTurn,
)

VALID_PASSWORD = "correct-horse-battery-staple"


def _register_and_login(client, email="ai-user@example.com") -> str:
    client.post(
        "/api/v1/auth/register",
        json={"name": "AI User", "email": email, "password": VALID_PASSWORD},
    )
    login = client.post(
        "/api/v1/auth/login", json={"email": email, "password": VALID_PASSWORD}
    )
    return login.json()["data"]["access_token"]


class _FakeAIService:
    """Stands in for AIService in tests — never touches the network."""

    def __init__(self, *, response: str | None = None, error: Exception | None = None):
        self.response = response
        self.error = error
        self.last_call: dict | None = None

    async def generate_response(
        self, *, user_message: str, history: list[ConversationTurn] | None = None, **_: object
    ) -> AIResponse:
        self.last_call = {"user_message": user_message, "history": history}
        if self.error is not None:
            raise self.error
        return AIResponse(text=self.response or "Mocked AI response.", model="gemini-3.1-flash-lite")


@pytest.fixture()
def override_ai_service():
    """Install a fake AI service and clean it up after the test."""

    def _install(fake: _FakeAIService):
        app.dependency_overrides[get_ai_service] = lambda: fake
        return fake

    yield _install
    app.dependency_overrides.pop(get_ai_service, None)


class TestAuthenticationRequired:
    def test_chat_without_token_is_denied(self, client):
        response = client.post("/api/v1/ai/chat", json={"message": "Hello"})
        assert response.status_code == 401
        assert response.json()["error_code"] == "UNAUTHORIZED"

    def test_chat_with_invalid_token_is_denied(self, client):
        response = client.post(
            "/api/v1/ai/chat",
            json={"message": "Hello"},
            headers={"Authorization": "Bearer not-a-real-token"},
        )
        assert response.status_code == 401


class TestValidation:
    def test_empty_message_is_rejected(self, client, override_ai_service):
        override_ai_service(_FakeAIService(response="unused"))
        token = _register_and_login(client)

        response = client.post(
            "/api/v1/ai/chat",
            json={"message": ""},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422
        assert response.json()["error_code"] == "VALIDATION_ERROR"

    def test_whitespace_only_message_is_rejected(self, client, override_ai_service):
        override_ai_service(_FakeAIService(response="unused"))
        token = _register_and_login(client)

        response = client.post(
            "/api/v1/ai/chat",
            json={"message": "   "},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    def test_oversized_message_is_rejected(self, client, override_ai_service):
        override_ai_service(_FakeAIService(response="unused"))
        token = _register_and_login(client)

        response = client.post(
            "/api/v1/ai/chat",
            json={"message": "x" * 10_001},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    def test_invalid_history_role_is_rejected(self, client, override_ai_service):
        override_ai_service(_FakeAIService(response="unused"))
        token = _register_and_login(client)

        response = client.post(
            "/api/v1/ai/chat",
            json={
                "message": "Explain it again",
                "conversation_history": [{"role": "system", "content": "not allowed"}],
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    def test_oversized_history_is_rejected(self, client, override_ai_service):
        override_ai_service(_FakeAIService(response="unused"))
        token = _register_and_login(client)

        history = [{"role": "user", "content": "hi"} for _ in range(41)]
        response = client.post(
            "/api/v1/ai/chat",
            json={"message": "hello", "conversation_history": history},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422


class TestChatSuccess:
    def test_valid_request_returns_mocked_response(self, client, override_ai_service):
        fake = override_ai_service(_FakeAIService(response="SQL injection is..."))
        token = _register_and_login(client)

        response = client.post(
            "/api/v1/ai/chat",
            json={
                "message": "What is SQL injection?",
                "conversation_history": [
                    {"role": "user", "content": "Hi"},
                    {"role": "assistant", "content": "Hello! How can I help?"},
                ],
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["response"] == "SQL injection is..."

        # The route actually called the (fake) service with the parsed input.
        assert fake.last_call is not None
        assert fake.last_call["user_message"] == "What is SQL injection?"
        assert len(fake.last_call["history"]) == 2


class TestMissingApiKeyRealPath:
    """
    Exercises the real AIService/GeminiClient code (not a fake), with no
    Gemini API key configured — the state this sandbox is actually in. No
    network call happens: GeminiClient rejects before ever contacting Gemini.
    """

    def test_generate_response_raises_configuration_error_without_key(self):
        import asyncio

        from app.core.config import settings
        from app.services.ai.ai_service import AIConfigurationError, ai_service

        assert settings.gemini_api_key == ""  # sandbox has no real key configured

        with pytest.raises(AIConfigurationError):
            asyncio.run(ai_service.generate_response(user_message="Hello"))


class TestChatFailureHandling:

    def test_missing_configuration_returns_safe_error(self, client, override_ai_service):
        override_ai_service(_FakeAIService(error=AIConfigurationError("no api key")))
        token = _register_and_login(client, email="config-fail@example.com")

        response = client.post(
            "/api/v1/ai/chat",
            json={"message": "Hello"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 503
        body = response.json()
        assert body["error_code"] == "AI_SERVICE_UNAVAILABLE"
        # The safe error must never mention the API key.
        assert "GEMINI_API_KEY" not in body["message"]
        assert "api key" not in body["message"].lower()

    def test_provider_failure_returns_safe_error(self, client, override_ai_service):
        override_ai_service(_FakeAIService(error=AIProviderError("upstream exploded")))
        token = _register_and_login(client, email="provider-fail@example.com")

        response = client.post(
            "/api/v1/ai/chat",
            json={"message": "Hello"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 503
        body = response.json()
        assert body["error_code"] == "AI_SERVICE_UNAVAILABLE"
        assert "upstream exploded" not in body["message"]

    def test_timeout_returns_safe_error(self, client, override_ai_service):
        override_ai_service(_FakeAIService(error=AITimeoutError("timed out")))
        token = _register_and_login(client, email="timeout-fail@example.com")

        response = client.post(
            "/api/v1/ai/chat",
            json={"message": "Hello"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 504
        assert response.json()["error_code"] == "AI_TIMEOUT"

    def test_unexpected_error_returns_generic_safe_error(self, client, override_ai_service):
        override_ai_service(_FakeAIService(error=RuntimeError("boom, something broke")))
        token = _register_and_login(client, email="unexpected-fail@example.com")

        response = client.post(
            "/api/v1/ai/chat",
            json={"message": "Hello"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 500
        body = response.json()
        assert body["error_code"] == "INTERNAL_SERVER_ERROR"
        assert "boom" not in body["message"]
