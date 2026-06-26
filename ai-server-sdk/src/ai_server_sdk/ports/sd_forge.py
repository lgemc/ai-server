from abc import ABC, abstractmethod
from typing import List, Dict, Any

from ..core.models import (
    SDTextToImageRequest,
    SDTextToImageResponse,
    SDImageToImageRequest,
    SDModel,
)


class SDForgePort(ABC):
    """Port for SD-Forge image generation service."""

    @abstractmethod
    def health(self) -> List[SDModel]:
        """Check service health / list models."""
        ...

    @abstractmethod
    def txt2img(self, request: SDTextToImageRequest) -> SDTextToImageResponse:
        """Generate image from text prompt."""
        ...

    @abstractmethod
    def img2img(self, request: SDImageToImageRequest) -> SDTextToImageResponse:
        """Generate image from image."""
        ...

    @abstractmethod
    async def txt2img_async(
        self, request: SDTextToImageRequest
    ) -> SDTextToImageResponse:
        """Async txt2img."""
        ...

    @abstractmethod
    async def img2img_async(
        self, request: SDImageToImageRequest
    ) -> SDTextToImageResponse:
        """Async img2img."""
        ...
