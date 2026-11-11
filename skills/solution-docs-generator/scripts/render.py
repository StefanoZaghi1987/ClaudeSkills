#!/usr/bin/env python3
"""
render.py - build the delivered document from the authored Markdown source.

    python render.py <source.md> --to docx|pdf|md [-o <output>] [--profile profile.md]
                     [--lang-pack pack.json] [--no-paginate] [--no-update-fields]

The source is Markdown with a front-matter block and a few extensions, documented in
references/authoring-format.md: '::: card', '::: note|tip|warning|important|info|verify|technical',
'::: part',
'Table: caption' lines, '![caption](image)' figures, '[[BADGE]]' inline badges, '\\newpage'.

Fixed texts (captions, "Page", callout titles, revision table) come from the language pack of the
front matter's 'lang' (assets/i18n/<lang>.json; --lang-pack for a language the skill does not ship).

- docx: python-docx, A4, one fixed house style (overridable from front matter 'style:' or from
  the profile's render-style block: fonts, colours, logo, header and footer texts, "Page N of M",
  cover as lines or as a form). The table of contents is a real Word TOC field; when LibreOffice
  and pypdf are available its entries are pre-filled with page numbers measured on a rendered
  copy, and Word refreshes the field when the file is opened.
- pdf:  the .docx above, converted with LibreOffice (headless).
- md:   clean, portable Markdown (extensions turned into plain Markdown, captions numbered).

Python 3.10+, python-docx for docx/pdf, pypdf for page numbers. No network access.
"""

from __future__ import annotations

import argparse
import copy
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (all_packs, configure_stdout, load_lang, parse_simple_yaml, read_text,  # noqa: E402
                    split_front_matter, write_text)

DEFAULT_STYLE = {"font": "Calibri", "mono": "Consolas", "color": "1F3864", "accent": "D9E2F3",
                 "muted": "595959", "body_size": 10.5, "h1_size": 16.0, "h2_size": 13.0, "h3_size": 11.5,
                 "h4_size": 10.5, "table_size": 9.5, "code_size": 8.5, "h1_new_page": False,
                 "margin_cm": 2.0,
                 # page furniture (all optional; placeholders: {title} {type} {ref} {version} {date})
                 "logo": "", "logo_width_cm": 3.0, "logo_position": "header",   # header | cover | both
                 "header_text": "", "footer_text": "",
                 "page_format": "",             # e.g. "Pag. {page} di {pages}"; default "<page label> {page}"
                 "cover_layout": "lines"}       # lines | form
CALLOUT_COLORS = {"note": "2E75B6", "info": "2E75B6", "tip": "548235", "warning": "C55A11", "important": "C00000",
                  "verify": "BF8F00", "technical": "7030A0"}
CALLOUT_FILLS = {"warning": "FBE5D6", "important": "FDE9E9", "tip": "E2EFDA", "verify": "FFF2CC",
                 "technical": "EDE4F5"}


# ======================================================================================
# Parsing: Markdown source -> list of blocks
# ======================================================================================
@dataclass
class Block:
    kind: str                       # heading, para, list, table, code, image, callout, card, part, pagebreak, rule
    text: str = ""
    level: int = 0
    items: list = field(default_factory=list)     # list: [(indent, ordered, number, text)]
    rows: list = field(default_factory=list)      # table rows (list of cells)
    caption: str = ""
    widths: list = field(default_factory=list)
    lang: str = ""
    path: str = ""
    width_cm: float = 0.0
    title: str = ""
    children: list = field(default_factory=list)  # callout/part: blocks; card: [(label, [blocks])]


TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")
LIST_RX = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$")
IMAGE_RX = re.compile(r"^!\[(.*?)\]\((\S+?)(?:\s+\"[^\"]*\")?\)(\{[^}]*\})?\s*$")
# "Table: caption" in English or in the label of any shipped language pack
_CAPTION_WORDS = sorted({"Table"} | {str(p.get("labels", {}).get("table", "")) for p in all_packs()} - {""},
                        key=len, reverse=True)
CAPTION_RX = re.compile(r"^(?:" + "|".join(map(re.escape, _CAPTION_WORDS)) + r"):\s*(.+?)\s*(\{[^}]*\})?\s*$", re.I)
FIELD_RX = re.compile(r"^([^\s:|][^:|]{0,48}?):\s*(.*)$")


def split_row(line: str) -> list[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    cells, cur, esc = [], [], False
    for ch in s:
        if esc:
            cur.append(ch if ch == "|" else "\\" + ch)
            esc = False
        elif ch == "\\":
            esc = True
        elif ch == "|":
            cells.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    cells.append("".join(cur).strip())
    return cells


def parse_attrs(s: str | None) -> dict:
    out = {}
    if s:
        for k, v in re.findall(r"(\w+)\s*=\s*([^\s}]+)", s):
            out[k] = v.strip("\"'")
    return out


def parse_blocks(lines: list[str]) -> list[Block]:
    blocks: list[Block] = []
    i = 0
    para: list[str] = []

    def flush_para():
        if para:
            blocks.append(Block("para", text=" ".join(l.strip() for l in para)))
            para.clear()

    while i < len(lines):
        line = lines[i].rstrip("\n")
        stripped = line.strip()

        # containers ::: kind [title] ... :::
        m = re.match(r"^:::\s*(\w+)\s*(.*)$", stripped)
        if m and stripped != ":::":
            flush_para()
            kind, title = m.group(1).lower(), m.group(2).strip()
            depth, j, inner = 1, i + 1, []
            while j < len(lines):
                s = lines[j].strip()
                if re.match(r"^:::\s*\w+", s):
                    depth += 1
                elif s == ":::":
                    depth -= 1
                    if depth == 0:
                        break
                inner.append(lines[j])
                j += 1
            if kind == "card":
                blocks.append(Block("card", title=title, children=parse_card(inner)))
            elif kind == "part":
                blocks.append(Block("part", title=title, children=parse_blocks(inner)))
            else:
                blocks.append(Block("callout", lang=kind, title=title, children=parse_blocks(inner)))
            i = j + 1
            continue

        # fenced code
        m = re.match(r"^(```+|~~~+)\s*([\w+#.\-]*)", stripped)
        if m:
            flush_para()
            fence, lang, code = m.group(1), m.group(2), []
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith(fence):
                code.append(lines[j].rstrip("\n"))
                j += 1
            blocks.append(Block("code", text="\n".join(code), lang=lang))
            i = j + 1
            continue

        if stripped in ("\\newpage", "\\pagebreak", "<!-- pagebreak -->", "<!-- newpage -->"):
            flush_para()
            blocks.append(Block("pagebreak"))
            i += 1
            continue

        if re.match(r"^<!--.*-->$", stripped):  # comments (e.g. source notes) are not rendered
            flush_para()
            i += 1
            continue
        if stripped.startswith("<!--"):
            flush_para()
            while i < len(lines) and "-->" not in lines[i]:
                i += 1
            i += 1
            continue

        m = re.match(r"^(#{1,6})\s+(.*?)\s*#*\s*$", stripped)
        if m:
            flush_para()
            blocks.append(Block("heading", text=m.group(2), level=len(m.group(1))))
            i += 1
            continue

        if re.match(r"^(\*\s*\*\s*\*|-\s*-\s*-|_\s*_\s*_)[\s*_-]*$", stripped):
            flush_para()
            blocks.append(Block("rule"))
            i += 1
            continue

        m = IMAGE_RX.match(stripped)
        if m:
            flush_para()
            attrs = parse_attrs(m.group(3))
            w = attrs.get("width", "")
            wm = re.match(r"([\d.]+)\s*cm", w)
            blocks.append(Block("image", caption=m.group(1), path=m.group(2),
                                width_cm=float(wm.group(1)) if wm else 0.0))
            i += 1
            continue

        # table: header row + separator
        if stripped.startswith("|") and i + 1 < len(lines) and TABLE_SEP.match(lines[i + 1]):
            flush_para()
            rows = [split_row(stripped)]
            j = i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                rows.append(split_row(lines[j]))
                j += 1
            b = Block("table", rows=rows)
            # caption line right after (blank lines allowed)
            k = j
            while k < len(lines) and not lines[k].strip():
                k += 1
            if k < len(lines):
                cm = CAPTION_RX.match(lines[k].strip())
                if cm:
                    b.caption = cm.group(1)
                    attrs = parse_attrs(cm.group(2))
                    if "widths" in attrs:
                        b.widths = [float(x) for x in re.split(r"[,;]", attrs["widths"]) if x]
                    j = k + 1
            blocks.append(b)
            i = j
            continue

        m = LIST_RX.match(line)
        if m and (not para):
            flush_para()
            items = []
            j = i
            while j < len(lines):
                lm = LIST_RX.match(lines[j].rstrip("\n"))
                if lm:
                    indent = len(lm.group(1).replace("\t", "    "))
                    marker = lm.group(2)
                    ordered = marker[0].isdigit()
                    num = int(re.match(r"\d+", marker).group()) if ordered else 0
                    items.append([indent, ordered, num, lm.group(3).strip()])
                    j += 1
                elif lines[j].strip() and lines[j].startswith((" ", "\t")) and items:
                    items[-1][3] += " " + lines[j].strip()  # continuation line
                    j += 1
                else:
                    break
            levels = sorted({it[0] for it in items})
            blocks.append(Block("list", items=[(min(levels.index(it[0]), 2), it[1], it[2], it[3]) for it in items]))
            i = j
            continue

        if not stripped:
            flush_para()
            i += 1
            continue
        if CAPTION_RX.match(stripped) and blocks and blocks[-1].kind == "table" and not para:
            blocks[-1].caption = CAPTION_RX.match(stripped).group(1)
            i += 1
            continue
        para.append(line)
        i += 1
    flush_para()
    return blocks


def parse_card(lines: list[str]) -> list[tuple[str, list[Block]]]:
    """'Label: text' starts a field; list items and other lines belong to the current field."""
    fields: list[tuple[str, list[str]]] = []
    for raw in lines:
        s = raw.rstrip("\n")
        m = FIELD_RX.match(s.strip()) if not LIST_RX.match(s) else None
        if m and not s.startswith((" ", "\t")) and not s.strip().startswith(("**", "`", "[", "!")):
            fields.append((m.group(1).strip(), [m.group(2)] if m.group(2).strip() else []))
        elif fields:
            fields[-1][1].append(s)
        elif s.strip():
            fields.append(("", [s]))
    return [(label, parse_blocks(body)) for label, body in fields]


# ======================================================================================
# Inline parsing: text -> runs [(text, {bold, italic, code, link, badge})]
# ======================================================================================
INLINE_RX = re.compile(
    r"(?P<code>`+)(?P<codetext>.+?)(?P=code)"
    r"|\[\[(?P<badge>[^\]]+)\]\]"
    r"|!?\[(?P<ltext>[^\]]+)\]\((?P<lurl>[^)\s]+)\)"
    r"|\*\*(?P<bold>.+?)\*\*"
    r"|__(?P<bold2>.+?)__"
    r"|(?<![\w*])\*(?!\s)(?P<ital>.+?)(?<![\s\\])\*(?!\*)"
    r"|(?<![\w_])_(?!\s)(?P<ital2>.+?)(?<!\s)_(?![\w_])"
    r"|<(?P<auto>https?://[^>\s]+)>"
)
ESCAPES = {"\\*": "\x01", "\\_": "\x02", "\\#": "\x03", "\\[": "\x04", "\\]": "\x05", "\\`": "\x06",
           "\\|": "\x07", "\\\\": "\x08", "\\<": "\x0e", "\\>": "\x0f"}
UNESCAPE = {v: k[1] for k, v in ESCAPES.items()}


def _escape(s: str) -> str:
    for k, v in ESCAPES.items():
        s = s.replace(k, v)
    return s


def _unescape(s: str) -> str:
    for k, v in UNESCAPE.items():
        s = s.replace(k, v)
    return s


def parse_inline(text: str, fmt: dict | None = None) -> list[tuple[str, dict]]:
    fmt = fmt or {}
    text = _escape(text) if not fmt else text
    runs: list[tuple[str, dict]] = []
    pos = 0
    for m in INLINE_RX.finditer(text):
        if m.start() > pos:
            runs.append((_unescape(text[pos:m.start()]), dict(fmt)))
        if m.group("codetext") is not None:
            runs.append((_unescape(m.group("codetext").strip() if m.group("code") == "``" else m.group("codetext")), {**fmt, "code": True}))
        elif m.group("badge") is not None:
            runs.append((_unescape(m.group("badge")), {**fmt, "badge": True}))
        elif m.group("ltext") is not None:
            runs.extend(parse_inline(m.group("ltext"), {**fmt, "link": _unescape(m.group("lurl"))}))
        elif m.group("bold") is not None or m.group("bold2") is not None:
            runs.extend(parse_inline(m.group("bold") or m.group("bold2"), {**fmt, "bold": True}))
        elif m.group("ital") is not None or m.group("ital2") is not None:
            runs.extend(parse_inline(m.group("ital") or m.group("ital2"), {**fmt, "italic": True}))
        elif m.group("auto") is not None:
            runs.append((m.group("auto"), {**fmt, "link": m.group("auto")}))
        pos = m.end()
    if pos < len(text):
        runs.append((_unescape(text[pos:]), dict(fmt)))
    return [r for r in runs if r[0]]


def plain(text: str) -> str:
    return "".join(t for t, _ in parse_inline(text))


# ======================================================================================
# Caption numbering (shared by docx and md)
# ======================================================================================
def number_captions(blocks: list[Block], counters: dict | None = None) -> dict:
    counters = counters if counters is not None else {"table": 0, "figure": 0}
    for b in blocks:
        if b.kind == "table" and b.caption:
            counters["table"] += 1
            b.level = counters["table"]
        elif b.kind == "image":
            counters["figure"] += 1
            b.level = counters["figure"]
        if b.kind in ("callout", "part"):
            number_captions(b.children, counters)
        if b.kind == "card":
            for _, bl in b.children:
                number_captions(bl, counters)
    return counters


def toc_entries(blocks: list[Block], max_level: int = 2) -> list[tuple[int, str]]:
    out = []
    for b in blocks:
        if b.kind == "part":
            out.append((0, plain(b.title)))
            out += toc_entries(b.children, max_level)
        elif b.kind == "heading" and b.level <= max_level:
            out.append((b.level, plain(b.text)))
    return out


# ======================================================================================
# DOCX writer
# ======================================================================================
class DocxWriter:
    def __init__(self, meta: dict, style: dict, pack: dict, base_dir: Path, page_numbers: list | None):
        try:
            import docx  # type: ignore
        except ImportError:
            sys.exit("python-docx is required for docx/pdf output: <interpreter> -m pip install python-docx")
        from docx.enum.section import WD_SECTION  # noqa: F401
        from docx.shared import Cm, Pt, RGBColor
        self.docx, self.Cm, self.Pt, self.RGB = docx, Cm, Pt, RGBColor
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        self.OX, self.qn = OxmlElement, qn
        self.meta, self.st, self.base = meta, style, base_dir
        self.pack = pack
        self.lang = pack["lang"]
        self.L = pack["labels"]
        self.page_numbers = page_numbers
        self.doc = docx.Document()
        self._setup()

    # ---------- styles and page ----------
    def _rgb(self, hexstr: str):
        return self.RGB.from_string(str(hexstr).lstrip("#").upper())

    def _style_font(self, style, name, size, rgb=None, bold=None):
        style.font.name, style.font.size = name, self.Pt(size)
        if rgb is not None:
            style.font.color.rgb = rgb
        if bold is not None:
            style.font.bold = bold
        rpr = style.element.get_or_add_rPr()
        rfonts = rpr.find(self.qn("w:rFonts"))
        if rfonts is None:
            rfonts = self.OX("w:rFonts")
            rpr.append(rfonts)
        for theme in ("asciiTheme", "hAnsiTheme", "eastAsiaTheme", "cstheme"):
            rfonts.attrib.pop(self.qn(f"w:{theme}"), None)
        for attr in ("ascii", "hAnsi", "eastAsia", "cs"):
            rfonts.set(self.qn(f"w:{attr}"), name)

    def _setup(self):
        st, Pt, Cm = self.st, self.Pt, self.Cm
        for s in self.doc.sections:
            s.page_width, s.page_height = Cm(21.0), Cm(29.7)
            m = Cm(float(st["margin_cm"]))
            s.left_margin = s.right_margin = s.top_margin = s.bottom_margin = m
            s.header_distance = s.footer_distance = Cm(1.0)
            s.different_first_page_header_footer = True
        styles = self.doc.styles
        normal = styles["Normal"]
        self._style_font(normal, st["font"], float(st["body_size"]), self._rgb("000000"))
        normal.paragraph_format.space_after = Pt(6)
        normal.paragraph_format.line_spacing = 1.1
        for lvl in (1, 2, 3, 4):
            hs = styles[f"Heading {lvl}"]
            self._style_font(hs, st["font"], float(st[f"h{lvl}_size"]), self._rgb(st["color"]), True)
            hs.font.italic = False
            pf = hs.paragraph_format
            pf.space_before = Pt({1: 18, 2: 14, 3: 10, 4: 8}[lvl])
            pf.space_after = Pt({1: 8, 2: 6, 3: 4, 4: 4}[lvl])
            pf.keep_with_next = True
            if lvl == 1 and st.get("h1_new_page"):
                pf.page_break_before = True
        for name in ("List Bullet", "List Bullet 2", "List Bullet 3"):
            if name in [s.name for s in styles]:
                self._style_font(styles[name], st["font"], float(st["body_size"]))
                styles[name].paragraph_format.space_after = Pt(3)
        self._header_footer()

    def _add_field(self, paragraph, instr: str, placeholder: str = "1"):
        r = paragraph.add_run()
        for tag, extra in (("w:fldChar", {"w:fldCharType": "begin"}), ("w:instrText", None),
                           ("w:fldChar", {"w:fldCharType": "separate"})):
            el = self.OX(tag)
            if extra:
                for k, v in extra.items():
                    el.set(self.qn(k), v)
            else:
                el.set(self.qn("xml:space"), "preserve")
                el.text = f" {instr} "
            r._r.append(el)
        r2 = paragraph.add_run(placeholder)
        r3 = paragraph.add_run()
        end = self.OX("w:fldChar")
        end.set(self.qn("w:fldCharType"), "end")
        r3._r.append(end)
        return r2

    def placeholders(self) -> dict:
        """Values for {title} {type} {ref} {version} {date} in header_text, footer_text, page_format."""
        m = self.meta
        type_key = str(m.get("type", ""))
        type_name = self.pack.get("types", {}).get(type_key, {}).get("name", type_key)
        return {"title": plain(str(m.get("title", ""))), "type": type_name, "ref": str(m.get("ref", "")),
                "version": str(m.get("version", "")), "date": str(m.get("date", ""))}

    def _fill(self, template: str) -> str:
        vals = self.placeholders()
        return re.sub(r"\{(title|type|ref|version|date)\}", lambda x: vals[x.group(1)], template)

    def _logo(self, paragraph, width_cm: float) -> bool:
        logo = str(self.st.get("logo") or "")
        if not logo:
            return False
        if not Path(logo).is_file():
            print(f"warning: logo not found: {logo}", file=sys.stderr)
            return False
        paragraph.add_run().add_picture(logo, width=self.Cm(width_cm))
        return True

    def _right_tab(self, paragraph):
        from docx.enum.text import WD_TAB_ALIGNMENT
        paragraph.paragraph_format.tab_stops.add_tab_stop(
            self.Cm(21.0 - 2 * float(self.st["margin_cm"])), WD_TAB_ALIGNMENT.RIGHT)

    def _page_runs(self, paragraph, size: float):
        """'Pag. {page} di {pages}' -> text runs with PAGE and NUMPAGES fields."""
        fmt = str(self.st.get("page_format") or f"{self.L['page']} {{page}}")
        for part in re.split(r"(\{pages?\})", self._fill(fmt)):
            if part in ("{page}", "{pages}"):
                self._add_field(paragraph, "PAGE" if part == "{page}" else "NUMPAGES").font.size = self.Pt(size)
            elif part:
                paragraph.add_run(part).font.size = self.Pt(size)

    def _header_footer(self):
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        sec = self.doc.sections[0]
        head_text = self._fill(str(self.st.get("header_text") or self.meta.get("header")
                                   or plain(str(self.meta.get("title", "")))))
        hp = sec.header.paragraphs[0]
        if str(self.st.get("logo_position", "header")) in ("header", "both") and \
                self._logo(hp, min(float(self.st["logo_width_cm"]), 4.0)):
            self._right_tab(hp)
            hp.add_run("\t")
        else:
            hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r = hp.add_run(head_text)
        r.font.size, r.font.color.rgb = self.Pt(8.5), self._rgb(self.st["muted"])
        self._border(hp, "bottom", "BFBFBF", 4)
        fp = sec.footer.paragraphs[0]
        footer_text = self._fill(str(self.st.get("footer_text") or ""))
        if footer_text:
            r = fp.add_run(footer_text)
            r.font.size, r.font.color.rgb = self.Pt(8.5), self._rgb(self.st["muted"])
            self._right_tab(fp)
            fp.add_run("\t")
        else:
            fp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        self._page_runs(fp, 8.5)

    def _border(self, paragraph, side: str, color: str, size: int, space: int = 4):
        ppr = paragraph._p.get_or_add_pPr()
        bdr = ppr.find(self.qn("w:pBdr"))
        if bdr is None:
            bdr = self.OX("w:pBdr")
            ppr.append(bdr)
        el = self.OX(f"w:{side}")
        for k, v in (("w:val", "single"), ("w:sz", str(size)), ("w:space", str(space)), ("w:color", color)):
            el.set(self.qn(k), v)
        bdr.append(el)

    def _shade(self, element_pr, fill: str):
        shd = self.OX("w:shd")
        shd.set(self.qn("w:val"), "clear")
        shd.set(self.qn("w:color"), "auto")
        shd.set(self.qn("w:fill"), fill)
        element_pr.append(shd)

    # ---------- inline ----------
    def add_runs(self, paragraph, text: str, size: float | None = None, base: dict | None = None):
        for t, f in parse_inline(text):
            f = {**(base or {}), **f}
            if f.get("link"):
                self._hyperlink(paragraph, t, f["link"], size)
                continue
            r = paragraph.add_run(t)
            if f.get("bold"):
                r.bold = True
            if f.get("italic"):
                r.italic = True
            if size:
                r.font.size = self.Pt(size)
            if f.get("code"):
                r.font.name = self.st["mono"]
                r._r.get_or_add_rPr().get_or_add_rFonts().set(self.qn("w:cs"), self.st["mono"])
                r.font.size = self.Pt((size or float(self.st["body_size"])) - 1)
            if f.get("badge"):
                r.bold = True
                r.font.size = self.Pt(max(7.0, (size or float(self.st["body_size"])) - 2.5))
                r.font.color.rgb = self._rgb("FFFFFF")
                self._shade(r._r.get_or_add_rPr(), self.st["color"])
                r.text = f"\u00a0{t}\u00a0"

    def _hyperlink(self, paragraph, text: str, url: str, size: float | None):
        part = paragraph.part
        rid = part.relate_to(url, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
                             is_external=True)
        h = self.OX("w:hyperlink")
        h.set(self.qn("r:id"), rid)
        r = self.OX("w:r")
        rpr = self.OX("w:rPr")
        c = self.OX("w:color")
        c.set(self.qn("w:val"), "0563C1")
        u = self.OX("w:u")
        u.set(self.qn("w:val"), "single")
        rpr.append(c)
        rpr.append(u)
        if size:
            sz = self.OX("w:sz")
            sz.set(self.qn("w:val"), str(int(size * 2)))
            rpr.append(sz)
        r.append(rpr)
        t = self.OX("w:t")
        t.text = text
        t.set(self.qn("xml:space"), "preserve")
        r.append(t)
        h.append(r)
        paragraph._p.append(h)

    # ---------- blocks ----------
    def cover(self, blocks: list[Block]):
        from docx.enum.text import WD_BREAK
        m, Pt = self.meta, self.Pt
        top = 110
        if str(self.st.get("logo_position", "header")) in ("cover", "both"):
            lp = self.doc.add_paragraph()
            if self._logo(lp, float(self.st["logo_width_cm"])):
                lp.paragraph_format.space_after = Pt(12)
                top = 60
        p = self.doc.add_paragraph()
        p.paragraph_format.space_before = Pt(top)
        r = p.add_run(plain(str(m.get("title", ""))))
        r.bold, r.font.size, r.font.color.rgb = True, Pt(24), self._rgb(self.st["color"])
        if m.get("subtitle"):
            p = self.doc.add_paragraph()
            r = p.add_run(plain(str(m["subtitle"])))
            r.font.size, r.font.color.rgb = Pt(13), self._rgb(self.st["muted"])
            self._border(p, "bottom", self.st["color"], 12, 8)
            p.paragraph_format.space_after = Pt(18)
        pairs = []
        for item in m.get("fields") or []:
            if isinstance(item, dict):
                pairs += [(str(k), str(v)) for k, v in item.items()]
            elif str(item).strip():
                pairs.append(("", str(item)))
        if pairs and str(self.st.get("cover_layout", "lines")) == "form":
            # the form of a corporate template: one shaded label cell and one value cell per field
            self.card(Block("card", children=[(k, [Block("para", text=v)]) for k, v in pairs]))
        else:
            for k, v in pairs:
                p = self.doc.add_paragraph()
                p.paragraph_format.space_after = Pt(3)
                if k:
                    p.add_run(f"{k}: ").bold = True
                self.add_runs(p, v)
        if m.get("notice"):
            p = self.doc.add_paragraph()
            p.paragraph_format.space_before = Pt(14)
            self.add_runs(p, str(m["notice"]), size=9.5, base={"italic": True})
        revs = m.get("revisions") or []
        if revs:
            p = self.doc.add_paragraph()
            p.paragraph_format.space_before = Pt(18)
            r = p.add_run(self.L["revisions"])
            r.bold = True
            rows = [self.L["rev_cols"]]
            for rv in revs:
                rows.append([c.strip() for c in str(rv).split("|")] if not isinstance(rv, dict)
                            else [str(x) for x in rv.values()])
            self.table(Block("table", rows=rows))
        self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    def toc(self, blocks: list[Block]):
        from docx.enum.text import WD_BREAK, WD_TAB_ALIGNMENT, WD_TAB_LEADER
        if self.meta.get("toc") is False:
            return
        p = self.doc.add_paragraph()
        r = p.add_run(str(self.meta.get("toc_title") or self.L["toc"]))
        r.bold, r.font.size, r.font.color.rgb = True, self.Pt(16), self._rgb(self.st["color"])
        entries = toc_entries(blocks, int(self.meta.get("toc_levels", 2)))
        usable = 21.0 - 2 * float(self.st["margin_cm"])
        # one paragraph holds the field start; entries are the cached result
        first = True
        for idx, (lvl, text) in enumerate(entries):
            q = self.doc.add_paragraph()
            q.paragraph_format.space_after = self.Pt(2 if lvl >= 2 else 4)
            q.paragraph_format.left_indent = self.Cm(0.6 * max(0, lvl - 1))
            q.paragraph_format.tab_stops.add_tab_stop(self.Cm(usable), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
            if first:
                self._field_begin(q, f'TOC \\o "1-{int(self.meta.get("toc_levels", 2))}" \\h \\z \\u')
                first = False
            run = q.add_run(text)
            if lvl <= 1:
                run.bold = True
            num = ""
            if self.page_numbers and idx < len(self.page_numbers) and self.page_numbers[idx]:
                num = str(self.page_numbers[idx])
            q.add_run("\t" + num)
            if idx == len(entries) - 1:
                self._field_end(q)
        if first:  # no headings at all: an empty TOC field
            q = self.doc.add_paragraph()
            self._field_begin(q, 'TOC \\o "1-2" \\h \\z \\u')
            self._field_end(q)
        self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    def _field_begin(self, paragraph, instr):
        r = paragraph.add_run()
        b = self.OX("w:fldChar")
        b.set(self.qn("w:fldCharType"), "begin")
        b.set(self.qn("w:dirty"), "true")
        r._r.append(b)
        r = paragraph.add_run()
        it = self.OX("w:instrText")
        it.set(self.qn("xml:space"), "preserve")
        it.text = f" {instr} "
        r._r.append(it)
        r = paragraph.add_run()
        s = self.OX("w:fldChar")
        s.set(self.qn("w:fldCharType"), "separate")
        r._r.append(s)

    def _field_end(self, paragraph):
        r = paragraph.add_run()
        e = self.OX("w:fldChar")
        e.set(self.qn("w:fldCharType"), "end")
        r._r.append(e)

    def render(self, blocks: list[Block], container=None):
        for b in blocks:
            getattr(self, b.kind)(b, container) if b.kind in ("heading", "para", "list", "code", "image",
                                                             "callout", "card", "part", "pagebreak",
                                                             "rule") else self.table(b, container)

    def _par(self, container):
        return (container.add_paragraph() if container is not None else self.doc.add_paragraph())

    def heading(self, b: Block, container=None):
        if container is not None:  # headings inside containers become bold paragraphs
            p = container.add_paragraph()
            self.add_runs(p, b.text, base={"bold": True})
            return
        h = self.doc.add_heading(level=min(b.level, 4))
        self.add_runs(h, b.text)

    def para(self, b: Block, container=None, size=None):
        p = self._par(container)
        self.add_runs(p, b.text, size=size)
        return p

    def list(self, b: Block, container=None, size=None):
        styles = [s.name for s in self.doc.styles]
        for level, ordered, num, text in b.items:
            p = self._par(container)
            pf = p.paragraph_format
            if ordered:
                pf.left_indent = self.Cm(0.75 + 0.6 * level)
                pf.first_line_indent = self.Cm(-0.6)
                pf.space_after = self.Pt(3)
                p.add_run(f"{num}.\t")
                pf.tab_stops.add_tab_stop(self.Cm(0.75 + 0.6 * level))
            else:
                name = "List Bullet" if level == 0 else f"List Bullet {level + 1}"
                p.style = self.doc.styles[name if name in styles else "List Bullet"]
                if container is not None:  # tighter indent inside table cells
                    pf.left_indent = self.Cm(0.45 + 0.45 * level)
                    pf.first_line_indent = self.Cm(-0.35)
            self.add_runs(p, text, size=size)

    def code(self, b: Block, container=None):
        tbl = self._box(container, fill="F2F2F2", border="D9D9D9")
        cell = tbl.cell(0, 0)
        lines = b.text.split("\n") or [""]
        first = cell.paragraphs[0]
        for n, line in enumerate(lines):
            p = first if n == 0 else cell.add_paragraph()
            p.paragraph_format.space_after = self.Pt(0)
            p.paragraph_format.line_spacing = 1.0
            r = p.add_run(line if line else "\u00a0")
            r.font.name = self.st["mono"]
            r._r.get_or_add_rPr().get_or_add_rFonts().set(self.qn("w:cs"), self.st["mono"])
            r.font.size = self.Pt(float(self.st["code_size"]))
        self._after_box(container)

    def _box(self, container, fill: str, border: str, left: str | None = None):
        parent = container if container is not None else self.doc
        tbl = parent.add_table(rows=1, cols=1)
        tbl.autofit = False
        tpr = tbl._tbl.tblPr
        borders = self.OX("w:tblBorders")
        for side in ("top", "left", "bottom", "right"):
            el = self.OX(f"w:{side}")
            if side == "left" and left:
                el.set(self.qn("w:val"), "single")
                el.set(self.qn("w:sz"), "24")
                el.set(self.qn("w:color"), left)
            else:
                el.set(self.qn("w:val"), "single" if border else "nil")
                el.set(self.qn("w:sz"), "4")
                el.set(self.qn("w:color"), border or "auto")
            el.set(self.qn("w:space"), "0")
            borders.append(el)
        tpr.append(borders)
        tcpr = tbl.cell(0, 0)._tc.get_or_add_tcPr()
        self._shade(tcpr, fill)
        width = self.Cm(21.0 - 2 * float(self.st["margin_cm"]) - (1.0 if container is not None else 0))
        self._set_widths(tbl, [width])
        return tbl

    def _after_box(self, container):
        p = self._par(container)
        p.paragraph_format.space_after = self.Pt(2)
        fmt = p.paragraph_format
        fmt.line_spacing = 0.6

    def callout(self, b: Block, container=None):
        color = CALLOUT_COLORS.get(b.lang, "2E75B6")
        fill = CALLOUT_FILLS.get(b.lang, "EAF1FB")
        tbl = self._box(container, fill=fill, border="", left=color)
        cell = tbl.cell(0, 0)
        title = b.title or self.L.get(b.lang, self.L["note"])
        p = cell.paragraphs[0]
        r = p.add_run(title)
        r.bold = True
        r.font.color.rgb = self._rgb(color)
        p.paragraph_format.space_after = self.Pt(2)
        self.render(b.children, cell)
        self._trim_cell(cell)
        self._after_box(container)

    def _trim_cell(self, cell):
        # python-docx cells start with one empty paragraph; drop trailing empty ones
        ps = cell.paragraphs
        if len(ps) > 1 and not ps[-1].text.strip() and not ps[-1]._p.findall(".//" + self.qn("w:drawing")):
            ps[-1]._p.getparent().remove(ps[-1]._p)

    def card(self, b: Block, container=None):
        parent = container if container is not None else self.doc
        rows = [f for f in b.children]
        tbl = parent.add_table(rows=len(rows), cols=2)
        tbl.style = self.doc.styles["Table Grid"]
        tbl.autofit = False
        usable = 21.0 - 2 * float(self.st["margin_cm"])
        w1, w2 = self.Cm(usable * 0.24), self.Cm(usable * 0.76)
        for i, (label, blocks) in enumerate(rows):
            c1, c2 = tbl.cell(i, 0), tbl.cell(i, 1)
            c1.width, c2.width = w1, w2
            self._shade(c1._tc.get_or_add_tcPr(), self.st["accent"])
            p = c1.paragraphs[0]
            r = p.add_run(label)
            r.bold, r.font.size = True, self.Pt(float(self.st["table_size"]))
            first = True
            for blk in blocks:
                if blk.kind == "para":
                    p = c2.paragraphs[0] if first else c2.add_paragraph()
                    self.add_runs(p, blk.text, size=float(self.st["table_size"]))
                    p.paragraph_format.space_after = self.Pt(2)
                elif blk.kind == "list":
                    if first:
                        c2.paragraphs[0]._p.getparent().remove(c2.paragraphs[0]._p)
                    self.list(blk, c2, size=float(self.st["table_size"]))
                else:
                    self.render([blk], c2)
                first = False
            self._trim_cell(c2)
        self._set_widths(tbl, [w1, w2])
        self._cant_split(tbl)
        # keep a card on one page: every row holds on to the next one
        for row in tbl.rows[:-1]:
            for cell in row.cells:
                for para in cell.paragraphs:
                    para.paragraph_format.keep_with_next = True
        self._after_box(container)

    def _set_widths(self, tbl, widths):
        """Cell widths alone are ignored by LibreOffice: set the grid and the table width too."""
        for j, w in enumerate(widths):
            tbl.columns[j].width = w
            for cell in tbl.columns[j].cells:
                cell.width = w
        tpr = tbl._tbl.tblPr
        tblw = tpr.find(self.qn("w:tblW"))
        if tblw is None:
            tblw = self.OX("w:tblW")
            tpr.append(tblw)
        tblw.set(self.qn("w:type"), "dxa")
        tblw.set(self.qn("w:w"), str(int(sum(w for w in widths) / 635)))
        layout = self.OX("w:tblLayout")
        layout.set(self.qn("w:type"), "fixed")
        tpr.append(layout)

    def _cant_split(self, tbl):
        for row in tbl.rows:
            trpr = row._tr.get_or_add_trPr()
            el = self.OX("w:cantSplit")
            trpr.append(el)

    def table(self, b: Block, container=None):
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        parent = container if container is not None else self.doc
        ncols = max(len(r) for r in b.rows)
        rows = [r + [""] * (ncols - len(r)) for r in b.rows]
        tbl = parent.add_table(rows=len(rows), cols=ncols)
        tbl.style = self.doc.styles["Table Grid"]
        tbl.autofit = False
        usable = 21.0 - 2 * float(self.st["margin_cm"]) - (1.0 if container is not None else 0)
        if b.widths and len(b.widths) == ncols:
            fr = [w / sum(b.widths) for w in b.widths]
        else:
            lens = [max(min(len(plain(r[c])), 60) for r in rows) + 4 for c in range(ncols)]
            fr = [l / sum(lens) for l in lens]
            fr = [max(f, 0.08) for f in fr]
            fr = [f / sum(fr) for f in fr]
        size = float(self.st["table_size"])
        for i, row in enumerate(rows):
            for j, text in enumerate(row):
                cell = tbl.cell(i, j)
                cell.width = self.Cm(usable * fr[j])
                parts = re.split(r"<br\s*/?>", text)
                for k, part in enumerate(parts):
                    p = cell.paragraphs[0] if k == 0 else cell.add_paragraph()
                    p.paragraph_format.space_after = self.Pt(1)
                    self.add_runs(p, part.strip(), size=size, base={"bold": True} if i == 0 else None)
                if i == 0:
                    self._shade(cell._tc.get_or_add_tcPr(), self.st["accent"])
        self._set_widths(tbl, [self.Cm(usable * f) for f in fr])
        hdr = tbl.rows[0]._tr.get_or_add_trPr()
        hdr.append(self.OX("w:tblHeader"))
        self._cant_split(tbl)
        if b.caption:
            p = self._par(container)
            p.paragraph_format.space_before = self.Pt(3)
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            self.add_runs(p, f"{self.L['table']} {b.level} – {b.caption}", size=8.5,
                          base={"italic": True})
        else:
            self._after_box(container)

    def image(self, b: Block, container=None):
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        path = (self.base / b.path) if not Path(b.path).is_absolute() else Path(b.path)
        p = self._par(container)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.keep_with_next = True
        if not path.is_file():
            r = p.add_run(f"[missing image: {b.path}]")
            r.font.color.rgb = self._rgb("C00000")
        else:
            usable = 21.0 - 2 * float(self.st["margin_cm"]) - (1.0 if container is not None else 0)
            want = b.width_cm or usable
            try:
                from docx.image.image import Image as DocxImage  # type: ignore
                img = DocxImage.from_file(str(path))
                native_cm = img.px_width / (img.horz_dpi or 96) * 2.54
                want = min(want, native_cm, usable)
            except Exception:
                want = min(want, usable)
            p.add_run().add_picture(str(path), width=self.Cm(want))
        c = self._par(container)
        c.alignment = WD_ALIGN_PARAGRAPH.CENTER
        self.add_runs(c, f"{self.L['figure']} {b.level} – {b.caption}" if b.caption else f"{self.L['figure']} {b.level}",
                      size=8.5, base={"italic": True})

    def part(self, b: Block, container=None):
        from docx.enum.text import WD_BREAK
        self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        p = self.doc.add_paragraph()
        p.paragraph_format.space_before = self.Pt(140)
        ppr = p._p.get_or_add_pPr()
        ol = self.OX("w:outlineLvl")
        ol.set(self.qn("w:val"), "0")
        ppr.append(ol)
        r = p.add_run(plain(b.title))
        r.bold, r.font.size, r.font.color.rgb = True, self.Pt(22), self._rgb(self.st["color"])
        self._border(p, "bottom", self.st["color"], 12, 8)
        intro = [x for x in b.children if x.kind in ("para", "list")]
        rest = [x for x in b.children if x.kind not in ("para", "list")]
        for x in intro:
            if x.kind == "para":
                q = self.para(x, size=12)
                for r in q.runs:
                    r.font.color.rgb = self._rgb(self.st["muted"])
            else:
                self.list(x)
        self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        self.render(rest)

    def pagebreak(self, b: Block, container=None):
        from docx.enum.text import WD_BREAK
        self._par(container).add_run().add_break(WD_BREAK.PAGE)

    def rule(self, b: Block, container=None):
        p = self._par(container)
        self._border(p, "bottom", "BFBFBF", 4)

    def finish(self, out: Path, update_fields: bool):
        cp = self.doc.core_properties
        cp.title = plain(str(self.meta.get("title", "")))
        cp.subject = plain(str(self.meta.get("subtitle", "")))
        if self.meta.get("author"):
            cp.author = str(self.meta["author"])
        cp.language = self.lang
        if update_fields:
            settings = self.doc.settings.element
            uf = self.OX("w:updateFields")
            uf.set(self.qn("w:val"), "true")
            settings.append(uf)
        out.parent.mkdir(parents=True, exist_ok=True)
        self.doc.save(str(out))


def build_docx(meta, style, pack, blocks, base, out: Path, page_numbers, update_fields: bool):
    w = DocxWriter(meta, style, pack, base, page_numbers)
    w.cover(blocks)
    w.toc(blocks)
    w.render(blocks)
    w.finish(out, update_fields)


# ======================================================================================
# Markdown writer
# ======================================================================================
def md_inline(text: str) -> str:
    text = re.sub(r"\[\[([^\]]+)\]\]", r"**[\1]**", text)
    return re.sub(r"<br\s*/?>", " ", text)


def blocks_to_md(blocks: list[Block], L: dict, base_out: Path, base_src: Path) -> list[str]:
    out: list[str] = []
    for b in blocks:
        if b.kind == "heading":
            out += ["#" * b.level + " " + md_inline(b.text), ""]
        elif b.kind == "para":
            out += [md_inline(b.text), ""]
        elif b.kind == "list":
            for level, ordered, num, text in b.items:
                out.append("   " * level + (f"{num}. " if ordered else "- ") + md_inline(text))
            out.append("")
        elif b.kind == "code":
            out += [f"```{b.lang}", b.text, "```", ""]
        elif b.kind == "table":
            ncols = max(len(r) for r in b.rows)
            for i, r in enumerate(b.rows):
                r = r + [""] * (ncols - len(r))
                out.append("| " + " | ".join(md_inline(c).replace("|", "\\|") if "\\|" not in c else md_inline(c) for c in r) + " |")
                if i == 0:
                    out.append("|" + "---|" * ncols)
            if b.caption:
                out += ["", f"*{L['table']} {b.level} – {md_inline(b.caption)}*"]
            out.append("")
        elif b.kind == "image":
            out += [f"![{L['figure']} {b.level} – {b.caption}]({b.path})", "",
                    f"*{L['figure']} {b.level} – {md_inline(b.caption)}*", ""]
        elif b.kind == "callout":
            title = b.title or L.get(b.lang, L["note"])
            inner = blocks_to_md(b.children, L, base_out, base_src)
            out.append(f"> **{title}**")
            out.append(">")
            out += [("> " + l) if l else ">" for l in inner[:-1] if True]
            out.append("")
        elif b.kind == "card":
            for label, bl in b.children:
                inner = blocks_to_md(bl, L, base_out, base_src)
                while inner and not inner[-1]:
                    inner.pop()
                if len(inner) == 1 and not inner[0].startswith(("- ", "1. ")):
                    out += [f"**{label}:** {inner[0]}", ""]
                else:
                    out += [f"**{label}:**", ""] + inner + [""]
        elif b.kind == "part":
            out += ["---", "", f"**{plain(b.title).upper()}**", ""]
            out += blocks_to_md(b.children, L, base_out, base_src)
        elif b.kind == "rule":
            out += ["---", ""]
    return out


def build_md(meta, pack, blocks, out: Path, base: Path):
    L = pack["labels"]
    lines = [f"**{plain(str(meta.get('title', '')))}**", ""]
    if meta.get("subtitle"):
        lines += [f"*{meta['subtitle']}*", ""]
    for item in meta.get("fields") or []:
        if isinstance(item, dict):
            for k, v in item.items():
                lines.append(f"- **{k}:** {v}")
    if meta.get("fields"):
        lines.append("")
    if meta.get("notice"):
        lines += [f"*{meta['notice']}*", ""]
    if meta.get("revisions"):
        lines += [f"**{L['revisions']}**", "", "| " + " | ".join(L["rev_cols"]) + " |", "|---|---|---|---|"]
        for rv in meta["revisions"]:
            lines.append("| " + " | ".join(c.strip() for c in str(rv).split("|")) + " |")
        lines.append("")
    if meta.get("toc") is not False:
        lines += [f"**{meta.get('toc_title') or L['toc']}**", ""]
        for lvl, text in toc_entries(blocks, int(meta.get("toc_levels", 2))):
            anchor = re.sub(r"[^\w\- ]", "", text.lower()).strip().replace(" ", "-")
            lines.append("  " * max(0, lvl - 1) + (f"- [{text}](#{anchor})" if lvl else f"- **{text}**"))
        lines.append("")
    lines += blocks_to_md(blocks, L, out.parent, base)
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip() + "\n"
    write_text(out, text)
    # copy referenced images next to the Markdown file, keeping relative paths
    for b in _walk(blocks):
        if b.kind == "image" and not Path(b.path).is_absolute():
            src, dst = base / b.path, out.parent / b.path
            if src.is_file() and src.resolve() != dst.resolve():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dst)


def _walk(blocks):
    for b in blocks:
        yield b
        if b.kind in ("callout", "part"):
            yield from _walk(b.children)
        if b.kind == "card":
            for _, bl in b.children:
                yield from _walk(bl)


# ======================================================================================
# PDF and page numbers
# ======================================================================================
def soffice_binary() -> str | None:
    for name in ("soffice", "libreoffice"):
        p = shutil.which(name)
        if p:
            return p
    for p in (r"C:\Program Files\LibreOffice\program\soffice.exe",
              "/Applications/LibreOffice.app/Contents/MacOS/soffice"):
        if Path(p).exists():
            return p
    return None


def to_pdf(docx_path: Path, outdir: Path) -> Path | None:
    exe = soffice_binary()
    if not exe:
        return None
    outdir.mkdir(parents=True, exist_ok=True)
    profile = Path(tempfile.mkdtemp(prefix="sdg-lo-"))
    try:
        subprocess.run([exe, f"-env:UserInstallation={profile.as_uri()}", "--headless",
                        "--convert-to", "pdf", "--outdir", str(outdir), str(docx_path)],
                       check=True, capture_output=True, timeout=300)
    except Exception as e:
        print(f"warning: LibreOffice conversion failed: {e}", file=sys.stderr)
        return None
    finally:
        shutil.rmtree(profile, ignore_errors=True)
    pdf = outdir / (docx_path.stem + ".pdf")
    return pdf if pdf.exists() else None


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def measure_pages(pdf: Path, entries: list[tuple[int, str]]) -> list[int | None]:
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError:
        return []
    pages = [_norm(p.extract_text() or "") for p in PdfReader(str(pdf)).pages]
    # the TOC itself lists every heading: start searching after the last TOC page
    start = 0
    if entries:
        first, last = _norm(entries[0][1])[:40], _norm(entries[-1][1])[:40]
        toc_from = next((i for i, t in enumerate(pages) if first in t), 0)
        toc_to = next((i for i in range(toc_from, len(pages)) if last in pages[i]), toc_from)
        start = toc_to + 1
    result: list[int | None] = []
    cur = start
    for _, text in entries:
        key = _norm(text)[:50]
        found = None
        for i in range(cur, len(pages)):
            if key and key in pages[i]:
                found = i
                break
        result.append(found + 1 if found is not None else None)
        if found is not None:
            cur = found
    return result


def load_style(meta: dict, profile: Path | None) -> dict:
    """House style: defaults < profile's render-style block < the document's 'style:' map.

    A 'logo' path is resolved against the file that names it. Label overrides (e.g. tip: Buona
    pratica) come from 'labels:' in the profile's render-style block, then from the document's
    top-level 'labels:' map, and are handed to the language pack.
    """
    st = dict(DEFAULT_STYLE)
    labels: dict = {}

    def take(src: dict, base: Path | None):
        for k, v in src.items():
            if k == "labels" and isinstance(v, dict):
                labels.update(v)
            elif k in DEFAULT_STYLE:
                st[k] = v
                if k == "logo" and v and base and not Path(str(v)).is_absolute():
                    st[k] = str((base / str(v)).resolve())

    if profile and profile.is_file():
        text = read_text(profile)
        m = re.search(r"```(?:ya?ml)?\s*\n(# *render-style[^\n]*\n[\s\S]*?)```", text)
        if m:
            take(parse_simple_yaml(m.group(1)), profile.parent)
    if isinstance(meta.get("style"), dict):
        take(meta["style"], Path(str(meta.get("_base", "."))))
    if isinstance(meta.get("labels"), dict):  # the document's own label overrides
        labels.update(meta["labels"])
    for k in ("color", "accent", "muted"):
        st[k] = str(st[k]).lstrip("#").upper()
        if not re.fullmatch(r"[0-9A-F]{6}", st[k]):
            print(f"warning: style '{k}' is not a six-digit hex colour ({st[k] or 'empty'}); the default "
                  f"{DEFAULT_STYLE[k]} is used (write it without '#', or in quotes: \"#1F3864\")", file=sys.stderr)
            st[k] = DEFAULT_STYLE[k]
    for k, v in DEFAULT_STYLE.items():  # numbers may arrive as strings from the line reader
        if isinstance(v, float) and not isinstance(st[k], float):
            try:
                st[k] = float(st[k])
            except (TypeError, ValueError):
                st[k] = v
    st["labels"] = labels
    return st


def main(argv=None) -> int:
    configure_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source")
    ap.add_argument("--to", choices=["docx", "pdf", "md"], required=True)
    ap.add_argument("-o", "--output")
    ap.add_argument("--profile", help="documentation profile with an optional render-style block")
    ap.add_argument("--lang-pack", help="language pack for a language the skill does not ship "
                    "(JSON, same keys as assets/i18n/en.json)")
    ap.add_argument("--no-paginate", action="store_true", help="do not measure TOC page numbers")
    ap.add_argument("--no-update-fields", action="store_true",
                    help="do not ask Word to refresh the table of contents when the file opens")
    args = ap.parse_args(argv)

    src = Path(args.source)
    meta, body = split_front_matter(read_text(src))
    if not meta.get("title"):
        sys.exit("error: the source needs a front-matter 'title'")
    meta["_base"] = str(src.parent)
    blocks = parse_blocks(body.splitlines())
    number_captions(blocks)
    base = src.parent
    out = Path(args.output) if args.output else src.with_suffix("." + args.to)
    if args.to == "md" and out.resolve() == src.resolve():
        out = src.with_name(src.stem + ".out.md")

    profile = Path(args.profile) if args.profile else None
    style = load_style(meta, profile)
    pack = load_lang(meta.get("lang", "it"), args.lang_pack, overrides=style.pop("labels", None))
    if args.to == "md":
        build_md(meta, pack, blocks, out, base)
        print(f"markdown: {out.resolve()}")
        return 0

    docx_out = out if args.to == "docx" else Path(tempfile.mkdtemp(prefix="sdg-")) / (out.stem + ".docx")
    entries = toc_entries(blocks, int(meta.get("toc_levels", 2)))
    numbers = None
    build_docx(meta, style, pack, blocks, base, docx_out, None, not args.no_update_fields)
    if not args.no_paginate and meta.get("toc") is not False and entries:
        tmp = Path(tempfile.mkdtemp(prefix="sdg-pages-"))
        pdf = to_pdf(docx_out, tmp)
        if pdf:
            numbers = measure_pages(pdf, entries)
            missing = sum(1 for n in numbers if n is None)
            if numbers:
                build_docx(meta, style, pack, blocks, base, docx_out, numbers, not args.no_update_fields)
                print(f"table of contents: {len(entries) - missing}/{len(entries)} page numbers measured")
        else:
            print("note: LibreOffice not found - the table of contents is filled by Word when the file opens")
        shutil.rmtree(tmp, ignore_errors=True)

    if args.to == "docx":
        print(f"docx: {docx_out.resolve()}")
        return 0
    pdf = to_pdf(docx_out, out.parent)
    if not pdf:
        sys.exit("error: PDF needs LibreOffice (soffice). Deliver the .docx, or install LibreOffice.")
    if pdf.resolve() != out.resolve():
        shutil.move(str(pdf), str(out))
    print(f"pdf: {out.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
