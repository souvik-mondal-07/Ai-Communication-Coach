"""
Voice conversation tests (Step 13).

Whisper, Gemini and TTS are all faked: audio -> transcript -> AI -> TTS is
exercised end to end without any model, network, or real provider.

A spoken turn is two requests: `/transcribe` (audio -> text, Whisper once) and
`/respond` (text -> AI reply -> TTS). `_respond` below performs both in order,
exactly as the app does automatically; `_transcribe` / `_process` call one step.
"""

from __future__ import annotations

import json
import time
from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.core.dependencies import get_voice_conversation_service
from app.db.collections import Collections
from app.main import app
from app.services.ai.ai_service import AIProviderError, AIResponse
from app.services.communication.communication_service import CommunicationService
from app.services.communication.evaluation_service import EvaluationService
from app.services.interview.interview_service import InterviewService
from app.services.pressure.pressure_service import PressureService
from app.services.voice.speech_to_text import (
    MalformedAudioError,
    TranscribedSegment,
    TranscribedWord,
    TranscriptionFailedError,
    TranscriptionResult,
)
from app.services.voice.text_to_speech import TextToSpeechService, TTSProviderError, SynthesizedAudio
from app.services.voice.voice_service import VoiceService
from app.services.voice_conversation.audio_store import AudioStore
from app.services.voice_conversation.conversation_engine import (
    ConversationEngine,
    build_history,
    to_spoken_text,
)
from app.services.voice_conversation.conversation_service import VoiceConversationService, build_summary
from app.services.voice_conversation.prompts import END_TOKEN, build_voice_system_prompt
from tests.test_interview import ScriptedInterviewAI
from tests.test_voice_api import FakeSTT, RecordingProvider, _login
from tests.test_voice_communication import EVAL_JSON, SPEAKING_JSON
from tests.test_voice_stt import WAV

BASE = "/api/v1/voice-conversation"
TRANSCRIPT = "A SIEM collects and correlates logs from many sources to detect suspicious activity."


def _result(text=TRANSCRIPT, duration=6.0):
    words = [TranscribedWord(0.0, 0.5, "a"), TranscribedWord(3.0, 3.4, "b")]
    return TranscriptionResult(
        text=text, language="en", duration_seconds=duration, segments=[TranscribedSegment(0, 3.4, text, words)]
    )


class VoiceAI(ScriptedInterviewAI):
    """Interview/pressure prompts behave as in Step 9; adds free-form voice + communication replies."""

    def __init__(self):
        super().__init__()
        self.voice_calls: list[dict] = []
        self.voice_reply = "Good start. Can you explain how correlation rules work?"
        self.voice_fail = False
        self.comm_fail = False

    async def generate_response(self, *, user_message, system_prompt=None, history=None, **kw):
        prompt = system_prompt or ""
        if "live spoken conversation" in prompt:
            self.voice_calls.append({"system": prompt, "user": user_message, "history": list(history or [])})
            if self.voice_fail:
                raise AIProviderError("down")
            return AIResponse(text=self.voice_reply, model="fake")
        if "communication coach evaluating" in prompt:
            return AIResponse(text=json.dumps(EVAL_JSON), model="fake")
        if "spoken-communication coach" in prompt:
            return AIResponse(text=json.dumps(SPEAKING_JSON), model="fake")
        if self.kind_of(system_prompt, user_message) == "other":
            # Communication roleplay chat.
            self.voice_calls.append({"system": prompt, "user": user_message, "history": list(history or [])})
            if self.comm_fail:
                raise AIProviderError("down")
            return AIResponse(text="Thanks for asking! I started with networking.", model="fake")
        return await super().generate_response(
            user_message=user_message, system_prompt=system_prompt, history=history, **kw
        )


@pytest.fixture()
def vc(tmp_path, monkeypatch):
    """A VoiceConversationService built entirely from fakes; yields a handle."""
    monkeypatch.setattr(settings, "voice_temp_dir", str(tmp_path))
    ai = VoiceAI()
    handle = SimpleNamespace(
        ai=ai, stt=FakeSTT(result=_result()), provider=RecordingProvider(), tmp=tmp_path, store=AudioStore(ttl_seconds=60)
    )
    voice = VoiceService(stt=handle.stt, tts=TextToSpeechService(provider=handle.provider))
    engine = ConversationEngine(
        ai_service_=ai,
        interview_service_=InterviewService(ai_service_=ai),
        pressure_service_=PressureService(ai_service_=ai),
        communication_service_=CommunicationService(ai_service_=ai),
        evaluation_service_=EvaluationService(ai_service_=ai),
    )
    handle.service = VoiceConversationService(voice=voice, engine=engine, audio=handle.store)
    app.dependency_overrides[get_voice_conversation_service] = lambda: handle.service
    yield handle
    app.dependency_overrides.pop(get_voice_conversation_service, None)


def _create(client, headers, **body):
    body = {"mode": "cybersecurity", "difficulty": "intermediate", **body}
    return client.post(f"{BASE}/sessions", json=body, headers=headers)


def _new_session(client, headers, **body) -> str:
    response = _create(client, headers, **body)
    assert response.status_code == 201, response.text
    return response.json()["data"]["session"]["session_id"]


def _start(client, headers, sid):
    return client.post(f"{BASE}/sessions/{sid}/start", headers=headers)


def _transcribe(client, headers, sid, data=WAV, content_type="audio/wav", **fields):
    """Step 1 of a turn: audio -> transcript. No AI, no TTS, nothing saved."""
    return client.post(
        f"{BASE}/sessions/{sid}/transcribe",
        files={"audio": ("x.wav", data, content_type)},
        data={k: str(v) for k, v in fields.items()},
        headers=headers,
    )


def _process(client, headers, sid, transcript, expected_turn, **extra):
    """Step 2 of a turn (and the retry path): transcript -> AI reply. JSON only, never audio."""
    return client.post(
        f"{BASE}/sessions/{sid}/respond",
        json={"transcript": transcript, "expected_turn": expected_turn, **extra},
        headers=headers,
    )


def _current_turn(client, headers, sid) -> int:
    body = client.get(f"{BASE}/sessions/{sid}", headers=headers).json()
    return (body.get("data") or {}).get("session", {}).get("user_turn_count", 0)


def _respond(client, headers, sid, data=WAV, content_type="audio/wav", **fields):
    """
    A whole spoken turn: transcribe, then submit the transcript automatically (no manual
    "send"), forwarding what the transcription measured -- the same thing the app does.
    Returns the failing/empty transcription response, or the AI-turn response.
    """
    expected_turn = fields.pop("expected_turn", None)
    if expected_turn is None:
        expected_turn = _current_turn(client, headers, sid)
    response_seconds = fields.pop("response_seconds", None)
    transcribed = _transcribe(client, headers, sid, data, content_type, expected_turn=expected_turn)
    if transcribed.status_code != 200 or transcribed.json()["data"]["is_empty"]:
        return transcribed
    t = transcribed.json()["data"]
    extra = {k: t[k] for k in ("duration_seconds", "language", "pause_metrics") if t.get(k) is not None}
    if response_seconds is not None:
        extra["response_seconds"] = float(response_seconds)
    return _process(client, headers, sid, t["transcript"], expected_turn, **extra)


def _active(client, headers, **body) -> str:
    sid = _new_session(client, headers, **body)
    assert _start(client, headers, sid).status_code == 200
    return sid


def _leftover_temp_files(handle) -> list:
    return [p for p in handle.tmp.iterdir()]


# --- Session creation ---------------------------------------------------------------------


class TestCreateSession:
    def test_requires_authentication(self, client, vc):
        assert client.post(f"{BASE}/sessions", json={"mode": "general"}).status_code == 401
        assert client.get(f"{BASE}/sessions").status_code == 401
        assert client.get(f"{BASE}/config").status_code == 401

    @pytest.mark.parametrize("mode", ["general", "cybersecurity", "communication", "interview", "pressure"])
    def test_every_mode_is_creatable(self, client, vc, mode):
        headers = _login(client)
        response = _create(client, headers, mode=mode)
        assert response.status_code == 201
        session = response.json()["data"]["session"]
        assert session["mode"] == mode and session["status"] == "created"
        assert session["messages"] == [] and session["turn_count"] == 0

    def test_practice_requires_topic(self, client, vc):
        headers = _login(client)
        assert _create(client, headers, mode="practice").status_code == 422
        ok = _create(client, headers, mode="practice", topic="web security")
        assert ok.status_code == 201 and ok.json()["data"]["session"]["topic"] == "web security"

    @pytest.mark.parametrize(
        "body",
        [
            {"mode": "nonsense"},
            {"mode": "general", "difficulty": "expert"},
            {"mode": "general", "user_id": "507f1f77bcf86cd799439011"},  # unknown field: no smuggled owner
            {"mode": "general", "question_count": 5},  # option for another mode
            {"mode": "interview", "pressure_level": 3},
            {"mode": "pressure", "pressure_level": 9},
            {"mode": "interview", "question_count": 7},
            {"mode": "general", "topic": "x" * 500},
            {"mode": "communication", "scenario_slug": "../etc/passwd"},
        ],
    )
    def test_invalid_requests_rejected(self, client, vc, body):
        headers = _login(client)
        assert client.post(f"{BASE}/sessions", json=body, headers=headers).status_code == 422

    def test_unknown_scenario_is_404(self, client, vc):
        headers = _login(client)
        assert _create(client, headers, mode="communication", scenario_slug="does-not-exist").status_code == 404

    def test_owner_is_the_authenticated_user(self, client, fake_db, vc):
        headers = _login(client)
        me = client.get("/api/v1/auth/me", headers=headers).json()["data"]
        sid = _new_session(client, headers)
        doc = fake_db[Collections.VOICE_CONVERSATION_SESSIONS].find_one()
        assert str(doc["user_id"]) == (me.get("user") or me)["id"] and sid == str(doc["_id"])

    def test_indexes_exist_without_duplicates(self, fake_db, vc):
        vc.service.ensure_indexes(fake_db)
        vc.service.ensure_indexes(fake_db)  # idempotent
        keys = [tuple(i["key"]) for i in fake_db[Collections.VOICE_CONVERSATION_SESSIONS].index_information().values()]
        assert (("user_id", 1), ("started_at", -1)) in keys
        assert (("user_id", 1), ("status", 1)) in keys
        assert len(keys) == len(set(keys))


class TestOwnership:
    def test_other_user_cannot_read_or_use_a_session(self, client, vc):
        a = _login(client, "a@example.com")
        b = _login(client, "b@example.com")
        sid = _active(client, a)
        assert client.get(f"{BASE}/sessions/{sid}", headers=a).status_code == 200
        assert client.get(f"{BASE}/sessions/{sid}", headers=b).status_code == 403
        assert _start(client, b, sid).status_code == 403
        assert _respond(client, b, sid).status_code == 403
        assert client.post(f"{BASE}/sessions/{sid}/end", headers=b).status_code == 403

    def test_listing_only_shows_own_sessions(self, client, vc):
        a = _login(client, "a@example.com")
        b = _login(client, "b@example.com")
        _new_session(client, a)
        _new_session(client, a, mode="general")
        _new_session(client, b)
        data = client.get(f"{BASE}/sessions", headers=a).json()["data"]
        assert data["total"] == 2 and len(data["sessions"]) == 2
        assert all("messages" not in row for row in data["sessions"])
        assert client.get(f"{BASE}/sessions", headers=b).json()["data"]["total"] == 1

    def test_malformed_and_unknown_ids(self, client, vc):
        headers = _login(client)
        assert client.get(f"{BASE}/sessions/not-an-id", headers=headers).status_code == 404
        assert client.get(f"{BASE}/sessions/507f1f77bcf86cd799439011", headers=headers).status_code == 404

    def test_audio_token_is_bound_to_the_user(self, client, vc):
        a = _login(client, "a@example.com")
        b = _login(client, "b@example.com")
        sid = _new_session(client, a)
        url = _start(client, a, sid).json()["data"]["audio_url"]
        assert client.get(url, headers=a).status_code == 200
        assert client.get(url, headers=b).status_code == 404
        assert client.get(url).status_code == 401


# --- Start -------------------------------------------------------------------------------------


class TestStart:
    def test_ai_speaks_first_prompt(self, client, vc):
        headers = _login(client)
        sid = _new_session(client, headers)
        response = _start(client, headers, sid)
        data = response.json()["data"]
        assert response.status_code == 200
        assert data["ai_response"] == vc.ai.voice_reply
        assert data["turn_number"] == 0 and data["conversation_complete"] is False
        assert data["session"]["status"] == "active" and data["session"]["turn_count"] == 1
        assert data["session"]["messages"][0]["role"] == "assistant"
        assert data["session"]["messages"][0]["audio_available"] is True
        audio = client.get(data["audio_url"], headers=headers)
        assert audio.status_code == 200 and audio.content == b"FAKE-MP3"
        assert audio.headers["cache-control"] == "no-store"

    def test_start_is_idempotent_resume(self, client, vc):
        headers = _login(client)
        sid = _new_session(client, headers)
        _start(client, headers, sid)
        again = _start(client, headers, sid).json()["data"]
        assert again["resumed"] is True
        assert len(again["session"]["messages"]) == 1  # no second opening, no new session
        assert len(vc.ai.voice_calls) == 1

    def test_ai_failure_leaves_session_startable(self, client, vc):
        headers = _login(client)
        sid = _new_session(client, headers)
        vc.ai.voice_fail = True
        assert _start(client, headers, sid).status_code == 503
        assert client.get(f"{BASE}/sessions/{sid}", headers=headers).json()["data"]["session"]["status"] == "created"
        vc.ai.voice_fail = False
        assert _start(client, headers, sid).status_code == 200

    def test_tts_failure_does_not_fail_the_turn(self, client, vc):
        headers = _login(client)
        vc.provider.error = TTSProviderError("boom")
        sid = _new_session(client, headers)
        data = _start(client, headers, sid).json()["data"]
        assert data["audio_url"] is None and data["audio_error"] == "TTS_FAILED"
        assert data["ai_response"]
        assert data["session"]["messages"][0]["audio_available"] is False

    def test_tts_not_configured_reports_it(self, client, vc, monkeypatch):
        headers = _login(client)
        monkeypatch.setattr(settings, "tts_provider", "")
        vc.service._voice = VoiceService(stt=vc.stt, tts=TextToSpeechService())
        sid = _new_session(client, headers)
        data = _start(client, headers, sid).json()["data"]
        assert data["audio_url"] is None and data["audio_error"] == "TTS_NOT_CONFIGURED"

    def test_spoken_text_has_no_markdown(self, client, vc):
        headers = _login(client)
        vc.ai.voice_reply = "**Great.** Here:\n- one\n```nmap -sV host```\nWhat is a port?"
        sid = _new_session(client, headers)
        data = _start(client, headers, sid).json()["data"]
        assert "*" not in data["ai_response"] and "```" not in data["ai_response"]
        assert vc.provider.texts and "*" not in vc.provider.texts[0]

    def test_profile_context_reaches_freeform_prompt_only_compactly(self, client, fake_db, vc):
        from bson import ObjectId

        headers = _login(client)
        me = client.get("/api/v1/auth/me", headers=headers).json()["data"]
        uid = (me.get("user") or me)["id"]
        fake_db[Collections.PERSONAL_PROFILES].insert_one(
            {
                "user_id": ObjectId(uid),
                "technical_profile": {"strong_areas": ["Linux"], "weak_areas": ["Cryptography"], "developing_areas": []},
                "recent_focus": ["Web Security"],
                "recommended_focus": [],
                "secret_private_field": "DO-NOT-SEND",
            }
        )
        sid = _new_session(client, headers)
        _start(client, headers, sid)
        system = vc.ai.voice_calls[0]["system"]
        assert "Linux" in system and "Cryptography" in system and "Web Security" in system
        assert "DO-NOT-SEND" not in system
        stored = client.get(f"{BASE}/sessions/{sid}", headers=headers).json()["data"]["session"]
        assert "profile_context" not in stored and "processing_token" not in stored


# --- Respond -------------------------------------------------------------------------------------


class TestRespond:
    def test_full_turn_audio_to_transcript_to_ai_to_tts(self, client, vc):
        headers = _login(client)
        sid = _active(client, headers)
        vc.ai.voice_reply = "Nice. What is the difference between a SIEM and an IDS?"
        response = _respond(client, headers, sid, expected_turn=0)
        assert response.status_code == 200, response.text
        data = response.json()["data"]
        assert data["user_transcript"] == TRANSCRIPT
        assert data["ai_response"] == vc.ai.voice_reply
        assert data["turn_number"] == 1 and data["conversation_complete"] is False
        assert client.get(data["audio_url"], headers=headers).content == b"FAKE-MP3"
        assert vc.provider.texts[-1] == vc.ai.voice_reply
        # Speaking metrics are measured, not invented.
        analysis = data["user_voice_analysis"]
        assert analysis["word_count"] > 5 and analysis["duration_seconds"] == 6.0

        session = client.get(f"{BASE}/sessions/{sid}", headers=headers).json()["data"]["session"]
        assert [m["role"] for m in session["messages"]] == ["assistant", "user", "assistant"]
        assert session["messages"][1]["text"] == TRANSCRIPT and session["messages"][1]["duration_seconds"] == 6.0
        assert session["turn_count"] == 3 and session["user_turn_count"] == 1
        assert _leftover_temp_files(vc) == []

    def test_conversation_memory_is_sent_to_the_model(self, client, vc):
        headers = _login(client)
        sid = _active(client, headers)
        _respond(client, headers, sid)
        vc.stt.result = _result("It watches network traffic for known attack signatures.")
        _respond(client, headers, sid)
        last = vc.ai.voice_calls[-1]
        assert last["user"] == "It watches network traffic for known attack signatures."
        texts = [t.content for t in last["history"]]
        assert TRANSCRIPT in texts and vc.ai.voice_reply in texts
        assert last["history"][0].role == "user"  # a conversation must open with the user

    def test_history_is_bounded(self):
        messages = []
        for i in range(30):
            messages += [
                {"role": "assistant", "text": f"q{i}"},
                {"role": "user", "text": f"a{i}"},
            ]
        history = build_history(messages, max_turns=5)
        # 5 exchanges + the placeholder user turn that lets the window open on the AI's question.
        assert len(history) == 11 and history[0].role == "user" and history[1].content == "q25"
        assert history[-1].content == "a29"

    def test_requires_session_to_be_active(self, client, vc):
        headers = _login(client)
        sid = _new_session(client, headers)  # never started
        assert _respond(client, headers, sid).status_code == 409
        assert vc.stt.paths == []  # nothing was transcribed

    def test_stale_turn_number_is_rejected_without_processing(self, client, vc):
        headers = _login(client)
        sid = _active(client, headers)
        _respond(client, headers, sid, expected_turn=0)
        calls = len(vc.stt.paths)
        assert _respond(client, headers, sid, expected_turn=0).status_code == 409  # duplicate submit
        assert len(vc.stt.paths) == calls

    def test_concurrent_turn_is_refused(self, client, fake_db, vc):
        headers = _login(client)
        sid = _active(client, headers)
        from bson import ObjectId
        from app.services.voice_conversation.session_manager import utcnow

        fake_db[Collections.VOICE_CONVERSATION_SESSIONS].update_one(
            {"_id": ObjectId(sid)}, {"$set": {"processing_token": "other", "processing_since": utcnow()}}
        )
        response = _respond(client, headers, sid)
        assert response.status_code == 409 and response.json()["error_code"] == "SESSION_BUSY"
        assert vc.stt.paths == []

    def test_stale_lock_is_recovered(self, client, fake_db, vc):
        from datetime import timedelta
        from bson import ObjectId
        from app.services.voice_conversation.session_manager import utcnow

        headers = _login(client)
        sid = _active(client, headers)
        fake_db[Collections.VOICE_CONVERSATION_SESSIONS].update_one(
            {"_id": ObjectId(sid)}, {"$set": {"processing_token": "dead", "processing_since": utcnow() - timedelta(minutes=10)}}
        )
        assert _respond(client, headers, sid).status_code == 200

    def test_lock_is_released_after_success_and_failure(self, client, fake_db, vc):
        from bson import ObjectId

        headers = _login(client)
        sid = _active(client, headers)
        vc.ai.voice_fail = True
        assert _respond(client, headers, sid).status_code == 503
        doc = fake_db[Collections.VOICE_CONVERSATION_SESSIONS].find_one({"_id": ObjectId(sid)})
        assert doc["processing_token"] is None
        vc.ai.voice_fail = False
        assert _respond(client, headers, sid).status_code == 200

    def test_end_token_completes_the_conversation(self, client, vc):
        headers = _login(client)
        sid = _active(client, headers)
        vc.ai.voice_reply = f"Goodbye, keep practising! {END_TOKEN}"
        data = _respond(client, headers, sid).json()["data"]
        assert data["conversation_complete"] is True and END_TOKEN not in data["ai_response"]
        assert data["summary"]["turns"] == 1
        session = client.get(f"{BASE}/sessions/{sid}", headers=headers).json()["data"]["session"]
        assert session["status"] == "completed" and session["ended_at"]
        assert _respond(client, headers, sid).status_code == 409

    def test_session_turn_cap_completes_the_session(self, client, vc, monkeypatch):
        monkeypatch.setattr(settings, "voice_conversation_max_session_turns", 2)
        headers = _login(client)
        sid = _active(client, headers)
        assert _respond(client, headers, sid).json()["data"]["conversation_complete"] is False
        assert _respond(client, headers, sid).json()["data"]["conversation_complete"] is True

    def test_recording_longer_than_limit_is_rejected_and_not_saved(self, client, vc, monkeypatch):
        monkeypatch.setattr(settings, "voice_max_recording_seconds", 5)
        headers = _login(client)
        sid = _active(client, headers)
        response = _respond(client, headers, sid)  # fake STT reports 6.0s
        assert response.status_code == 422 and response.json()["error_code"] == "AUDIO_TOO_LONG"
        session = client.get(f"{BASE}/sessions/{sid}", headers=headers).json()["data"]["session"]
        assert session["user_turn_count"] == 0
        assert _leftover_temp_files(vc) == []


class TestAudioValidationAndFailures:
    def test_valid_webm_with_codec_parameter(self, client, vc):
        from tests.test_voice_stt import WEBM_HEADER

        headers = _login(client)
        sid = _active(client, headers)
        response = _respond(client, headers, sid, data=WEBM_HEADER + b"\x00" * 64, content_type="audio/webm;codecs=opus")
        assert response.status_code == 200

    def test_missing_audio_field(self, client, vc):
        headers = _login(client)
        sid = _active(client, headers)
        response = client.post(
            f"{BASE}/sessions/{sid}/transcribe", files={"file": ("x.wav", WAV, "audio/wav")}, headers=headers
        )
        assert response.status_code == 422 and response.json()["error_code"] == "AUDIO_REQUIRED"

    def test_non_multipart_body(self, client, vc):
        headers = _login(client)
        sid = _active(client, headers)
        response = client.post(f"{BASE}/sessions/{sid}/transcribe", json={"a": 1}, headers=headers)
        assert response.status_code in (400, 422)

    def test_empty_audio(self, client, vc):
        headers = _login(client)
        sid = _active(client, headers)
        response = _respond(client, headers, sid, data=b"")
        assert response.status_code == 400 and response.json()["error_code"] == "EMPTY_AUDIO"

    def test_not_audio(self, client, vc):
        headers = _login(client)
        sid = _active(client, headers)
        response = _respond(client, headers, sid, data=b"#!/bin/sh\nrm -rf /\n" * 10, content_type="audio/wav")
        assert response.status_code == 415 and vc.stt.paths == []

    def test_disallowed_content_type(self, client, vc):
        headers = _login(client)
        sid = _active(client, headers)
        assert _respond(client, headers, sid, content_type="text/html").status_code == 415

    def test_oversized_audio(self, client, vc, monkeypatch):
        monkeypatch.setattr(settings, "voice_max_audio_bytes", 1024)
        headers = _login(client)
        sid = _active(client, headers)
        response = _respond(client, headers, sid, data=WAV + b"\x00" * 200_000)
        assert response.status_code == 413 and response.json()["error_code"] == "AUDIO_TOO_LARGE"
        assert vc.stt.paths == []

    def test_unauthenticated_upload_is_rejected(self, client, vc):
        response = client.post(
            f"{BASE}/sessions/507f1f77bcf86cd799439011/transcribe", files={"audio": ("x.wav", WAV, "audio/wav")}
        )
        assert response.status_code == 401

    def test_corrupted_audio(self, client, vc):
        headers = _login(client)
        sid = _active(client, headers)
        vc.stt.error = MalformedAudioError("bad")
        response = _respond(client, headers, sid)
        assert response.status_code == 422 and response.json()["error_code"] == "AUDIO_UNREADABLE"
        assert _leftover_temp_files(vc) == []

    def test_whisper_failure_keeps_session_intact(self, client, vc):
        headers = _login(client)
        sid = _active(client, headers)
        vc.stt.error = TranscriptionFailedError("x")
        response = _respond(client, headers, sid)
        assert response.status_code == 503 and response.json()["error_code"] == "STT_FAILED"
        assert _leftover_temp_files(vc) == []
        vc.stt.error = None
        assert _respond(client, headers, sid, expected_turn=0).status_code == 200  # can just retry

    def test_silence_is_an_empty_transcript_not_an_error(self, client, vc):
        headers = _login(client)
        sid = _active(client, headers)
        vc.stt.result = _result(text="   ")
        data = _transcribe(client, headers, sid, expected_turn=0).json()["data"]
        assert data["is_empty"] is True and data["transcript"] == ""

    def test_gemini_failure_saves_nothing(self, client, vc):
        headers = _login(client)
        sid = _active(client, headers)
        vc.ai.voice_fail = True
        response = _respond(client, headers, sid)
        assert response.status_code == 503 and response.json()["error_code"] == "AI_SERVICE_UNAVAILABLE"
        session = client.get(f"{BASE}/sessions/{sid}", headers=headers).json()["data"]["session"]
        assert session["status"] == "active" and session["user_turn_count"] == 0 and len(session["messages"]) == 1
        assert _leftover_temp_files(vc) == []

    def test_tts_failure_still_returns_text_and_saves_the_turn(self, client, vc):
        headers = _login(client)
        sid = _active(client, headers)
        vc.provider.error = TTSProviderError("down")
        data = _respond(client, headers, sid).json()["data"]
        assert data["audio_url"] is None and data["audio_error"] == "TTS_FAILED" and data["ai_response"]
        session = client.get(f"{BASE}/sessions/{sid}", headers=headers).json()["data"]["session"]
        assert session["user_turn_count"] == 1

    def test_hostile_filename_is_ignored(self, client, vc):
        headers = _login(client)
        sid = _active(client, headers)
        response = client.post(
            f"{BASE}/sessions/{sid}/transcribe",
            files={"audio": ("../../etc/passwd", WAV, "audio/wav")},
            headers=headers,
        )
        assert response.status_code == 200
        assert all("passwd" not in str(p) for p in vc.stt.paths)
        assert _leftover_temp_files(vc) == []

    def test_transcripts_and_audio_are_never_logged(self, client, vc, caplog):
        import logging

        caplog.set_level(logging.DEBUG)
        headers = _login(client)
        sid = _active(client, headers)
        _respond(client, headers, sid)
        logged = caplog.text
        assert "SIEM" not in logged and vc.ai.voice_reply not in logged


# --- Separated flow: STT once, then transcript -> AI --------------------------------------------------------------------


EMPTY_MESSAGE = "I couldn't hear a clear response. Please try again."
BLANKS = ["", "   ", "\n", "\t", " \n\t "]


def _session_view(client, headers, sid) -> dict:
    return client.get(f"{BASE}/sessions/{sid}", headers=headers).json()["data"]["session"]


class TestTranscription:
    # TEST 1
    def test_audio_becomes_a_transcript_and_nothing_else_happens(self, client, vc):
        headers = _login(client)
        sid = _active(client, headers)
        ai_calls, tts_calls = len(vc.ai.voice_calls), len(vc.provider.texts)

        response = _transcribe(client, headers, sid, expected_turn=0)

        assert response.status_code == 200, response.text
        data = response.json()["data"]
        assert data["transcript"] == TRANSCRIPT and data["is_empty"] is False
        assert data["duration_seconds"] == 6.0 and data["language"] == "en"
        assert len(vc.stt.paths) == 1
        # Transcription alone: no Gemini, no TTS, no saved turn.
        assert len(vc.ai.voice_calls) == ai_calls and len(vc.provider.texts) == tts_calls
        session = _session_view(client, headers, sid)
        assert session["user_turn_count"] == 0 and len(session["messages"]) == 1
        assert _leftover_temp_files(vc) == []

    def test_transcription_reveals_no_internals(self, client, vc):
        headers = _login(client)
        sid = _active(client, headers)
        data = _transcribe(client, headers, sid, expected_turn=0).json()["data"]
        assert set(data) == {"transcript", "is_empty", "duration_seconds", "language", "pause_metrics"}

    # TEST 2
    def test_transcript_goes_straight_to_ai_processing_with_no_manual_send(self, client, vc):
        headers = _login(client)
        sid = _active(client, headers)
        ai_before = len(vc.ai.voice_calls)

        # Exactly the two requests the app chains by itself after recording stops.
        t = _transcribe(client, headers, sid, expected_turn=0).json()["data"]
        extra = {k: t[k] for k in ("duration_seconds", "language", "pause_metrics") if t[k] is not None}
        response = _process(client, headers, sid, t["transcript"], 0, **extra)

        assert response.status_code == 200, response.text
        data = response.json()["data"]
        assert data["user_transcript"] == TRANSCRIPT and data["ai_response"] == vc.ai.voice_reply
        assert len(vc.stt.paths) == 1 and len(vc.ai.voice_calls) == ai_before + 1
        assert vc.ai.voice_calls[-1]["user"] == TRANSCRIPT
        assert client.get(data["audio_url"], headers=headers).content == b"FAKE-MP3"
        # The measured duration made the round trip, so the speaking analysis is still real.
        assert data["user_voice_analysis"]["duration_seconds"] == 6.0

    def test_respond_no_longer_accepts_audio(self, client, vc):
        headers = _login(client)
        sid = _active(client, headers)
        response = client.post(
            f"{BASE}/sessions/{sid}/respond", files={"audio": ("x.wav", WAV, "audio/wav")}, headers=headers
        )
        assert response.status_code == 422
        assert vc.stt.paths == []  # the AI endpoint can never trigger Whisper

    def test_recording_longer_than_limit_is_rejected(self, client, vc, monkeypatch):
        monkeypatch.setattr(settings, "voice_max_recording_seconds", 5)
        headers = _login(client)
        sid = _active(client, headers)
        response = _transcribe(client, headers, sid, expected_turn=0)
        assert response.status_code == 422 and response.json()["error_code"] == "AUDIO_TOO_LONG"


class TestEmptyTranscript:
    # TEST 3
    def test_empty_transcript_never_reaches_gemini_or_tts(self, client, vc):
        headers = _login(client)
        sid = _active(client, headers)
        vc.stt.result = _result(text="")
        ai_calls, tts_calls = len(vc.ai.voice_calls), len(vc.provider.texts)

        transcribed = _transcribe(client, headers, sid, expected_turn=0)
        assert transcribed.status_code == 200
        assert transcribed.json()["data"]["is_empty"] is True and transcribed.json()["data"]["transcript"] == ""

        # Even if a client submitted the empty text anyway, the server refuses it with the user-facing message.
        submitted = _process(client, headers, sid, "", 0)
        assert submitted.status_code == 422
        assert submitted.json()["error_code"] == "EMPTY_TRANSCRIPT"
        assert submitted.json()["message"] == EMPTY_MESSAGE

        assert len(vc.ai.voice_calls) == ai_calls and len(vc.provider.texts) == tts_calls
        session = _session_view(client, headers, sid)
        assert session["user_turn_count"] == 0 and len(session["messages"]) == 1  # no AI turn was created

        # The conversation is immediately usable again: record again and it works.
        vc.stt.result = _result()
        assert _respond(client, headers, sid, expected_turn=0).status_code == 200

    # TEST 4
    @pytest.mark.parametrize("blank", BLANKS)
    def test_whitespace_transcript_behaves_like_empty(self, client, vc, blank):
        headers = _login(client)
        sid = _active(client, headers)
        vc.stt.result = _result(text=blank)
        ai_calls, tts_calls = len(vc.ai.voice_calls), len(vc.provider.texts)

        transcribed = _transcribe(client, headers, sid, expected_turn=0).json()["data"]
        assert transcribed["is_empty"] is True and transcribed["transcript"] == ""

        submitted = _process(client, headers, sid, blank, 0)
        assert submitted.status_code == 422 and submitted.json()["error_code"] == "EMPTY_TRANSCRIPT"
        assert EMPTY_MESSAGE in submitted.text
        assert len(vc.ai.voice_calls) == ai_calls and len(vc.provider.texts) == tts_calls
        assert _session_view(client, headers, sid)["user_turn_count"] == 0

    def test_blank_text_from_the_stt_layer_is_also_empty(self, client, vc, monkeypatch):
        from app.services.voice.voice_service import TranscriptionOutcome

        async def blank(*_a, **_k):
            return TranscriptionOutcome(text="  \n ", language="en", duration_seconds=2.0, pause_metrics=None)

        monkeypatch.setattr(vc.service._voice, "transcribe", blank)
        headers = _login(client)
        sid = _active(client, headers)
        data = _transcribe(client, headers, sid, expected_turn=0).json()["data"]
        assert data["is_empty"] is True and data["transcript"] == ""

    def test_null_or_missing_transcript_is_rejected_before_the_ai(self, client, vc):
        headers = _login(client)
        sid = _active(client, headers)
        ai_calls = len(vc.ai.voice_calls)
        for body in ({"transcript": None, "expected_turn": 0}, {"expected_turn": 0}):
            assert client.post(f"{BASE}/sessions/{sid}/respond", json=body, headers=headers).status_code == 422
        assert len(vc.ai.voice_calls) == ai_calls and _session_view(client, headers, sid)["user_turn_count"] == 0

    def test_empty_transcript_check_does_not_bypass_ownership(self, client, vc):
        a = _login(client, "a@example.com")
        b = _login(client, "b@example.com")
        sid = _active(client, a)
        assert _process(client, b, sid, "   ", 0).status_code == 403


class TestTranscriptRetry:
    # TEST 5
    def test_ai_failure_after_stt_leaves_a_retryable_transcript(self, client, vc):
        headers = _login(client)
        sid = _active(client, headers)
        transcript = _transcribe(client, headers, sid, expected_turn=0).json()["data"]["transcript"]

        vc.ai.voice_fail = True
        failed = _process(client, headers, sid, transcript, 0)
        assert failed.status_code == 503 and failed.json()["error_code"] == "AI_SERVICE_UNAVAILABLE"
        session = _session_view(client, headers, sid)
        assert session["user_turn_count"] == 0 and len(session["messages"]) == 1  # nothing half-saved

        # Retry needs only the text: no audio is part of the request, and it succeeds.
        vc.ai.voice_fail = False
        retried = _process(client, headers, sid, transcript, 0)
        assert retried.status_code == 200 and retried.json()["data"]["user_transcript"] == transcript

    # TEST 6 -- the critical one
    def test_retry_does_not_call_stt_again(self, client, vc):
        headers = _login(client)
        sid = _active(client, headers)
        ai_base = len(vc.ai.voice_calls)  # the opening prompt used one

        transcribed = _transcribe(client, headers, sid, expected_turn=0).json()["data"]
        assert len(vc.stt.paths) == 1

        vc.ai.voice_fail = True
        assert _process(client, headers, sid, transcribed["transcript"], 0).status_code == 503
        assert len(vc.stt.paths) == 1 and len(vc.ai.voice_calls) == ai_base + 1  # first Gemini attempt

        vc.ai.voice_fail = False
        retry = _process(client, headers, sid, transcribed["transcript"], 0)  # "Retry response"
        assert retry.status_code == 200

        assert len(vc.stt.paths) == 1  # STT call count did not increase
        assert len(vc.ai.voice_calls) == ai_base + 2  # Gemini was called a second time
        assert _leftover_temp_files(vc) == []

    def test_retry_does_not_call_stt_even_if_it_would_now_fail(self, client, vc):
        headers = _login(client)
        sid = _active(client, headers)
        transcript = _transcribe(client, headers, sid, expected_turn=0).json()["data"]["transcript"]
        vc.ai.voice_fail = True
        _process(client, headers, sid, transcript, 0)
        vc.ai.voice_fail = False
        vc.stt.error = TranscriptionFailedError("whisper is down")  # would break any second STT run
        assert _process(client, headers, sid, transcript, 0).status_code == 200

    # TEST 7
    def test_retry_sends_gemini_the_exact_original_transcript(self, client, vc):
        headers = _login(client)
        sid = _active(client, headers)
        vc.stt.result = _result("I would first check the authentication logs for the suspicious login.")
        transcribed = _transcribe(client, headers, sid, expected_turn=0).json()["data"]
        original = transcribed["transcript"]

        vc.ai.voice_fail = True
        _process(client, headers, sid, original, 0)
        failed_attempt_input = vc.ai.voice_calls[-1]["user"]
        vc.ai.voice_fail = False
        vc.stt.result = _result("SOMETHING ELSE ENTIRELY")  # a second STT run would produce this
        _process(client, headers, sid, original, 0)

        assert failed_attempt_input == original
        assert vc.ai.voice_calls[-1]["user"] == original
        stored = _session_view(client, headers, sid)["messages"][1]
        assert stored["role"] == "user" and stored["text"] == original

    def test_retry_after_a_failed_linked_session_step_also_skips_stt(self, client, fake_db, vc):
        headers = _login(client)
        sid = _active(client, headers, mode="interview")
        transcript = _transcribe(client, headers, sid, expected_turn=0).json()["data"]["transcript"]
        vc.ai.fail = {"technical"}
        assert _process(client, headers, sid, transcript, 0).status_code == 503
        vc.ai.fail = set()
        assert _process(client, headers, sid, transcript, 0).status_code == 200
        assert len(vc.stt.paths) == 1


class TestDuplicateProtection:
    # TEST 8
    def test_duplicate_recording_events_create_one_stt_and_one_ai_turn(self, client, vc):
        headers = _login(client)
        sid = _active(client, headers)
        ai_base = len(vc.ai.voice_calls)

        first = _respond(client, headers, sid, expected_turn=0)
        assert first.status_code == 200

        # The same recording delivered again (double stop / repeated callback): both steps are refused.
        again_stt = _transcribe(client, headers, sid, expected_turn=0)
        again_ai = _process(client, headers, sid, TRANSCRIPT, 0)
        assert again_stt.status_code == 409 and again_stt.json()["error_code"] == "TURN_MISMATCH"
        assert again_ai.status_code == 409 and again_ai.json()["error_code"] == "TURN_MISMATCH"

        assert len(vc.stt.paths) == 1
        assert len(vc.ai.voice_calls) == ai_base + 1
        session = _session_view(client, headers, sid)
        assert session["user_turn_count"] == 1 and [m["role"] for m in session["messages"]] == [
            "assistant", "user", "assistant",
        ]

    def test_transcription_in_flight_blocks_a_second_upload_before_stt(self, client, fake_db, vc):
        from bson import ObjectId

        from app.services.voice_conversation.session_manager import utcnow

        headers = _login(client)
        sid = _active(client, headers)
        fake_db[Collections.VOICE_CONVERSATION_SESSIONS].update_one(
            {"_id": ObjectId(sid)}, {"$set": {"processing_token": "in-flight", "processing_since": utcnow()}}
        )
        response = _transcribe(client, headers, sid, expected_turn=0)
        assert response.status_code == 409 and response.json()["error_code"] == "SESSION_BUSY"
        assert vc.stt.paths == []

    # TEST 9
    def test_same_transcript_and_turn_cannot_create_two_ai_turns(self, client, fake_db, vc):
        headers = _login(client)
        sid = _active(client, headers)
        ai_base = len(vc.ai.voice_calls)

        first = _process(client, headers, sid, TRANSCRIPT, 0)
        second = _process(client, headers, sid, TRANSCRIPT, 0)

        assert first.status_code == 200
        assert second.status_code == 409 and second.json()["error_code"] == "TURN_MISMATCH"
        assert len(vc.ai.voice_calls) == ai_base + 1
        assert _session_view(client, headers, sid)["user_turn_count"] == 1

    def test_ai_processing_in_flight_refuses_a_second_submission(self, client, fake_db, vc):
        from bson import ObjectId

        from app.services.voice_conversation.session_manager import utcnow

        headers = _login(client)
        sid = _active(client, headers)
        ai_base = len(vc.ai.voice_calls)
        fake_db[Collections.VOICE_CONVERSATION_SESSIONS].update_one(
            {"_id": ObjectId(sid)}, {"$set": {"processing_token": "in-flight", "processing_since": utcnow()}}
        )
        response = _process(client, headers, sid, TRANSCRIPT, 0)
        assert response.status_code == 409 and response.json()["error_code"] == "SESSION_BUSY"
        assert len(vc.ai.voice_calls) == ai_base

    def test_racing_submissions_for_one_turn_produce_exactly_one_turn(self, client, vc):
        import asyncio

        from app.schemas.voice_conversation import ProcessTranscriptRequest

        headers = _login(client)
        me = client.get("/api/v1/auth/me", headers=headers).json()["data"]
        user_id = (me.get("user") or me)["id"]
        sid = _active(client, headers)
        db = app.dependency_overrides[__import__("app.core.dependencies", fromlist=["get_db"]).get_db]()

        async def race():
            request = ProcessTranscriptRequest(transcript=TRANSCRIPT, expected_turn=0)
            return await asyncio.gather(
                *(vc.service.process_transcript(db, user_id=user_id, session_id=sid, request=request) for _ in range(3)),
                return_exceptions=True,
            )

        results = asyncio.run(race())
        assert sum(isinstance(r, dict) for r in results) == 1
        assert _session_view(client, headers, sid)["user_turn_count"] == 1

    def test_request_schema_is_strict(self, client, vc):
        headers = _login(client)
        sid = _active(client, headers)
        bad_bodies = [
            {"transcript": "hi", "expected_turn": 0, "user_id": "507f1f77bcf86cd799439011"},  # smuggled owner
            {"transcript": "hi", "expected_turn": 0, "audio": "AAAA"},  # no audio on this endpoint
            {"transcript": "hi"},  # expected_turn is required
            {"transcript": "hi", "expected_turn": -1},
            {"transcript": "hi", "expected_turn": 0, "language": "en; drop table"},
            {"transcript": "hi", "expected_turn": 0, "pause_metrics": {"pause_count": 1, "evil": {"x": 1}}},
            {"transcript": "x" * 20_000, "expected_turn": 0},
        ]
        for body in bad_bodies:
            assert client.post(f"{BASE}/sessions/{sid}/respond", json=body, headers=headers).status_code == 422, body
        assert len(vc.ai.voice_calls) == 1  # only the opening prompt


class TestSeparatedFlowSecurity:
    # TEST 10
    def test_other_users_cannot_transcribe_or_process(self, client, vc):
        a = _login(client, "a@example.com")
        b = _login(client, "b@example.com")
        sid = _active(client, a)
        ai_calls = len(vc.ai.voice_calls)

        assert _transcribe(client, b, sid, expected_turn=0).status_code == 403
        assert _process(client, b, sid, TRANSCRIPT, 0).status_code == 403
        assert _respond(client, b, sid).status_code == 403
        assert vc.stt.paths == [] and len(vc.ai.voice_calls) == ai_calls
        assert _session_view(client, a, sid)["user_turn_count"] == 0  # the owner's session is untouched

    def test_unauthenticated_requests_are_rejected(self, client, vc):
        a = _login(client, "a@example.com")
        sid = _active(client, a)
        files = {"audio": ("x.wav", WAV, "audio/wav")}
        assert client.post(f"{BASE}/sessions/{sid}/transcribe", files=files).status_code == 401
        assert client.post(f"{BASE}/sessions/{sid}/respond", json={"transcript": "x", "expected_turn": 0}).status_code == 401

    def test_unknown_session_is_404(self, client, vc):
        headers = _login(client)
        missing = "507f1f77bcf86cd799439011"
        assert _transcribe(client, headers, missing, expected_turn=0).status_code == 404
        assert _process(client, headers, missing, TRANSCRIPT, 0).status_code == 404

    def test_transcription_and_ai_errors_do_not_leak_internals(self, client, vc):
        headers = _login(client)
        sid = _active(client, headers)
        vc.stt.error = TranscriptionFailedError("secret-model-path /opt/whisper")
        stt = _transcribe(client, headers, sid, expected_turn=0)
        assert stt.status_code == 503 and "secret-model-path" not in stt.text
        vc.stt.error = None
        vc.ai.voice_fail = True
        ai = _process(client, headers, sid, TRANSCRIPT, 0)
        assert ai.status_code == 503 and "down" not in ai.text.lower().replace("unavailable", "")

    def test_transcripts_are_never_logged_by_either_step(self, client, vc, caplog):
        import logging

        caplog.set_level(logging.DEBUG)
        headers = _login(client)
        sid = _active(client, headers)
        _transcribe(client, headers, sid, expected_turn=0)
        _process(client, headers, sid, TRANSCRIPT, 0)
        assert "SIEM" not in caplog.text and vc.ai.voice_reply not in caplog.text


class TestTtsAfterTranscript:
    # TEST 11
    def test_tts_failure_keeps_the_ai_text_and_the_conversation_usable(self, client, vc):
        headers = _login(client)
        sid = _active(client, headers)
        vc.provider.error = TTSProviderError("boom")

        transcribed = _transcribe(client, headers, sid, expected_turn=0).json()["data"]
        response = _process(client, headers, sid, transcribed["transcript"], 0)

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["ai_response"] == vc.ai.voice_reply  # text preserved
        assert data["audio_url"] is None and data["audio_error"] == "TTS_FAILED"
        session = _session_view(client, headers, sid)
        assert session["user_turn_count"] == 1 and session["status"] == "active"
        assert session["messages"][-1]["text"] == vc.ai.voice_reply
        assert session["messages"][-1]["audio_available"] is False

        # The next turn works normally once speech is back.
        vc.provider.error = None
        nxt = _respond(client, headers, sid, expected_turn=1)
        assert nxt.status_code == 200 and nxt.json()["data"]["audio_url"]
        assert len(vc.stt.paths) == 2  # one STT per recording, never more

    def test_tts_not_called_when_ai_fails(self, client, vc):
        headers = _login(client)
        sid = _active(client, headers)
        tts_before = len(vc.provider.texts)
        vc.ai.voice_fail = True
        assert _process(client, headers, sid, TRANSCRIPT, 0).status_code == 503
        assert len(vc.provider.texts) == tts_before


class TestHistoryContinuity:
    # TEST 12
    def test_transcript_and_ai_reply_are_stored_in_order(self, client, vc):
        headers = _login(client)
        sid = _active(client, headers)
        vc.ai.voice_reply = "Good. Now tell me about correlation rules."

        t = _transcribe(client, headers, sid, expected_turn=0).json()["data"]
        _process(client, headers, sid, t["transcript"], 0, duration_seconds=t["duration_seconds"])

        session = _session_view(client, headers, sid)
        assert [(m["role"], m["text"]) for m in session["messages"][1:]] == [
            ("user", TRANSCRIPT),
            ("assistant", "Good. Now tell me about correlation rules."),
        ]
        assert session["messages"][1]["duration_seconds"] == 6.0
        assert session["turn_count"] == 3 and session["user_turn_count"] == 1 and session["assistant_turn_count"] == 2

    def test_history_keeps_growing_across_a_retry(self, client, vc):
        headers = _login(client)
        sid = _active(client, headers)
        first = _transcribe(client, headers, sid, expected_turn=0).json()["data"]["transcript"]
        vc.ai.voice_fail = True
        _process(client, headers, sid, first, 0)
        vc.ai.voice_fail = False
        assert _process(client, headers, sid, first, 0).status_code == 200  # the retry

        vc.stt.result = _result("It watches network traffic for known attack signatures.")
        second = _transcribe(client, headers, sid, expected_turn=1).json()["data"]["transcript"]
        assert _process(client, headers, sid, second, 1).status_code == 200

        session = _session_view(client, headers, sid)
        assert [m["role"] for m in session["messages"]] == ["assistant", "user", "assistant", "user", "assistant"]
        assert session["user_turn_count"] == 2  # the failed attempt did not consume a turn
        texts = [t.content for t in vc.ai.voice_calls[-1]["history"]]
        assert first in texts and vc.ai.voice_reply in texts  # earlier turns reach the model
        assert len(vc.stt.paths) == 2


# --- End / summary ------------------------------------------------------------------------------------


class TestEnd:
    def test_end_summarises_only_measured_values(self, client, vc):
        headers = _login(client)
        sid = _active(client, headers)
        _respond(client, headers, sid)
        _respond(client, headers, sid)
        data = client.post(f"{BASE}/sessions/{sid}/end", headers=headers).json()["data"]
        summary = data["summary"]
        assert data["session"]["status"] == "completed"
        assert summary["turns"] == 2 and summary["average_response_duration_seconds"] == 6.0
        assert summary["speaking_metrics"]["voice_message_count"] == 2
        # Free-form conversations have no scored evaluation, and none is invented.
        assert summary["evaluation"] is None and summary["evaluation_available"] is False
        assert summary["strengths"] == [] and summary["areas_to_improve"] == []

    def test_end_is_idempotent(self, client, vc):
        headers = _login(client)
        sid = _active(client, headers)
        _respond(client, headers, sid)
        first = client.post(f"{BASE}/sessions/{sid}/end", headers=headers).json()["data"]
        second = client.post(f"{BASE}/sessions/{sid}/end", headers=headers).json()["data"]
        assert first["session"]["ended_at"] == second["session"]["ended_at"]

    def test_ending_without_answers_marks_abandoned(self, client, vc):
        headers = _login(client)
        sid = _active(client, headers)
        data = client.post(f"{BASE}/sessions/{sid}/end", headers=headers).json()["data"]
        assert data["session"]["status"] == "abandoned"
        assert data["summary"]["speaking_metrics"] is None and data["summary"]["average_response_words"] is None

    def test_can_end_a_session_that_was_never_started(self, client, vc):
        headers = _login(client)
        sid = _new_session(client, headers)
        assert client.post(f"{BASE}/sessions/{sid}/end", headers=headers).json()["data"]["session"]["status"] == "abandoned"

    def test_cannot_start_or_respond_after_ending(self, client, vc):
        headers = _login(client)
        sid = _active(client, headers)
        client.post(f"{BASE}/sessions/{sid}/end", headers=headers)
        assert _start(client, headers, sid).status_code == 409
        assert _respond(client, headers, sid).status_code == 409

    def test_summary_helper_handles_missing_data(self):
        from datetime import datetime, timezone

        session = {"mode": "general", "difficulty": "beginner", "started_at": datetime.now(timezone.utc), "messages": []}
        summary = build_summary(session, evaluation=None)
        assert summary["turns"] == 0 and summary["speaking_metrics"] is None and summary["evaluation"] is None


# --- Mode integration ------------------------------------------------------------------------------------------


class TestInterviewMode:
    def test_voice_interview_reuses_step9(self, client, fake_db, vc):
        headers = _login(client)
        sid = _new_session(client, headers, mode="interview", interview_type="technical", question_count=5)
        started = _start(client, headers, sid).json()["data"]
        assert "interview" in started["ai_response"].lower() and "?" in started["ai_response"]

        linked = started["session"]["linked_session"]
        assert linked["kind"] == "interview"
        interview = fake_db[Collections.INTERVIEW_SESSIONS].find_one()
        assert str(interview["_id"]) == linked["session_id"] and interview["mode"] == "voice"

        vc.ai.suggest = True
        data = _respond(client, headers, sid).json()["data"]
        assert data["ai_response"] and data["turn_number"] == 1
        interview = fake_db[Collections.INTERVIEW_SESSIONS].find_one()
        answered = interview["questions"][0]
        assert answered["answer"] == TRANSCRIPT and answered["answer_input_type"] == "voice"
        assert answered["voice_analysis"]["duration_seconds"] == 6.0  # Step 8 analysis stored by Step 9
        assert answered["technical_evaluation"] is not None
        assert vc.ai.count("technical") == 1 and vc.ai.count("communication") == 1
        # Interview feedback is hidden mid-interview: the spoken reply carries no score.
        assert "80" not in data["ai_response"]

    def test_full_interview_completes_and_feeds_progress(self, client, fake_db, vc):
        headers = _login(client)
        sid = _active(client, headers, mode="interview", question_count=5)
        last = None
        for _ in range(12):
            last = _respond(client, headers, sid).json()["data"]
            if last["conversation_complete"]:
                break
        assert last["conversation_complete"] is True
        assert last["summary"]["evaluation"]["technical_score"] == 80
        assert last["summary"]["strengths"] == ["Clear fundamentals"]
        interview = fake_db[Collections.INTERVIEW_SESSIONS].find_one()
        assert interview["status"] == "completed" and interview["final_evaluation"]
        voice_doc = fake_db[Collections.VOICE_CONVERSATION_SESSIONS].find_one()
        assert voice_doc["status"] == "completed"
        # The real Step 9 record is what Step 11 aggregates -- no second progress store.
        overview = client.get("/api/v1/progress/overview", headers=headers)
        assert overview.status_code == 200
        summary = client.get("/api/v1/progress/skills", headers=headers)
        assert summary.status_code == 200

    def test_ending_early_evaluates_via_step9(self, client, fake_db, vc):
        headers = _login(client)
        sid = _active(client, headers, mode="interview")
        _respond(client, headers, sid)
        data = client.post(f"{BASE}/sessions/{sid}/end", headers=headers).json()["data"]
        assert data["summary"]["evaluation_available"] is True
        assert fake_db[Collections.INTERVIEW_SESSIONS].find_one()["status"] == "completed"

    def test_ending_with_no_answers_abandons_the_interview(self, client, fake_db, vc):
        headers = _login(client)
        sid = _active(client, headers, mode="interview")
        client.post(f"{BASE}/sessions/{sid}/end", headers=headers)
        assert fake_db[Collections.INTERVIEW_SESSIONS].find_one()["status"] == "abandoned"

    def test_interview_ai_failure_saves_nothing(self, client, fake_db, vc):
        headers = _login(client)
        sid = _active(client, headers, mode="interview")
        vc.ai.fail = {"technical"}
        assert _respond(client, headers, sid).status_code == 503
        interview = fake_db[Collections.INTERVIEW_SESSIONS].find_one()
        assert interview["questions"][0]["answer"] is None
        voice_doc = fake_db[Collections.VOICE_CONVERSATION_SESSIONS].find_one()
        assert voice_doc["user_turn_count"] == 0
        vc.ai.fail = set()
        assert _respond(client, headers, sid).status_code == 200

    def test_interview_start_failure_leaves_no_interview(self, client, fake_db, vc):
        headers = _login(client)
        sid = _new_session(client, headers, mode="interview")
        vc.ai.fail = {"question"}
        assert _start(client, headers, sid).status_code == 503
        assert fake_db[Collections.INTERVIEW_SESSIONS].count_documents({}) == 0


class TestPressureMode:
    def test_voice_pressure_reuses_step10(self, client, fake_db, vc):
        headers = _login(client)
        sid = _new_session(client, headers, mode="pressure", pressure_level=3, question_count=5)
        started = _start(client, headers, sid).json()["data"]
        assert started["session"]["linked_session"]["kind"] == "pressure"
        pressure = fake_db[Collections.PRESSURE_SESSIONS].find_one()
        assert pressure["pressure_level"] == 3 and pressure["input_mode"] == "voice"
        assert pressure["config"]  # config computed server-side from the level

        data = _respond(client, headers, sid, response_seconds=12).json()["data"]
        assert data["ai_response"]
        pressure = fake_db[Collections.PRESSURE_SESSIONS].find_one()
        first = pressure["questions"][0]
        assert first["answer"] == TRANSCRIPT and first["answer_input_type"] == "voice"
        assert first["response_duration_seconds"] is not None

    def test_pressure_session_completes_with_pressure_evaluation(self, client, fake_db, vc):
        headers = _login(client)
        sid = _active(client, headers, mode="pressure", pressure_level=1, question_count=5)
        last = None
        for _ in range(20):
            last = _respond(client, headers, sid).json()["data"]
            if last["conversation_complete"]:
                break
        assert last["conversation_complete"] is True
        final = fake_db[Collections.PRESSURE_SESSIONS].find_one()["final_evaluation"]
        assert "pressure_handling_score" in final  # produced by the Step 10 evaluator
        assert last["summary"]["evaluation"].get("pressure_handling_score") == final["pressure_handling_score"]

    def test_client_cannot_inject_pressure_internals(self, client, vc):
        headers = _login(client)
        r = client.post(
            f"{BASE}/sessions",
            json={"mode": "pressure", "config": {"interrupt_probability": 1}},
            headers=headers,
        )
        assert r.status_code == 422


class TestCommunicationMode:
    def test_voice_communication_reuses_step7_and_step8(self, client, fake_db, vc):
        headers = _login(client)
        sid = _new_session(client, headers, mode="communication")
        started = _start(client, headers, sid).json()["data"]
        assert started["mode_info"]["scenario_title"]
        comm = fake_db[Collections.COMMUNICATION_SESSIONS].find_one()
        assert comm["messages"][0]["role"] == "assistant"

        data = _respond(client, headers, sid).json()["data"]
        assert data["ai_response"] == "Thanks for asking! I started with networking."
        comm = fake_db[Collections.COMMUNICATION_SESSIONS].find_one()
        user_msg = comm["messages"][1]
        assert user_msg["input_type"] == "voice" and user_msg["voice_analysis"]["word_count"] > 5

    def test_end_uses_existing_communication_evaluation(self, client, fake_db, vc):
        headers = _login(client)
        sid = _active(client, headers, mode="communication")
        _respond(client, headers, sid)
        data = client.post(f"{BASE}/sessions/{sid}/end", headers=headers).json()["data"]
        comm = fake_db[Collections.COMMUNICATION_SESSIONS].find_one()
        assert comm["status"] == "completed"
        assert comm["evaluation"]["overall_score"] == EVAL_JSON["overall_score"]
        assert data["summary"]["evaluation"]["overall_score"] == EVAL_JSON["overall_score"]
        assert "voice_summary" in comm["evaluation"]  # Step 8 speaking summary, reused

    def test_evaluation_failure_still_ends_the_session(self, client, fake_db, vc, monkeypatch):
        headers = _login(client)
        sid = _active(client, headers, mode="communication")
        _respond(client, headers, sid)

        async def broken(*a, **k):
            raise AIProviderError("down")

        monkeypatch.setattr(vc.ai, "generate_response", broken)
        data = client.post(f"{BASE}/sessions/{sid}/end", headers=headers).json()["data"]
        assert data["session"]["status"] == "completed"
        assert data["summary"]["evaluation_error"] is True and data["summary"]["evaluation"] is None


class TestPracticeMode:
    def test_topic_is_in_the_prompt(self, client, vc):
        headers = _login(client)
        sid = _new_session(client, headers, mode="practice", topic="SQL injection", difficulty="advanced")
        _start(client, headers, sid)
        system = vc.ai.voice_calls[0]["system"]
        assert "SQL injection" in system and "advanced" in system.lower()


# --- Units --------------------------------------------------------------------------------------------------------------


class TestUnits:
    def test_spoken_text_cleanup_and_cap(self):
        assert END_TOKEN not in to_spoken_text(f"Bye. {END_TOKEN}")
        long = ("This is a sentence. " * 200).strip()
        out = to_spoken_text(long)
        assert len(out) <= 1200 and out.endswith(".")

    def test_prompts_demand_spoken_style(self):
        prompt = build_voice_system_prompt(mode="general", difficulty="beginner")
        for phrase in ("ONE main question", "No markdown", END_TOKEN):
            assert phrase in prompt

    def test_audio_store_expiry_eviction_and_ownership(self):
        now = [0.0]
        store = AudioStore(ttl_seconds=10, max_entries=2, clock=lambda: now[0])
        t1 = store.put("u1", b"a", "audio/mpeg")
        assert store.get("u1", t1).data == b"a"
        assert store.get("u2", t1) is None
        now[0] = 11
        assert store.get("u1", t1) is None  # expired
        t2, t3, t4 = (store.put("u1", b"x", "audio/mpeg") for _ in range(3))
        assert store.get("u1", t2) is None and store.get("u1", t4) is not None  # oldest evicted
        assert store.get("u1", "guess") is None

    def test_audio_store_byte_cap(self):
        store = AudioStore(ttl_seconds=60, max_total_bytes=10)
        first = store.put("u", b"123456", "audio/mpeg")
        store.put("u", b"123456", "audio/mpeg")
        assert store.get("u", first) is None

    def test_config_endpoint_exposes_no_secrets(self, client, vc):
        headers = _login(client)
        data = client.get(f"{BASE}/config", headers=headers).json()["data"]
        assert data["max_recording_seconds"] == settings.voice_max_recording_seconds
        assert set(data) >= {"stt_available", "tts_available", "auto_play", "modes"}
        assert "key" not in json.dumps(data).lower()


def test_existing_step8_endpoints_still_registered(client):
    paths = {r.path for r in app.routes}
    assert "/api/v1/voice/transcribe" in paths and "/api/v1/voice/synthesize" in paths
    _ = time
