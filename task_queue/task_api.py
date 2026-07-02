"""
Task API — HTTP interface for submitting and querying tasks.

Endpoints:
    POST   /tasks                  Submit a new task
    GET    /tasks                  List tasks (filter: ?status=&type=&limit=&offset=)
    GET    /tasks/{id}             Get a single task
    DELETE /tasks/{id}             Cancel a pending task
    POST   /tasks/{id}/retry       Re-enqueue a failed task
    GET    /tasks/stats            Queue stats
    GET    /health                 Health check
"""

import os
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from task_store import TaskStore
from vocab_api import app as vocab_app

app = FastAPI(title="Task Queue API", version="1.0.0")
app.mount("/vocab", vocab_app)

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
store = TaskStore(redis_url=REDIS_URL)


# ------------------------------------------------------------------
# Schemas
# ------------------------------------------------------------------

class SubmitRequest(BaseModel):
    type: str
    payload: Dict[str, Any] = {}
    priority: int = 0


class TaskResponse(BaseModel):
    id: str
    type: str
    status: str
    payload: Optional[Any] = None
    result: Optional[Any] = None
    error: str = ""
    created_at: Optional[float] = None
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    worker_id: str = ""


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------

@app.get("/health")
def health():
    try:
        store.r.ping()
        return {"status": "ok", "redis": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Redis unavailable: {e}")


@app.get("/tasks/stats")
def get_stats():
    return store.stats()


@app.post("/tasks", response_model=TaskResponse, status_code=201)
def submit_task(req: SubmitRequest):
    task_id = store.submit(req.type, req.payload, priority=req.priority)
    task = store.get(task_id)
    if not task:
        raise HTTPException(status_code=500, detail="Task creation failed")
    return task


@app.get("/tasks", response_model=list[TaskResponse])
def list_tasks(
    status: Optional[str] = Query(None, description="Filter by status: pending|in_progress|done|failed|cancelled"),
    type: Optional[str] = Query(None, description="Filter by task type"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    return store.list(status=status, task_type=type, limit=limit, offset=offset)


@app.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: str):
    task = store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.delete("/tasks/{task_id}")
def cancel_task(task_id: str):
    ok = store.cancel(task_id)
    if not ok:
        task = store.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        raise HTTPException(status_code=409, detail=f"Cannot cancel task with status '{task['status']}'")
    return {"cancelled": True, "id": task_id}


@app.post("/tasks/{task_id}/retry")
def retry_task(task_id: str, priority: int = 0):
    ok = store.requeue(task_id, priority=priority)
    if not ok:
        task = store.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        raise HTTPException(status_code=409, detail=f"Cannot retry task with status '{task['status']}'")
    return {"requeued": True, "id": task_id}
