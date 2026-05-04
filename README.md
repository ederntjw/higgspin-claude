# higgspin-claude

> Turn a few inspiration images into a finished 10-second vertical ad — without ever opening Photoshop, Premiere, or an AI tool you've never used before.

## What this actually does (in plain English)

You hand over:
- 5–10 images that capture the *vibe* you want (Pinterest pins, Instagram screenshots, photos you've taken — anything).
- *(Optional)* A clean photo of the product you're advertising.

The project does this on your behalf:
1. **Looks at your inspiration images** and figures out the visual style — palette, mood, lighting, the kind of photography you're after.
2. **Searches Pinterest** for 40 more images in that same style, so we have lots to draw from.
3. **Generates 10 brand-new images** in that style using AI. If you gave it a product photo, it keeps your product visible and unchanged in every single one.
4. **Stitches those images into a 10-second vertical ad** with background music, ready to post on TikTok, Reels, or Shorts.

You stay in the loop — Claude (the AI assistant that runs this) walks you through it conversationally, asks you what you're advertising, what feeling you want, checks your setup, and explains what every step does before doing it.

**Cost:** uses Higgsfield credits — the exact amount depends on which models the cascade picks for your moodboard. Check your Higgsfield billing dashboard for live usage. **Time:** about 10–15 minutes from clean clone to finished video.

**Who this is for:** founders, creators, agency people, hobbyists. You don't need to know what an "I2V model" is. You don't need to write prompts. You don't need to use Adobe anything.

## Two modes

| Mode | When | What happens |
|---|---|---|
| **Placeholder** | You don't have a product photo yet | Pipeline produces editorial scenes that match your moodboard. You composite a real product in later if you want. |
| **Product-lock** | You drop a clean photo at `references/product/hero.png` | Pipeline preserves the product's exact geometry, label, and branding across all 10 stills and into the video. No hallucinated bottles, no rewritten labels. |

The mode switches automatically based on whether the file is there.

---

## Getting started — the actual experience

Here's what your first run looks like end-to-end.

### Step 1 — Get the code on your machine

```bash
git clone https://github.com/ederntjw/higgspin-claude
cd higgspin-claude
```

### Step 2 — Run setup once

```bash
./setup.sh
```

This installs the Python libraries the project uses (in a folder called `.venv` so nothing on your computer outside this project is touched), downloads a small browser tool we need (Playwright Chromium), and copies a template for your credentials file.

You'll also need `ffmpeg` — the standard tool for combining video clips and audio. The setup script prints a warning if it's missing:

- macOS: `brew install ffmpeg`
- Linux: `sudo apt install ffmpeg`

### Step 3 — Get your accounts

You need two free signups before the pipeline can work:

1. **[Higgsfield](https://cloud.higgsfield.ai)** — this is the AI service that actually generates the images and video. It runs on a credit-based plan; check your dashboard at https://cloud.higgsfield.ai/billing for live usage. Sign up first.
2. **[Pinterest](https://pinterest.com)** — we use Pinterest as a fresh visual source. The pipeline searches Pinterest for 40 images that match your moodboard's vibe, so we have lots to draw from. Pinterest doesn't have a public API for visual search, so we use a real browser (Playwright) to log in as you and pull the search results. Your password stays on your computer; it never leaves.

Open `.env` (it was just created in step 2) and paste in your Pinterest email and Pinterest password. There are comments in the file showing the format.

### Step 4 — Open the folder in Claude Code, register the Higgsfield MCP

Install [Claude Code](https://claude.com/claude-code) if you don't have it, then open this folder in it. Once inside, register and authorise the Higgsfield MCP — this is the recommended path because it means **you don't need to put a Higgsfield API key in `.env` at all**:

```bash
claude mcp add --transport http higgsfield https://mcp.higgsfield.ai/mcp
```

Then type `/mcp` in the Claude Code session and complete the OAuth flow that pops up. Restart the session once so the MCP tools register.

> **Tip:** if you'd rather use the Python SDK fallback (or run outside Claude Code entirely), you instead need to put `HF_KEY=key:secret` into `.env` — get the value from Higgsfield Settings → API Keys. You only need *one* of the two — MCP **or** API key — not both.

### Step 5 — Tell Claude what you're making

Just type something like:

> *"I want to make an ad for my new sparkling water brand"*
>
> or
>
> *"help me get started"*
>
> or
>
> *"first time here, how does this work?"*

Claude reads `CLAUDE.md` (the instructions file in this repo) and walks you through the rest as a conversation:

1. It asks what you're selling, who the audience is, and what feeling you want.
2. It tells you to drop 5–10 inspiration images into `references/images/`.
3. It asks if you have a clean product photo (optional but recommended).
4. It checks your setup is complete and explains anything that's missing.
5. It runs the whole 8-stage pipeline and shows progress at each step.
6. When it's done, your ad is at `output/ad/final.mp4` and the cost breakdown is at `output/prompts/run_summary.md`.

You never write a prompt yourself, never pick a model, never call an API. Claude does all of that based on your visual references.

---

## Power-user mode

If you've used this before and just want to run it directly:

```bash
python scripts/orchestrate.py
```

Stages 1 and 3 (vision passes) need an LLM with vision; the easiest path is still to run from inside Claude Code. Without Claude Code, you can populate `output/prompts/fingerprint.json` and `output/prompts/extracted_prompts.jsonl` yourself (see [docs/superpowers/specs/](./docs/superpowers/specs/) for the schemas) and the orchestrator will use them.

---

## Without Claude Code (advanced)

The pipeline can run from a regular shell, but Stages 1 and 3 need vision over images. You'll need the Anthropic API directly. Drop in your `ANTHROPIC_API_KEY`, write a small script that produces `output/prompts/fingerprint.json` and `output/prompts/extracted_prompts.jsonl`, then run:

```bash
python scripts/orchestrate.py --duration 10
```

The orchestrator pauses if either artifact is missing and prints exactly what is expected.

---

## Common flags

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

## Optional: Higgsfield MCP

Faster than the SDK. Register once:

```bash
claude mcp add --transport http higgsfield https://mcp.higgsfield.ai/mcp
```

Then `/mcp` in Claude Code and authorize. **If you skip this, the pipeline still works** — it falls back to the `higgsfield-client` Python SDK automatically.

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

| Lane | Model slug | Why this one |
|---|---|---|
| Hero shot, multi-ref | `google/nano-banana-pro` | 2026 SOTA for product photography; up to 14 reference images |
| Scene variations (subject lock) | `black-forest-labs/flux/kontext` | Subject-preserving instruction edits |
| Insurance (label drift) | `higgsfield-ai/soul/inpaint` | Mask the product, regenerate only the background |
| Image-to-video (default) | `kling-video/v2.1/pro/image-to-video` | Best label readability among mid-tier video models |
| Image-to-video (product-lock) | `bytedance/seedance/v2/fast` | Best product/logo consistency in 2026 video models |

The cascade is automatic: a 4xx from the primary model falls through to the next tier, and you can see exactly which slug each call hit in the JSON sidecar next to every output.

For exact credit costs and live usage, see your Higgsfield billing dashboard at <https://cloud.higgsfield.ai/billing>. The Higgsfield MCP and SDK do not currently return per-call credit cost in the response payload, so the pipeline can show you *which model ran* but not *what it cost* — only Higgsfield can.

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
