import os
from typing import Optional, List

from ..ports.sd_forge import SDForgePort
from ..adapters.sd_forge import SDForgeAdapter
from ..core.models import (
    SDTextToImageRequest,
    SDTextToImageResponse,
    SDImageToImageRequest,
    SDModel,
)


class SDForgeClient:
    """
    User-facing client for SD-Forge image generation.

    Usage:
        client = SDForgeClient(base_url="http://localhost:5000")
        result = client.txt2img("a cat in a garden", steps=30)
        # result.artifacts[0].image is base64 encoded
    """

    def __init__(self, base_url: Optional[str] = None):
        self._port: SDForgePort = SDForgeAdapter(base_url)

    @property
    def port(self) -> SDForgePort:
        return self._port

    def health(self) -> List[SDModel]:
        """Check service health / list models."""
        return self._port.health()

    def txt2img(
        self,
        prompt: str,
        negative_prompt: str = "",
        steps: int = 20,
        cfg_scale: float = 7.0,
        width: int = 1024,
        height: int = 1024,
        sampler_name: str = "Euler a",
        seed: int = -1,
    ) -> SDTextToImageResponse:
        """Generate image from text prompt."""
        request = SDTextToImageRequest(
            prompt=prompt,
            negative_prompt=negative_prompt,
            steps=steps,
            cfg_scale=cfg_scale,
            width=width,
            height=height,
            sampler_name=sampler_name,
            seed=seed,
        )
        return self._port.txt2img(request)

    def img2img(
        self,
        prompt: str,
        init_images: List[str],
        negative_prompt: str = "",
        steps: int = 20,
        cfg_scale: float = 7.0,
        width: int = 1024,
        height: int = 1024,
        sampler_name: str = "Euler a",
        seed: int = -1,
        denoising_strength: float = 0.75,
    ) -> SDTextToImageResponse:
        """Generate image from image."""
        request = SDImageToImageRequest(
            prompt=prompt,
            negative_prompt=negative_prompt,
            steps=steps,
            cfg_scale=cfg_scale,
            width=width,
            height=height,
            sampler_name=sampler_name,
            seed=seed,
            init_images=init_images,
            denoising_strength=denoising_strength,
        )
        return self._port.img2img(request)

    async def txt2img_async(
        self,
        prompt: str,
        negative_prompt: str = "",
        steps: int = 20,
        cfg_scale: float = 7.0,
        width: int = 1024,
        height: int = 1024,
        sampler_name: str = "Euler a",
        seed: int = -1,
    ) -> SDTextToImageResponse:
        """Async txt2img."""
        request = SDTextToImageRequest(
            prompt=prompt,
            negative_prompt=negative_prompt,
            steps=steps,
            cfg_scale=cfg_scale,
            width=width,
            height=height,
            sampler_name=sampler_name,
            seed=seed,
        )
        return await self._port.txt2img_async(request)

    async def img2img_async(
        self,
        prompt: str,
        init_images: List[str],
        negative_prompt: str = "",
        steps: int = 20,
        cfg_scale: float = 7.0,
        width: int = 1024,
        height: int = 1024,
        sampler_name: str = "Euler a",
        seed: int = -1,
        denoising_strength: float = 0.75,
    ) -> SDTextToImageResponse:
        """Async img2img."""
        request = SDImageToImageRequest(
            prompt=prompt,
            negative_prompt=negative_prompt,
            steps=steps,
            cfg_scale=cfg_scale,
            width=width,
            height=height,
            sampler_name=sampler_name,
            seed=seed,
            init_images=init_images,
            denoising_strength=denoising_strength,
        )
        return await self._port.img2img_async(request)
