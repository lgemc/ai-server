import asyncio
import json
import logging
import traceback
from typing import AsyncIterator


from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from google.genai import types
from google.adk.agents.run_config import RunConfig, StreamingMode

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
    log.info("chat start session=%s model=%s", session_id, config.MODEL)
    yield _sse("status", {"state": "thinking"})

    sent_partial_text = False
    event_count = 0

    try:
        async for event in runner.run_async(
            user_id=config.USER_ID,
            session_id=session_id,
            new_message=new_message,
            run_config=RunConfig(streaming_mode=StreamingMode.SSE),
        ):
            event_count += 1
            log.info(
                "adk event #%d author=%s partial=%s has_content=%s",
                event_count, event.author, event.partial, bool(event.content),
            )

            if not event.content or not event.content.parts:
                continue

            is_partial = event.partial is True

            for part in event.content.parts:
                if part.text:
                    thought = getattr(part, "thought", False)
                    if is_partial:
                        if thought:
                            yield _sse("thinking", {"content": part.text})
                        else:
                            sent_partial_text = True
                            yield _sse("text", {"content": part.text, "author": event.author})
                    elif not sent_partial_text:
                        if thought:
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

    except (asyncio.CancelledError, GeneratorExit):
        log.debug("chat cancelled after %d events session=%s", event_count, session_id)
        raise
    except Exception as e:
        short = _friendly(e)
        log.error("chat error session=%s: %s\n%s", session_id, short, traceback.format_exc())
        yield _sse("error", {"message": short, "detail": traceback.format_exc()})


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
