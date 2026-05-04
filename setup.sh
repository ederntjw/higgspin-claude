#!/usr/bin/env bash
# One-shot setup for higgspin-claude.
# Creates a venv, installs deps, fetches the Playwright browser, and
# copies the .env template if you haven't filled one in yet.
# Idempotent: safe to re-run.

set -euo pipefail

cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 not found. Install Python 3.9+ first."
  exit 1
fi

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "WARNING: ffmpeg not found on PATH."
  echo "  macOS:  brew install ffmpeg"
  echo "  Linux:  sudo apt install ffmpeg"
  echo "  Stage 7 (stitch) will fail until this is installed."
  echo
fi

echo "[1/4] Creating .venv (if missing)..."
[ -d .venv ] || python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate

echo "[2/4] Installing Python dependencies..."
python -m pip install --upgrade pip >/dev/null
python -m pip install -r requirements.txt

echo "[3/4] Fetching Playwright Chromium..."
python -m playwright install chromium

echo "[4/4] Preparing .env..."
if [ -f .env ]; then
  echo "  .env already exists, leaving it alone."
else
  cp .env.example .env
  echo "  copied .env.example -> .env. Open it and fill in HF_KEY + Pinterest creds."
fi

cat <<'EOF'

Setup complete. Next steps:

  1. Edit .env  -> set HF_KEY (key:secret from https://cloud.higgsfield.ai/api-keys)
                   and your Pinterest email + password.
  2. Drop 5-10 moodboard images into references/images/  (>=1024px each).
  3. (Optional) Drop a clean product photo at references/product/hero.png to
     enable product-lock mode.
  4. Open this folder in Claude Code (https://claude.com/claude-code) and say:
       "run the pipeline"
     Claude reads CLAUDE.md, does the two vision passes, and runs everything else.

EOF
