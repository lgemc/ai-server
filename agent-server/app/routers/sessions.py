import time

from fastapi import APIRouter, Request, HTTPException
from google.adk.events import Event, EventActions
from pydantic import BaseModel
from typing import Optional

from .. import config

router = APIRouter()


class CreateSessionRequest(BaseModel):
    title: Optional[str] = None


@router.post("")
async def create_session(req: Request, body: CreateSessionRequest = CreateSessionRequest()):
    runner = req.app.state.runner
    session = await runner.session_service.create_session(
        app_name=config.APP_NAME,
        user_id=config.USER_ID,
        state={"title": body.title or "New chat"},
    )
    return _session_summary(session)


@router.get("")
async def list_sessions(req: Request):
    runner = req.app.state.runner
    resp = await runner.session_service.list_sessions(
        app_name=config.APP_NAME,
        user_id=config.USER_ID,
    )
    return [_session_summary(s) for s in resp.sessions]


@router.get("/{session_id}")
async def get_session(session_id: str, req: Request):
    runner = req.app.state.runner
    session = await runner.session_service.get_session(
        app_name=config.APP_NAME,
        user_id=config.USER_ID,
        session_id=session_id,
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return _session_detail(session)


@router.patch("/{session_id}")
async def rename_session(session_id: str, req: Request, body: CreateSessionRequest):
    runner = req.app.state.runner
    session = await runner.session_service.get_session(
        app_name=config.APP_NAME,
        user_id=config.USER_ID,
        session_id=session_id,
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await runner.session_service.append_event(
        session=session,
        event=Event(
            author=config.APP_NAME,
            actions=EventActions(state_delta={"title": body.title}),
            timestamp=time.time(),
        ),
    )
    return {"ok": True}


@router.delete("/{session_id}")
async def delete_session(session_id: str, req: Request):
    runner = req.app.state.runner
    await runner.session_service.delete_session(
        app_name=config.APP_NAME,
        user_id=config.USER_ID,
        session_id=session_id,
    )
    return {"ok": True}


def _session_summary(s) -> dict:
    return {
        "id": s.id,
        "title": s.state.get("title", "Chat") if s.state else "Chat",
        "last_update_time": s.last_update_time,
        "message_count": len(s.events) if s.events else 0,
    }


def _session_detail(s) -> dict:
    messages = []
    for event in (s.events or []):
        if not event.content or not event.content.parts:
            continue
        role = event.content.role or event.author
        if role not in ("user", "model"):
            continue
        thinking_parts = [p.text for p in event.content.parts if p.text and getattr(p, 'thought', False)]
        text_parts = [p.text for p in event.content.parts if p.text and not getattr(p, 'thought', False)]
        if not text_parts:
            continue
        content = " ".join(text_parts)
        if thinking_parts:
            content = f"<think>{''.join(thinking_parts)}</think>\n\n{content}"
        messages.append({
            "id": event.id,
            "role": "assistant" if role == "model" else "user",
            "content": content,
            "timestamp": event.timestamp,
        })
    return {**_session_summary(s), "messages": messages}
