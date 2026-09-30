"""
Pressure & Nervousness Training API tests (Step 10).

Reuses `ScriptedInterviewAI` from `test_interview.py` -- the pressure service
calls the exact same `QuestionService` / `InterviewEvaluationService`
prompts, so the existing scripted fake AI already understands every prompt
kind (question / follow_up / technical / communication / final) it will see.
Gemini itself is always mocked; no real network calls are made.
"""

from __future__ import annotations

import pytest

from app.core.dependencies import get_interview_service, get_pressure_service
from app.db.collections import Collections
from app.main import app
from app.services.interview.interview_service import InterviewService
from app.services.pressure.pressure_service import PressureService
from tests.test_communication import _register_and_login
from tests.test_interview import ScriptedInterviewAI


def _auth(client, email):
    return {"Authorization": f"Bearer {_register_and_login(client, email=email)}"}


@pytest.fixture()
def ai():
    """Wires the scripted fake AI into the pressure service (deterministic RNG)."""
    fake = ScriptedInterviewAI()
    service = PressureService(ai_service_=fake)
    app.dependency_overrides[get_pressure_service] = lambda: service
    yield fake
    app.dependency_overrides.pop(get_pressure_service, None)


def _start(client, headers, **overrides):
    body = {"pressure_level": 1, "mode": "interview", "interview_type": "cybersecurity",
             "difficulty": "intermediate", "question_count": 5, "input_mode": "text", **overrides}
    return client.post("/api/v1/pressure/sessions", json=body, headers=headers)


def _new(client, email, **overrides):
    headers = _auth(client, email)
    response = _start(client, headers, **overrides)
    assert response.status_code == 201, response.text
    return headers, response.json()["data"]["session_id"], response.json()["data"]


def _respond(client, headers, sid, text="A thorough answer covering the key ideas in reasonable detail.", **extra):
    return client.post(f"/api/v1/pressure/sessions/{sid}/response", json={"answer": text, **extra}, headers=headers)


def _get(client, headers, sid):
    return client.get(f"/api/v1/pressure/sessions/{sid}", headers=headers)


def _finish(client, headers, sid, limit=80):
    """Answer until the session completes; returns the last response's data."""
    last = None
    for _ in range(limit):
        response = _respond(client, headers, sid)
        assert response.status_code == 200, response.text
        last = response.json()["data"]
        if last["session_complete"]:
            return last
    raise AssertionError("pressure session never completed")


# --- Config -------------------------------------------------------------------


class TestConfig:
    def test_config_requires_authentication(self, client):
        assert client.get("/api/v1/pressure/config").status_code == 401

    def test_returns_five_levels_without_internal_probabilities(self, client):
        response = client.get("/api/v1/pressure/config", headers=_auth(client, "cfg@example.com"))
        assert response.status_code == 200
        levels = response.json()["data"]["levels"]
        assert [lvl["pressure_level"] for lvl in levels] == [1, 2, 3, 4, 5]
        for lvl in levels:
            assert "label" in lvl and "description" in lvl and "characteristics" in lvl
            # Internal randomization knobs must never be exposed to the client.
            assert "follow_up_frequency" not in lvl
            assert "interruption_frequency" not in lvl


# --- Session creation -----------------------------------------------------------


class TestCreation:
    def test_requires_authentication(self, client, ai):
        assert client.post("/api/v1/pressure/sessions", json={}).status_code == 401
        assert client.get("/api/v1/pressure/sessions").status_code == 401

    def test_creates_session_and_returns_first_question(self, client, ai, fake_db):
        _, sid, data = _new(client, "create1@example.com")
        assert data["question_number"] == 1 and data["question"]
        assert data["pressure_level"] == 1 and data["status"] == "in_progress"
        doc = fake_db[Collections.PRESSURE_SESSIONS].find_one({})
        assert str(doc["_id"]) == sid
        assert doc["status"] == "in_progress"
        assert doc["config"]["time_limit_seconds"] is None  # level 1 = no time limit
        assert len(doc["topic_plan"]) == 5

    @pytest.mark.parametrize("level", [1, 2, 3, 4, 5])
    def test_every_pressure_level_can_start(self, client, ai, level):
        headers = _auth(client, f"level-{level}@example.com")
        response = _start(client, headers, pressure_level=level)
        assert response.status_code == 201, response.text
        assert response.json()["data"]["pressure_level"] == level

    def test_communication_mode_forces_hr_topic_pool(self, client, ai, fake_db):
        _, sid, _ = _new(client, "comm-mode@example.com", mode="communication")
        doc = fake_db[Collections.PRESSURE_SESSIONS].find_one({})
        assert doc["interview_type"] == "hr"
        assert doc["mode"] == "communication"

    @pytest.mark.parametrize(
        "field, value",
        [("pressure_level", 0), ("pressure_level", 6), ("pressure_level", "high"),
         ("difficulty", "expert"), ("question_count", 7), ("input_mode", "video")],
    )
    def test_invalid_configuration_is_rejected(self, client, ai, field, value):
        response = _start(client, _auth(client, "bad@example.com"), **{field: value})
        assert response.status_code == 422
        assert ai.calls == []

    def test_client_supplied_user_id_is_rejected(self, client, ai):
        headers = _auth(client, "extra@example.com")
        assert _start(client, headers, user_id="507f1f77bcf86cd799439011").status_code == 422

    def test_session_belongs_to_the_authenticated_user(self, client, ai, fake_db):
        headers, _, _ = _new(client, "owner-check@example.com")
        me = client.get("/api/v1/auth/me", headers=headers).json()["data"]
        doc = fake_db[Collections.PRESSURE_SESSIONS].find_one({})
        assert str(doc["user_id"]) == me["user"]["id"]

    def test_ai_failure_creates_no_session(self, client, ai, fake_db):
        ai.fail = {"question"}
        response = _start(client, _auth(client, "fail-start@example.com"))
        assert response.status_code == 503
        assert response.json()["error_code"] == "AI_SERVICE_UNAVAILABLE"
        assert fake_db[Collections.PRESSURE_SESSIONS].count_documents({}) == 0


# --- Ownership / not-found / not-active -----------------------------------------


class TestOwnership:
    def test_other_users_session_is_forbidden(self, client, ai):
        _, sid, _ = _new(client, "user-a@example.com")
        other = _auth(client, "user-b@example.com")
        assert _get(client, other, sid).status_code == 403
        assert _respond(client, other, sid).status_code == 403

    def test_unknown_session_is_not_found(self, client, ai):
        headers = _auth(client, "unknown@example.com")
        assert _get(client, headers, "507f1f77bcf86cd799439011").status_code == 404

    def test_completed_session_rejects_further_responses(self, client, ai):
        headers, sid, _ = _new(client, "finished@example.com", question_count=5)
        _finish(client, headers, sid)
        response = _respond(client, headers, sid)
        assert response.status_code == 409
        assert response.json()["error_code"] == "SESSION_NOT_ACTIVE"


# --- Responses, timing, and completion ------------------------------------------


class TestResponses:
    def test_session_completes_after_question_count_and_hides_scores_meanwhile(self, client, ai):
        headers, sid, _ = _new(client, "complete1@example.com", question_count=5, pressure_level=1)
        result = _finish(client, headers, sid)
        assert result["final_evaluation"] is not None
        assert result["final_evaluation"]["overall_score"] is not None
        # Pressure-specific fields must be present and non-diagnostic.
        fe = result["final_evaluation"]
        assert "pressure_handling_score" in fe
        assert "pressure_indicators" in fe
        assert "comparison" in fe

    def test_scores_are_hidden_while_in_progress(self, client, ai):
        headers, sid, _ = _new(client, "hidden@example.com")
        _respond(client, headers, sid)
        session = _get(client, headers, sid).json()["data"]
        assert session["questions"][0]["technical_score"] is None
        assert session["questions"][0]["communication_score"] is None
        # But pressure indicators (metrics, not judgments) are still visible.
        assert session["questions"][0]["pressure_indicators"] is not None

    def test_timed_out_blank_answer_is_accepted_not_discarded(self, client, ai):
        headers, sid, _ = _new(client, "timeout@example.com")
        response = _respond(client, headers, sid, text="", timed_out=True)
        assert response.status_code == 200, response.text
        session = _get(client, headers, sid).json()["data"]
        assert session["questions"][0]["timed_out"] is True
        assert session["questions"][0]["answer"]  # never silently discarded / left None

    def test_blank_answer_without_timeout_is_rejected(self, client, ai):
        headers, sid, _ = _new(client, "blank@example.com")
        response = _respond(client, headers, sid, text="")
        assert response.status_code == 422

    def test_response_duration_is_server_measured_not_trusted_from_client(self, client, ai, fake_db):
        headers, sid, _ = _new(client, "timing@example.com")
        # Client claims an implausible near-zero duration; the server measures
        # its own elapsed wall-clock time and does not blindly trust this.
        _respond(client, headers, sid, response_duration_seconds=0.001)
        doc = fake_db[Collections.PRESSURE_SESSIONS].find_one({})
        stored = doc["questions"][0]["response_duration_seconds"]
        assert stored is not None and stored >= 0

    def test_text_mode_still_produces_pressure_indicators(self, client, ai):
        headers, sid, _ = _new(client, "textmetrics@example.com", input_mode="text")
        data = _respond(client, headers, sid).json()["data"]
        assert data["pressure_indicators"] is not None
        assert "word_count" in data["pressure_indicators"]

    def test_voice_mode_reuses_step8_analysis(self, client, ai):
        headers, sid, _ = _new(client, "voicemetrics@example.com", input_mode="voice")
        data = _respond(
            client, headers, sid, input_type="voice",
            audio_metadata={"duration_seconds": 12.0, "language": "en"},
        ).json()["data"]
        assert data["pressure_indicators"]["speaking_rate_wpm"] is not None

    def test_ai_failure_does_not_consume_the_answer(self, client, ai, fake_db):
        headers, sid, _ = _new(client, "aifail@example.com")
        ai.fail = {"technical"}
        response = _respond(client, headers, sid)
        assert response.status_code == 503
        doc = fake_db[Collections.PRESSURE_SESSIONS].find_one({})
        assert doc["questions"][0]["answer"] is None
        ai.fail = set()
        assert _respond(client, headers, sid).status_code == 200


# --- Self-report -----------------------------------------------------------------


class TestSelfReport:
    def test_self_report_is_stored(self, client, ai):
        headers, sid, _ = _new(client, "selfreport@example.com")
        response = client.post(
            f"/api/v1/pressure/sessions/{sid}/self-report",
            json={"difficulty": "challenging", "note": "The follow-ups caught me off guard."},
            headers=headers,
        )
        assert response.status_code == 200, response.text
        session = _get(client, headers, sid).json()["data"]
        assert session["self_reported_difficulty"] == "challenging"
        assert session["self_report_note"]

    def test_invalid_self_report_value_is_rejected(self, client, ai):
        headers, sid, _ = _new(client, "badreport@example.com")
        response = client.post(
            f"/api/v1/pressure/sessions/{sid}/self-report", json={"difficulty": "terrified"}, headers=headers
        )
        assert response.status_code == 422


# --- History ----------------------------------------------------------------------


class TestHistory:
    def test_history_lists_only_the_caller_s_own_sessions(self, client, ai):
        headers_a, _, _ = _new(client, "hist-a@example.com")
        headers_b, _, _ = _new(client, "hist-b@example.com")
        list_a = client.get("/api/v1/pressure/sessions", headers=headers_a).json()["data"]
        assert list_a["total"] == 1
        list_b = client.get("/api/v1/pressure/sessions", headers=headers_b).json()["data"]
        assert list_b["total"] == 1
        assert list_a["sessions"][0]["session_id"] != list_b["sessions"][0]["session_id"]


# --- Comparison with normal (non-pressure) practice ------------------------------


class TestComparison:
    def test_no_baseline_available_when_no_prior_interview_exists(self, client, ai):
        headers, sid, _ = _new(client, "nobaseline@example.com", question_count=5)
        result = _finish(client, headers, sid)
        comparison = result["final_evaluation"]["comparison"]
        assert comparison["baseline_available"] is False
        assert "No baseline available yet" in comparison["message"]

    def test_baseline_available_after_a_completed_interview(self, client, ai):
        interview_fake = ScriptedInterviewAI()
        interview = InterviewService(ai_service_=interview_fake)
        app.dependency_overrides[get_interview_service] = lambda: interview
        headers = _auth(client, "withbaseline@example.com")
        try:
            start = client.post(
                "/api/v1/interview/sessions",
                json={"interview_type": "cybersecurity", "difficulty": "intermediate", "question_count": 5, "mode": "text"},
                headers=headers,
            )
            assert start.status_code == 201, start.text
            isid = start.json()["data"]["session_id"]
            for _ in range(40):
                r = client.post(f"/api/v1/interview/sessions/{isid}/answer",
                                 json={"answer": "A solid, detailed answer."}, headers=headers)
                if r.json()["data"]["interview_complete"]:
                    break
        finally:
            app.dependency_overrides.pop(get_interview_service, None)

        # Same user now starts a pressure session -- it should see the
        # completed interview above as a baseline for comparison.
        response = _start(client, headers, question_count=5)
        assert response.status_code == 201, response.text
        sid = response.json()["data"]["session_id"]
        result = _finish(client, headers, sid)
        comparison = result["final_evaluation"]["comparison"]
        assert comparison["baseline_available"] is True
        assert comparison["normal_practice"]["technical_score"] is not None

    def test_pressure_indicators_never_use_diagnostic_language(self, client, ai):
        headers, sid, _ = _new(client, "nolabel@example.com", question_count=5)
        result = _finish(client, headers, sid)
        indicators = result["final_evaluation"]["pressure_indicators"]
        text = " ".join(indicators).lower()
        for banned in ("anxious", "anxiety", "nervous", "you have a disorder"):
            assert banned not in text
