"""
Whisper worker — handles tasks of type "transcription".

Expected payload:
    {
        "url": "http://...",       # URL of the audio/video file to transcribe
        "language": "en",          # optional, default auto-detect
        "word_timestamps": false   # optional
    }

Result shape:
    {
        "text": "...",
        "language": "en",
        "segments": [...]          # from whisper, if present
    }
"""

import logging
import os
from typing import Any, Dict

import httpx

log = logging.getLogger(__name__)

WHISPER_URL = os.getenv("WHISPER_BASE_URL", "http://whisper-api:8003")
TIMEOUT = 600  # whisper can be slow on long audio


async def handle_transcription(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Download the audio file from payload["url"] and send it to the
    whisper-api service for transcription.
    """
    audio_url: str = payload.get("url", "")
    if not audio_url:
        raise ValueError("payload must include a 'url' field")

    language: str = payload.get("language", "")
    word_timestamps: bool = payload.get("word_timestamps", False)

    # Download the file into memory
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        log.info(f"[transcription] Downloading audio from {audio_url}")
        dl = await client.get(audio_url, follow_redirects=True)
        dl.raise_for_status()
        audio_bytes = dl.content
        # Guess a filename extension from content-type or URL
        content_type = dl.headers.get("content-type", "")
        ext = _guess_ext(audio_url, content_type)

        # Build multipart form
        files = {"file": (f"audio{ext}", audio_bytes, content_type or "application/octet-stream")}
        data: Dict[str, str] = {}
        if language:
            data["language"] = language
        if word_timestamps:
            data["word_timestamps"] = "true"

        log.info(f"[transcription] Sending {len(audio_bytes)} bytes to whisper-api")
        resp = await client.post(
            f"{WHISPER_URL}/transcribe",
            files=files,
            data=data,
            timeout=TIMEOUT,
        )
        resp.raise_for_status()

    result = resp.json()
    log.info(f"[transcription] Done — {len(result.get('text', ''))} chars")
    return result


def _guess_ext(url: str, content_type: str) -> str:
    ct_map = {
        "audio/mpeg": ".mp3",
        "audio/mp4": ".m4a",
        "audio/ogg": ".ogg",
        "audio/wav": ".wav",
        "audio/webm": ".webm",
        "video/mp4": ".mp4",
        "video/webm": ".webm",
    }
    for mime, ext in ct_map.items():
        if mime in content_type:
            return ext
    # fallback: sniff from URL
    for ext in (".mp3", ".mp4", ".wav", ".ogg", ".m4a", ".webm", ".flac"):
        if url.lower().endswith(ext):
            return ext
    return ".mp3"
