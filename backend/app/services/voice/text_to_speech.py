"""
Text-to-speech service with a provider abstraction.

    synthesize_speech(text) -> SynthesizedAudio(data, media_type)

The rest of the application only ever talks to `TextToSpeechService`; it
never names a provider. Providers implement `TTSProvider` and are selected by
`TTS_PROVIDER` in the environment, so swapping providers later means adding
one class and one registry entry.

* API keys stay on the backend (`TTS_API_KEY`) and are sent in request
  *headers* — never in URLs — so they can't leak through logs or tracebacks.
* Provider error bodies are never echoed to the client or logged.
* If no provider is configured the service reports "not configured" cleanly;
  text-mode communication is unaffected.
"""

from __future__ import annotations

import base64
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx

from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

MAX_TTS_CHARS = 2_000
_REQUEST_TIMEOUT_SECONDS = 30.0


# --- Errors -----------------------------------------------------------------


class TTSError(Exception):
    """Base class for text-to-speech failures."""


class TTSNotConfiguredError(TTSError):
    """No (valid) TTS provider is configured."""


class TTSProviderError(TTSError):
    """The provider failed or returned something unusable."""


@dataclass(frozen=True)
class SynthesizedAudio:
    data: bytes
    media_type: str


# --- Text preparation -------------------------------------------------------


def clean_text_for_speech(text: str) -> str:
    """Strip markdown/formatting characters so they aren't read aloud."""
    cleaned = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    cleaned = re.sub(r"`([^`]*)`", r"\1", cleaned)
    cleaned = re.sub(r"^\s{0,3}#{1,6}\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^\s*[-*+]\s+", "", cleaned, flags=re.MULTILINE)
    cleaned = cleaned.replace("*", "")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


# --- Providers --------------------------------------------------------------


class TTSProvider(ABC):
    """A text-to-speech backend."""

    @abstractmethod
    async def synthesize(self, text: str) -> SynthesizedAudio: ...


class OpenAITTSProvider(TTSProvider):
    """OpenAI `/audio/speech` (also works with OpenAI-compatible servers via TTS_BASE_URL)."""

    DEFAULT_BASE_URL = "https://api.openai.com/v1"
    DEFAULT_MODEL = "tts-1"
    DEFAULT_VOICE = "alloy"

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "",
        voice: str = "",
        base_url: str = "",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model or self.DEFAULT_MODEL
        self._voice = voice or self.DEFAULT_VOICE
        self._url = (base_url or self.DEFAULT_BASE_URL).rstrip("/") + "/audio/speech"
        self._transport = transport

    async def synthesize(self, text: str) -> SynthesizedAudio:
        payload = {
            "model": self._model,
            "voice": self._voice,
            "input": text,
            "response_format": "mp3",
        }
        headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}
        try:
            async with httpx.AsyncClient(
                timeout=_REQUEST_TIMEOUT_SECONDS, transport=self._transport
            ) as client:
                response = await client.post(self._url, json=payload, headers=headers)
        except httpx.HTTPError as exc:
            logger.error("TTS request failed: %s", type(exc).__name__)
            raise TTSProviderError("Text-to-speech provider could not be reached.") from None
        if response.status_code != 200 or not response.content:
            logger.error("TTS provider returned HTTP %s", response.status_code)
            raise TTSProviderError("Text-to-speech provider returned an error.")
        return SynthesizedAudio(data=response.content, media_type="audio/mpeg")


class GoogleCloudTTSProvider(TTSProvider):
    """Google Cloud Text-to-Speech REST API (`text:synthesize`)."""

    URL = "https://texttospeech.googleapis.com/v1/text:synthesize"
    DEFAULT_LANGUAGE = "en-US"

    def __init__(
        self,
        *,
        api_key: str,
        voice: str = "",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self._voice = voice
        self._transport = transport

    async def synthesize(self, text: str) -> SynthesizedAudio:
        voice_config: dict[str, str] = {"languageCode": self.DEFAULT_LANGUAGE}
        if self._voice:
            # Google voice names look like "en-US-Neural2-F"; the language
            # code is the first two segments.
            voice_config = {
                "languageCode": "-".join(self._voice.split("-")[:2]) or self.DEFAULT_LANGUAGE,
                "name": self._voice,
            }
        payload = {
            "input": {"text": text},
            "voice": voice_config,
            "audioConfig": {"audioEncoding": "MP3"},
        }
        # Key goes in a header, not the query string, so it never lands in a URL.
        headers = {"X-Goog-Api-Key": self._api_key}
        try:
            async with httpx.AsyncClient(
                timeout=_REQUEST_TIMEOUT_SECONDS, transport=self._transport
            ) as client:
                response = await client.post(self.URL, json=payload, headers=headers)
        except httpx.HTTPError as exc:
            logger.error("TTS request failed: %s", type(exc).__name__)
            raise TTSProviderError("Text-to-speech provider could not be reached.") from None
        if response.status_code != 200:
            logger.error("TTS provider returned HTTP %s", response.status_code)
            raise TTSProviderError("Text-to-speech provider returned an error.")
        try:
            audio = base64.b64decode(response.json()["audioContent"], validate=True)
        except (ValueError, KeyError, TypeError):
            raise TTSProviderError("Text-to-speech provider returned unusable audio.") from None
        if not audio:
            raise TTSProviderError("Text-to-speech provider returned empty audio.")
        return SynthesizedAudio(data=audio, media_type="audio/mpeg")


# --- Service ----------------------------------------------------------------


def _build_provider_from_settings() -> TTSProvider:
    name = settings.tts_provider.strip().lower()
    if not name:
        raise TTSNotConfiguredError("Text-to-speech is not configured.")

    if name == "openai":
        # A key is required for the real OpenAI API; a custom base URL
        # (self-hosted, OpenAI-compatible) may not need one.
        if not settings.tts_api_key and not settings.tts_base_url:
            raise TTSNotConfiguredError("Text-to-speech is not configured.")
        return OpenAITTSProvider(
            api_key=settings.tts_api_key,
            model=settings.tts_model,
            voice=settings.tts_voice,
            base_url=settings.tts_base_url,
        )
    if name == "google":
        if not settings.tts_api_key:
            raise TTSNotConfiguredError("Text-to-speech is not configured.")
        return GoogleCloudTTSProvider(api_key=settings.tts_api_key, voice=settings.tts_voice)

    logger.warning("Unknown TTS_PROVIDER '%s' — text-to-speech disabled", name)
    raise TTSNotConfiguredError("Text-to-speech is not configured.")


class TextToSpeechService:
    """Provider-agnostic text-to-speech facade."""

    def __init__(self, provider: TTSProvider | None = None) -> None:
        # Tests (or future code) may inject a provider; otherwise it's built
        # from settings on each call so configuration changes take effect.
        self._provider = provider

    def is_configured(self) -> bool:
        if self._provider is not None:
            return True
        try:
            _build_provider_from_settings()
        except TTSNotConfiguredError:
            return False
        return True

    async def synthesize_speech(self, text: str) -> SynthesizedAudio:
        """Synthesize `text` to audio. Raises `TTSError` subclasses on failure."""
        provider = self._provider or _build_provider_from_settings()
        prepared = clean_text_for_speech(text)[:MAX_TTS_CHARS]
        if not prepared:
            raise TTSProviderError("There is no speakable text.")
        return await provider.synthesize(prepared)


# Module-level singleton, matching the project's existing pattern.
text_to_speech_service = TextToSpeechService()


async def synthesize_speech(text: str) -> SynthesizedAudio:
    """Convenience wrapper: `synthesize_speech(text) -> audio`."""
    return await text_to_speech_service.synthesize_speech(text)
