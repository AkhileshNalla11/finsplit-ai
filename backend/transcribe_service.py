"""Speech-to-text via Groq's Whisper API.

The browser records a short audio clip (MediaRecorder) and posts it here; we
forward it to Groq's OpenAI-compatible Whisper endpoint and return the
transcript. This is far more reliable across devices than the browser's native
SpeechRecognition, which behaves inconsistently on Android.
"""

import logging
import os

import httpx

logger = logging.getLogger(__name__)

GROQ_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
# whisper-large-v3-turbo is fast and accurate; override via env if needed.
GROQ_MODEL = os.environ.get("GROQ_WHISPER_MODEL") or "whisper-large-v3-turbo"


class TranscribeError(Exception):
    """Raised when transcription fails."""


def transcribe(audio_bytes: bytes, filename: str, content_type: str) -> str:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise TranscribeError("GROQ_API_KEY is not set")

    files = {"file": (filename, audio_bytes, content_type)}
    data = {"model": GROQ_MODEL, "response_format": "text", "language": "en"}
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        resp = httpx.post(GROQ_URL, files=files, data=data, headers=headers, timeout=60)
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.error("Groq HTTP error %s: %s", exc.response.status_code, exc.response.text[:300])
        raise TranscribeError(f"Transcription failed ({exc.response.status_code})") from exc
    except httpx.RequestError as exc:
        logger.error("Groq request error: %s", exc)
        raise TranscribeError(f"Transcription request error: {exc}") from exc

    # response_format=text returns the raw transcript as the response body.
    return resp.text.strip()
