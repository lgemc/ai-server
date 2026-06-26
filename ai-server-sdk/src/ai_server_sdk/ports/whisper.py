from abc import ABC, abstractmethod
from typing import BinaryIO, AsyncIterator, Iterator

from ..core.models import (
    TranscribeResponse,
    TranscribeRequest,
)


class WhisperPort(ABC):
    """Port for Whisper transcription service."""

    @abstractmethod
    def health(self) -> dict:
        """Check service health."""
        ...

    @abstractmethod
    def transcribe(
        self,
        audio_file: BinaryIO,
        request: TranscribeRequest = None,
    ) -> TranscribeResponse:
        """Transcribe audio file to text."""
        ...

    @abstractmethod
    async def transcribe_async(
        self,
        audio_file: BinaryIO,
        request: TranscribeRequest = None,
    ) -> TranscribeResponse:
        """Async transcription."""
        ...
