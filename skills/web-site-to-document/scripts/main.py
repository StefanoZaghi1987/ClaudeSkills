#!/usr/bin/env python3
"""
main.py — Entry point for web-site-to-document skill.

Usage:
  python main.py --url <URL> --format <docx|pdf|md> --output <path> [options]

Options:
  --url           Starting URL (required)
  --format        Output format: docx (default), pdf, md
  --output        Output file path (required unless --analyze-only)
  --depth         Depth of link traversal: integer or "unlimited" (default: unlimited)
  --scope         Domain scope: same (default), subdomains, custom
  --allowed-domains  Space-separated list of allowed domains (when scope=custom)
  --include-path  Only follow URL paths starting with these prefixes (e.g. /docs/)
  --exclude-path  Never follow URL paths starting with these prefixes (wins over include)
  --max-pages     Max pages to scrape: integer or "unlimited" (default: unlimited)
  --rate-limit    Seconds between requests (default: 1.0)
  --no-images     Skip downloading and embedding images
  --analyze-only  Only analyze the site and print stats, do not scrape
  --work-dir      Directory for intermediate files (default: an auto-created temp dir)
"""

import argparse
import json
import os
import re
import sys
import tempfile
import urllib.parse
from pathlib import Path

# Windows pipes default to the ANSI code page, which cannot encode the progress glyphs
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def _limit(minimum: int):
    """argparse type for a limit that also accepts the word "unlimited" (None).

    These were parsed with a bare int() halfway through main(), so a wrong value
    raised a traceback after the work directory had already been created. "full"
    is a likely thing to type here — it is the word SKILL.md uses as the
    filename's depth label — and argparse answers it with a usage line instead.
    The minimum also retires a falsy-zero trap: --max-pages 0 read as "no limit".
    """
    def parse(v):
        if v == "unlimited":
            return None
        try:
            n = int(v)
        except ValueError:
            raise argparse.ArgumentTypeError(
                f"{v!r} is not a number — pass a whole number or 'unlimited'")
        if n < minimum:
            raise argparse.ArgumentTypeError(
                f"{v!r} is below the minimum of {minimum}")
        return n
    return parse


def parse_args():
    p = argparse.ArgumentParser(description="Convert a website to a document.")
    p.add_argument("--url", required=True)
    p.add_argument("--format", default="docx", choices=["docx", "pdf", "md"])
    p.add_argument("--output", default=None, help="Output file path (required unless --analyze-only)")
    p.add_argument("--depth", type=_limit(0), default=None)
    p.add_argument("--scope", default="same", choices=["same", "subdomains", "custom"])
    p.add_argument("--allowed-domains", nargs="*", default=[])
    p.add_argument("--include-path", nargs="*", default=[],
                   help="Only follow URLs whose path starts with one of these prefixes "
                        "(e.g. /docs/). The start URL is always archived.")
    p.add_argument("--exclude-path", nargs="*", default=[],
                   help="Never follow URLs whose path starts with one of these prefixes. "
                        "Wins over --include-path.")
    p.add_argument("--max-pages", type=_limit(1), default=None)
    p.add_argument("--rate-limit", type=float, default=1.0)
    p.add_argument("--no-images", action="store_true")
    p.add_argument("--analyze-only", action="store_true")
    p.add_argument("--work-dir", default=None)
    p.add_argument(
        "--pages-file",
        default=None,
        help="Path to a JSON file with pre-extracted pages (skips scraping and analysis). "
             "Used when Claude extracts pages via Chrome MCP for JS-heavy sites.",
    )
    args = p.parse_args()
    # A bare "example.com" reaches requests as a scheme-less URL and fails there;
    # the crawl base and the cover page want the full form too
    args.url = args.url.strip()
    if "://" not in args.url:
        args.url = "https://" + args.url
    if not args.output and not args.analyze_only:
        p.error("--output is required (or pass --analyze-only for analysis only)")
    # The pages-file branch builds a document and runs before the analysis, so
    # the two flags together reached it with no --output and raised a TypeError
    # from inside os.path
    if args.pages_file and args.analyze_only:
        p.error("--pages-file builds a document from pages already extracted; "
                "it does not combine with --analyze-only")
    return args


def non_clobbering_path(path: str) -> str:
    """Never overwrite an earlier archive: bump _v2, _v3, … on collision."""
    if not os.path.exists(path):
        return path
    stem, ext = os.path.splitext(path)
    n = 2
    while os.path.exists(f"{stem}_v{n}{ext}"):
        n += 1
    return f"{stem}_v{n}{ext}"


def coverage_path(pages_file: str) -> str:
    """The coverage sidecar that belongs to a pages file.

    Beside it, named after it, so a rebuild finds it without being told and a
    pages file that travelled alone simply has none.
    """
    return os.path.splitext(pages_file)[0] + ".coverage.json"


def read_coverage(pages_file: str):
    """(blocked_domains, robots_excluded) recorded beside a pages file.

    Both empty when there is no sidecar — the Chrome MCP path writes none, and
    has no crawl coverage to record. Hand-edited or half-written is answered the
    same way: an unreadable record of the gaps must not fail the rebuild, which
    is the one thing the pages file is kept for.
    """
    try:
        with open(coverage_path(pages_file), "r", encoding="utf-8") as f:
            data = json.load(f)
        blocked, excluded = data.get("blocked_domains"), data.get("robots_excluded")
        # Shape checked before use, as the pages file's is. `or []` alone let a
        # JSON string through, and sorted("oops") is four one-letter domains in
        # the document's References section.
        if not isinstance(blocked, list) or not isinstance(excluded, list):
            return [], []
        return sorted(str(d) for d in blocked), [str(u) for u in excluded]
    except Exception:
        return [], []


def build_document(fmt, pages, output, source_url, blocked, excluded_listing):
    """Hand the pages to the builder for `fmt`.

    One dispatch, two callers: a fresh crawl and a rebuild from --pages-file. It
    was written out twice, and the rebuild's copy passed neither list — so a
    rebuilt archive said nothing about the pages robots.txt withheld.

    The imports stay inside the branches: python-docx is needed for Word and for
    the LibreOffice PDF path, and asking for Markdown must not require it.
    """
    if fmt == "docx":
        from build_docx import build_docx
        builder = build_docx
    elif fmt == "md":
        from build_md import build_md
        builder = build_md
    elif fmt == "pdf":
        from build_pdf import build_pdf
        builder = build_pdf
    else:
        # argparse's choices already refuse this. Raising rather than falling
        # through to a default keeps a fourth format from silently building the
        # third one when someone adds it to choices and not here.
        raise ValueError(f"unknown format: {fmt}")
    builder(pages, output, source_url, blocked_domains=blocked,
            robots_excluded=excluded_listing)


def cap_listing(urls, limit: int = 50):
    """First `limit` URLs plus a count of the rest, for a list bound for the document.

    A robots.txt that disallows a whole branch excludes thousands of URLs on an
    unlimited-depth crawl, and the reference section prints every one of them.

    The tail line must not open with -, + or *: the Markdown builder writes each
    entry as "- {entry}", and a second marker there nests it into a sublist.
    """
    extra = len(urls) - limit
    return urls[:limit] + ([f"{extra} more not listed"] if extra > 0 else [])


def main():
    args = parse_args()

    # Work dir — created only when something is written to it. --analyze-only and
    # --pages-file both write nothing here, and used to leave an empty temp
    # directory behind on every run
    if not args.analyze_only and not args.pages_file:
        if not args.work_dir:
            # netloc can contain characters that are illegal in directory names (e.g. the port colon)
            domain = re.sub(r"[^A-Za-z0-9._-]", "_", urllib.parse.urlparse(args.url).netloc)
            args.work_dir = tempfile.mkdtemp(prefix=f"w2d_{domain}_")
        os.makedirs(args.work_dir, exist_ok=True)

    # Add src/ to path so sibling modules import correctly
    src_dir = Path(__file__).parent
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    from common import sparse, text_chars
    from crawl import SiteAnalyzer, WebScraper, _asked_delay, effective_delay

    max_depth, max_pages = args.depth, args.max_pages   # None means unlimited

    # ── Header ────────────────────────────────────────────────────────────────
    depth_label = "unlimited" if max_depth is None else str(max_depth)
    pages_label = "unlimited" if max_pages is None else str(max_pages)
    print(f"\n{'═' * 60}", flush=True)
    print(f"  🌐 web-site-to-document", flush=True)
    print(f"{'═' * 60}", flush=True)
    print(f"  URL    : {args.url}", flush=True)
    print(f"  Format : {args.format.upper()}", flush=True)
    print(f"  Depth  : {depth_label}", flush=True)
    print(f"  Scope  : {args.scope}", flush=True)
    print(f"  Pages  : {pages_label}", flush=True)
    print(f"  Images : {'no' if args.no_images else 'yes (embedded)'}", flush=True)
    # build_md keeps the page's own image URLs, so a Markdown run downloads and paces every
    # picture for a document that never reads them. Said, not decided: pages.json is written
    # on every crawl, so the downloads still pay off for a later --pages-file rebuild as
    # Word or PDF, and flipping the default would take that away in silence.
    if args.format == "md" and not args.no_images:
        print("           (Markdown keeps the original image URLs — --no-images costs it "
              "nothing, unless you plan to rebuild these pages as Word or PDF)", flush=True)
    if args.include_path:
        print(f"  Only   : {' '.join(args.include_path)}", flush=True)
    if args.exclude_path:
        print(f"  Except : {' '.join(args.exclude_path)}", flush=True)
    if args.work_dir:
        print(f"  Workdir: {args.work_dir}", flush=True)
    print(f"{'═' * 60}\n", flush=True)

    # Never overwrite: bump _v2, _v3, … if the target file already exists
    # (skipped for --analyze-only: nothing is written there, the message would lie)
    if args.output and not args.analyze_only:
        out = non_clobbering_path(args.output)
        if out != args.output:
            print(f"  ℹ️  {args.output} already exists — writing {out} instead", flush=True)
            args.output = out

    # ── Pre-extracted pages: no analysis, no network. Reached from the Chrome MCP
    # workflow, and from a rebuild of a crawl this script itself called sparse ──
    if args.pages_file:
        print(f"\n📂 Building from pre-extracted pages: {args.pages_file}", flush=True)
        if not os.path.exists(args.pages_file):
            print(f"  ❌ Pages file not found: {args.pages_file}", flush=True)
            sys.exit(1)
        with open(args.pages_file, "r", encoding="utf-8") as f:
            pages = json.load(f)
        # The file is appended to one page at a time, so a half-written or
        # hand-edited one is a real possibility. Without this the wrong shape
        # surfaces as an AttributeError from inside a builder.
        if not isinstance(pages, list) or not all(isinstance(q, dict) for q in pages):
            print("  ❌ Pages file must hold a JSON list of page objects", flush=True)
            sys.exit(1)
        print(f"  ✅ Loaded {len(pages)} pre-extracted pages", flush=True)
        # The gaps the crawl recorded, when this pages file came from one. Capped
        # here as the fresh build caps them, so both documents list the same
        # first 50 and the same count of the rest. Reported in the summary below,
        # in the same two lines the fresh build reports them with.
        blocked, excluded = read_coverage(args.pages_file)
        # Jump directly to document generation
        print(f"\n📄 Phase 3 — Building {args.format.upper()} document", flush=True)
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        build_document(args.format, pages, args.output, args.url,
                       blocked, cap_listing(excluded))
        size_mb = os.path.getsize(args.output) / (1024 * 1024)
        print(f"\n{'═' * 60}", flush=True)
        print(f"  ✅ Document saved: {args.output}", flush=True)
        print(f"  📊 Pages: {len(pages)}  |  Size: {size_mb:.1f} MB", flush=True)
        if blocked:
            print(f"  ⛔ Domains excluded (unreachable): {', '.join(blocked)}", flush=True)
        if excluded:
            print(f"  🤖 Pages excluded by robots.txt: {len(excluded)}", flush=True)
        print(f"{'═' * 60}\n", flush=True)
        return

    # ── Phase 1: Analyze ──────────────────────────────────────────────────────
    print("📊 Phase 1 — Site Analysis", flush=True)
    # The pace reaches Phase 1 too: a sitemap index can fan out to hundreds of
    # fetches, and those were the one requests in the pipeline nothing paced.
    analyzer = SiteAnalyzer(args.url, args.rate_limit)
    # The sitemap is read only where it is used: to report a page count for
    # --analyze-only, and to seed an unlimited-depth crawl. A depth-limited
    # build follows links only, and used to pay up to 200 paced fetches for a
    # list it then ignored — an hour of Phase 1 on a host asking 30s a request.
    read_sitemap = args.analyze_only or max_depth is None
    analysis = analyzer.analyze(read_sitemap=read_sitemap)

    if not analysis["reachable"]:
        # A host that answered and refused is not a host that is down, and
        # SKILL.md sends the agent somewhere different for each: 403 and 429 are
        # bot-protection to work around, unreachable is a stop. Both used to
        # print under "not reachable".
        if analysis.get("status"):
            print(f"  ❌ Site refused the request: HTTP {analysis['status']}", flush=True)
        else:
            print(f"  ❌ Site not reachable: {analysis.get('error', 'Unknown error')}", flush=True)
        sys.exit(1)

    print(f"  ✓ Reachable: {analysis['final_url']}", flush=True)
    # Reachable and yet something to say: the homepage answered but was too
    # large to read, so the JS verdict and the link count below are both zero
    # for a reason the user needs told rather than left to infer.
    if analysis.get("error"):
        print(f"  ⚠️  {analysis['error']}", flush=True)
    print(f"  ✓ Type    : {'JavaScript-rendered ⚠️' if analysis['js_rendered'] else 'Static HTML'}", flush=True)
    print(f"  ✓ Robots  : {'found' if analysis['has_robots'] else 'not found'}", flush=True)
    if read_sitemap:
        print(f"  ✓ Sitemap : {'found' if analysis['has_sitemap'] else 'not found'}", flush=True)
    else:
        print("  ✓ Sitemap : not read — a depth-limited run follows links only", flush=True)

    # A Crawl-delay decides how long the whole run takes, so it belongs with the
    # other Phase 1 facts — not in a progress line the user only reads once the
    # crawl is already under way. WebScraper enforces it; this only reports it.
    asked_delay = _asked_delay(analysis.get("_rp"))
    if asked_delay > args.rate_limit:
        pace = effective_delay(analysis.get("_rp"), args.rate_limit)
        print(f"  ✓ Pace    : {pace:g}s between requests "
              f"(robots.txt asks for {asked_delay:g}s)", flush=True)

    if analysis["js_rendered"]:
        print(
            "\n  ⚠️  WARNING: This site appears to use JavaScript rendering.\n"
            "     Static scraping may capture incomplete content.\n"
            "     For full fidelity on JS-heavy sites, consider using\n"
            "     browser-based extraction (Claude in Chrome).\n",
            flush=True,
        )

    if analysis["sitemap_page_count"]:
        print(f"  ✓ Sitemap pages found: {analysis['sitemap_page_count']}", flush=True)
    # A floor, not a total: what the homepage links to within scope. On a site
    # with no sitemap it is the only page figure the analysis can honestly give.
    print(f"  ✓ In-scope links on the homepage: {analysis['homepage_links']}", flush=True)

    if args.analyze_only:
        print("\n✅ Analysis complete (--analyze-only mode). No scraping performed.", flush=True)
        # sitemap_urls stays out: up to 5000 URLs would flood the conversation context
        summary = {k: v for k, v in analysis.items() if not k.startswith("_") and k != "sitemap_urls"}
        print(json.dumps(summary, indent=2))
        return

    # ── Phase 2: Scrape ───────────────────────────────────────────────────────
    print(f"\n🕷️  Phase 2 — Scraping", flush=True)

    # Crawl from where the site actually answers, not from what the user typed.
    # An apex that redirects to another host (angular.io → angular.dev) would
    # otherwise scope the crawl to the host it just left: the start page is
    # archived, every link on it is judged out of scope, and the run yields a
    # one-page document while Phase 1 reports dozens of in-scope links. It also
    # keeps the analyzer's robots.txt filed under the host it was fetched from.
    crawl_base = analysis["final_url"]
    if urllib.parse.urlparse(crawl_base).netloc != urllib.parse.urlparse(args.url).netloc:
        print(f"  ↪️  Redirected to {crawl_base} — crawling that address", flush=True)

    scraper = WebScraper(
        base_url=crawl_base,
        scope=args.scope,
        allowed_domains=args.allowed_domains,
        max_depth=max_depth,
        max_pages=max_pages,
        rate_limit=args.rate_limit,
        embed_images=not args.no_images,
        work_dir=args.work_dir,
        robots=analysis.get("_rp"),
        js_rendered=analysis["js_rendered"],
        include_paths=args.include_path,
        exclude_paths=args.exclude_path,
    )

    sitemap_urls = analysis.get("sitemap_urls", []) if analysis["has_sitemap"] else None
    pages = scraper.scrape(sitemap_urls=sitemap_urls)

    if not pages:
        print("\n❌ No pages could be scraped. Exiting.", flush=True)
        sys.exit(1)

    print(f"\n  ✅ Scraped {len(pages)} pages ({scraper.total_errors} errors total)", flush=True)

    # ── Content quality check ─────────────────────────────────────────────────
    # The crawl stops itself once its first pages come out near-empty, so this
    # both reports that stop and catches a site that thins out later on. Same
    # question as the one the crawl asked, so it gets the same answer — the
    # average below is only for the message.
    avg_chars_per_page = sum(
        text_chars(p.get("content", [])) for p in pages) / max(len(pages), 1)

    # The pages as extracted, for a rebuild with --pages-file or for debugging.
    # Written before the sparse check, because a refused build is when that file
    # matters most. One write, not one per branch: the success branch used to
    # drop the image base64 by filtering the key "data", which is also what a
    # table block calls its rows, so every table came back empty from a rebuild.
    pages_json_path = os.path.join(args.work_dir, "pages.json")
    with open(pages_json_path, "w", encoding="utf-8") as f:
        json.dump(pages, f, ensure_ascii=False, indent=2)

    # What the crawl could not reach, beside the pages it did. A rebuild used to
    # drop both lists, so its References section said nothing about the gaps and
    # a reader months later could not tell a withheld page from one that never
    # existed — the very thing recording them was for. A sidecar rather than a
    # key in pages.json: that file is a list of pages, and chrome_extract.py
    # appends to it one page at a time.
    with open(coverage_path(pages_json_path), "w", encoding="utf-8") as f:
        json.dump({"blocked_domains": sorted(scraper.blocked_domains),
                   "robots_excluded": scraper.robots_excluded}, f,
                  ensure_ascii=False, indent=2)

    if sparse(pages):
        print(f"\n{'⚠' * 60}", flush=True)
        print(f"  ⚠️  SPARSE CONTENT WARNING", flush=True)
        print(f"  Average extracted text per page: {avg_chars_per_page:.0f} characters", flush=True)
        print(f"  This site likely uses JavaScript to render its content.", flush=True)
        print(f"  The document was NOT built.", flush=True)
        print(f"", flush=True)
        print(f"  💡 The extracted pages were saved to: {pages_json_path}", flush=True)
        print(f"     - For full content, re-extract via Chrome MCP", flush=True)
        print(f"       (references/chrome-mcp-extraction.md), then build with --pages-file.", flush=True)
        print(f"     - To keep the sparse result anyway, re-run this script with", flush=True)
        print(f"       --pages-file \"{pages_json_path}\".", flush=True)
        print(f"{'⚠' * 60}\n", flush=True)
        return

    # ── Phase 3: Build document ────────────────────────────────────────────────
    print(f"\n📄 Phase 3 — Building {args.format.upper()} document", flush=True)

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)

    blocked = sorted(scraper.blocked_domains)
    excluded = scraper.robots_excluded
    # ponytail: capped in the orchestrator, at build_document — the one point
    # all three builders converge on, for both the fresh and the rebuild path. A
    # caller importing a builder directly bypasses the cap.
    build_document(args.format, pages, args.output, args.url,
                   blocked, cap_listing(excluded))

    size_mb = os.path.getsize(args.output) / (1024 * 1024)
    print(f"\n{'═' * 60}", flush=True)
    print(f"  ✅ Document saved: {args.output}", flush=True)
    print(f"  📊 Pages: {len(pages)}  |  Size: {size_mb:.1f} MB", flush=True)
    if blocked:
        print(f"  ⛔ Domains excluded (unreachable): {', '.join(blocked)}", flush=True)
    if excluded:
        print(f"  🤖 Pages excluded by robots.txt: {len(excluded)}", flush=True)
    print(f"{'═' * 60}\n", flush=True)


if __name__ == "__main__":
    main()
