import os
from pathlib import Path

APP_NAME = os.getenv("AGENT_APP_NAME", "ai_agent")
USER_ID = os.getenv("AGENT_USER_ID", "default")
MODEL = os.getenv("AGENT_MODEL", "openai/gpt-oss-120b")
DB_URL = os.getenv("AGENT_DB_URL", "postgresql+asyncpg://agent:agent@agent-postgres:5432/agent")
ARTIFACTS_DIR = Path(os.getenv("AGENT_ARTIFACTS_DIR", "/data/artifacts"))
WHISPER_URL = os.getenv("WHISPER_BASE_URL", "http://whisper-api:8003")
TTS_URL = os.getenv("TTS_BASE_URL", "http://tts-api:4123")
YOUTUBE_URL = os.getenv("YOUTUBE_BASE_URL", "http://youtube-api:8000")
FILES_BASE_URL = os.getenv("AGENT_FILES_BASE_URL", "http://localhost:8091")
