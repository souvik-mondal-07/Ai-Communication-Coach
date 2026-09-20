"""
Voice <-> communication integration: a voice transcript becomes an ordinary
communication message (same session, roleplay, history, evaluation) with
stored speaking metrics. Gemini is always mocked.
"""

from __future__ import annotations

import json

import pytest

from app.core.dependencies import get_communication_service, get_evaluation_service
from app.main import app
from app.services.ai.ai_service import AIProviderError, AIResponse
from app.services.communication.communication_service import CommunicationService
from app.services.communication.evaluation_service import EvaluationService
from tests.test_communication import _get_scenario_id, _register_and_login

SPOKEN = "Um, I wanted to ask how you prepared for your cybersecurity internship, basically."
AUDIO_META = {
    "duration_seconds": 6.0,
    "language": "en",
    "pause_metrics": {
        "pause_count": 2,
        "long_pauses": 1,
        "average_pause_seconds": 1.5,
        "longest_pause_seconds": 2.1,
        "total_pause_seconds": 3.0,
        "granularity": "word",
    },
}

EVAL_JSON = {
    "overall_score": 78, "clarity_score": 82, "grammar_score": 74, "vocabulary_score": 76,
    "professionalism_score": 80, "confidence_score": 72, "relevance_score": 85,
    "conversation_flow_score": 76, "strengths": ["Relevant."], "weaknesses": ["Grammar."],
    "improvements": ["Shorter sentences."], "better_responses": [], "summary": "Good.",
}
SPEAKING_JSON = {
    "clarity_score": 90, "grammar_score": 80, "vocabulary_score": 70, "conciseness_score": 85,
    "strengths": ["Clear question."], "improvements": ["Add context."], "summary": "Clear.",
}


class RecordingAI:
    """Scripted AI that records every call; can be told to fail the speaking step."""

    def __init__(self):
        self.calls = []
        self.speaking_response = json.dumps(SPEAKING_JSON)
        self.speaking_error = None

    async def generate_response(self, *, user_message, system_prompt=None, history=None, **_):
        prompt = system_prompt or ""
        self.calls.append(prompt)
        if "communication coach evaluating" in prompt:
            return AIResponse(text=json.dumps(EVAL_JSON), model="fake")
        if "spoken-communication coach" in prompt:
            if self.speaking_error:
                raise self.speaking_error
            return AIResponse(text=self.speaking_response, model="fake")
        return AIResponse(text="Thanks for asking! I started with networking.", model="fake")

    def count(self, marker):
        return sum(1 for c in self.calls if marker in c)


@pytest.fixture()
def ai():
    fake = RecordingAI()
    comm = CommunicationService(ai_service_=fake)
    evaluation = EvaluationService(ai_service_=fake)
    app.dependency_overrides[get_communication_service] = lambda: comm
    app.dependency_overrides[get_evaluation_service] = lambda: evaluation
    yield fake
    app.dependency_overrides.pop(get_communication_service, None)
    app.dependency_overrides.pop(get_evaluation_service, None)


def _start(client, headers, token):
    scenario_id = _get_scenario_id(client, token)
    response = client.post("/api/v1/communication/sessions", json={"scenario_id": scenario_id}, headers=headers)
    return response.json()["data"]["session_id"]


def _setup(client, email):
    token = _register_and_login(client, email=email)
    headers = {"Authorization": f"Bearer {token}"}
    return token, headers, _start(client, headers, token)


def _send_voice(client, headers, session_id, text=SPOKEN, **overrides):
    body = {"message": text, "input_type": "voice", "audio_metadata": AUDIO_META, **overrides}
    return client.post(f"/api/v1/communication/sessions/{session_id}/message", json=body, headers=headers)


class TestVoiceMessages:
    def test_transcript_becomes_a_voice_message_with_metrics(self, client, ai):
        _, headers, sid = _setup(client, "vm1@example.com")
        response = _send_voice(client, headers, sid, transcript_edited=True)
        assert response.status_code == 200
        data = response.json()["data"]
        assert "started with networking" in data["reply"]
        va = data["voice_analysis"]
        assert va["word_count"] == 13
        assert va["speaking_rate_wpm"] == 130  # 13 words / 6 s
        assert va["total_filler_words"] == 2  # um, basically
        assert va["pause_count"] == 2 and va["longest_pause_seconds"] == 2.1
        assert va["transcript_edited"] is True

    def test_voice_message_is_persisted_and_returned_with_history(self, client, ai):
        _, headers, sid = _setup(client, "vm2@example.com")
        _send_voice(client, headers, sid)
        detail = client.get(f"/api/v1/communication/sessions/{sid}", headers=headers).json()["data"]
        user_msgs = [m for m in detail["messages"] if m["role"] == "user"]
        assert user_msgs[-1]["input_type"] == "voice"
        assert user_msgs[-1]["content"] == SPOKEN
        assert user_msgs[-1]["voice_analysis"]["speaking_rate_wpm"] == 130
        assistant = [m for m in detail["messages"] if m["role"] == "assistant"][-1]
        assert assistant["input_type"] == "text"

    def test_voice_roleplay_prompt_asks_for_speakable_replies(self, client, ai):
        _, headers, sid = _setup(client, "vm3@example.com")
        _send_voice(client, headers, sid)
        assert ai.count("VOICE MODE") == 1

    def test_text_messages_are_unchanged(self, client, ai):
        _, headers, sid = _setup(client, "vm4@example.com")
        response = client.post(
            f"/api/v1/communication/sessions/{sid}/message", json={"message": "Hello there"}, headers=headers
        )
        assert response.status_code == 200
        assert "voice_analysis" not in response.json()["data"]
        assert ai.count("VOICE MODE") == 0
        detail = client.get(f"/api/v1/communication/sessions/{sid}", headers=headers).json()["data"]
        last_user = [m for m in detail["messages"] if m["role"] == "user"][-1]
        assert last_user["input_type"] == "text" and last_user["voice_analysis"] is None

    def test_voice_message_without_audio_metadata_still_works(self, client, ai):
        _, headers, sid = _setup(client, "vm5@example.com")
        response = client.post(
            f"/api/v1/communication/sessions/{sid}/message",
            json={"message": SPOKEN, "input_type": "voice"},
            headers=headers,
        )
        va = response.json()["data"]["voice_analysis"]
        assert va["speaking_rate_wpm"] is None and va["pause_count"] is None  # not invented
        assert va["word_count"] == 13

    def test_invalid_metadata_is_rejected(self, client, ai):
        _, headers, sid = _setup(client, "vm6@example.com")
        base = {"message": SPOKEN, "input_type": "voice"}
        url = f"/api/v1/communication/sessions/{sid}/message"
        bad_metas = [
            {"duration_seconds": -5},
            {"duration_seconds": 0},
            {"duration_seconds": 999999},
            {"duration_seconds": 5, "pause_metrics": {"pause_count": 1, "long_pauses": 5}},
            {"duration_seconds": 5, "language": "en<script>"},
        ]
        for meta in bad_metas:
            assert client.post(url, json={**base, "audio_metadata": meta}, headers=headers).status_code == 422, meta
        # metadata on a text message makes no sense
        assert (
            client.post(url, json={"message": "hi", "audio_metadata": AUDIO_META}, headers=headers).status_code == 422
        )
        assert client.post(url, json={**base, "input_type": "video"}, headers=headers).status_code == 422

    def test_session_ownership_is_enforced(self, client, ai):
        _, _, sid = _setup(client, "vm7-owner@example.com")
        other = {"Authorization": f"Bearer {_register_and_login(client, email='vm7-other@example.com')}"}
        assert _send_voice(client, other, sid).status_code == 403

    def test_requires_authentication(self, client, ai):
        _, _, sid = _setup(client, "vm8@example.com")
        response = client.post(
            f"/api/v1/communication/sessions/{sid}/message", json={"message": "x", "input_type": "voice"}
        )
        assert response.status_code == 401

    def test_completed_session_rejects_voice_messages(self, client, ai):
        _, headers, sid = _setup(client, "vm9@example.com")
        _send_voice(client, headers, sid)
        client.post(f"/api/v1/communication/sessions/{sid}/complete", headers=headers)
        assert _send_voice(client, headers, sid).status_code == 409

    def test_ai_failure_does_not_store_a_half_message(self, client, ai, monkeypatch):
        _, headers, sid = _setup(client, "vm10@example.com")

        async def boom(**_):
            raise AIProviderError("down")

        monkeypatch.setattr(ai, "generate_response", boom)
        response = _send_voice(client, headers, sid)
        assert response.status_code >= 500 or response.status_code == 503
        detail = client.get(f"/api/v1/communication/sessions/{sid}", headers=headers).json()["data"]
        assert all(m.get("input_type") != "voice" for m in detail["messages"])


class TestVoiceEvaluation:
    def test_completed_voice_session_has_voice_summary(self, client, ai):
        _, headers, sid = _setup(client, "ve1@example.com")
        _send_voice(client, headers, sid)
        _send_voice(client, headers, sid, text="I mean, I studied networking and Linux at home.")
        response = client.post(f"/api/v1/communication/sessions/{sid}/complete", headers=headers)
        assert response.status_code == 200
        evaluation = response.json()["data"]["evaluation"]
        assert evaluation["overall_score"] == 78  # Step 7 evaluation untouched
        vs = evaluation["voice_summary"]
        assert vs["voice_message_count"] == 2
        assert vs["ai_feedback_available"] is True
        assert vs["grammar_score"] == 80
        assert 0 <= vs["clarity_score"] <= 100
        assert vs["total_filler_words"] >= 3
        assert vs["average_speaking_rate_wpm"] is not None
        assert vs["longest_pause_seconds"] == 2.1
        assert "Clear question." in vs["strengths"]
        assert vs["summary"] == "Clear."
        assert ai.count("spoken-communication coach") == 1

    def test_voice_summary_is_persisted(self, client, ai):
        _, headers, sid = _setup(client, "ve2@example.com")
        _send_voice(client, headers, sid)
        client.post(f"/api/v1/communication/sessions/{sid}/complete", headers=headers)
        detail = client.get(f"/api/v1/communication/sessions/{sid}", headers=headers).json()["data"]
        assert detail["evaluation"]["voice_summary"]["voice_message_count"] == 1
        # completing again is idempotent and does not call the AI again
        client.post(f"/api/v1/communication/sessions/{sid}/complete", headers=headers)
        assert ai.count("spoken-communication coach") == 1

    def test_speaking_ai_failure_still_completes_with_metrics(self, client, ai):
        ai.speaking_error = AIProviderError("down")
        _, headers, sid = _setup(client, "ve3@example.com")
        _send_voice(client, headers, sid)
        response = client.post(f"/api/v1/communication/sessions/{sid}/complete", headers=headers)
        assert response.status_code == 200
        vs = response.json()["data"]["evaluation"]["voice_summary"]
        assert vs["ai_feedback_available"] is False
        assert vs["grammar_score"] is None
        assert vs["total_words_spoken"] == 13

    def test_malformed_speaking_ai_response_degrades_gracefully(self, client, ai):
        ai.speaking_response = "Sure! Here you go: not json"
        _, headers, sid = _setup(client, "ve4@example.com")
        _send_voice(client, headers, sid)
        response = client.post(f"/api/v1/communication/sessions/{sid}/complete", headers=headers)
        assert response.status_code == 200
        assert response.json()["data"]["evaluation"]["voice_summary"]["ai_feedback_available"] is False

    def test_text_only_session_has_no_voice_summary_and_no_extra_ai_call(self, client, ai):
        _, headers, sid = _setup(client, "ve5@example.com")
        client.post(
            f"/api/v1/communication/sessions/{sid}/message", json={"message": "Hello there"}, headers=headers
        )
        response = client.post(f"/api/v1/communication/sessions/{sid}/complete", headers=headers)
        assert response.status_code == 200
        assert "voice_summary" not in response.json()["data"]["evaluation"]
        assert ai.count("spoken-communication coach") == 0

    def test_mixed_session_only_scores_spoken_messages(self, client, ai):
        _, headers, sid = _setup(client, "ve6@example.com")
        client.post(
            f"/api/v1/communication/sessions/{sid}/message",
            json={"message": "A typed message with um and basically"},
            headers=headers,
        )
        _send_voice(client, headers, sid)
        vs = client.post(f"/api/v1/communication/sessions/{sid}/complete", headers=headers).json()["data"][
            "evaluation"
        ]["voice_summary"]
        assert vs["voice_message_count"] == 1
        assert vs["total_words_spoken"] == 13  # the typed message isn't counted as speech
