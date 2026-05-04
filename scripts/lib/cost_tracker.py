"""Append-only credit ledger for the aesthetic-automation pipeline.

Records every billable call from any lane and aggregates totals on demand.
Persisted as JSON Lines at output/prompts/cost_ledger.jsonl. Stdlib only.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

_LEDGER_PATH = Path("output/prompts/cost_ledger.jsonl")


def record(lane: str, slug: str, credits: float, sidecar_path: str) -> None:
    """Append a single ledger entry. Creates parent dirs if missing."""
    _LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "lane": lane,
        "slug": slug,
        "credits": float(credits),
        "sidecar_path": sidecar_path,
    }
    with _LEDGER_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def total() -> dict:
    """Aggregate ledger totals. Returns zeros if the ledger is missing."""
    summary = {
        "total_credits": 0.0,
        "by_lane": {},
        "by_slug": {},
        "calls": 0,
    }
    if not _LEDGER_PATH.exists():
        return summary

    with _LEDGER_PATH.open("r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            credits = float(entry.get("credits", 0) or 0)
            lane = entry.get("lane", "unknown")
            slug = entry.get("slug", "unknown")
            summary["total_credits"] += credits
            summary["by_lane"][lane] = summary["by_lane"].get(lane, 0.0) + credits
            summary["by_slug"][slug] = summary["by_slug"].get(slug, 0.0) + credits
            summary["calls"] += 1

    return summary
