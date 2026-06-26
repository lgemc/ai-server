import os
from typing import BinaryIO, Optional

from ..ports.whisper import WhisperPort
from ..adapters.whisper import WhisperAdapter
from ..core.models import TranscribeResponse, TranscribeRequest


class WhisperClient:
    """
    User-facing client for Whisper transcription.

    Usage:
        client = WhisperClient(base_url="http://localhost:8080")
        # or via env var WHISPER_BASE_URL

        with open("audio.wav", "rb") as f:
            result = client.transcribe(f, TranscribeRequest(language="en"))
        print(result.segments)
    """

    def __init__(self, base_url: Optional[str] = None):
        self._port: WhisperPort = WhisperAdapter(base_url)

    @property
    def port(self) -> WhisperPort:
        return self._port

    def health(self) -> dict:
        """Check transcription service health."""
        return self._port.health()

    def transcribe(
        self,
        audio_file: BinaryIO,
        language: Optional[str] = None,
    ) -> TranscribeResponse:
        """Transcribe an audio file."""
        request = TranscribeRequest(language=language) if language else None
        return self._port.transcribe(audio_file, request)

    async def transcribe_async(
        self,
        audio_file: BinaryIO,
        language: Optional[str] = None,
    ) -> TranscribeResponse:
        """Async transcription."""
        request = TranscribeRequest(language=language) if language else None
        return await self._port.transcribe_async(audio_file, request)
