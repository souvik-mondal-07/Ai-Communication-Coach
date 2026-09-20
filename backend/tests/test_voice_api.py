"""
Voice API tests (/api/v1/voice/*). STT/TTS are faked — no model, no network.
"""

from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.core.dependencies import get_voice_service
from app.main import app
from app.services.voice.speech_to_text import (
    MalformedAudioError,
    SpeechToTextService,
    TranscriptionUnavailableError,
    TranscribedSegment,
    TranscribedWord,
    TranscriptionFailedError,
    TranscriptionResult,
)
from app.services.voice.text_to_speech import (
    SynthesizedAudio,
    TextToSpeechService,
    TTSProviderError,
)
from app.services.voice.voice_service import VoiceService
from tests.test_voice_stt import WAV, WEBM_HEADER

VALID_PASSWORD = "correct-horse-battery-staple"
SECRET_TRANSCRIPT = "my very private spoken sentence about salaries"


def _login(client, email="voice-user@example.com") -> dict:
    client.post("/api/v1/auth/register", json={"name": "Voice User", "email": email, "password": VALID_PASSWORD})
    token = client.post("/api/v1/auth/login", json={"email": email, "password": VALID_PASSWORD}).json()["data"][
        "access_token"
    ]
    return {"Authorization": f"Bearer {token}"}


class FakeSTT(SpeechToTextService):
    def __init__(self, result=None, error=None):
        super().__init__(model_factory=lambda: None)
        self.result, self.error, self.paths = result, error, []

    def is_available(self):
        return True

    def transcribe_audio(self, audio_file):
        self.paths.append(audio_file)
        if self.error:
            raise self.error
        return self.result


def _result(text=SECRET_TRANSCRIPT):
    words = [TranscribedWord(0.0, 0.5, "a"), TranscribedWord(3.0, 3.4, "b")]
    return TranscriptionResult(
        text=text, language="en", duration_seconds=5.2, segments=[TranscribedSegment(0, 3.4, text, words)]
    )


class RecordingProvider:
    def __init__(self, error=None):
        self.error, self.texts = error, []

    async def synthesize(self, text):
        self.texts.append(text)
        if self.error:
            raise self.error
        return SynthesizedAudio(b"FAKE-MP3", "audio/mpeg")


@pytest.fixture()
def voice(tmp_path, monkeypatch):
    """Install a VoiceService with fakes; yields a handle to tweak them."""
    monkeypatch.setattr(settings, "voice_temp_dir", str(tmp_path))
    handle = SimpleNamespace(stt=FakeSTT(result=_result()), provider=RecordingProvider(), tmp=tmp_path)

    def install():
        service = VoiceService(stt=handle.stt, tts=TextToSpeechService(provider=handle.provider))
        app.dependency_overrides[get_voice_service] = lambda: service

    handle.install = install
    install()
    yield handle
    app.dependency_overrides.pop(get_voice_service, None)


def _upload(client, headers, data=WAV, content_type="audio/wav", filename="recording.wav", field="audio"):
    return client.post(
        "/api/v1/voice/transcribe", files={field: (filename, data, content_type)}, headers=headers
    )


class TestTranscribeEndpoint:
    def test_requires_authentication(self, client, voice):
        response = client.post("/api/v1/voice/transcribe", files={"audio": ("a.wav", WAV, "audio/wav")})
        assert response.status_code == 401
        assert voice.stt.paths == []  # nothing was processed

    def test_unauthenticated_oversized_request_is_rejected_by_auth_first(self, client, voice):
        response = client.post(
            "/api/v1/voice/transcribe",
            content=b"x",
            headers={"Content-Type": "multipart/form-data; boundary=x", "Content-Length": "999999999"},
        )
        # Rejected before any body/size handling — auth runs first.
        assert response.status_code in (401, 403)

    def test_valid_transcription(self, client, voice):
        headers = _login(client)
        response = _upload(client, headers)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["text"] == SECRET_TRANSCRIPT
        assert data["language"] == "en"
        assert data["duration_seconds"] == 5.2
        assert data["pause_metrics"]["pause_count"] == 1
        assert data["pause_metrics"]["long_pauses"] == 1

    def test_accepts_browser_webm_with_codec_parameter(self, client, voice):
        headers = _login(client)
        assert _upload(client, headers, WEBM_HEADER, "audio/webm;codecs=opus", "blob").status_code == 200

    def test_empty_file(self, client, voice):
        headers = _login(client)
        response = _upload(client, headers, b"")
        assert response.status_code == 400
        assert response.json()["error_code"] == "EMPTY_AUDIO"

    def test_invalid_file(self, client, voice):
        headers = _login(client)
        response = _upload(client, headers, b"<html>not audio</html>", "audio/wav")
        assert response.status_code == 415
        assert response.json()["error_code"] == "UNSUPPORTED_AUDIO"
        response = _upload(client, headers, WAV, "text/html")
        assert response.status_code == 415

    def test_oversized_file(self, client, voice, monkeypatch):
        headers = _login(client)
        monkeypatch.setattr(settings, "voice_max_audio_bytes", 1000)
        response = _upload(client, headers, WAV)  # ~32 KB
        assert response.status_code == 413
        assert response.json()["error_code"] == "AUDIO_TOO_LARGE"
        assert voice.stt.paths == []

    def test_missing_audio_field(self, client, voice):
        headers = _login(client)
        response = _upload(client, headers, field="file")
        assert response.status_code == 422
        assert response.json()["error_code"] == "AUDIO_REQUIRED"

    def test_non_multipart_body(self, client, voice):
        headers = _login(client)
        response = client.post("/api/v1/voice/transcribe", json={"audio": "x"}, headers=headers)
        assert response.status_code in (400, 422)

    def test_malformed_audio_is_a_client_error(self, client, voice):
        headers = _login(client)
        voice.stt.error = MalformedAudioError("bad")
        response = _upload(client, headers)
        assert response.status_code == 422
        assert response.json()["error_code"] == "AUDIO_UNREADABLE"

    def test_whisper_unavailable_points_user_to_text_mode(self, client, voice):
        headers = _login(client)
        voice.stt.error = TranscriptionUnavailableError("no model")
        response = _upload(client, headers)
        assert response.status_code == 503
        assert response.json()["error_code"] == "STT_UNAVAILABLE"
        assert "type" in response.json()["message"].lower()

    def test_stt_failure(self, client, voice):
        headers = _login(client)
        voice.stt.error = TranscriptionFailedError("boom")
        response = _upload(client, headers)
        assert response.status_code == 503
        assert response.json()["error_code"] == "STT_FAILED"

    def test_silence_returns_no_speech_error(self, client, voice):
        headers = _login(client)
        voice.stt.result = TranscriptionResult(text="", language="en", duration_seconds=2.0, segments=[])
        response = _upload(client, headers)
        assert response.status_code == 422
        assert response.json()["error_code"] == "NO_SPEECH_DETECTED"

    def test_hostile_filename_is_ignored_and_temp_files_are_cleaned(self, client, voice):
        headers = _login(client)
        response = _upload(client, headers, filename="../../../etc/passwd.wav")
        assert response.status_code == 200
        path = voice.stt.paths[0]
        assert "passwd" not in path and ".." not in path
        assert path.startswith(str(voice.tmp))
        assert list(voice.tmp.iterdir()) == []  # deleted after processing

    def test_audio_and_transcript_are_never_logged(self, client, voice, caplog):
        headers = _login(client)
        with caplog.at_level(logging.DEBUG):
            _upload(client, headers)
        assert SECRET_TRANSCRIPT not in caplog.text
        assert "RIFF" not in caplog.text


class TestSynthesizeEndpoint:
    def test_requires_authentication(self, client, voice):
        assert client.post("/api/v1/voice/synthesize", json={"text": "hi"}).status_code == 401

    def test_success_returns_audio(self, client, voice):
        headers = _login(client)
        response = client.post(
            "/api/v1/voice/synthesize",
            json={"text": "That's a good point. Can you explain it further?"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "audio/mpeg"
        assert response.headers["cache-control"] == "no-store"
        assert response.content == b"FAKE-MP3"

    def test_provider_failure(self, client, voice):
        headers = _login(client)
        voice.provider.error = TTSProviderError("provider down")
        response = client.post("/api/v1/voice/synthesize", json={"text": "hi"}, headers=headers)
        assert response.status_code == 503
        assert response.json()["error_code"] == "TTS_FAILED"

    def test_not_configured(self, client, voice, monkeypatch):
        headers = _login(client)
        monkeypatch.setattr(settings, "tts_provider", "")
        app.dependency_overrides[get_voice_service] = lambda: VoiceService(
            stt=voice.stt, tts=TextToSpeechService()
        )
        response = client.post("/api/v1/voice/synthesize", json={"text": "hi"}, headers=headers)
        assert response.status_code == 503
        assert response.json()["error_code"] == "TTS_NOT_CONFIGURED"

    def test_validation(self, client, voice):
        headers = _login(client)
        assert client.post("/api/v1/voice/synthesize", json={"text": "   "}, headers=headers).status_code == 422
        assert client.post("/api/v1/voice/synthesize", json={"text": "x" * 2001}, headers=headers).status_code == 422
        assert client.post("/api/v1/voice/synthesize", json={}, headers=headers).status_code == 422


class TestCapabilities:
    def test_requires_authentication(self, client, voice):
        assert client.get("/api/v1/voice/capabilities").status_code == 401

    def test_reports_public_config_only(self, client, voice):
        headers = _login(client)
        data = client.get("/api/v1/voice/capabilities", headers=headers).json()["data"]
        assert data["stt_available"] is True
        assert data["tts_available"] is True
        assert set(data) == {"stt_available", "tts_available", "max_audio_seconds", "max_audio_bytes"}
