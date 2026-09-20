"""
Text-to-speech provider tests. HTTP is mocked with httpx.MockTransport —
no real provider is ever contacted.
"""

from __future__ import annotations

import asyncio
import base64
import json

import httpx
import pytest

from app.core.config import settings
from app.services.voice.text_to_speech import (
    GoogleCloudTTSProvider,
    OpenAITTSProvider,
    SynthesizedAudio,
    TextToSpeechService,
    TTSNotConfiguredError,
    TTSProviderError,
    clean_text_for_speech,
)

SECRET = "sk-super-secret-key"


def run(coro):
    return asyncio.run(coro)


class TestOpenAIProvider:
    def test_success_sends_key_in_header_and_returns_audio(self):
        seen = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["url"] = str(request.url)
            seen["auth"] = request.headers.get("authorization")
            seen["body"] = json.loads(request.content)
            return httpx.Response(200, content=b"MP3DATA")

        provider = OpenAITTSProvider(api_key=SECRET, transport=httpx.MockTransport(handler))
        audio = run(provider.synthesize("Hello there"))
        assert audio == SynthesizedAudio(data=b"MP3DATA", media_type="audio/mpeg")
        assert seen["url"] == "https://api.openai.com/v1/audio/speech"
        assert seen["auth"] == f"Bearer {SECRET}"
        assert seen["body"]["input"] == "Hello there"
        assert seen["body"]["model"] == "tts-1"

    def test_custom_model_voice_and_base_url(self):
        seen = {}

        def handler(request):
            seen["url"] = str(request.url)
            seen["body"] = json.loads(request.content)
            return httpx.Response(200, content=b"x")

        provider = OpenAITTSProvider(
            api_key="", model="m1", voice="v1", base_url="http://localhost:8880/v1/",
            transport=httpx.MockTransport(handler),
        )
        run(provider.synthesize("hi"))
        assert seen["url"] == "http://localhost:8880/v1/audio/speech"
        assert (seen["body"]["model"], seen["body"]["voice"]) == ("m1", "v1")

    def test_http_error_becomes_provider_error_without_leaking_details(self):
        def handler(request):
            return httpx.Response(401, json={"error": {"message": f"bad key {SECRET}"}})

        provider = OpenAITTSProvider(api_key=SECRET, transport=httpx.MockTransport(handler))
        with pytest.raises(TTSProviderError) as info:
            run(provider.synthesize("hi"))
        assert SECRET not in str(info.value)

    def test_network_error_becomes_provider_error(self):
        def handler(request):
            raise httpx.ConnectError("connection refused")

        provider = OpenAITTSProvider(api_key=SECRET, transport=httpx.MockTransport(handler))
        with pytest.raises(TTSProviderError):
            run(provider.synthesize("hi"))

    def test_empty_audio_is_an_error(self):
        provider = OpenAITTSProvider(
            api_key=SECRET, transport=httpx.MockTransport(lambda r: httpx.Response(200, content=b""))
        )
        with pytest.raises(TTSProviderError):
            run(provider.synthesize("hi"))


class TestGoogleProvider:
    def test_success_key_in_header_not_url(self):
        seen = {}

        def handler(request):
            seen["url"] = str(request.url)
            seen["key"] = request.headers.get("x-goog-api-key")
            seen["body"] = json.loads(request.content)
            return httpx.Response(200, json={"audioContent": base64.b64encode(b"AUDIO").decode()})

        provider = GoogleCloudTTSProvider(
            api_key=SECRET, voice="en-GB-Neural2-A", transport=httpx.MockTransport(handler)
        )
        audio = run(provider.synthesize("Hello"))
        assert audio.data == b"AUDIO"
        assert SECRET not in seen["url"]
        assert seen["key"] == SECRET
        assert seen["body"]["voice"] == {"languageCode": "en-GB", "name": "en-GB-Neural2-A"}

    def test_bad_payload_is_a_provider_error(self):
        for response in (
            httpx.Response(200, json={"nope": 1}),
            httpx.Response(200, json={"audioContent": "!!!not base64!!!"}),
            httpx.Response(500, text="err"),
        ):
            provider = GoogleCloudTTSProvider(
                api_key=SECRET, transport=httpx.MockTransport(lambda r, resp=response: resp)
            )
            with pytest.raises(TTSProviderError):
                run(provider.synthesize("hi"))


class TestTextToSpeechService:
    def test_not_configured_by_default(self, monkeypatch):
        monkeypatch.setattr(settings, "tts_provider", "")
        service = TextToSpeechService()
        assert service.is_configured() is False
        with pytest.raises(TTSNotConfiguredError):
            run(service.synthesize_speech("hi"))

    def test_unknown_provider_or_missing_key_is_not_configured(self, monkeypatch):
        monkeypatch.setattr(settings, "tts_provider", "nonesuch")
        assert TextToSpeechService().is_configured() is False
        monkeypatch.setattr(settings, "tts_provider", "google")
        monkeypatch.setattr(settings, "tts_api_key", "")
        assert TextToSpeechService().is_configured() is False

    def test_configured_via_environment_settings(self, monkeypatch):
        monkeypatch.setattr(settings, "tts_provider", "openai")
        monkeypatch.setattr(settings, "tts_api_key", SECRET)
        assert TextToSpeechService().is_configured() is True

    def test_text_is_cleaned_and_capped_before_reaching_provider(self):
        received = []

        class Recorder:
            async def synthesize(self, text):
                received.append(text)
                return SynthesizedAudio(b"a", "audio/mpeg")

        run(TextToSpeechService(Recorder()).synthesize_speech("**Great** point!\n- one\n`code`"))
        assert received == ["Great point! one code"]

    def test_unspeakable_text_is_rejected(self):
        with pytest.raises(TTSProviderError):
            run(TextToSpeechService(provider=object()).synthesize_speech("*** ***"))


def test_clean_text_for_speech():
    assert clean_text_for_speech("## Title\n*smiles* Hello   world") == "Title smiles Hello world"
