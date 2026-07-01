#!/usr/bin/env python3
"""
get_transcript.py — fetch a transcription task result and print plain text.

Usage:
    python3 get_transcript.py <task_id>
    python3 get_transcript.py <task_id> --timestamps
    python3 get_transcript.py <task_id> --json
"""

import argparse
import json
import sys
import urllib.request

TASK_API = "http://localhost:8092"


def fetch(task_id: str) -> dict:
    url = f"{TASK_API}/tasks/{task_id}"
    with urllib.request.urlopen(url) as resp:
        return json.load(resp)


def plain_text(result: dict) -> str:
    # Some whisper builds populate top-level "text", others only "segments"
    if result.get("text"):
        return result["text"].strip()
    segments = result.get("segments") or []
    return " ".join(s.get("text", "").strip() for s in segments)


def timestamped(result: dict) -> str:
    segments = result.get("segments") or []
    lines = []
    for s in segments:
        start = s.get("start", 0)
        end = s.get("end", 0)
        text = s.get("text", "").strip()
        m_s, sec_s = divmod(int(start), 60)
        m_e, sec_e = divmod(int(end), 60)
        lines.append(f"[{m_s:02d}:{sec_s:02d} – {m_e:02d}:{sec_e:02d}]  {text}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Print plain transcript from task queue.")
    parser.add_argument("task_id", help="Task UUID")
    parser.add_argument("--timestamps", action="store_true", help="Include segment timestamps")
    parser.add_argument("--json", action="store_true", help="Dump raw result JSON")
    args = parser.parse_args()

    task = fetch(args.task_id)
    status = task.get("status")

    if status != "done":
        print(f"Task is not done yet (status: {status})", file=sys.stderr)
        if task.get("error"):
            print(f"Error: {task['error']}", file=sys.stderr)
        sys.exit(1)

    result = task.get("result") or {}

    if args.json:
        print(json.dumps(result, indent=2))
    elif args.timestamps:
        print(timestamped(result))
    else:
        print(plain_text(result))


if __name__ == "__main__":
    main()
