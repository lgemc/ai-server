import os
from typing import Optional

from ..ports.tts import TTSPort
from ..adapters.tts import TTSAdapter
from ..core.models import TTSRequest, TTSResponse, TTSVoice, TTSSResponseFormat


class TTSClient:
    """
    User-facing client for Text-to-Speech.

    Usage:
        client = TTSClient(base_url="http://localhost:8082")
        result = client.synthesize("Hello world", voice=TTSVoice.ALLOY)
        with open("output.mp3", "wb") as f:
            f.write(result.audio_data)
    """

    def __init__(self, base_url: Optional[str] = None):
        self._port: TTSPort = TTSAdapter(base_url)

    @property
    def port(self) -> TTSPort:
        return self._port

    def health(self) -> dict:
        """Check service health."""
        return self._port.health()

    def synthesize(
        self,
        text: str,
        voice: TTSVoice = TTSVoice.ALLOY,
        model: str = "tts-1",
        response_format: TTSSResponseFormat = TTSSResponseFormat.MP3,
        speed: Optional[float] = None,
    ) -> TTSResponse:
        """Synthesize speech from text."""
        request = TTSRequest(
            input=text,
            model=model,
            voice=voice,
            response_format=response_format,
            speed=speed,
        )
        return self._port.synthesize(request)

    async def synthesize_async(
        self,
        text: str,
        voice: TTSVoice = TTSVoice.ALLOY,
        model: str = "tts-1",
        response_format: TTSSResponseFormat = TTSSResponseFormat.MP3,
        speed: Optional[float] = None,
    ) -> TTSResponse:
        """Async synthesis."""
        request = TTSRequest(
            input=text,
            model=model,
            voice=voice,
            response_format=response_format,
            speed=speed,
        )
        return await self._port.synthesize_async(request)
