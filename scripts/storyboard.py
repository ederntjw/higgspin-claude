"""Storyboard planner: top prompts + fingerprint -> ordered shot list with camera moves.

Camera-move prompts follow the Seedance 2.0 image-to-video formula (works equally well for Kling 2.1 Pro):
  "Animate the provided image: preserve composition. <camera>. <style>. No scene cuts, one continuous shot.
   Avoid jitter, bent limbs, temporal flicker, identity drift."
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

CAMERA_ROTATIONS: dict[str, list[str]] = {
    "fashion": ["camera slow push-in, eye-level", "camera subtle parallax, lateral track left"],
    "lifestyle": ["camera slow push-in, eye-level", "camera subtle parallax, lateral track left"],
    "portrait": ["camera slow push-in, eye-level", "camera subtle parallax, lateral track left"],
    "cinematic": ["camera dolly forward, low angle hero shot", "camera slow orbit around subject"],
    "atmospheric": ["camera dolly forward, low angle hero shot", "camera slow orbit around subject"],
    "product": ["camera push-in close-up on product label", "camera tabletop arc move with shallow DoF"],
    "architectural": ["camera slow tilt up", "camera wide tracking shot"],
}
DEFAULT_ROTATION = ["camera gentle push-in", "camera slow lateral track"]

STYLE_BY_AESTHETIC: dict[str, str] = {
    "fashion": "cinematic film tone, 35mm, warm natural light",
    "lifestyle": "cinematic film tone, 35mm, warm natural light",
    "portrait": "cinematic film tone, 35mm, soft natural window light",
    "cinematic": "Denis Villeneuve cinematic, IMAX, anamorphic lens flare, teal-orange grade",
    "atmospheric": "moody atmospheric grade, soft volumetric light, film grain",
    "product": "clean studio commercial, soft rim light, editorial product photography",
    "architectural": "wide-angle architectural, even daylight, IMAX scale",
    "typography": "graphic poster motion, high contrast, bold composition",
    "poster": "graphic poster motion, high contrast, bold composition",
    "illustration": "stylized illustration motion, painterly transitions",
    "stylized": "stylized illustration motion, painterly transitions",
    "brand_palette": "brand-locked palette, even color grading, minimal motion",
}
DEFAULT_STYLE = "cinematic film tone, soft natural light"

NEGATIVES_BASE = "Avoid jitter, bent limbs, temporal flicker, identity drift."
NEGATIVES_PRODUCT = "Avoid jitter, label drift, bent limbs, temporal flicker, identity drift."

MAX_SHOTS = 8


def _rotation_for(aesthetic_type: str | None) -> list[str]:
    if not aesthetic_type:
        return DEFAULT_ROTATION
    return CAMERA_ROTATIONS.get(aesthetic_type.strip().lower(), DEFAULT_ROTATION)


def _style_for(aesthetic_type: str | None) -> str:
    if not aesthetic_type:
        return DEFAULT_STYLE
    return STYLE_BY_AESTHETIC.get(aesthetic_type.strip().lower(), DEFAULT_STYLE)


def _still_for(prompt_entry: dict) -> str:
    return prompt_entry.get("output_path") or prompt_entry.get("src") or ""


def _build_camera_prompt(camera: str, style: str, *, product_lock: bool) -> str:
    """Compose a Seedance/Kling-shaped I2V prompt: animate, camera, style, no cuts, negatives."""
    if product_lock:
        animate = "Animate the provided image: preserve product geometry, label text, and brand marks exactly"
        negatives = NEGATIVES_PRODUCT
    else:
        animate = "Animate the provided image: preserve composition and colors"
        negatives = NEGATIVES_BASE
    return (
        f"{animate}. {camera}. {style}. "
        f"No scene cuts, one continuous shot. {negatives}"
    )


def storyboard(
    fingerprint: dict,
    top_prompts: list[dict],
    duration_s: int = 10,
    clip_s: int = 5,
    *,
    product_lock: bool = False,
) -> list[dict]:
    """Returns list of {shot_n, still_path, camera_move_prompt, duration_s}.

    `product_lock=True` swaps in label-preservation language and product-aware negatives.
    """
    if clip_s <= 0:
        raise ValueError("clip_s must be > 0")
    if duration_s <= 0:
        raise ValueError("duration_s must be > 0")
    if not top_prompts:
        raise ValueError("top_prompts must contain at least one entry")

    n_shots = min(MAX_SHOTS, max(1, math.ceil(duration_s / clip_s)))
    aesthetic = (fingerprint.get("aesthetic_type") if fingerprint else None) or ""
    rotation = _rotation_for(aesthetic)
    style = _style_for(aesthetic)

    shots: list[dict] = []
    remaining = duration_s
    for i in range(n_shots):
        prompt_entry = top_prompts[i % len(top_prompts)]
        camera = rotation[i % len(rotation)]
        is_last = i == n_shots - 1
        dur = min(clip_s, remaining) if is_last else clip_s
        if dur <= 0:
            dur = clip_s
        shots.append({
            "shot_n": i + 1,
            "still_path": _still_for(prompt_entry),
            "camera_move_prompt": _build_camera_prompt(camera, style, product_lock=product_lock),
            "duration_s": dur,
        })
        remaining -= dur
    return shots


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _main() -> int:
    parser = argparse.ArgumentParser(description="Plan a storyboard from fingerprint + top prompts.")
    parser.add_argument("--fingerprint", required=True, help="Path to fingerprint.json")
    parser.add_argument("--top-prompts", required=True, help="Path to top_prompts.json (list of dicts)")
    parser.add_argument("--duration", type=int, default=10, help="Total duration in seconds (default 10)")
    parser.add_argument("--clip", type=int, default=5, help="Clip length in seconds (default 5)")
    parser.add_argument("--write", action="store_true", help="Write to output/prompts/storyboard.json")
    args = parser.parse_args()

    fp_path = Path(args.fingerprint)
    tp_path = Path(args.top_prompts)
    fingerprint = _load_json(fp_path) if fp_path.exists() else {}
    top_prompts = _load_json(tp_path) if tp_path.exists() else []
    if not isinstance(top_prompts, list):
        raise SystemExit("top_prompts file must contain a JSON list")

    shots = storyboard(fingerprint, top_prompts, duration_s=args.duration, clip_s=args.clip)

    if args.write:
        out_dir = Path("output/prompts")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "storyboard.json"
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(shots, f, indent=2)
        print(f"wrote {out_path} ({len(shots)} shots)")
    else:
        print(json.dumps(shots, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
