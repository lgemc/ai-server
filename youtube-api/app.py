import os
import tempfile
import uuid
import yt_dlp
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional

app = FastAPI(
    title="YouTube Download API",
    description="API to download YouTube videos using yt-dlp",
    version="1.0.0"
)

# Download directory
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "/tmp/youtube-downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


class DownloadRequest(BaseModel):
    url: str
    format: Optional[str] = "best"
    audio_only: Optional[bool] = False


class VideoInfo(BaseModel):
    url: str


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "youtube-api"}


@app.post("/info")
async def get_video_info(request: VideoInfo):
    """
    Get video information without downloading.

    - **url**: YouTube video URL
    """
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(request.url, download=False)

            return JSONResponse(content={
                "success": True,
                "title": info.get("title"),
                "duration": info.get("duration"),
                "uploader": info.get("uploader"),
                "view_count": info.get("view_count"),
                "thumbnail": info.get("thumbnail"),
                "description": info.get("description", "")[:500],
                "formats": [
                    {
                        "format_id": f.get("format_id"),
                        "ext": f.get("ext"),
                        "resolution": f.get("resolution"),
                        "filesize": f.get("filesize"),
                        "format_note": f.get("format_note"),
                    }
                    for f in info.get("formats", [])[:20]
                ]
            })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get video info: {str(e)}")


@app.post("/download")
async def download_video(request: DownloadRequest):
    """
    Download a YouTube video.

    - **url**: YouTube video URL
    - **format**: Format selection (default: 'best')
    - **audio_only**: If True, download only audio as mp3
    """
    download_id = str(uuid.uuid4())
    output_dir = os.path.join(DOWNLOAD_DIR, download_id)
    os.makedirs(output_dir, exist_ok=True)

    output_template = os.path.join(output_dir, "%(title)s.%(ext)s")

    ydl_opts = {
        "outtmpl": output_template,
        "quiet": True,
        "no_warnings": True,
    }

    if request.audio_only:
        ydl_opts.update({
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        })
    else:
        ydl_opts["format"] = request.format

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(request.url, download=True)

            # Find the downloaded file
            files = os.listdir(output_dir)
            if not files:
                raise HTTPException(status_code=500, detail="Download completed but no file found")

            filename = files[0]
            filepath = os.path.join(output_dir, filename)

            return JSONResponse(content={
                "success": True,
                "download_id": download_id,
                "title": info.get("title"),
                "filename": filename,
                "download_url": f"/file/{download_id}/{filename}"
            })
    except yt_dlp.utils.DownloadError as e:
        raise HTTPException(status_code=400, detail=f"Download failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")


@app.get("/file/{download_id}/{filename}")
async def get_file(download_id: str, filename: str):
    """
    Retrieve a downloaded file.

    - **download_id**: The download ID returned from /download
    - **filename**: The filename returned from /download
    """
    filepath = os.path.join(DOWNLOAD_DIR, download_id, filename)

    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")

    # Security check - prevent path traversal
    real_path = os.path.realpath(filepath)
    if not real_path.startswith(os.path.realpath(DOWNLOAD_DIR)):
        raise HTTPException(status_code=403, detail="Access denied")

    return FileResponse(
        filepath,
        filename=filename,
        media_type="application/octet-stream"
    )


@app.delete("/file/{download_id}")
async def delete_file(download_id: str):
    """
    Delete a downloaded file to free up space.

    - **download_id**: The download ID returned from /download
    """
    dirpath = os.path.join(DOWNLOAD_DIR, download_id)

    if not os.path.exists(dirpath):
        raise HTTPException(status_code=404, detail="Download not found")

    # Security check - prevent path traversal
    real_path = os.path.realpath(dirpath)
    if not real_path.startswith(os.path.realpath(DOWNLOAD_DIR)):
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        import shutil
        shutil.rmtree(dirpath)
        return {"success": True, "message": "File deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete: {str(e)}")


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "YouTube Download API",
        "endpoints": {
            "/": "This information",
            "/health": "Health check",
            "/info": "POST - Get video information",
            "/download": "POST - Download a video",
            "/file/{download_id}/{filename}": "GET - Retrieve downloaded file",
            "/file/{download_id}": "DELETE - Delete downloaded file",
            "/docs": "Swagger UI documentation"
        }
    }
