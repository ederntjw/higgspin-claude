# Aesthetic Automation v2 — Product-Locked Pipeline + Short-Form Ad

Pinterest moodboard → extracted prompts → Higgsfield stills → Kling I2V clips → stitched short-form ad. One CLI entry point; the two vision passes (Stages 1 + 3) are done by Claude Code automatically when an operator runs the pipeline from inside it.

---

## How to onboard a user (READ THIS FIRST)

**Assume the user has never touched AI video generation before.** They might not know what a `.env` file is, why we use Pinterest, what Playwright does, or what an "I2V model" is. Your job is to walk them through it like a patient friend, not to dump commands.

### When to run the guided flow vs. just execute

- **Guided flow** — when ANY of these are true: `references/images/` is empty, `.env` has placeholder values, `output/prompts/fingerprint.json` doesn't exist, or the user says anything like "how do I use this", "I want to make an ad", "help me get started", "first time".
- **Just execute** — when the user has clearly run this before and says something direct like "run a 30s version", "redo the video", "skip to stage 6". Then don't re-onboard, just run.

If unsure, default to the guided flow. A wasted question is cheaper than a wasted API call on misaligned references.

### The guided flow — phases 0 → 5

Run them in order. After each user response, save the relevant intent to memory so you can refer back to it later in the same session.

#### Phase 0 — Welcome and discovery

Open with something like:

> "Welcome! I help turn your visual taste into a finished short-form ad. Before we touch any code, I want to understand what you're making.
>
> A few quick questions:
> 1. What are you advertising? (a product, a brand, an experience, something else?)
> 2. Who's the audience?
> 3. What feeling should the ad give? (e.g. clean and minimal, dreamy and cinematic, bold and colourful)
>
> Just write a couple of sentences — no need to be precise."

Wait for the answer. **Do not move on until they reply.** Acknowledge what they said briefly so they feel heard.

#### Phase 1 — Inspiration images

> "Now I need a moodboard — 5 to 10 images that capture the visual feeling you want. These don't need to be perfect or related to your actual product — they just need to convey the *vibe*.
>
> Where to find them:
> - Pinterest, Instagram screenshots, ads you love, photos you took, frames from films you like.
> - Each image should be at least 1024 pixels on the long edge (anything from a recent phone is fine).
>
> Drop them into `references/images/` in this folder. When you're done, just say 'done' and I'll continue."

Wait for confirmation. After they confirm, run `ls references/images/` to verify there are images present. If the directory is still empty, gently re-prompt.

#### Phase 2 — Optional product photo

> "Quick optional step that makes a huge difference: do you have a clean photo of the actual product you're selling?
>
> If yes — drop it at `references/product/hero.png`. I'll lock that exact product into every generated image and video frame, so the AI doesn't invent a fake bottle or rewrite your label. White or transparent background works best. Sharp focus, even lighting.
>
> If no — that's fine. I'll generate editorial scenes that match your moodboard, and you can composite the real product in later using Photoshop or Canva.
>
> Tell me 'yes I added it' or 'skip'."

#### Phase 3 — Setup check (only if needed)

Run a quick check to verify the environment. **Don't lecture** — only mention the pieces that aren't installed.

```bash
# Check .env has real values
grep -q "your_higgsfield_key" .env 2>/dev/null && echo "ENV_PLACEHOLDER"
# Check ffmpeg exists
command -v ffmpeg >/dev/null && echo "FFMPEG_OK" || echo "FFMPEG_MISSING"
# Check venv exists
[ -d .venv ] && echo "VENV_OK" || echo "VENV_MISSING"
```

For each missing piece, explain plainly what it is and why it's needed:

- **`./setup.sh` not yet run / `.venv` missing** —
  > "I need to install the Python libraries this project uses. They get installed in a folder called `.venv` inside this project, kept separate from the rest of your computer so nothing else gets affected. Run this in your terminal: `./setup.sh`"

- **`ffmpeg` missing** —
  > "We need `ffmpeg` — it's the standard tool for combining video clips and audio. The AI services give us individual 5-second clips; ffmpeg stitches them together with music into your final ad. Install with: `brew install ffmpeg` (Mac) or `sudo apt install ffmpeg` (Linux)."

- **Higgsfield auth not set up** — the user has two paths; pick ONE:
  > "Higgsfield is the AI service that actually generates your images and video. You only need ONE of the two paths below — not both:
  >
  > **Path A (recommended, no API key needed)** — register the Higgsfield MCP in Claude Code:
  > ```bash
  > claude mcp add --transport http higgsfield https://mcp.higgsfield.ai/mcp
  > ```
  > then run `/mcp` here and complete the OAuth pop-up, then restart this session. That's it — no values in `.env` for Higgsfield.
  >
  > **Path B (fallback, needs an API key)** — sign up at https://cloud.higgsfield.ai, go to Settings → API Keys, copy the key (format: `key:secret`), and paste it after `HF_KEY=` in `.env`. Use this if you don't want the MCP, or if you want to run the pipeline outside Claude Code.
  >
  > Either way, check live usage at https://higgsfield.ai (sign in and open your account profile)."

- **`.env` Pinterest values are placeholders** —
  > "Pinterest login — we use Pinterest as a fresh visual source. Based on the moodboard you gave me, I'll search Pinterest for 40 more matching images so we have lots of variety to draw from. Pinterest doesn't have a public API for visual search, so we use a real browser (a tool called Playwright) to log in as you and scrape the search results. Your credentials stay on your machine — they never leave it. Paste your email and password into `PINTEREST_EMAIL=` and `PINTEREST_PASSWORD=` in `.env`."

After they confirm setup is done, verify by re-running the check.

#### Phase 4 — Confirm before spending money

Before running anything that costs credits, summarise back:

> "Here's the plan:
> - Topic: [what they told me in Phase 0]
> - Moodboard: [N] images
> - Product-lock: [on / off based on Phase 2]
> - Output: a 10-second vertical ad at `output/ad/final.mp4`
> - This will use Higgsfield credits — see your dashboard at https://higgsfield.ai (sign in and open your account profile) for live usage.
>
> Ready to run? (yes / no / change something)"

Only proceed on a clear yes.

#### Phase 5 — Run the pipeline

Now run the work. Talk through each stage as it happens — short status lines, not silence.

1. **Stage 1 — fingerprint.** Read every image in `references/images/` with vision. Produce a JSON object with palette, mood, lighting, aesthetic_type, and a 4–8 word Pinterest search query. Save to `output/prompts/fingerprint.json`. Show the result to the user.
2. **Stage 2 — Pinterest scrape.** Run `python scripts/orchestrate.py --skip-stages 1,3,4,5,6,7,8` to scrape 40 fresh pins matching the search query. Mention that the first scrape may pop a CAPTCHA in a visible browser — they solve it once, the session caches.
3. **Stage 3 — score and pick prompts.** For each scraped pin, vision-read it and write a detailed prompt that includes lighting, lens spec, film stock, photographer reference, composition. Score 0–1 against the fingerprint. Append to `output/prompts/extracted_prompts.jsonl`. Top 5 by score advance.
4. **Stages 4–8 — generate, storyboard, video, stitch, report.** Run `python scripts/orchestrate.py --skip-stages 1,2,3` (or skip more if applicable). Stream the output. When it's done, show them where the final ad lives and link to the cost ledger.

After completion, ask:

> "Done. Final ad: `output/ad/final.mp4` (open it). Want me to make any tweaks — different length, swap a still, different music?"

### Examples of direct execute (no onboarding)

If the user has clearly used the pipeline before and says any of these, skip the guided flow and just run:

- *"run a 30-second version"* → `python scripts/orchestrate.py --duration 30`
- *"only redo the video"* → `python scripts/orchestrate.py --skip-stages 1,2,3,4`
- *"dry run"* → `python scripts/orchestrate.py --dry-run`
- *"why did stage 6 fail"* → read `output/prompts/run_summary.md` and explain.

---

## One-time setup (manual equivalent of `./setup.sh`)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium    # add --with-deps on Apple Silicon
brew install ffmpeg            # required for Stage 7 stitch
cp .env.example .env           # fill in Pinterest creds; Higgsfield auth handled below
```

**Higgsfield auth — pick ONE path:**

- **MCP (recommended for Claude Code users)** — register and authorise once, no API key in `.env` needed:
  ```bash
  claude mcp add --transport http higgsfield https://mcp.higgsfield.ai/mcp
  # then `/mcp` and OAuth, then restart the Claude Code session
  ```
- **API key (fallback / for non-Claude-Code users)** — set `HF_KEY=key:secret` in `.env` (get from https://cloud.higgsfield.ai → Settings → API Keys).

If both are present, the MCP is preferred and the SDK is the automatic fallback.

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

## Tracking what a run costs

The Higgsfield MCP and SDK do not currently return a per-call credit cost in the response, so the pipeline cannot tell the user exactly what a run consumed. Instead:

- Each generation writes a JSON sidecar with `model_id` so you know which slug was used.
- After a run, `output/prompts/run_summary.md` lists every call by model.
- For the actual credit usage, point users at their Higgsfield billing dashboard: <https://higgsfield.ai (sign in and open your account profile)>.

Do not surface dollar estimates — they are speculation.

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
