"""
Step 14 — profile, preferences and password-change tests.

Uses the mongomock-backed `client`/`fake_db` fixtures from conftest.py. No test
here makes an external (Gemini / Whisper / TTS) call.
"""

from __future__ import annotations

import pytest

from app.core.security import verify_password
from app.db.collections import Collections
from tests.test_communication import VALID_PASSWORD, _register_and_login

ME = "/api/v1/users/me"
PREFS = "/api/v1/users/me/preferences"
CHANGE_PW = "/api/v1/users/me/change-password"


def _headers(client, email="profile-user@example.com") -> dict:
    return {"Authorization": f"Bearer {_register_and_login(client, email=email)}"}


def _stored(fake_db, email):
    return fake_db[Collections.USERS].find_one({"email": email})


# --------------------------------------------------------------------- profile
class TestGetProfile:
    def test_returns_defaults_for_a_user_without_profile_data(self, client, fake_db):
        headers = _headers(client)
        # Registered before Step 14: the stored document has no profile/preferences keys.
        assert "profile" not in _stored(fake_db, "profile-user@example.com")

        response = client.get(ME, headers=headers)
        assert response.status_code == 200
        user = response.json()["data"]["user"]
        assert user["email"] == "profile-user@example.com"
        assert user["full_name"] == "Comm User"
        assert user["profile"]["cybersecurity_interests"] == []
        assert user["profile"]["experience_level"] is None
        assert user["preferences"] == {
            "response_style": "balanced",
            "difficulty": "adaptive",
            "learning_style": "mixed",
            "interview_focus": [],
            "theme": "system",
            # Step 19 defaults: users created earlier get these without a migration.
            "daily_practice_enabled": True,
            "daily_practice_minutes": 15,
            "preferred_practice_time": "18:00",
            "preferred_timezone": None,
            "practice_days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            "reminders_enabled": True,
            "interview_reminders_enabled": True,
            "communication_reminders_enabled": True,
            "cybersecurity_reminders_enabled": True,
            "browser_notifications_enabled": False,
        }
        assert user["completion"]["percentage"] == 14  # only the name is filled in

    def test_never_exposes_secrets(self, client):
        text = client.get(ME, headers=_headers(client)).text
        for forbidden in ("password", "hash", "argon2", "token"):
            assert forbidden not in text.lower()

    def test_unauthenticated_is_401(self, client):
        assert client.get(ME).status_code == 401
        assert client.get(PREFS).status_code == 401
        assert client.patch(ME, json={"bio": "x"}).status_code == 401
        assert client.patch(PREFS, json={"theme": "dark"}).status_code == 401
        assert client.post(CHANGE_PW, json={}).status_code == 401


class TestUpdateProfile:
    def test_patch_persists_and_returns_updated_profile(self, client, fake_db):
        headers = _headers(client)
        body = {
            "full_name": "  Souvik Mondal  ",
            "bio": "Learning security.",
            "education": "B.Tech CSE",
            "career_goal": "Penetration Tester",
            "experience_level": "intermediate",
            "cybersecurity_interests": ["web_security", "ctf"],
            "learning_goals": ["practice_ctfs"],
            "custom_learning_goals": ["Pass OSCP"],
        }
        response = client.patch(ME, json=body, headers=headers)
        assert response.status_code == 200
        user = response.json()["data"]["user"]
        assert user["full_name"] == "Souvik Mondal"  # trimmed
        assert user["profile"]["cybersecurity_interests"] == ["web_security", "ctf"]
        assert user["completion"]["percentage"] == 100

        # Persisted: a fresh GET returns the same thing, and `name` (used by the
        # rest of the app) was updated rather than a duplicate field being added.
        again = client.get(ME, headers=headers).json()["data"]["user"]
        assert again["profile"]["career_goal"] == "Penetration Tester"
        stored = _stored(fake_db, "profile-user@example.com")
        assert stored["name"] == "Souvik Mondal"
        assert stored["profile"]["cybersecurity_interests"] == ["web_security", "ctf"]
        assert "full_name" not in stored

    def test_updated_name_is_visible_via_auth_me(self, client):
        headers = _headers(client)
        client.patch(ME, json={"full_name": "New Name"}, headers=headers)
        assert client.get("/api/v1/auth/me", headers=headers).json()["data"]["user"]["name"] == "New Name"

    def test_partial_patch_leaves_other_fields_alone(self, client):
        headers = _headers(client)
        client.patch(ME, json={"bio": "keep me", "career_goal": "SOC Analyst"}, headers=headers)
        client.patch(ME, json={"career_goal": "Red Teamer"}, headers=headers)
        user = client.get(ME, headers=headers).json()["data"]["user"]
        assert user["profile"]["bio"] == "keep me"
        assert user["profile"]["career_goal"] == "Red Teamer"

    def test_empty_string_clears_a_text_field_and_empty_list_clears_a_list(self, client):
        headers = _headers(client)
        client.patch(ME, json={"bio": "x", "cybersecurity_interests": ["ctf"]}, headers=headers)
        client.patch(ME, json={"bio": "", "cybersecurity_interests": []}, headers=headers)
        profile = client.get(ME, headers=headers).json()["data"]["user"]["profile"]
        assert profile["bio"] == ""
        assert profile["cybersecurity_interests"] == []

    def test_duplicate_list_entries_are_collapsed(self, client):
        headers = _headers(client)
        response = client.patch(
            ME, json={"cybersecurity_interests": ["ctf", "ctf", "soc"]}, headers=headers
        )
        assert response.json()["data"]["user"]["profile"]["cybersecurity_interests"] == ["ctf", "soc"]

    def test_empty_body_is_a_harmless_noop(self, client):
        assert client.patch(ME, json={}, headers=_headers(client)).status_code == 200

    @pytest.mark.parametrize(
        "body",
        [
            {"full_name": "   "},
            {"full_name": "x" * 101},
            {"bio": "x" * 501},
            {"education": "x" * 151},
            {"career_goal": "x" * 101},
            {"experience_level": "guru"},
            {"cybersecurity_interests": ["underwater_basket_weaving"]},
            {"cybersecurity_interests": "web_security"},
            {"learning_goals": ["not_a_goal"]},
            {"custom_learning_goals": ["a"] * 6},
            {"custom_learning_goals": ["x" * 101]},
            {"custom_learning_goals": [""]},
        ],
    )
    def test_invalid_data_is_rejected(self, client, body):
        response = client.patch(ME, json=body, headers=_headers(client))
        assert response.status_code == 422
        assert response.json()["error_code"] == "VALIDATION_ERROR"

    def test_corrupt_stored_profile_falls_back_to_defaults(self, client, fake_db):
        headers = _headers(client)
        fake_db[Collections.USERS].update_one(
            {"email": "profile-user@example.com"},
            {"$set": {"profile": {"experience_level": "wizard"}, "preferences": {"theme": 5}}},
        )
        response = client.get(ME, headers=headers)
        assert response.status_code == 200
        assert response.json()["data"]["user"]["preferences"]["theme"] == "system"


class TestProtectedFieldsCannotBeMassAssigned:
    @pytest.mark.parametrize(
        "field,value",
        [
            ("_id", "000000000000000000000000"),
            ("id", "000000000000000000000000"),
            ("user_id", "000000000000000000000000"),
            ("email", "attacker@example.com"),
            ("password_hash", "$argon2id$evil"),
            ("password", "new-secret-123"),
            ("created_at", "2000-01-01T00:00:00Z"),
            ("is_active", False),
            ("is_admin", True),
            ("roles", ["admin"]),
            ("permissions", ["*"]),
            ("profile", {"bio": "x"}),
            ("preferences", {"theme": "dark"}),
        ],
    )
    def test_protected_field_is_rejected_and_nothing_changes(self, client, fake_db, field, value):
        headers = _headers(client)
        before = _stored(fake_db, "profile-user@example.com")

        response = client.patch(ME, json={"bio": "ok", field: value}, headers=headers)
        assert response.status_code == 422

        after = _stored(fake_db, "profile-user@example.com")
        assert after == before  # not even the legitimate field was applied

    def test_preferences_endpoint_also_rejects_unknown_fields(self, client):
        response = client.patch(
            PREFS, json={"theme": "dark", "is_admin": True}, headers=_headers(client)
        )
        assert response.status_code == 422


# ----------------------------------------------------------------- preferences
class TestPreferences:
    def test_get_defaults(self, client):
        response = client.get(PREFS, headers=_headers(client))
        assert response.status_code == 200
        prefs = response.json()["data"]["preferences"]
        assert prefs["response_style"] == "balanced"
        assert prefs["difficulty"] == "adaptive"

    def test_patch_persists(self, client, fake_db):
        headers = _headers(client)
        response = client.patch(
            PREFS,
            json={
                "response_style": "technical",
                "difficulty": "adaptive",
                "learning_style": "hands_on",
                "interview_focus": ["soc", "blue_team", "soc"],
                "theme": "light",
            },
            headers=headers,
        )
        assert response.status_code == 200
        prefs = client.get(PREFS, headers=headers).json()["data"]["preferences"]
        assert {k: prefs[k] for k in ("response_style", "difficulty", "learning_style", "interview_focus", "theme")} == {
            "response_style": "technical",
            "difficulty": "adaptive",
            "learning_style": "hands_on",
            "interview_focus": ["soc", "blue_team"],
            "theme": "light",
        }
        assert prefs["daily_practice_minutes"] == 15  # Step 19 settings untouched by this patch
        assert _stored(fake_db, "profile-user@example.com")["preferences"]["theme"] == "light"

    def test_partial_patch_keeps_other_preferences(self, client):
        headers = _headers(client)
        client.patch(PREFS, json={"theme": "dark"}, headers=headers)
        client.patch(PREFS, json={"response_style": "simple"}, headers=headers)
        prefs = client.get(PREFS, headers=headers).json()["data"]["preferences"]
        assert prefs["theme"] == "dark"
        assert prefs["response_style"] == "simple"

    def test_preferences_show_up_in_profile_response(self, client):
        headers = _headers(client)
        client.patch(PREFS, json={"learning_style": "practical"}, headers=headers)
        user = client.get(ME, headers=headers).json()["data"]["user"]
        assert user["preferences"]["learning_style"] == "practical"

    @pytest.mark.parametrize(
        "body",
        [
            {"response_style": "verbose"},
            {"difficulty": "impossible"},
            {"learning_style": "osmosis"},
            {"interview_focus": ["small_talk"]},
            {"interview_focus": "hr"},
            {"theme": "neon"},
        ],
    )
    def test_invalid_values_rejected(self, client, body):
        response = client.patch(PREFS, json=body, headers=_headers(client))
        assert response.status_code == 422
        assert response.json()["error_code"] == "VALIDATION_ERROR"


# -------------------------------------------------------------------- profile %
class TestProfileCompletion:
    def test_percentage_tracks_filled_fields(self, client):
        headers = _headers(client)
        patch = lambda body: client.patch(ME, json=body, headers=headers).json()["data"]["user"]["completion"]  # noqa: E731

        assert patch({"education": "BSc"})["percentage"] == 29  # 2 / 7
        assert patch({"experience_level": "beginner"})["percentage"] == 43  # 3 / 7
        done = patch({"custom_learning_goals": ["Pass OSCP"]})  # custom goal counts as goals
        assert done["percentage"] == 57  # 4 / 7
        by_key = {item["key"]: item["done"] for item in done["items"]}
        assert by_key["learning_goals"] is True
        assert by_key["bio"] is False

    def test_clearing_a_field_lowers_the_percentage(self, client):
        headers = _headers(client)
        client.patch(ME, json={"bio": "hello"}, headers=headers)
        cleared = client.patch(ME, json={"bio": ""}, headers=headers).json()["data"]["user"]
        assert cleared["completion"]["percentage"] == 14


# -------------------------------------------------------------------- password
class TestChangePassword:
    NEW = "a-brand-new-passphrase"

    def _change(self, client, headers, current=VALID_PASSWORD, new=None, confirm=None):
        new = new if new is not None else self.NEW
        return client.post(
            CHANGE_PW,
            json={
                "current_password": current,
                "new_password": new,
                "confirm_new_password": confirm if confirm is not None else new,
            },
            headers=headers,
        )

    def _login(self, client, password, email="profile-user@example.com"):
        return client.post("/api/v1/auth/login", json={"email": email, "password": password})

    def test_successful_change(self, client, fake_db):
        headers = _headers(client)
        response = self._change(client, headers)
        assert response.status_code == 200
        assert response.json()["message"] == "Password changed successfully"
        assert "password" not in response.text.lower().replace("password changed", "")

        # New password works, old one no longer does.
        assert self._login(client, self.NEW).status_code == 200
        assert self._login(client, VALID_PASSWORD).status_code == 401

        # Stored as an Argon2 hash, never plaintext.
        stored = _stored(fake_db, "profile-user@example.com")["password_hash"]
        assert stored.startswith("$argon2")
        assert self.NEW not in stored
        assert verify_password(self.NEW, stored)

    def test_user_stays_logged_in_after_changing_password(self, client):
        headers = _headers(client)
        self._change(client, headers)
        assert client.get("/api/v1/auth/me", headers=headers).status_code == 200

    def test_wrong_current_password(self, client):
        response = self._change(client, _headers(client), current="not-my-password")
        assert response.status_code == 400  # not 401: that would sign the user out
        body = response.json()
        assert body["error_code"] == "INVALID_CURRENT_PASSWORD"
        assert body["message"] == "Current password is incorrect."

    def test_wrong_current_password_leaves_password_unchanged(self, client):
        headers = _headers(client)
        self._change(client, headers, current="not-my-password")
        assert self._login(client, VALID_PASSWORD).status_code == 200

    def test_confirmation_mismatch(self, client):
        response = self._change(client, _headers(client), confirm="something-else-entirely")
        assert response.status_code == 400
        assert response.json()["error_code"] == "PASSWORD_MISMATCH"
        assert response.json()["message"] == "New passwords do not match."

    def test_new_password_too_short(self, client):
        response = self._change(client, _headers(client), new="short")
        assert response.status_code == 400
        assert response.json()["error_code"] == "PASSWORD_TOO_SHORT"
        assert response.json()["message"] == "Password must be at least 8 characters."

    def test_new_password_must_differ(self, client):
        response = self._change(client, _headers(client), new=VALID_PASSWORD)
        assert response.status_code == 400
        assert response.json()["error_code"] == "PASSWORD_UNCHANGED"

    def test_missing_or_oversized_fields_are_validation_errors(self, client):
        headers = _headers(client)
        assert client.post(CHANGE_PW, json={"current_password": "x"}, headers=headers).status_code == 422
        assert self._change(client, headers, new="x" * 129).status_code == 422

    def test_password_is_not_logged(self, client, caplog):
        headers = _headers(client)
        with caplog.at_level("DEBUG"):
            self._change(client, headers)
        assert self.NEW not in caplog.text
        assert VALID_PASSWORD not in caplog.text


# --------------------------------------------------------------- authorization
class TestUsersAreIsolated:
    def test_user_a_cannot_modify_user_b_via_body_fields(self, client, fake_db):
        a = _headers(client, "user-a@example.com")
        _headers(client, "user-b@example.com")
        b_before = _stored(fake_db, "user-b@example.com")
        b_id = str(b_before["_id"])

        # Every "who am I editing" hint an attacker could try is rejected...
        for hint in ({"user_id": b_id}, {"id": b_id}, {"_id": b_id}, {"email": "user-b@example.com"}):
            assert client.patch(ME, json={"bio": "pwned", **hint}, headers=a).status_code == 422
            assert client.patch(PREFS, json={"theme": "dark", **hint}, headers=a).status_code == 422

        # ...and query-string / path tricks have no effect either: the target is the JWT's user.
        client.patch(f"{ME}?user_id={b_id}", json={"bio": "only mine"}, headers=a)
        client.patch(f"{PREFS}?user_id={b_id}", json={"theme": "dark"}, headers=a)

        assert _stored(fake_db, "user-b@example.com") == b_before
        assert _stored(fake_db, "user-a@example.com")["profile"]["bio"] == "only mine"

    def test_each_user_only_sees_their_own_profile(self, client):
        a = _headers(client, "iso-a@example.com")
        b = _headers(client, "iso-b@example.com")
        client.patch(ME, json={"bio": "A's bio"}, headers=a)
        assert client.get(ME, headers=b).json()["data"]["user"]["profile"]["bio"] == ""
        assert client.get(ME, headers=b).json()["data"]["user"]["email"] == "iso-b@example.com"

    def test_user_a_password_change_does_not_affect_user_b(self, client):
        a = _headers(client, "pw-a@example.com")
        _headers(client, "pw-b@example.com")
        client.post(
            CHANGE_PW,
            json={
                "current_password": VALID_PASSWORD,
                "new_password": "another-long-passphrase",
                "confirm_new_password": "another-long-passphrase",
            },
            headers=a,
        )
        login_b = client.post(
            "/api/v1/auth/login", json={"email": "pw-b@example.com", "password": VALID_PASSWORD}
        )
        assert login_b.status_code == 200
