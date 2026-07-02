"""
Quiz API — mounted under /quiz on the task-api service.

Endpoints:
    GET    /quiz/due?limit=N     Get questions due for review
    GET    /quiz/question/<id>   Get a specific question
    POST   /quiz/answer          Submit an answer and get SM-2 feedback
    GET    /quiz/stats           Overall stats + per-section breakdown
    POST   /quiz/seed            Seed default question bank
"""
import json
import os
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from quiz_engine import (
    init_db, seed_defaults as _seed_defaults, get_due_questions, get_due_count,
    get_stats, submit_answer, get_question_by_id, add_question,
)

app = FastAPI(title="Quiz API", version="1.0.0")


class AnswerRequest(BaseModel):
    question_id: int
    chosen: int  # 0-3


class AddQuestionRequest(BaseModel):
    section: str
    question: str
    options: list[str]
    answer: int
    explanation: str = ""


# Init DB and seed at import time — sub-app mounted startup events don't fire
init_db()
_seed_defaults()


@app.get("/due")
def due(limit: int = Query(5, ge=1, le=20)):
    """Get questions due for spaced repetition review."""
    questions = get_due_questions(limit=limit)
    # Strip correct answer from options for clients — only show question+options
    for q in questions:
        q.pop("answer", None)
        q.pop("explanation", None)
        q.pop("ef", None)
        q.pop("interval", None)
        q.pop("reps", None)
        q.pop("next_review", None)
        q.pop("total_right", None)
        q.pop("total_wrong", None)
    return {"due_count": get_due_count(), "questions": questions}


@app.get("/question/{qid}")
def question(qid: int):
    """Get a single question (without answer) for display."""
    q = get_question_by_id(qid)
    if not q:
        raise HTTPException(404, "Question not found")
    # Strip answer
    q.pop("answer", None)
    q.pop("explanation", None)
    q.pop("ef", None)
    q.pop("interval", None)
    q.pop("reps", None)
    q.pop("next_review", None)
    q.pop("total_right", None)
    q.pop("total_wrong", None)
    return q


@app.post("/answer")
def answer(req: AnswerRequest):
    """Submit an answer. Returns whether correct, explanation, and SM-2 update."""
    result = submit_answer(req.question_id, req.chosen)
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result


@app.get("/stats")
def stats():
    """Quiz statistics — total questions, due count, accuracy by section."""
    return get_stats()


@app.post("/seed")
def seed():
    """Seed the question bank with default questions."""
    _seed_defaults()
    return {"status": "seeded", "message": "Default questions seeded"}