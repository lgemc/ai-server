from pathlib import Path
from typing import Optional

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService, InMemorySessionService

from ..clients.whisper import WhisperClient
from ..clients.tts import TTSClient
from ..clients.youtube import YouTubeClient
from .services.artifacts import LocalFsArtifactService
from .tools import make_whisper_tools, make_tts_tools, make_youtube_tools, make_artifact_tools


def create_runner(
    model: str,
    app_name: str = "ai_agent",
    user_id: str = "default",
    instruction: str = (
        "You are a helpful personal AI assistant. "
        "You can transcribe audio/video, synthesize speech, download YouTube videos, "
        "and answer questions. "
        "IMPORTANT: Respond directly and concisely. Never narrate your thought process "
        "or explain what you are about to do — just do it. "
        "Only call synthesize_speech when the user explicitly asks for audio output — "
        "never synthesize speech automatically as part of summaries or other tasks. "
        "When working with files, always save results as artifacts and tell the user "
        "the download URL for each file you create. "
        "When the user asks which files exist or what files are available, ALWAYS call "
        "browse_all_files (not list_session_files) — it searches across all sessions. "
        "When the user references a file by partial name or description, use "
        "find_and_read_artifact to locate it before doing further work on it. "
        "When a file is already saved and the user wants it transcribed, use "
        "transcribe_saved_artifact — do not use transcribe_audio (which needs a local path)."
    ),
    whisper_url: Optional[str] = None,
    tts_url: Optional[str] = None,
    youtube_url: Optional[str] = None,
    artifacts_dir: str | Path = ".artifacts",
    db_url: Optional[str] = None,
    files_base_url: str = "",
    extra_tools: Optional[list] = None,
) -> Runner:
    """Create a fully configured ADK Runner backed by local services.

    Args:
        model: litellm model string e.g. 'openai/Qwen/Qwen2.5-72B-Instruct'.
        app_name: Application namespace — scopes sessions and artifacts.
        user_id: User namespace for sessions and artifacts.
        instruction: System prompt for the agent.
        whisper_url: Base URL of the Whisper service.
        tts_url: Base URL of the TTS service.
        youtube_url: Base URL of the YouTube download service.
        artifacts_dir: Local directory for artifact storage.
        db_url: SQLAlchemy async URL for persistent sessions.
            Uses in-memory sessions when None.
        files_base_url: Public base URL of the file server (e.g.
            'http://localhost:8091'). Used to build download URLs returned
            to the agent and stored in session state.
        extra_tools: Additional ADK-compatible tool functions to register.
    """
    whisper = WhisperClient(whisper_url)
    tts = TTSClient(tts_url)
    youtube = YouTubeClient(youtube_url)

    shared = dict(files_base_url=files_base_url, app_name=app_name, user_id=user_id, artifacts_dir=artifacts_dir)

    tools = [
        *make_whisper_tools(whisper, **shared),
        *make_tts_tools(tts),
        *make_youtube_tools(youtube, whisper, **shared),
        *make_artifact_tools(artifacts_dir=artifacts_dir, files_base_url=files_base_url, app_name=app_name, user_id=user_id),
        *(extra_tools or []),
    ]

    agent = LlmAgent(
        name=app_name,
        model=LiteLlm(
            model=model,
            max_tokens=8192,
            temperature=0.6,
        ),
        instruction=instruction,
        tools=tools,
    )

    session_service = (
        DatabaseSessionService(db_url=db_url) if db_url else InMemorySessionService()
    )

    artifact_service = LocalFsArtifactService(base_dir=artifacts_dir)

    return Runner(
        agent=agent,
        app_name=app_name,
        session_service=session_service,
        artifact_service=artifact_service,
    )
