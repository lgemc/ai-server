"""
Vocabulary API — store and retrieve word definitions with examples.

Storage: plain markdown files, one per word, in ~/Do/vocab/words/
Format:
    # Word
    **Part of speech:** ...
    **Definition:** ...
    
    **Examples:**
    1. ...
    2. ...
    
Endpoints:
    POST   /add          Add or update a word
    GET    /search?word=xxx  Search a word
    GET    /list         List all stored words (alphabetical)
    GET    /stats        Word count stats
"""
import os
import re
import json
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

app = FastAPI(title="Vocabulary API", version="1.0.0")

WORD_DIR = os.getenv("VOCAB_DIR", os.path.expanduser("~/Do/vocab/words"))
os.makedirs(WORD_DIR, exist_ok=True)


class VocabularyEntry(BaseModel):
    word: str
    part_of_speech: str
    definition: str
    examples: list[str] = []


class AddWordRequest(BaseModel):
    word: str
    meaning: str
    definition: str = ""
    examples: list[str] = []
    part_of_speech: str = ""

    model_config = {"populate_by_name": True}

    def normalize(self) -> VocabularyEntry:
        """Normalize fields — accept 'meaning' OR 'definition'."""
        definition_text = self.definition or self.meaning
        pos = self.part_of_speech or "word"
        # Limit to 10 examples
        examples = self.examples[:10]
        return VocabularyEntry(
            word=self.word.lower().strip(),
            part_of_speech=pos,
            definition=definition_text.strip(),
            examples=examples,
        )


class WordResponse(BaseModel):
    word: str
    part_of_speech: str
    definition: str
    examples: list[str]
    created_at: str = ""
    updated_at: str = ""


# ── Helpers ─────────────────────────────────────────────────────────────────

def _word_file(word: str) -> str:
    return os.path.join(WORD_DIR, f"{word}.md")


def _write_markdown(entry: VocabularyEntry, created: str = "") -> dict:
    """Write a word file in clean markdown format, sorted alphabetically."""
    parts_of_speech_line = f"**Part of Speech:** {entry.part_of_speech}" if entry.part_of_speech else ""
    definition_line = f"**Definition:** {entry.definition}" if entry.definition else ""

    examples_section = ""
    if entry.examples:
        numbered = "\n".join(f"{i+1}. {ex}" for i, ex in enumerate(entry.examples))
        examples_section = f"\n**Examples:**\n{numbered}"

    content = f"# {entry.word}\n\n"
    if parts_of_speech_line:
        content += f"{parts_of_speech_line}\n\n"
    if definition_line:
        content += f"{definition_line}\n\n"
    content += examples_section
    content += f"\n\n> _Updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_\n"

    path = _word_file(entry.word)
    with open(path, "w") as f:
        f.write(content)

    return {
        "word": entry.word,
        "part_of_speech": entry.part_of_speech,
        "definition": entry.definition,
        "examples": entry.examples,
    }


def _read_markdown(word: str) -> dict:
    """Read and parse a word markdown file."""
    path = _word_file(word)
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        text = f.read()

    result: dict = {"word": word, "examples": []}

    # Extract part of speech
    m = re.search(r"\*\*Part of Speech:\*\*\s*(.+)", text)
    if m:
        result["part_of_speech"] = m.group(1).strip()

    # Extract definition
    m = re.search(r"\*\*Definition:\*\*\s*(.+)", text)
    if m:
        result["definition"] = m.group(1).strip()

    # Extract numbered examples
    examples = re.findall(r"(\d+)\.\s*(.+)", text)
    if examples:
        result["examples"] = [ex[1] for ex in examples]

    return result


# ── Routes ──────────────────────────────────────────────────────────────────

@app.post("/add", status_code=201)
def add_word(req: AddWordRequest):
    entry = req.normalize()
    result = _write_markdown(entry)
    # Re-index: read all words, sort, write an index
    _write_index()
    return {"status": "added", "word": result["word"], "path": _word_file(result["word"])}


@app.get("/search")
def search_word(word: str = Query(..., description="Word to look up")):
    word = word.lower().strip()
    data = _read_markdown(word)
    if not data:
        # Also check for partial match
        matches = []
        for f in os.listdir(WORD_DIR):
            if f.endswith(".md") and word in f.lower():
                matches.append({"word": f[:-3], "partial": True})
        if matches:
            raise HTTPException(status_code=206, detail={"exact": None, "partial_matches": matches})
        raise HTTPException(status_code=404, detail=f"Word '{word}' not found")
    return WordResponse(**data)


@app.get("/list")
def list_words():
    """Return all stored words in alphabetical order."""
    words = []
    for f in os.listdir(WORD_DIR):
        if f.endswith(".md") and f != "INDEX.md":
            words.append(f[:-3])
    words.sort()
    return {"total": len(words), "words": words}


@app.get("/index")
def get_index():
    """Read the alphabetical index file."""
    index_path = os.path.join(WORD_DIR, "INDEX.md")
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail="Index not found. Run add first.")
    with open(index_path) as f:
        text = f.read()
    return {"index": text}


@app.get("/stats")
def stats():
    count = len([f for f in os.listdir(WORD_DIR) if f.endswith(".md") and f != "INDEX.md"])
    return {"total_words": count, "directory": WORD_DIR}


def _write_index():
    """Build the INDEX.md file — alphabetical listing of all words."""
    words = sorted(f[:-3] for f in os.listdir(WORD_DIR) if f.endswith(".md") and f != "INDEX.md")
    lines = [f"# Vocabulary Index\n\n{len(words)} words stored.\n"]
    for w in words:
        lines.append(f"- [{w}](./{w}.md)")
    lines.append("")
    with open(os.path.join(WORD_DIR, "INDEX.md"), "w") as f:
        f.write("\n".join(lines))