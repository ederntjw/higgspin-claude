"""Single-entry orchestrator for the aesthetic-automation v2 pipeline.

Wires stages 1-8 from the v2 spec. Vision steps (fingerprint, extract) are
operator-run via Claude Code per CLAUDE.md; this runner expects their
on-disk artifacts and codifies everything else.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts import extract_prompts, fingerprint as fingerprint_mod  # noqa: E402
from scripts import generate_image, generate_video, storyboard as storyboard_mod, stitch_video  # noqa: E402
from scripts import models as models_mod  # noqa: E402
from scripts.lib import cost_tracker  # noqa: E402

PROMPTS = ROOT / "output" / "prompts"
FINGERPRINT_PATH = PROMPTS / "fingerprint.json"
EXTRACTED_PATH = PROMPTS / "extracted_prompts.jsonl"
STORYBOARD_PATH = PROMPTS / "storyboard.json"
SUMMARY_PATH = PROMPTS / "run_summary.md"
PINTEREST_DIR = ROOT / "output" / "pinterest"
FINAL_MP4 = ROOT / "output" / "ad" / "final.mp4"
PRODUCT_PATH = ROOT / "references" / "product" / "hero.png"
AUDIO_DIR = ROOT / "assets" / "audio"
IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def _slugify(s: str) -> str:
    return (re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "query")[:60]


@dataclass
class Context:
    args: argparse.Namespace
    fingerprint: dict | None = None
    query: str | None = None
    pin_slug: str | None = None
    pin_count: int = 0
    top_prompts: list[dict] = field(default_factory=list)
    sidecars: list[dict] = field(default_factory=list)
    storyboard: list[dict] = field(default_factory=list)
    clip_paths: list[str] = field(default_factory=list)
    final_video: str | None = None
    product_path: str | None = None
    errors: list[tuple[int, str]] = field(default_factory=list)
    skip: set[int] = field(default_factory=set)


def _log(stage: int, msg: str) -> None:
    print(f"[Stage {stage}] {msg}", flush=True)


def _skipped(stage: int, ctx: Context) -> bool:
    if stage in ctx.skip:
        _log(stage, "skipped (--skip-stages)")
        return True
    return False


def stage_1_fingerprint(args: argparse.Namespace, ctx: Context) -> None:
    if _skipped(1, ctx):
        return
    _log(1, f"expects fingerprint at {FINGERPRINT_PATH}. Run Claude vision per CLAUDE.md Stage 1 if missing.")
    if args.dry_run:
        _log(1, "[dry-run] would validate fingerprint.json via scripts.fingerprint.validate")
        return
    if not FINGERPRINT_PATH.exists():
        raise SystemExit(
            f"Stage 1: missing {FINGERPRINT_PATH}. Run the Claude vision step "
            f"described in CLAUDE.md Stage 1 to produce it, then rerun."
        )
    data = json.loads(FINGERPRINT_PATH.read_text(encoding="utf-8"))
    fingerprint_mod.validate(data)
    ctx.fingerprint = data
    _log(1, f"fingerprint OK (aesthetic_type={data['aesthetic_type']})")


def _count_pins(target: Path) -> int:
    if not target.exists():
        return 0
    return sum(1 for p in target.iterdir() if p.is_file() and p.suffix.lower() in IMG_EXTS)


def stage_2_pinterest(args: argparse.Namespace, ctx: Context) -> None:
    if _skipped(2, ctx):
        return
    query = args.query or (ctx.fingerprint or {}).get("search_query")
    if not query:
        if args.dry_run:
            query = "<search_query from fingerprint>"
        else:
            raise SystemExit("Stage 2: no search query (pass --query or supply fingerprint.json)")
    ctx.query = query
    ctx.pin_slug = _slugify(query)
    target = PINTEREST_DIR / ctx.pin_slug
    cmd = [sys.executable, str(ROOT / "scripts" / "pinterest_scrape.py"), query, "--count", "40"]
    if args.dry_run:
        _log(2, f"[dry-run] would run: {' '.join(cmd)}")
        return
    if target.exists() and any(target.iterdir()):
        ctx.pin_count = _count_pins(target)
        _log(2, f"reusing {target} ({ctx.pin_count} files)")
        return
    _log(2, f"running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True, cwd=str(ROOT))
    ctx.pin_count = _count_pins(target)
    _log(2, f"scraped {ctx.pin_count} pins into {target}")


def stage_3_extract(args: argparse.Namespace, ctx: Context) -> None:
    if _skipped(3, ctx):
        return
    _log(3, f"expects {EXTRACTED_PATH}. Run Claude vision over output/pinterest/{ctx.pin_slug or '<slug>'}/ to populate it.")
    n_top = max(1, int(args.n_images) // 2)
    if args.dry_run:
        _log(3, f"[dry-run] would call extract_prompts.top_n({EXTRACTED_PATH}, {n_top})")
        return
    if not EXTRACTED_PATH.exists():
        raise SystemExit(
            f"Stage 3: missing {EXTRACTED_PATH}. Run the Claude vision extract step "
            f"per CLAUDE.md Stage 3, then rerun."
        )
    ctx.top_prompts = extract_prompts.top_n(str(EXTRACTED_PATH), n_top)
    if not ctx.top_prompts:
        raise SystemExit("Stage 3: extracted_prompts.jsonl is empty.")
    _log(3, f"selected top {len(ctx.top_prompts)} prompts")


def _resolve_product(args: argparse.Namespace) -> str | None:
    mode = args.product_lock
    if mode == "off":
        return None
    if PRODUCT_PATH.exists():
        return str(PRODUCT_PATH)
    if mode == "on":
        raise SystemExit(f"Stage 4: --product-lock=on but {PRODUCT_PATH} not found.")
    return None


def stage_4_generate(args: argparse.Namespace, ctx: Context) -> None:
    if _skipped(4, ctx):
        return
    ctx.product_path = _resolve_product(args)
    aesthetic = (ctx.fingerprint or {}).get("aesthetic_type", "lifestyle")
    pairs = ctx.top_prompts or ([{"src": "<top_pin>", "prompt": "<top_prompt>", "score": 1.0}] if args.dry_run else [])
    primary_slug = (
        models_mod.LANE_CASCADE["i2i_product_middle"][0]
        if ctx.product_path
        else models_mod.AESTHETIC_TO_MODEL.get(aesthetic, models_mod.LANE_TO_MODEL["t2i_middle"])
    )
    for p in pairs:
        mood, prompt = p.get("src"), p.get("prompt", "")
        for variant in (1, 2):
            if args.dry_run:
                _log(4, f"[dry-run] generate_image.generate slug={primary_slug} aesthetic={aesthetic} product={ctx.product_path} mood={mood} variant={variant}")
                continue
            _log(4, f"generating variant {variant} for prompt score={p.get('score')}")
            ctx.sidecars.append(generate_image.generate(
                prompt, aesthetic=aesthetic, product_image=ctx.product_path,
                mood_image=mood, aspect="4:5", resolution="2K",
            ))
    _log(4, f"produced {len(ctx.sidecars)} stills")


def stage_5_storyboard(args: argparse.Namespace, ctx: Context) -> None:
    if _skipped(5, ctx):
        return
    if args.dry_run:
        _log(5, f"[dry-run] would build storyboard for duration={args.duration}s clip={args.clip}s")
        return
    stills = [s.get("output_path") for s in ctx.sidecars if s.get("output_path")]
    if not stills:
        raise SystemExit("Stage 5: no generated stills available for storyboard.")
    shot_inputs = [{"output_path": p} for p in stills]
    ctx.storyboard = storyboard_mod.storyboard(
        ctx.fingerprint or {},
        shot_inputs,
        duration_s=int(args.duration),
        clip_s=int(args.clip),
        product_lock=bool(ctx.product_path),
    )
    STORYBOARD_PATH.parent.mkdir(parents=True, exist_ok=True)
    STORYBOARD_PATH.write_text(json.dumps(ctx.storyboard, indent=2), encoding="utf-8")
    _log(5, f"wrote {STORYBOARD_PATH} ({len(ctx.storyboard)} shots)")


def stage_6_video(args: argparse.Namespace, ctx: Context) -> None:
    if _skipped(6, ctx):
        return
    if args.dry_run:
        slug = models_mod.LANE_TO_MODEL["i2v_middle"]
        _log(6, f"[dry-run] would generate {max(1, args.duration // args.clip)} clips via slug={slug}")
        return
    video_lane = "i2v_product_lock" if ctx.product_path else "i2v_middle"
    for shot in ctx.storyboard:
        _log(6, f"clip shot_{shot['shot_n']} ({shot['duration_s']}s, lane={video_lane})")
        sc = generate_video.generate_clip(
            shot["still_path"], shot["camera_move_prompt"],
            duration_s=shot["duration_s"], lane=video_lane,
        )
        ctx.clip_paths.append(sc["output_path"])
    _log(6, f"generated {len(ctx.clip_paths)} clips")


def stage_7_stitch(args: argparse.Namespace, ctx: Context) -> None:
    if _skipped(7, ctx):
        return
    audio = next((str(f) for f in sorted(AUDIO_DIR.glob("*.mp3"))), "") if AUDIO_DIR.exists() else ""
    if args.dry_run:
        _log(7, f"[dry-run] would stitch {len(ctx.clip_paths) or 'N'} clips with audio={audio or '(none)'} to {FINAL_MP4}")
        return
    if not ctx.clip_paths:
        raise SystemExit("Stage 7: no clips to stitch.")
    FINAL_MP4.parent.mkdir(parents=True, exist_ok=True)
    ctx.final_video = stitch_video.stitch(ctx.clip_paths, audio, str(FINAL_MP4))
    _log(7, f"final ad: {ctx.final_video}")


def stage_8_report(args: argparse.Namespace, ctx: Context) -> None:
    if _skipped(8, ctx):
        return
    if args.dry_run:
        _log(8, f"[dry-run] would write {SUMMARY_PATH} with cost ledger + artifact links")
        return
    totals = cost_tracker.total()
    fp = ctx.fingerprint or {}
    parts = [
        "# Run summary\n\n## Fingerprint\n",
        "```json\n" + json.dumps(fp, indent=2) + "\n```\n",
        f"\n## Search query\n\n`{ctx.query or '(none)'}`\n",
        f"\n## Pins scraped\n\n{ctx.pin_count} files in `output/pinterest/{ctx.pin_slug}/`\n",
        "\n## Top prompts\n",
    ]
    for i, p in enumerate(ctx.top_prompts, 1):
        sc = ctx.sidecars[(i - 1) * 2] if (i - 1) * 2 < len(ctx.sidecars) else {}
        parts.append(
            f"{i}. score={p.get('score', 0):.2f} model={sc.get('model_id', '(none)')}\n"
            f"   prompt: {p.get('prompt')}\n   sidecar: {sc.get('output_path', '(none)')}\n"
        )
    parts.append("\n## Generated stills\n")
    parts.extend(f"- {s.get('output_path')} (model {s.get('model_id')})\n" for s in ctx.sidecars)
    parts.append("\n## Clips\n")
    parts.extend(f"- {c}\n" for c in ctx.clip_paths)
    parts.append(f"\n## Final ad\n\n{ctx.final_video or '(not produced)'}\n")
    parts.append("\n## Cost ledger\n```json\n" + json.dumps(totals, indent=2) + "\n```\n")
    if ctx.errors:
        parts.append("\n## Errors\n")
        parts.extend(f"- stage {n}: {m}\n" for n, m in ctx.errors)
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text("".join(parts), encoding="utf-8")
    _log(8, f"wrote {SUMMARY_PATH} (total credits={totals.get('total_credits')})")


STAGES: list[tuple[int, str, Callable[[argparse.Namespace, Context], None]]] = [
    (1, "fingerprint", stage_1_fingerprint),
    (2, "pinterest", stage_2_pinterest),
    (3, "extract", stage_3_extract),
    (4, "generate-images", stage_4_generate),
    (5, "storyboard", stage_5_storyboard),
    (6, "generate-video", stage_6_video),
    (7, "stitch", stage_7_stitch),
]


def _parse_skip(raw: str | None) -> set[int]:
    return {int(t) for t in (raw or "").split(",") if t.strip()}


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Aesthetic automation v2 orchestrator.")
    p.add_argument("--duration", type=int, default=10)
    p.add_argument("--clip", type=int, default=5)
    p.add_argument("--product-lock", choices=("auto", "on", "off"), default="auto")
    p.add_argument("--skip-stages", default="")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--query", default=None)
    p.add_argument("--n-images", type=int, default=10)
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    ctx = Context(args=args, skip=_parse_skip(args.skip_stages))
    first: tuple[int, str] | None = None
    for stage_n, name, fn in STAGES:
        try:
            fn(args, ctx)
        except SystemExit as e:
            msg = str(e) or f"stage {stage_n} ({name}) requested exit"
            ctx.errors.append((stage_n, msg))
            first = first or (stage_n, msg)
            _log(stage_n, f"FAIL: {msg}")
        except Exception as e:  # noqa: BLE001
            msg = f"{type(e).__name__}: {e}"
            ctx.errors.append((stage_n, msg))
            first = first or (stage_n, msg)
            _log(stage_n, f"ERROR: {msg}")
    try:
        stage_8_report(args, ctx)
    except Exception as e:  # noqa: BLE001
        _log(8, f"ERROR: {type(e).__name__}: {e}")
        first = first or (8, str(e))
    if first is not None:
        return 1 if args.dry_run else max(1, first[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
