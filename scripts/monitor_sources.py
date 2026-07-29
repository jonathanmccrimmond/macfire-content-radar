#!/usr/bin/env python3
"""Monitor Scottish fire safety sources for new content and auto-generate social drafts.

Reads source config from monitor/sources.json.
Tracks seen item URLs in monitor/last_seen.json so nothing is drafted twice.
Calls generate_draft.py for each genuinely new item found.

Usage:
  GEMINI_API_KEY=... python3 scripts/monitor_sources.py
  GEMINI_API_KEY=... python3 scripts/monitor_sources.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import feedparser

ROOT = Path(__file__).resolve().parents[1]
MONITOR_DIR = ROOT / "monitor"
STATE_FILE = MONITOR_DIR / "last_seen.json"
SOURCES_FILE = MONITOR_DIR / "sources.json"

MAX_PER_SOURCE = 5


def load_state() -> dict[str, list[str]]:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(state: dict[str, list[str]]) -> None:
    MONITOR_DIR.mkdir(exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n")


def fetch_items(source: dict) -> list[dict]:
    """Fetch and filter items from an RSS/Atom feed."""
    print(f"  Fetching {source['feed']}")
    try:
        feed = feedparser.parse(source["feed"])
    except Exception as exc:
        print(f"  Warning: could not fetch feed: {exc}", file=sys.stderr)
        return []

    keywords = [k.lower() for k in source.get("keywords", [])]
    items = []

    for entry in feed.entries:
        url = entry.get("link", "").strip()
        title = entry.get("title", "").strip()
        if not url or not title:
            continue

        if keywords:
            text = (title + " " + entry.get("summary", "")).lower()
            if not any(kw in text for kw in keywords):
                continue

        notes = source.get("notes_template", "{title}").format(title=title)
        items.append({"url": url, "title": title, "notes": notes})

    return items


def generate_draft(item: dict, dry_run: bool) -> bool:
    if dry_run:
        print(f"    [dry-run] Would generate: {item['title'][:70]}")
        return True

    env = {**os.environ, "SOURCE_URL": item["url"], "NOTES": item["notes"]}
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "generate_draft.py")],
        env=env,
    )
    return result.returncode == 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Detect new items but do not generate drafts")
    args = parser.parse_args()

    if not args.dry_run and not os.environ.get("GEMINI_API_KEY"):
        sys.exit("Error: GEMINI_API_KEY is not set.")

    sources = json.loads(SOURCES_FILE.read_text())
    state = load_state()
    first_run = not STATE_FILE.exists()

    total_new = 0
    total_generated = 0

    for source in sources:
        name = source["name"]
        print(f"\nSource: {name}")

        items = fetch_items(source)
        seen = set(state.get(name, []))
        new_items = [item for item in items if item["url"] not in seen]

        print(f"  {len(items)} item(s) fetched, {len(new_items)} new")
        total_new += len(new_items)

        # On first run, seed state without generating (avoids flooding on setup).
        # Cap subsequent runs at MAX_PER_SOURCE to stay within rate limits.
        to_generate = [] if first_run else new_items[:MAX_PER_SOURCE]

        for item in to_generate:
            print(f"  -> {item['title'][:70]}")
            ok = generate_draft(item, args.dry_run)
            if ok:
                seen.add(item["url"])
                total_generated += 1
            else:
                print(f"  Warning: draft generation failed for {item['url']}", file=sys.stderr)

        # On first run, mark everything as seen so future runs only pick up genuinely new items
        if first_run:
            for item in items:
                seen.add(item["url"])

        state[name] = list(seen)

    save_state(state)

    if first_run:
        print(f"\nFirst run: seeded state with {total_new} existing item(s). Future runs will pick up new content.")
    else:
        print(f"\nDone. {total_generated} draft(s) generated.")

    # Write output for GitHub Actions
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"drafts_generated={total_generated}\n")


if __name__ == "__main__":
    main()
