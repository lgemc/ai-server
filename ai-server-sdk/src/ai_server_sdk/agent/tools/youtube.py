import io
from pathlib import Path
from typing import Optional

from google.adk.tools import ToolContext
from google.genai import types

from ...clients.whisper import WhisperClient
from ...clients.youtube import YouTubeClient
from ._utils import save_tracked_artifact, format_transcript


def _find_audio_for_url(artifacts_dir: Path, app_name: str, user_id: str, url: str):
    """Search artifact store for an audio file whose metadata matches this URL."""
    import json
    root = artifacts_dir / app_name / user_id
    if not root.exists():
        return None, None
    for session_dir in root.iterdir():
        if not session_dir.is_dir():
            continue
        for file_dir in session_dir.iterdir():
            if not file_dir.is_dir():
                continue
            versions = sorted(
                (v for v in file_dir.iterdir() if v.is_dir() and v.name.isdigit()),
                key=lambda v: int(v.name),
            )
            for ver in reversed(versions):
                meta_path = ver / "meta.json"
                if not meta_path.exists():
                    continue
                try:
                    meta = json.loads(meta_path.read_text())
                except Exception:
                    continue
                if meta.get("source_url") == url and meta.get("type") == "audio":
                    data_path = ver / "data"
                    if data_path.exists():
                        return data_path.read_bytes(), file_dir.name
    return None, None


def make_youtube_tools(
    youtube_client: YouTubeClient,
    whisper_client: WhisperClient,
    files_base_url: str = "",
    artifacts_dir=None,
    app_name: str = "ai_agent",
    user_id: str = "default",
) -> list:
    adapter = youtube_client.port
    _artifacts_dir = Path(artifacts_dir) if artifacts_dir else None

    async def download_youtube_video(
        url: str,
        tool_context: ToolContext,
        audio_only: bool = False,
    ) -> dict:
        """Download a YouTube video and save it as an artifact.

        Args:
            url: YouTube video URL.
            audio_only: True to download audio only (mp3). Defaults to False (mp4).

        Returns:
            dict with 'artifact' (filename), 'title', 'url', and 'status'.
        """
        fmt = "mp3" if audio_only else "mp4"
        resp = await youtube_client.download_async(url, format=fmt)
        if resp.status != "success" or not resp.download_id:
            return {"status": resp.status, "message": resp.message}

        raw = await adapter.fetch_file_async(resp.download_id, resp.filename)
        mime = "audio/mpeg" if audio_only else "video/mp4"
        filename = resp.filename or f"video.{fmt}"

        version = await save_tracked_artifact(
            tool_context, filename,
            artifact=types.Part(inline_data=types.Blob(data=raw, mime_type=mime)),
            meta={"type": "audio" if audio_only else "video", "title": resp.title, "source_url": url},
            files_base_url=files_base_url, app_name=app_name, user_id=user_id,
        )
        file_url = f"{files_base_url}/{app_name}/{user_id}/{getattr(tool_context, 'session_id', '')}/{filename}/{version}/data"
        return {"status": "success", "artifact": filename, "title": resp.title, "url": file_url}

    async def transcribe_youtube_video(
        url: str,
        tool_context: ToolContext,
        language: Optional[str] = None,
    ) -> dict:
        """Download a YouTube video and transcribe its audio.

        If the audio was already downloaded in a previous session, it reuses
        the existing file instead of downloading again. Only downloads when
        no cached copy exists.

        Args:
            url: YouTube video URL.
            language: BCP-47 language code hint e.g. 'en', 'es'. Optional.
        """
        raw_audio: Optional[bytes] = None
        audio_filename: Optional[str] = None
        title: str = ""

        # 1. Check if audio already exists in any session
        if _artifacts_dir is not None:
            raw_audio, audio_filename = _find_audio_for_url(_artifacts_dir, app_name, user_id, url)
            if raw_audio:
                # extract title from meta if available (already read above; just use filename)
                title = audio_filename.rsplit(".", 1)[0] if audio_filename else ""

        # 2. Fall back to downloading
        if raw_audio is None:
            resp = await youtube_client.download_async(url, format="mp3")
            if resp.status != "success" or not resp.download_id:
                return {"status": resp.status, "message": resp.message}

            raw_audio = await adapter.fetch_file_async(resp.download_id, resp.filename)
            audio_filename = resp.filename or "audio.mp3"
            title = resp.title or ""

            # save audio artifact to current session
            await save_tracked_artifact(
                tool_context, audio_filename,
                artifact=types.Part(inline_data=types.Blob(data=raw_audio, mime_type="audio/mpeg")),
                meta={"type": "audio", "title": title, "source_url": url},
                files_base_url=files_base_url, app_name=app_name, user_id=user_id,
            )

        # 3. Transcribe
        transcript = await whisper_client.transcribe_async(io.BytesIO(raw_audio), language=language)

        content = format_transcript(transcript.segments, title=title, language=transcript.language or "")
        transcript_filename = (audio_filename or "audio.mp3").rsplit(".", 1)[0] + ".transcript.txt"

        transcript_version = await save_tracked_artifact(
            tool_context, transcript_filename,
            artifact=types.Part(text=content),
            meta={"type": "transcript", "title": title, "source_url": url, "language": transcript.language},
            files_base_url=files_base_url, app_name=app_name, user_id=user_id,
        )

        session_id = getattr(tool_context, "session_id", "")
        transcript_url = f"{files_base_url}/{app_name}/{user_id}/{session_id}/{transcript_filename}/{transcript_version}/data"
        full_text = " ".join(s.text.strip() for s in transcript.segments)

        return {
            "status": "success",
            "title": title,
            "text": full_text,
            "language": transcript.language,
            "audio_artifact": audio_filename,
            "transcript_artifact": transcript_filename,
            "transcript_url": transcript_url,
            "segments": [
                {"start": s.start, "end": s.end, "text": s.text, "speaker": getattr(s, "speaker", None)}
                for s in transcript.segments
            ],
        }

    return [download_youtube_video, transcribe_youtube_video]
