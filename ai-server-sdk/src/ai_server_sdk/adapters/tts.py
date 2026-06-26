import os
from typing import Dict, Any

import httpx

from ..ports.tts import TTSPort
from ..core.models import TTSRequest, TTSResponse


class TTSAdapter(TTSPort):
    """Adapter for Text-to-Speech service."""

    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.getenv("TTS_BASE_URL", "http://localhost:8082")

    def health(self) -> Dict[str, Any]:
        """Check service health."""
        try:
            resp = httpx.get(f"{self.base_url}/health", timeout=5.0)
            return resp.json()
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def synthesize(self, request: TTSRequest) -> TTSResponse:
        """Synthesize speech from text."""
        data = request.model_dump(exclude_none=True)
        resp = httpx.post(f"{self.base_url}/tts/synthesize", json=data)
        resp.raise_for_status()
        return TTSResponse(
            audio_data=resp.content,
            content_type=resp.headers.get("content-type", "audio/mpeg"),
        )

    async def synthesize_async(self, request: TTSRequest) -> TTSResponse:
        """Async synthesis."""
        async with httpx.AsyncClient() as client:
            data = request.model_dump(exclude_none=True)
            resp = await client.post(f"{self.base_url}/tts/synthesize", json=data)
            resp.raise_for_status()
            return TTSResponse(
                audio_data=resp.content,
                content_type=resp.headers.get("content-type", "audio/mpeg"),
            )
