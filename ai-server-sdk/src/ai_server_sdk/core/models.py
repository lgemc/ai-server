from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum


class WordTiming(BaseModel):
    """Timing information for a single word."""
    word: str
    start: float
    end: float
    score: float
    speaker: Optional[str] = None


class Segment(BaseModel):
    """A transcribed text segment with timing."""
    start: float
    end: float
    text: str
    words: Optional[List[WordTiming]] = None
    speaker: Optional[str] = None


class TranscribeResponse(BaseModel):
    """Response from Whisper transcription service."""
    status: str = "success"
    language: Optional[str] = None
    segments: List[Segment]


class TranscribeRequest(BaseModel):
    """Request for transcription."""
    language: Optional[str] = None  # e.g., "en", "es", "fr"


# ─── YouTube Models ───────────────────────────────────────────────────────────

class DownloadResponse(BaseModel):
    """Response from YouTube download service."""
    status: str
    url: Optional[str] = None
    message: Optional[str] = None


class DownloadRequest(BaseModel):
    """Request to download a YouTube video."""
    url: str
    format: str = "mp4"


# ─── TTS Models ───────────────────────────────────────────────────────────────

class TTSVoice(str, Enum):
    """Available TTS voices."""
    ALLOY = "alloy"
    ECHO = "echo"
    FABLE = "fable"
    ONYX = "onyx"
    NOVA = "nova"
    SHIMMER = "shimmer"


class TTSSResponseFormat(str, Enum):
    """Output format options."""
    MP3 = "mp3"
    OPUS = "opus"
    AAC = "aac"
    FLAC = "flac"


class TTSResponse(BaseModel):
    """Response from TTS service - contains audio bytes."""
    audio_data: bytes
    content_type: str = "audio/mpeg"


class TTSRequest(BaseModel):
    """Request for text-to-speech synthesis."""
    input: str  # text to synthesize
    model: str = "tts-1"
    voice: TTSVoice = TTSVoice.ALLOY
    response_format: TTSSResponseFormat = TTSSResponseFormat.MP3
    speed: Optional[float] = None


# ─── ComfyUI Models ───────────────────────────────────────────────────────────

class ComfyUIPrompt(BaseModel):
    """A ComfyUI workflow node."""
    class_type: str
    inputs: Dict[str, Any]


class ComfyUIQueueResponse(BaseModel):
    """Response from ComfyUI queue endpoint."""
    queue_running: List[list]
    queue_pending: List[list]


class ComfyUIStatusResponse(BaseModel):
    """Overall status from ComfyUI."""
    status: Dict[str, Any]
    system: Dict[str, Any]


# ─── SD-Forge Models ──────────────────────────────────────────────────────────

class SDModel(BaseModel):
    """A Stable Diffusion model."""
    model_name: str
    title: str
    model_hash: str
    parameter_count: int
    device: str


class SDImageResult(BaseModel):
    """An image result from generation."""
    image: str  # base64 encoded
    finish_reason: str = "SUCCESS"
    seed: int = -1


class SDTextToImageResponse(BaseModel):
    """Response from txt2img endpoint."""
    artifacts: List[SDImageResult]
    info: str


class SDTextToImageRequest(BaseModel):
    """Request for text-to-image generation."""
    prompt: str
    negative_prompt: str = ""
    steps: int = 20
    cfg_scale: float = 7.0
    width: int = 1024
    height: int = 1024
    sampler_name: str = "Euler a"
    seed: int = -1


class SDImageToImageRequest(SDTextToImageRequest):
    """Request for image-to-image generation."""
    init_images: List[str]  # base64 encoded images
    denoising_strength: float = 0.75


# ─── Ollama Models ────────────────────────────────────────────────────────────

class OllamaMessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class OllamaMessage(BaseModel):
    """A chat message."""
    role: OllamaMessageRole
    content: str


class OllamaMessageResponse(BaseModel):
    """A message in the response."""
    role: str
    content: str


class OllamaChatResponse(BaseModel):
    """Response from Ollama chat."""
    model: str
    created_at: str
    message: OllamaMessageResponse
    done: bool


class OllamaOpenAIChatResponse(BaseModel):
    """OpenAI-compatible chat response."""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Dict[str, int]


class OllamaTag(BaseModel):
    """Information about an available Ollama model."""
    model: str
    name: str
    size: int
    digest: str
    modelfile: str = ""
    parameters: str = ""
    template: str = ""
    system: str = ""
    license: str = ""
    details: Dict[str, Any] = Field(default_factory=dict)


class OllamaTagsResponse(BaseModel):
    """Response listing available Ollama models."""
    models: List[OllamaTag]


# ─── Chat Message (shared across LLM providers) ───────────────────────────────

class ChatMessage(BaseModel):
    """A chat message (request)."""
    role: str  # "user", "assistant", "system"
    content: str


class CompletionRequest(BaseModel):
    """Request for text completion."""
    prompt: str
    model: str
    max_tokens: int = 64
    temperature: float = 0.0
