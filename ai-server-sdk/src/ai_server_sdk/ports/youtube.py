from abc import ABC, abstractmethod
from typing import List

from ..core.models import (
    DownloadResponse,
    DownloadRequest,
)


class YouTubePort(ABC):
    """Port for YouTube video download service."""

    @abstractmethod
    def health(self) -> dict:
        """Check service health."""
        ...

    @abstractmethod
    def download(self, request: DownloadRequest) -> DownloadResponse:
        """Download a YouTube video."""
        ...

    @abstractmethod
    async def download_async(self, request: DownloadRequest) -> DownloadResponse:
        """Async download."""
        ...
