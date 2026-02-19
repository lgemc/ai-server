import os
import tempfile
import threading
import time
from uuid import uuid4
from typing import Optional
import whisper
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse

app = FastAPI(
    title="Whisper Transcription API",
    description="API to transcribe audio/video files using OpenAI Whisper",
    version="1.0.0"
)

# Load model at startup (large model by default)
MODEL_NAME = os.getenv("WHISPER_MODEL", "large")
print(f"Loading Whisper model: {MODEL_NAME}")
model = whisper.load_model(MODEL_NAME)
print(f"Model {MODEL_NAME} loaded successfully")

# Job storage (in-memory)
jobs: dict = {}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "model": MODEL_NAME}


@app.post("/transcribe")
async def transcribe(
    file: UploadFile = File(..., description="Audio or video file to transcribe"),
    language: str = Form(default="en", description="Language code (e.g., 'en', 'es', 'fr')"),
    task: str = Form(default="transcribe", description="Task: 'transcribe' or 'translate' (to English)")
):
    """
    Transcribe an audio or video file.

    - **file**: Audio/video file (mp3, mp4, wav, m4a, webm, etc.)
    - **language**: Language code (default: 'en' for English)
    - **task**: 'transcribe' keeps original language, 'translate' translates to English
    """
    if task not in ["transcribe", "translate"]:
        raise HTTPException(status_code=400, detail="Task must be 'transcribe' or 'translate'")

    # Get file extension
    file_ext = os.path.splitext(file.filename)[1] if file.filename else ".tmp"

    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # Transcribe using Whisper
        result = model.transcribe(
            tmp_path,
            language=language,
            task=task,
            verbose=False
        )

        return JSONResponse(content={
            "success": True,
            "filename": file.filename,
            "language": language,
            "task": task,
            "text": result["text"],
            "segments": [
                {
                    "id": seg["id"],
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": seg["text"]
                }
                for seg in result["segments"]
            ]
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
    finally:
        # Clean up temp file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def transcribe_job(job_id: str, file_path: str, language: str, task: str, filename: str):
    """Background job to transcribe audio with progress tracking."""
    try:
        jobs[job_id]["status"] = "loading_audio"

        # Load audio to get duration
        audio = whisper.load_audio(file_path)
        duration = len(audio) / whisper.audio.SAMPLE_RATE
        jobs[job_id]["duration"] = duration
        jobs[job_id]["status"] = "transcribing"
        jobs[job_id]["started_at"] = time.time()

        # Transcribe - whisper processes in ~30s chunks
        result = model.transcribe(
            file_path,
            language=language,
            task=task,
            verbose=False
        )

        # Update progress based on segments as they complete
        segments = [
            {
                "id": seg["id"],
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"]
            }
            for seg in result["segments"]
        ]

        jobs[job_id].update({
            "status": "completed",
            "progress": 100,
            "completed_at": time.time(),
            "result": {
                "success": True,
                "filename": filename,
                "language": language,
                "task": task,
                "duration": duration,
                "text": result["text"],
                "segments": segments
            }
        })
    except Exception as e:
        jobs[job_id].update({
            "status": "failed",
            "error": str(e),
            "completed_at": time.time()
        })
    finally:
        # Clean up temp file
        if os.path.exists(file_path):
            os.unlink(file_path)


@app.post("/transcribe/async")
async def transcribe_async(
    file: UploadFile = File(..., description="Audio or video file to transcribe"),
    language: str = Form(default="en", description="Language code (e.g., 'en', 'es', 'fr')"),
    task: str = Form(default="transcribe", description="Task: 'transcribe' or 'translate'")
):
    """
    Submit an async transcription job.

    Returns a job_id that can be used to poll for progress via /transcribe/status/{job_id}
    """
    if task not in ["transcribe", "translate"]:
        raise HTTPException(status_code=400, detail="Task must be 'transcribe' or 'translate'")

    # Generate job ID
    job_id = str(uuid4())

    # Get file extension and save file
    file_ext = os.path.splitext(file.filename)[1] if file.filename else ".tmp"
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    # Initialize job
    jobs[job_id] = {
        "status": "queued",
        "progress": 0,
        "filename": file.filename,
        "language": language,
        "task": task,
        "created_at": time.time(),
        "result": None,
        "error": None
    }

    # Start background thread
    thread = threading.Thread(
        target=transcribe_job,
        args=(job_id, tmp_path, language, task, file.filename)
    )
    thread.start()

    return {"job_id": job_id, "status": "queued"}


@app.get("/transcribe/status/{job_id}")
async def get_job_status(job_id: str):
    """
    Get the status of an async transcription job.

    Status values: queued, loading_audio, transcribing, completed, failed
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]

    # Calculate estimated progress while transcribing
    if job["status"] == "transcribing" and "duration" in job and "started_at" in job:
        elapsed = time.time() - job["started_at"]
        # Rough estimate: whisper processes ~1x real-time on GPU
        estimated_progress = min(95, (elapsed / job["duration"]) * 100)
        job["progress"] = int(estimated_progress)

    response = {
        "job_id": job_id,
        "status": job["status"],
        "progress": job["progress"],
        "filename": job.get("filename"),
        "duration": job.get("duration"),
        "error": job.get("error")
    }

    if job["status"] == "completed":
        response["result"] = job["result"]

    return response


@app.get("/transcribe/jobs")
async def list_jobs():
    """List all jobs with their current status."""
    return {
        job_id: {
            "status": job["status"],
            "progress": job["progress"],
            "filename": job.get("filename"),
            "created_at": job.get("created_at")
        }
        for job_id, job in jobs.items()
    }


@app.delete("/transcribe/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a completed or failed job from memory."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    if job["status"] not in ["completed", "failed"]:
        raise HTTPException(status_code=400, detail="Cannot delete a running job")

    del jobs[job_id]
    return {"deleted": job_id}


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Whisper Transcription API",
        "model": MODEL_NAME,
        "endpoints": {
            "/": "This information",
            "/health": "Health check",
            "/transcribe": "POST - Synchronous transcription (blocks until done)",
            "/transcribe/async": "POST - Submit async transcription job",
            "/transcribe/status/{job_id}": "GET - Poll job status and progress",
            "/transcribe/jobs": "GET - List all jobs",
            "/transcribe/jobs/{job_id}": "DELETE - Remove completed job",
            "/docs": "Swagger UI documentation"
        }
    }
