import os
from typing import Dict, Any

import httpx

from ..ports.comfyui import ComfyUIPort
from ..core.models import ComfyUIQueueResponse, ComfyUIStatusResponse


class ComfyUIAdapter(ComfyUIPort):
    """Adapter for ComfyUI service."""

    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.getenv("COMFYUI_BASE_URL", "http://localhost:8188")

    def health(self) -> ComfyUIStatusResponse:
        """Check service health."""
        try:
            resp = httpx.get(f"{self.base_url}/system_stats", timeout=5.0)
            resp.raise_for_status()
            return ComfyUIStatusResponse(
                status=resp.json().get("status", {}),
                system=resp.json().get("system", {}),
            )
        except Exception as e:
            raise RuntimeError(f"ComfyUI health check failed: {e}")

    def queue_prompt(self, prompt: Dict[str, Any]) -> ComfyUIQueueResponse:
        """Queue a generation prompt."""
        resp = httpx.post(f"{self.base_url}/prompt", json=prompt)
        resp.raise_for_status()
        data = resp.json()
        return ComfyUIQueueResponse(
            queue_running=data.get("queue_running", []),
            queue_pending=data.get("queue_pending", []),
        )

    def get_queue(self) -> ComfyUIQueueResponse:
        """Get current queue status."""
        resp = httpx.get(f"{self.base_url}/queue")
        resp.raise_for_status()
        data = resp.json()
        return ComfyUIQueueResponse(
            queue_running=data.get("queue_running", []),
            queue_pending=data.get("queue_pending", []),
        )

    async def queue_prompt_async(self, prompt: Dict[str, Any]) -> ComfyUIQueueResponse:
        """Async queue prompt."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.base_url}/prompt", json=prompt)
            resp.raise_for_status()
            data = resp.json()
            return ComfyUIQueueResponse(
                queue_running=data.get("queue_running", []),
                queue_pending=data.get("queue_pending", []),
            )
