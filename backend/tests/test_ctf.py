"""
CTF & Practical Lab Mentor tests.

Uses a scripted fake AI service (no network calls) wired into a real
CtfService, so session/ownership/hint-progression/persistence logic all
runs for real.
"""

from __future__ import annotations

import pytest

from app.core.dependencies import get_ctf_service
from app.main import app
from app.services.ai.ai_service import AIResponse
from app.services.cybersecurity.ctf_service import CtfService

VALID_PASSWORD = "correct-horse-battery-staple"


def _register_and_login(client, email="ctf-user@example.com") -> str:
    client.post(
        "/api/v1/auth/register",
        json={"name": "CTF User", "email": email, "password": VALID_PASSWORD},
    )
    login = client.post(
        "/api/v1/auth/login", json={"email": email, "password": VALID_PASSWORD}
    )
    return login.json()["data"]["access_token"]


VALID_SESSION_PAYLOAD = {
    "platform": "Hack The Box",
    "category": "web_security",
    "difficulty": "easy",
    "title": "Example Challenge",
    "description": "I found port 80 open and the website has a login page.",
    "user_notes": "Checked the page source, found a comment mentioning /admin.",
}


class _ScriptedAIService:
    """Returns deterministic, distinguishable text per prompt — no network calls."""

    async def generate_response(self, *, user_message, system_prompt=None, history=None, **_):
        prompt = system_prompt or ""
        if "Give Hint 1" in prompt:
            text = "HINT1: think about how input is handled."
        elif "Give Hint 2" in prompt:
            text = "HINT2: inspect the login request in dev tools."
        elif "Give Hint 3" in prompt:
            text = "HINT3: this looks like SQL injection."
        elif "full solution" in prompt:
            text = "SOLUTION: use ' OR '1'='1 to bypass the login."
        else:
            text = f"CHAT_RESPONSE to: {user_message[:50]}"
        return AIResponse(text=text, model="fake-model")


@pytest.fixture()
def with_ctf_service():
    service = CtfService(ai_service_=_ScriptedAIService())
    app.dependency_overrides[get_ctf_service] = lambda: service
    yield service
    app.dependency_overrides.pop(get_ctf_service, None)


class TestSessionCreation:
    def test_requires_authentication(self, client, with_ctf_service):
        response = client.post("/api/v1/ctf/sessions", json=VALID_SESSION_PAYLOAD)
        assert response.status_code == 401

    def test_creates_session(self, client, with_ctf_service):
        token = _register_and_login(client)
        response = client.post(
            "/api/v1/ctf/sessions",
            json=VALID_SESSION_PAYLOAD,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["status"] == "in_progress"
        assert "session_id" in data

    def test_invalid_category_is_rejected(self, client, with_ctf_service):
        token = _register_and_login(client, email="invalid-category@example.com")
        payload = {**VALID_SESSION_PAYLOAD, "category": "not_a_real_category"}
        response = client.post(
            "/api/v1/ctf/sessions", json=payload, headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 422

    def test_invalid_difficulty_is_rejected(self, client, with_ctf_service):
        token = _register_and_login(client, email="invalid-difficulty@example.com")
        payload = {**VALID_SESSION_PAYLOAD, "difficulty": "impossible"}
        response = client.post(
            "/api/v1/ctf/sessions", json=payload, headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 422

    def test_blank_title_is_rejected(self, client, with_ctf_service):
        token = _register_and_login(client, email="blank-title@example.com")
        payload = {**VALID_SESSION_PAYLOAD, "title": "   "}
        response = client.post(
            "/api/v1/ctf/sessions", json=payload, headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 422


class TestSessionOwnership:
    def _create_session(self, client, token) -> str:
        response = client.post(
            "/api/v1/ctf/sessions",
            json=VALID_SESSION_PAYLOAD,
            headers={"Authorization": f"Bearer {token}"},
        )
        return response.json()["data"]["session_id"]

    def test_owner_can_access_own_session(self, client, with_ctf_service):
        token = _register_and_login(client, email="owner-a@example.com")
        session_id = self._create_session(client, token)

        response = client.get(
            f"/api/v1/ctf/sessions/{session_id}", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["data"]["session_id"] == session_id

    def test_other_user_cannot_access_session(self, client, with_ctf_service):
        token_a = _register_and_login(client, email="ctf-owner-a@example.com")
        token_b = _register_and_login(client, email="ctf-owner-b@example.com")
        session_id = self._create_session(client, token_a)

        response = client.get(
            f"/api/v1/ctf/sessions/{session_id}", headers={"Authorization": f"Bearer {token_b}"}
        )
        assert response.status_code == 403
        assert response.json()["error_code"] == "SESSION_FORBIDDEN"

    def test_other_user_cannot_chat_in_session(self, client, with_ctf_service):
        token_a = _register_and_login(client, email="ctf-chat-owner-a@example.com")
        token_b = _register_and_login(client, email="ctf-chat-owner-b@example.com")
        session_id = self._create_session(client, token_a)

        response = client.post(
            f"/api/v1/ctf/sessions/{session_id}/chat",
            json={"message": "hi"},
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert response.status_code == 403

    def test_unknown_session_returns_404(self, client, with_ctf_service):
        token = _register_and_login(client, email="unknown-session@example.com")
        response = client.get(
            "/api/v1/ctf/sessions/000000000000000000000000",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404
        assert response.json()["error_code"] == "SESSION_NOT_FOUND"

    def test_history_lists_only_own_sessions(self, client, with_ctf_service):
        token_a = _register_and_login(client, email="ctf-history-a@example.com")
        token_b = _register_and_login(client, email="ctf-history-b@example.com")
        session_id_a = self._create_session(client, token_a)

        history_b = client.get(
            "/api/v1/ctf/sessions", headers={"Authorization": f"Bearer {token_b}"}
        )
        assert all(s["session_id"] != session_id_a for s in history_b.json()["data"]["sessions"])


class TestChat:
    def test_chat_requires_authentication(self, client, with_ctf_service):
        response = client.post("/api/v1/ctf/sessions/some-id/chat", json={"message": "hi"})
        assert response.status_code == 401

    def test_blank_message_is_rejected(self, client, with_ctf_service):
        token = _register_and_login(client, email="ctf-blank-msg@example.com")
        create = client.post(
            "/api/v1/ctf/sessions",
            json=VALID_SESSION_PAYLOAD,
            headers={"Authorization": f"Bearer {token}"},
        )
        session_id = create.json()["data"]["session_id"]

        response = client.post(
            f"/api/v1/ctf/sessions/{session_id}/chat",
            json={"message": "   "},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    def test_chat_uses_challenge_context_and_persists_messages(self, client, with_ctf_service):
        token = _register_and_login(client, email="ctf-chat-context@example.com")
        create = client.post(
            "/api/v1/ctf/sessions",
            json=VALID_SESSION_PAYLOAD,
            headers={"Authorization": f"Bearer {token}"},
        )
        session_id = create.json()["data"]["session_id"]

        response = client.post(
            f"/api/v1/ctf/sessions/{session_id}/chat",
            json={"message": "What should I investigate next?"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert "CHAT_RESPONSE" in response.json()["data"]["response"]

        detail = client.get(
            f"/api/v1/ctf/sessions/{session_id}", headers={"Authorization": f"Bearer {token}"}
        )
        messages = detail.json()["data"]["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"


class TestHints:
    def _create_session(self, client, token) -> str:
        response = client.post(
            "/api/v1/ctf/sessions",
            json=VALID_SESSION_PAYLOAD,
            headers={"Authorization": f"Bearer {token}"},
        )
        return response.json()["data"]["session_id"]

    def test_hint_1_available_immediately(self, client, with_ctf_service):
        token = _register_and_login(client, email="hint1@example.com")
        session_id = self._create_session(client, token)

        response = client.get(
            f"/api/v1/ctf/sessions/{session_id}/hint?level=hint_1",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["level"] == "hint_1"
        assert "HINT1" in data["content"]
        assert data["hints_used"] == 1

    def test_hint_2_locked_before_hint_1(self, client, with_ctf_service):
        token = _register_and_login(client, email="hint2-locked@example.com")
        session_id = self._create_session(client, token)

        response = client.get(
            f"/api/v1/ctf/sessions/{session_id}/hint?level=hint_2",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 409
        assert response.json()["error_code"] == "HINT_LOCKED"

    def test_hint_progression_1_2_3(self, client, with_ctf_service):
        token = _register_and_login(client, email="hint-progression@example.com")
        session_id = self._create_session(client, token)
        headers = {"Authorization": f"Bearer {token}"}

        h1 = client.get(f"/api/v1/ctf/sessions/{session_id}/hint?level=hint_1", headers=headers)
        assert h1.status_code == 200
        h2 = client.get(f"/api/v1/ctf/sessions/{session_id}/hint?level=hint_2", headers=headers)
        assert h2.status_code == 200
        assert "HINT2" in h2.json()["data"]["content"]
        h3 = client.get(f"/api/v1/ctf/sessions/{session_id}/hint?level=hint_3", headers=headers)
        assert h3.status_code == 200
        assert "HINT3" in h3.json()["data"]["content"]
        assert h3.json()["data"]["hints_used"] == 3

    def test_solution_available_directly_without_prior_hints(self, client, with_ctf_service):
        token = _register_and_login(client, email="solution-direct@example.com")
        session_id = self._create_session(client, token)

        response = client.get(
            f"/api/v1/ctf/sessions/{session_id}/hint?level=solution",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert "SOLUTION" in response.json()["data"]["content"]

    def test_force_skips_progression_lock(self, client, with_ctf_service):
        token = _register_and_login(client, email="force-skip@example.com")
        session_id = self._create_session(client, token)

        response = client.get(
            f"/api/v1/ctf/sessions/{session_id}/hint?level=hint_3&force=true",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert "HINT3" in response.json()["data"]["content"]

    def test_duplicate_hint_request_returns_persisted_content_not_regenerated(
        self, client, with_ctf_service
    ):
        token = _register_and_login(client, email="duplicate-hint@example.com")
        session_id = self._create_session(client, token)
        headers = {"Authorization": f"Bearer {token}"}

        first = client.get(f"/api/v1/ctf/sessions/{session_id}/hint?level=hint_1", headers=headers)
        second = client.get(f"/api/v1/ctf/sessions/{session_id}/hint?level=hint_1", headers=headers)

        assert first.json()["data"]["content"] == second.json()["data"]["content"]
        # hints_used must not increment on the duplicate/persisted fetch.
        assert second.json()["data"]["hints_used"] == 1

    def test_invalid_hint_level_is_rejected(self, client, with_ctf_service):
        token = _register_and_login(client, email="invalid-hint-level@example.com")
        session_id = self._create_session(client, token)

        response = client.get(
            f"/api/v1/ctf/sessions/{session_id}/hint?level=not_a_real_level",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    def test_hints_persist_across_requests(self, client, with_ctf_service):
        token = _register_and_login(client, email="hint-persist@example.com")
        session_id = self._create_session(client, token)
        headers = {"Authorization": f"Bearer {token}"}

        client.get(f"/api/v1/ctf/sessions/{session_id}/hint?level=hint_1", headers=headers)

        detail = client.get(f"/api/v1/ctf/sessions/{session_id}", headers=headers)
        hints = detail.json()["data"]["hints"]
        assert len(hints) == 1
        assert hints[0]["level"] == "hint_1"


class TestCompletion:
    def _create_session(self, client, token) -> str:
        response = client.post(
            "/api/v1/ctf/sessions",
            json=VALID_SESSION_PAYLOAD,
            headers={"Authorization": f"Bearer {token}"},
        )
        return response.json()["data"]["session_id"]

    def test_complete_requires_authentication(self, client, with_ctf_service):
        response = client.post("/api/v1/ctf/sessions/some-id/complete", json={})
        assert response.status_code == 401

    def test_complete_marks_session_completed(self, client, with_ctf_service):
        token = _register_and_login(client, email="ctf-complete@example.com")
        session_id = self._create_session(client, token)

        response = client.post(
            f"/api/v1/ctf/sessions/{session_id}/complete",
            json={"flag": "FLAG{example}"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["status"] == "completed"

    def test_already_completed_session_is_idempotent(self, client, with_ctf_service):
        token = _register_and_login(client, email="ctf-double-complete@example.com")
        session_id = self._create_session(client, token)
        headers = {"Authorization": f"Bearer {token}"}

        first = client.post(f"/api/v1/ctf/sessions/{session_id}/complete", json={}, headers=headers)
        second = client.post(f"/api/v1/ctf/sessions/{session_id}/complete", json={}, headers=headers)
        assert first.status_code == 200
        assert second.status_code == 200
        assert second.json()["data"]["status"] == "completed"

    def test_other_user_cannot_complete_session(self, client, with_ctf_service):
        token_a = _register_and_login(client, email="ctf-complete-owner-a@example.com")
        token_b = _register_and_login(client, email="ctf-complete-owner-b@example.com")
        session_id = self._create_session(client, token_a)

        response = client.post(
            f"/api/v1/ctf/sessions/{session_id}/complete",
            json={},
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert response.status_code == 403


class TestHistoryPagination:
    def test_pagination_shape(self, client, with_ctf_service):
        token = _register_and_login(client, email="ctf-pagination@example.com")
        for _ in range(3):
            client.post(
                "/api/v1/ctf/sessions",
                json=VALID_SESSION_PAYLOAD,
                headers={"Authorization": f"Bearer {token}"},
            )

        response = client.get(
            "/api/v1/ctf/sessions?page=1&limit=2", headers={"Authorization": f"Bearer {token}"}
        )
        data = response.json()["data"]
        assert data["page"] == 1
        assert data["limit"] == 2
        assert len(data["sessions"]) == 2
        assert data["total"] == 3
