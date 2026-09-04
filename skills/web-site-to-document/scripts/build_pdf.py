#!/usr/bin/env python3
"""
build_pdf.py — PDF builder for web-site-to-document skill.
Strategy: generate DOCX first, then convert via LibreOffice (headless).
Fallback: generate styled HTML and convert via weasyprint.
"""

import base64
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List

from common import image_bytes, is_rtl


def _find_libreoffice():
    """PATH first; on Windows the default install location is not on PATH."""
    lo = shutil.which("libreoffice") or shutil.which("soffice")
    if lo:
        return lo
    for env in ("ProgramFiles", "ProgramFiles(x86)"):
        base = os.environ.get(env)
        if base:
            candidate = os.path.join(base, "LibreOffice", "program", "soffice.exe")
            if os.path.exists(candidate):
                return candidate
    return None


def build_pdf(pages: List[Dict], output_path: str, source_url: str, blocked_domains=None,
              robots_excluded=None):
    """Generate a PDF document from scraped pages."""

    # Strategy 1: LibreOffice headless conversion from DOCX
    lo = _find_libreoffice()
    if lo:
        print("  📄 Using LibreOffice for PDF generation...", flush=True)
        try:
            _build_via_libreoffice(pages, output_path, source_url, lo, blocked_domains,
                                   robots_excluded)
            return
        except Exception as e:
            # LO found but conversion failed, hung, or would not start:
            # weasyprint may still save the run
            # Same question, same answer, one place: an unusable weasyprint must
            # not mask the LibreOffice error that got us here
            if _import_weasyprint() is not None:
                raise e  # a bare raise here would re-raise the import failure
            print(f"  ⚠️  {e}", flush=True)

    # Strategy 2: weasyprint from HTML
    reason = _import_weasyprint()
    if reason is None:
        print("  📄 Using weasyprint for PDF generation...", flush=True)
        _build_via_weasyprint(pages, output_path, source_url, blocked_domains,
                              robots_excluded)
        return

    print(
        "  ❌ PDF needs LibreOffice (headless) or the weasyprint package — neither is available.\n"
        "     Ask the user before installing anything; this script installs nothing itself.",
        flush=True,
    )
    print(f"     weasyprint could not be used: {reason}", flush=True)
    sys.exit(1)


def _import_weasyprint():
    """None when weasyprint is usable, else one line saying why it is not.

    Not only ImportError: `pip install weasyprint` succeeds on Windows and the
    import then raises OSError from cffi, because the GTK libraries it binds to
    are not pip-installable there. That is the ordinary state on Windows, and it
    is the exact path SKILL.md sends a user down when LibreOffice is absent, so
    the failure has to arrive as the message below, not as a traceback.
    """
    try:
        import weasyprint  # noqa: F401
    except Exception as e:
        return f"{type(e).__name__}: {str(e).splitlines()[0]}"
    return None


# ─── LibreOffice path ─────────────────────────────────────────────────────────

def _build_via_libreoffice(pages, output_path, source_url, lo_path, blocked_domains=None,
                           robots_excluded=None):
    from build_docx import build_docx

    with tempfile.TemporaryDirectory() as tmpdir:
        docx_path = os.path.join(tmpdir, "document.docx")
        # static_toc: headless conversion cannot update a TOC field, so emit a plain list
        build_docx(pages, docx_path, source_url, static_toc=True,
                   blocked_domains=blocked_domains, robots_excluded=robots_excluded)

        # Isolated user profile: a running LibreOffice GUI holds the default
        # profile, and headless conversion fails while it is locked
        profile = os.path.join(tmpdir, "lo-profile")
        os.makedirs(profile, exist_ok=True)
        result = subprocess.run(
            [lo_path, f"-env:UserInstallation={Path(profile).as_uri()}",
             "--headless", "--convert-to", "pdf", "--outdir", tmpdir, docx_path],
            capture_output=True, text=True, timeout=300,
        )

        pdf_tmp = os.path.join(tmpdir, "document.pdf")
        if os.path.exists(pdf_tmp):
            shutil.move(pdf_tmp, output_path)
        else:
            # soffice logs most failures to stdout, not stderr
            raise RuntimeError(
                f"LibreOffice conversion failed:\n{result.stderr or result.stdout}"
            )


# ─── Weasyprint path ──────────────────────────────────────────────────────────

def _build_via_weasyprint(pages, output_path, source_url, blocked_domains=None,
                          robots_excluded=None):
    import weasyprint

    html = _build_html(pages, source_url, blocked_domains, robots_excluded)
    weasyprint.HTML(string=html).write_pdf(output_path)


def _build_html(pages: List[Dict], source_url: str, blocked_domains=None,
                robots_excluded=None) -> str:
    from datetime import datetime
    import html as html_module

    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    parts = [f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Website Archive — {html_module.escape(source_url)}</title>
<style>
  @page {{ size: a4; }}
  body {{ font-family: Calibri, Arial, sans-serif; font-size: 11pt; color: #222; margin: 2cm; }}
  h1 {{ color: #1F4E79; font-size: 18pt; page-break-before: always; }}
  h2 {{ color: #2E74B5; font-size: 14pt; }}
  h3, h4, h5, h6 {{ color: #333; }}
  code, pre {{ font-family: "Courier New", monospace; font-size: 9pt; background: #f4f4f4; }}
  pre {{ padding: 8px; border-left: 3px solid #ccc; white-space: pre-wrap; word-break: break-all; }}
  table {{ border-collapse: collapse; width: 100%; margin: 8px 0; font-size: 10pt; }}
  th, td {{ border: 1px solid #ccc; padding: 4px 8px; }}
  th {{ background: #f0f0f0; font-weight: bold; }}
  blockquote {{ border-left: 3px solid #aaa; margin: 8px 0 8px 16px; padding: 4px 12px; color: #555; font-style: italic; }}
  .meta {{ color: #777; font-size: 9pt; }}
  /* The cover owns its page. :first-of-type is scoped per parent, so the old
     h1:first-of-type rule matched the "Contents" heading — body's first h1 —
     rather than the cover's, and the contents list rendered on the cover. */
  .cover {{ text-align: center; padding: 80px 0; page-break-after: always; }}
  .cover h1 {{ font-size: 28pt; color: #1F4E79; page-break-before: avoid; }}
  .cover .url {{ color: #0056B3; font-size: 13pt; }}
  img {{ max-width: 100%; max-height: 22cm; height: auto; display: block; margin: 8px 0; }}
  .img-placeholder {{ color: #999; font-style: italic; }}
  hr {{ border: none; border-top: 1px solid #ddd; margin: 20px 0; }}
  .refs li {{ font-size: 9pt; color: #333; }}
  .toc {{ font-size: 10pt; }}
</style>
</head>
<body>
<div class="cover">
  <h1>Website Archive</h1>
  <p class="url">{html_module.escape(source_url)}</p>
  <p class="meta">Extracted: {date_str} &nbsp;|&nbsp; Pages: {len(pages)}</p>
</div>
"""]

    # Static contents list — weasyprint cannot render the Word TOC field
    if pages:
        toc_items = []
        for i, p in enumerate(pages):
            title = html_module.escape(p.get("title") or f"Page {i + 1}")
            toc_items.append(f"<li>{title}</li>")
        parts.append("<h1>Contents</h1><ul class='toc'>" + "".join(toc_items) + "</ul>")

    all_binary_refs: List[Dict] = []

    for i, page in enumerate(pages):
        title = page.get("title") or f"Page {i + 1}"
        url = page.get("url", "")
        breadcrumb = page.get("breadcrumb", [])

        parts.append("<hr>")
        parts.append(f"<h1{_dir(title)}>{html_module.escape(title)}</h1>")
        if url:
            parts.append(f'<p class="meta">Source: <a href="{html_module.escape(url)}">{html_module.escape(url)}</a></p>')
        if breadcrumb:
            crumb = " › ".join(breadcrumb)
            parts.append(f'<p class="meta"{_dir(crumb)}>{html_module.escape(crumb)}</p>')

        for block in page.get("content", []):
            parts.append(_block_html(block))

        all_binary_refs.extend(page.get("binary_references", []))

    # References
    if all_binary_refs or blocked_domains or robots_excluded:
        seen = set()
        unique_refs = [r for r in all_binary_refs if r["url"] not in seen and not seen.add(r["url"])]
        parts.append("<hr><h1>References and Attachments</h1><ul class='refs'>")
        for ref in unique_refs:
            name = html_module.escape(ref.get("name") or ref["url"])
            url_esc = html_module.escape(ref["url"])
            ftype = html_module.escape(ref.get("type", "FILE"))
            parts.append(f'<li><a href="{url_esc}">{name}</a> <code>{ftype}</code></li>')
        parts.append("</ul>")

        if blocked_domains:
            parts.append("<h2>Domains not reachable during extraction</h2><ul class='refs'>")
            for domain in sorted(blocked_domains):
                parts.append(f"<li>{html_module.escape(domain)}</li>")
            parts.append("</ul>")

        if robots_excluded:
            parts.append("<h2>Pages excluded by robots.txt</h2><ul class='refs'>")
            for page_url in robots_excluded:
                parts.append(f"<li>{html_module.escape(page_url)}</li>")
            parts.append("</ul>")

    parts.append("</body></html>")
    return "\n".join(parts)


def _dir(text: str) -> str:
    """` dir="rtl"` for right-to-left text, nothing for the rest.

    An explicit direction rather than `dir="auto"`: the auto algorithm is not something every
    HTML-to-PDF engine implements, and `dir="rtl"` maps to `direction: rtl` in all of them. It
    also carries into the LibreOffice route, which converts the Word file this pipeline builds.
    """
    return ' dir="rtl"' if is_rtl(text) else ""


def _block_html(block: Dict) -> str:
    import html as h

    btype = block.get("type", "")

    if btype == "heading":
        level = min(block.get("level", 1) + 1, 6)
        return (f"<h{level}{_dir(block.get('text', ''))}>"
                f"{h.escape(block.get('text', ''))}</h{level}>")

    elif btype == "paragraph":
        text = block.get("text", "").strip()
        if not text:
            return ""
        d = _dir(text)
        # Light markdown → HTML
        text = h.escape(text)
        text = _md_inline(text)
        return f"<p{d}>{text}</p>"

    elif btype == "code":
        lang = h.escape(block.get("language", ""))
        code = h.escape(block.get("text", ""))
        label = f'<small style="color:#888">[{lang}]</small><br>' if lang else ""
        return f"<pre>{label}{code}</pre>"

    elif btype == "list":
        # A sublist arrives as its own block: indent by its level, and continue
        # an ordered list's numbering from where the parent block stopped
        tag = "ol" if block.get("ordered") else "ul"
        start = block.get("start", 0)
        attrs = f' start="{start + 1}"' if tag == "ol" and start else ""
        level = block.get("level", 0)
        style = f' style="margin-left:{level * 1.5}em"' if level else ""
        d = _dir(" ".join(str(i) for i in block.get("items", [])))
        items = "".join(f"<li>{_md_inline(h.escape(it))}</li>" for it in block.get("items", []))
        return f"<{tag}{attrs}{style}{d}>{items}</{tag}>"

    elif btype == "table":
        data = block.get("data", [])
        if not data:
            return ""
        rows_html = []
        for ri, row in enumerate(data):
            cells = "".join(
                f"<{'th' if ri == 0 else 'td'}>{_md_inline(h.escape(str(c)))}</{'th' if ri == 0 else 'td'}>"
                for c in row
            )
            rows_html.append(f"<tr>{cells}</tr>")
        # `dir` on the table mirrors its columns, the job w:bidiVisual does in the docx
        d = _dir(" ".join(str(c) for row in data for c in row))
        return f"<table{d}>{''.join(rows_html)}</table>"

    elif btype == "image":
        alt = h.escape(block.get("alt", "") or "")
        raw = image_bytes(block)
        # Escaped like every other value here. ImageHandler rejects a mime that
        # is not a bare type/subtype, but a --pages-file written by an older
        # version or by hand can still carry one, and this was the single
        # unescaped interpolation in the builder.
        mime = h.escape(block.get("mime_type") or "image/png")
        if raw:
            data_b64 = base64.b64encode(raw).decode("ascii")
            return f'<img src="data:{mime};base64,{data_b64}" alt="{alt}">'
        # No picture to be had → placeholder, same as the docx builder; a remote
        # <img src> would make weasyprint re-fetch every image at build time. Alt
        # text and URL both: a caption with no address is a dead end for the reader.
        src = h.escape(block.get("src", ""))
        return f'<p class="img-placeholder">[Image: {" — ".join(x for x in (alt, src) if x)}]</p>'

    elif btype == "callout":
        d = _dir(block.get("text", "") or "")
        text = _md_inline(h.escape(block.get("text", "").strip()))
        return f"<blockquote{d}>{text}</blockquote>"

    return ""


def _md_inline(text: str) -> str:
    """Convert minimal markdown inline to HTML (already HTML-escaped input)."""
    import re
    # Links first: the label may carry **bold**, which the rules below then
    # format inside the anchor. The input is already escaped, so an & in the
    # URL arrives as &amp; — which is what an href needs anyway.
    text = re.sub(r"\[([^\]\[]+)\]\(([^()\s]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    return text
