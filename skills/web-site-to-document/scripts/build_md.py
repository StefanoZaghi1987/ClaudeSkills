#!/usr/bin/env python3
"""
build_md.py — Markdown document builder for web-site-to-document skill.
"""

import re
from datetime import datetime
from typing import Dict, List


def build_md(pages: List[Dict], output_path: str, source_url: str, blocked_domains=None,
             robots_excluded=None):
    """Generate a Markdown document from scraped pages."""
    lines = []
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    # ── Cover ──────────────────────────────────────────────────────────────────
    lines += [
        "# Website Archive",
        "",
        f"**Source:** {source_url}  ",
        f"**Extracted:** {date_str}  ",
        f"**Pages:** {len(pages)}",
        "",
        "---",
        "",
    ]

    # ── Table of Contents ──────────────────────────────────────────────────────
    lines.append("## Table of Contents")
    lines.append("")
    seen_anchors: Dict[str, int] = {}
    for i, page in enumerate(pages):
        title = page.get("title") or f"Page {i + 1}"
        anchor = _unique_anchor(_anchor(title), seen_anchors)
        indent = "  " * min(page.get("depth", 0), 4)
        lines.append(f"{indent}- [{title}](#{anchor})")
    lines += ["", "---", ""]

    # ── Content ────────────────────────────────────────────────────────────────
    all_binary_refs: List[Dict] = []

    for i, page in enumerate(pages):
        title = page.get("title") or f"Page {i + 1}"
        url = page.get("url", "")
        breadcrumb = page.get("breadcrumb", [])

        lines.append(f"## {title}")
        lines.append("")
        if url:
            lines.append(f"*Source: [{url}]({url})*")
            lines.append("")
        if breadcrumb:
            lines.append(f"*{' › '.join(breadcrumb)}*")
            lines.append("")

        for block in page.get("content", []):
            lines.extend(_render(block))

        all_binary_refs.extend(page.get("binary_references", []))
        lines += ["", "---", ""]

    # ── References ─────────────────────────────────────────────────────────────
    if all_binary_refs or blocked_domains or robots_excluded:
        seen = set()
        unique_refs = []
        for r in all_binary_refs:
            if r["url"] not in seen:
                seen.add(r["url"])
                unique_refs.append(r)

        lines += ["## References and Attachments", ""]
        for ref in unique_refs:
            name = ref.get("name") or ref["url"]
            ftype = ref.get("type", "FILE")
            lines.append(f"- [{name}]({ref['url']}) `{ftype}`")
        lines.append("")

        if blocked_domains:
            lines += ["### Domains not reachable during extraction", ""]
            lines += [f"- {d}" for d in sorted(blocked_domains)]
            lines.append("")

        if robots_excluded:
            lines += ["### Pages excluded by robots.txt", ""]
            lines += [f"- {u}" for u in robots_excluded]
            lines.append("")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _brs(text: str) -> str:
    """Keep the breaks a <br> asked for as <br>, not as a raw newline.

    _tidy stores them as newlines — how a site writes an address or a multi-line
    spec. Markdown does not read a raw newline that way anywhere it matters: it
    ends a table row, and inside a list item or a paragraph it loses the break
    outright, or ends the block when the next line opens with -, 1. or #.
    <br> is the portable spelling, and the table syntax is a GitHub-flavored
    extension already. Code blocks keep their real newlines, and a callout
    prefixes every line with > before it gets here.
    """
    return text.replace("\n", "<br>")


def _cell(value) -> str:
    """A table cell: a literal | in the text would silently add a column."""
    return _brs(str(value).replace("|", "\\|"))


def _anchor(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"\s+", "-", text)
    return text


def _unique_anchor(anchor: str, seen: Dict[str, int]) -> str:
    """GitHub's rule for a repeated heading: the second "Introduction" is
    #introduction-1. Without it both contents links jump to the first page."""
    n = seen.get(anchor, 0)
    seen[anchor] = n + 1
    return anchor if n == 0 else f"{anchor}-{n}"


def _render(block: Dict) -> List[str]:
    btype = block.get("type", "")
    lines = []

    if btype == "heading":
        # A page title is written as "## {title}" above, so the page's own <h2>
        # is the level below it. + 2 skipped that level and flattened h4, h5 and
        # h6 into one: the deepest three headings of an API reference all came
        # out as "######". Word and PDF both offset by one; this is the builder
        # that did not.
        level = min(block.get("level", 2) + 1, 6)
        lines += [f"{'#' * level} {block.get('text', '')}", ""]

    elif btype == "paragraph":
        text = block.get("text", "").strip()
        if text:
            lines += [_brs(text), ""]

    elif btype == "code":
        lang = block.get("language", "")
        code = block.get("text", "")
        # The fence must outlast the longest backtick run inside the code, or a
        # code sample that itself shows a fence ends the block early and the
        # rest of the document renders as source
        ticks = max((len(m) for m in re.findall(r"`+", code)), default=0)
        fence = "`" * max(3, ticks + 1)
        lines += [f"{fence}{lang}", code, fence, ""]

    elif btype == "list":
        # A sublist arrives as its own block: indent by its level, and continue
        # an ordered list's numbering from where the parent block stopped.
        # Four spaces per level, not two: nesting under an ordered parent has to
        # clear the "1. " marker, or the sublist reads as a sibling list instead
        indent = "    " * block.get("level", 0)
        start = block.get("start", 0)
        for j, item in enumerate(block.get("items", [])):
            prefix = f"{start + j + 1}." if block.get("ordered") else "-"
            lines.append(f"{indent}{prefix} {_brs(item)}")
        lines.append("")

    elif btype == "table":
        data = block.get("data", [])
        if data:
            # The widest row sets the width, not the header. A colspan header
            # extracts as one cell above two-cell body rows, and truncating to the
            # header's width dropped the extra values with nothing said about it.
            # Word takes the widest row already; PDF emits every cell it is given.
            width = max(len(r) for r in data)
            for i, row in enumerate(data):
                cells = list(row) + [""] * (width - len(row))
                lines.append("| " + " | ".join(_cell(c) for c in cells) + " |")
                if i == 0:
                    lines.append("| " + " | ".join(["---"] * width) + " |")
            lines.append("")

    elif btype == "image":
        alt = block.get("alt", "Image")
        src = block.get("src", "")
        lines += [f"![{alt}]({src})", ""]

    elif btype == "callout":
        text = block.get("text", "").strip()
        if text:
            for ln in text.splitlines():
                lines.append(f"> {ln}")
            lines.append("")

    return lines
