from abc import ABC, abstractmethod

from ..core.models import TTSRequest, TTSResponse


class TTSPort(ABC):
    """Port for Text-to-Speech service."""

    @abstractmethod
    def health(self) -> dict:
        """Check service health."""
        ...

    @abstractmethod
    def synthesize(self, request: TTSRequest) -> TTSResponse:
        """Synthesize speech from text."""
        ...

    @abstractmethod
    async def synthesize_async(self, request: TTSRequest) -> TTSResponse:
        """Async synthesis."""
        ...
