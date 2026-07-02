"""
Quiz Engine — SM-2 spaced repetition with SQLite storage.

Stores questions and tracks:
 - ease_factor (EF)
 - interval (days)
 - repetitions
 - next_review_date

SM-2 algorithm: https://en.wikipedia.org/wiki/SuperMemo#SM-2
"""
import json
import sqlite3
import os
import math
from datetime import datetime, timedelta, timezone
from typing import Optional

DB_PATH = os.getenv("QUIZ_DB", "/app/quiz_data/quiz.db")


def _get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = _get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS questions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            section     TEXT NOT NULL,
            question    TEXT NOT NULL,
            options     TEXT NOT NULL,       -- JSON array of 4 strings
            answer      INTEGER NOT NULL,    -- index 0-3 of correct option
            explanation TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS reviews (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id  INTEGER NOT NULL REFERENCES questions(id),
            ef           REAL NOT NULL DEFAULT 2.5,
            interval     REAL NOT NULL DEFAULT 0,
            reps         INTEGER NOT NULL DEFAULT 0,
            next_review  TEXT NOT NULL DEFAULT '',  -- ISO datetime
            total_right  INTEGER NOT NULL DEFAULT 0,
            total_wrong  INTEGER NOT NULL DEFAULT 0,
            created_at   TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_reviews_next ON reviews(next_review);
        CREATE INDEX IF NOT EXISTS idx_reviews_qid ON reviews(question_id);
    """)
    conn.commit()
    conn.close()


# ── SM-2 Algorithm ──────────────────────────────────────────────────────────

def sm2_next(quality: int, ef: float, interval: float, reps: int):
    """
    quality: 0-5 (0=complete blackout, 5=perfect response)
    Returns (new_ef, new_interval, new_reps)
    """
    if quality < 0:
        quality = 0
    if quality > 5:
        quality = 5

    if quality < 3:
        # Failed — reset
        reps = 0
        interval = 1.0
    else:
        if reps == 0:
            interval = 1.0
        elif reps == 1:
            interval = 6.0
        else:
            interval = interval * ef
        reps += 1

    # Update ease factor
    ef = ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    if ef < 1.3:
        ef = 1.3

    return round(ef, 2), round(interval, 1), reps


# ── Question CRUD ───────────────────────────────────────────────────────────

def add_question(section: str, question: str, options: list[str], answer: int, explanation: str = "") -> int:
    conn = _get_db()
    cur = conn.execute(
        "INSERT INTO questions (section, question, options, answer, explanation) VALUES (?, ?, ?, ?, ?)",
        (section, question, json.dumps(options), answer, explanation),
    )
    qid = cur.lastrowid
    # Also seed a review row
    conn.execute(
        "INSERT INTO reviews (question_id, ef, interval, reps, next_review) VALUES (?, 2.5, 0, 0, datetime('now'))",
        (qid,),
    )
    conn.commit()
    conn.close()
    return qid


def get_due_questions(limit: int = 10) -> list[dict]:
    """Return questions where next_review <= now, ordered by next_review ASC."""
    conn = _get_db()
    rows = conn.execute("""
        SELECT q.id, q.section, q.question, q.options, q.answer, q.explanation,
               r.ef, r.interval, r.reps, r.next_review, r.total_right, r.total_wrong
        FROM questions q
        JOIN reviews r ON r.question_id = q.id
        WHERE r.next_review <= datetime('now')
        ORDER BY r.next_review ASC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def get_due_count() -> int:
    conn = _get_db()
    row = conn.execute("""
        SELECT COUNT(*) as cnt FROM reviews
        WHERE next_review <= datetime('now')
    """).fetchone()
    conn.close()
    return row["cnt"] if row else 0


def get_stats() -> dict:
    conn = _get_db()
    total_q = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
    due = get_due_count()
    total_r = conn.execute("SELECT SUM(total_right) FROM reviews").fetchone()[0] or 0
    total_w = conn.execute("SELECT SUM(total_wrong) FROM reviews").fetchone()[0] or 0
    # Per section
    sections = []
    for row in conn.execute("""
        SELECT q.section, COUNT(*) as total,
               SUM(r.total_right) as right, SUM(r.total_wrong) as wrong
        FROM questions q JOIN reviews r ON r.question_id = q.id
        GROUP BY q.section ORDER BY q.section
    """).fetchall():
        sections.append({
            "section": row["section"],
            "total": row["total"],
            "right": row["right"] or 0,
            "wrong": row["wrong"] or 0,
        })
    conn.close()
    total = total_r + total_w
    return {
        "total_questions": total_q,
        "due_today": due,
        "total_answers": total,
        "accuracy": round(total_r / total * 100, 1) if total else 0,
        "sections": sections,
    }


def submit_answer(question_id: int, chosen: int) -> dict:
    """Record an answer and update SM-2 params. Returns feedback dict."""
    conn = _get_db()
    q = conn.execute("SELECT * FROM questions WHERE id=?", (question_id,)).fetchone()
    if not q:
        conn.close()
        return {"error": "Question not found"}
    r = conn.execute("SELECT * FROM reviews WHERE question_id=?", (question_id,)).fetchone()
    if not r:
        conn.close()
        return {"error": "Review not found"}

    correct = chosen == q["answer"]
    quality = 5 if correct else 1  # binary: perfect or fail
    new_ef, new_interval, new_reps = sm2_next(quality, r["ef"], r["interval"], r["reps"])

    next_review = (datetime.now(timezone.utc) + timedelta(days=new_interval)).strftime("%Y-%m-%d %H:%M:%S")

    conn.execute("""
        UPDATE reviews SET ef=?, interval=?, reps=?, next_review=?,
            total_right=total_right+?, total_wrong=total_wrong+?
        WHERE question_id=?
    """, (new_ef, new_interval, new_reps, next_review, 1 if correct else 0, 0 if correct else 1, question_id))
    conn.commit()
    conn.close()

    return {
        "question_id": question_id,
        "correct": correct,
        "correct_answer": q["answer"],
        "explanation": q["explanation"],
        "sm2": {
            "ef": new_ef,
            "interval": new_interval,
            "reps": new_reps,
            "next_review": next_review,
        },
    }


def get_question_by_id(qid: int) -> Optional[dict]:
    conn = _get_db()
    row = conn.execute("""
        SELECT q.*, r.ef, r.interval, r.reps, r.next_review, r.total_right, r.total_wrong
        FROM questions q JOIN reviews r ON r.question_id = q.id
        WHERE q.id=?
    """, (qid,)).fetchone()
    conn.close()
    return _row_to_dict(row) if row else None


def _row_to_dict(r) -> dict:
    return {
        "id": r["id"],
        "section": r["section"],
        "question": r["question"],
        "options": json.loads(r["options"]),
        "answer": r["answer"],
        "explanation": r["explanation"],
        "ef": r["ef"],
        "interval": r["interval"],
        "reps": r["reps"],
        "next_review": r["next_review"],
        "total_right": r["total_right"],
        "total_wrong": r["total_wrong"],
    }


# ── Seed default questions from summaries ────────────────────────────────────

DEFAULT_QUESTIONS = [
    # LISTENING
    ("Listening", "How many sections are there in IELTS Listening?", ["2", "4", "6", "8"], 1, "4 sections, 10 questions each."),
    ("Listening", "Which listening section is an academic monologue?", ["Section 1", "Section 2", "Section 3", "Section 4"], 3, "Section 4 = one speaker on an academic topic."),
    ("Listening", "How many times do you hear the recording?", ["Once", "Twice", "Three times", "As many times as needed"], 0, "Only one chance — recordings play once."),
    ("Listening", "What score is a Band 7 in Listening?", ["23/40", "30/40", "35/40", "40/40"], 1, "Band 7 = 30/40. Band 8 = 35/40."),
    ("Listening", "What is a 'distractor' in listening?", ["A loud background noise", "A tempting wrong answer option", "An extra question", "A repeated word"], 1, "Distractors are tempting but incorrect answer options."),
    ("Listening", "In Form Completion, names are usually ___", ["Written in lowercase", "Spelled out by the speaker", "Given only once quickly", "Irrelevant"], 1, "Speakers usually spell names — listen carefully for correct spelling."),
    ("Listening", "In Matching questions, the numbered list is always:", ["In random order", "In reverse order", "The same order as the audio", "Unrelated to the audio"], 2, "The numbered list follows the audio sequence."),
    ("Listening", "For Plan/Map Labeling, the speaker typically starts at:", ["The center", "The entrance", "The north side", "The back"], 1, "Always start at the entrance point and follow directions."),

    # READING
    ("Reading", "How many questions are in IELTS Reading?", ["20", "30", "40", "50"], 2, "40 questions across 3 passages."),
    ("Reading", "Which question type follows passage order?", ["Match Headings", "True/False/Not Given", "Match Information", "Match Features"], 1, "Multiple Choice, T/F/NG, Y/N/NG, and Short Answer follow passage order."),
    ("Reading", "In True/False/Not Given, what does FALSE mean?", ["Statement has different wording", "Statement contradicts the passage", "Statement is about a different topic", "The passage doesn't mention it"], 1, "FALSE = contradictory information in the passage."),
    ("Reading", "In Yes/No/Not Given, what does YES mean?", ["Statement matches facts", "Statement matches the writer's opinion", "The writer mentions it briefly", "Statement is common knowledge"], 1, "YES = statement agrees with the writer's claims/opinions."),
    ("Reading", "What's the main difference between Yes/No and True/False?", ["They're the same", "Y/N tests writer's opinion, T/F tests facts", "T/F is harder", "Y/N only appears in General"], 1, "T/F = factual agreement. Y/N = agreement with writer's opinions."),
    ("Reading", "The best strategy for Match Headings is:", ["Read all headings first", "Read the paragraph first, then choose a heading", "Start with the longest heading", "Match headings in alphabetical order"], 1, "Paragraph-first — read section, think of your own heading, then pick."),
    ("Reading", "How should Match Information be approached?", ["Same as True/False", "Paragraph by paragraph, checking all questions per paragraph", "Question by question, scanning whole passage each time", "Start with the last paragraph"], 1, "Read one paragraph, check ALL questions for matches, repeat."),
    ("Reading", "What type of word is usually the answer in gap-fill questions?", ["Verb", "Adverb", "Noun", "Preposition"], 2, "Target words = nouns (or occasionally adjectives)."),
    ("Reading", "Can you change the word form in Sentence Completion?", ["Yes, change tense as needed", "No, copy directly from text", "Only plural to singular", "Only if it fits grammatically"], 1, "Words must come directly from the text — no changes."),
    ("Reading", "In Match Sentence Endings, there are:", ["Equal endings and beginnings", "More endings than beginnings", "More beginnings than endings", "No endings provided"], 1, "Always more sentence endings to choose from than beginnings."),

    # SPEAKING
    ("Speaking", "How long is Speaking Part 1?", ["2 minutes", "4-5 minutes", "10 minutes", "15 minutes"], 1, "Part 1 = 4-5 minutes (ID check + interview)."),
    ("Speaking", "How many methods are taught for Part 1 answers?", ["3", "4", "5", "6"], 3, "6 methods: opinion, details, contrasts, past-present, present-future, reasons."),
    ("Speaking", "What should you avoid in Part 1?", ["Giving examples", "Short yes/no answers", "Using opinions", "Talking about yourself"], 1, "Never give yes/no/short answers — always extend and elaborate."),
    ("Speaking", "How long should you aim to speak in Part 2?", ["30 seconds", "1 minute", "2 minutes", "5 minutes"], 2, "Aim for the full 2 minutes until the examiner stops you."),
    ("Speaking", "What does the PPF method stand for?", ["Practice-Prepare-Finish", "Past-Present-Future", "Point-Prove-Frame", "Plan-Present-Flow"], 1, "PPF = Past → Present → Future. Transition through tenses."),
    ("Speaking", "Should you memorize answers for Part 2?", ["Yes, it's safer", "No, it sounds unnatural", "Only for difficult topics", "Yes, examiners expect it"], 1, "Don't memorize — delivery becomes unnatural and examiners disregard it."),
    ("Speaking", "How many questions in Speaking Part 3?", ["1-2", "3-5", "6-8", "10-12"], 1, "Examiner asks 3-5 abstract follow-up questions."),
    ("Speaking", "Part 3 questions are ___ compared to Part 1", ["Easier", "More abstract and complex", "About the same", "Shorter"], 1, "Part 3 requires deeper thought and more sophisticated answers."),
    ("Speaking", "What is a 'hesitation device' for?", ["To fill silence while thinking", "To correct grammar", "To end the test early", "To signal you're done"], 0, "Buy time with phrases like 'That's a big question…' while you formulate your answer."),

    # WRITING TASK 1
    ("Writing Task 1", "How much time for Writing Task 1?", ["20 minutes", "30 minutes", "40 minutes", "60 minutes"], 0, "20 minutes to write 150+ words."),
    ("Writing Task 1", "Which of these is NOT a Task 1 image type?", ["Line graph", "Bar chart", "Essay", "Process diagram"], 2, "Task 1 = graphs, charts, tables, maps, or process diagrams."),
    ("Writing Task 1", "The Task 1 instruction always says:", ["Write your opinion", "Summarize by selecting main features and compare", "Describe everything you see", "Give a conclusion with your view"], 1, "Always: 'Summarize by selecting and reporting main features, make comparisons.'"),
    ("Writing Task 1", "What goes in the overview paragraph?", ["Specific data and numbers", "A broad statement with no details", "Your opinion", "A full description of every element"], 1, "Overview = broad statement of main trends/differences — NO numbers."),
    ("Writing Task 1", "For a process diagram, you must:", ["Only describe the first and last step", "Include EVERY step in order", "Add your opinion about efficiency", "Skip less important steps"], 1, "Process diagrams require mentioning every single stage."),
    ("Writing Task 1", "What tense is most common in process diagrams?", ["Past simple", "Present simple passive", "Future perfect", "Present continuous"], 1, "Passive voice (present simple) is heavily used: 'is dug', 'are added', 'are heated'."),
    ("Writing Task 1", "For map questions, what must you describe?", ["Only what changed", "Only what stayed the same", "Both changes AND what remained", "Only the present map"], 2, "Must mention everything that changed AND everything that stayed the same."),
    ("Writing Task 1", "In a change-over-time graph, what should you identify first?", ["All the numbers", "What went up and what went down", "The colors used", "The units of measurement"], 1, "Key questions: what went up, what went down, did positions change?"),

    # WRITING TASK 2
    ("Writing Task 2", "How long for Writing Task 2?", ["20 minutes", "30 minutes", "40 minutes", "60 minutes"], 2, "40 minutes to write 250+ words."),
    ("Writing Task 2", "How many parts in the introduction formula?", ["1", "2", "3", "4"], 2, "Three-part intro: reword background → reword specific statement → answer the question."),
    ("Writing Task 2", "What does PEEL stand for?", ["Point-Explain-Example-Effect-Link", "Plan-Edit-Evaluate-Learn", "Position-Evidence-Explanation-Link", "Prepare-Execute-Evaluate-List"], 0, "PEEL = Point, Explain, Example/Evidence, Effect, Link."),
    ("Writing Task 2", "What does UPEPE stand for?", ["Umbrella-Point-Extend-Point-Extend", "Understand-Prepare-Evaluate-Practice-Edit", "Use-Paragraphs-Evidence-Prove-End", "Unify-Present-Examine-Prove-Execute"], 0, "UPEPE = Umbrella, Point 1, Extend, Point 2, Extend."),
    ("Writing Task 2", "The conclusion should be ___ sentences minimum.", ["1", "2", "3", "4"], 1, "Minimum 2 sentences in the conclusion. Some examiners consider 1 sentence not a paragraph."),
    ("Writing Task 2", "What should you NOT do in a conclusion?", ["Summarize your opinion", "Include new information or examples", "Start with 'In conclusion'", "Restate your arguments"], 1, "Don't introduce new info or examples — save those for body paragraphs."),
    ("Writing Task 2", "What is a run-on sentence?", ["A very long sentence", "Two independent clauses joined without correct punctuation/conjunction", "A sentence with no verb", "A sentence starting with 'and'"], 1, "Two complete sentences joined without proper conjunction or punctuation."),
    ("Writing Task 2", "How to fix a comma splice?", ["Add more commas", "Use a full stop, semicolon, coordinating or subordinating conjunction", "Remove the comma entirely", "Make both clauses longer"], 1, "Four fixes: full stop, semicolon, coordinating conjunction, or subordinating conjunction."),
]


def seed_defaults():
    """Insert default questions if DB is empty."""
    conn = _get_db()
    count = conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
    conn.close()
    if count == 0:
        for section, question, options, answer, explanation in DEFAULT_QUESTIONS:
            add_question(section, question, options, answer, explanation)