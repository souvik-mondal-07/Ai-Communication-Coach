"""
Speech-to-text service + voice-service validation tests.

No real Whisper model is used (weights can't be assumed present); a fake model
stands in. Audio fixtures are generated in-test, and one test drives the *real*
PyAV decoder to check corrupt audio is classified correctly.
"""

from __future__ import annotations

import asyncio
import io
import os
import struct
import wave
from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.services.voice.speech_to_text import (
    AudioTooLongError,
    MalformedAudioError,
    SpeechToTextService,
    TranscriptionFailedError,
    TranscriptionUnavailableError,
)
from app.services.voice.voice_service import (
    AudioTooLargeError,
    EmptyAudioError,
    NoSpeechDetectedError,
    UnsupportedAudioError,
    VoiceService,
    read_upload_limited,
    sniff_audio_format,
    validate_audio,
)


def make_wav(seconds: float = 1.0, rate: int = 16000) -> bytes:
    buffer = io.BytesIO()

    with wave.open(buffer, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(struct.pack("<h", 0) * int(rate * seconds))

    return buffer.getvalue()


WAV = make_wav()
WEBM_HEADER = b"\x1a\x45\xdf\xa3" + b"\x00" * 60


def _word(start, end, text):
    return SimpleNamespace(
        start=start,
        end=end,
        word=text,
        probability=0.9,
    )


def _segment(start, end, text, words=None):
    return SimpleNamespace(
        start=start,
        end=end,
        text=text,
        words=words or [],
    )


class FakeModel:
    def __init__(
        self,
        segments=None,
        duration=4.8,
        language="en",
        error=None,
    ):
        self.segments = segments or []
        self.duration = duration
        self.language = language
        self.error = error
        self.calls = []
        self.consumed = False

    def transcribe(self, source, **kwargs):
        self.calls.append((source, kwargs))

        if self.error:
            raise self.error

        def gen():
            self.consumed = True
            yield from self.segments

        return gen(), SimpleNamespace(
            language=self.language,
            duration=self.duration,
        )


class TestSpeechToTextService:
    def _service(self, model):
        calls = {"n": 0}

        def factory():
            calls["n"] += 1
            return model

        return SpeechToTextService(model_factory=factory), calls

    def test_mocked_transcription_maps_to_structured_result(self):
        model = FakeModel(
            segments=[
                _segment(
                    0.0,
                    2.0,
                    " I would like to know ",
                    [
                        _word(0.0, 0.5, "I"),
                        _word(0.6, 1.0, "would"),
                    ],
                ),
                _segment(
                    2.5,
                    4.8,
                    " about internships. ",
                ),
            ]
        )

        service, _ = self._service(model)

        result = service.transcribe_audio("/tmp/x.wav")

        assert result.text == "I would like to know about internships."
        assert result.language == "en"
        assert result.duration_seconds == 4.8
        assert len(result.segments) == 2
        assert result.segments[0].words[1].text == "would"

        # Only what we need is exposed — not Whisper's internals.
        assert not hasattr(result, "avg_logprob")
        assert not hasattr(result.segments[0], "tokens")

    def test_model_is_loaded_once_and_reused(self):
        service, calls = self._service(
            FakeModel(
                segments=[
                    _segment(0, 1, "hi"),
                ]
            )
        )

        service.transcribe_audio("/tmp/a.wav")
        service.transcribe_audio("/tmp/b.wav")

        assert calls["n"] == 1

    def test_model_not_loaded_until_first_use(self):
        _, calls = self._service(FakeModel())

        assert calls["n"] == 0

    def test_language_setting_is_passed_and_empty_means_autodetect(
        self,
        monkeypatch,
    ):
        model = FakeModel(
            segments=[
                _segment(0, 1, "hi"),
            ]
        )

        service, _ = self._service(model)

        monkeypatch.setattr(settings, "whisper_language", "en")
        service.transcribe_audio("/tmp/a.wav")

        monkeypatch.setattr(settings, "whisper_language", "")
        service.transcribe_audio("/tmp/b.wav")

        assert model.calls[0][1]["language"] == "en"
        assert model.calls[1][1]["language"] is None
        assert model.calls[0][1]["word_timestamps"] is True

    def test_model_load_failure_is_reported_as_unavailable(self):
        def broken():
            raise OSError("weights missing")

        service = SpeechToTextService(model_factory=broken)

        with pytest.raises(TranscriptionUnavailableError):
            service.transcribe_audio("/tmp/a.wav")

    def test_decode_errors_are_malformed_audio_not_server_errors(self):
        av_error = type(
            "InvalidDataError",
            (Exception,),
            {"__module__": "av.error"},
        )

        service, _ = self._service(
            FakeModel(
                error=av_error("bad data"),
            )
        )

        with pytest.raises(MalformedAudioError):
            service.transcribe_audio("/tmp/a.wav")

    def test_config_errors_are_not_blamed_on_the_audio(self):
        service, _ = self._service(
            FakeModel(
                error=ValueError("invalid language code"),
            )
        )

        with pytest.raises(TranscriptionFailedError):
            service.transcribe_audio("/tmp/a.wav")

    def test_too_long_recording_is_rejected_before_segments_are_processed(
        self,
        monkeypatch,
    ):
        monkeypatch.setattr(
            settings,
            "voice_max_audio_seconds",
            10,
        )

        model = FakeModel(
            segments=[
                _segment(0, 1, "hi"),
            ],
            duration=11.0,
        )

        service, _ = self._service(model)

        with pytest.raises(AudioTooLongError):
            service.transcribe_audio("/tmp/a.wav")

        assert model.consumed is False

    def test_real_pyav_decoder_errors_are_classified_as_malformed(
        self,
        tmp_path,
    ):
        """Drives the genuine faster-whisper/PyAV decoder with corrupt audio."""
        pytest.importorskip("faster_whisper")

        from faster_whisper.audio import decode_audio

        class DecodingModel:
            def transcribe(self, source, **_):
                decode_audio(source)
                return (
                    iter(()),
                    SimpleNamespace(
                        language="en",
                        duration=0.0,
                    ),
                )

        corrupt = tmp_path / "corrupt.wav"

        corrupt.write_bytes(
            b"RIFF\x24\x00\x00\x00WAVE" + os.urandom(400)
        )

        service = SpeechToTextService(
            model_factory=DecodingModel,
        )

        with pytest.raises(MalformedAudioError):
            service.transcribe_audio(str(corrupt))


class TestAudioValidation:
    def test_sniffs_known_formats(self):
        assert sniff_audio_format(WAV[:16]) == ".wav"
        assert sniff_audio_format(WEBM_HEADER[:16]) == ".webm"
        assert sniff_audio_format(b"OggS" + b"\x00" * 12) == ".ogg"
        assert (
            sniff_audio_format(
                b"\x00\x00\x00\x1cftypM4A " + b"\x00" * 4
            )
            == ".m4a"
        )
        assert sniff_audio_format(b"ID3\x04" + b"\x00" * 12) == ".mp3"
        assert sniff_audio_format(b"fLaC" + b"\x00" * 12) == ".flac"

    def test_empty_file(self):
        with pytest.raises(EmptyAudioError):
            validate_audio(b"", "audio/wav")

    def test_invalid_file_content(self):
        with pytest.raises(UnsupportedAudioError):
            validate_audio(
                b"<html><script>alert(1)</script></html>",
                "audio/wav",
            )

        with pytest.raises(UnsupportedAudioError):
            validate_audio(
                b"MZ\x90\x00" + b"\x00" * 100,
                "audio/wav",
            )

    def test_content_type_is_checked_but_content_is_what_counts(self):
        with pytest.raises(UnsupportedAudioError):
            validate_audio(WAV, "text/html")

        assert validate_audio(
            WAV,
            "application/octet-stream",
        ) == ".wav"

        assert validate_audio(
            WEBM_HEADER,
            "audio/webm;codecs=opus",
        ) == ".webm"

        assert validate_audio(
            WAV,
            None,
        ) == ".wav"

    def test_oversized(self, monkeypatch):
        monkeypatch.setattr(
            settings,
            "voice_max_audio_bytes",
            100,
        )

        with pytest.raises(AudioTooLargeError):
            validate_audio(WAV, "audio/wav")

    def test_streaming_read_stops_at_the_limit(self):
        class Upload:
            def __init__(self):
                self.reads = 0

            async def read(self, size=-1):
                self.reads += 1
                return b"x" * size

        upload = Upload()

        with pytest.raises(AudioTooLargeError):
            asyncio.run(
                read_upload_limited(
                    upload,
                    max_bytes=200_000,
                )
            )

        assert upload.reads < 10
        # gave up early instead of buffering forever


class TestVoiceServiceTranscription:
    def _voice_service(
        self,
        model,
        tmp_path,
        monkeypatch,
    ):
        monkeypatch.setattr(
            settings,
            "voice_temp_dir",
            str(tmp_path),
        )

        stt = SpeechToTextService(
            model_factory=lambda: model
        )

        return VoiceService(
            stt=stt,
            tts=SimpleNamespace(),
        )

    def test_transcribes_and_computes_pause_metrics_from_word_timestamps(
        self,
        tmp_path,
        monkeypatch,
    ):
        words = [
            _word(0.0, 0.5, "hello"),
            _word(3.0, 3.5, "world"),
        ]

        model = FakeModel(
            segments=[
                _segment(
                    0.0,
                    3.5,
                    "hello world",
                    words,
                )
            ],
            duration=4.0,
        )

        outcome = asyncio.run(
            self._voice_service(
                model,
                tmp_path,
                monkeypatch,
            ).transcribe(
                WAV,
                "audio/wav",
            )
        )

        assert outcome.text == "hello world"
        assert outcome.duration_seconds == 4.0
        assert outcome.pause_metrics["pause_count"] == 1
        assert outcome.pause_metrics["long_pauses"] == 1
        assert outcome.pause_metrics["granularity"] == "word"

    def test_pause_metrics_unavailable_when_no_timestamps(
        self,
        tmp_path,
        monkeypatch,
    ):
        model = FakeModel(
            segments=[
                _segment(
                    0.0,
                    3.5,
                    "hello world",
                )
            ],
            duration=4.0,
        )

        outcome = asyncio.run(
            self._voice_service(
                model,
                tmp_path,
                monkeypatch,
            ).transcribe(
                WAV,
                "audio/wav",
            )
        )

        # Not invented when timestamps are unavailable.
        assert outcome.pause_metrics is None

    def test_no_speech_detected(
        self,
        tmp_path,
        monkeypatch,
    ):
        model = FakeModel(
            segments=[],
            duration=2.0,
        )

        with pytest.raises(NoSpeechDetectedError):
            asyncio.run(
                self._voice_service(
                    model,
                    tmp_path,
                    monkeypatch,
                ).transcribe(
                    WAV,
                    "audio/wav",
                )
            )

    def test_temp_file_is_deleted_after_success(
        self,
        tmp_path,
        monkeypatch,
    ):
        seen = {}

        class Model(FakeModel):
            def transcribe(self, source, **kw):
                seen["path"] = source
                seen["existed_during"] = os.path.exists(source)
                seen["mode"] = oct(
                    os.stat(source).st_mode & 0o777
                )
                return super().transcribe(source, **kw)

        model = Model(
            segments=[
                _segment(
                    0,
                    1,
                    "hi",
                )
            ]
        )

        asyncio.run(
            self._voice_service(
                model,
                tmp_path,
                monkeypatch,
            ).transcribe(
                WAV,
                "audio/wav",
            )
        )

        assert seen["existed_during"] is True

        # POSIX systems expose 0600 permissions through st_mode.
        # Windows does not provide equivalent POSIX permission semantics,
        # so the numeric mode is not reliable there.
        if os.name != "nt":
            assert seen["mode"] == "0o600"

        assert seen["path"].endswith(".wav")
        assert list(tmp_path.iterdir()) == []

    def test_temp_file_is_deleted_after_failure(
        self,
        tmp_path,
        monkeypatch,
    ):
        model = FakeModel(
            error=RuntimeError("boom"),
        )

        with pytest.raises(TranscriptionFailedError):
            asyncio.run(
                self._voice_service(
                    model,
                    tmp_path,
                    monkeypatch,
                ).transcribe(
                    WAV,
                    "audio/wav",
                )
            )

        assert list(tmp_path.iterdir()) == []

    def test_rejected_upload_never_touches_disk(
        self,
        tmp_path,
        monkeypatch,
    ):
        model = FakeModel()

        service = self._voice_service(
            model,
            tmp_path,
            monkeypatch,
        )

        with pytest.raises(UnsupportedAudioError):
            asyncio.run(
                service.transcribe(
                    b"not audio at all",
                    "audio/wav",
                )
            )

        assert list(tmp_path.iterdir()) == []
        assert model.calls == []