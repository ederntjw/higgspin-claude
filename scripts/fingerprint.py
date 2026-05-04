"""Fingerprint schema validator for the aesthetic-automation pipeline.

Validates the JSON object produced in STAGE 1 against the contract defined
in CLAUDE.md. Stdlib only.
"""
from __future__ import annotations

import json
import re
import sys

SCHEMA_KEYS = (
    "palette",
    "composition",
    "lighting",
    "subject",
    "mood",
    "aesthetic_type",
    "search_query",
)

AESTHETIC_TYPES = frozenset({
    "fashion", "portrait", "lifestyle", "product",
    "cinematic", "architectural", "atmospheric",
    "typography", "poster", "illustration",
    "stylized", "brand_palette",
})

_HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
_STRING_FIELDS = ("composition", "lighting", "subject", "mood", "search_query")


def validate(d: dict) -> None:
    """Raises ValueError on bad shape."""
    if not isinstance(d, dict):
        raise ValueError("fingerprint: expected a JSON object")

    for key in SCHEMA_KEYS:
        if key not in d:
            raise ValueError(f"fingerprint: missing required key '{key}'")

    palette = d["palette"]
    if not isinstance(palette, list) or len(palette) < 3:
        raise ValueError("palette: must be a list with 3 or more hex strings")
    for i, c in enumerate(palette):
        if not isinstance(c, str) or not _HEX_RE.match(c):
            raise ValueError(
                f"palette: entry {i} ({c!r}) is not a #RRGGBB hex string"
            )

    for field in _STRING_FIELDS:
        v = d[field]
        if not isinstance(v, str) or not v.strip():
            raise ValueError(f"{field}: must be a non-empty string")

    aesthetic = d["aesthetic_type"]
    if aesthetic not in AESTHETIC_TYPES:
        raise ValueError(
            f"aesthetic_type: {aesthetic!r} is not one of {sorted(AESTHETIC_TYPES)}"
        )

    word_count = len(d["search_query"].split())
    if not (3 <= word_count <= 10):
        raise ValueError(
            f"search_query: word count {word_count} outside allowed range 3-10"
        )


def _main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python scripts/fingerprint.py <fingerprint.json>", file=sys.stderr)
        return 1
    path = argv[1]
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        validate(data)
    except (OSError, json.JSONDecodeError, ValueError) as e:
        print(f"INVALID: {e}", file=sys.stderr)
        return 1
    print(f"OK: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
