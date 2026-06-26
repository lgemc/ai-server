import os
from typing import BinaryIO, Dict, Any

import httpx

from ..ports.whisper import WhisperPort
from ..core.models import TranscribeResponse, TranscribeRequest


class WhisperAdapter(WhisperPort):
    """Adapter for Whisper transcription service."""

    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.getenv("WHISPER_BASE_URL", "http://localhost:8080")

    def health(self) -> Dict[str, Any]:
        """Check service health."""
        try:
            resp = httpx.get(f"{self.base_url}/health", timeout=5.0)
            return resp.json()
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def transcribe(
        self,
        audio_file: BinaryIO,
        request: TranscribeRequest = None,
    ) -> TranscribeResponse:
        """Transcribe audio file to text."""
        files = {"file": ("audio.wav", audio_file, "audio/wav")}
        data = {}
        if request and request.language:
            data["language"] = request.language

        resp = httpx.post(f"{self.base_url}/whisper/transcribe", files=files, data=data)
        resp.raise_for_status()
        return TranscribeResponse(**resp.json())

    async def transcribe_async(
        self,
        audio_file: BinaryIO,
        request: TranscribeRequest = None,
    ) -> TranscribeResponse:
        """Async transcription."""
        async with httpx.AsyncClient() as client:
            files = {"file": ("audio.wav", audio_file, "audio/wav")}
            data = {}
            if request and request.language:
                data["language"] = request.language

            resp = await client.post(f"{self.base_url}/whisper/transcribe", files=files, data=data)
            resp.raise_for_status()
            return TranscribeResponse(**resp.json())
