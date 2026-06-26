import os
from typing import Optional

from ..ports.youtube import YouTubePort
from ..adapters.youtube import YouTubeAdapter
from ..core.models import DownloadResponse, DownloadRequest


class YouTubeClient:
    """
    User-facing client for YouTube downloads.

    Usage:
        client = YouTubeClient(base_url="http://localhost:8081")
        result = client.download("https://youtube.com/watch?v=...", format="mp4")
    """

    def __init__(self, base_url: Optional[str] = None):
        self._port: YouTubePort = YouTubeAdapter(base_url)

    @property
    def port(self) -> YouTubePort:
        return self._port

    def health(self) -> dict:
        """Check service health."""
        return self._port.health()

    def download(self, url: str, format: str = "mp4") -> DownloadResponse:
        """Download a YouTube video."""
        request = DownloadRequest(url=url, format=format)
        return self._port.download(request)

    async def download_async(self, url: str, format: str = "mp4") -> DownloadResponse:
        """Async download."""
        request = DownloadRequest(url=url, format=format)
        return await self._port.download_async(request)
