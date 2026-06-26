import json
import mimetypes
import time
from pathlib import Path
from typing import Any, Optional

from google.adk.artifacts.base_artifact_service import ArtifactVersion, BaseArtifactService
from google.genai import types


class LocalFsArtifactService(BaseArtifactService):
    """Artifact service backed by the local filesystem.

    Layout:
        {base_dir}/{app}/{user}/user/{filename}/{version}         (user-scoped)
        {base_dir}/{app}/{user}/{session}/{filename}/{version}    (session-scoped)

    Each version directory contains:
        data     — raw bytes of the artifact
        meta.json — ArtifactVersion metadata
    """

    def __init__(self, base_dir: str | Path = ".artifacts"):
        self._base = Path(base_dir)

    # ── internal helpers ──────────────────────────────────────────────────────

    def _scope(self, session_id: Optional[str]) -> str:
        return session_id if session_id else "user"

    def _artifact_dir(self, app_name: str, user_id: str, filename: str, session_id: Optional[str]) -> Path:
        return self._base / app_name / user_id / self._scope(session_id) / filename

    def _version_dir(self, artifact_dir: Path, version: int) -> Path:
        return artifact_dir / str(version)

    def _next_version(self, artifact_dir: Path) -> int:
        if not artifact_dir.exists():
            return 0
        existing = [int(p.name) for p in artifact_dir.iterdir() if p.is_dir() and p.name.isdigit()]
        return max(existing) + 1 if existing else 0

    def _read_meta(self, vdir: Path) -> Optional[ArtifactVersion]:
        meta_file = vdir / "meta.json"
        if not meta_file.exists():
            return None
        data = json.loads(meta_file.read_text())
        return ArtifactVersion(**data)

    # ── BaseArtifactService implementation ───────────────────────────────────

    async def save_artifact(
        self,
        *,
        app_name: str,
        user_id: str,
        filename: str,
        artifact: types.Part | dict[str, Any],
        session_id: Optional[str] = None,
        custom_metadata: Optional[dict[str, Any]] = None,
    ) -> int:
        if isinstance(artifact, dict):
            artifact = types.Part(**artifact)

        adir = self._artifact_dir(app_name, user_id, filename, session_id)
        version = self._next_version(adir)
        vdir = self._version_dir(adir, version)
        vdir.mkdir(parents=True, exist_ok=True)

        if artifact.inline_data and artifact.inline_data.data:
            (vdir / "data").write_bytes(artifact.inline_data.data)
            mime_type = artifact.inline_data.mime_type
        elif artifact.text is not None:
            (vdir / "data").write_bytes(artifact.text.encode())
            mime_type = "text/plain"
        else:
            (vdir / "data").write_bytes(b"")
            mime_type = None

        meta = ArtifactVersion(
            version=version,
            canonical_uri=f"file://{(vdir / 'data').absolute()}",
            custom_metadata=custom_metadata or {},
            create_time=time.time(),
            mime_type=mime_type,
        )
        (vdir / "meta.json").write_text(meta.model_dump_json())
        return version

    async def load_artifact(
        self,
        *,
        app_name: str,
        user_id: str,
        filename: str,
        session_id: Optional[str] = None,
        version: Optional[int] = None,
    ) -> Optional[types.Part]:
        adir = self._artifact_dir(app_name, user_id, filename, session_id)
        if not adir.exists():
            return None

        if version is None:
            versions = [int(p.name) for p in adir.iterdir() if p.is_dir() and p.name.isdigit()]
            if not versions:
                return None
            version = max(versions)

        vdir = self._version_dir(adir, version)
        meta = self._read_meta(vdir)
        data_file = vdir / "data"
        if not data_file.exists() or not meta:
            return None

        raw = data_file.read_bytes()
        if meta.mime_type == "text/plain":
            return types.Part(text=raw.decode())
        return types.Part(inline_data=types.Blob(data=raw, mime_type=meta.mime_type or "application/octet-stream"))

    async def list_artifact_keys(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: Optional[str] = None,
    ) -> list[str]:
        keys: list[str] = []
        scopes = [self._scope(session_id), "user"] if session_id else ["user"]
        for scope in set(scopes):
            scope_dir = self._base / app_name / user_id / scope
            if scope_dir.exists():
                keys.extend(p.name for p in scope_dir.iterdir() if p.is_dir())
        return sorted(set(keys))

    async def delete_artifact(
        self,
        *,
        app_name: str,
        user_id: str,
        filename: str,
        session_id: Optional[str] = None,
    ) -> None:
        import shutil
        adir = self._artifact_dir(app_name, user_id, filename, session_id)
        if adir.exists():
            shutil.rmtree(adir)

    async def list_versions(
        self,
        *,
        app_name: str,
        user_id: str,
        filename: str,
        session_id: Optional[str] = None,
    ) -> list[int]:
        adir = self._artifact_dir(app_name, user_id, filename, session_id)
        if not adir.exists():
            return []
        return sorted(int(p.name) for p in adir.iterdir() if p.is_dir() and p.name.isdigit())

    async def list_artifact_versions(
        self,
        *,
        app_name: str,
        user_id: str,
        filename: str,
        session_id: Optional[str] = None,
    ) -> list[ArtifactVersion]:
        adir = self._artifact_dir(app_name, user_id, filename, session_id)
        if not adir.exists():
            return []
        result = []
        for v in sorted(int(p.name) for p in adir.iterdir() if p.is_dir() and p.name.isdigit()):
            meta = self._read_meta(self._version_dir(adir, v))
            if meta:
                result.append(meta)
        return result

    async def get_artifact_version(
        self,
        *,
        app_name: str,
        user_id: str,
        filename: str,
        session_id: Optional[str] = None,
        version: Optional[int] = None,
    ) -> Optional[ArtifactVersion]:
        adir = self._artifact_dir(app_name, user_id, filename, session_id)
        if not adir.exists():
            return None
        if version is None:
            versions = [int(p.name) for p in adir.iterdir() if p.is_dir() and p.name.isdigit()]
            if not versions:
                return None
            version = max(versions)
        return self._read_meta(self._version_dir(adir, version))
