# Aesthetic Automation v2 — Product-Locked Pipeline + Short-Form Ad

**Date:** 2026-05-04
**Status:** Approved (implicit) — proceeding to plan + parallel build
**Owner:** project root `/Users/edernimac/Desktop/higgspin-claude`

## Problem

The v1 pipeline (CLAUDE.md) takes a Pinterest moodboard and produces aesthetically-on-brand AI images via Higgsfield. It has no concept of an actual **product** to keep consistent across generations, and it produces no video output. The user wants:

1. The exact product they're advertising to remain unmodified across all generated images (geometry, label, branding intact).
2. A short-form ad (default 10 seconds, configurable) assembled from the generated stills.
3. Middle-cost models throughout (not cheapest, not flagship).
4. Live-as-of-May-2026 model selection — no stale slugs.

## Non-goals

- AI voice-over (skipped; instrumental + on-screen text only unless user asks).
- Audio mixing beyond background music + simple text overlays.
- Multi-aspect-ratio export (single 9:16 vertical default; configurable).
- Production-grade error retries / queueing — best-effort with disk-resumable stages is enough.

## Models — May 2026, middle-cost tier

Verified via two parallel research agents on 2026-05-04 (Higgsfield docs via context7, PyPI, official launch posts, third-party reviews).

| Lane | Model slug | Cost | Why this tier |
|---|---|---|---|
| Hero shot, multi-ref (moodboard + product) | `google/nano-banana-pro` | 2 cr/img | Industry leader for product photography in 2026; up to 14 reference images; auto-fidelity. Middle vs. flagship Sora-2-image. |
| Scene variations (instruction edit, subject lock) | `black-forest-labs/flux/kontext` | 1.5 cr/img | Subject-preserving instruction edits, cheaper than nano-banana for high-volume scenes. |
| Insurance / pixel-perfect product | `higgsfield-ai/soul/inpaint` | 0.25 cr/img | Mask product region, regenerate only background. Used as fallback when label drifts. |
| Image-to-video (10s ad clips) | `kling-video/v2.1/pro/image-to-video` | ~7 cr / 5s clip | Best label readability among video models per May 2026 reviews; explicitly named middle sweet spot. |
| Vision (fingerprint + extract) | Claude Opus 4.7 (this session) | n/a | Already available, no extra API cost. |
| Audio + stitch | `ffmpeg` + bundled royalty-free track | $0 | No AI audio per assumption. |

**Avoided:** Veo 3.1 / Sora 2 (premium, drift on product text), Soul/standard for product (person-tuned), Seedance 2.0 pro (premium tier — its v2/fast lane is acceptable as alt fallback).

**Slug fixes vs. v1 CLAUDE.md:**
- `bytedance/seedream-5` → `bytedance/seedream/v5/lite`
- `openai/gpt-image-2` → `openai/gpt-image`

## Architecture

```
references/
  images/          (moodboard pins — existing)
  product/
    hero.png       (OPTIONAL — if present, pipeline runs in product-lock mode)

output/
  pinterest/{slug}/   (scraped pins)
  prompts/            (fingerprint.json, extracted_prompts.jsonl, storyboard.json, run_summary.md)
  generated/          (PNG stills + JSON sidecars)
  ad/
    clips/            (raw 5s I2V clips)
    final.mp4         (stitched ad, default 10s)

scripts/
  lib/
    mcp_client.py     (MCP-first wrapper, falls through to higgsfield-client SDK, then HTTP)
    cost_tracker.py   (per-call credit accounting, JSON sidecar)
  models.py           (LANE_TO_MODEL + AESTHETIC_TO_MODEL — refreshed slugs)
  fingerprint.py      (schema validator; no API calls)
  pinterest_scrape.py (existing — unchanged)
  extract_prompts.py  (Claude vision is invoked from orchestrator; this module
                       just owns the JSONL writer + scoring math)
  generate_image.py   (product-lock aware; cascades nano-banana-pro → flux/kontext → soul/inpaint)
  storyboard.py       (10s → 2 × 5s shot beats; configurable to 30s = 6 × 5s)
  generate_video.py   (Kling 2.1 Pro I2V wrapper; one call per shot)
  stitch_video.py     (ffmpeg concat + audio overlay + optional text)
  orchestrate.py      (single-entry pipeline runner, CLI: python scripts/orchestrate.py [--duration 10])

assets/
  audio/              (3 royalty-free instrumental tracks bundled)

tests/
  test_models.py      (routing tables — no API calls)
  test_dry_run.py     (orchestrator with --dry-run prints calls without executing)

docs/superpowers/specs/
  2026-05-04-aesthetic-automation-v2-design.md   (this file)
```

## Data flow

```
Stage 1  fingerprint     Claude vision over references/images/  →  fingerprint.json
Stage 2  pinterest       existing scraper                         →  output/pinterest/{slug}/
Stage 3  extract-prompts Claude vision scores pins                →  extracted_prompts.jsonl (top 5)
Stage 4  generate-images per prompt: nano-banana-pro
                          inputs:  prompt + product.png + best mood pin
                          on 4xx:  flux/kontext same inputs
                          on drift: soul/inpaint with product mask
                                                                  →  output/generated/*.png + sidecar.json
Stage 5  storyboard      Claude breaks the duration into N × 5s   →  storyboard.json (default N=2)
Stage 6  generate-video  per shot: kling-video/v2.1/pro/image-to-video
                          input:   chosen still + camera-move prompt
                                                                  →  output/ad/clips/shot_{n}.mp4
Stage 7  stitch          ffmpeg concat + music + text overlays    →  output/ad/final.mp4
Stage 8  report          markdown summary with cost ledger        →  output/prompts/run_summary.md
```

## Product-lock semantics

The pipeline checks for `references/product/hero.png` at startup:

- **Present** → product-lock mode. Every Stage 4 call passes `hero.png` as the first reference and prepends to each prompt:
  > *"Preserve the product in the first reference image exactly — geometry, label text, brand marks, proportions, and material. Place it into the following scene:"*
- **Absent** → placeholder mode. Stage 4 generates moodboard-only scenes. User composites a real product later.

A `--product-lock=on|off|auto` CLI flag overrides detection.

## Failure semantics

- Each stage writes its artifact to disk before exiting; pipeline auto-resumes from last good stage.
- MCP-first call. If the registered MCP returns an error or the user hasn't authenticated (`/mcp`), the wrapper falls through to direct `higgsfield-client` SDK with `HF_KEY`. If that fails, raw HTTP `POST https://platform.higgsfield.ai/{slug}` with `Authorization: Key {key}:{secret}`.
- Model 4xx/5xx → cascade `nano-banana-pro → flux/kontext → soul/inpaint`. Each tier logged in the sidecar.
- Video drift past 8s → enforced 5s clip ceiling. Always stitch in post.
- Pinterest CAPTCHA on first run is unchanged from v1 — solve once, session cached in `.playwright-state/`.

## Cost ceiling per full run (10s default)

| Item | Quantity | Unit | Subtotal |
|---|---|---|---|
| Stage 4 hero+variant images | 10 | 2 cr | 20 cr |
| Stage 6 video clips | 2 × 5s | 7 cr | 14 cr |
| **Total** | | | **34 cr ≈ $3–6** on Higgsfield mid-tier plan |

For the 30s configuration: ~62 cr ≈ $5–10.

## Authentication

- `HF_KEY=key:secret` in `.env` — required for SDK fallback.
- Pinterest creds in `.env` — existing.
- MCP is registered (`https://mcp.higgsfield.ai/mcp`); user authenticates via `/mcp` once. Tools register in tool-registry on next Claude Code session restart.

## Testing

- `tests/test_models.py` — pure-Python; verifies the routing tables produce expected slugs for known inputs.
- `tests/test_dry_run.py` — calls `orchestrate.py --dry-run`; asserts the printed call list matches expectations without hitting any API.
- One smoke run end-to-end after build, using the cheapest fallback (`soul/inpaint` only) to validate the SDK path with minimal credit burn.

## 14 work units (parallel build lanes)

Numbered 1–14; each maps to one parallel build agent. Interfaces are spec'd in this document so all 14 can be implemented concurrently.

1. `scripts/lib/mcp_client.py` — call wrapper with three-tier fallback
2. `scripts/lib/cost_tracker.py` — credit accounting
3. `scripts/models.py` — refreshed routing tables
4. `scripts/fingerprint.py` — schema + validator
5. `scripts/extract_prompts.py` — JSONL writer + score math
6. `scripts/generate_image.py` — product-lock aware, cascade
7. `scripts/storyboard.py` — N × 5s shot decomposition
8. `scripts/generate_video.py` — Kling I2V wrapper
9. `scripts/stitch_video.py` — ffmpeg + audio + text overlay
10. `scripts/orchestrate.py` — CLI single-entry runner
11. `references/product/README.md` — drop-in instructions
12. `tests/test_models.py` + `tests/test_dry_run.py`
13. `CLAUDE.md` — refresh for v2
14. `assets/audio/` + `assets/audio/README.md` — three royalty-free tracks (download instructions, licence note)

## Interface contracts (so the 14 lanes can run in parallel)

```python
# scripts/lib/mcp_client.py
def call(slug: str, args: dict, *, lane: str | None = None) -> dict:
    """Returns {"images": [{"url": ...}]} or {"video_url": ...}.
    Cascades MCP → SDK → HTTP. Raises HiggsfieldError on terminal failure."""

# scripts/lib/cost_tracker.py
def record(lane: str, slug: str, credits: float, sidecar_path: str) -> None: ...
def total() -> dict: ...

# scripts/models.py
LANE_TO_MODEL: dict[str, str]              # {"i2i_product_middle": "...", ...}
AESTHETIC_TO_MODEL: dict[str, str]
def resolve(lane: str, *, fallback: int = 0) -> str: ...

# scripts/fingerprint.py
def validate(d: dict) -> None: ...   # raises ValueError on bad shape
SCHEMA_KEYS = ("palette","composition","lighting","subject","mood","aesthetic_type","search_query")

# scripts/extract_prompts.py
def write_prompt(jsonl_path: str, src: str, prompt: str, score: float) -> None: ...
def top_n(jsonl_path: str, n: int = 5) -> list[dict]: ...

# scripts/generate_image.py
def generate(prompt: str, *, aesthetic: str, product_image: str | None,
             mood_image: str | None, aspect: str = "4:5",
             resolution: str = "2K") -> dict:
    """Returns sidecar dict with: model_id, prompt, references, output_path, credits_spent."""

# scripts/storyboard.py
def storyboard(fingerprint: dict, top_prompts: list[dict],
               duration_s: int = 10, clip_s: int = 5) -> list[dict]:
    """Returns list of {shot_n, still_path, camera_move_prompt, duration_s}."""

# scripts/generate_video.py
def generate_clip(still_path: str, camera_move_prompt: str,
                  duration_s: int = 5, resolution: str = "1080p") -> dict:
    """Returns sidecar dict with: model_id, still_path, prompt, output_path, credits_spent."""

# scripts/stitch_video.py
def stitch(clips: list[str], audio_path: str, out_path: str,
           text_overlays: list[dict] | None = None) -> str: ...

# scripts/orchestrate.py
# CLI: python scripts/orchestrate.py [--duration 10] [--product-lock auto]
#                                    [--skip-stages 1,2] [--dry-run]
```

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| MCP not auth'd in this session | SDK fallback already in `mcp_client.py`. Once user runs `/mcp` and restarts, MCP path activates automatically. |
| Higgsfield slug drift mid-pipeline | Static fallback dictionaries in `models.py`; orchestrator can be re-run with `--skip-stages` to re-do only the affected stage. |
| Label drift in long video clips | 5s clip ceiling enforced; stitch in post. |
| Royalty-free music files not present | Bundled `assets/audio/README.md` lists Pixabay tracks; pipeline auto-picks the first `.mp3` it finds; no music if directory empty (silent ad). |
| User hasn't dropped product photo | Auto-detection — pipeline runs in placeholder mode without breaking. |

## Cutover plan

The v2 pipeline replaces v1's orchestration prompt in `CLAUDE.md`. v1 scripts (`pinterest_scrape.py`, `generate.py`, `models.py`) stay; `generate.py` becomes the SDK fallback that `mcp_client.py` invokes.
