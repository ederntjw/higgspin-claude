# Aesthetic Automation v2 — Product-Locked Pipeline + Short-Form Ad

Pinterest moodboard → extracted prompts → Higgsfield stills → Kling I2V clips → stitched short-form ad. One CLI entry point; the two vision passes (Stages 1 + 3) are done by Claude Code automatically when an operator runs the pipeline from inside it.

---

## If the user asks "how do I use this" / "how do I run this" / "how do I use you"

Answer with this exact sequence — these are the 5 steps a public user follows from a fresh clone. Don't editorialize, don't add philosophy, don't split "use the pipeline" from "use Claude Code". They're the same thing.

1. **Run setup once** (creates `.venv`, installs deps, fetches Playwright Chromium, copies `.env.example` → `.env`):
   ```bash
   ./setup.sh
   ```
   If `ffmpeg` isn't installed it prints a warning — install it (`brew install ffmpeg` on macOS, `sudo apt install ffmpeg` on Linux).

2. **Fill in `.env`** with the user's Higgsfield key and Pinterest credentials. The file has comments explaining the format.

3. **Drop 5–10 moodboard images** into `references/images/`. Each ≥1024px on the long edge. JPG / PNG / WEBP all fine.

4. *(Optional, enables product-lock mode)* **Drop a clean product photo** at `references/product/hero.png`. Transparent or white background, sharp focus.

5. **Tell Claude Code in plain English**: *"run the pipeline"*. Claude will:
   - Do Stage 1 by reading `references/images/` with vision and writing `output/prompts/fingerprint.json`.
   - Run Stage 2 (`python scripts/orchestrate.py --skip-stages 1`) to scrape Pinterest.
   - Do Stage 3 by scoring each scraped pin against the fingerprint and writing `output/prompts/extracted_prompts.jsonl`.
   - Run Stages 4–8 via the orchestrator. Final ad lands at `output/ad/final.mp4`. Cost ledger lands at `output/prompts/run_summary.md`.

That's the whole user-facing flow. Other useful one-liners the user might say:

- *"run a 30-second version"* → `python scripts/orchestrate.py --duration 30`
- *"only redo the video"* → `python scripts/orchestrate.py --skip-stages 1,2,3,4`
- *"dry run"* → `python scripts/orchestrate.py --dry-run` (no API calls, no credit burn)
- *"why did it fail"* → check `output/prompts/run_summary.md` — every stage's error is logged there.

Do not pause and ask "what would you like to do?" when the user clearly just wants to run the thing. Run it.

---

## One-time setup (manual equivalent of `./setup.sh`)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium    # add --with-deps on Apple Silicon
brew install ffmpeg            # required for Stage 7 stitch
cp .env.example .env           # then fill in HF_KEY + Pinterest creds
```

The Higgsfield MCP is registered for this project (see `claude mcp list`). Authenticate it once via `/mcp` inside an interactive Claude Code session — after that, generation runs through the MCP and the SDK is the automatic fallback.

## Project layout

```
references/
  images/              # 5–10 moodboard refs, ≥1024px, JPG/PNG/WEBP
  product/             # OPTIONAL: drop hero.png|jpg|webp here for product-lock mode

output/
  pinterest/{slug}/    # scraped pins per query
  prompts/             # fingerprint.json, extracted_prompts.jsonl, storyboard.json, run_summary.md
  generated/           # final stills + JSON sidecars
  ad/
    clips/             # raw 5s I2V clips
    final.mp4          # stitched ad (default 10s)

scripts/
  orchestrate.py       # single-entry CLI runner
  pinterest_scrape.py  # Playwright Pinterest scraper
  fingerprint.py       # schema + validator
  extract_prompts.py   # JSONL writer + scoring math
  generate_image.py    # product-lock-aware cascade
  storyboard.py        # duration → N × 5s shot beats
  generate_video.py    # Kling 2.1 Pro I2V wrapper
  stitch_video.py      # ffmpeg concat + audio + text overlays
  generate.py          # legacy SDK wrapper, retained as fallback
  models.py            # LANE_TO_MODEL + AESTHETIC_TO_MODEL routing tables
  lib/
    mcp_client.py      # MCP → SDK → HTTP three-tier wrapper
    cost_tracker.py    # per-call credit accounting

assets/
  audio/               # bundled royalty-free instrumentals (MP3)

tests/
  test_models.py       # routing tables (no API calls)
  test_dry_run.py      # orchestrator --dry-run smoke test

docs/superpowers/specs/
  2026-05-04-aesthetic-automation-v2-design.md   # full design doc
```

## Product photo (optional, drop-in)

- Drop a single `hero.png`, `hero.jpg`, or `hero.webp` into `references/product/`.
- The pipeline auto-detects it and switches into **product-lock mode**: every Stage 4 call passes the hero as the first reference and prepends a "preserve geometry, label text, brand marks" instruction.
- Without it, the pipeline runs in **placeholder mode** — moodboard-only scenes, ready for you to composite the real product later.
- Override detection with `--product-lock=on|off|auto`.

## Run it (single command)

```bash
python scripts/orchestrate.py [--duration 10] [--product-lock auto]
```

Flags:
- `--duration` — final ad length in seconds (default `10`; configurable, e.g. `30` produces 6 × 5s clips).
- `--product-lock` — `auto` (default), `on`, or `off`.
- `--skip-stages 1,2` — resume after a failure; each stage writes its artifact to disk.
- `--dry-run` — print the planned API calls without executing them.

Stages 1 and 3 are vision passes. The orchestrator pauses and prints exactly what to fingerprint or score; the operator (you, in Claude Code) does the vision work and writes the JSON, then resumes.

## Stage map

```
Stage 1  Fingerprint        Vision pass over references/images/      → output/prompts/fingerprint.json
Stage 2  Pinterest scrape   python scripts/pinterest_scrape.py       → output/pinterest/{slug}/
Stage 3  Extract prompts    Vision pass + score against fingerprint  → output/prompts/extracted_prompts.jsonl (top 5)
Stage 4  Generate stills    nano-banana-pro → flux/kontext → soul/inpaint cascade
                            with optional hero.png as ref-1          → output/generated/*.png + sidecars
Stage 5  Storyboard         duration ÷ 5s = N shot beats             → output/prompts/storyboard.json
Stage 6  Generate clips     kling-video/v2.1/pro/image-to-video      → output/ad/clips/shot_{n}.mp4
Stage 7  Stitch             ffmpeg concat + music + text overlays    → output/ad/final.mp4
Stage 8  Run report         markdown summary with cost ledger        → output/prompts/run_summary.md
```

### Stage 1 — Fingerprint (vision pass)

Read every image in `references/images/`. Produce:

```json
{
  "palette": ["#hex", "..."],
  "composition": "...",
  "lighting": "...",
  "subject": "...",
  "mood": "...",
  "aesthetic_type": "fashion|portrait|lifestyle|product|cinematic|architectural|atmospheric|typography|poster|illustration|stylized|brand_palette",
  "search_query": "concise 4–8 word Pinterest query"
}
```

Save to `output/prompts/fingerprint.json`. The orchestrator validates the shape before continuing.

### Stage 3 — Prompt extraction (vision pass)

Per pin under `output/pinterest/<slug>/`, reverse-engineer a prompt that includes: subject + action + setting, lighting style, lens / camera spec, film stock or grade, photographer or aesthetic reference, composition note. Score 0–1 against the fingerprint and append to `extracted_prompts.jsonl`. Top 5 by score advance.

### Stage 5 — Storyboard

Default 10s = 2 × 5s shots. `--duration 30` = 6 × 5s. Each beat picks a still from Stage 4 and a camera-move prompt (e.g. *slow push-in*, *parallax dolly*).

### Stage 6 — Image-to-video

One Kling 2.1 Pro I2V call per shot, 5s ceiling enforced. Drift past 8s is the documented failure mode for label-bearing video — always stitch in post.

### Stage 7 — Stitch

`ffmpeg` concat → overlay first `.mp3` from `assets/audio/` → optional text overlays. Silent ad if the audio directory is empty.

## Model routing — May 2026, middle-cost tier

Live as of 2026-05-04 (see design doc for sourcing).

| Lane | Model | Why |
|---|---|---|
| Hero / multi-ref product | `google/nano-banana-pro` | 2026 SOTA product fidelity, up to 14 reference images |
| Scene variations | `black-forest-labs/flux/kontext` | Subject-locked instruction edits; cheaper for high volume |
| Insurance inpaint | `higgsfield-ai/soul/inpaint` | Mask + paste-back; zero label drift |
| I2V (10s clips) | `kling-video/v2.1/pro/image-to-video` | Best label readability in mid-tier video |

Aesthetic-type fallback table (`scripts/models.py`, used when MCP discovery is unavailable):

| aesthetic_type | model_id |
|---|---|
| fashion / portrait / lifestyle / product (default) | `google/nano-banana-pro` |
| cinematic / architectural / atmospheric | `black-forest-labs/flux-2` |
| typography / poster | `openai/gpt-image` |
| illustration / stylized | `bytedance/seedream/v5/lite` |
| brand_palette | `higgsfield-ai/soul/hex` |

Slug fixes vs. v1: `bytedance/seedream-5` → `bytedance/seedream/v5/lite`; `openai/gpt-image-2` → `openai/gpt-image`. If a 404 returns from the platform, update `scripts/models.py` and rerun the affected stage with `--skip-stages`.

## Cost ceiling per full run

| Item | Quantity | Unit | Subtotal |
|---|---|---|---|
| Stage 4 stills | 10 | 2 cr | 20 cr |
| Stage 6 video clips (10s default) | 2 × 5s | 7 cr | 14 cr |
| **Total** | | | **~34 cr ≈ $3–6** |

30s configuration ≈ 62 cr ≈ $5–10. Cost ledger written into `run_summary.md`.

## Failure modes (and the actual fix)

- **Pinterest CAPTCHA on first run.** Solve it manually in the visible browser; the session is cached in `.playwright-state/`. Subsequent runs are headless-friendly.
- **`HF_KEY` not set.** SDK fails fast. `HF_KEY` is `key:secret` joined with a colon, or set `HF_API_KEY` + `HF_API_SECRET` separately.
- **MCP not authenticated.** SDK fallback activates automatically via `scripts/lib/mcp_client.py`. Restart the Claude Code session after running `/mcp` to enable the MCP path.
- **Generations look generic.** Reference images are too low-res (<1024px) → vision can't extract specifics. Replace refs first; do not paper over with prompt engineering.
- **Wrong house aesthetic on outputs.** Routed to the wrong model. Edit `LANE_TO_MODEL` / `AESTHETIC_TO_MODEL` in `scripts/models.py` and rerun Stage 4 only with `--skip-stages 1,2,3`.
- **Label drift in video.** 5s clip ceiling is enforced; concat in Stage 7. If still drifting, regenerate the underlying still via the `soul/inpaint` insurance lane and re-run Stage 6.
- **Slug 404 from platform.** Update the slug in `scripts/models.py`; orchestrator resumes from the failed stage on rerun.

---

Refreshed 2026-05-04 — see docs/superpowers/specs/2026-05-04-aesthetic-automation-v2-design.md for the full design.
