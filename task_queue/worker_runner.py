"""
Worker Runner — polls Redis for pending tasks and dispatches them
to the registered handler for each task type.

To add a new task type, just register a handler:

    @register("my_type")
    async def handle_my_type(payload: dict) -> dict:
        ...

The worker polls all registered types in a round-robin, sleeping
briefly when there's nothing to do.
"""

import asyncio
import logging
import os
import socket
import sys
from typing import Any, Callable, Coroutine, Dict

from task_store import TaskStore
from workers.whisper_worker import handle_transcription

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
log = logging.getLogger("worker")

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", "1.0"))  # seconds between polls

# ------------------------------------------------------------------
# Handler registry
# ------------------------------------------------------------------

Handler = Callable[[Dict[str, Any]], Coroutine[Any, Any, Dict[str, Any]]]
_REGISTRY: Dict[str, Handler] = {}


def register(task_type: str):
    """Decorator to register a handler for a task type."""
    def decorator(fn: Handler) -> Handler:
        _REGISTRY[task_type] = fn
        log.info(f"Registered handler for task type: {task_type}")
        return fn
    return decorator


# Register built-in handlers
register("transcription")(handle_transcription)


# ------------------------------------------------------------------
# Worker loop
# ------------------------------------------------------------------

WORKER_ID = f"{socket.gethostname()}-{os.getpid()}"


async def process_one(store: TaskStore, task_type: str) -> bool:
    """
    Try to claim and process one task of the given type.
    Returns True if a task was processed, False if queue was empty.
    """
    task = store.claim(task_type, worker_id=WORKER_ID)
    if task is None:
        return False

    task_id = task["id"]
    log.info(f"[{task_type}] Claimed task {task_id}")

    handler = _REGISTRY[task_type]
    try:
        result = await handler(task["payload"] or {})
        store.complete(task_id, result)
        log.info(f"[{task_type}] Completed task {task_id}")
    except Exception as exc:
        error_msg = f"{type(exc).__name__}: {exc}"
        log.error(f"[{task_type}] Failed task {task_id}: {error_msg}")
        store.fail(task_id, error_msg)

    return True


async def run():
    store = TaskStore(redis_url=REDIS_URL)
    task_types = list(_REGISTRY.keys())
    log.info(f"Worker {WORKER_ID} starting — handling types: {task_types}")

    while True:
        did_work = False
        for task_type in task_types:
            try:
                worked = await process_one(store, task_type)
                if worked:
                    did_work = True
            except Exception as exc:
                log.error(f"Unexpected error in worker loop ({task_type}): {exc}")

        if not did_work:
            await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        log.info("Worker stopped.")
        sys.exit(0)
