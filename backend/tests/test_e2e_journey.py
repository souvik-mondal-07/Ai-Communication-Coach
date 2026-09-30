"""
Step 12 — API-level user journey.

Walks one user through the real routes and services (mongomock instead of a
live MongoDB; scripted fakes instead of Gemini/Whisper/TTS):

    register -> login -> mentor -> topics -> CTF list -> progress ->
    recalculate -> weaknesses -> recommendations -> "logout" -> login again
    -> history/progress still there.

The AI-generation steps (practice / CTF / communication / interview / pressure
sessions) are exercised in their own module suites; here their *results* are
seeded directly so this test verifies the hand-off into Progress and that data
survives a new login, without needing one giant shared AI fake.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.core.dependencies import get_mentor_service, get_progress_service
from app.db.collections import Collections
from app.main import app
from app.services.progress.progress_service import ProgressService
from tests.test_communication import VALID_PASSWORD
from tests.test_mentor import _FakeMentorService
from tests.test_progress import _FakeAIService, _insert_ctf_session, _insert_practice_session

API = "/api/v1"
EMAIL = "journey@example.com"


def test_full_user_journey(client, fake_db):
    mentor = _FakeMentorService(response="XSS lets attackers run script in a victim's browser.")
    progress_ai = _FakeAIService()
    app.dependency_overrides[get_mentor_service] = lambda: mentor
    app.dependency_overrides[get_progress_service] = lambda: ProgressService(ai_service_=progress_ai)
    try:
        # Register, then log in explicitly (registration does not sign in).
        reg = client.post(f"{API}/auth/register", json={"name": "Journey", "email": EMAIL, "password": VALID_PASSWORD})
        assert reg.status_code == 201
        login = client.post(f"{API}/auth/login", json={"email": EMAIL, "password": VALID_PASSWORD})
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}
        me = client.get(f"{API}/auth/me", headers=headers).json()["data"]
        assert me["user"]["email"] == EMAIL

        # Mentor question.
        chat = client.post(f"{API}/mentor/chat", headers=headers, json={"message": "What is XSS?", "mode": "explain", "level": "beginner"})
        assert chat.status_code == 200 and "XSS" in chat.json()["data"]["response"]

        # Cybersecurity topics are browsable.
        topics = client.get(f"{API}/cybersecurity/topics", headers=headers).json()["data"]
        assert topics
        slug = (topics["topics"] if isinstance(topics, dict) else topics)[0]["slug"]
        assert client.get(f"{API}/cybersecurity/topics/{slug}", headers=headers).status_code == 200

        # Nothing done yet: empty states, not errors.
        assert client.get(f"{API}/ctf/sessions", headers=headers).json()["data"]["total"] == 0
        assert client.get(f"{API}/progress/overview", headers=headers).json()["data"]["has_activity"] is False

        # Completed work from several modules (their generation is tested elsewhere).
        uid = fake_db[Collections.USERS].find_one({"email": EMAIL})["_id"]
        for score in (20, 25, 30):
            _insert_practice_session(fake_db, user_id=uid, category="Cryptography", score=score)
        _insert_ctf_session(fake_db, user_id=uid, category="Web", hints_used=3)

        # The minimal seed helper omits list-view fields real sessions always have.
        fake_db[Collections.PRACTICE_SESSIONS].update_many({}, {"$set": {"topic_slug": "cryptography-basics", "total_questions": 5}})

        fake_db[Collections.CTF_SESSIONS].update_many({}, {"$set": {"platform": "picoCTF", "difficulty": "easy", "created_at": datetime.now(timezone.utc)}})

        # Recalculate twice: must not duplicate recommendations.
        assert client.post(f"{API}/progress/recalculate", headers=headers).status_code == 200
        first = client.get(f"{API}/progress/recommendations", headers=headers).json()["data"]
        assert client.post(f"{API}/progress/recalculate", headers=headers).status_code == 200
        second = client.get(f"{API}/progress/recommendations", headers=headers).json()["data"]
        assert len(second) == len(first) > 0

        weaknesses = client.get(f"{API}/progress/weaknesses", headers=headers).json()["data"]
        assert weaknesses
        overview = client.get(f"{API}/progress/overview", headers=headers).json()["data"]
        assert overview["has_activity"] is True
        assert client.get(f"{API}/progress/profile", headers=headers).status_code == 200

        rec_id = second[0].get("id") or second[0].get("recommendation_id") or second[0]["_id"]
        assert client.post(f"{API}/progress/recommendations/{rec_id}/complete", headers=headers).status_code == 200

        # "Logout" is client-side (token discarded): without it, access is gone.
        assert client.get(f"{API}/progress/overview").status_code == 401

        # Login again: everything is still there.
        relogin = client.post(f"{API}/auth/login", json={"email": EMAIL, "password": VALID_PASSWORD})
        headers2 = {"Authorization": f"Bearer {relogin.json()['data']['access_token']}"}
        assert client.get(f"{API}/progress/overview", headers=headers2).json()["data"]["has_activity"] is True
        assert client.get(f"{API}/cybersecurity/practice/history", headers=headers2).json()["data"]["total"] == 3
        assert client.get(f"{API}/ctf/sessions", headers=headers2).json()["data"]["total"] == 1
        assert len(client.get(f"{API}/progress/weaknesses", headers=headers2).json()["data"]) == len(weaknesses)
    finally:
        app.dependency_overrides.pop(get_mentor_service, None)
        app.dependency_overrides.pop(get_progress_service, None)
