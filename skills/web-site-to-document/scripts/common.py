#!/usr/bin/env python3
"""
common.py — symbols shared by more than one module of the pipeline.

Only what genuinely has more than one consumer lives here; a helper used by a
single module belongs with that module.
"""

import base64
import functools
import ipaddress
import os
import socket
import urllib.parse
from typing import Dict, List, Optional

USER_AGENT = (
    "Mozilla/5.0 (compatible; WebSiteToDocument/1.0; "
    "+https://github.com/StefanoZaghi1987/ClaudeSkills)"
)
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB
BINARY_EXTENSIONS = {
    ".pdf", ".zip", ".tar", ".gz", ".rar", ".7z",
    ".mp4", ".mp3", ".avi", ".mov", ".mkv", ".webm",
    ".exe", ".dmg", ".pkg", ".deb", ".rpm",
    ".xls", ".xlsx", ".ppt", ".pptx", ".doc", ".docx",
}


def _parse_link(base_url: str, href: str):
    """Absolute parsed URL for an href, or None when it cannot be parsed.

    urljoin/urlparse raise ValueError on malformed IPv6 brackets
    (`http://[::1`), and page hrefs are untrusted: one bad link must not take
    down the page that holds it, nor the site analysis.
    """
    try:
        return urllib.parse.urlparse(urllib.parse.urljoin(base_url, href))
    except ValueError:
        return None

def text_chars(blocks: List[Dict]) -> int:
    """Visible text length of a page's blocks.

    Lists, tables and code count: a page structured as a list is not sparse.
    """
    n = 0
    for b in blocks:
        t = b.get("type")
        if t in ("paragraph", "heading", "callout", "code"):
            n += len(b.get("text", ""))
        elif t == "list":
            n += sum(len(i) for i in b.get("items", []))
        elif t == "table":
            n += sum(len(str(c)) for row in b.get("data", []) for c in row)
    return n


# Below this average a document is not worth building, and — during a crawl —
# not worth walking the rest of the site at one request per second to reach.
SPARSE_MIN_CHARS = 150


def sparse(pages: List[Dict]) -> bool:
    """True when a page set holds too little to build a document from.

    One rule, two callers: WebScraper asks it mid-crawl to decide whether to
    stop, main.py asks it afterwards to decide whether to build. They used to
    ask different questions — the crawl counted text only, main.py counted
    pictures too — so a photo archive was cut to the first ten pages and then
    published as a complete archive, with only a console line saying otherwise.

    Pictures count because text_chars counts none of them, and a slide portal
    or a photo archive is thin on text by nature rather than by failure. A page
    of pictures on average, not one picture anywhere: a JavaScript shell
    carrying its logo is exactly what this refusal exists to catch.
    """
    if not pages:
        return True
    avg = sum(text_chars(p.get("content", [])) for p in pages) / len(pages)
    images = sum(1 for p in pages for b in p.get("content", [])
                 if b.get("type") == "image")
    return avg < SPARSE_MIN_CHARS and images < len(pages)


def image_bytes(block: Dict) -> Optional[bytes]:
    """The picture an image block carries: the file on disk, or legacy base64.

    `path` is where ImageHandler put the picture, and it is the whole of what a
    block records today. `data` is what pages files written before that change
    hold — blocks used to carry the base64 too, which kept every picture of an
    unlimited crawl in memory — so reading it keeps those files building. One
    question, one answer, both builders.
    """
    try:
        data = block.get("data")
        if data:
            return base64.b64decode(data)
        path = block.get("path")
        if path:
            if not os.path.exists(path):
                # The block names a file that is gone: the work directory moved,
                # or the pages file travelled without its images. Saying so is
                # the whole of the fix — silence here is what let 71 pictures
                # become placeholders under a line reporting the document saved.
                print(f"    ⚠ Picture file missing: {path}", flush=True)
                return None
            with open(path, "rb") as f:
                raw = f.read(MAX_IMAGE_BYTES + 1)
            # The same ceiling the download honours, because this read has to
            # honour it too: a pages file is an input like any other, and
            # main.py already checks its shape at the same boundary. Nothing
            # ImageHandler wrote can exceed the cap, so only a hand-edited or
            # crafted file reaches this.
            return raw if len(raw) <= MAX_IMAGE_BYTES else None
    except Exception:
        pass
    return None


def read_capped(resp, cap: int) -> Optional[bytes]:
    """A response body read to `cap` bytes, or None when it runs past them.

    resp.content buffers the whole body first, so without a cap the remote
    server decides how much memory this run uses. Two callers, one rule: an
    image and a page are both untrusted bodies, and both used to be read whole.
    Closes the response on the path that stops reading; what a too-large body
    *means* is the caller's to say — a skipped picture, a skipped page.
    """
    chunks, size = [], 0
    for chunk in resp.iter_content(64 * 1024):
        size += len(chunk)
        if size > cap:
            resp.close()
            return None
        chunks.append(chunk)
    return b"".join(chunks)


def _internal_ip(value: str) -> bool:
    """True when a literal address belongs to this machine or its own network.

    The scope suffix of a link-local address (fe80::1%eth0) is not part of the
    address, and ip_address refuses the whole string with it attached.
    """
    try:
        ip = ipaddress.ip_address(value.split("%")[0])
    except ValueError:
        return False
    return (ip.is_private or ip.is_loopback or ip.is_link_local
            or ip.is_reserved or ip.is_multicast or ip.is_unspecified)


@functools.lru_cache(maxsize=4096)
def host_is_internal(host: str) -> bool:
    """True when a host names an address on this machine or its own network.

    An archived page chooses this address: its <img src> is untrusted input in
    the way a sitemap is, and the sitemap already has a host rule. Without this
    a page could point the download at 127.0.0.1 or 169.254.169.254, and the
    crawl would probe its operator's own network on the site's behalf.

    Resolved, not merely read: a name is the cheap way past a literal-IP test.
    Any address of the name counts, because a name answering with one public and
    one private address is the shape of the attack, not of a real CDN. A name
    that does not resolve is not internal — the fetch fails on its own.

    ponytail: checked here, connected to later, so an address that changes in
    between (DNS rebinding) still gets through. Closing that means resolving
    once and connecting to the address resolved, which requests does not do
    without a custom adapter.
    """
    if not host:
        return True
    if _internal_ip(host):
        return True
    try:
        infos = socket.getaddrinfo(host, None)
    except Exception:
        # More than OSError reaches here — an over-long label raises
        # UnicodeError — and a crawl must not end because a page named a
        # strange host. Unresolvable is not internal; the fetch fails anyway.
        return False
    return any(_internal_ip(sa[0]) for *_, sa in infos)


# Unicode blocks whose scripts read right-to-left. Not every RTL block exists, only the ones
# a public website is written in.
_RTL_RANGES = (
    (0x0590, 0x05FF),   # Hebrew
    (0x0600, 0x06FF),   # Arabic
    (0x0700, 0x074F),   # Syriac
    (0x0750, 0x077F),   # Arabic Supplement
    (0x0780, 0x07BF),   # Thaana
    (0x07C0, 0x07FF),   # NKo
    (0x08A0, 0x08FF),   # Arabic Extended-A
    (0xFB1D, 0xFB4F),   # Hebrew Presentation Forms
    (0xFB50, 0xFDFF),   # Arabic Presentation Forms-A
    (0xFE70, 0xFEFF),   # Arabic Presentation Forms-B
)


def is_rtl(text: str) -> bool:
    """Does this text read right-to-left?

    Decided per block, never per document: an archive holds the site's own language beside an
    English scaffold, so one direction for the whole file is wrong for one half of it.

    Predominance, not the first strong character. A heading like "API - <arabic>" opens with
    Latin letters and still belongs to an Arabic page; a paragraph of Arabic quoting one English
    product name still reads right-to-left. The first-strong-character rule gets both wrong, and
    counting gets both right. A script with no direction of its own — CJK, digits, punctuation —
    counts as left-to-right, which is how it is set today.
    """
    rtl = ltr = 0
    for ch in text:
        o = ord(ch)
        if any(a <= o <= b for a, b in _RTL_RANGES):
            rtl += 1
        elif ch.isalpha():
            ltr += 1
    return rtl > ltr
