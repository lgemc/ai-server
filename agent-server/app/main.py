import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import config
from .routers import sessions, chat, artifacts

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)


log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from ai_server_sdk.agent import create_runner
    config.ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    log.info("Starting agent — model=%s db=%s", config.MODEL, config.DB_URL)
    app.state.runner = create_runner(
        model=config.MODEL,
        app_name=config.APP_NAME,
        user_id=config.USER_ID,
        db_url=config.DB_URL,
        artifacts_dir=config.ARTIFACTS_DIR,
        whisper_url=config.WHISPER_URL,
        tts_url=config.TTS_URL,
        youtube_url=config.YOUTUBE_URL,
        files_base_url=config.FILES_BASE_URL,
    )
    yield


app = FastAPI(title="AI Agent Server", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
app.include_router(chat.router, prefix="/api/sessions", tags=["chat"])
app.include_router(artifacts.router, prefix="/api/artifacts", tags=["artifacts"])


@app.get("/health")
async def health():
    return {"status": "ok"}
