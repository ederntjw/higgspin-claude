"""Lane 8 — image-to-video clip generation via Higgsfield.

Cascade is sourced from scripts.models.LANE_CASCADE; pass `lane="i2v_product_lock"`
to prefer Seedance v2/fast (best product/label consistency in May 2026 video models).

CLI:
    python scripts/generate_video.py --still output/generated/foo.png \
        --prompt "slow push-in" [--duration 5] [--resolution 1080p] [--lane i2v_middle]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts import models as models_mod  # noqa: E402
from scripts.lib import cost_tracker  # noqa: E402
from scripts.lib.mcp_client import HiggsfieldError, call as mcp_call  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CLIPS_DIR = ROOT / "output" / "ad" / "clips"
DEFAULT_LANE = "i2v_middle"

CREDIT_RATES_PER_5S = {
    "kling-video/v2.1/pro/image-to-video": 7.0,
    "higgsfield-ai/dop/turbo": 5.0,
    "bytedance/seedance/v2/fast": 8.5,
}
DEFAULT_RATE = 7.0


def _coerce_duration(duration_s) -> int:
    try:
        d = int(duration_s)
    except (TypeError, ValueError):
        return 5
    if d <= 0:
        return 5
    if d > 8:
        return 8
    return d


def _next_shot_index() -> int:
    CLIPS_DIR.mkdir(parents=True, exist_ok=True)
    used = set()
    pattern = re.compile(r"^shot_(\d+)\.(mp4|json)$")
    for entry in CLIPS_DIR.iterdir():
        m = pattern.match(entry.name)
        if m:
            used.add(int(m.group(1)))
    n = 1
    while n in used:
        n += 1
    return n


def _credits_for(slug: str, duration_s: int) -> float:
    rate = CREDIT_RATES_PER_5S.get(slug, DEFAULT_RATE)
    return round(rate * duration_s / 5.0, 4)


def _download(url: str, dest: Path) -> None:
    resp = requests.get(url, timeout=600, stream=True)
    resp.raise_for_status()
    with dest.open("wb") as fh:
        for chunk in resp.iter_content(chunk_size=1 << 16):
            if chunk:
                fh.write(chunk)


def generate_clip(still_path: str, camera_move_prompt: str,
                  duration_s: int = 5, resolution: str = "1080p",
                  *, lane: str = DEFAULT_LANE) -> dict:
    """Returns sidecar dict with: model_id, still_path, prompt, output_path, credits_spent.

    `lane` selects the cascade from scripts.models.LANE_CASCADE.
    Use `lane="i2v_product_lock"` when the source still has a product whose label
    must be preserved through motion (Seedance v2/fast leads that cascade).
    """
    duration_s = _coerce_duration(duration_s)
    args = {
        "image": still_path,
        "prompt": camera_move_prompt,
        "duration": duration_s,
        "resolution": resolution,
    }
    cascade = models_mod.LANE_CASCADE.get(lane)
    if not cascade:
        cascade = [models_mod.LANE_TO_MODEL.get(lane, "kling-video/v2.1/pro/image-to-video")]

    last_err: Exception | None = None
    result: dict | None = None
    chosen_slug: str | None = None
    for slug in cascade:
        try:
            print(f"[generate_video] attempting {slug} (lane={lane})", file=sys.stderr)
            result = mcp_call(slug, args, lane=lane)
            chosen_slug = slug
            break
        except HiggsfieldError as exc:
            print(f"[generate_video] {slug} failed: {exc}", file=sys.stderr)
            last_err = exc
            continue

    if result is None or chosen_slug is None:
        assert last_err is not None
        raise last_err

    video_url = result.get("video_url")
    if not video_url:
        raise HiggsfieldError(f"No video_url in response for {chosen_slug}: {result!r}")

    idx = _next_shot_index()
    output_path = CLIPS_DIR / f"shot_{idx}.mp4"
    sidecar_path = CLIPS_DIR / f"shot_{idx}.json"
    _download(video_url, output_path)

    credits_spent = _credits_for(chosen_slug, duration_s)
    sidecar = {
        "model_id": chosen_slug,
        "still_path": still_path,
        "prompt": camera_move_prompt,
        "duration_s": duration_s,
        "resolution": resolution,
        "source_url": video_url,
        "output_path": str(output_path),
        "credits_spent": credits_spent,
    }
    sidecar_path.write_text(json.dumps(sidecar, indent=2))
    cost_tracker.record(lane, chosen_slug, credits_spent, str(sidecar_path))
    print(json.dumps({"output_path": str(output_path), "model_id": chosen_slug,
                      "credits_spent": credits_spent}))
    return sidecar


def main() -> int:
    load_dotenv(ROOT / ".env")
    ap = argparse.ArgumentParser()
    ap.add_argument("--still", required=True, help="path to source still image")
    ap.add_argument("--prompt", required=True, help="camera move prompt")
    ap.add_argument("--duration", type=int, default=5)
    ap.add_argument("--resolution", default="1080p")
    ap.add_argument("--lane", default=DEFAULT_LANE,
                    choices=("i2v_middle", "i2v_product_lock"),
                    help="cascade lane (i2v_product_lock prefers Seedance v2/fast)")
    args = ap.parse_args()
    generate_clip(args.still, args.prompt, args.duration, args.resolution, lane=args.lane)
    return 0


if __name__ == "__main__":
    sys.exit(main())
