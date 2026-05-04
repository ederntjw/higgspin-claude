"""JSONL reader/writer for extracted Pinterest prompts.

This module is the storage + scoring layer for Stage 3 of the aesthetic
automation pipeline. Vision extraction happens in the orchestrator (Claude
Code's vision capability per CLAUDE.md). This module just persists the
results and exposes a top-N selector.

JSONL line schema:
    {"src": "<absolute path to source image>", "prompt": "<str>", "score": <float 0..1>}
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any


def _clamp(score: float) -> float:
    """Clamp a score into [0.0, 1.0]. Non-numeric becomes 0.0."""
    try:
        s = float(score)
    except (TypeError, ValueError):
        return 0.0
    if s < 0.0:
        return 0.0
    if s > 1.0:
        return 1.0
    return s


def write_prompt(jsonl_path: str, src: str, prompt: str, score: float) -> None:
    """Append a {src, prompt, score} record to the JSONL file.

    Auto-creates the parent directory. Score is clamped to [0,1] without
    raising. `src` is normalized to an absolute path.
    """
    parent = os.path.dirname(os.path.abspath(jsonl_path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    record: dict[str, Any] = {
        "src": os.path.abspath(src),
        "prompt": str(prompt),
        "score": _clamp(score),
    }
    line = json.dumps(record, ensure_ascii=False)
    with open(jsonl_path, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def top_n(jsonl_path: str, n: int = 5) -> list[dict]:
    """Return the top-n records sorted by score descending.

    Missing or empty file returns []. Malformed lines are skipped.
    """
    if not os.path.exists(jsonl_path):
        return []
    rows: list[dict] = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                obj["score"] = _clamp(obj.get("score", 0.0))
                rows.append(obj)
    rows.sort(key=lambda r: r.get("score", 0.0), reverse=True)
    return rows[: max(0, int(n))]


def _main(argv: list[str]) -> int:
    if len(argv) >= 4 and argv[1] == "top-n":
        path = argv[2]
        try:
            n = int(argv[3])
        except ValueError:
            print("n must be an integer", file=sys.stderr)
            return 2
        print(json.dumps(top_n(path, n), ensure_ascii=False, indent=2))
        return 0
    print(
        "usage: python scripts/extract_prompts.py top-n <jsonl_path> <n>",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))
