"""Higgsfield generation client with three-tier cascade.

Cascade order on every call():
  Tier A — MCP. The Higgsfield MCP lives at https://mcp.higgsfield.ai/mcp
           but its tools only register on Claude Code session restart, so
           there is no in-process MCP transport from plain Python. We gate
           Tier A on env var HIGGSFIELD_MCP_AVAILABLE and treat it as a
           future hook (subprocess to `claude mcp`); when the env var is
           not truthy we skip silently.
  Tier B — `higgsfield-client` Python SDK (PyPI v0.1.0, 2025-11-17).
           Calls higgsfield_client.subscribe(slug, arguments=args).
           Reads HF_KEY ("key:secret") or HF_API_KEY + HF_API_SECRET.
  Tier C — Raw HTTPS POST to https://platform.higgsfield.ai/{slug} with
           Authorization: Key {key}:{secret} and JSON body = args.

All tiers normalize the result to either {"images": [{"url": ...}]} or
{"video_url": ...}. Terminal failure raises HiggsfieldError.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any

import requests


class HiggsfieldError(Exception):
    pass


def _credentials() -> tuple[str, str]:
    hf_key = os.getenv("HF_KEY")
    if hf_key and ":" in hf_key:
        key, secret = hf_key.split(":", 1)
        return key, secret
    key = os.getenv("HF_API_KEY", "")
    secret = os.getenv("HF_API_SECRET", "")
    if not key or not secret:
        raise HiggsfieldError(
            "Missing Higgsfield credentials: set HF_KEY=key:secret or HF_API_KEY + HF_API_SECRET"
        )
    return key, secret


def _normalize(payload: Any) -> dict:
    """Coerce SDK / HTTP responses into the documented return shape."""
    if not isinstance(payload, dict):
        raise HiggsfieldError(f"Unexpected response type: {type(payload).__name__}")
    if "images" in payload and isinstance(payload["images"], list):
        norm = []
        for item in payload["images"]:
            if isinstance(item, dict) and "url" in item:
                norm.append({"url": item["url"]})
            elif isinstance(item, str):
                norm.append({"url": item})
        return {"images": norm}
    if "video_url" in payload:
        return {"video_url": payload["video_url"]}
    if "url" in payload:
        return {"images": [{"url": payload["url"]}]}
    if "output" in payload:
        return _normalize(payload["output"])
    raise HiggsfieldError(f"Response missing images/video_url: {payload!r}")


def _try_mcp(slug: str, args: dict, lane: str | None) -> dict | None:
    if not os.getenv("HIGGSFIELD_MCP_AVAILABLE"):
        return None
    print(f"[mcp_client lane={lane}] Tier A (MCP) attempting {slug}", file=sys.stderr)
    try:
        proc = subprocess.run(
            ["claude", "mcp", "call", "higgsfield", slug, "--json", json.dumps(args)],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if proc.returncode != 0:
            print(f"[mcp_client lane={lane}] Tier A failed: {proc.stderr.strip()}", file=sys.stderr)
            return None
        return _normalize(json.loads(proc.stdout))
    except Exception as exc:
        print(f"[mcp_client lane={lane}] Tier A exception: {exc}", file=sys.stderr)
        return None


def _try_sdk(slug: str, args: dict, lane: str | None) -> dict | None:
    print(f"[mcp_client lane={lane}] Tier B (SDK) attempting {slug}", file=sys.stderr)
    try:
        import higgsfield_client  # type: ignore
    except ImportError as exc:
        print(f"[mcp_client lane={lane}] Tier B import failed: {exc}", file=sys.stderr)
        return None
    try:
        _credentials()  # ensure env is populated for the SDK
        result = higgsfield_client.subscribe(slug, arguments=args)
        return _normalize(result)
    except Exception as exc:
        print(f"[mcp_client lane={lane}] Tier B failed: {exc}", file=sys.stderr)
        return None


def _try_http(slug: str, args: dict, lane: str | None) -> dict:
    print(f"[mcp_client lane={lane}] Tier C (HTTP) attempting {slug}", file=sys.stderr)
    key, secret = _credentials()
    url = f"https://platform.higgsfield.ai/{slug}"
    headers = {
        "Authorization": f"Key {key}:{secret}",
        "Content-Type": "application/json",
    }
    try:
        resp = requests.post(url, headers=headers, json=args, timeout=300)
        resp.raise_for_status()
        return _normalize(resp.json())
    except requests.RequestException as exc:
        raise HiggsfieldError(f"HTTP fallback failed for {slug}: {exc}") from exc
    except ValueError as exc:
        raise HiggsfieldError(f"HTTP fallback returned non-JSON for {slug}: {exc}") from exc


def call(slug: str, args: dict, *, lane: str | None = None) -> dict:
    """Returns {"images": [{"url": ...}]} or {"video_url": ...}.
    Cascades MCP -> SDK -> HTTP. Raises HiggsfieldError on terminal failure."""
    result = _try_mcp(slug, args, lane)
    if result is not None:
        return result
    result = _try_sdk(slug, args, lane)
    if result is not None:
        return result
    return _try_http(slug, args, lane)
