#!/usr/bin/env python3
"""
chrome_extract.py — Helper for Chrome MCP-based content extraction.

This script is called by Claude AFTER Claude has manually extracted pages
using Chrome MCP tools. Claude writes page content to a JSON file, then
calls main.py with --pages-file to build the document.

Usage (called by Claude after Chrome MCP extraction):
  python chrome_extract.py \
    --url 'https://example.com/page' \
    --html-file "<workdir>/page_1.html" \
    --depth 0 \
    --pages-file "<workdir>/pages.json"

The URL in single quotes, and no --title or --html from a shell: both carry the
site's own text, which Bash expands inside double quotes ($(...), backticks).

Images found in the HTML are downloaded and embedded, as in the static
pipeline; a failed download degrades to a placeholder in the document.
They are paced by --rate-limit, the same 1 second the crawler defaults to.
"""

import argparse
import codecs
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

# main.py's floor (3.10), checked before the third-party imports so an older
# interpreter gets this message and not an ImportError
if sys.version_info < (3, 10):
    sys.exit(f"web-site-to-document needs Python 3.10 or newer (this is "
             f"{sys.version_info[0]}.{sys.version_info[1]})")

import requests

# Windows pipes default to the ANSI code page, which cannot encode the progress glyphs
# (stderr too: the sys.exit messages below go there)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def read_html_file(path: str):
    """The file's text, or its bytes when no encoding is certain.

    A redirect in Windows PowerShell 5.1 writes UTF-16 with a BOM, which a plain
    UTF-8 read refuses. A BOM decides; UTF-8 is tried next; anything else goes
    to the extractor as bytes, where BeautifulSoup reads the page's own
    <meta charset>.
    """
    with open(path, "rb") as f:
        raw = f.read()
    for bom, enc in ((codecs.BOM_UTF8, "utf-8-sig"), (codecs.BOM_UTF16_LE, "utf-16"),
                     (codecs.BOM_UTF16_BE, "utf-16")):
        if raw.startswith(bom):
            return raw.decode(enc)
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw


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

    from common import USER_AGENT, absolute_image_paths, host_is_internal, relative_image_paths
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
        # an unreadable pages file stops the run: read as empty, the rewrite below
        # would replace every page saved so far with this one
        with open(pages_file, "r", encoding="utf-8") as f:
            try:
                pages = json.load(f)
            except ValueError as e:
                sys.exit(f"  ❌ {pages_file} is not readable JSON ({e}); nothing was written. "
                         f"Restore it, or start again in an empty work directory")
        if not isinstance(pages, list) or not all(isinstance(p, dict) for p in pages):
            sys.exit(f"  ❌ {pages_file} does not hold a list of pages; nothing was written")

    # Deduplicate by URL
    existing_urls = {p.get("url") for p in pages}
    if url not in existing_urls:
        pages.append(page)
        # Relative to the pages file, as main.py writes them: the file and its
        # images/ folder then rebuild wherever they are moved together
        base = os.path.dirname(os.path.abspath(pages_file))
        # temp file + os.replace: a run stopped mid-write leaves the previous file whole
        tmp = pages_file + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(relative_image_paths(absolute_image_paths(pages, base), base), f,
                      ensure_ascii=False, indent=2)
        os.replace(tmp, pages_file)
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
        html = read_html_file(args.html_file)
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
