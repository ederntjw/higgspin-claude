# Hero product photo — drop-in instructions

Drop a single hero shot of your product into this folder and the pipeline
will lock its geometry and label across every generated scene.

## Required filename

One of:

- `hero.png`
- `hero.jpg`
- `hero.webp`

The pipeline scans this directory for any of those exact names. First match wins.

## Recommendations

- **Resolution:** at least **1500px** on the longest edge. Higher is better.
- **Background:** plain white or transparent. The pipeline preserves the
  product, not the background — anything behind it gets discarded.
- **Focus + lighting:** sharp focus, even lighting, single hero angle.
  Soft shadows are fine; harsh hotspots will bleed into the generations.

## Product-lock detection

| Folder state | Pipeline mode |
| --- | --- |
| `hero.{png,jpg,webp}` is present | **product-lock** — geometry + label preserved across all generations |
| No `hero.*` file | **placeholder** — moodboard-only scenes; composite the product yourself afterwards |

Override the auto-detection from the orchestrator:

```bash
python scripts/orchestrate.py --product-lock on    # force product-lock
python scripts/orchestrate.py --product-lock off   # force placeholder
python scripts/orchestrate.py --product-lock auto  # default — detect from folder
```

## How the lock is enforced

The first generation pass uses **Google Nano-Banana-Pro** (May 2026 SOTA for
product fidelity). If label text drifts on inspection, the pipeline
auto-falls-back in this order:

1. **Nano-Banana-Pro** — primary pass.
2. **Flux Kontext** — second pass, structure-aware reference conditioning.
3. **Soul Inpaint** — final pass with a masked paste-back of the original
   product pixels over the generated scene.

You don't need to choose — the orchestrator escalates automatically when QA
flags a drifted label.

## Common pitfalls

- **Photos under 1024px.** Vision model can't read fine label detail and
  you'll get garbled type on every output. Refresh the reference first;
  prompt engineering can't recover lost pixels.
- **Reflective products** (chrome, glass, polished bottles). The single
  hero angle isn't enough — provide two angles as `hero.png` and
  `hero_b.png` and the pipeline will rotate between them per scene.
- **Multi-product packs.** The lock targets exactly one product at a time.
  Break a pack into separate runs (one hero per run) and composite the
  collection downstream.
