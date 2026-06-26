import os
import time
from datetime import datetime, timezone
from typing import Optional

from google.adk.tools import ToolContext
from google.genai import types


async def save_tracked_artifact(
    tool_context: ToolContext,
    filename: str,
    artifact: types.Part,
    meta: dict,
    files_base_url: str = "",
    app_name: str = "ai_agent",
    user_id: str = "default",
) -> int:
    """Save artifact and record it in session state so the agent tracks all files."""
    version = await tool_context.save_artifact(filename=filename, artifact=artifact)

    session_id = tool_context.session_id if hasattr(tool_context, "session_id") else "unknown"
    file_url = (
        f"{files_base_url}/{app_name}/{user_id}/{session_id}/{filename}/{version}/data"
        if files_base_url
        else ""
    )

    entry = {
        "filename": filename,
        "version": version,
        "url": file_url,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        **meta,
    }

    files: list = tool_context.state.get("files", [])
    # replace if same filename already tracked, otherwise append
    existing = next((i for i, f in enumerate(files) if f["filename"] == filename), None)
    if existing is not None:
        files[existing] = entry
    else:
        files.append(entry)
    tool_context.state["files"] = files

    return version


def format_transcript(segments, title: str = "", language: str = "") -> str:
    """Render segments (with optional speaker) into a readable transcript file."""
    lines = []
    if title:
        lines.append(f"TRANSCRIPT: {title}")
    if language:
        lines.append(f"Language: {language}")
    lines.append(f"Saved: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("")

    for seg in segments:
        start = _ts(seg.start)
        end = _ts(seg.end)
        speaker = getattr(seg, "speaker", None) or ""
        label = f" | {speaker}" if speaker else ""
        lines.append(f"[{start} → {end}{label}] {seg.text.strip()}")

    return "\n".join(lines)


def _ts(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"
