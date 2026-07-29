#!/usr/bin/env python3
"""Validate URLs referenced in draft posts under content/posts/*.md.

Checks every URL in frontmatter `sources:` entries and every URL appearing
in the markdown body. Returns non-zero exit code if any URL is unreachable
or returns an HTTP status >= 400.

Usage:
  python3 scripts/validate_links.py
  python3 scripts/validate_links.py --timeout 15
"""

from __future__ import annotations

import argparse
import re
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POSTS_DIR = ROOT / "content" / "posts"

URL_RE = re.compile(r"https?://[^\s\"'<>)\]]+", re.IGNORECASE)
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
SSL_CTX = ssl._create_unverified_context()


def extract_urls(text: str) -> list[str]:
    seen: dict[str, None] = {}
    for match in URL_RE.findall(text):
        url = match.rstrip(".,;:)\"'")
        seen.setdefault(url, None)
    return list(seen)


def check_url(url: str, timeout: float) -> tuple[bool, str]:
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as resp:
            return resp.status < 400, f"HTTP {resp.status}"
    except urllib.error.HTTPError as exc:
        if exc.code in (403, 405):
            return _check_get(url, timeout)
        return False, f"HTTP {exc.code}"
    except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
        return _check_get(url, timeout)


def _check_get(url: str, timeout: float) -> tuple[bool, str]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as resp:
            return resp.status < 400, f"HTTP {resp.status}"
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}"
    except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
        return False, f"{type(exc).__name__}: {exc}"


def validate(timeout: float = 15.0) -> int:
    files = sorted(p for p in POSTS_DIR.glob("*.md") if p.name != "README.md")
    failures: list[tuple[Path, str, str]] = []
    total = 0

    for path in files:
        text = path.read_text(encoding="utf-8")
        urls = extract_urls(text)
        for url in urls:
            total += 1
            ok, detail = check_url(url, timeout)
            status = "OK " if ok else "FAIL"
            print(f"  [{status}] {detail:14s} {url}")
            if not ok:
                failures.append((path, url, detail))

    print()
    print(f"Checked {total} URL(s) across {len(files)} post(s).")
    if failures:
        print(f"{len(failures)} broken link(s):")
        for path, url, detail in failures:
            print(f"  - {path.name}: {url} ({detail})")
        return 1
    print("All links OK.")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=float, default=15.0, help="Per-URL timeout in seconds.")
    args = parser.parse_args(argv)
    return validate(timeout=args.timeout)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
