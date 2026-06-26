from abc import ABC, abstractmethod
from typing import Any, Dict, List

from ..core.models import (
    ComfyUIQueueResponse,
    ComfyUIStatusResponse,
)


class ComfyUIPort(ABC):
    """Port for ComfyUI service."""

    @abstractmethod
    def health(self) -> ComfyUIStatusResponse:
        """Check service health."""
        ...

    @abstractmethod
    def queue_prompt(self, prompt: Dict[str, Any]) -> ComfyUIQueueResponse:
        """Queue a generation prompt."""
        ...

    @abstractmethod
    def get_queue(self) -> ComfyUIQueueResponse:
        """Get current queue status."""
        ...

    @abstractmethod
    async def queue_prompt_async(self, prompt: Dict[str, Any]) -> ComfyUIQueueResponse:
        """Async queue prompt."""
        ...
