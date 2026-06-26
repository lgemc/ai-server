import os
from typing import Dict, Any

import httpx

from ..ports.youtube import YouTubePort
from ..core.models import DownloadResponse, DownloadRequest


class YouTubeAdapter(YouTubePort):
    """Adapter for YouTube download service."""

    def __init__(self, base_url: str = None):
        self.base_url = (base_url or os.getenv("YOUTUBE_BASE_URL", "http://localhost:8002")).rstrip("/")

    def health(self) -> Dict[str, Any]:
        try:
            resp = httpx.get(f"{self.base_url}/health", timeout=5.0)
            return resp.json()
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def download(self, request: DownloadRequest) -> DownloadResponse:
        audio_only = request.format == "mp3"
        data = {"url": request.url, "audio_only": audio_only, "format": "best"}
        resp = httpx.post(f"{self.base_url}/download", json=data, timeout=300.0)
        resp.raise_for_status()
        return _parse(resp.json(), self.base_url)

    async def download_async(self, request: DownloadRequest) -> DownloadResponse:
        audio_only = request.format == "mp3"
        data = {"url": request.url, "audio_only": audio_only, "format": "best"}
        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(f"{self.base_url}/download", json=data)
            resp.raise_for_status()
            return _parse(resp.json(), self.base_url)

    async def fetch_file_async(self, download_id: str, filename: str) -> bytes:
        """Download the actual file bytes after a successful download call."""
        import urllib.parse
        encoded = urllib.parse.quote(filename, safe="")
        url = f"{self.base_url}/file/{download_id}/{encoded}"
        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.content


def _parse(body: dict, base_url: str) -> DownloadResponse:
    if not body.get("success"):
        return DownloadResponse(status="error", message=body.get("message", "unknown error"))
    return DownloadResponse(
        status="success",
        download_id=body.get("download_id"),
        filename=body.get("filename"),
        title=body.get("title"),
        url=base_url + body.get("download_url", ""),
    )
