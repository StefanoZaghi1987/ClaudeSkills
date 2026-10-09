#!/usr/bin/env python3
"""
extract.py — HTML to structured content for web-site-to-document skill.
Turns one fetched page into content blocks (headings, paragraphs, lists,
tables, code, images) and downloads the images those blocks reference.
"""

import hashlib
import os
import re
import time
import urllib.parse
from typing import Any, Dict, List, Optional, Union

import requests
from bs4 import BeautifulSoup, NavigableString, Tag
from bs4.element import Comment, Doctype, ProcessingInstruction

from common import (BINARY_EXTENSIONS, MAX_IMAGE_BYTES, _parse_link,
                    host_is_internal, read_capped)

# NavigableString subclasses that are markup plumbing, not page text
NON_TEXT_NODES = (Comment, Doctype, ProcessingInstruction)

# <br> marker. A raw newline here would be indistinguishable from the newlines
# the HTML source is merely indented with, and _tidy has to collapse those.
BR = "\x00"


def _tidy(text: str) -> str:
    """Collapse HTML source whitespace, keeping only the breaks <br> asked for."""
    return "\n".join(" ".join(seg.split()) for seg in text.split(BR)).strip()


def _marked(mark: str, inner: str) -> str:
    """Wrap inner in a markdown marker, whitespace and empties excepted.

    Icon fonts are empty inline elements: five <i class="icon-star"></i> in a
    row are five empty italics, and marking those prints "** ** ** ** **" into
    the document where the page shows a star rating.

    The marker also has to hug the text. Pretty-printed HTML puts newlines
    inside the tag, and "** bold **" is literal asterisks in Markdown, not
    emphasis — so the surrounding whitespace stays outside the marker.
    """
    core = inner.strip()
    if not core:
        return inner
    lead = inner[: len(inner) - len(inner.lstrip())]
    trail = inner[len(inner.rstrip()):]
    return f"{lead}{mark}{core}{mark}{trail}"


# type/subtype in the token charset RFC 2045 allows, and nothing besides. The
# Content-Type header is the site's to write, and this value is stored in
# pages.json and interpolated into an HTML attribute by the PDF builder, so
# "image/" as the whole of the check let `image/png" onload="…` through and it
# broke straight out of that attribute. Real types all pass: image/svg+xml,
# image/vnd.microsoft.icon, image/x-icon.
# re.ASCII, because \w is Unicode-aware by default and a MIME type is not.
MIME_RE = re.compile(r"[\w.+-]+/[\w.+-]+", re.ASCII)


# How many hops a picture may be chased through. A real CDN redirects once or
# twice; past this it is not a picture worth following.
MAX_IMAGE_REDIRECTS = 5
# The statuses requests itself follows. Named here rather than read off the
# response as .is_redirect, so the hop test rests on the status line the server
# actually sent rather than on a property only requests' own class carries.
REDIRECT_STATUSES = (301, 302, 303, 307, 308)


# A colspan is page-authored, so it is untrusted: one cell claiming 99999
# columns would otherwise decide how wide the row — and the Word table built
# from it — becomes. No real table is cut short by this.
MAX_TABLE_COLUMNS = 256


def _span(cell, attr: str) -> int:
    """A colspan or rowspan as a usable count. Anything unreadable is 1.

    "0" is legal markup — HTML 4 read it as "to the end of the group" and
    HTML 5 dropped it — and arrives here from real pages either way.
    """
    try:
        n = int(cell.get(attr, 1))
    except (TypeError, ValueError):
        return 1
    return max(1, min(n, MAX_TABLE_COLUMNS))


# CSS selectors for the main content area (tried in order)
CONTENT_SELECTORS = [
    "main", "article", '[role="main"]', '[role="article"]',
    ".content", ".main-content", ".documentation", ".doc-content",
    ".page-content", ".article-content", "#content", "#main",
    ".markdown-body", ".prose", ".rst-content", ".body-content",
    '[class*="content"]', '[class*="article"]',
]

# Removed on sight: markup that is never page content, whatever it holds.
STRUCTURAL_NOISE = [
    # <template> is inert by specification: no browser renders what it holds, so
    # its row blueprints and {{placeholders}} were archived as text the page
    # never showed. Proof, not a hint — unlike a hidden element, which an
    # accordion or a tab panel opens on click and whose content a reader wants.
    "nav", "script", "style", "noscript", "iframe", "template",
    # controls and icons: their labels are UI, not content, and bare-text
    # capture would otherwise emit them as paragraphs
    "button", "select", "svg",
]

# One definition, two consumers: _breadcrumb harvests it into the page's own
# breadcrumb field, and the noise pass below removes it from the content so it is
# not printed twice.
BREADCRUMB_SELECTOR = ('[aria-label="breadcrumb"], [class*="breadcrumb"], '
                       'nav[class*="bread"]')

# Also removed on sight: words whose only meaning is page furniture. A breadcrumb
# is a breadcrumb, and the extractor keeps it as a page field of its own anyway,
# so dropping it from the content loses nothing. "toc" is three letters, and a
# bare [class*="toc"] matches it inside "protocol-spec" and "in-stock", so these
# stay word-bounded — the pattern is what makes the word single-meaning here.
SINGLE_MEANING_NOISE = [
    BREADCRUMB_SELECTOR,
    '[class~="toc"]', '[class*="toc-"]', '[class*="-toc"]',
    '[class*="toc_"]', '[class*="_toc"]', '[class*="table-of-contents"]',
    '[id~="toc"]', '[id*="toc-"]', '[id*="-toc"]',
    '[id*="toc_"]', '[id*="_toc"]',
]

# Removed only when the element also reads like page furniture — see _is_chrome.
# For these words a class or an id is a hint, not proof: "lunch-menu",
# "banner-specs", "announcements-archive", "navigation-api-reference" and
# id="naval-architecture" are all page content. No pattern can separate them,
# because "page-toc" and "lunch-menu" are the same string shape.
LEXICAL_NOISE = [
    '[class*="navigation"]', '[class*="sidebar"]', '[class*="menu"]',
    '[id*="sidebar"]', '[id*="nav"]',
    '[class*="cookie"]', '[class*="banner"]', '[class*="announce"]',
]

# ponytail: one calibration knob, measured rather than derived. A documentation
# sidebar, a breadcrumb and a page header all read ~1.0; a prose block with a few
# inline links reads ~0.15. The separation is wide, so move this only for a real
# page that lands between. Length is deliberately not a second signal: a short
# block of prose and a short cookie bar are the same length, so testing it put
# every one-line content block back in the bin this guard exists to keep it out of.
NOISE_LINK_DENSITY = 0.5


def _removable(el) -> bool:
    """False for anything a noise selector must not take out of a sentence.

    A noise selector names a block of page furniture, never an inline fragment
    inside content. `<h2><a class="toc-backref">Introduction</a></h2>` is what
    docutils writes for every section heading it can link back to, and
    [class*="toc-"] matched that anchor: the heading came out empty, so _walk
    emitted nothing and PEP 8 reached the archive without a single one of its
    42 section titles. Removing an inline element does not remove furniture, it
    corrupts the sentence around it.
    """
    return not el.decomposed and el.name not in INLINE_TAGS


def _is_chrome(el) -> bool:
    """True when a lexically-matched element reads like page furniture.

    Navigation is mostly link text; prose is not. Structure is the only thing
    that separates them, because the class name cannot: "page-toc" and
    "lunch-menu" are the same string shape.

    A consent bar or an announcement strip is prose with few links, so it can
    survive this test. That is the accepted cost: such a strip is what the page
    showed on the day it was archived, and it usually sits outside the content
    area anyway, where these selectors never reach it. Deleting a page's real
    text is the failure worth avoiding.
    """
    text = el.get_text(strip=True)
    if not text:
        return True
    linked = sum(len(a.get_text(strip=True)) for a in el.find_all("a"))
    return linked / len(text) >= NOISE_LINK_DENSITY

# Lazy-loading attributes, in the order sites fall back through them. An
# <img> whose src a script fills in later has none of the real address in
# src, and without these the picture leaves no block at all — not even a
# placeholder naming what went missing.
LAZY_SRC_ATTRS = ("src", "data-src", "data-original", "data-lazy-src")
LAZY_SRCSET_ATTRS = ("srcset", "data-srcset")

# Inline-level tags: a contiguous run of these (with bare text) inside a
# container is one paragraph, not one paragraph per fragment
INLINE_TAGS = {
    "a", "span", "strong", "b", "em", "i", "code", "br", "img",
    "small", "u", "sub", "sup", "mark", "cite", "q", "kbd", "abbr",
    "time", "label", "s", "samp", "var", "data", "bdi", "output",
    "font", "big", "tt",
}


# ─── Image Handler ────────────────────────────────────────────────────────────

class ImageHandler:
    """Downloads images to the work directory for document embedding."""

    def __init__(self, session: requests.Session, images_dir: str,
                 rate_limit: float = 0.0, allow_internal: bool = False):
        self.session = session
        self.images_dir = images_dir
        # Whether a picture may come from this machine's own network. False for
        # a public site, whose pages must not aim the download at 127.0.0.1 or
        # 169.254.169.254; True when the archived site is itself on such an
        # address, because a docs server on localhost keeps its own pictures.
        self.allow_internal = allow_internal
        # The crawl's pace applies here too. Images are most of the requests a
        # picture-heavy site receives, so leaving them unthrottled meant the one
        # politeness control the skill offers barely reached the traffic it was
        # meant to pace — measured at 12 image requests in 0.056s from one page.
        self.rate_limit = rate_limit
        os.makedirs(images_dir, exist_ok=True)
        self._cache: Dict[str, Optional[Dict]] = {}

    def _refused(self, url: str) -> bool:
        """True when this address is outside the crawl's trust zone.

        Asked of every hop, not only of the address the page named. requests
        follows a redirect by default, so one check before the request is a
        302 away from useless: any host a page links could hand the download
        on to 169.254.169.254, and the guard would never see that address.
        """
        if self.allow_internal:
            return False
        if not host_is_internal(urllib.parse.urlparse(url).hostname or ""):
            return False
        print(f"    ⏭️  Image on an internal address, skipped: {url}", flush=True)
        return True

    def _get(self, url: str):
        """The response for an image address, redirects walked one hop at a time.

        allow_redirects=False, because the guard has to run *between* the hops:
        letting requests follow them means the request has already reached the
        internal address by the time the final URL comes back to be checked.
        Refusing the picture is the whole answer — None, like any other skip.
        """
        for _ in range(MAX_IMAGE_REDIRECTS + 1):
            if self._refused(url):
                return None
            resp = self.session.get(url, timeout=10, stream=True,
                                    allow_redirects=False)
            if resp.status_code not in REDIRECT_STATUSES:
                return resp
            location = resp.headers.get("location", "")
            resp.close()
            if not location:
                return None
            url = urllib.parse.urljoin(url, location)
        return None

    def fetch(self, img_url: str, base_url: str) -> Optional[Dict[str, str]]:
        """Return {'mime_type': str, 'path': str} or None."""
        try:
            img_url = urllib.parse.urljoin(base_url, img_url)
        except Exception:
            return None

        if img_url in self._cache:
            return self._cache[img_url]

        try:
            resp = self._get(img_url)
            # close() on every skip path: stream=True never reads the body,
            # so without it the connection waits for the garbage collector
            if resp is None or resp.status_code != 200:
                if resp is not None:
                    resp.close()
                self._cache[img_url] = None
                return None

            mime = resp.headers.get("content-type", "image/png").split(";")[0].strip()
            if not mime.startswith("image/") or not MIME_RE.fullmatch(mime):
                resp.close()
                self._cache[img_url] = None
                return None

            # Trust Content-Length when present: skip the download itself,
            # not just the embedding, for oversized images
            cl = resp.headers.get("content-length")
            if cl and cl.isdigit() and int(cl) > MAX_IMAGE_BYTES:
                resp.close()
                print(f"    ⚠ Image too large (>{MAX_IMAGE_BYTES//1024//1024}MB), skipped: {img_url}", flush=True)
                self._cache[img_url] = None
                return None

            # Read to the cap, not past it: a Content-Length is optional, and
            # without one the remote server would decide this run's memory use
            content = read_capped(resp, MAX_IMAGE_BYTES)
            if content is None:
                print(f"    ⚠ Image too large (>{MAX_IMAGE_BYTES//1024//1024}MB), skipped: {img_url}", flush=True)
                self._cache[img_url] = None
                return None

            key = hashlib.md5(img_url.encode()).hexdigest()[:12]
            ext = mime.split("/")[-1].replace("jpeg", "jpg").replace("svg+xml", "svg")
            filepath = os.path.join(self.images_dir, f"{key}.{ext}")
            with open(filepath, "wb") as f:
                f.write(content)

            # The file just written is the only copy. The block used to carry
            # the base64 as well, which held every picture of the crawl in memory
            # at 1.33x its bytes — for a run whose page count is unlimited by
            # default — and left main.py stripping it back out of pages.json.
            # common.image_bytes reads the file for whichever builder asks.
            result = {"mime_type": mime, "path": filepath}
            self._cache[img_url] = result
            return result

        except Exception:
            self._cache[img_url] = None
            return None

        finally:
            # Every network attempt, failures included — a host answering 403 or
            # 429 must not be hit at full speed either. The cache check above
            # returns before this, so a repeated image costs nothing.
            if self.rate_limit > 0:
                time.sleep(self.rate_limit)


# ─── Page Content Extractor ───────────────────────────────────────────────────

class PageExtractor:
    """Converts raw HTML into a structured content dict."""

    def __init__(self, image_handler: Optional[ImageHandler] = None):
        self.image_handler = image_handler

    def extract(self, html: Union[str, bytes], url: str) -> Dict[str, Any]:
        # bytes input lets BeautifulSoup honor the page's <meta charset> itself:
        # when the server declares no charset, resp.text mis-decodes UTF-8 as
        # latin-1 and non-ASCII text comes out mojibake
        soup = BeautifulSoup(html, "lxml")

        # Every relative address on the page resolves against <base href>, not
        # against the page's own address, whenever the page declares one. A
        # framework app ships one by default (`ng new` writes <base href="/">),
        # and rendered app HTML still carries it into the Chrome MCP path, so
        # joining on `url` there sent every link and every picture to an address
        # that does not exist — a whole site of crawl errors and placeholders.
        # `url` itself stays the page's identity: only the join base moves.
        join_base = url
        base_tag = soup.find("base", href=True)
        if base_tag:
            join_base = urllib.parse.urljoin(url, base_tag["href"].strip())

        # Breadcrumb
        breadcrumb = self._breadcrumb(soup)

        # Discovery links come from the whole page, navigation included — the
        # site's own nav tree is the depth-limited discovery mechanism. Content
        # extraction below still reads only the noise-stripped main area.
        # Whole page, not just the content area: sidebars and menus live outside
        # it, and _walk early-returns on headings, tables, and code.
        links: List[str] = []
        binary_refs: List[Dict] = []
        for a in (soup.body or soup).find_all("a"):
            self._collect_link(a.get("href", ""), join_base, links, binary_refs)

        # Find main content area, strip noise
        area = self._find_content_area(soup)

        # A "link to this place" permalink is furniture, whatever the generator
        # calls it: Sphinx writes ¶, MkDocs-Material a Font-Awesome glyph Word
        # prints as an empty box, VitePress and Docusaurus a zero-width space. The
        # class names disagree (headerlink, hash-link, anchor) and the placement
        # disagrees too — Sphinx hangs one off every heading, every <dt> API entry
        # and every figure caption — so neither a class nor a tag list is the
        # target. The structural property is: a link to a fragment of this same
        # page, carrying no word character, points *at* something rather than
        # saying anything. Measured live, ¶ sat on all 225 headings of one Django
        # settings page and on all 68 built-in functions of one CPython page.
        #
        # Two guards keep the removal from taking content with it. An anchor around
        # an <img> reads as empty text and is a picture, not a permalink. And
        # _removable does not gate this, deliberately: it refuses inline tags so a
        # noise selector can never take a fragment out of a sentence, whereas here
        # the no-word-character test is what makes removal safe, because it cannot
        # delete a word. Docutils wraps its toc-backref around the heading's own
        # words, so that anchor is full of them and never matches.
        for a in area.find_all("a", href=True):
            if (a["href"].startswith("#") and not a.find("img")
                    and not re.search(r"\w", a.get_text())):
                a.decompose()

        # The page's own <h1> as it stands before the noise pass below runs.
        # MediaWiki puts it inside the page <header>, which is furniture on every
        # other site, so the pass removes it there. Used only as a title candidate,
        # and only when <title> corroborates it.
        early = area.find("h1")
        early_h1 = " ".join(early.get_text().split()) if early else ""

        for sel in STRUCTURAL_NOISE + SINGLE_MEANING_NOISE:
            for el in area.select(sel):
                if _removable(el):
                    el.decompose()
        # A page's <header> is its logo and menu; an <article>'s own <header>
        # holds that article's title, byline and date. The parent tells the two
        # apart exactly, so this needs no heuristic — and the site header on a
        # page with no <main> reaches here, where it used to be dropped blind.
        for el in area.select("header, footer"):
            if _removable(el) and el.find_parent("article") is None:
                el.decompose()
        for sel in LEXICAL_NOISE:
            for el in area.select(sel):
                # _removable also covers the snapshot select() hands back: a
                # parent and a child can both match one selector, and an element
                # an earlier decompose already took now reads empty, which
                # _is_chrome would take for furniture
                if _removable(el) and _is_chrome(el):
                    el.decompose()

        # Title: the <h1> left in the *cleaned* content area, else <title>.
        # After noise removal on purpose — the whole document's first <h1> is
        # often the site name in the page header, which would title every page
        # of the site identically and throw the real per-page <title> away.
        # " ".join(…split()) collapses whitespace; get_text(strip=True) would glue
        # words split by nested tags ("Docs <a>index</a>" → "Docsindex")
        h1 = area.find("h1")
        if h1:
            title = " ".join(h1.get_text().split())
        else:
            title = " ".join(soup.title.get_text().split()) if soup.title else ""
            # A page header holding the page's own <h1> was dropped as furniture
            # just above, leaving <title> with the site name still on it: every
            # MediaWiki page read "Python (programming language) - Wikipedia".
            # That h1 wins only when <title> opens with it, so the page's own
            # heading proves where the real title ends and nothing is guessed.
            # Round 7 rejected guessing a separator, and that still holds.
            #
            # Opening the title is not enough on its own, though, because a site
            # name opens one too: "ACME Docs | Install guide" against an <h1>
            # logo reading "ACME Docs" titled every page of the site "ACME Docs",
            # and its whole table of contents said that N times. So the h1 has to
            # be more than half of the title — the page's own name against a site
            # name suffix, rather than the other way round.
            #
            # The cost, accepted: a short page name under a long site name stays
            # whole, so <h1>Go</h1> keeps "Go - Wikipedia". Nothing on one page
            # separates that from the ACME shape — the remainder is a separator
            # and words either way, and length is the only thing that differs at
            # all. Comparing the h1 against the domain label does separate them,
            # and was rejected: it fails for every site whose name is not its
            # domain. A verbose title is per-page distinct, which is the failure
            # worth having; the same title on every page is not.
            if early_h1 and title.startswith(early_h1) and len(early_h1) * 2 > len(title):
                title = early_h1

        # Extract structured blocks
        content: List[Dict] = []
        # The title renders as the section header in every builder; drop the h1
        # it came from so it is not printed twice. Anchors inside it were already
        # collected above.
        if h1 is not None:
            h1.decompose()
        self._walk(area, content, join_base)

        return {
            "url": url,
            "title": title,
            "breadcrumb": breadcrumb,
            "content": content,
            "links": list(dict.fromkeys(links)),   # dedup, preserve order
            "binary_references": binary_refs,
        }

    def _find_content_area(self, soup: BeautifulSoup) -> Tag:
        for sel in CONTENT_SELECTORS:
            el = soup.select_one(sel)
            if el and len(el.get_text(strip=True)) > 80:
                return el
        return soup.body or soup

    def _breadcrumb(self, soup: BeautifulSoup) -> List[str]:
        crumbs = []
        bc = soup.select_one(BREADCRUMB_SELECTOR)
        if bc:
            for item in bc.find_all(["a", "span", "li"]):
                text = item.get_text(strip=True)
                if text and text not in crumbs:
                    crumbs.append(text)
        return crumbs

    def _walk(self, el, content, base_url):
        if isinstance(el, NavigableString):
            return
        tag = el.name
        if not tag:
            return

        # ── Headings ──────────────────────────────────────────────────────────
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            text = " ".join(el.get_text().split())
            if text:
                content.append({"type": "heading", "level": int(tag[1]), "text": text})
            return

        # ── Pre / code blocks ─────────────────────────────────────────────────
        if tag == "pre":
            inner = el.find("code") or el
            code_text = inner.get_text()
            lang = ""
            for cls in (inner.get("class") or []):
                if "language-" in cls:
                    lang = cls.replace("language-", "")
                elif "lang-" in cls:
                    lang = cls.replace("lang-", "")
            # An empty <pre> prints as an empty grey box in Word and PDF and as
            # an empty fence in Markdown — furniture the page never showed
            if code_text.strip():
                content.append({"type": "code", "text": code_text,
                                "language": lang})
            return

        # ── Images ────────────────────────────────────────────────────────────
        if tag == "img":
            block = self._image_block(el, base_url)
            if block:
                content.append(block)
            return

        # ── Tables ────────────────────────────────────────────────────────────
        if tag == "table":
            # A nested table is a block of its own. Left in place, find_all("tr")
            # would emit its rows a second time and get_text() would glue its
            # text into the enclosing cell ("outer" + "inner" → "outerinner").
            # find_parent("table") is el detaches only the directly-nested ones,
            # so a table three deep is reached by the recursive pass below.
            nested = [t.extract() for t in el.find_all("table")
                      if t.find_parent("table") is el]
            pending_imgs: List[Dict] = []
            # A <caption> is the table's title — "Table 3: Torque values in Nm"
            # is what tells a reader which table this is — and it reached no
            # block at all, because this branch reads <tr> and then returns.
            # Above the table, where the page shows it, and as a paragraph:
            # every builder renders one already, so a block type of its own
            # would be three new branches for a line of text.
            # recursive=False: a <caption> is a direct child of its table, so
            # searching the subtree would walk every cell of every table that
            # has none, and could pick one up from a malformed cell.
            cap = el.find("caption", recursive=False)
            cap_text = _tidy(self._inline_text(cap, pending_imgs, base_url)) if cap else ""
            rows = self._table_rows(el, pending_imgs, base_url)
            if cap_text:
                content.append({"type": "paragraph", "text": cap_text})
            if rows:
                content.append({"type": "table", "data": rows})
            content.extend(pending_imgs)
            for sub in nested:
                self._walk(sub, content, base_url)
            return

        # ── Lists ─────────────────────────────────────────────────────────────
        if tag in ("ul", "ol"):
            self._walk_list(el, content, base_url)
            return

        # ── Blockquotes / callouts ────────────────────────────────────────────
        if tag == "blockquote":
            text = " ".join(el.get_text().split())
            if text:
                content.append({"type": "callout", "text": text})
            return

        # ── Paragraphs ────────────────────────────────────────────────────────
        if tag == "p":
            pending_imgs = []
            text = _tidy(self._inline_text(el, pending_imgs, base_url))
            if text:
                content.append({"type": "paragraph", "text": text})
            content.extend(pending_imgs)
            return

        # ── Recurse into containers ───────────────────────────────────────────
        # Bare text and inline tags directly under a container (no <p> wrapper,
        # <dl>/<figcaption> content) are real content: each contiguous run is
        # emitted as one paragraph, in document order, around the block children
        run: List[Any] = []
        for child in el.children:
            if isinstance(child, NON_TEXT_NODES):
                continue
            if isinstance(child, NavigableString) or child.name in INLINE_TAGS:
                run.append(child)
            else:
                self._flush_inline(run, content, base_url)
                run = []
                self._walk(child, content, base_url)
        self._flush_inline(run, content, base_url)

    def _table_rows(self, el, pending, base_url) -> List[List[str]]:
        """A table as a rectangular grid, colspan and rowspan honoured.

        Reading the cells of each <tr> in order is only right for a table with
        no merged cells. A colspan header is one cell above two body cells, so
        every value to its right moves one column left; a rowspan row label is
        written once and missing from the rows below, which shifts those rows
        the same way. Measured: "Val" landed over "b", and "c" under the "Spec"
        heading. That is worse than losing the table — the numbers arrive under
        the wrong headings and the document says nothing about it.

        ponytail: a merged cell repeats its text in every position it covers,
        rather than the block format carrying the span. A reader of the flat
        document sees what a reader of the page sees, and Word shows "Zodiac"
        three times where the page merged one cell down three rows — give the
        block a span field, and every builder a merge call, if that shows.
        """
        rows: List[List[str]] = []
        # column → [text, rows it still has to fill] for a cell spanning down
        carry: Dict[int, List] = {}
        for tr in el.find_all("tr"):
            cells = iter(tr.find_all(["th", "td"]))
            row: List[str] = []
            ci = 0
            while len(row) < MAX_TABLE_COLUMNS:
                held = carry.get(ci)
                if held:
                    row.append(held[0])
                    held[1] -= 1
                    if held[1] <= 0:
                        del carry[ci]
                    ci += 1
                    continue
                cell = next(cells, None)
                if cell is None:
                    # This row ran out of its own cells while a cell spanning
                    # down is still pending further right. Padding to reach it
                    # is what keeps that value in the row it belongs to: the
                    # bare break lost it, and left the carry to be spent by a
                    # row further down that the cell never covered.
                    if not any(c >= ci for c in carry):
                        break
                    row.append("")
                    ci += 1
                    continue
                text = _tidy(self._inline_text(cell, pending, base_url))
                down = _span(cell, "rowspan") - 1
                for _ in range(_span(cell, "colspan")):
                    if len(row) >= MAX_TABLE_COLUMNS:
                        break
                    row.append(text)
                    if down:
                        carry[ci] = [text, down]
                    ci += 1
            if row:
                rows.append(row)
        return rows

    def _walk_list(self, el, content: List[Dict], base_url: str, level: int = 0):
        """Emit one list block per nesting level, in document order.

        A sublist becomes a block of its own carrying `level`, placed straight
        after the items it hangs from, so the flat block format still expresses
        the nesting. `start` keeps an ordered list numbering across the split.
        ponytail: block children of an <li> other than a list (a <pre>, a
        <table>) still flatten into the item's text — give them their own blocks
        if a site turns up that needs it
        """
        ordered = el.name == "ol"
        items: List[str] = []
        pending_imgs: List[Dict] = []
        start = 0

        def flush():
            nonlocal start
            if items:
                content.append({"type": "list", "ordered": ordered, "level": level,
                                "start": start, "items": list(items)})
                start += len(items)
                items.clear()
            content.extend(pending_imgs)
            pending_imgs.clear()

        for li in el.find_all("li", recursive=False):
            # extract() first: a sublist is a block of its own, never part of the
            # parent item's text
            sublists = [s.extract() for s in li.find_all(["ul", "ol"], recursive=False)]
            text = _tidy(self._inline_text(li, pending_imgs, base_url))
            if text:
                items.append(text)
            if sublists:
                flush()
                for sub in sublists:
                    self._walk_list(sub, content, base_url, level + 1)
        flush()

    def _flush_inline(self, run: List[Any], content: List[Dict], base_url: str):
        """Emit one paragraph from a run of bare text and inline tags."""
        if not run:
            return
        pending_imgs: List[Dict] = []
        text = _tidy("".join(self._inline_node(n, pending_imgs, base_url) for n in run))
        if text:
            content.append({"type": "paragraph", "text": text})
        content.extend(pending_imgs)

    def _image_block(self, el, base_url) -> Optional[Dict]:
        src = next((el.get(a, "").strip() for a in LAZY_SRC_ATTRS
                    if el.get(a, "").strip()), "")
        if not src:
            # "/a-480.png 480w, /a-960.png 960w" → the first candidate's URL
            srcset = next((el.get(a, "").strip() for a in LAZY_SRCSET_ATTRS
                           if el.get(a, "").strip()), "")
            src = srcset.split(",")[0].strip().split(" ")[0] if srcset else ""
        if not src or src.startswith("data:"):
            return None
        alt = el.get("alt", "")
        abs_src = urllib.parse.urljoin(base_url, src)
        img_data = self.image_handler.fetch(src, base_url) if self.image_handler else None
        return {
            "type": "image",
            "src": abs_src,
            "alt": alt,
            "mime_type": img_data["mime_type"] if img_data else None,
            "path": img_data["path"] if img_data else None,
        }

    def _inline_node(self, node, pending, base_url) -> str:
        """One node of an inline run as text, carrying its markdown marker.

        The single inline path: _inline_text walks an element's children through
        it, _flush_inline walks a run of siblings through it. One implementation,
        so a marker cannot survive on one path and vanish on the other.
        """
        if isinstance(node, NON_TEXT_NODES):
            return ""
        if isinstance(node, NavigableString):
            return str(node)
        name = node.name
        if name == "a":
            return self._link_text(node, pending, base_url)
        if name in ("strong", "b"):
            return _marked("**", self._inline_text(node, pending, base_url))
        if name in ("em", "i"):
            return _marked("*", self._inline_text(node, pending, base_url))
        if name == "code":
            return _marked("`", node.get_text())
        if name == "br":
            return BR
        if name == "img":
            # Buffered so the image block lands after the text block it belongs to
            block = self._image_block(node, base_url)
            if block:
                pending.append(block)
            return ""
        if name in INLINE_TAGS:
            return self._inline_text(node, pending, base_url)
        # A block child is a word boundary, inside and around it: without the
        # padding "<li><p>one</p><p>and two</p></li>" came out as "oneand two".
        # _tidy collapses the padding again. Recursing rather than reading
        # get_text() keeps the block's own markers and its <img> descendants,
        # which get_text() leaves behind — every branch above recurses too,
        # except <code>, so an <img> inside a code span leaves no block.
        return " " + self._inline_text(node, pending, base_url) + " "

    def _inline_text(self, el, pending, base_url) -> str:
        return "".join(self._inline_node(c, pending, base_url) for c in el.children)

    def _link_text(self, el, pending, base_url) -> str:
        """An anchor as `[label](url)`, so the link survives into the document.

        Markdown, because that is the format the block text already carries
        (**bold**, `code`) and every builder already parses. Plain label
        whenever the markdown form would be ambiguous — a bracket in the label
        or a parenthesis in the URL closes the link early, and a mangled link
        reads worse than none.
        """
        label = self._inline_text(el, pending, base_url)
        href = el.get("href", "").strip()
        if not label.strip() or not href or "[" in label or "]" in label:
            return label
        parsed = _parse_link(base_url, href)
        if parsed is None or parsed.scheme not in ("http", "https"):
            return label
        url = parsed.geturl()
        if any(c in url for c in ("(", ")", " ", "	")):
            return label
        return f"[{label}]({url})"

    def _collect_link(self, href, base_url, links, binary_refs):
        if not href or href.startswith(("mailto:", "tel:", "javascript:", "#", "data:")):
            return
        parsed = _parse_link(base_url, href)
        if parsed is None:
            return
        abs_url = parsed.geturl()
        path = parsed.path.lower()
        ext = os.path.splitext(path)[1]
        if ext in BINARY_EXTENSIONS:
            binary_refs.append({
                "url": abs_url,
                "type": ext.lstrip(".").upper(),
                "name": os.path.basename(path) or abs_url,
            })
        elif parsed.scheme in ("http", "https"):
            links.append(abs_url)
