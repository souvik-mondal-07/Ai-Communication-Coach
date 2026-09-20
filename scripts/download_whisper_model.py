"""
Download / warm up the configured Whisper speech-to-text model (Step 8).

The first time faster-whisper uses a model size it downloads the weights
(roughly 460 MB for "small"). Doing that inside the first voice request would
leave the user waiting for minutes, so run this once after installing:

    cd backend
    python ../scripts/download_whisper_model.py

It reads WHISPER_MODEL / WHISPER_DEVICE / WHISPER_COMPUTE_TYPE from
backend/.env (or the environment), exactly like the API does.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.config import settings  # noqa: E402
from app.services.voice.speech_to_text import (  # noqa: E402
    SpeechToTextService,
    TranscriptionUnavailableError,
)


def main() -> int:
    print(
        f"Loading Whisper model '{settings.whisper_model}' "
        f"(device={settings.whisper_device}, compute_type={settings.whisper_compute_type})..."
    )
    started = time.time()
    try:
        SpeechToTextService().warm_up()
    except TranscriptionUnavailableError:
        print(
            "Could not load the model. Check that faster-whisper is installed "
            "(pip install -r backend/requirements.txt), that you have internet "
            "access to download the model, and that WHISPER_MODEL / WHISPER_DEVICE "
            "/ WHISPER_COMPUTE_TYPE are valid.",
            file=sys.stderr,
        )
        return 1
    print(f"Model ready in {time.time() - started:.1f}s. Voice transcription is good to go.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
