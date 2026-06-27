import json
from pathlib import Path
from google.adk.tools import ToolContext


def _fuzzy_match(query: str, files: list) -> dict | None:
    """Return the best matching file entry for a loose query string."""
    q = query.lower()
    # exact filename match first
    for f in files:
        if f["filename"].lower() == q:
            return f
    # substring match in filename or title
    scored = []
    for f in files:
        hits = sum(1 for word in q.split() if word in f["filename"].lower() or word in (f.get("title") or "").lower())
        if hits:
            scored.append((hits, f))
    if scored:
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1]
    return None


def make_artifact_tools(artifacts_dir: str | Path = "", files_base_url: str = "", app_name: str = "ai_agent", user_id: str = "default") -> list:
    """Tools for the agent to inspect and read its own artifacts."""
    _base = Path(artifacts_dir) if artifacts_dir else None

    def _find_in_fs(query: str) -> dict | None:
        """Search all sessions on disk for best filename match, return a file entry dict."""
        if _base is None:
            return None
        root = _base / app_name / user_id
        if not root.exists():
            return None
        q = query.lower()
        best = None
        best_score = 0
        for session_dir in root.iterdir():
            if not session_dir.is_dir():
                continue
            for file_dir in session_dir.iterdir():
                if not file_dir.is_dir():
                    continue
                filename = file_dir.name
                score = sum(1 for w in q.split() if w in filename.lower())
                if score > best_score:
                    best_score = score
                    versions = sorted(
                        (v for v in file_dir.iterdir() if v.is_dir() and v.name.isdigit()),
                        key=lambda v: int(v.name),
                    )
                    version = int(versions[-1].name) if versions else 0
                    url = f"{files_base_url}/{app_name}/{user_id}/{session_dir.name}/{filename}/{version}/data" if files_base_url else ""
                    best = {"filename": filename, "session_id": session_dir.name, "version": version, "url": url}
        return best if best_score > 0 else None

    async def list_session_files(tool_context: ToolContext) -> dict:
        """List files saved in the CURRENT session only (not across all sessions).

        For a global listing across all sessions use browse_all_files instead.

        Returns:
            dict with 'files' list. Each entry has filename, type, url,
            title (if any), and saved_at.
        """
        files = tool_context.state.get("files", [])
        return {"count": len(files), "files": files}

    async def read_artifact_text(
        filename: str,
        tool_context: ToolContext,
    ) -> dict:
        """Read the text content of a saved artifact by filename.

        Use this to retrieve a transcript, summary, or any text artifact
        that was previously saved in this session.

        Args:
            filename: The artifact filename as returned by list_session_files
                or any transcription/download tool.

        Returns:
            dict with 'text' content of the artifact, or 'error' if not found
            or not a text artifact.
        """
        part = await tool_context.load_artifact(filename=filename)
        if part is None:
            return {"error": f"Artifact '{filename}' not found in this session."}
        if part.text is not None:
            return {"filename": filename, "text": part.text}
        if part.inline_data:
            try:
                return {"filename": filename, "text": part.inline_data.data.decode("utf-8")}
            except UnicodeDecodeError:
                return {"error": f"Artifact '{filename}' is binary (mime: {part.inline_data.mime_type}). Use the download URL instead."}
        return {"error": "Artifact has no readable content."}

    async def find_and_read_artifact(
        query: str,
        tool_context: ToolContext,
    ) -> dict:
        """Find a session artifact by approximate name or title and read its text content.

        Use this when the user refers to a file loosely, e.g. "the Training Agents
        transcript" or "the audio from yesterday". Matches against filename and title
        using word overlap — typos and partial names are fine.

        Args:
            query: Loose description or partial filename to search for.

        Returns:
            dict with 'filename', 'text' of the matched artifact, and 'url'.
            If no match, returns 'candidates' list so you can ask the user to clarify.
        """
        files = tool_context.state.get("files", [])
        match = _fuzzy_match(query, files)

        # If not found in session state, fall back to full filesystem search
        if not match and _base is not None:
            match = _find_in_fs(query)

        if not match:
            return {
                "error": f"No artifact matching '{query}' found across any session.",
                "candidates": [f["filename"] for f in files],
            }

        filename = match["filename"]
        session_id = match.get("session_id", "")

        # Try filesystem read first when session_id is known (cross-session safe)
        if session_id and _base is not None:
            file_dir = _base / app_name / user_id / session_id / filename
            versions = sorted(
                (v for v in file_dir.iterdir() if v.is_dir() and v.name.isdigit()),
                key=lambda v: int(v.name),
            ) if file_dir.exists() else []
            if versions:
                data_path = versions[-1] / "data"
                if data_path.exists():
                    raw = data_path.read_bytes()
                    url = match.get("url", "")
                    try:
                        return {"filename": filename, "session_id": session_id, "url": url, "text": raw.decode("utf-8")}
                    except UnicodeDecodeError:
                        return {"filename": filename, "session_id": session_id, "url": url, "error": "File is binary. Use the URL to download it."}

        part = await tool_context.load_artifact(filename=filename)
        if part is None:
            return {"error": f"Artifact '{filename}' not found."}
        if part.text is not None:
            return {"filename": filename, "url": match.get("url", ""), "text": part.text}
        if part.inline_data:
            try:
                return {"filename": filename, "url": match.get("url", ""), "text": part.inline_data.data.decode("utf-8")}
            except UnicodeDecodeError:
                return {"filename": filename, "url": match.get("url", ""), "error": f"File is binary ({part.inline_data.mime_type}). Use the URL to download it."}
        return {"error": "Artifact has no readable content."}

    async def browse_all_files(query: str = "", tool_context: ToolContext = None) -> dict:
        """List ALL files on the files server across every session — use this by default
        when the user asks 'which files do we have', 'what files exist', 'show me all files',
        or wants to find something from a previous session.

        Also use this before find_and_read_artifact when you are not sure which session
        the file is from. Optionally filter by a search term.

        Args:
            query: Optional filter — returns only files whose name or title
                contains this string (case-insensitive). Leave empty to list all.

        Returns:
            dict with 'files' list. Each entry has session_id, filename, type,
            title, url, and saved_at.
        """
        if _base is None:
            return {"error": "artifacts_dir not configured"}

        results = []
        root = _base / app_name / user_id
        if not root.exists():
            return {"count": 0, "files": []}

        for session_dir in sorted(root.iterdir()):
            if not session_dir.is_dir():
                continue
            session_id = session_dir.name
            for file_dir in sorted(session_dir.iterdir()):
                if not file_dir.is_dir():
                    continue
                filename = file_dir.name
                # find highest version
                versions = sorted(
                    (v for v in file_dir.iterdir() if v.is_dir() and v.name.isdigit()),
                    key=lambda v: int(v.name),
                )
                if not versions:
                    continue
                latest = versions[-1]
                meta_path = latest / "meta.json"
                meta = {}
                if meta_path.exists():
                    try:
                        meta = json.loads(meta_path.read_text())
                    except Exception:
                        pass

                version = int(latest.name)
                url = f"{files_base_url}/{app_name}/{user_id}/{session_id}/{filename}/{version}/data" if files_base_url else ""
                entry = {
                    "session_id": session_id,
                    "filename": filename,
                    "version": version,
                    "url": url,
                    **{k: v for k, v in meta.items() if k not in ("data",)},
                }
                if query:
                    q = query.lower()
                    if q not in filename.lower() and q not in str(meta.get("title", "")).lower():
                        continue
                results.append(entry)

        return {"count": len(results), "files": results}

    async def delete_artifact(filename: str, session_id: str = "", tool_context: ToolContext = None) -> dict:
        """Delete a saved artifact by filename.

        Removes the file from the files server permanently. If session_id is not
        provided, deletes from the current session. Use browse_all_files first to
        confirm the filename and session_id before deleting.

        Args:
            filename: Exact filename of the artifact to delete.
            session_id: Session the file belongs to. Defaults to current session.

        Returns:
            dict with 'deleted' True on success, or 'error' message.
        """
        if _base is None:
            return {"error": "artifacts_dir not configured"}

        sid = session_id or (tool_context.session_id if tool_context and hasattr(tool_context, "session_id") else "")
        if not sid:
            return {"error": "Could not determine session_id"}

        file_dir = _base / app_name / user_id / sid / filename
        if not file_dir.exists():
            return {"error": f"Artifact '{filename}' not found in session {sid}"}

        import shutil
        shutil.rmtree(file_dir)

        # remove from session state tracking if same session
        if tool_context and (not session_id or session_id == getattr(tool_context, "session_id", None)):
            files = tool_context.state.get("files", [])
            tool_context.state["files"] = [f for f in files if f["filename"] != filename]

        return {"deleted": True, "filename": filename, "session_id": sid}

    return [list_session_files, read_artifact_text, find_and_read_artifact, browse_all_files, delete_artifact]
