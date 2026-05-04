"""Higgsfield generation wrapper.

Submits a prompt to a Higgsfield model and saves the resulting image to
output/generated/. Uses the official higgsfield-client SDK.

Usage:
    python scripts/generate.py \
        --prompt "long detailed extracted prompt" \
        --aesthetic fashion \
        --aspect 4:5 \
        --resolution 2K

If --model-id is passed it overrides aesthetic-based routing.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

import higgsfield_client  # type: ignore

# Local import so the script can run from anywhere.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from models import resolve as resolve_model  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "output" / "generated"


def generate(prompt: str, model_id: str, aspect: str, resolution: str) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    args = {"prompt": prompt, "aspect_ratio": aspect, "resolution": resolution}

    print(f"→ {model_id}  [{aspect} {resolution}]", file=sys.stderr)
    result = higgsfield_client.subscribe(model_id, arguments=args)
    image_url = result["images"][0]["url"]

    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_model = model_id.replace("/", "_")
    fp = OUT_DIR / f"{stamp}_{safe_model}.jpg"
    fp.write_bytes(requests.get(image_url, timeout=60).content)

    sidecar = fp.with_suffix(".json")
    sidecar.write_text(json.dumps({
        "model_id": model_id,
        "prompt": prompt,
        "aspect_ratio": aspect,
        "resolution": resolution,
        "source_url": image_url,
        "created_at": stamp,
    }, indent=2))
    print(json.dumps({"file": str(fp), "model_id": model_id}))
    return fp


def main() -> int:
    load_dotenv(ROOT / ".env")
    if not os.environ.get("HF_KEY") and not os.environ.get("HF_API_KEY"):
        print("error: set HF_KEY (or HF_API_KEY+HF_API_SECRET) in .env", file=sys.stderr)
        return 2

    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--aesthetic", default=None,
                    help="aesthetic_type for routing (e.g. fashion, cinematic)")
    ap.add_argument("--model-id", default=None,
                    help="explicit Higgsfield model_id; overrides --aesthetic")
    ap.add_argument("--aspect", default="4:5")
    ap.add_argument("--resolution", default="2K")
    args = ap.parse_args()

    model_id = args.model_id or resolve_model(args.aesthetic)
    generate(args.prompt, model_id, args.aspect, args.resolution)
    return 0


if __name__ == "__main__":
    sys.exit(main())
