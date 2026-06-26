import mimetypes
from urllib.parse import quote
from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import Response


def _content_disposition(filename: str) -> str:
    try:
        filename.encode("latin-1")
        return f'attachment; filename="{filename}"'
    except UnicodeEncodeError:
        encoded = quote(filename, safe="")
        return f"attachment; filename*=UTF-8''{encoded}"

from .. import config

router = APIRouter()


@router.get("")
async def list_artifacts(req: Request, session_id: str = Query(...)):
    runner = req.app.state.runner
    keys = await runner.artifact_service.list_artifact_keys(
        app_name=config.APP_NAME,
        user_id=config.USER_ID,
        session_id=session_id,
    )
    result = []
    for filename in keys:
        meta = await runner.artifact_service.get_artifact_version(
            app_name=config.APP_NAME,
            user_id=config.USER_ID,
            session_id=session_id,
            filename=filename,
        )
        result.append({
            "filename": filename,
            "mime_type": meta.mime_type if meta else None,
            "version": meta.version if meta else 0,
            "create_time": meta.create_time if meta else None,
        })
    return result


@router.get("/download")
async def download_artifact(
    req: Request,
    session_id: str = Query(...),
    filename: str = Query(...),
    version: int = Query(None),
):
    runner = req.app.state.runner
    part = await runner.artifact_service.load_artifact(
        app_name=config.APP_NAME,
        user_id=config.USER_ID,
        session_id=session_id,
        filename=filename,
        version=version,
    )
    if not part:
        raise HTTPException(status_code=404, detail="Artifact not found")

    if part.text is not None:
        return Response(
            content=part.text.encode(),
            media_type="text/plain",
            headers={"Content-Disposition": _content_disposition(filename)},
        )

    if part.inline_data:
        return Response(
            content=part.inline_data.data,
            media_type=part.inline_data.mime_type or "application/octet-stream",
            headers={"Content-Disposition": _content_disposition(filename)},
        )

    raise HTTPException(status_code=422, detail="Artifact has no downloadable content")
