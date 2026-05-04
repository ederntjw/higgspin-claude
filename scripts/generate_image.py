"""Single-image generation entrypoint with lane cascading.

Routes a prompt + optional reference images through the right Higgsfield
model. When a product image is supplied we lock onto the i2i_product_middle
cascade (flux/kontext -> nano-banana-pro -> soul/inpaint). Otherwise we go
straight to the aesthetic-mapped t2i model with no fallback.

Outputs land in output/generated/<slug>_<n>.png plus a JSON sidecar with
model + prompt + references + credit estimate.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import requests

# Make `scripts` importable when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.lib import cost_tracker, mcp_client  # noqa: E402
from scripts.models import AESTHETIC_TO_MODEL, LANE_CASCADE  # noqa: E402

OUTPUT_DIR = Path("output/generated")

PRODUCT_PREAMBLE = (
    "Preserve the product in the first reference image exactly — geometry, "
    "label text, brand marks, proportions, and material. Place it into the "
    "following scene: "
)

CREDIT_ESTIMATES = {
    "google/nano-banana-pro":          2.0,
    "black-forest-labs/flux/kontext":  1.5,
    "higgsfield-ai/soul/inpaint":      0.25,
    "black-forest-labs/flux-2":        2.0,
    "bytedance/seedream/v5/lite":      0.5,
    "openai/gpt-image":                1.0,
    "higgsfield-ai/soul/hex":          1.5,
}
DEFAULT_CREDIT = 1.0


def _slugify(text: str, max_len: int = 40) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return (text or "image")[:max_len]


def _next_index(slug: str) -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    existing = list(OUTPUT_DIR.glob(f"{slug}_*.png"))
    nums = []
    for p in existing:
        m = re.match(rf"{re.escape(slug)}_(\d+)\.png$", p.name)
        if m:
            nums.append(int(m.group(1)))
    return (max(nums) + 1) if nums else 1


def _credit_estimate(model_id: str) -> float:
    return CREDIT_ESTIMATES.get(model_id, DEFAULT_CREDIT)


def _download(url: str, dest: Path) -> None:
    resp = requests.get(url, timeout=300, stream=True)
    resp.raise_for_status()
    with dest.open("wb") as fh:
        for chunk in resp.iter_content(chunk_size=65536):
            if chunk:
                fh.write(chunk)


def _extract_url(result: dict) -> str:
    if "images" in result and result["images"]:
        first = result["images"][0]
        if isinstance(first, dict) and "url" in first:
            return first["url"]
    if "video_url" in result:
        return result["video_url"]
    raise mcp_client.HiggsfieldError(f"No image URL in response: {result!r}")


def generate(prompt: str, *, aesthetic: str, product_image: str | None,
             mood_image: str | None, aspect: str = "4:5",
             resolution: str = "2K") -> dict:
    """Run a single generation through the appropriate lane.

    Returns the sidecar dict (also written to disk).
    """
    if product_image is not None:
        lane = "i2i_product_middle"
        cascade = LANE_CASCADE[lane]
        final_prompt = PRODUCT_PREAMBLE + prompt
    else:
        lane = f"t2i_{aesthetic}"
        if aesthetic not in AESTHETIC_TO_MODEL:
            raise KeyError(f"Unknown aesthetic '{aesthetic}'")
        cascade = [AESTHETIC_TO_MODEL[aesthetic]]
        final_prompt = prompt

    references = [p for p in (product_image, mood_image) if p]
    args = {
        "prompt": final_prompt,
        "aspect_ratio": aspect,
        "resolution": resolution,
    }
    if references:
        args["reference_images"] = references

    last_err: Exception | None = None
    result: dict | None = None
    model_id: str | None = None
    for idx, candidate in enumerate(cascade):
        try:
            print(f"[generate_image] lane={lane} fallback={idx} model={candidate}",
                  file=sys.stderr)
            result = mcp_client.call(candidate, args, lane=lane)
            model_id = candidate
            break
        except mcp_client.HiggsfieldError as exc:
            last_err = exc
            print(f"[generate_image] {candidate} failed: {exc}", file=sys.stderr)
            continue

    if result is None or model_id is None:
        raise mcp_client.HiggsfieldError(
            f"All cascade candidates exhausted for lane {lane}: {last_err}"
        )

    source_url = _extract_url(result)
    slug = _slugify(prompt)
    n = _next_index(slug)
    output_path = OUTPUT_DIR / f"{slug}_{n}.png"
    sidecar_path = OUTPUT_DIR / f"{slug}_{n}.json"
    _download(source_url, output_path)

    credits_spent = _credit_estimate(model_id)
    sidecar = {
        "model_id": model_id,
        "prompt": final_prompt,
        "references": [product_image, mood_image],
        "aspect": aspect,
        "resolution": resolution,
        "source_url": source_url,
        "output_path": str(output_path),
        "credits_spent": credits_spent,
    }
    sidecar_path.write_text(json.dumps(sidecar, indent=2, ensure_ascii=False),
                            encoding="utf-8")

    cost_tracker.record(lane, model_id, credits_spent, str(sidecar_path))
    return sidecar


def _cli() -> None:
    p = argparse.ArgumentParser(description="Generate a single image via Higgsfield.")
    p.add_argument("--prompt", required=True)
    p.add_argument("--aesthetic", required=True,
                   help="One of: " + ", ".join(sorted(AESTHETIC_TO_MODEL)))
    p.add_argument("--product", default=None,
                   help="Path to product reference image (locks i2i lane).")
    p.add_argument("--mood", default=None, help="Path to mood reference image.")
    p.add_argument("--aspect", default="4:5")
    p.add_argument("--resolution", default="2K")
    args = p.parse_args()

    sidecar = generate(
        args.prompt,
        aesthetic=args.aesthetic,
        product_image=args.product,
        mood_image=args.mood,
        aspect=args.aspect,
        resolution=args.resolution,
    )
    print(json.dumps(sidecar, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    _cli()
