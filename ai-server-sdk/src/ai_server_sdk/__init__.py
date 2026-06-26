# AI Server SDK — Hexagonal Architecture
#
# Ports (interfaces) are in ai_server_sdk.ports
# Adapters (implementations) are in ai_server_sdk.adapters
# User-facing clients are in ai_server_sdk.clients
# Agent (ADK-backed) is in ai_server_sdk.agent

from ai_server_sdk.core.models import (
    # Whisper
    Segment,
    WordTiming,
    TranscribeResponse,
    TranscribeRequest,
    # YouTube
    DownloadResponse,
    DownloadRequest,
    # TTS
    TTSRequest,
    TTSResponse,
    TTSVoice,
    TTSSResponseFormat,
    # ComfyUI
    ComfyUIPrompt,
    ComfyUIQueueResponse,
    ComfyUIStatusResponse,
    # SD-Forge
    SDModel,
    SDImageResult,
    SDTextToImageRequest,
    SDTextToImageResponse,
    SDImageToImageRequest,
    # Ollama / shared chat models (kept for schema compatibility)
    OllamaMessage,
    OllamaMessageRole,
    OllamaChatResponse,
    OllamaOpenAIChatResponse,
    OllamaTag,
    OllamaTagsResponse,
    # Chat (shared)
    ChatMessage,
    CompletionRequest,
)

from ai_server_sdk.clients import (
    WhisperClient,
    YouTubeClient,
    TTSClient,
    ComfyUIClient,
    SDForgeClient,
)

from ai_server_sdk.ports import (
    WhisperPort,
    YouTubePort,
    TTSPort,
    ComfyUIPort,
    SDForgePort,
)

from ai_server_sdk.adapters import (
    WhisperAdapter,
    YouTubeAdapter,
    TTSAdapter,
    ComfyUIAdapter,
    SDForgeAdapter,
)

from ai_server_sdk import agent  # noqa: F401

__all__ = [
    # Models
    "Segment",
    "WordTiming",
    "TranscribeResponse",
    "TranscribeRequest",
    "DownloadResponse",
    "DownloadRequest",
    "TTSRequest",
    "TTSResponse",
    "TTSVoice",
    "TTSSResponseFormat",
    "ComfyUIPrompt",
    "ComfyUIQueueResponse",
    "ComfyUIStatusResponse",
    "SDModel",
    "SDImageResult",
    "SDTextToImageRequest",
    "SDTextToImageResponse",
    "SDImageToImageRequest",
    "OllamaMessage",
    "OllamaMessageRole",
    "OllamaChatResponse",
    "OllamaOpenAIChatResponse",
    "OllamaTag",
    "OllamaTagsResponse",
    "ChatMessage",
    "CompletionRequest",
    # Clients
    "WhisperClient",
    "YouTubeClient",
    "TTSClient",
    "ComfyUIClient",
    "SDForgeClient",
    # Ports
    "WhisperPort",
    "YouTubePort",
    "TTSPort",
    "ComfyUIPort",
    "SDForgePort",
    # Adapters
    "WhisperAdapter",
    "YouTubeAdapter",
    "TTSAdapter",
    "ComfyUIAdapter",
    "SDForgeAdapter",
    # Agent
    "agent",
]
