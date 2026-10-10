"""
Final audit (Step 20) — regression tests for the hardening done during the audit, plus the
cross-user / data-isolation checks that were not covered elsewhere.

No external (Gemini / Whisper / TTS) call is made here.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
import pytest
from bson import ObjectId
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from app.core import config as config_module
from app.core.config import ConfigurationError, settings
from app.core.dependencies import get_db
from app.core.security import create_access_token
from app.db import mongodb
from app.db.collections import Collections
from app.main import app
from app.services.auth import auth_service
from tests.test_communication import VALID_PASSWORD, _register_and_login

API = settings.api_v1_prefix
BACKEND_DIR = Path(__file__).resolve().parents[1]


def _isolated_env(**overrides) -> dict:
    """
    Environment for a subprocess that imports the app without picking up the developer's own
    configuration: it runs from a neutral working directory (so `backend/.env`, which Settings
    resolves relative to the cwd, is not found) and with the app's config variables cleared.
    """
    import tempfile
    config_names = {n.upper() for n in config_module.Settings.model_fields}
    env = {k: v for k, v in os.environ.items() if k.upper() not in config_names}
    env["PYTHONPATH"] = str(BACKEND_DIR)
    env["_NEUTRAL_CWD"] = tempfile.gettempdir()
    env.update(overrides)
    return env


def _strip(env: dict) -> dict:
    return {k: v for k, v in env.items() if k != "_NEUTRAL_CWD"}


def _auth(client, email: str) -> dict:
    return {"Authorization": f"Bearer {_register_and_login(client, email=email)}"}


def _uid(fake_db, email: str) -> ObjectId:
    return fake_db[Collections.USERS].find_one({"email": email})["_id"]


# --------------------------------------------------------------------------- production config
class TestProductionConfiguration:
    @pytest.fixture(autouse=True)
    def _fresh_settings(self, monkeypatch):
        # Hermetic: a developer's local backend/.env (which normally holds a real JWT secret)
        # must not leak into these tests, so neither the environment nor the .env file is read.
        monkeypatch.setitem(config_module.Settings.model_config, "env_file", None)
        for name in ("APP_ENV", "JWT_SECRET_KEY", "CORS_ALLOWED_ORIGINS", "JWT_ALGORITHM"):
            monkeypatch.delenv(name, raising=False)
        config_module.get_settings.cache_clear()
        yield
        config_module.get_settings.cache_clear()

    @pytest.mark.parametrize("secret", [None, "", "too-short"])
    def test_production_refuses_a_missing_or_weak_jwt_secret(self, monkeypatch, secret):
        monkeypatch.setenv("APP_ENV", "production")
        if secret is not None:
            monkeypatch.setenv("JWT_SECRET_KEY", secret)
        with pytest.raises(ConfigurationError) as err:
            config_module.get_settings()
        assert "too-short" not in str(err.value)  # the message never echoes a secret

    def test_production_refuses_wildcard_cors(self, monkeypatch):
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("JWT_SECRET_KEY", "k" * 40)
        monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "*")
        with pytest.raises(ConfigurationError):
            config_module.get_settings()

    def test_production_accepts_a_strong_configuration(self, monkeypatch):
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("JWT_SECRET_KEY", "k" * 40)
        assert config_module.get_settings().is_production

    def test_development_still_starts_without_a_secret(self, monkeypatch):
        resolved = config_module.get_settings()
        assert len(resolved.jwt_secret_key) >= 32  # random per-process fallback

    def test_jwt_algorithm_cannot_be_none(self, monkeypatch):
        monkeypatch.setenv("JWT_ALGORITHM", "none")
        with pytest.raises(ConfigurationError):
            config_module.get_settings()

    def test_ai_test_endpoint_is_not_mounted_in_production(self):
        code = (
            "from app.api.router import api_router;"
            "print(any(getattr(r,'path','').endswith('/ai/chat') for r in api_router.routes))"
        )
        env = _isolated_env(APP_ENV="production", JWT_SECRET_KEY="k" * 40)
        out = subprocess.run([sys.executable, "-c", code], cwd=env["_NEUTRAL_CWD"], env=_strip(env),
                             capture_output=True, text=True, timeout=60)
        assert out.stdout.strip().splitlines()[-1] == "False", out.stderr[-500:]


class TestApiDocsInProduction:
    CODE = (
        "from fastapi.testclient import TestClient;from app.main import app;"
        "c=TestClient(app);print([c.get(p).status_code for p in ('/docs','/redoc','/openapi.json')])"
    )

    def _run(self, **extra_env):
        env = _isolated_env(**extra_env)
        out = subprocess.run([sys.executable, "-c", self.CODE], cwd=env["_NEUTRAL_CWD"], env=_strip(env),
                             capture_output=True, text=True, timeout=90)
        return out.stdout.strip().splitlines()[-1] if out.stdout.strip() else out.stderr[-400:]

    def test_docs_and_schema_are_disabled_in_production(self):
        assert self._run(APP_ENV="production", JWT_SECRET_KEY="k" * 40) == "[404, 404, 404]"

    def test_docs_remain_available_in_development(self):
        assert self._run(APP_ENV="development") == "[200, 200, 200]"


# --------------------------------------------------------------------------- authentication
class TestLoginHardening:
    def test_unknown_email_still_does_the_password_hash_work(self, client, monkeypatch):
        calls = []
        real = auth_service.verify_password
        monkeypatch.setattr(auth_service, "verify_password", lambda p, h: calls.append(h) or real(p, h))
        response = client.post(f"{API}/auth/login", json={"email": "ghost@example.com", "password": "Whatever123"})
        assert response.status_code == 401
        assert len(calls) == 1  # same Argon2 cost as a wrong password -> no timing oracle

    def test_overlong_login_password_is_rejected(self, client):
        response = client.post(f"{API}/auth/login", json={"email": "a@example.com", "password": "p" * 129})
        assert response.status_code == 422


def _forge(uid, **claims) -> str:
    """A correctly signed token with exactly the claims given (for testing the validator)."""
    now = datetime.now(timezone.utc)
    payload = {"sub": str(uid), "iat": now, "exp": now + timedelta(minutes=30), **claims}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class TestPasswordChangeRevokesOldTokens:
    BODY = {"current_password": VALID_PASSWORD, "new_password": "BrandNew-Pass-456", "confirm_new_password": "BrandNew-Pass-456"}

    def test_old_token_stops_working_and_the_returned_token_works(self, client):
        old = _register_and_login(client, email="rotate@example.com")
        response = client.post(f"{API}/users/me/change-password", json=self.BODY, headers=_bearer(old))
        assert response.status_code == 200
        new_token = response.json()["data"]["access_token"]
        assert client.get(f"{API}/auth/me", headers=_bearer(old)).status_code == 401
        assert client.get(f"{API}/auth/me", headers=_bearer(new_token)).status_code == 200

    def test_same_second_regression_token_issued_in_the_same_second_as_the_change(self, client, monkeypatch):
        """
        Regression for the audit finding: JWT `iat` has whole-second precision, so a timestamp
        comparison could not tell a token issued *before* a password change from one issued
        after it when both fell in the same second. With the clock frozen, the old token, the
        change and the fresh token all share one `iat` — only the token version can separate them.
        """
        import app.core.security as security_module

        frozen = datetime.now(timezone.utc).replace(microsecond=250_000)

        class _FrozenDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return frozen

        monkeypatch.setattr(security_module, "datetime", _FrozenDatetime)
        old = _register_and_login(client, email="samesec@example.com")
        response = client.post(f"{API}/users/me/change-password", json=self.BODY, headers=_bearer(old))
        assert response.status_code == 200
        fresh = response.json()["data"]["access_token"]

        old_claims = jwt.decode(old, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        fresh_claims = jwt.decode(fresh, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        assert old_claims["iat"] == fresh_claims["iat"]            # genuinely the same second
        assert client.get(f"{API}/auth/me", headers=_bearer(old)).status_code == 401
        assert client.get(f"{API}/auth/me", headers=_bearer(fresh)).status_code == 200

    def test_a_second_password_change_revokes_the_token_from_the_first(self, client):
        first = _register_and_login(client, email="twice@example.com")
        r1 = client.post(f"{API}/users/me/change-password", json=self.BODY, headers=_bearer(first))
        token_v1 = r1.json()["data"]["access_token"]
        again = {"current_password": "BrandNew-Pass-456", "new_password": "Third-Pass-789!", "confirm_new_password": "Third-Pass-789!"}
        r2 = client.post(f"{API}/users/me/change-password", json=again, headers=_bearer(token_v1))
        token_v2 = r2.json()["data"]["access_token"]
        assert [client.get(f"{API}/auth/me", headers=_bearer(t)).status_code for t in (first, token_v1, token_v2)] == [401, 401, 200]

    def test_login_after_a_change_issues_a_token_for_the_current_version(self, client):
        headers = _bearer(_register_and_login(client, email="relogin@example.com"))
        client.post(f"{API}/users/me/change-password", json=self.BODY, headers=headers)
        login = client.post(f"{API}/auth/login", json={"email": "relogin@example.com", "password": "BrandNew-Pass-456"})
        assert client.get(f"{API}/auth/me", headers=_bearer(login.json()["data"]["access_token"])).status_code == 200

    def test_new_password_logs_in_and_old_one_does_not(self, client):
        headers = _auth(client, "rotate2@example.com")
        client.post(f"{API}/users/me/change-password", json=self.BODY, headers=headers)
        ok = client.post(f"{API}/auth/login", json={"email": "rotate2@example.com", "password": "BrandNew-Pass-456"})
        bad = client.post(f"{API}/auth/login", json={"email": "rotate2@example.com", "password": VALID_PASSWORD})
        assert (ok.status_code, bad.status_code) == (200, 401)

    def test_a_token_that_predates_the_version_claim_still_works_until_the_password_changes(self, client, fake_db):
        _register_and_login(client, email="legacy@example.com")
        uid = _uid(fake_db, "legacy@example.com")
        legacy = _forge(uid)                                   # no `tv` claim at all
        assert client.get(f"{API}/auth/me", headers=_bearer(legacy)).status_code == 200
        client.post(f"{API}/users/me/change-password", json=self.BODY,
                    headers=_bearer(_forge(uid)))
        assert client.get(f"{API}/auth/me", headers=_bearer(legacy)).status_code == 401

    @pytest.mark.parametrize("claim", [1, -1, 10**6, "0", None, 0.0, True, [0]])
    def test_forged_version_claims_are_rejected(self, client, fake_db, claim):
        _register_and_login(client, email="forged@example.com")
        uid = _uid(fake_db, "forged@example.com")             # account is at version 0
        # 0.0 and True compare equal to 0 / 1 in Python but are not valid integer versions.
        assert client.get(f"{API}/auth/me", headers=_bearer(_forge(uid, tv=claim))).status_code == 401

    def test_wrong_current_password_does_not_revoke_anything(self, client):
        headers = _auth(client, "wrongcur@example.com")
        bad = {**self.BODY, "current_password": "not-the-password"}
        assert client.post(f"{API}/users/me/change-password", json=bad, headers=headers).status_code == 400
        assert client.get(f"{API}/auth/me", headers=headers).status_code == 200

    def test_response_never_contains_password_material(self, client):
        headers = _auth(client, "nopw@example.com")
        text = client.post(f"{API}/users/me/change-password", json=self.BODY, headers=headers).text
        assert "BrandNew" not in text and VALID_PASSWORD not in text and "$argon2" not in text
        assert "password_hash" not in client.get(f"{API}/users/me", headers=headers).text


class TestJwtValidationMatrix:
    """Malformed, expired, wrongly signed, unsigned and tampered tokens are all rejected."""

    def _uid_and_good_token(self, client, fake_db):
        good = _register_and_login(client, email="matrix@example.com")
        return _uid(fake_db, "matrix@example.com"), good

    def test_good_token_is_accepted(self, client, fake_db):
        _, good = self._uid_and_good_token(client, fake_db)
        assert client.get(f"{API}/auth/me", headers=_bearer(good)).status_code == 200

    def test_malformed_tokens(self, client):
        for bad in ("", "abc", "a.b.c", "Bearer", "x" * 5000, "....", "eyJhbGciOiJIUzI1NiJ9.e30."):
            assert client.get(f"{API}/auth/me", headers=_bearer(bad)).status_code == 401, bad[:20]

    def test_expired_token(self, client, fake_db):
        uid, _ = self._uid_and_good_token(client, fake_db)
        past = datetime.now(timezone.utc) - timedelta(minutes=5)
        expired = jwt.encode({"sub": str(uid), "tv": 0, "iat": past - timedelta(minutes=30), "exp": past},
                             settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
        assert client.get(f"{API}/auth/me", headers=_bearer(expired)).status_code == 401

    def test_token_signed_with_another_secret(self, client, fake_db):
        uid, _ = self._uid_and_good_token(client, fake_db)
        wrong = jwt.encode({"sub": str(uid), "tv": 0, "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
                           "a-completely-different-secret-value-32+", algorithm="HS256")
        assert client.get(f"{API}/auth/me", headers=_bearer(wrong)).status_code == 401

    def test_unsigned_alg_none_token(self, client, fake_db):
        import base64, json
        uid, _ = self._uid_and_good_token(client, fake_db)
        enc = lambda d: base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()
        unsigned = f"{enc({'alg': 'none', 'typ': 'JWT'})}.{enc({'sub': str(uid), 'tv': 0, 'exp': 9999999999})}."
        assert client.get(f"{API}/auth/me", headers=_bearer(unsigned)).status_code == 401

    def test_payload_tampered_after_signing(self, client, fake_db):
        import base64, json
        uid, good = self._uid_and_good_token(client, fake_db)
        other = ObjectId()
        header, payload, signature = good.split(".")
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        claims["sub"] = str(other)
        forged = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()
        assert client.get(f"{API}/auth/me", headers=_bearer(f"{header}.{forged}.{signature}")).status_code == 401

    def test_token_for_a_deleted_or_unknown_user(self, client):
        assert client.get(f"{API}/auth/me", headers=_bearer(_forge(ObjectId(), tv=0))).status_code == 401

    def test_non_objectid_subject(self, client):
        assert client.get(f"{API}/auth/me", headers=_bearer(_forge("not-an-object-id", tv=0))).status_code == 401

    def test_token_payload_contains_no_personal_data(self, client, fake_db):
        _, good = self._uid_and_good_token(client, fake_db)
        claims = jwt.decode(good, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        assert set(claims) == {"sub", "tv", "iat", "exp"}


# --------------------------------------------------------------------------- request size
class TestRequestBodyLimit:
    def test_oversized_json_is_rejected_with_413_before_parsing(self, client):
        big = b'{"email":"a@example.com","password":"' + b"x" * (settings.max_request_body_bytes + 10) + b'"}'
        response = client.post(f"{API}/auth/login", content=big, headers={"Content-Type": "application/json"})
        assert response.status_code == 413
        assert response.json() == {"success": False, "message": "The request is too large.", "error_code": "PAYLOAD_TOO_LARGE"}

    def test_chunked_body_without_content_length_is_capped_too(self, client):
        def chunks():
            for _ in range(settings.max_request_body_bytes // 65536 + 2):
                yield b"x" * 65536
        response = client.post(f"{API}/auth/login", content=chunks(), headers={"Content-Type": "application/json"})
        assert response.status_code == 413

    def test_normal_requests_are_unaffected(self, client):
        assert client.post(f"{API}/auth/login", json={"email": "a@example.com", "password": "x"}).status_code == 401

    def test_audio_routes_keep_their_own_limit(self, client):
        # Not stopped by the generic limit: the route itself answers (401 without a token).
        big = b"x" * (settings.max_request_body_bytes + 1000)
        response = client.post(f"{API}/voice/transcribe", content=big, headers={"Content-Type": "application/octet-stream"})
        assert response.status_code != 413


# --------------------------------------------------------------------------- pagination
class TestPageUpperBound:
    @pytest.mark.parametrize("path", ["/history", "/notifications", "/ctf/sessions", "/interview/sessions",
                                      "/pressure/sessions", "/communication/sessions",
                                      "/cybersecurity/practice/history", "/voice-conversation/sessions"])
    def test_absurd_page_numbers_are_rejected(self, client, path):
        headers = _auth(client, "pagecap@example.com")
        assert client.get(f"{API}{path}?page=100001", headers=headers).status_code == 422
        assert client.get(f"{API}{path}?page={10**30}", headers=headers).status_code == 422


# --------------------------------------------------------------------------- AI prompt budget
class TestAiHistoryBudget:
    def test_history_is_trimmed_to_the_character_budget_keeping_the_newest(self):
        from app.services.ai.ai_service import MAX_HISTORY_CHARS, ConversationTurn, _trim_to_budget
        turns = [ConversationTurn("user" if i % 2 == 0 else "assistant", f"{i}:" + "x" * 9_000) for i in range(40)]
        kept = _trim_to_budget(turns)
        assert sum(len(t.content) for t in kept) <= MAX_HISTORY_CHARS
        assert kept[-1] is turns[-1] and len(kept) < len(turns)

    def test_short_history_is_untouched(self):
        from app.services.ai.ai_service import ConversationTurn, _trim_to_budget
        turns = [ConversationTurn("user", "hi"), ConversationTurn("assistant", "hello")]
        assert _trim_to_budget(turns) == turns

    def test_one_huge_turn_is_still_kept_rather_than_dropping_everything(self):
        from app.services.ai.ai_service import MAX_HISTORY_CHARS, ConversationTurn, _trim_to_budget
        only = [ConversationTurn("user", "x" * (MAX_HISTORY_CHARS + 5))]
        assert _trim_to_budget(only) == only


# --------------------------------------------------------------------------- database outages
class _Boom:
    def __getitem__(self, _):
        raise ServerSelectionTimeoutError("host-a:27017 timed out, topology details")


class TestDatabaseOutages:
    def test_connection_failure_mid_request_is_a_clean_503(self, client):
        token = create_access_token(subject=str(ObjectId()))
        app.dependency_overrides[get_db] = lambda: _Boom()
        response = client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 503
        body = response.json()
        assert body["error_code"] == "SERVICE_UNAVAILABLE"
        assert "host-a" not in response.text and "topology" not in response.text.lower()
        assert response.headers.get("retry-after") == "5"

    def test_no_client_at_all_is_a_503_not_a_traceback(self, client, monkeypatch):
        app.dependency_overrides.pop(get_db, None)
        monkeypatch.setattr(mongodb, "_client", None)
        token = create_access_token(subject=str(ObjectId()))
        response = client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 503 and response.json()["error_code"] == "SERVICE_UNAVAILABLE"

    def test_client_is_kept_when_the_first_ping_fails_and_recovers_later(self, monkeypatch):
        state = {"up": False}

        class _Admin:
            def command(self, _):
                if not state["up"]:
                    raise ServerSelectionTimeoutError("down")
                return {"ok": 1}

        class _Client:
            admin = _Admin()
            def __init__(self, *a, **k): ...
            def close(self): ...
            def __getitem__(self, name): return f"db:{name}"

        # conftest stubs out `mongodb.connect`, so exercise a fresh copy of the real module.
        import importlib.util
        spec = importlib.util.spec_from_file_location("mongodb_under_test", mongodb.__file__)
        real = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(real)
        monkeypatch.setattr(real, "MongoClient", _Client)
        real.connect()
        assert real.is_connected() is False
        assert real.get_database() is not None      # client kept -> can recover without a restart
        state["up"] = True
        assert real.is_connected() is True

    def test_startup_setup_is_retried_until_the_database_is_available(self, fake_db, monkeypatch):
        import app.main as main_module
        from starlette.testclient import TestClient

        state = {"up": False}
        monkeypatch.setattr(main_module, "DB_SETUP_RETRY_SECONDS", 0.05)
        monkeypatch.setattr(main_module.mongodb, "connect", lambda: None)
        monkeypatch.setattr(main_module.mongodb, "is_connected", lambda: state["up"])
        monkeypatch.setattr(main_module.mongodb, "get_database", lambda: fake_db)
        monkeypatch.setattr(main_module.mongodb, "disconnect", lambda: None)
        fake_db.drop_collection(Collections.USERS)
        assert "email_1" not in fake_db[Collections.USERS].index_information()
        with TestClient(main_module.app):
            time.sleep(0.2)
            assert "email_1" not in fake_db[Collections.USERS].index_information()  # still down
            state["up"] = True
            deadline = time.time() + 5
            while time.time() < deadline and "email_1" not in fake_db[Collections.USERS].index_information():
                time.sleep(0.05)
        assert "email_1" in fake_db[Collections.USERS].index_information()
        assert any(i.get("unique") for n, i in fake_db[Collections.USERS].index_information().items() if n == "email_1")

    def test_one_failing_setup_step_does_not_block_the_others(self, fake_db, monkeypatch):
        import app.main as main_module
        monkeypatch.setattr(main_module.ctf_service_module.ctf_service, "ensure_indexes",
                            lambda db: (_ for _ in ()).throw(RuntimeError("boom")))
        fake_db.drop_collection(Collections.PRESSURE_SESSIONS)
        assert main_module._ensure_database_ready(fake_db) is False
        assert "user_id_1" in fake_db[Collections.PRESSURE_SESSIONS].index_information()


# --------------------------------------------------------------------------- cross-user access
class TestCrossUserCoverageGaps:
    def test_voice_conversation_sessions_are_owner_only(self, client, fake_db):
        _auth(client, "va@example.com")
        b = _auth(client, "vb@example.com")
        sid = fake_db[Collections.VOICE_CONVERSATION_SESSIONS].insert_one(
            {"user_id": _uid(fake_db, "va@example.com"), "status": "active", "mode": "practice",
             "started_at": datetime.now(timezone.utc), "turn_count": 0}).inserted_id
        probes = [("GET", f"/voice-conversation/sessions/{sid}", None),
                  ("POST", f"/voice-conversation/sessions/{sid}/start", {}),
                  ("POST", f"/voice-conversation/sessions/{sid}/respond", {"transcript": "hello", "expected_turn": 0}),
                  ("POST", f"/voice-conversation/sessions/{sid}/end", {})]
        for method, path, body in probes:
            kwargs = {"json": body} if body is not None else {}
            response = client.request(method, API + path, headers=b, **kwargs)
            assert response.status_code in (403, 404), f"{method} {path} -> {response.status_code}"
        assert fake_db[Collections.VOICE_CONVERSATION_SESSIONS].find_one({"_id": sid})["status"] == "active"
        assert client.get(f"{API}/voice-conversation/sessions", headers=b).json()["data"]["total"] == 0

    def test_ai_audio_token_is_bound_to_its_user(self, client, fake_db):
        from app.services.voice_conversation.conversation_service import voice_conversation_service
        a = _auth(client, "aa@example.com")
        b = _auth(client, "ab@example.com")
        token = voice_conversation_service._audio.put(str(_uid(fake_db, "aa@example.com")), b"RIFFdata", "audio/wav")
        assert client.get(f"{API}/voice-conversation/audio/{token}", headers=b).status_code == 404
        assert client.get(f"{API}/voice-conversation/audio/{token}", headers=a).status_code == 200

    def test_notifications_are_owner_only(self, client, fake_db):
        from app.core.dependencies import get_notification_service
        from app.schemas.notification import NotificationPriority, NotificationType
        a = _auth(client, "na@example.com")
        b = _auth(client, "nb@example.com")
        a_id = str(_uid(fake_db, "na@example.com"))
        item = get_notification_service().create_if_absent(
            fake_db, user_id=a_id, type=NotificationType.SYSTEM, priority=NotificationPriority.LOW,
            title="A only", message="secret-marker-a", action_target=None, dedupe_key="t:1", expires_at=None)
        nid = item["id"]
        assert client.post(f"{API}/notifications/{nid}/read", headers=b).status_code == 404
        assert client.delete(f"{API}/notifications/{nid}", headers=b).status_code == 404
        assert client.post(f"{API}/notifications/read-all", headers=b).status_code == 200  # only B's own
        assert "secret-marker-a" not in client.get(f"{API}/notifications", headers=b).text
        assert client.get(f"{API}/notifications/unread-count", headers=b).json()["data"]["unread_count"] == 0
        # A is untouched by everything B did.
        assert client.get(f"{API}/notifications/unread-count", headers=a).json()["data"]["unread_count"] == 1
        assert client.get(f"{API}/notifications", headers=a).json()["data"]["total"] == 1

    def test_history_detail_is_owner_only(self, client, fake_db):
        _auth(client, "ha@example.com")
        b = _auth(client, "hb@example.com")
        now = datetime.now(timezone.utc)
        for collection, kind in ((Collections.PRACTICE_SESSIONS, "cybersecurity_practice"),
                                 (Collections.INTERVIEW_SESSIONS, "interview"),
                                 (Collections.PRESSURE_SESSIONS, "pressure_training"),
                                 (Collections.COMMUNICATION_SESSIONS, "communication"),
                                 (Collections.CTF_SESSIONS, "ctf")):
            sid = fake_db[collection].insert_one({"user_id": _uid(fake_db, "ha@example.com"), "status": "completed",
                                                  "started_at": now, "created_at": now}).inserted_id
            response = client.get(f"{API}/history/{kind}/{sid}", headers=b)
            assert response.status_code in (403, 404), f"{kind} -> {response.status_code}"

    def test_daily_practice_cannot_link_another_users_session(self, client, fake_db):
        _auth(client, "da@example.com")
        b = _auth(client, "db@example.com")
        sid = fake_db[Collections.PRACTICE_SESSIONS].insert_one(
            {"user_id": _uid(fake_db, "da@example.com"), "status": "in_progress",
             "started_at": datetime.now(timezone.utc)}).inserted_id
        client.get(f"{API}/daily-practice", headers=b)
        response = client.post(f"{API}/daily-practice/tasks/cybersecurity/link", json={"session_id": str(sid)}, headers=b)
        assert response.status_code in (404, 422)
        plan = client.get(f"{API}/daily-practice", headers=b).json()["data"]["plan"]
        assert all(t["session_id"] != str(sid) for t in plan["tasks"])


# --------------------------------------------------------------------------- full data isolation
MARKER = "ZZ-ISOLATION-MARKER-ZZ"
_PARAMLESS_GETS = (
    "/auth/me", "/users/me", "/users/me/preferences", "/history", "/history/summary", "/notifications",
    "/notifications/unread-count", "/daily-practice", "/daily-practice/streak", "/progress/overview",
    "/progress/skills", "/progress/trends", "/progress/weaknesses", "/progress/recommendations",
    "/progress/activity", "/progress/profile", "/personalization/profile", "/personalization/recommendations",
    "/personalization/weaknesses", "/analytics/overview", "/analytics/interviews", "/analytics/communication",
    "/analytics/speaking", "/analytics/pressure", "/analytics/domains", "/analytics/trends",
    "/analytics/readiness", "/analytics/insights", "/ctf/sessions", "/interview/sessions",
    "/pressure/sessions", "/communication/sessions", "/cybersecurity/practice/history",
    "/cybersecurity/progress", "/voice-conversation/sessions",
)


class TestUserDataIsolation:
    def _seed_user_a(self, fake_db, a_id: ObjectId) -> None:
        now = datetime.now(timezone.utc)
        base = {"user_id": a_id, "status": "completed", "started_at": now, "created_at": now,
                "completed_at": now, "updated_at": now}
        fake_db[Collections.PRACTICE_SESSIONS].insert_one({**base, "topic_title": MARKER, "topic_slug": "x",
                                                           "category": "web", "score": 91})
        fake_db[Collections.CTF_SESSIONS].insert_one({**base, "title": MARKER, "platform": "p", "category": "web"})
        fake_db[Collections.COMMUNICATION_SESSIONS].insert_one({**base, "scenario_title": MARKER, "category": "c"})
        fake_db[Collections.INTERVIEW_SESSIONS].insert_one({**base, "interview_type": MARKER})
        fake_db[Collections.PRESSURE_SESSIONS].insert_one({**base, "interview_type": MARKER})
        fake_db[Collections.VOICE_CONVERSATION_SESSIONS].insert_one({**base, "topic": MARKER, "mode": "practice"})
        fake_db[Collections.USER_WEAKNESSES].insert_one({"user_id": a_id, "area": MARKER, "skill": MARKER, "source": "t"})
        fake_db[Collections.RECOMMENDATIONS].insert_one({"user_id": a_id, "area": MARKER, "reason": MARKER,
                                                         "completed": False, "created_at": now})
        fake_db[Collections.LEARNING_PROGRESS].insert_one({"user_id": a_id, "skill": MARKER, "score": 90})
        fake_db[Collections.PERSONAL_PROFILES].insert_one({"user_id": a_id, "recent_focus": [MARKER]})
        from app.core.dependencies import get_notification_service
        from app.schemas.notification import NotificationPriority, NotificationType
        get_notification_service().create_if_absent(
            fake_db, user_id=str(a_id), type=NotificationType.SYSTEM, priority=NotificationPriority.LOW,
            title=MARKER, message=MARKER, action_target=None, dedupe_key="iso:1", expires_at=None)

    def test_user_b_never_sees_user_a_data_and_user_a_still_does(self, client, fake_db):
        a = _auth(client, "iso-a@example.com")
        b = _auth(client, "iso-b@example.com")
        a_id = _uid(fake_db, "iso-a@example.com")
        self._seed_user_a(fake_db, a_id)

        leaks, errors = [], []
        for path in _PARAMLESS_GETS:
            response = client.get(API + path, headers=b)
            if response.status_code >= 500:
                errors.append((path, response.status_code))
            if MARKER in response.text or str(a_id) in response.text or "iso-a@example.com" in response.text:
                leaks.append(path)
        assert not errors, f"5xx for user B: {errors}"
        assert not leaks, f"user A's data leaked to user B via: {leaks}"

        # A's own data is still there, and B's activity didn't alter it.
        history = client.get(f"{API}/history?limit=50", headers=a)
        assert history.status_code == 200 and MARKER in history.text
        assert client.get(f"{API}/notifications", headers=a).json()["data"]["total"] == 1
        # Weaknesses/recommendations are re-derived (and unsupported rows pruned) per reader.
        # User B's reads must therefore only ever have touched B's rows, never A's stored ones.
        assert fake_db[Collections.USER_WEAKNESSES].count_documents({"user_id": a_id}) == 1
        assert fake_db[Collections.RECOMMENDATIONS].count_documents({"user_id": a_id}) == 1
        assert fake_db[Collections.LEARNING_PROGRESS].count_documents({"user_id": a_id}) == 1


# --------------------------------------------------------------------------- concurrent duplicate actions
class TestConcurrentCtfHintRequests:
    """
    Two requests for the same hint level can interleave (double-click, a retry racing the
    original). Sequential duplicates were already handled; this covers the overlapping case,
    where both requests pass the "not yet persisted" check before either has written.
    """

    def _session_id(self, client, headers) -> str:
        from tests.test_ctf import VALID_SESSION_PAYLOAD
        return client.post(f"{API}/ctf/sessions", json=VALID_SESSION_PAYLOAD, headers=headers).json()["data"]["session_id"]

    def test_overlapping_requests_for_one_level_record_the_hint_once(self, client, fake_db):
        import asyncio
        from app.services.cybersecurity.ctf_service import CtfService
        from tests.test_ctf import _ScriptedAIService

        headers = _auth(client, "race@example.com")
        user_id = str(_uid(fake_db, "race@example.com"))
        session_id = self._session_id(client, headers)

        class _RacingAI(_ScriptedAIService):
            """While request #1 is 'waiting for Gemini', request #2 for the same level finishes first."""
            def __init__(self):
                self.service: CtfService | None = None
                self.calls = 0

            async def generate_response(self, **kwargs):
                self.calls += 1
                if self.calls == 1:
                    await self.service.get_hint(fake_db, user_id=user_id, session_id=session_id, level="hint_1")
                return await super().generate_response(**kwargs)

        ai = _RacingAI()
        service = CtfService(ai_service_=ai)
        ai.service = service
        result = asyncio.run(service.get_hint(fake_db, user_id=user_id, session_id=session_id, level="hint_1"))

        stored = fake_db[Collections.CTF_SESSIONS].find_one({"_id": ObjectId(session_id)})
        assert len(stored["hint_history"]) == 1, "the same hint was recorded twice"
        assert stored["hints_used"] == 1, "hints_used was incremented twice for one hint"
        assert result["hints_used"] == 1
        assert result["content"] == stored["hint_history"][0]["content"]


# --------------------------------------------------------------------------- legacy (pre-token_version) accounts
def _make_legacy_user(client, fake_db, email: str, changed_at: datetime) -> ObjectId:
    """
    A user record exactly as the earlier Step 20 build left it after a password change:
    `password_changed_at` set, and no `token_version` field at all.
    """
    email = email.lower()                      # the API stores emails lowercased
    _register_and_login(client, email=email)
    uid = _uid(fake_db, email)
    fake_db[Collections.USERS].update_one(
        {"_id": uid}, {"$set": {"password_changed_at": changed_at}, "$unset": {"token_version": ""}}
    )
    assert "token_version" not in fake_db[Collections.USERS].find_one({"_id": uid})
    return uid


def _claims(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


def _login(client, email: str, password: str = VALID_PASSWORD) -> str:
    response = client.post(f"{API}/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["data"]["access_token"]


_PW_CHANGE = {"current_password": VALID_PASSWORD, "new_password": "BrandNew-Pass-456", "confirm_new_password": "BrandNew-Pass-456"}


class TestLegacyAccountsKeepTheirRevocation:
    """
    The earlier build revoked tokens with `password_changed_at`. Accounts that already changed
    their password under it must not have those revoked tokens become valid again just because
    the new scheme reads a missing `token_version` as 0 — and tokens without a `tv` claim are
    also version 0, which is exactly what such an old token looks like.
    """

    def test_token_revoked_by_the_previous_build_does_not_become_valid_again(self, client, fake_db):
        changed = datetime.now(timezone.utc) - timedelta(minutes=1)
        uid = _make_legacy_user(client, fake_db, "legacy1@example.com", changed)
        revoked = _forge(uid, iat=changed - timedelta(minutes=5))      # issued before the change, no `tv`
        assert client.get(f"{API}/auth/me", headers=_bearer(revoked)).status_code == 401

    def test_legacy_same_second_token_stays_revoked(self, client, fake_db):
        second = datetime.now(timezone.utc).replace(microsecond=0)
        uid = _make_legacy_user(client, fake_db, "legacy2@example.com", second + timedelta(milliseconds=900))
        issued_earlier_in_the_same_second = _forge(uid, iat=second)
        assert client.get(f"{API}/auth/me", headers=_bearer(issued_earlier_in_the_same_second)).status_code == 401

    def test_token_the_previous_build_issued_after_the_change_must_sign_in_again(self, client, fake_db):
        """Cannot be told apart from a revoked one without trusting `iat` (the original flaw), so it is retired too."""
        changed = datetime.now(timezone.utc) - timedelta(minutes=1)
        uid = _make_legacy_user(client, fake_db, "legacy3@example.com", changed)
        later = _forge(uid, iat=changed + timedelta(seconds=30))
        assert client.get(f"{API}/auth/me", headers=_bearer(later)).status_code == 401
        assert client.get(f"{API}/auth/me", headers=_bearer(_login(client, "legacy3@example.com"))).status_code == 200

    @pytest.mark.parametrize("migrated", [False, True], ids=["before-migration-runs", "after-migration-ran"])
    def test_fresh_login_gets_the_current_version_and_works(self, client, fake_db, migrated):
        changed = datetime.now(timezone.utc) - timedelta(minutes=1)
        uid = _make_legacy_user(client, fake_db, f"legacy4-{migrated}@example.com", changed)
        if migrated:
            auth_service.migrate_legacy_token_versions(fake_db)
        token = _login(client, f"legacy4-{migrated}@example.com")
        assert _claims(token)["tv"] == 1
        assert client.get(f"{API}/auth/me", headers=_bearer(token)).status_code == 200
        revoked = _forge(uid, iat=changed - timedelta(minutes=5))
        assert client.get(f"{API}/auth/me", headers=_bearer(revoked)).status_code == 401   # still revoked

    @pytest.mark.parametrize("migrated", [False, True], ids=["before-migration-runs", "after-migration-ran"])
    def test_a_further_password_change_revokes_every_earlier_token(self, client, fake_db, migrated):
        email = f"legacy5-{migrated}@example.com"
        changed = datetime.now(timezone.utc) - timedelta(minutes=1)
        uid = _make_legacy_user(client, fake_db, email, changed)
        if migrated:
            auth_service.migrate_legacy_token_versions(fake_db)
        revoked_by_old_build = _forge(uid, iat=changed - timedelta(minutes=5))
        first_login = _login(client, email)                                     # version 1
        assert _claims(first_login)["tv"] == 1

        response = client.post(f"{API}/users/me/change-password", json=_PW_CHANGE, headers=_bearer(first_login))
        assert response.status_code == 200
        second = response.json()["data"]["access_token"]
        assert _claims(second)["tv"] == 2                                       # NOT 1: must differ from first_login
        assert [client.get(f"{API}/auth/me", headers=_bearer(t)).status_code
                for t in (revoked_by_old_build, first_login, second)] == [401, 401, 200]

        again = {"current_password": "BrandNew-Pass-456", "new_password": "Third-Pass-789!", "confirm_new_password": "Third-Pass-789!"}
        third = client.post(f"{API}/users/me/change-password", json=again, headers=_bearer(second)).json()["data"]["access_token"]
        assert _claims(third)["tv"] == 3
        assert [client.get(f"{API}/auth/me", headers=_bearer(t)).status_code for t in (second, third)] == [401, 200]

    def test_password_change_directly_on_a_legacy_record_never_reuses_a_live_version(self, client, fake_db):
        """The first change after the upgrade, with no login in between and no migration run."""
        email = "legacy6@example.com"
        uid = _make_legacy_user(client, fake_db, email, datetime.now(timezone.utc) - timedelta(minutes=1))
        # a token minted for version 1 (what a login on this record yields) ...
        v1 = create_access_token(subject=str(uid), token_version=1)
        assert client.get(f"{API}/auth/me", headers=_bearer(v1)).status_code == 200
        # ... must die when the password changes, even though the stored field was missing.
        fresh = client.post(f"{API}/users/me/change-password", json=_PW_CHANGE, headers=_bearer(v1)).json()["data"]["access_token"]
        assert client.get(f"{API}/auth/me", headers=_bearer(v1)).status_code == 401
        assert client.get(f"{API}/auth/me", headers=_bearer(fresh)).status_code == 200

    @pytest.mark.parametrize("migrated", [False, True], ids=["before-migration-runs", "after-migration-ran"])
    def test_same_second_scenario_still_holds_for_a_migrated_account(self, client, fake_db, monkeypatch, migrated):
        import app.core.security as security_module
        email = f"legacy7-{migrated}@example.com"
        _make_legacy_user(client, fake_db, email, datetime.now(timezone.utc) - timedelta(minutes=1))
        if migrated:
            auth_service.migrate_legacy_token_versions(fake_db)
        frozen = datetime.now(timezone.utc).replace(microsecond=250_000)

        class _Frozen(datetime):
            @classmethod
            def now(cls, tz=None):
                return frozen

        monkeypatch.setattr(security_module, "datetime", _Frozen)
        old = _login(client, email)
        fresh = client.post(f"{API}/users/me/change-password", json=_PW_CHANGE, headers=_bearer(old)).json()["data"]["access_token"]
        assert _claims(old)["iat"] == _claims(fresh)["iat"]                       # identical second
        assert client.get(f"{API}/auth/me", headers=_bearer(old)).status_code == 401
        assert client.get(f"{API}/auth/me", headers=_bearer(fresh)).status_code == 200


class TestLegacyMigration:
    def _users(self, client, fake_db):
        now = datetime.now(timezone.utc)
        legacy = _make_legacy_user(client, fake_db, "m-legacy@example.com", now - timedelta(days=3))
        modern = _make_legacy_user(client, fake_db, "m-modern@example.com", now - timedelta(days=3))
        fake_db[Collections.USERS].update_one({"_id": modern}, {"$set": {"token_version": 4}})
        _register_and_login(client, email="m-never@example.com")
        null_changed = _make_legacy_user(client, fake_db, "m-null@example.com", now)
        fake_db[Collections.USERS].update_one({"_id": null_changed}, {"$set": {"password_changed_at": None}})
        users = fake_db[Collections.USERS]
        return {name: users.find_one({"email": f"m-{name}@example.com"})["_id"] for name in ("legacy", "modern", "never", "null")}

    def test_backfills_only_legacy_accounts_and_is_idempotent(self, client, fake_db):
        ids = self._users(client, fake_db)
        assert auth_service.migrate_legacy_token_versions(fake_db) == 1
        read = lambda k: fake_db[Collections.USERS].find_one({"_id": ids[k]})
        assert read("legacy")["token_version"] == 1
        assert read("modern")["token_version"] == 4          # an existing version is never lowered or rewritten
        assert "token_version" not in read("never")           # never changed their password: stays at the implicit 0
        assert "token_version" not in read("null")            # a null timestamp is not a password change
        assert auth_service.migrate_legacy_token_versions(fake_db) == 0
        assert read("legacy")["token_version"] == 1

    def test_accounts_that_never_changed_their_password_keep_their_existing_sessions(self, client, fake_db):
        token = _register_and_login(client, email="m-keep@example.com")
        auth_service.migrate_legacy_token_versions(fake_db)
        assert client.get(f"{API}/auth/me", headers=_bearer(token)).status_code == 200

    def test_the_migration_runs_as_part_of_database_setup(self, client, fake_db):
        import app.main as main_module
        uid = _make_legacy_user(client, fake_db, "m-startup@example.com", datetime.now(timezone.utc))
        main_module._ensure_database_ready(fake_db)
        assert fake_db[Collections.USERS].find_one({"_id": uid})["token_version"] == 1