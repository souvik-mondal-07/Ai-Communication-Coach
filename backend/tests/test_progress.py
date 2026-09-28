"""
Tests for Step 11 — Progress & Personal AI Profile.

Mirrors the project's existing test conventions: `fake_db` (mongomock) +
`client` fixtures from `conftest.py`, `_register_and_login` from
`tests/test_communication.py`, and a scripted fake AI service so no real
Gemini call is ever made.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId

from app.core.dependencies import get_progress_service
from app.db.collections import Collections
from app.main import app
from app.services.progress.profile_service import _ProfileSummaryOut  # noqa: F401 (import sanity)
from app.services.progress.progress_service import ProgressService
from tests.test_communication import VALID_PASSWORD, _register_and_login


def _auth(client, email):
    return {"Authorization": f"Bearer {_register_and_login(client, email=email)}"}


def _user_id(fake_db, email) -> ObjectId:
    user = fake_db[Collections.USERS].find_one({"email": email})
    assert user is not None
    return user["_id"]


class _FakeAIService:
    """Deterministic stand-in for AIService; never calls the network."""

    def __init__(self, *, fail: bool = False, payload: dict | None = None):
        self.fail = fail
        self.payload = payload or {
            "summary": "Solid progress overall.",
            "strengths": ["Linux"],
            "improvement_areas": ["Networking"],
            "suggested_next_focus": ["Practice networking fundamentals."],
        }
        self.calls = 0

    async def generate_response(self, *, user_message, system_prompt=None, history=None, **_):
        self.calls += 1
        if self.fail:
            from app.services.ai.ai_service import AIProviderError

            raise AIProviderError("boom")

        class _Result:
            text = json.dumps(self.payload)

        return _Result()


@pytest.fixture()
def ai():
    fake = _FakeAIService()
    service = ProgressService(ai_service_=fake)
    app.dependency_overrides[get_progress_service] = lambda: service
    yield fake
    app.dependency_overrides.pop(get_progress_service, None)


def _insert_practice_session(fake_db, *, user_id, category, score, days_ago=0, topic_title="Topic"):
    now = datetime.now(timezone.utc) - timedelta(days=days_ago)
    fake_db[Collections.PRACTICE_SESSIONS].insert_one(
        {
            "user_id": user_id,
            "topic_title": topic_title,
            "category": category,
            "difficulty": "intermediate",
            "started_at": now,
            "completed_at": now,
            "status": "completed",
            "score": score,
        }
    )


def _insert_ctf_session(fake_db, *, user_id, category, status="completed", hints_used=0, title="Challenge"):
    now = datetime.now(timezone.utc)
    fake_db[Collections.CTF_SESSIONS].insert_one(
        {
            "user_id": user_id,
            "title": title,
            "category": category,
            "status": status,
            "hints_used": hints_used,
            "updated_at": now,
            "completed_at": now if status == "completed" else None,
        }
    )


def _insert_communication_session(fake_db, *, user_id, clarity=90, overall=90):
    now = datetime.now(timezone.utc)
    fake_db[Collections.COMMUNICATION_SESSIONS].insert_one(
        {
            "user_id": user_id,
            "scenario_title": "Scenario",
            "category": "teachers",
            "status": "completed",
            "completed_at": now,
            "evaluation": {
                "overall_score": overall,
                "clarity_score": clarity,
                "grammar_score": 90,
                "vocabulary_score": 90,
                "professionalism_score": 90,
                "confidence_score": 90,
                "relevance_score": 90,
                "conversation_flow_score": 90,
            },
        }
    )


def _insert_interview_session(fake_db, *, user_id, topic, avg_score, questions=3, overall=70, technical=70, communication=70):
    now = datetime.now(timezone.utc)
    fake_db[Collections.INTERVIEW_SESSIONS].insert_one(
        {
            "user_id": user_id,
            "interview_type": "cybersecurity",
            "status": "completed",
            "completed_at": now,
            "final_evaluation": {
                "overall_score": overall,
                "technical_score": technical,
                "communication_score": communication,
                "topic_scores": [{"topic": topic, "label": topic, "average_score": avg_score, "questions": questions}],
            },
        }
    )


def _insert_pressure_session(fake_db, *, user_id, handling=40, control=40, overall=50):
    now = datetime.now(timezone.utc)
    fake_db[Collections.PRESSURE_SESSIONS].insert_one(
        {
            "user_id": user_id,
            "pressure_level": 2,
            "status": "completed",
            "completed_at": now,
            "final_evaluation": {
                "overall_score": overall,
                "pressure_handling_score": handling,
                "response_control_score": control,
                "pressure_indicators": ["Frequent pauses"],
            },
        }
    )


# --- Overview -----------------------------------------------------------------


class TestOverview:
    def test_requires_auth(self, client):
        response = client.get("/api/v1/progress/overview")
        assert response.status_code in (401, 403)

    def test_no_activity_is_empty_but_well_shaped(self, client, ai):
        headers = _auth(client, "overview-empty@example.com")
        response = client.get("/api/v1/progress/overview", headers=headers)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["has_activity"] is False
        assert data["strengths"] == []
        assert data["weaknesses"] == []
        assert data["communication_performance"] is None
        assert data["interview_performance"] is None
        assert data["pressure_performance"] is None

    def test_activity_produces_correct_aggregation(self, client, ai, fake_db):
        email = "overview-active@example.com"
        headers = _auth(client, email)
        uid = _user_id(fake_db, email)

        for score in (90, 92, 88):
            _insert_practice_session(fake_db, user_id=uid, category="Linux", score=score)

        response = client.get("/api/v1/progress/overview", headers=headers)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["has_activity"] is True
        assert data["cybersecurity_performance"]["categories_practiced"] == 1
        assert data["cybersecurity_performance"]["average_score"] == 90
        assert "Linux" in data["strengths"]
        assert data["session_counts"]["practice_sessions"]["completed"] == 3


# --- Skills --------------------------------------------------------------------


class TestSkills:
    def test_category_aggregation(self, client, ai, fake_db):
        email = "skills-user@example.com"
        headers = _auth(client, email)
        uid = _user_id(fake_db, email)

        _insert_practice_session(fake_db, user_id=uid, category="Networking", score=40)
        _insert_practice_session(fake_db, user_id=uid, category="Networking", score=50)
        _insert_practice_session(fake_db, user_id=uid, category="Networking", score=45)
        _insert_practice_session(fake_db, user_id=uid, category="Linux", score=95)
        _insert_practice_session(fake_db, user_id=uid, category="Linux", score=93)
        _insert_practice_session(fake_db, user_id=uid, category="Linux", score=97)

        response = client.get("/api/v1/progress/skills", headers=headers)
        data = response.json()["data"]
        by_category = {row["category"]: row for row in data["cybersecurity_skills"]}
        assert by_category["Networking"]["status"] == "weak"
        assert by_category["Linux"]["status"] == "strong"

    def test_ctf_breakdown_has_no_fabricated_score(self, client, ai, fake_db):
        email = "ctf-user@example.com"
        headers = _auth(client, email)
        uid = _user_id(fake_db, email)
        _insert_ctf_session(fake_db, user_id=uid, category="web_security", status="completed")
        _insert_ctf_session(fake_db, user_id=uid, category="web_security", status="abandoned")

        response = client.get("/api/v1/progress/skills", headers=headers)
        data = response.json()["data"]
        ctf_row = data["ctf_activity"][0]
        assert "score" not in ctf_row
        assert ctf_row["attempts"] == 2
        assert ctf_row["completed"] == 1


# --- Trends ----------------------------------------------------------------


class TestTrends:
    def test_insufficient_data(self, client, ai, fake_db):
        email = "trend-thin@example.com"
        headers = _auth(client, email)
        uid = _user_id(fake_db, email)
        _insert_practice_session(fake_db, user_id=uid, category="Linux", score=80)

        response = client.get("/api/v1/progress/trends?period=30d", headers=headers)
        data = response.json()["data"]
        assert data["dimensions"]["technical"]["trend"] == "insufficient_data"

    def test_rejects_invalid_period(self, client, ai):
        headers = _auth(client, "trend-bad-period@example.com")
        response = client.get("/api/v1/progress/trends?period=999d", headers=headers)
        assert response.status_code == 422

    def test_multiple_records_produce_a_trend(self, client, ai, fake_db):
        email = "trend-rich@example.com"
        headers = _auth(client, email)
        uid = _user_id(fake_db, email)
        # Improving scores over several distinct weeks within the last 90 days.
        for weeks_ago, score in [(8, 50), (6, 55), (4, 75), (2, 85), (0, 90)]:
            _insert_practice_session(fake_db, user_id=uid, category="Linux", score=score, days_ago=weeks_ago * 7)

        response = client.get("/api/v1/progress/trends?period=90d", headers=headers)
        data = response.json()["data"]
        technical = data["dimensions"]["technical"]
        assert len(technical["points"]) >= 2
        assert technical["trend"] == "improving"


# --- Weakness detection ------------------------------------------------------


class TestWeaknessDetection:
    def test_repeated_low_scores_are_flagged(self, client, ai, fake_db):
        email = "weak-repeated@example.com"
        headers = _auth(client, email)
        uid = _user_id(fake_db, email)
        for score in (30, 35, 40):
            _insert_practice_session(fake_db, user_id=uid, category="Cryptography", score=score)

        response = client.get("/api/v1/progress/weaknesses", headers=headers)
        areas = {w["area"] for w in response.json()["data"]}
        assert "Cryptography" in areas

    def test_insufficient_attempts_not_flagged(self, client, ai, fake_db):
        email = "weak-insufficient@example.com"
        headers = _auth(client, email)
        uid = _user_id(fake_db, email)
        # Only two low-scoring attempts -- below MIN_ATTEMPTS (3).
        _insert_practice_session(fake_db, user_id=uid, category="Cryptography", score=20)
        _insert_practice_session(fake_db, user_id=uid, category="Cryptography", score=25)

        response = client.get("/api/v1/progress/weaknesses", headers=headers)
        areas = {w["area"] for w in response.json()["data"]}
        assert "Cryptography" not in areas

    def test_strong_performance_is_not_a_weakness(self, client, ai, fake_db):
        email = "weak-strong@example.com"
        headers = _auth(client, email)
        uid = _user_id(fake_db, email)
        for score in (85, 90, 95):
            _insert_practice_session(fake_db, user_id=uid, category="Linux", score=score)

        response = client.get("/api/v1/progress/weaknesses", headers=headers)
        areas = {w["area"] for w in response.json()["data"]}
        assert "Linux" not in areas


# --- Recommendations ---------------------------------------------------------


class TestRecommendations:
    def test_generation_from_weakness(self, client, ai, fake_db):
        email = "rec-gen@example.com"
        headers = _auth(client, email)
        uid = _user_id(fake_db, email)
        for score in (30, 35, 25):
            _insert_practice_session(fake_db, user_id=uid, category="Cryptography", score=score)

        response = client.get("/api/v1/progress/recommendations", headers=headers)
        recs = response.json()["data"]
        assert any(r["area"] == "Cryptography" and "Repeated low scores" in r["reason"] for r in recs)

    def test_completion_updates_state(self, client, ai, fake_db):
        email = "rec-complete@example.com"
        headers = _auth(client, email)
        uid = _user_id(fake_db, email)
        for score in (30, 35, 25):
            _insert_practice_session(fake_db, user_id=uid, category="Cryptography", score=score)
        client.get("/api/v1/progress/recommendations", headers=headers)

        recs = client.get("/api/v1/progress/recommendations", headers=headers).json()["data"]
        rec_id = recs[0]["_id"]

        response = client.post(f"/api/v1/progress/recommendations/{rec_id}/complete", headers=headers)
        assert response.status_code == 200
        assert response.json()["data"]["completed"] is True

        active = client.get("/api/v1/progress/recommendations", headers=headers).json()["data"]
        assert all(r["_id"] != rec_id for r in active)

    def test_ownership_enforced_on_completion(self, client, ai, fake_db):
        owner_headers = _auth(client, "rec-owner@example.com")
        other_headers = _auth(client, "rec-other@example.com")
        owner_id = _user_id(fake_db, "rec-owner@example.com")
        for score in (30, 35, 25):
            _insert_practice_session(fake_db, user_id=owner_id, category="Cryptography", score=score)

        recs = client.get("/api/v1/progress/recommendations", headers=owner_headers).json()["data"]
        rec_id = recs[0]["_id"]

        response = client.post(f"/api/v1/progress/recommendations/{rec_id}/complete", headers=other_headers)
        assert response.status_code == 403

    def test_completing_unknown_recommendation_is_404(self, client, ai):
        headers = _auth(client, "rec-missing@example.com")
        response = client.post(
            f"/api/v1/progress/recommendations/{ObjectId()}/complete", headers=headers
        )
        assert response.status_code == 404


# --- Profile -----------------------------------------------------------------


class TestProfile:
    def test_profile_generation_via_recalculate(self, client, ai, fake_db):
        email = "profile-gen@example.com"
        headers = _auth(client, email)
        uid = _user_id(fake_db, email)
        for score in (90, 92, 88):
            _insert_practice_session(fake_db, user_id=uid, category="Linux", score=score)
        for score in (30, 35, 25):
            _insert_practice_session(fake_db, user_id=uid, category="Cryptography", score=score)

        recalc = client.post("/api/v1/progress/recalculate", headers=headers)
        assert recalc.status_code == 200
        assert recalc.json()["data"]["ai_summary_generated"] is True

        profile = client.get("/api/v1/progress/profile", headers=headers).json()["data"]
        assert "Linux" in profile["technical_profile"]["strong_areas"]
        assert "Cryptography" in profile["technical_profile"]["weak_areas"]
        assert profile["ai_summary"]["summary"]

    def test_profile_ownership(self, client, ai, fake_db):
        owner_headers = _auth(client, "profile-owner@example.com")
        other_headers = _auth(client, "profile-other@example.com")
        owner_id = _user_id(fake_db, "profile-owner@example.com")
        for score in (90, 92, 88):
            _insert_practice_session(fake_db, user_id=owner_id, category="Linux", score=score)
        client.post("/api/v1/progress/recalculate", headers=owner_headers)

        other_profile = client.get("/api/v1/progress/profile", headers=other_headers).json()["data"]
        assert other_profile["technical_profile"]["strong_areas"] == []

    def test_no_unsupported_psychological_claims(self, client, fake_db):
        """When the AI is unreachable, the profile is still returned with ai_summary=None -- never a fabricated claim."""
        failing = _FakeAIService(fail=True)
        service = ProgressService(ai_service_=failing)
        app.dependency_overrides[get_progress_service] = lambda: service
        try:
            email = "profile-no-ai@example.com"
            headers = _auth(client, email)
            uid = _user_id(fake_db, email)
            for score in (90, 92, 88):
                _insert_practice_session(fake_db, user_id=uid, category="Linux", score=score)

            recalc = client.post("/api/v1/progress/recalculate", headers=headers)
            assert recalc.status_code == 200
            assert recalc.json()["data"]["ai_summary_generated"] is False

            profile = client.get("/api/v1/progress/profile", headers=headers).json()["data"]
            assert profile["ai_summary"] is None
        finally:
            app.dependency_overrides.pop(get_progress_service, None)


# --- Security ------------------------------------------------------------------


class TestSecurity:
    def test_user_a_cannot_read_user_b_progress(self, client, ai, fake_db):
        a_headers = _auth(client, "sec-a@example.com")
        b_headers = _auth(client, "sec-b@example.com")
        a_id = _user_id(fake_db, "sec-a@example.com")
        for score in (20, 25, 30):
            _insert_practice_session(fake_db, user_id=a_id, category="Cryptography", score=score)

        b_overview = client.get("/api/v1/progress/overview", headers=b_headers).json()["data"]
        assert b_overview["has_activity"] is False
        assert b_overview["weaknesses"] == []

    def test_user_a_cannot_read_user_b_weaknesses_or_recommendations(self, client, ai, fake_db):
        a_headers = _auth(client, "sec-c@example.com")
        b_headers = _auth(client, "sec-d@example.com")
        a_id = _user_id(fake_db, "sec-c@example.com")
        for score in (20, 25, 30):
            _insert_practice_session(fake_db, user_id=a_id, category="Cryptography", score=score)
        client.get("/api/v1/progress/weaknesses", headers=a_headers)

        b_weaknesses = client.get("/api/v1/progress/weaknesses", headers=b_headers).json()["data"]
        b_recs = client.get("/api/v1/progress/recommendations", headers=b_headers).json()["data"]
        assert b_weaknesses == []
        assert b_recs == []

    def test_no_user_id_query_param_can_impersonate(self, client, ai, fake_db):
        a_headers = _auth(client, "sec-e@example.com")
        b_headers = _auth(client, "sec-f@example.com")
        b_id = _user_id(fake_db, "sec-f@example.com")
        for score in (90, 92, 88):
            _insert_practice_session(fake_db, user_id=b_id, category="Linux", score=score)

        # Even if a client tries to pass another user's id, the route never
        # reads a user_id from the request -- only from the JWT.
        response = client.get("/api/v1/progress/overview?user_id=someone-else", headers=a_headers)
        data = response.json()["data"]
        assert data["has_activity"] is False


# --- Mentor context integration ------------------------------------------------


class TestMentorContext:
    def test_no_profile_means_no_context(self, fake_db):
        uid = str(ObjectId())
        assert ProgressService().get_mentor_context(fake_db, user_id=uid) is None

    def test_context_is_compact_and_built_from_profile(self, client, ai, fake_db):
        email = "ctx-user@example.com"
        headers = _auth(client, email)
        uid = _user_id(fake_db, email)
        for score in (90, 92, 88):
            _insert_practice_session(fake_db, user_id=uid, category="Linux", score=score)
        for score in (30, 35, 25):
            _insert_practice_session(fake_db, user_id=uid, category="Cryptography", score=score)
        client.post("/api/v1/progress/recalculate", headers=headers)

        context = ProgressService().get_mentor_context(fake_db, user_id=str(uid))
        assert set(context) == {
            "technical_level", "strong_areas", "weak_areas", "recent_focus", "recommended_focus",
        }
        assert "Linux" in context["strong_areas"]
        assert "Cryptography" in context["weak_areas"]

    def test_mentor_route_forwards_context_when_profile_exists(self, client, ai, fake_db):
        from app.core.dependencies import get_mentor_service

        class _Recorder:
            last = None

            async def chat(self, **kwargs):
                _Recorder.last = kwargs
                from app.services.mentor.mentor_service import MentorChatResult
                return MentorChatResult(response="ok", mode=kwargs["mode"], level=kwargs["level"])

        email = "ctx-route@example.com"
        headers = _auth(client, email)
        uid = _user_id(fake_db, email)
        for score in (30, 35, 25):
            _insert_practice_session(fake_db, user_id=uid, category="Cryptography", score=score)
        client.post("/api/v1/progress/recalculate", headers=headers)

        app.dependency_overrides[get_mentor_service] = lambda: _Recorder()
        try:
            response = client.post("/api/v1/mentor/chat", json={"message": "Teach me crypto"}, headers=headers)
        finally:
            app.dependency_overrides.pop(get_mentor_service, None)
        assert response.status_code == 200
        assert "Cryptography" in _Recorder.last["mentor_context"]["weak_areas"]

    def test_mentor_service_appends_context_to_system_prompt(self):
        import asyncio
        from app.services.mentor.mentor_service import MentorService

        seen = {}

        class _AI:
            async def generate_response(self, *, user_message, history=None, system_prompt=None, **_):
                seen["prompt"] = system_prompt
                class R:
                    text = "hi"
                return R()

        ctx = {"technical_level": "developing", "strong_areas": ["Linux"], "weak_areas": ["Cryptography"],
               "recent_focus": [], "recommended_focus": []}
        asyncio.run(MentorService(_AI()).chat(message="x", mode="learn", level="intermediate", mentor_context=ctx))
        assert "Cryptography" in seen["prompt"]
        asyncio.run(MentorService(_AI()).chat(message="x", mode="learn", level="intermediate"))
        assert "LEARNER CONTEXT" not in seen["prompt"]
