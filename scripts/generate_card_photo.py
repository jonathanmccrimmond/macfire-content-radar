#!/usr/bin/env python3
"""Generate a relevant, TEXT-FREE background photo for a post's card.

This is the "relevant imagery" step. Each card carries an `image_idea` (written
by generate_draft.py), e.g. "fireworks bursting over a calm city skyline". This
script fetches a matching stock photo (Pexels) or generates one via AI, stores
it under content/images/<slug>-bg.jpg, records it as `card.photo`, and
re-renders the branded card so the photo sits behind the copy.

Provider priority (automatic):
  1. Pexels stock photos  — set PEXELS_API_KEY (free at pexels.com/api/)
  2. Gemini image gen     — set CARD_IMAGE_PROVIDER=gemini + GEMINI_API_KEY
  3. Pollinations (Flux)  — keyless fallback, lower quality

Override the auto-selection with: CARD_IMAGE_PROVIDER=pexels|gemini|pollinations

Usage:
  python3 scripts/generate_card_photo.py content/posts/<file>.md [<file2>.md ...]
  python3 scripts/generate_card_photo.py --all          # every card missing a photo
  python3 scripts/generate_card_photo.py --all --force   # regenerate all photos
"""
from __future__ import annotations

import argparse
import base64
import os
import sys
import time
from pathlib import Path
from urllib.parse import quote, urlencode

import requests
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_post_image as bpi  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
POSTS_DIR = ROOT / "content" / "posts"
IMAGES_DIR = ROOT / "content" / "images"

_explicit_provider = os.environ.get("CARD_IMAGE_PROVIDER", "").strip().lower()
IMAGE_PROVIDER = _explicit_provider or (
    "pexels" if os.environ.get("PEXELS_API_KEY") else "pollinations"
)
IMAGE_MODEL = os.environ.get("CARD_IMAGE_MODEL", "gemini-2.5-flash-image")
POLLINATIONS_MODEL = os.environ.get("POLLINATIONS_IMAGE_MODEL", "flux")

PROMPT_TEMPLATE = (
    "Generate a premium photorealistic editorial photograph for MacFire, a "
    "Scottish fire-safety company, portrait orientation (4:5). Subject: {idea}. "
    "Make it feel like a real Scottish commercial, residential or hospitality "
    "premises photographed for a trusted local service business. Calm, practical, "
    "reassuring and well lit; natural daylight or soft interior light; muted "
    "professional colours that sit behind a deep navy overlay. Simple composition "
    "with one clear subject, believable materials, and generous uncluttered space "
    "through the centre/lower third for a branded overlay. Do not include people "
    "unless the subject is explicitly staff/fire-warden training. For non-training "
    "images: no humans, faces, hands, bodies, silhouettes, crowds, staff, reflections "
    "of people or partial figures. For staff/fire-warden training only, people may "
    "appear naturally in the scene, but avoid close-up faces, posed smiles and stock "
    "photo gloss. Avoid dramatic emergency response, smoke, damage, panic, theatrical "
    "flames, cartoons, CGI, illustrations and exaggerated wide angles. Do not show "
    "branded products. Absolutely no text, no words, no letters, no numbers, no "
    "readable signage, no posters, no labels, no badges, no logos and no visible "
    "watermarks anywhere in the image."
)


def post_frontmatter(post: Path) -> dict:
    text = post.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    return yaml.safe_load(parts[1]) or {}


def image_bytes_from_response(resp) -> bytes | None:
    parts = list(getattr(resp, "parts", []) or [])
    for cand in getattr(resp, "candidates", None) or []:
        parts.extend(getattr(getattr(cand, "content", None), "parts", []) or [])
    for part in parts:
        inline = getattr(part, "inline_data", None)
        if not inline or not getattr(inline, "data", None):
            continue
        data = inline.data
        return data if isinstance(data, bytes) else base64.b64decode(data)
    return None


def pollinations_prompt(image_idea: str) -> str:
    return PROMPT_TEMPLATE.format(idea=image_idea.rstrip("."))


def generate_photo_pexels(image_idea: str, out_path: Path) -> Path:
    api_key = os.environ.get("PEXELS_API_KEY", "")
    if not api_key:
        raise RuntimeError("PEXELS_API_KEY is not set")
    resp = requests.get(
        "https://api.pexels.com/v1/search",
        headers={"Authorization": api_key},
        params={"query": image_idea, "orientation": "portrait", "size": "large", "per_page": 5},
        timeout=30,
    )
    resp.raise_for_status()
    photos = resp.json().get("photos", [])
    if not photos:
        raise RuntimeError(f"No Pexels photos found for: {image_idea!r}")
    photo = photos[0]
    img_resp = requests.get(photo["src"]["large2x"], timeout=60)
    img_resp.raise_for_status()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(img_resp.content)
    credit = f"{photo.get('photographer', 'Unknown')} / Pexels\n{photo.get('url', '')}\n"
    out_path.with_suffix(".credit.txt").write_text(credit, encoding="utf-8")
    return out_path


def generate_photo_pollinations(image_idea: str, out_path: Path) -> Path:
    params = {
        "width": "1080",
        "height": "1350",
        "model": POLLINATIONS_MODEL,
        "nologo": "true",
        "private": "true",
        "safe": "true",
        "seed": str(int(time.time() * 1000) % 2147483647),
    }
    url = "https://image.pollinations.ai/prompt/" + quote(pollinations_prompt(image_idea), safe="")
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            response = requests.get(f"{url}?{urlencode(params)}", timeout=45)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            if not content_type.startswith("image/"):
                raise RuntimeError(f"Pollinations returned {content_type or 'non-image content'}")
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(response.content)
            return out_path
        except Exception as exc:
            last_error = exc
            print(f"  attempt {attempt}/3 failed: {exc}", flush=True)
            time.sleep(2 * attempt)
    raise RuntimeError(f"Could not generate image for {image_idea!r}: {last_error}")


def generate_photo_gemini(image_idea: str, out_path: Path) -> Path:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        sys.exit("Error: GEMINI_API_KEY is not set.")
    from google import genai  # imported lazily so card helpers work without the SDK
    from google.genai import types

    client = genai.Client(api_key=api_key)
    resp = client.models.generate_content(
        model=IMAGE_MODEL,
        contents=[PROMPT_TEMPLATE.format(idea=image_idea.rstrip("."))],
        config=types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"]),
    )
    image_bytes = image_bytes_from_response(resp)
    if image_bytes:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(image_bytes)
        return out_path
    sys.exit(f"Image model returned no image for: {image_idea!r}")


def photo_extension() -> str:
    return "png" if IMAGE_PROVIDER == "gemini" else "jpg"


def generate_photo(image_idea: str, out_path: Path) -> Path:
    if IMAGE_PROVIDER == "pexels":
        return generate_photo_pexels(image_idea, out_path)
    if IMAGE_PROVIDER == "pollinations":
        return generate_photo_pollinations(image_idea, out_path)
    if IMAGE_PROVIDER == "gemini":
        return generate_photo_gemini(image_idea, out_path)
    sys.exit("Error: CARD_IMAGE_PROVIDER must be 'pexels', 'pollinations', or 'gemini'.")


def set_card_photo(post: Path, photo_rel: str) -> dict:
    """Insert/replace `photo:` inside the card block and return the updated card."""
    text = post.read_text(encoding="utf-8")
    pre, fm, body = text.split("---", 2)
    lines = fm.split("\n")
    out, in_card, done = [], False, False
    for line in lines:
        if line.startswith("card:"):
            in_card = True
            out.append(line)
            out.append(f'  photo: "{photo_rel}"')
            done = True
            continue
        # drop any existing card.photo line so we don't duplicate it
        if in_card and line.strip().startswith("photo:") and line.startswith("  "):
            continue
        if in_card and line and not line.startswith("  "):
            in_card = False
        out.append(line)
    if not done:
        sys.exit(f"{post} has no card: block")
    post.write_text(f"---{chr(10).join(out)}---{body}", encoding="utf-8")
    return yaml.safe_load(chr(10).join(out)).get("card", {})


def posts_needing_photo(force: bool) -> list[Path]:
    result = []
    for post in sorted(POSTS_DIR.glob("*.md")):
        data = post_frontmatter(post)
        card = data.get("card") or {}
        if not card.get("image_idea"):
            continue
        photo = card.get("photo")
        if photo and (ROOT / photo).exists() and not force:
            continue
        result.append(post)
    return result


def set_image_field(post: Path, image_rel: str) -> None:
    """Replace (or insert) the top-level `image:` line in the frontmatter."""
    text = post.read_text(encoding="utf-8")
    pre, fm, body = text.split("---", 2)
    lines = fm.split("\n")
    out, done = [], False
    for line in lines:
        if line.startswith("image:"):
            out.append(f'image: "{image_rel}"')
            done = True
        else:
            out.append(line)
    if not done:
        # insert after the date line, or at the top of the frontmatter
        idx = next((i for i, l in enumerate(out) if l.startswith("date:")), 0)
        out.insert(idx + 1, f'image: "{image_rel}"')
    post.write_text(f"---{chr(10).join(out)}---{body}", encoding="utf-8")


def process(post: Path) -> bool:
    data = post_frontmatter(post)
    card = data.get("card") or {}
    idea = card.get("image_idea")
    if not idea:
        print(f"skip (no image_idea): {post.name}", flush=True)
        return True
    intent = str(data.get("intent", "")).strip().lower()
    photo_rel = f"content/images/{post.stem}-bg.{photo_extension()}"
    print(f"{post.name}: generating photo -> {photo_rel}", flush=True)
    try:
        generate_photo(idea, ROOT / photo_rel)
    except Exception as exc:
        print(f"  failed: {exc}", flush=True)
        return False
    card = set_card_photo(post, photo_rel)
    if intent == "awareness":
        # Awareness posts use the clean photo directly: no branded card.
        poster = IMAGES_DIR / f"{post.stem}.png"
        if poster.exists():
            poster.unlink()
        set_image_field(post, photo_rel)
        print(f"  awareness: photo used directly -> {photo_rel}", flush=True)
    else:
        out = bpi.render_png(card, IMAGES_DIR / f"{post.stem}.png")
        set_image_field(post, f"content/images/{post.stem}.png")
        print(f"  re-rendered card -> {out.relative_to(ROOT)}", flush=True)
    return True


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("posts", nargs="*", help="post .md paths")
    ap.add_argument("--all", action="store_true", help="all cards missing a photo")
    ap.add_argument("--force", action="store_true", help="regenerate even if a photo exists")
    args = ap.parse_args()

    if args.all:
        targets = posts_needing_photo(args.force)
    elif args.posts:
        targets = [Path(p) for p in args.posts]
    else:
        ap.error("provide post paths or --all")

    if not targets:
        print("Nothing to do.")
        return
    failures = 0
    for post in targets:
        if not process(post):
            failures += 1
    if failures:
        sys.exit(f"Done with {failures} failed image(s). Re-run the same command to retry.")


if __name__ == "__main__":
    main()
