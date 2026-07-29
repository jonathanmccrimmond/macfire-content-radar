#!/usr/bin/env python3
"""Render the premium MacFire card (PNG) for a sell post.

Why this exists
---------------
Sell posts get a minimal, premium treatment: the text-free background photo
(generated free by generate_card_photo.py) with one short headline, the MacFire
mark and the phone number. Every word is REAL text rendered here by headless
Chromium, never baked into the AI photo, so spelling and branding are always
correct. This deliberately replaces the older busy poster (kicker, bullets,
service pills, CTA band).

Awareness posts do not use this renderer at all: they show the plain photo with
the caption alongside (their `image:` points straight at the `-bg.jpg`).

Input comes from a post's frontmatter:

  intent: sell
  card:
    photo: "content/images/<slug>-bg.jpg"     # made by generate_card_photo.py
    headline: "Summer comfort and *fire safety* can work together"  # *words* = red

Output: content/images/<slug>.png  (the post's `image:` already points here)

Usage:
  python3 scripts/build_post_image.py --all                 # every sell post with a photo
  python3 scripts/build_post_image.py --post content/posts/<file>.md
  python3 scripts/build_post_image.py --demo                # layout check, van photo
"""
from __future__ import annotations

import argparse
import glob
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
POSTS_DIR = ROOT / "content" / "posts"
IMAGES_DIR = ROOT / "content" / "images"
ASSETS_DIR = ROOT / "preview" / "assets"
TEMPLATE = Path(__file__).resolve().parent / "templates" / "post_card.html"

PHONE = "0141 881 5455"
LOGO = ASSETS_DIR / "macfire-logo.png"
CANVAS = (1080, 1350)


def find_chrome() -> str:
    if os.environ.get("CHROME_BIN"):
        return os.environ["CHROME_BIN"]
    roots = [os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers")]
    for root in roots:
        for pattern in ("chromium-*/chrome-linux/chrome", "chromium-*/chrome-linux/headless_shell"):
            hits = sorted(glob.glob(os.path.join(root, pattern)))
            if hits:
                return hits[-1]
    for name in ("chromium", "chromium-browser", "google-chrome", "chrome"):
        found = shutil.which(name)
        if found:
            return found
    sys.exit("No Chromium/Chrome binary found. Set CHROME_BIN or install chromium.")


def _highlight(text: str) -> str:
    """Escape HTML, then turn *asterisk* spans into red highlight spans."""
    parts = re.split(r"\*(.+?)\*", text)
    out = []
    for i, part in enumerate(parts):
        esc = html.escape(part)
        out.append(f'<span class="hl">{esc}</span>' if i % 2 else esc)
    return "".join(out)


MACFIRE_LOGO_SVG = """<svg class="logo" viewBox="0 0 270 100" xmlns="http://www.w3.org/2000/svg" aria-label="MacFire Ltd, Fire Protection Company">
<rect width="270" height="100" fill="#1A1F3C"/>
<rect x="2" y="69" width="266" height="29" fill="#ffffff"/>
<text x="7" y="57" font-family="Impact,'Arial Black',sans-serif" font-size="46" fill="#ffffff" textLength="107" lengthAdjust="spacingAndGlyphs">Mac</text>
<text x="119" y="57" font-family="Impact,'Arial Black',sans-serif" font-size="46" fill="#ffffff" textLength="92" lengthAdjust="spacingAndGlyphs">Fire</text>
<text x="213" y="57" font-family="Impact,'Arial Black',sans-serif" font-size="34" fill="#ffffff" textLength="53" lengthAdjust="spacingAndGlyphs">Ltd</text>
<text x="135" y="83" text-anchor="middle" dominant-baseline="central" font-family="Arial,Helvetica,sans-serif" font-weight="bold" font-size="17" fill="#C31E1F" letter-spacing="1.5">Fire Protection Company</text>
</svg>"""


def logo_tag() -> str:
    return MACFIRE_LOGO_SVG


def load_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    _, fm, _ = text.split("---", 2)
    return yaml.safe_load(fm) or {}


def resolve_photo(photo: str) -> Path | None:
    if not photo:
        return None
    p = Path(photo)
    if not p.is_absolute():
        p = ROOT / photo
    return p if p.exists() else None


def render_png(card: dict, out_path: Path, scale: int = 2) -> Path:
    """Render the minimal premium card from a `card:` dict (photo + headline).

    Kept to the (card, out_path) signature so generate_draft.py and
    generate_card_photo.py keep working unchanged. Extra card fields from the
    old busy poster (kicker, bullets, services, cta) are simply ignored.
    """
    card = card or {}
    photo = resolve_photo(card.get("photo", ""))
    bg_uri = photo.resolve().as_uri() if photo else ""
    headline = card.get("headline") or ""
    markup = TEMPLATE.read_text(encoding="utf-8")
    markup = (
        markup.replace("{{BG}}", bg_uri)
        .replace("{{HEADLINE}}", _highlight(headline))
        .replace("{{LOGO}}", logo_tag())
        .replace("{{PHONE}}", html.escape(PHONE))
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as fh:
        fh.write(markup)
        html_path = fh.name
    try:
        subprocess.run(
            [
                find_chrome(), "--headless", "--no-sandbox", "--hide-scrollbars",
                "--force-color-profile=srgb",
                f"--force-device-scale-factor={scale}",
                f"--window-size={CANVAS[0]},{CANVAS[1]}",
                f"--screenshot={out_path}",
                f"file://{html_path}",
            ],
            check=True, capture_output=True, text=True,
        )
    except subprocess.CalledProcessError as exc:
        sys.exit(f"Chromium render failed:\n{exc.stderr}")
    finally:
        os.unlink(html_path)
    return out_path


def card_for_post(path: Path) -> Path | None:
    meta = load_frontmatter(path)
    if str(meta.get("intent", "")).strip().lower() != "sell":
        return None
    card = meta.get("card") or {}
    photo = resolve_photo(card.get("photo", ""))
    if not photo:
        print(f"  skip {path.stem}: no background photo yet")
        return None
    out = IMAGES_DIR / f"{path.stem}.png"
    render_png(card, out)
    print(f"  wrote {out.relative_to(ROOT)}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--post", help="path to a single sell post .md")
    ap.add_argument("--all", action="store_true", help="render cards for every sell post with a photo")
    ap.add_argument("--demo", action="store_true", help="layout check using the van photo")
    ap.add_argument("--out", help="output PNG path (demo only)")
    args = ap.parse_args()

    if args.demo:
        demo_card = {
            "photo": str(ASSETS_DIR / "macfire-van.jpg"),
            "headline": "Keep residents *safe* this summer",
        }
        out = Path(args.out) if args.out else IMAGES_DIR / "demo-card.png"
        render_png(demo_card, out)
        print(f"Wrote {out}")
        return

    if args.post:
        p = Path(args.post) if os.path.isabs(args.post) else ROOT / args.post
        card_for_post(p)
        return

    made = 0
    for path in sorted(POSTS_DIR.glob("*.md")):
        if path.name == "README.md":
            continue
        if card_for_post(path):
            made += 1
    print(f"Done. {made} card(s) rendered.")


if __name__ == "__main__":
    main()
