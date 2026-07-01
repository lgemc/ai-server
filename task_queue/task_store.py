"""
Task Store — Redis-backed task lifecycle tracking.

Each task lives as a Redis Hash at key  task:{task_id}
A sorted set  tasks:queue:{type}  holds pending task IDs (score = priority)
A sorted set  tasks:index         holds ALL task IDs (score = created_at epoch) for listing

Task fields:
    id          str   unique UUID
    type        str   handler name, e.g. "transcription"
    status      str   pending | in_progress | done | failed | cancelled
    payload     json  arbitrary input data
    result      json  output when done
    error       str   error message when failed
    created_at  float epoch
    started_at  float epoch or None
    finished_at float epoch or None
    worker_id   str   which worker picked it up
"""

import json
import time
import uuid
from typing import Any, Dict, List, Optional

import redis

TASK_TTL = 60 * 60 * 24 * 7  # keep finished tasks for 7 days


class TaskStore:
    def __init__(self, redis_url: str = "redis://redis:6379"):
        self.r = redis.from_url(redis_url, decode_responses=True)

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def submit(self, task_type: str, payload: Dict[str, Any], priority: int = 0) -> str:
        """Submit a new task. Returns the task_id."""
        task_id = str(uuid.uuid4())
        now = time.time()
        task: Dict[str, Any] = {
            "id": task_id,
            "type": task_type,
            "status": "pending",
            "payload": json.dumps(payload),
            "result": "",
            "error": "",
            "created_at": str(now),
            "started_at": "",
            "finished_at": "",
            "worker_id": "",
        }
        pipe = self.r.pipeline()
        pipe.hset(f"task:{task_id}", mapping=task)  # type: ignore[arg-type]
        pipe.expire(f"task:{task_id}", TASK_TTL)
        pipe.zadd(f"tasks:queue:{task_type}", {task_id: priority})
        pipe.zadd("tasks:index", {task_id: now})
        pipe.execute()
        return task_id

    def claim(self, task_type: str, worker_id: str) -> Optional[Dict[str, Any]]:
        """
        Atomically pop the highest-priority pending task of task_type.
        Returns the task dict or None.
        """
        result = self.r.zpopmin(f"tasks:queue:{task_type}", count=1)
        if not result:
            return None
        task_id = str(result[0][0])

        now = time.time()
        update: Dict[str, Any] = {
            "status": "in_progress",
            "started_at": str(now),
            "worker_id": worker_id,
        }
        pipe = self.r.pipeline()
        pipe.hset(f"task:{task_id}", mapping=update)  # type: ignore[arg-type]
        pipe.expire(f"task:{task_id}", TASK_TTL)
        pipe.execute()
        return self.get(task_id)

    def complete(self, task_id: str, result: Any) -> None:
        """Mark a task as done with its result."""
        update: Dict[str, Any] = {
            "status": "done",
            "result": json.dumps(result),
            "finished_at": str(time.time()),
        }
        pipe = self.r.pipeline()
        pipe.hset(f"task:{task_id}", mapping=update)  # type: ignore[arg-type]
        pipe.expire(f"task:{task_id}", TASK_TTL)
        pipe.execute()

    def fail(self, task_id: str, error: str) -> None:
        """Mark a task as failed and add to DLQ."""
        update: Dict[str, Any] = {
            "status": "failed",
            "error": error,
            "finished_at": str(time.time()),
        }
        pipe = self.r.pipeline()
        pipe.hset(f"task:{task_id}", mapping=update)  # type: ignore[arg-type]
        pipe.expire(f"task:{task_id}", TASK_TTL)
        pipe.zadd("tasks:dlq", {task_id: time.time()})
        pipe.execute()

    def cancel(self, task_id: str) -> bool:
        """Cancel a pending task. Returns False if not pending."""
        task = self.get(task_id)
        if not task or task["status"] != "pending":
            return False
        update: Dict[str, Any] = {
            "status": "cancelled",
            "finished_at": str(time.time()),
        }
        pipe = self.r.pipeline()
        pipe.hset(f"task:{task_id}", mapping=update)  # type: ignore[arg-type]
        pipe.expire(f"task:{task_id}", TASK_TTL)
        pipe.zrem(f"tasks:queue:{task['type']}", task_id)
        pipe.execute()
        return True

    def requeue(self, task_id: str, priority: int = 0) -> bool:
        """Re-enqueue a failed task (retry from DLQ). Returns False if not failed."""
        task = self.get(task_id)
        if not task or task["status"] != "failed":
            return False
        update: Dict[str, Any] = {
            "status": "pending",
            "error": "",
            "started_at": "",
            "finished_at": "",
            "worker_id": "",
        }
        pipe = self.r.pipeline()
        pipe.hset(f"task:{task_id}", mapping=update)  # type: ignore[arg-type]
        pipe.expire(f"task:{task_id}", TASK_TTL)
        pipe.zadd(f"tasks:queue:{task['type']}", {task_id: priority})
        pipe.zrem("tasks:dlq", task_id)
        pipe.execute()
        return True

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a single task by ID. Returns None if not found."""
        data = self.r.hgetall(f"task:{task_id}")
        if not data:
            return None
        return self._hydrate({str(k): str(v) for k, v in data.items()})

    def list(
        self,
        status: Optional[str] = None,
        task_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List tasks newest-first, optionally filtered by status and/or type."""
        ids = self.r.zrevrange("tasks:index", 0, -1)
        tasks = []
        skipped = 0
        for tid in ids:
            t = self.get(str(tid))
            if t is None:
                continue
            if status and t["status"] != status:
                continue
            if task_type and t["type"] != task_type:
                continue
            if skipped < offset:
                skipped += 1
                continue
            tasks.append(t)
            if len(tasks) >= limit:
                break
        return tasks

    def stats(self) -> Dict[str, Any]:
        """Return queue depth, DLQ size, and per-type/status counts."""
        all_ids = self.r.zrange("tasks:index", 0, -1)
        counts: Dict[str, int] = {}
        type_pending: Dict[str, int] = {}

        for tid in all_ids:
            row = self.r.hmget(f"task:{tid}", "status", "type")
            st = str(row[0]) if row[0] else None
            tp = str(row[1]) if row[1] else None
            if st:
                counts[st] = counts.get(st, 0) + 1
            if st == "pending" and tp:
                type_pending[tp] = type_pending.get(tp, 0) + 1

        dlq_size = self.r.zcard("tasks:dlq")
        return {
            "total": len(list(all_ids)),
            "by_status": counts,
            "pending_by_type": type_pending,
            "dlq_size": int(dlq_size),
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _hydrate(self, raw: Dict[str, str]) -> Dict[str, Any]:
        """Convert raw Redis strings back to typed Python values."""
        task: Dict[str, Any] = dict(raw)
        for field in ("payload", "result"):
            val = task.get(field, "")
            task[field] = json.loads(val) if val else None
        for field in ("created_at", "started_at", "finished_at"):
            val = task.get(field, "")
            task[field] = float(val) if val else None
        return task
