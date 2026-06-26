import os
from typing import Optional, Dict, Any, List

from ..ports.comfyui import ComfyUIPort
from ..adapters.comfyui import ComfyUIAdapter
from ..core.models import ComfyUIQueueResponse, ComfyUIStatusResponse


class ComfyUIClient:
    """
    User-facing client for ComfyUI.

    Usage:
        client = ComfyUIClient(base_url="http://localhost:8188")
        prompt = {"node1": {"class_type": "KSampler", "inputs": {...}}}
        result = client.queue_prompt(prompt)
    """

    def __init__(self, base_url: Optional[str] = None):
        self._port: ComfyUIPort = ComfyUIAdapter(base_url)

    @property
    def port(self) -> ComfyUIPort:
        return self._port

    def health(self) -> ComfyUIStatusResponse:
        """Check service health."""
        return self._port.health()

    def queue_prompt(self, prompt: Dict[str, Any]) -> ComfyUIQueueResponse:
        """Queue a generation prompt."""
        return self._port.queue_prompt(prompt)

    def get_queue(self) -> ComfyUIQueueResponse:
        """Get current queue status."""
        return self._port.get_queue()

    async def queue_prompt_async(self, prompt: Dict[str, Any]) -> ComfyUIQueueResponse:
        """Async queue prompt."""
        return await self._port.queue_prompt_async(prompt)
