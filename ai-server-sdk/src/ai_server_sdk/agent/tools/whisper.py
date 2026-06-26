import io
import json
from pathlib import Path
from typing import Optional

from google.adk.tools import ToolContext
from google.genai import types

from ...clients.whisper import WhisperClient
from ._utils import save_tracked_artifact, format_transcript


def _find_in_artifacts(artifacts_dir: Path, app_name: str, user_id: str, query: str):
    """Walk the artifact store and return (raw_bytes, filename, session_id) for the best match."""
    root = artifacts_dir / app_name / user_id
    if not root.exists():
        return None, None, None

    q = query.lower()
    candidates = []
    for session_dir in root.iterdir():
        if not session_dir.is_dir():
            continue
        for file_dir in session_dir.iterdir():
            if not file_dir.is_dir():
                continue
            filename = file_dir.name
            score = sum(1 for w in q.split() if w in filename.lower())
            if score:
                candidates.append((score, session_dir.name, filename, file_dir))

    if not candidates:
        return None, None, None

    candidates.sort(key=lambda x: x[0], reverse=True)
    _, session_id, filename, file_dir = candidates[0]

    versions = sorted(
        (v for v in file_dir.iterdir() if v.is_dir() and v.name.isdigit()),
        key=lambda v: int(v.name),
    )
    if not versions:
        return None, None, None

    data_path = versions[-1] / "data"
    if not data_path.exists():
        return None, None, None

    return data_path.read_bytes(), filename, session_id


def make_whisper_tools(
    client: WhisperClient,
    files_base_url: str = "",
    app_name: str = "ai_agent",
    user_id: str = "default",
    artifacts_dir: str | Path = "",
) -> list:
    _artifacts_dir = Path(artifacts_dir) if artifacts_dir else None

    async def transcribe_audio(
        audio_path: str,
        tool_context: ToolContext,
        language: Optional[str] = None,
    ) -> dict:
        """Transcribe a LOCAL audio or video file at a filesystem path.

        Use transcribe_saved_artifact if the file is already saved as a session
        artifact. Use this only for real local file paths.

        Args:
            audio_path: Absolute path to the audio/video file on disk.
            language: BCP-47 language code hint e.g. 'en', 'es'. Optional.
        """
        with open(audio_path, "rb") as f:
            resp = await client.transcribe_async(f, language=language)

        content = format_transcript(resp.segments, language=resp.language or "")
        filename = audio_path.replace("/", "_").lstrip("_") + ".transcript.txt"
        version = await save_tracked_artifact(
            tool_context, filename,
            artifact=types.Part(text=content),
            meta={"type": "transcript", "source": audio_path},
            files_base_url=files_base_url, app_name=app_name, user_id=user_id,
        )
        url = f"{files_base_url}/{app_name}/{user_id}/{getattr(tool_context, 'session_id', '')}/{filename}/{version}/data"
        full_text = " ".join(s.text.strip() for s in resp.segments)
        return {
            "text": full_text, "language": resp.language,
            "transcript_artifact": filename, "url": url,
            "segments": [{"start": s.start, "end": s.end, "text": s.text, "speaker": getattr(s, "speaker", None)} for s in resp.segments],
        }

    async def transcribe_saved_artifact(
        filename_query: str,
        tool_context: ToolContext,
        language: Optional[str] = None,
    ) -> dict:
        """Transcribe an audio artifact already saved on the files server — works
        across ALL sessions, not just the current one.

        Use this whenever the user wants to transcribe a file that was previously
        downloaded. The filename_query can be a partial name — it fuzzy-matches
        across every session's artifacts. The transcript is saved into the current
        session so it is immediately accessible.

        Args:
            filename_query: Partial or full filename of the saved audio artifact,
                e.g. 'Training Agents' or 'training_agents.mp3'.
            language: BCP-47 language code hint e.g. 'en', 'es'. Optional.
        """
        raw_audio: Optional[bytes] = None
        source_filename: Optional[str] = None

        # 1. Try current session first via ToolContext (fast path)
        part = await tool_context.load_artifact(filename=filename_query)
        if part and part.inline_data:
            raw_audio = part.inline_data.data
            source_filename = filename_query
        else:
            # 2. Cross-session search via filesystem
            if _artifacts_dir is None:
                return {"error": "artifacts_dir not configured; cannot search across sessions."}
            raw_audio, source_filename, found_session = _find_in_artifacts(
                _artifacts_dir, app_name, user_id, filename_query
            )
            if raw_audio is None:
                return {
                    "error": f"No audio artifact matching '{filename_query}' found across any session. "
                             "Use browse_all_files to see what is available."
                }

        resp = await client.transcribe_async(io.BytesIO(raw_audio), language=language)

        content = format_transcript(resp.segments, language=resp.language or "")
        transcript_filename = (source_filename or filename_query).rsplit(".", 1)[0] + ".transcript.txt"

        version = await save_tracked_artifact(
            tool_context, transcript_filename,
            artifact=types.Part(text=content),
            meta={"type": "transcript", "source": source_filename, "language": resp.language},
            files_base_url=files_base_url, app_name=app_name, user_id=user_id,
        )
        url = f"{files_base_url}/{app_name}/{user_id}/{getattr(tool_context, 'session_id', '')}/{transcript_filename}/{version}/data"
        full_text = " ".join(s.text.strip() for s in resp.segments)
        return {
            "status": "success",
            "text": full_text,
            "language": resp.language,
            "transcript_artifact": transcript_filename,
            "transcript_url": url,
            "segments": [{"start": s.start, "end": s.end, "text": s.text, "speaker": getattr(s, "speaker", None)} for s in resp.segments],
        }

    return [transcribe_audio, transcribe_saved_artifact]
