# higgspin-claude

> Pinterest moodboard → on-brand AI stills → 10s short-form ad. Driven from a single Claude Code prompt, with your real product locked in across every frame.

This is a small, opinionated pipeline that turns reference images into a finished vertical ad. It uses [Higgsfield AI](https://higgsfield.ai) for image and video generation (with a three-tier fallback: MCP → SDK → raw HTTP), and Claude Code for the vision and orchestration parts. Models are chosen for the **middle-cost tier** as of **May 2026** — not the cheapest, not the flagship.

## What you get

For every run:

- A **visual fingerprint** of your moodboard (palette, mood, aesthetic type, search query)
- 40 fresh Pinterest pins matching the vibe
- 10 generated stills that follow the fingerprint and (optionally) **lock your real product** across all of them
- A 2-shot **10-second vertical ad** stitched from those stills with background music
- A run summary with cost ledger and links to every artifact

Default budget per run: about 34 Higgsfield credits (~$3–6 on the mid plan). Configurable.

## Pick your mode

| Mode | When | What happens |
|---|---|---|
| **Placeholder** | You don't have a hero product photo yet | Pipeline produces editorial moodboard scenes for you to composite a product into later |
| **Product-lock** | Drop a clean photo at `references/product/hero.png` | Pipeline preserves the product's geometry, label, and brand marks across all 10 stills and into the video |

Switching is automatic. Override with `--product-lock=on|off|auto`.

---

## Prerequisites

| Tool | Why | Install |
|---|---|---|
| Python ≥ 3.9 | Pipeline is pure Python | system or `pyenv` |
| `ffmpeg` | Stitches the final ad | `brew install ffmpeg` (macOS), `apt install ffmpeg` (Debian/Ubuntu) |
| [Claude Code](https://claude.com/claude-code) CLI | Runs the orchestration prompt + does the vision passes | follow the install docs |
| A [Higgsfield](https://cloud.higgsfield.ai) account | Image + video generation | get an API key from `Settings → API Keys` (mid plan recommended) |
| A Pinterest account | Scraping reference pins | any account; first scrape may need a manual CAPTCHA solve |

Optional but recommended:

- The official **Higgsfield MCP** — registered automatically by the setup steps below; gives Claude Code a faster, native call surface.

---

## One-time setup

```bash
git clone <this-repo> higgspin-claude
cd higgspin-claude

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium     # add --with-deps on Apple Silicon

cp .env.example .env            # then fill in HF_KEY + Pinterest creds
```

`.env` keys:

```ini
# Higgsfield: combined "key:secret" OR set the two halves separately
HF_KEY=your_key:your_secret

# Pinterest: used by the scraper
PINTEREST_EMAIL=you@example.com
PINTEREST_PASSWORD=your_password
```

Register the Higgsfield MCP in Claude Code (one-time, project-scoped):

```bash
claude mcp add --transport http higgsfield https://mcp.higgsfield.ai/mcp
```

Then in an interactive Claude Code session, run `/mcp` and authorize. After authorization, restart the session so the MCP tools register. **If you skip this, the pipeline still works** — it falls back to the `higgsfield-client` Python SDK automatically.

---

## Drop in your moodboard (and your product)

```
references/
├── images/                # 5–10 Pinterest pins, ≥1024px, JPG/PNG/WEBP
└── product/
    └── hero.png           # optional — your actual product, transparent or white BG
```

Tips:

- Moodboard refs **must be ≥1024px** on the long edge or the vision model can't extract specifics. This is the #1 cause of generic-looking output.
- For product-lock mode, hero.png should be a **single clean angle**, sharp focus, even lighting. Reflective products (chrome/glass) benefit from two angles (`hero.png` + `hero_b.png`).

---

## Run it

The whole pipeline is one command, but two of the eight stages need Claude Code to do the vision pass for you. The orchestrator pauses at those points and tells you exactly what to run.

### Path A — interactive Claude Code (recommended)

Open this directory in Claude Code and paste the master prompt from [CLAUDE.md](./CLAUDE.md). Claude will do the vision passes inline, then run the orchestrator for everything else. End-to-end in one shot.

### Path B — manual orchestration

```bash
# Stage 1: Claude vision over references/images/ → output/prompts/fingerprint.json
#   (run this inside Claude Code: see CLAUDE.md Stage 1)

# Stage 2 onward — run the orchestrator
python scripts/orchestrate.py --duration 10
```

Stage 3 also pauses for a Claude vision pass to extract per-pin prompts. The orchestrator prints what to do.

### Common flags

```bash
# Different ad lengths
python scripts/orchestrate.py --duration 10        # 2 × 5s clips (default)
python scripts/orchestrate.py --duration 30        # 6 × 5s clips
python scripts/orchestrate.py --duration 15 --clip 5

# Force product-lock (or off)
python scripts/orchestrate.py --product-lock on
python scripts/orchestrate.py --product-lock off

# Skip stages (e.g. only re-do video if stills are good)
python scripts/orchestrate.py --skip-stages 1,2,3,4

# Dry run — print what would happen without burning a single credit
python scripts/orchestrate.py --dry-run

# Override search query (otherwise uses fingerprint.json's search_query)
python scripts/orchestrate.py --query "minimal scandinavian skincare"

# Generate more or fewer images
python scripts/orchestrate.py --n-images 6        # 3 prompts × 2 variants
```

---

## What happens, stage by stage

| # | Stage | Tool | Output |
|---|---|---|---|
| 1 | Visual fingerprint | Claude vision | `output/prompts/fingerprint.json` |
| 2 | Pinterest scrape | Playwright (`pinterest_scrape.py`) | `output/pinterest/<slug>/` |
| 3 | Per-pin prompt extraction | Claude vision | `output/prompts/extracted_prompts.jsonl` |
| 4 | Image generation (product-lock or moodboard-only) | Higgsfield via MCP/SDK | `output/generated/*.png` + JSON sidecars |
| 5 | Storyboard (10s → 2 × 5s shots) | local Python | `output/prompts/storyboard.json` |
| 6 | Image-to-video clips | Higgsfield via MCP/SDK | `output/ad/clips/shot_*.mp4` |
| 7 | Stitch + audio + (optional) text overlays | `ffmpeg` | `output/ad/final.mp4` |
| 8 | Run report | local Python | `output/prompts/run_summary.md` |

Each stage writes its artifacts to disk before exiting, so you can resume from any stage with `--skip-stages`.

---

## Models used (May 2026, middle-cost tier)

| Lane | Model slug | Cost (Higgsfield credits) | Why this one |
|---|---|---|---|
| Hero shot, multi-ref | `google/nano-banana-pro` | 2 cr / 2K image | 2026 SOTA for product photography; up to 14 reference images |
| Scene variations (subject lock) | `black-forest-labs/flux/kontext` | 1.5 cr | Subject-preserving instruction edits |
| Insurance (label drift) | `higgsfield-ai/soul/inpaint` | 0.25 cr | Mask the product, regenerate only the background |
| Image-to-video (default) | `kling-video/v2.1/pro/image-to-video` | ~7 cr / 5s | Best label readability among mid-tier video models |
| Image-to-video (product-lock) | `bytedance/seedance/v2/fast` | ~8.5 cr / 5s | Best product/logo consistency in 2026 video models |

The cascade is automatic: a 4xx from the primary model falls through to the next tier, and you can see exactly which slug each call hit in the JSON sidecar next to every output.

---

## Cost expectations

For the default 10-second run, with product-lock on:

| Item | Quantity | Subtotal |
|---|---|---|
| Stage 4 hero+variant images | 10 × 2 cr | 20 cr |
| Stage 6 video clips | 2 × 7–8.5 cr | 14–17 cr |
| **Total** | | **~34–37 cr ≈ $3–6** |

For 30-second config: about 62–70 credits ≈ $5–10. The full ledger is in `output/prompts/run_summary.md` after every run.

---

## Customizing

### Use a different aesthetic

Edit `output/prompts/fingerprint.json` after Stage 1 — change `aesthetic_type` to one of: `fashion`, `portrait`, `lifestyle`, `product`, `cinematic`, `architectural`, `atmospheric`, `typography`, `poster`, `illustration`, `stylized`, `brand_palette`. The model routing in `scripts/models.py` will pick the right Higgsfield model for that look.

### Swap models

Edit `scripts/models.py` — `LANE_TO_MODEL` and `LANE_CASCADE` are short, plain-Python dictionaries. Slug syntax matches Higgsfield's `{vendor}/{model}/{variant}` convention.

### Pick your music

Drop any `.mp3` into `assets/audio/` — the stitcher picks the first one alphabetically. Recommended Pixabay royalty-free tracks are listed in `assets/audio/README.md`. Empty directory → silent ad.

### Add text overlays

Pass JSON-shaped overlay specs to `scripts/stitch_video.py` directly (the orchestrator does not yet wire this up — it's a one-line addition if you want it):

```bash
python scripts/stitch_video.py \
  --clips output/ad/clips/shot_1.mp4,output/ad/clips/shot_2.mp4 \
  --audio assets/audio/track.mp3 \
  --out output/ad/final.mp4 \
  --overlay '{"text":"Available now","start_s":7,"duration_s":3,"position":"bottom"}'
```

---

## Failure modes (and the actual fix)

- **Pinterest CAPTCHA on first run.** Solve it once in the visible browser; the session caches in `.playwright-state/` for next time.
- **`HF_KEY` not set.** SDK fails fast. Set it in `.env` as `key:secret` joined with a colon, or split into `HF_API_KEY` + `HF_API_SECRET`.
- **MCP not authenticated.** The pipeline's three-tier wrapper falls back to the SDK transparently. To enable the MCP path, run `/mcp` in Claude Code, authorize, then restart your session.
- **Generations look generic.** Your reference images are too low-res (<1024px). Replace them — no amount of prompt engineering downstream can recover detail that wasn't in the references.
- **Wrong house aesthetic.** You're routed to the wrong model. Edit the `AESTHETIC_TO_MODEL` table in `scripts/models.py` and rerun stage 4 only.
- **Label drifts in video.** That's why the product-lock cascade leads with Seedance v2/fast. If it still drifts, edit the storyboard to keep clips ≤4s — drift correlates with shot length above 5s.
- **`ffmpeg: command not found`.** Install ffmpeg via your package manager.

---

## Architecture (one-screen overview)

```
┌─ references/{images, product}     ← you drop files here
│
├─ scripts/
│   ├─ orchestrate.py               ← single-entry runner (8 stages)
│   ├─ fingerprint.py               ← Stage 1 schema validator
│   ├─ pinterest_scrape.py          ← Stage 2 (Playwright)
│   ├─ extract_prompts.py           ← Stage 3 reader/writer
│   ├─ generate_image.py            ← Stage 4 (product-lock aware, 3-tier cascade)
│   ├─ storyboard.py                ← Stage 5 (Seedance 6-step formula)
│   ├─ generate_video.py            ← Stage 6 (Kling / Seedance / DoP cascade)
│   ├─ stitch_video.py              ← Stage 7 (ffmpeg)
│   ├─ models.py                    ← May 2026 routing tables
│   └─ lib/
│       ├─ mcp_client.py            ← MCP → SDK → HTTP cascade
│       └─ cost_tracker.py          ← per-call credit ledger
│
├─ output/
│   ├─ prompts/                     ← fingerprint, JSONL, storyboard, summary
│   ├─ pinterest/<slug>/            ← scraped pins
│   ├─ generated/                   ← stills + sidecars
│   └─ ad/{clips,final.mp4}         ← video clips + final cut
│
├─ assets/audio/                    ← bundled royalty-free music
├─ tests/                           ← unit + dry-run tests
├─ docs/superpowers/specs/          ← design doc
├─ CLAUDE.md                        ← Claude Code's master orchestration prompt
└─ README.md                        ← this file
```

The pipeline is deliberately **flat and inspectable**: every stage is one Python file under 200 lines, every output has a JSON sidecar with exactly which model slug produced it and how many credits it cost.

---

## Tests

```bash
python -m unittest discover tests
```

Two test files run instantly without burning any credits:

- `tests/test_models.py` — verifies the routing tables produce expected slugs.
- `tests/test_dry_run.py` — runs `orchestrate.py --dry-run` and asserts all 8 stages are reached and the right model slugs would be called.

---

## Contributing

Please open issues for:

- Higgsfield slug changes (this repo is pinned to May 2026 — slugs drift)
- New aesthetic categories you'd like routed
- Reproducible quality regressions (with a small set of references that exhibit the problem)

PRs welcome. Keep new modules under 200 lines and write a test in `tests/`.

---

## License

MIT. The Pinterest scraper is for personal/research use — respect Pinterest's ToS in your jurisdiction.

---

## Credits

- Models: [Higgsfield AI](https://higgsfield.ai), [Google Nano-Banana-Pro](https://blog.google/innovation-and-ai/products/nano-banana-pro/), [Black Forest Labs Flux.2](https://docs.bfl.ai/), [ByteDance Seedance 2.0](https://seed.bytedance.com/), [Kling AI](https://klingai.com/).
- Prompting: heavily informed by the [Seedance 2.0 Complete Prompting Guide](https://github.com/issastash/AI_Complete_Prompting_Guides/blob/main/Seedance_2.0_Complete_Prompting_Guide.md) — the 6-step camera-prompt formula, lighting-as-leverage, and standard negatives all come from there.
- Orchestration: [Claude Code](https://claude.com/claude-code).

Refreshed 2026-05-04. Full design lives at [`docs/superpowers/specs/2026-05-04-aesthetic-automation-v2-design.md`](./docs/superpowers/specs/2026-05-04-aesthetic-automation-v2-design.md).
