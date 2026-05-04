"""Stitch generated clips into a final 9:16 ad with optional audio + text overlays.

Three-pass ffmpeg pipeline:
  1) lossless concat of clips via the concat demuxer
  2) optional audio mux (-shortest, trims music to video length)
  3) optional drawtext burn-ins, timed via enable='between(t,...)'
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

_HELVETICA = "/System/Library/Fonts/Helvetica.ttc"
_FALLBACK_FONT = "Arial"


def _font() -> str:
    return _HELVETICA if os.path.exists(_HELVETICA) else _FALLBACK_FONT


def _require_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "ffmpeg not found on PATH. Install ffmpeg (e.g. `brew install ffmpeg`) and retry."
        )


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed (exit {proc.returncode})\n"
            f"cmd: {' '.join(cmd)}\n"
            f"stderr:\n{proc.stderr}"
        )


def _escape_drawtext(text: str) -> str:
    # ffmpeg drawtext requires escaping these chars
    return (
        text.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace("%", "\\%")
        .replace(",", "\\,")
    )


def _y_for(position: str) -> str:
    pos = (position or "center").lower()
    if pos == "top":
        return "h*0.08"
    if pos == "bottom":
        return "h-th-h*0.08"
    return "(h-th)/2"


def _build_drawtext_filter(overlays: list[dict]) -> str:
    font = _font()
    fontfile_arg = f"fontfile='{font}'" if os.path.isabs(font) else f"font='{font}'"
    parts: list[str] = []
    for ov in overlays:
        text = _escape_drawtext(str(ov.get("text", "")))
        start = float(ov.get("start_s", 0.0))
        dur = float(ov.get("duration_s", 2.0))
        end = start + dur
        y = _y_for(ov.get("position", "center"))
        parts.append(
            f"drawtext={fontfile_arg}:text='{text}':"
            f"fontsize=64:fontcolor=white:borderw=3:bordercolor=black@0.7:"
            f"x=(w-tw)/2:y={y}:"
            f"enable='between(t,{start:.3f},{end:.3f})'"
        )
    return ",".join(parts)


def stitch(
    clips: list[str],
    audio_path: str,
    out_path: str,
    text_overlays: list[dict] | None = None,
) -> str:
    """Concatenate clips, mux audio, burn overlays. Returns absolute out_path."""
    _require_ffmpeg()
    if not clips:
        raise ValueError("clips must contain at least one path")
    for c in clips:
        if not os.path.exists(c):
            raise FileNotFoundError(f"clip not found: {c}")

    out_path_abs = os.path.abspath(out_path)
    os.makedirs(os.path.dirname(out_path_abs) or ".", exist_ok=True)

    tmpdir = tempfile.mkdtemp(prefix="stitch_")
    concat_txt = os.path.join(tmpdir, "concat.txt")
    concat_mp4 = os.path.join(tmpdir, "concat.mp4")
    muxed_mp4 = os.path.join(tmpdir, "muxed.mp4")

    try:
        # Step 1: concat demuxer (lossless)
        with open(concat_txt, "w", encoding="utf-8") as f:
            for c in clips:
                abs_c = os.path.abspath(c).replace("'", "'\\''")
                f.write(f"file '{abs_c}'\n")

        _run([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "concat", "-safe", "0", "-i", concat_txt,
            "-c", "copy", concat_mp4,
        ])

        # Step 2: optional audio mux
        has_audio = bool(audio_path) and audio_path.strip() != ""
        if has_audio:
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"audio not found: {audio_path}")
            _run([
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-i", concat_mp4, "-i", audio_path,
                "-map", "0:v", "-map", "1:a",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                "-shortest", muxed_mp4,
            ])
            stage2 = muxed_mp4
        else:
            # Strip any audio for deterministic silent output
            _run([
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-i", concat_mp4, "-an", "-c:v", "copy", muxed_mp4,
            ])
            stage2 = muxed_mp4

        # Step 3: optional drawtext overlays
        if text_overlays:
            vf = _build_drawtext_filter(text_overlays)
            audio_args = ["-c:a", "copy"] if has_audio else ["-an"]
            _run([
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-i", stage2, "-vf", vf,
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "medium",
                *audio_args, out_path_abs,
            ])
        else:
            shutil.copyfile(stage2, out_path_abs)

        return out_path_abs
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Stitch clips + audio + overlays into a final mp4.")
    p.add_argument("--clips", required=True, help="comma-separated mp4 paths in playback order")
    p.add_argument("--audio", default="", help="path to mp3/wav (omit for silent)")
    p.add_argument("--out", required=True, help="output mp4 path")
    p.add_argument(
        "--overlay", action="append", default=[],
        help='JSON dict per overlay, e.g. \'{"text":"hi","start_s":0,"duration_s":2,"position":"center"}\'',
    )
    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    args = _parse_args(argv)
    clips = [c.strip() for c in args.clips.split(",") if c.strip()]
    overlays = [json.loads(o) for o in args.overlay] or None
    out = stitch(clips, args.audio, args.out, overlays)
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
