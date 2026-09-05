"""
Authentication tests.

Uses the `client`/`fake_db` fixtures from conftest.py (mongomock-backed —
see that file's docstring for why). Passwords/tokens used here are test
fixtures only and are never printed.
"""

from __future__ import annotations

from app.core.security import create_access_token
from app.db.collections import Collections

VALID_PASSWORD = "correct-horse-battery-staple"


def _register(client, email="user@example.com", password=VALID_PASSWORD, name="Test User"):
    return client.post(
        "/api/v1/auth/register",
        json={"name": name, "email": email, "password": password},
    )


class TestRegister:
    def test_valid_registration_succeeds(self, client):
        response = _register(client)
        assert response.status_code == 201
        body = response.json()
        assert body["success"] is True
        user = body["data"]["user"]
        assert user["email"] == "user@example.com"
        assert user["name"] == "Test User"
        assert "id" in user
        # Never leak password/hash to the client.
        assert "password" not in user
        assert "password_hash" not in user

    def test_email_is_normalized(self, client):
        response = _register(client, email="  User@Example.COM  ")
        assert response.status_code == 201
        assert response.json()["data"]["user"]["email"] == "user@example.com"

    def test_duplicate_email_is_rejected(self, client):
        first = _register(client, email="dupe@example.com")
        assert first.status_code == 201

        second = _register(client, email="dupe@example.com")
        assert second.status_code == 409
        body = second.json()
        assert body["success"] is False
        assert body["error_code"] == "EMAIL_ALREADY_EXISTS"

    def test_duplicate_email_case_insensitive(self, client):
        first = _register(client, email="dupe@example.com")
        assert first.status_code == 201

        second = _register(client, email="DUPE@EXAMPLE.com")
        assert second.status_code == 409
        assert second.json()["error_code"] == "EMAIL_ALREADY_EXISTS"

    def test_invalid_email_is_validation_error(self, client):
        response = _register(client, email="not-an-email")
        assert response.status_code == 422
        assert response.json()["error_code"] == "VALIDATION_ERROR"

    def test_short_password_is_validation_error(self, client):
        response = _register(client, password="short")
        assert response.status_code == 422
        assert response.json()["error_code"] == "VALIDATION_ERROR"

    def test_blank_name_is_validation_error(self, client):
        response = _register(client, name="   ")
        assert response.status_code == 422


class TestPasswordSecurity:
    def test_mongodb_stores_hash_not_plaintext(self, client, fake_db):
        _register(client, email="secure@example.com", password=VALID_PASSWORD)

        stored = fake_db[Collections.USERS].find_one({"email": "secure@example.com"})
        assert stored is not None
        assert "password_hash" in stored
        assert "password" not in stored
        # The hash must not equal or contain the raw password.
        assert stored["password_hash"] != VALID_PASSWORD
        assert VALID_PASSWORD not in stored["password_hash"]
        # Argon2 hashes are self-describing and start with this prefix.
        assert stored["password_hash"].startswith("$argon2")


class TestLogin:
    def test_valid_credentials_return_token(self, client):
        _register(client, email="login@example.com", password=VALID_PASSWORD)

        response = client.post(
            "/api/v1/auth/login",
            json={"email": "login@example.com", "password": VALID_PASSWORD},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["token_type"] == "bearer"
        assert isinstance(data["access_token"], str) and len(data["access_token"]) > 0
        assert data["user"]["email"] == "login@example.com"

    def test_wrong_password_is_rejected(self, client):
        _register(client, email="login2@example.com", password=VALID_PASSWORD)

        response = client.post(
            "/api/v1/auth/login",
            json={"email": "login2@example.com", "password": "totally-wrong"},
        )
        assert response.status_code == 401
        body = response.json()
        assert body["error_code"] == "INVALID_CREDENTIALS"
        assert body["message"] == "Invalid email or password"

    def test_unknown_email_is_rejected_with_generic_error(self, client):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": VALID_PASSWORD},
        )
        assert response.status_code == 401
        # Same error/message as a wrong password — never reveals whether the
        # account exists.
        assert response.json()["error_code"] == "INVALID_CREDENTIALS"


class TestCurrentUser:
    def _login_and_get_token(self, client, email="me@example.com") -> str:
        _register(client, email=email, password=VALID_PASSWORD)
        login = client.post(
            "/api/v1/auth/login", json={"email": email, "password": VALID_PASSWORD}
        )
        return login.json()["data"]["access_token"]

    def test_valid_token_returns_user(self, client):
        token = self._login_and_get_token(client)

        response = client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["data"]["user"]["email"] == "me@example.com"

    def test_missing_token_is_unauthorized(self, client):
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401
        assert response.json()["error_code"] == "UNAUTHORIZED"

    def test_invalid_token_is_unauthorized(self, client):
        response = client.get(
            "/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"}
        )
        assert response.status_code == 401
        assert response.json()["error_code"] == "UNAUTHORIZED"

    def test_expired_token_is_unauthorized(self, client):
        register_response = _register(client, email="expired@example.com", password=VALID_PASSWORD)
        user_id = register_response.json()["data"]["user"]["id"]

        expired_token = create_access_token(subject=user_id, expires_minutes=-1)
        response = client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert response.status_code == 401
        assert response.json()["error_code"] == "UNAUTHORIZED"


class TestProtectedRoute:
    """`/auth/me` doubles as the protected-route check required by Step 2."""

    def test_no_token_denied(self, client):
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_valid_token_allowed(self, client):
        _register(client, email="protected@example.com", password=VALID_PASSWORD)
        login = client.post(
            "/api/v1/auth/login",
            json={"email": "protected@example.com", "password": VALID_PASSWORD},
        )
        token = login.json()["data"]["access_token"]

        response = client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200


class TestLogout:
    def test_logout_requires_auth_and_succeeds(self, client):
        _register(client, email="logout@example.com", password=VALID_PASSWORD)
        login = client.post(
            "/api/v1/auth/login",
            json={"email": "logout@example.com", "password": VALID_PASSWORD},
        )
        token = login.json()["data"]["access_token"]

        response = client.post(
            "/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_logout_without_token_is_unauthorized(self, client):
        response = client.post("/api/v1/auth/logout")
        assert response.status_code == 401
