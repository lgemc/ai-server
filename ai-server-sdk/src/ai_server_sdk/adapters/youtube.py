import os
from typing import Dict, Any

import httpx

from ..ports.youtube import YouTubePort
from ..core.models import DownloadResponse, DownloadRequest


class YouTubeAdapter(YouTubePort):
    """Adapter for YouTube download service."""

    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.getenv("YOUTUBE_BASE_URL", "http://localhost:8081")

    def health(self) -> Dict[str, Any]:
        """Check service health."""
        try:
            resp = httpx.get(f"{self.base_url}/health", timeout=5.0)
            return resp.json()
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def download(self, request: DownloadRequest) -> DownloadResponse:
        """Download a YouTube video."""
        data = {"url": request.url, "format": request.format}
        resp = httpx.post(f"{self.base_url}/youtube/download", json=data)
        resp.raise_for_status()
        return DownloadResponse(**resp.json())

    async def download_async(self, request: DownloadRequest) -> DownloadResponse:
        """Async download."""
        async with httpx.AsyncClient() as client:
            data = {"url": request.url, "format": request.format}
            resp = await client.post(f"{self.base_url}/youtube/download", json=data)
            resp.raise_for_status()
            return DownloadResponse(**resp.json())
