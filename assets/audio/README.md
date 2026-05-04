# Background music — bundled royalty-free tracks

This directory holds the soundtrack used by the final video stitch step.

`stitch_video.py` auto-picks the **first `.mp3` it finds in this directory**
(alphabetical order). If the directory contains no `.mp3` files, the ad is
rendered **silent** — no error, just no audio track.

## Recommended Pixabay tracks (May 2026)

All three are free under the [Pixabay Content License](https://pixabay.com/service/license-summary/)
— **free for commercial use, no attribution required**. The links below are
search URLs; pick whichever specific track on the result page matches your
moodboard best, then download the `.mp3`.

| Track name | Mood | Good fit for | Download (search) |
|---|---|---|---|
| Inspiring Cinematic Ambient | calm, contemplative, slow build | cinematic / architectural / atmospheric | <https://pixabay.com/music/search/cinematic-ambient/> |
| Upbeat Corporate Lo-Fi | warm, optimistic, mid-tempo groove | fashion / portrait / lifestyle / product | <https://pixabay.com/music/search/corporate-lofi/> |
| Atmospheric Synth Pad | dreamy, washed-out, dark-romantic | stylized / illustration / brand_palette | <https://pixabay.com/music/search/atmospheric-synth-pad/> |

## Licence

Pixabay Content License — **free for commercial use, no attribution required**
as of May 2026. Full terms: <https://pixabay.com/service/license-summary/>.

Always re-confirm the licence on each individual track's Pixabay page before
shipping a paid client deliverable — Pixabay occasionally re-tags older
uploads.

## Drop-in instructions

1. Pick a track from one of the searches above (or anywhere — any
   royalty-free `.mp3` works).
2. Save it into this directory:

   ```bash
   mv ~/Downloads/your-track.mp3 assets/audio/track.mp3
   ```

   The filename does not matter — `stitch_video.py` takes the first `.mp3`
   it finds. Keeping a single file here is the simplest setup.

3. To override for a single run without moving files, set the
   `AESTHETIC_AUDIO` env var to an absolute (or repo-relative) path. The
   orchestrator respects it and skips the auto-pick:

   ```bash
   AESTHETIC_AUDIO=assets/audio/cinematic-build.mp3 \
     python scripts/stitch_video.py ...
   ```

4. To render a deliberately silent ad, just empty this directory:

   ```bash
   rm assets/audio/*.mp3
   ```

## Notes

- Keep tracks under ~3 minutes; the stitcher loops/truncates to match the
  video duration.
- 44.1 kHz stereo `.mp3` at 192 kbps or higher is the sweet spot — smaller
  files cause audible artefacts after re-encoding into the final `.mp4`.
- Do **not** commit large `.mp3` files to git. Add `assets/audio/*.mp3` to
  `.gitignore` if you haven't already.
