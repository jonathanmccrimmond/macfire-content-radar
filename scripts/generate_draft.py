#!/usr/bin/env python3
"""Generate a MacFire social draft using Gemini 2.5 Flash.

Usage (local):
  GEMINI_API_KEY=... python3 scripts/generate_draft.py \\
      --url https://example.com --notes "topic notes"

Usage (GitHub Actions):
  Set SOURCE_URL, NOTES, and optionally SECOND_URL as env vars alongside GEMINI_API_KEY.
  The script is invoked with no arguments; it reads from the environment.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import textwrap
import time
from datetime import date
from pathlib import Path

import requests
import yaml
from google import genai

ROOT = Path(__file__).resolve().parents[1]
POSTS_DIR = ROOT / "content" / "posts"


def fetch_page_text(url: str, max_chars: int = 4000) -> str:
    """Fetch a URL and return lightly stripped plain text."""
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "MacFire-ContentBot/1.0"})
        resp.raise_for_status()
    except Exception as exc:
        print(f"  Warning: could not fetch {url}: {exc}", file=sys.stderr)
        return ""
    text = re.sub(r"<[^>]+>", " ", resp.text)
    text = re.sub(r"&[a-z]+;", " ", text)
    text = re.sub(r"\s{2,}", " ", text).strip()
    return text[:max_chars]


def next_output_path(today: date, notes: str) -> Path:
    """Return the next available post filename for today."""
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    prefix = today.strftime("%Y-%m-%d")
    md_files = [f for f in POSTS_DIR.glob(f"{prefix}-*.md") if f.name != "README.md"]
    n = len(md_files) + 1
    slug = re.sub(r"[^a-z0-9]+", "-", notes.lower())[:35].strip("-")
    return POSTS_DIR / f"{prefix}-{n:02d}-{slug}.md"


def build_prompt(sources: list[dict], notes: str) -> str:
    source_block = "\n\n".join(
        f"Source URL: {s['url']}\n{s['text'] or '[could not fetch — use URL for context only]'}"
        for s in sources
    )
    return f"""You are writing social media content for MacFire Ltd, a Scottish fire safety consultancy.

MacFire's services: fire risk assessments, fire alarms (supply/install/maintenance), fire extinguishers,
fire suppression systems, fire extinguisher training, emergency signage. BAFE-registered, ISO 9001:2015
certified. Free no-obligation site survey. Phone: 0141 881 5455.

Rules:
- Use only public, verifiable facts from the sources provided.
- Tone: practical, calm, useful. Never alarmist.
- Do not invent dates, regulations, or legal interpretations.
- Avoid legal advice language.
- After the main post content, add one short CTA sentence referencing whichever MacFire service is
  most relevant. Include 0141 881 5455. Mention the free site survey only on LinkedIn where there is
  space. Keep it natural — not salesy.
- LinkedIn: 80–120 words total (post + CTA). End with 3–4 hashtags on their own line.
- Facebook: 50–80 words total (post + CTA). End with 2–3 hashtags on their own line.
- X: maximum 240 characters total including CTA and one hashtag. One punchy sentence summarising
  the key point, then the CTA with the phone number, then one hashtag. No more.

Also decide the post's "intent", which controls how its image is treated:
- "sell": a genuine business opportunity to offer MacFire's services, e.g. new premises,
  care homes, HMOs, seasonal readiness checks for businesses. These get a branded image
  (the photo plus a short headline, the MacFire mark and phone number).
- "awareness": a public-safety or goodwill message where a sales pitch would be off, e.g.
  fireworks night, bonfire night, BBQ safety, candle safety, and general regulation news.
  These show the clean photo on its own; the caption carries the message.
When unsure, choose "awareness".

Also produce a "card": copy for the image that accompanies the post.
The card is rendered into a fixed MacFire template (logo, contact details, services and badges are
added automatically — do NOT include them in the card). Card rules:
- kicker: 1–4 words, the topic label (e.g. "Fire safety training", "Care home checks"). No hashtags.
- headline: one short punchy line, 6–12 words, plain sentence case. Wrap the 2–4 most important
  words in *single asterisks* to highlight them in red. Must be spelled correctly and match the post.
- bullets: 3–4 benefit points, each 4–8 words, no trailing punctuation, no hashtags.
- cta_big: a short rallying line, 3–6 words (e.g. "A trained team is a safer team").
- cta_small: a short action label, 3–6 words (e.g. "Book your Fire Awareness training").
- image_idea: one sentence describing a relevant, calm, on-brand photo to sit behind the text
  (e.g. "a fire extinguisher mounted on an office wall"). Never alarming or cartoonish.
  Do not include people, faces, hands, bodies, silhouettes, crowds, staff, reflections of people,
  or partial figures unless the post is specifically about staff/fire-warden training. For training
  images only, people can appear naturally, but avoid close-up faces and posed stock-photo smiles.

Return ONLY a valid JSON object — no markdown fences, no commentary outside the JSON:
{{
  "title": "<concise post title, max 80 chars>",
  "angle": "<one sentence: why this matters for MacFire's audience>",
  "linkedin": "<LinkedIn post text + CTA + hashtags>",
  "facebook": "<Facebook post text + CTA + hashtags>",
  "x": "<X/Twitter post — max 240 chars including CTA and one hashtag>",
  "notes": "<1–2 sentences of review guidance for the human editor>",
  "intent": "<sell or awareness>",
  "card": {{
    "kicker": "<1–4 word topic label>",
    "headline": "<6–12 word line with *highlighted* words>",
    "bullets": ["<point 1>", "<point 2>", "<point 3>"],
    "cta_big": "<3–6 word rallying line>",
    "cta_small": "<3–6 word action label>",
    "image_idea": "<one sentence describing a calm, relevant photo>"
  }}
}}

Editor notes / angle:
{notes}

Sources:
{source_block}"""


def card_block(card: dict, image_path: str) -> str:
    """Serialise the card copy + image path as YAML frontmatter lines."""
    card_yaml = yaml.safe_dump(card, sort_keys=False, allow_unicode=True, width=1000).rstrip()
    return f"card:\n{textwrap.indent(card_yaml, '  ')}\nimage: \"{image_path}\""


def write_post(path: Path, title: str, today: date, sources: list[dict], data: dict) -> None:
    source_lines = "\n".join(
        f'  - title: "{s["title"]}"\n    url: "{s["url"]}"'
        for s in sources
    )
    intent = data.get("intent", "awareness")
    # Sell posts show the rendered card; awareness posts show the plain photo.
    # generate_card_photo.py keeps these correct once the background is made.
    image_path = (
        f"content/images/{path.stem}.png" if intent == "sell"
        else f"content/images/{path.stem}-bg.jpg"
    )
    card_fm = card_block(data["card"], image_path) if data.get("card") else ""
    path.write_text(
        f"""---
title: "{title}"
date: {today.isoformat()}
intent: {intent}
status: draft
platforms:
  - linkedin
  - facebook
  - x
sources:
{source_lines}
{card_fm}
---

## Angle

{data['angle']}

## LinkedIn

{data['linkedin']}

## Facebook

{data['facebook']}

## X

{data['x']}

## Notes

{data['notes']}
""",
        encoding="utf-8",
    )


def parse_args() -> tuple[list[str], str]:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", action="append", dest="urls", default=[], metavar="URL")
    parser.add_argument("--notes", default="", metavar="TEXT")
    args = parser.parse_args()

    urls = args.urls or [u for u in [os.getenv("SOURCE_URL"), os.getenv("SECOND_URL")] if u]
    notes = args.notes or os.getenv("NOTES", "")
    return urls, notes


def main() -> None:
    urls, notes = parse_args()

    if not urls:
        sys.exit("Error: provide at least one --url or set SOURCE_URL env var.")
    if not notes:
        sys.exit("Error: provide --notes or set NOTES env var.")
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        sys.exit("Error: GEMINI_API_KEY is not set.")

    print(f"Fetching {len(urls)} source(s)...")
    sources = []
    for url in urls:
        print(f"  -> {url}")
        text = fetch_page_text(url)
        title = url.rstrip("/").rsplit("/", 1)[-1].replace("-", " ").replace("_", " ").title()
        sources.append({"url": url, "title": title or url, "text": text})

    print("Generating draft with Gemini 2.5 Flash...")
    client = genai.Client(api_key=api_key)
    prompt = build_prompt(sources, notes)
    raw = None
    for attempt in range(4):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            raw = response.text.strip()
            break
        except Exception as exc:
            msg = str(exc)
            if ("503" in msg or "UNAVAILABLE" in msg or "429" in msg) and attempt < 3:
                wait = 30 * (attempt + 1)
                print(f"  API busy (attempt {attempt + 1}/4), retrying in {wait}s...")
                time.sleep(wait)
            else:
                sys.exit(f"Error calling Gemini API: {exc}")
    if raw is None:
        sys.exit("Error: all retry attempts failed.")
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print(f"Model output:\n{raw}", file=sys.stderr)
        sys.exit("Error: model did not return valid JSON.")

    for key in ("title", "angle", "linkedin", "facebook", "x", "notes"):
        if key not in data:
            sys.exit(f"Error: missing key '{key}' in model response.")

    intent = str(data.get("intent", "")).strip().lower()
    if intent not in ("sell", "awareness"):
        intent = "awareness"
    data["intent"] = intent

    card = data.get("card")
    if not isinstance(card, dict) or not card.get("headline"):
        print("Warning: model returned no usable card; draft will have no image.", file=sys.stderr)
        data["card"] = None

    today = date.today()
    output_path = next_output_path(today, notes)
    write_post(output_path, data["title"], today, sources, data)
    print(f"Draft written -> {output_path.relative_to(ROOT)}")

    # Sell posts get a rendered card now (non-fatal if Chromium is unavailable).
    # Awareness posts show the plain photo, so no card is rendered. Either way the
    # background photo is added afterwards by generate_card_photo.py.
    if intent == "sell" and data.get("card"):
        try:
            from build_post_image import render_png

            out = render_png(data["card"], ROOT / "content" / "images" / f"{output_path.stem}.png")
            print(f"Card image  -> {out.relative_to(ROOT)}")
        except SystemExit as exc:
            print(f"Note: card image not rendered ({exc}). Run build_post_image.py to add it.",
                  file=sys.stderr)
        except Exception as exc:
            print(f"Note: card image not rendered ({exc}). Run build_post_image.py to add it.",
                  file=sys.stderr)
    elif intent == "awareness":
        print("Awareness post: clean photo only, no branded card.")


if __name__ == "__main__":
    main()
