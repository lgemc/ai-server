import os
from typing import Dict, Any, List

import httpx

from ..ports.sd_forge import SDForgePort
from ..core.models import (
    SDTextToImageRequest,
    SDTextToImageResponse,
    SDImageToImageRequest,
    SDModel,
)


class SDForgeAdapter(SDForgePort):
    """Adapter for SD-Forge image generation service."""

    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.getenv("SD_FORGE_BASE_URL", "http://localhost:5000")

    def health(self) -> List[SDModel]:
        """Check service health / list models."""
        try:
            resp = httpx.get(f"{self.base_url}/health", timeout=5.0)
            resp.raise_for_status()
            models_data = resp.json().get("models", [])
            return [SDModel(**m) for m in models_data]
        except Exception as e:
            raise RuntimeError(f"SD-Forge health check failed: {e}")

    def txt2img(self, request: SDTextToImageRequest) -> SDTextToImageResponse:
        """Generate image from text prompt."""
        data = request.model_dump()
        resp = httpx.post(f"{self.base_url}/sdapi/v1/txt2img", json=data)
        resp.raise_for_status()
        return SDTextToImageResponse(**resp.json())

    def img2img(self, request: SDImageToImageRequest) -> SDTextToImageResponse:
        """Generate image from image."""
        data = request.model_dump()
        resp = httpx.post(f"{self.base_url}/sdapi/v1/img2img", json=data)
        resp.raise_for_status()
        return SDTextToImageResponse(**resp.json())

    async def txt2img_async(
        self, request: SDTextToImageRequest
    ) -> SDTextToImageResponse:
        """Async txt2img."""
        async with httpx.AsyncClient() as client:
            data = request.model_dump()
            resp = await client.post(f"{self.base_url}/sdapi/v1/txt2img", json=data)
            resp.raise_for_status()
            return SDTextToImageResponse(**resp.json())

    async def img2img_async(
        self, request: SDImageToImageRequest
    ) -> SDTextToImageResponse:
        """Async img2img."""
        async with httpx.AsyncClient() as client:
            data = request.model_dump()
            resp = await client.post(f"{self.base_url}/sdapi/v1/img2img", json=data)
            resp.raise_for_status()
            return SDTextToImageResponse(**resp.json())
