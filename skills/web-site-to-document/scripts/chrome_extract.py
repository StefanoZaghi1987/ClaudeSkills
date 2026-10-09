#!/usr/bin/env python3
"""
chrome_extract.py — Helper for Chrome MCP-based content extraction.

This script is called by Claude AFTER Claude has manually extracted pages
using Chrome MCP tools. Claude writes page content to a JSON file, then
calls main.py with --pages-file to build the document.

Usage (called by Claude after Chrome MCP extraction):
  python chrome_extract.py \
    --url "https://example.com/page" \
    --title "Page Title" \
    --html "<html>...</html>" \
    --depth 0 \
    --pages-file <workdir>/pages.json

Images found in the HTML are downloaded and embedded, as in the static
pipeline; a failed download degrades to a placeholder in the document.
They are paced by --rate-limit, the same 1 second the crawler defaults to.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import requests

# Windows pipes default to the ANSI code page, which cannot encode the progress glyphs
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def save_page(pages_file: str, url: str, title: str, html: str, depth: int = 0,
              rate_limit: float = 1.0, embed_images: bool = True):
    """
    Append a pre-fetched HTML page to the pages JSON file.
    Claude calls this after extracting each page via Chrome MCP.
    """
    # Add src/ to path for importing the extractor
    src_dir = Path(__file__).parent
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    from common import USER_AGENT, host_is_internal
    from extract import PageExtractor, ImageHandler

    # The write below needs this directory. It happens to exist already, because
    # ImageHandler makes <dir>/images a few lines down and that creates <dir> on
    # the way — a side effect of the *image* path that the page write must not
    # depend on. Owned here instead, where reading save_page shows the guarantee.
    os.makedirs(os.path.dirname(os.path.abspath(pages_file)), exist_ok=True)

    # Same image path as the static pipeline: download and embed, placeholder on
    # failure, paced the same way, and skippable the same way. The browser
    # fetched the page, but the pictures are still fetched from the site — a
    # rendered page with 40 of them fired 40 back-to-back requests while the
    # crawler was pausing between pages, and --no-images was the one control
    # main.py offered that this path had no answer for.
    handler = None
    if embed_images:
        session = requests.Session()
        session.headers["User-Agent"] = USER_AGENT
        images_dir = os.path.join(os.path.dirname(os.path.abspath(pages_file)), "images")
        # The same trust zone the crawler applies: a page's pictures may come
        # from this machine's own network only when the page itself is on it.
        allow_internal = host_is_internal(urlparse(url).hostname or "")
        handler = ImageHandler(session, images_dir, rate_limit,
                               allow_internal=allow_internal)
    extractor = PageExtractor(image_handler=handler)
    page = extractor.extract(html, url)
    if not page.get("title"):
        page["title"] = title  # --title is the fallback when the HTML has no <title>/<h1>
    page["depth"] = depth

    # Load existing
    # ponytail: whole-file rewrite per page — switch to one-line-per-page if
    # multi-hundred-page extractions ever get slow
    pages = []
    if os.path.exists(pages_file):
        with open(pages_file, "r", encoding="utf-8") as f:
            try:
                pages = json.load(f)
            except Exception:
                pages = []

    # Deduplicate by URL
    existing_urls = {p.get("url") for p in pages}
    if url not in existing_urls:
        pages.append(page)
        with open(pages_file, "w", encoding="utf-8") as f:
            json.dump(pages, f, ensure_ascii=False, indent=2)
        # page["title"], not the --title argument: report the title actually stored
        print(f"  ✓ Saved: {page['title'] or url} ({len(pages)} pages total)", flush=True)
    else:
        print(f"  ⚠ Skipped (already saved): {url}", flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", required=True)
    p.add_argument("--title", default="")
    p.add_argument("--html", default="")
    p.add_argument("--html-file", default="")  # alternative: read HTML from file
    p.add_argument("--depth", type=int, default=0)
    p.add_argument("--rate-limit", type=float, default=1.0,
                   help="Seconds between image downloads (default: 1.0)")
    p.add_argument("--no-images", action="store_true",
                   help="Skip downloading images (as in main.py)")
    p.add_argument("--pages-file", required=True)
    args = p.parse_args()

    html = args.html
    if args.html_file:
        if not os.path.exists(args.html_file):
            sys.exit(f"  ❌ HTML file not found: {args.html_file}")
        with open(args.html_file, "r", encoding="utf-8") as f:
            html = f.read()
    if not html.strip():
        sys.exit("  ❌ No HTML to save: pass --html or an existing --html-file")

    # Saving a page is the only thing this script does. It used to be gated
    # behind a --save-page flag, so a call that forgot the flag exited 0, printed
    # nothing and wrote nothing: a fifty-page extraction looked successful one
    # page at a time and ended with an empty pages file.
    save_page(args.pages_file, args.url, args.title, html, args.depth,
              args.rate_limit, not args.no_images)


if __name__ == "__main__":
    main()
