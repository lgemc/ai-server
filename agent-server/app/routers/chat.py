import asyncio
import json
import logging
import traceback
from typing import AsyncIterator

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from google.genai import types

from .. import config

log = logging.getLogger(__name__)
router = APIRouter()


class ChatRequest(BaseModel):
    message: str


@router.post("/{session_id}/chat")
async def chat(session_id: str, body: ChatRequest, req: Request):
    runner = req.app.state.runner
    session = await runner.session_service.get_session(
        app_name=config.APP_NAME,
        user_id=config.USER_ID,
        session_id=session_id,
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    new_message = types.Content(
        role="user",
        parts=[types.Part(text=body.message)],
    )

    return StreamingResponse(
        _stream_events(runner, session_id, new_message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


async def _stream_events(runner, session_id: str, new_message: types.Content) -> AsyncIterator[str]:
    try:
        log.info("chat start session=%s model=%s", session_id, config.MODEL)

        adk_iter = runner.run_async(
            user_id=config.USER_ID,
            session_id=session_id,
            new_message=new_message,
        )

        # Wrap the ADK iterator with keepalive pings every 25s so nginx
        # (proxy_read_timeout) and browsers never see a silent connection.
        async for event in _with_keepalive(adk_iter, interval=25):
            if event is None:
                # keepalive tick — send SSE comment (browsers ignore it)
                yield ": keepalive\n\n"
                continue

            if not event.content or not event.content.parts:
                continue

            for part in event.content.parts:
                if part.text:
                    if getattr(part, "thought", False):
                        yield _sse("thinking", {"content": part.text})
                    else:
                        yield _sse("text", {"content": part.text, "author": event.author})

                elif part.function_call:
                    log.info("tool_call name=%s args=%s", part.function_call.name, part.function_call.args)
                    yield _sse("tool_call", {
                        "name": part.function_call.name,
                        "args": part.function_call.args,
                    })

                elif part.function_response:
                    log.info("tool_result name=%s", part.function_response.name)
                    yield _sse("tool_result", {
                        "name": part.function_response.name,
                        "result": part.function_response.response,
                    })

            if event.actions and event.actions.artifact_delta:
                keys = list(event.actions.artifact_delta.keys())
                log.info("artifacts saved: %s", keys)
                yield _sse("artifact_saved", {"keys": keys})

        log.info("chat done session=%s", session_id)
        yield _sse("done", {})

    except Exception as e:
        short = _friendly(e)
        log.error("chat error session=%s: %s\n%s", session_id, short, traceback.format_exc())
        yield _sse("error", {"message": short, "detail": traceback.format_exc()})


async def _with_keepalive(aiter, interval: int = 25):
    """Interleave None ticks every `interval` seconds with items from aiter."""
    sentinel = object()
    it = aiter.__aiter__()
    pending_event = asyncio.ensure_future(it.__anext__())
    try:
        while True:
            try:
                result = await asyncio.wait_for(asyncio.shield(pending_event), timeout=interval)
                pending_event = asyncio.ensure_future(it.__anext__())
                yield result
            except asyncio.TimeoutError:
                yield None  # keepalive tick
            except StopAsyncIteration:
                return
    finally:
        pending_event.cancel()


def _friendly(e: Exception) -> str:
    import litellm
    msg = str(e)
    if isinstance(e, litellm.exceptions.APIConnectionError) or "Connection error" in msg:
        return f"Cannot reach LLM backend ({config.MODEL}). Is the vLLM container running?"
    if isinstance(e, litellm.exceptions.NotFoundError):
        return f"Model not found on backend: {config.MODEL}"
    if isinstance(e, litellm.exceptions.AuthenticationError):
        return "LLM backend returned 401 — check API key config."
    if isinstance(e, litellm.exceptions.Timeout):
        return f"LLM backend timed out ({config.MODEL}). It may still be loading."
    cause = e.__cause__ or e.__context__
    if cause:
        return f"{type(e).__name__}: {msg} | caused by: {type(cause).__name__}: {cause}"
    return f"{type(e).__name__}: {msg}"


def _sse(event_type: str, data: dict) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
