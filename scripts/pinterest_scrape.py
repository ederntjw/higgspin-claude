"""Pinterest scraper — driven by Playwright.

Reads a search query (built upstream from the visual fingerprint), drives a
real Chromium with a persistent profile so the login session and any solved
CAPTCHA persist between runs.

Usage:
    python scripts/pinterest_scrape.py "minimalist pastel interior" --count 40

Outputs to output/pinterest/{slug}/ as JPGs, plus a metadata.jsonl with the
source pin URL alongside each saved file.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv
from playwright.sync_api import Page, sync_playwright

ROOT = Path(__file__).resolve().parent.parent
STATE_DIR = ROOT / ".playwright-state"
OUT_BASE = ROOT / "output" / "pinterest"


def slugify(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s[:60] or "query"


def login_if_needed(page: Page, email: str, password: str) -> None:
    page.goto("https://www.pinterest.com/", wait_until="domcontentloaded")
    if page.locator('[data-test-id="header-profile"]').count() > 0:
        return
    page.goto("https://www.pinterest.com/login/", wait_until="domcontentloaded")
    try:
        page.fill('input#email', email, timeout=8000)
        page.fill('input#password', password, timeout=4000)
        page.click('button[type="submit"]', timeout=4000)
    except Exception:
        # Form may already be partially filled or selectors changed — fall through.
        pass
    # Give the user up to 90s to clear any CAPTCHA in the visible browser.
    for _ in range(90):
        if page.locator('[data-test-id="header-profile"]').count() > 0:
            return
        time.sleep(1)
    print("warning: could not confirm login; continuing anyway", file=sys.stderr)


def upscale_url(url: str) -> str:
    """Pinterest serves /236x/ thumbs by default. Swap for /originals/."""
    return re.sub(r"/\d+x\d*/", "/originals/", url, count=1)


def scrape(query: str, count: int) -> Path:
    load_dotenv(ROOT / ".env")
    email = os.environ.get("PINTEREST_EMAIL", "")
    password = os.environ.get("PINTEREST_PASSWORD", "")

    out_dir = OUT_BASE / slugify(query)
    out_dir.mkdir(parents=True, exist_ok=True)
    meta_path = out_dir / "metadata.jsonl"
    meta_path.write_text("")

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(STATE_DIR),
            headless=False,
            viewport={"width": 1400, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = ctx.new_page()
        if email and password:
            login_if_needed(page, email, password)

        url = f"https://www.pinterest.com/search/pins/?q={requests.utils.quote(query)}"
        page.goto(url, wait_until="domcontentloaded")

        seen: set[str] = set()
        saved = 0
        scrolls = 0
        while saved < count and scrolls < 40:
            srcs = page.eval_on_selector_all(
                'div[data-test-id="pin"] img',
                "els => els.map(e => e.src).filter(Boolean)",
            )
            for src in srcs:
                if src in seen:
                    continue
                seen.add(src)
                hi = upscale_url(src)
                try:
                    r = requests.get(hi, timeout=20)
                    if r.status_code != 200 or len(r.content) < 5_000:
                        # fall back to whatever res Pinterest served
                        r = requests.get(src, timeout=20)
                    if r.status_code != 200:
                        continue
                    name = Path(urlparse(hi).path).name or f"img_{saved}.jpg"
                    fp = out_dir / f"{saved:03d}_{name}"
                    fp.write_bytes(r.content)
                    with meta_path.open("a") as f:
                        f.write(json.dumps({"file": fp.name, "src": hi}) + "\n")
                    saved += 1
                    if saved >= count:
                        break
                except requests.RequestException:
                    continue
            page.mouse.wheel(0, 4000)
            time.sleep(1.2)
            scrolls += 1

        ctx.close()

    print(json.dumps({"query": query, "saved": saved, "out": str(out_dir)}))
    return out_dir


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--count", type=int, default=40)
    args = ap.parse_args()
    scrape(args.query, args.count)
    return 0


if __name__ == "__main__":
    sys.exit(main())
