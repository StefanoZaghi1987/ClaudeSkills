#!/usr/bin/env python3
"""
check_doc.py - quality gate for a document before delivery.

    python check_doc.py <source.md> [--docx built.docx] [--profile profile.md] [-o report.md]
                        [--set other.md ...] [--previous old.md] [--parity other-lang.md ...]
                        [--lang-pack pack.json] [--type-def type.md ...]

Checks on the Markdown source:
  E  cross-references: every ID cited (S01, A03, Q7, ...) is defined exactly once
  E  section references: "procedura 9.4", "capitolo 8", "section 7.2" point to an existing heading
  E  secrets: no password, client secret, token or key survives in the text
  E  images: every figure file exists
  E  containers: every '::: ...' block is closed
  W  heading numbering: 1., 1.1, 1.2, 2. ... and appendices A., B. ... in sequence
  W  IDs defined but never cited; gaps in an ID sequence
  W  empty sections; tables whose rows have a different number of cells; tables without caption
  W  leftover markers: TODO, TBD, FIXME, XXX, «REDACTED»
  W  level-1 chapters out of the order of the front matter's 'type' (references/types/<type>.md
     or a type file passed with --type-def, names from the language pack); I lists the chapters
     of the type not present
  I  open items marked [da confermare] / [to be confirmed] (to list in the delivery message)

Across documents:
  --set       E  "user manual, chapter 5" / an ID of another document of the set must exist there
              W  two documents share an ID prefix; another document is not on the cover
  --previous  E  an ID renumbered since the previous version; version not increased
              W  an ID of the previous version is gone; no 'revisions:' row for the new version
  --parity    E  the same document in another language defines other IDs or other heading numbers
              W  a different number of figures or tables

Words (section, other document, open item, table caption) come from every language pack in
assets/i18n, plus --lang-pack for a language the skill does not ship.

Checks on the built .docx (optional): the file opens, the TOC field is present, no secret in
body, tables, headers and footers, the number of pictures matches the number of figures.

Exit code 1 when an error (E) is found, otherwise 0. Standard library (+ python-docx for --docx).
"""

from __future__ import annotations

import argparse
import difflib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (REDACTED, all_packs, compile_extra_patterns, configure_stdout,  # noqa: E402
                    find_secrets, load_lang, read_text, split_front_matter, write_text)

MARKER_RX = re.compile(r"\b(TODO|TBD|FIXME|XXX)\b|" + re.escape(REDACTED))
# Built from the language packs by set_vocabulary(): a document in any shipped language (or in
# the language of --lang-pack) is checked with the same rules.
SECTION_REF_RX: re.Pattern
OPEN_ITEM_RX: re.Pattern
DOC_WORD_RX: re.Pattern
SELF_WORD_RX: re.Pattern
CAPTION_LINE_RX: re.Pattern


def _alternation(words) -> str:
    return "|".join(re.escape(w) for w in sorted({w for w in words if w}, key=len, reverse=True))


def set_vocabulary(extra_pack: Path | None = None) -> None:
    """Every word the gate recognizes, from every language pack.

    A document is named by a generic word ("manuale", "Handbuch") or by the name or file word of
    a document type ("procedura di manutenzione", "Benutzerhandbuch"); a generic word also
    matches at the end of a compound word ("Konfigurations-handbuch").
    """
    global SECTION_REF_RX, OPEN_ITEM_RX, DOC_WORD_RX, SELF_WORD_RX, CAPTION_LINE_RX
    packs = all_packs(extra_pack)
    section, docs, open_items, selfs, captions = set(), set(), set(), set(), {"Table"}
    for p in packs:
        chk = p.get("check", {})
        section |= set(chk.get("section_words", []))
        docs |= set(chk.get("document_words", []))
        docs |= {str(v) for t in p.get("types", {}).values() for k, v in t.items() if k in ("name", "file")}
        open_items |= set(chk.get("open_item", []))
        selfs |= set(chk.get("self_words", []))
        captions.add(p.get("labels", {}).get("table", ""))
    SECTION_REF_RX = re.compile(rf"(?<![\w.])(?:{_alternation(section)})\s+(\d+(?:\.\d+)*)"
                                r"(?:\s*[–\-]\s*(\d+(?:\.\d+)*))?", re.I)
    OPEN_ITEM_RX = re.compile(rf"\[(?:{_alternation(open_items)})[^\]]*\]", re.I)
    # the whole word: "Betriebshandbuch" starts at "Betriebs", so "diesem" is right before it
    DOC_WORD_RX = re.compile(rf"(?<!\w)\w*?(?:{_alternation(docs)})(?!\w)", re.I)
    # "questo manuale", "questo stesso manuale", "this same guide": at most one word in between
    SELF_WORD_RX = re.compile(rf"(?<!\w)(?:{_alternation(selfs)})\s+(?:\w+\s+)?$", re.I)
    CAPTION_LINE_RX = re.compile(rf"^(?:{_alternation(captions)}):", re.I)


def names_other_document(before: str, own: set[str] | frozenset) -> bool:
    """True when the text before a section reference names another document: a document word in
    the same clause, not preceded by 'this' ("questo documento, capitolo 3" is this document),
    and not a name of the document itself — a set holds one document of each type, so the type's
    own name ("il manuale utente, capitolo 5" said inside the user manual) is this document."""
    clause = re.split(r"[.;]", before)[-1]
    last = None
    for last in DOC_WORD_RX.finditer(clause):
        pass
    return (last is not None
            and clause[last.start():last.end()].strip().lower() not in own
            and not SELF_WORD_RX.search(clause[:last.start()]))


set_vocabulary()


def strip_code(lines: list[str]) -> list[tuple[int, str]]:
    """(line number, text) of the lines outside fenced code blocks and HTML comments."""
    out, fence, comment = [], None, False
    for n, line in enumerate(lines, 1):
        s = line.strip()
        if comment:
            if "-->" in s:
                comment = False
            continue
        if fence:
            if s.startswith(fence):
                fence = None
            continue
        m = re.match(r"^(```+|~~~+)", s)
        if m:
            fence = m.group(1)
            continue
        if s.startswith("<!--") and "-->" not in s:
            comment = True
            continue
        out.append((n, re.sub(r"<!--.*?-->", "", line)))
    return out


def id_prefixes(meta: dict, lines: list[tuple[int, str]]) -> list[str]:
    declared = meta.get("ids")
    if isinstance(declared, str):
        declared = re.findall(r"[A-Z]{1,3}", declared)
    if isinstance(declared, dict):
        declared = list(declared)
    if declared:
        return [str(x) for x in declared]
    found = set()
    for _, l in lines:
        m = re.match(r"^#{2,6}\s+([A-Z]{1,3})\d{1,3}\s*[·–\-:.]", l.strip())
        if m:
            found.add(m.group(1))
        m = re.match(r"^\|\s*\**([A-Z]{1,3})\d{1,3}\**\s*\|", l.strip())
        if m:
            found.add(m.group(1))
    return sorted(found)


def scan_ids(prefixes, lines) -> dict:
    """Definitions and citations of the IDs with the given prefixes.

    defs/refs: {(prefix, number): [line, ...]}; titles: {(prefix, number): title of the definition}.
    """
    scan: dict = {"defs": {}, "refs": {}, "widths": {}, "ref_digits": {}, "titles": {}}
    if not prefixes:
        return scan
    defs, refs, widths, ref_digits, titles = (scan[k] for k in ("defs", "refs", "widths", "ref_digits", "titles"))
    pfx = "|".join(re.escape(p) for p in sorted(prefixes, key=len, reverse=True))
    any_id = re.compile(rf"(?<![A-Za-z0-9_\-#@./])({pfx})(\d{{1,3}})(?![A-Za-z0-9_])")
    def_rx = [rf"^#{{2,6}}\s+\**({pfx})(\d{{1,3}})\**\s*[·–\-:.]",      # ### S01 · title
              rf"^\|\s*\**({pfx})(\d{{1,3}})\**\s*\|",                  # | A01 | ... (table row)
              rf"^\**({pfx})(\d{{1,3}})\s*[–\-·:.]",                    # **Q1 – title**
              rf"^[-*]\s+\**({pfx})(\d{{1,3}})\**\s*[–\-·:.]"]         # - **A01** – ...
    for n, l in lines:
        s = l.strip()
        def_pos = None
        for k, rx in enumerate(def_rx):
            m = re.match(rx, s)
            if m and k == 1 and (m.group(1), int(m.group(2))) in defs:
                break  # a later table keyed by the same IDs (e.g. code references): a citation
            if m:
                key = (m.group(1), int(m.group(2)))
                defs.setdefault(key, []).append(n)
                widths.setdefault(m.group(1), set()).add(len(m.group(2)))
                def_pos = m.start(2)
                rest = s[m.end():]
                title = rest.split("|")[1] if k == 1 and "|" in rest else rest
                titles.setdefault(key, re.sub(r"[*\"“”«»]", "", title).strip(" ·–-:.").lower())
                break
        for m in any_id.finditer(s):
            if def_pos is not None and m.start(2) == def_pos:
                continue
            key = (m.group(1), int(m.group(2)))
            refs.setdefault(key, []).append(n)
            ref_digits.setdefault(key, set()).add(len(m.group(2)))
    return scan


def is_citation(n_digits: int, widths: set[int] | None) -> bool:
    """A prefix followed by n digits cites an ID only with the width the prefix is defined with:
    with S01..S40 defined, "B1" in "SAP B1", "Q1" in "Q1 2026" or "A320" (a model) is text.
    A prefix with no definition counts from two digits."""
    return n_digits in widths if widths else n_digits >= 2


def check_ids(prefixes, lines, issues):
    if not prefixes:
        return
    scan = scan_ids(prefixes, lines)
    defs, refs, widths, ref_digits = scan["defs"], scan["refs"], scan["widths"], scan["ref_digits"]
    for key, where in sorted(refs.items()):
        if key not in defs and any(is_citation(d, widths.get(key[0])) for d in ref_digits[key]):
            issues.append(("E", where[0], f"{key[0]}{key[1]:02d} is cited (lines {', '.join(map(str, where[:5]))}) "
                                          "but never defined"))
    for key, where in sorted(defs.items()):
        if len(where) > 1:
            issues.append(("E", where[1], f"{key[0]}{key[1]:02d} is defined more than once (lines {where})"))
        if key not in refs:
            issues.append(("W", where[0], f"{key[0]}{key[1]:02d} is defined but never cited"))
    for p in prefixes:
        nums = sorted(k[1] for k in defs if k[0] == p)
        missing = [x for x in range(nums[0], nums[-1] + 1) if x not in nums] if nums else []
        if missing:
            issues.append(("W", 0, f"gap in the {p} sequence: {', '.join(f'{p}{x:02d}' for x in missing)} missing"))


def headings(lines):
    out = []
    for n, l in lines:
        m = re.match(r"^(#{1,6})\s+(.*?)\s*#*\s*$", l.strip())
        if m:
            out.append((n, len(m.group(1)), m.group(2)))
    return out


def check_numbering(hs, issues) -> set[str]:
    numbers = set()
    last: list[int] = []
    letter = None
    for n, lvl, text in hs:
        m = re.match(r"^(\d+(?:\.\d+)*)\.?\s", text)
        a = re.match(r"^([A-Z])\.\s", text)
        if m:
            parts = [int(x) for x in m.group(1).split(".")]
            numbers.add(m.group(1))
            if len(parts) == 1:
                expect = [(last[0] + 1) if last else 1]
            else:
                prefix = last[:len(parts) - 1]
                if prefix != parts[:-1]:
                    issues.append(("W", n, f"heading {m.group(1)} is not under section {'.'.join(map(str, parts[:-1]))}"))
                    last = parts
                    continue
                prev = last[len(parts) - 1] if len(last) >= len(parts) else 0
                expect = parts[:-1] + [prev + 1]
            if parts != expect:
                issues.append(("W", n, f"heading number {m.group(1)} out of sequence (expected {'.'.join(map(str, expect))})"))
            last = parts
        elif a:
            if letter and ord(a.group(1)) != ord(letter) + 1:
                issues.append(("W", n, f"appendix {a.group(1)}. out of sequence (after {letter}.)"))
            letter = a.group(1)
            numbers.add(a.group(1))
    return numbers


def check_section_refs(lines, numbers, issues, own):
    for n, l in lines:
        for m in SECTION_REF_RX.finditer(l):
            before = l[max(0, m.start() - 90):m.start()]
            if names_other_document(before, own):
                continue  # a section of another document ("manuale di X, procedura 9.4"): see --set
            for ref in (m.group(1), m.group(2)):
                if ref and ref not in numbers and ref.rstrip(".") not in numbers:
                    issues.append(("E", n, f"'{m.group(0).strip()}' points to {ref}, which is not a heading number"))


def check_structure(lines, body_lines, base: Path, issues):
    hs = headings(lines)
    # empty sections: a heading followed by a heading of the same or higher level
    text_after: dict[int, bool] = {}
    idx = {n: i for i, (n, _) in enumerate(lines)}
    for k, (n, lvl, _) in enumerate(hs):
        nxt = hs[k + 1] if k + 1 < len(hs) else None
        start, end = idx[n] + 1, (idx[nxt[0]] if nxt else len(lines))
        has = any(lines[i][1].strip() for i in range(start, end))
        text_after[n] = has
        if nxt and nxt[1] <= lvl and not has:
            issues.append(("W", n, f"empty section: '{hs[k][2]}'"))
    # containers balanced
    depth = 0
    for n, l in lines:
        s = l.strip()
        if re.match(r"^:::\s*\w+", s):
            depth += 1
        elif s == ":::":
            depth -= 1
            if depth < 0:
                issues.append(("E", n, "':::' closes a block that was never opened"))
                depth = 0
    if depth:
        issues.append(("E", 0, f"{depth} '::: ...' block(s) not closed"))
    # tables
    for i, (n, l) in enumerate(lines):
        s = l.strip()
        if s.startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|?\s*:?-{2,}", lines[i + 1][1]) \
                and (i == 0 or not lines[i - 1][1].strip().startswith("|")):
            width = len(re.findall(r"(?<!\\)\|", s.strip("|"))) + 1
            j = i + 2
            while j < len(lines) and lines[j][1].strip().startswith("|"):
                w = len(re.findall(r"(?<!\\)\|", lines[j][1].strip().strip("|"))) + 1
                if w != width:
                    issues.append(("W", lines[j][0], f"table row has {w} cells, header has {width}"))
                j += 1
            k = j
            while k < len(lines) and not lines[k][1].strip():
                k += 1
            if k >= len(lines) or not CAPTION_LINE_RX.match(lines[k][1].strip()):
                issues.append(("W", n, "table without a 'Table:' caption line"))
    # images
    for n, l in lines:
        m = re.match(r"^!\[(.*?)\]\((\S+?)\)", l.strip())
        if m:
            p = Path(m.group(2))
            if not (p if p.is_absolute() else base / p).is_file():
                issues.append(("E", n, f"image not found: {m.group(2)}"))
            if not m.group(1).strip():
                issues.append(("W", n, f"figure without caption: {m.group(2)}"))


# --------------------------------------------------------------------------------------
# Checks across documents: --set (a documentation set), --previous (a revision),
# --parity (the same document in another language)
# --------------------------------------------------------------------------------------
def load_doc(path: Path, type_defs: list[Path] | None = None) -> dict:
    raw = read_text(path)
    meta, body = split_front_matter(raw)
    offset = raw[: len(raw) - len(body)].count("\n")
    lines = [(n + offset, l) for n, l in strip_code(body.splitlines())]
    hs = headings(lines)
    numbered = [m.group(1) for _, _, t in hs for m in [re.match(r"^(\d+(?:\.\d+)*|[A-Z])\.?\s", t)] if m]
    prefixes = id_prefixes(meta, lines)
    # the card prefix: the first one declared in 'ids', else the type's default when the document
    # uses it; with neither, unknown (no shared-prefix warning on a guess)
    if meta.get("ids"):
        card = prefixes[0] if prefixes else None
    else:
        default = (load_type(str(meta.get("type") or ""), type_defs) or {}).get("default_prefix")
        card = default if default in prefixes else None
    return {"path": path, "meta": meta, "raw": raw, "lines": lines, "headings": hs,
            "numbers": set(numbered), "numbered": numbered, "prefixes": prefixes, "card": card,
            "ids": scan_ids(prefixes, lines),
            "figures": sum(1 for _, l in lines if re.match(r"^!\[.*?\]\(\S+?\)", l.strip())),
            "tables": sum(1 for _, l in lines if CAPTION_LINE_RX.match(l.strip()))}


def _title(doc: dict) -> str:
    return re.sub(r"[*_`]", "", str(doc["meta"].get("title", doc["path"].stem)))


def doc_names(doc: dict, extra_pack: Path | None = None) -> set[str]:
    """Ways a sentence can name this document: its title, its type name in its language."""
    names = {_title(doc).lower()}
    t = str(doc["meta"].get("type", ""))
    if t:
        tp = load_lang(doc["meta"].get("lang", "it"), extra_pack, quiet=True).get("types", {}).get(t, {})
        names |= {str(tp.get("name", "")).lower(), str(tp.get("file", "")).lower()}
    for sep in (" – ", " - ", ": "):  # "ShipLabelApp – Manuale utente" is also named by its second half
        if sep in _title(doc):
            names.add(_title(doc).split(sep, 1)[1].lower())
    return {n for n in names if len(n) > 3}


def check_set(doc: dict, others: list[dict], issues, extra_pack: Path | None = None) -> None:
    named = [(o, doc_names(o, extra_pack)) for o in others]
    own = doc_names(doc, extra_pack)
    # section references to another document of the set
    for n, l in doc["lines"]:
        for m in SECTION_REF_RX.finditer(l):
            before = l[max(0, m.start() - 90):m.start()].lower()
            if not names_other_document(before, own):
                continue
            hits = [o for o, names in named if any(nm in before for nm in names)]
            if len(hits) != 1:
                continue  # a document outside the set, or a sentence that names two
            for ref in (m.group(1), m.group(2)):
                if ref and ref not in hits[0]["numbers"] and ref.rstrip(".") not in hits[0]["numbers"]:
                    issues.append(("E", n, f"'{m.group(0).strip()}' points to {ref} in "
                                           f"'{_title(hits[0])}', which has no such heading"))
    # IDs of another document cited here. The card prefix (the first of 'ids') must differ
    # between documents; known behaviours (A) and queries (Q) are local to each document.
    own_prefixes = set(doc["prefixes"])
    card = doc["card"]
    for o in others:
        if card and o["card"] == card:
            issues.append(("W", 0, f"card prefix {card} is also the card prefix of '{_title(o)}': "
                                   "give each document of the set its own card letter"))
        foreign = [p for p in o["prefixes"] if p not in own_prefixes]
        if not foreign:
            continue
        pfx = "|".join(re.escape(p) for p in sorted(foreign, key=len, reverse=True))
        rx = re.compile(rf"(?<![A-Za-z0-9_\-#@./])({pfx})(\d{{1,3}})(?![A-Za-z0-9_])")
        for n, l in doc["lines"]:
            for m in rx.finditer(l):
                if (m.group(1), int(m.group(2))) not in o["ids"]["defs"] and \
                        is_citation(len(m.group(2)), o["ids"]["widths"].get(m.group(1))):
                    issues.append(("E", n, f"{m.group(0)} is cited as an ID of '{_title(o)}', "
                                           "which does not define it"))
    # every other document of the set appears on the cover ("Related documents")
    cover = str(doc["meta"]).lower()
    for o in others:
        if not any(nm in cover for nm in doc_names(o)):
            issues.append(("W", 0, f"'{_title(o)}' is not named among the related documents on the cover"))


def _version(meta: dict) -> tuple[int, ...] | None:
    cands = [meta.get("version")]
    version_labels = {str(p.get("fields", {}).get("version", "")).lower() for p in all_packs()}
    for item in meta.get("fields") or []:
        if isinstance(item, dict):
            cands += [v for k, v in item.items() if str(k).strip().lower() in version_labels]
    for c in cands:
        m = re.search(r"\d+(?:\.\d+)+|\d+", str(c or ""))
        if m:
            return tuple(int(x) for x in m.group(0).split("."))
    return None


def check_previous(doc: dict, prev: dict, issues) -> None:
    old, new = prev["ids"]["defs"], doc["ids"]["defs"]
    new_by_title = {t: k for k, t in doc["ids"]["titles"].items() if t}
    for key in sorted(old):
        if key in new:
            continue
        title = prev["ids"]["titles"].get(key, "")
        moved = new_by_title.get(title)
        if title and moved and moved != key:
            issues.append(("E", 0, f"{key[0]}{key[1]:02d} of the previous version is now "
                                   f"{moved[0]}{moved[1]:02d}: IDs are stable, restore the old number"))
        else:
            issues.append(("W", 0, f"{key[0]}{key[1]:02d} of the previous version is gone: keep it "
                                   "(marked as retired) or record the removal in the revision note"))
    v_old, v_new = _version(prev["meta"]), _version(doc["meta"])
    if v_old is None or v_new is None:
        issues.append(("W", 0, "version not found in the front matter ('version:' or the version field)"))
    elif v_new <= v_old:
        issues.append(("E", 0, f"version {'.'.join(map(str, v_new))} is not greater than the previous "
                               f"{'.'.join(map(str, v_old))}"))
    revs = doc["meta"].get("revisions") or []
    if v_new and revs and not any(str(r).strip().startswith(".".join(map(str, v_new))) for r in revs):
        issues.append(("W", 0, f"no 'revisions:' row for version {'.'.join(map(str, v_new))}"))


def check_parity(doc: dict, other: dict, issues) -> None:
    a, b = set(doc["ids"]["defs"]), set(other["ids"]["defs"])
    name = _title(other)
    for key in sorted(a - b):
        issues.append(("E", 0, f"{key[0]}{key[1]:02d} is defined here but not in '{name}'"))
    for key in sorted(b - a):
        issues.append(("E", 0, f"{key[0]}{key[1]:02d} is defined in '{name}' but not here"))
    if doc["numbered"] != other["numbered"]:
        diff = next((i for i, (x, y) in enumerate(zip(doc["numbered"], other["numbered"])) if x != y),
                    min(len(doc["numbered"]), len(other["numbered"])))
        here = doc["numbered"][diff] if diff < len(doc["numbered"]) else "(end)"
        there = other["numbered"][diff] if diff < len(other["numbered"]) else "(end)"
        issues.append(("E", 0, f"heading numbers diverge from '{name}' at heading {diff + 1}: "
                               f"{here} here, {there} there"))
    for what in ("figures", "tables"):
        if doc[what] != other[what]:
            issues.append(("W", 0, f"{doc[what]} {what} here, {other[what]} in '{name}'"))


# --------------------------------------------------------------------------------------
# Chapters of the document type (references/types/<type>.md or a --type-def file,
# names from the language pack)
# --------------------------------------------------------------------------------------
TYPES_DIR = Path(__file__).resolve().parent.parent / "references" / "types"


def load_type(key: str, extra: list[Path] | None = None) -> dict | None:
    """The type's definition: files passed with --type-def first (an organization's own type,
    kept beside the profile or in the work folder, or its variant of a shipped type), then the
    skill's registry. An extra file matches by its front-matter 'key', or by its name."""
    for p in extra or []:
        if p.is_file():
            tdef = split_front_matter(read_text(p))[0]
            if str(tdef.get("key") or p.stem) == key:
                return tdef
    p = TYPES_DIR / f"{key}.md"
    return split_front_matter(read_text(p))[0] if p.is_file() else None


def _norm_heading(t: str) -> str:
    t = re.sub(r"^(?:\d+(?:\.\d+)*|[A-Z])\.?\s+", "", t.strip())
    t = re.sub(r"[*_`]", "", t).replace("–", "-").replace("...", "…")
    return re.sub(r"\s+", " ", t).strip(" .:…").lower()


def check_chapters(meta: dict, lines, issues, extra_pack: Path | None = None,
                   type_defs: list[Path] | None = None) -> None:
    """Level-1 chapters follow the type's order, with the language pack's names."""
    key = str(meta.get("type") or "")
    if not key:
        return
    tdef = load_type(key, type_defs)
    if tdef is None:
        known = ", ".join(sorted(p.stem for p in TYPES_DIR.glob("*.md")))
        issues.append(("W", 0, f"unknown document type '{key}' (known: {known}); "
                               "a type of your own is passed with --type-def"))
        return
    variants = tdef.get("variants") or ["default"]
    variant = str(meta.get("variant") or variants[0])
    chapters = (tdef.get("chapters") or {}).get(variant)
    if not chapters:
        issues.append(("W", 0, f"type '{key}' has no variant '{variant}' (variants: {', '.join(map(str, variants))})"))
        return
    names = load_lang(meta.get("lang", "it"), extra_pack, quiet=True)["chapters"]
    pats = []
    for c in chapters:
        k = str(c).rstrip("*")
        # a placeholder ("Funzioni di {area}", "Functions for {role}") is filled by the writer
        rx = re.sub(r"\\\{\w+\\\}", ".+", re.escape(_norm_heading(str(names.get(k, k)))))
        pats.append((k, re.compile(f"^{rx}$"), str(c).endswith("*")))
    named = [rx for _, rx, rep in pats if not rep]
    named_names = {_norm_heading(str(names.get(k, k))): str(names.get(k, k)) for k, _, rep in pats if not rep}

    def near_miss(t: str) -> str | None:
        """The chapter name a heading is almost equal to (a typo), if any."""
        close = difflib.get_close_matches(t, list(named_names), n=1, cutoff=0.85)
        return named_names[close[0]] if close else None

    def fits(i: int, t: str) -> bool:
        # an area chapter ("{area}", "Funzioni di {area}") is the last choice: a heading that is
        # the name of another chapter of the type, or almost (a typo), is never an area
        k, rx, rep = pats[i]
        return bool(rx.match(t)) and not (rep and (any(r.match(t) for r in named) or near_miss(t)))

    pos, found = 0, set()
    for n, lvl, text in headings(lines):
        if lvl != 1:
            continue
        t = _norm_heading(text)
        idx = next((i for i in range(pos, len(pats)) if fits(i, t)), None)
        if idx is None:
            earlier = next((i for i in range(len(pats)) if fits(i, t)), None)
            if earlier is not None and pats[earlier][0] in found and not pats[earlier][2]:
                issues.append(("W", n, f"chapter '{text}' appears more than once"))
            elif earlier is not None:
                found.add(pats[earlier][0])
                issues.append(("W", n, f"chapter '{text}' is out of the order of the {key} type"))
            else:
                hint = near_miss(t)
                issues.append(("W", n, f"chapter '{text}' is not a chapter of the {key} type ({variant}) "
                                       "with the language pack's name" + (f" (did you mean '{hint}'?)" if hint else "")))
            continue
        found.add(pats[idx][0])
        pos = idx if pats[idx][2] else idx + 1
    missing = [re.sub(r"\{\w+\}", "…", str(names.get(k, k))) for k, _, rep in pats if k not in found and not rep]
    if missing:
        issues.append(("I", 0, f"chapters of the {key} type not present (fine when the sources give "
                               f"nothing for them): {', '.join(missing)}"))


def check_docx(path: Path, extra, n_figures: int, issues):
    try:
        import docx  # type: ignore
    except ImportError:
        issues.append(("W", 0, "python-docx not installed: .docx checks skipped"))
        return
    try:
        d = docx.Document(str(path))
    except Exception as e:
        issues.append(("E", 0, f"the .docx cannot be opened: {e}"))
        return
    texts = [p.text for p in d.paragraphs]
    for t in d.tables:
        for row in t.rows:
            for c in row.cells:
                texts.append(c.text)
    for s in d.sections:
        for part in (s.header, s.footer, s.first_page_header, s.first_page_footer):
            texts += [p.text for p in part.paragraphs]
    for h in find_secrets("\n".join(texts), extra):
        issues.append(("E", 0, f"docx: possible secret ({h['kind']})"))
    xml = d.element.xml
    if "TOC \\o" not in xml and " TOC " not in xml:
        issues.append(("W", 0, "docx: no table-of-contents field"))
    pics = xml.count("<pic:pic")
    if pics < n_figures:
        issues.append(("E", 0, f"docx: {pics} pictures for {n_figures} figures"))


def main(argv=None) -> int:
    configure_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source")
    ap.add_argument("--docx")
    ap.add_argument("--profile")
    ap.add_argument("-o", "--output")
    ap.add_argument("--set", nargs="+", default=[], metavar="MD", help="the other documents of the set")
    ap.add_argument("--previous", metavar="MD", help="the master of the previous version")
    ap.add_argument("--parity", nargs="+", default=[], metavar="MD",
                    help="the same document in other languages")
    ap.add_argument("--lang-pack", help="language pack of a language the skill does not ship")
    ap.add_argument("--type-def", action="append", default=[], metavar="MD",
                    help="a document-type file of your own (beside the profile or in the work "
                         "folder): its chapters are checked like the shipped types'")
    args = ap.parse_args(argv)
    pack = Path(args.lang_pack) if args.lang_pack else None
    set_vocabulary(pack)
    type_defs = [Path(p) for p in args.type_def]
    for p in type_defs:
        if not p.is_file():
            sys.exit(f"error: --type-def file not found: {p}")

    src = Path(args.source)
    raw = read_text(src)
    meta, body = split_front_matter(raw)
    offset = raw[: len(raw) - len(body)].count("\n")
    body_lines = body.splitlines()
    lines = [(n + offset, l) for n, l in strip_code(body_lines)]
    issues: list[tuple[str, int, str]] = []

    extra = []
    if args.profile:
        from extract_sources import secret_patterns_from_profile
        extra = compile_extra_patterns(secret_patterns_from_profile(Path(args.profile)))
    if not meta.get("title"):
        issues.append(("E", 1, "front matter has no 'title'"))
    for h in find_secrets(raw, extra):
        issues.append(("E", h["line"], f"possible secret ({h['kind']}): replace it with where the secret is kept"))
    numbers = check_numbering(headings(lines), issues)
    doc = load_doc(src, type_defs)
    check_section_refs(lines, numbers, issues, doc_names(doc, pack))
    check_ids(id_prefixes(meta, lines), lines, issues)
    check_structure(lines, body_lines, src.parent, issues)
    check_chapters(meta, lines, issues, pack, type_defs)
    for n, l in lines:
        for m in MARKER_RX.finditer(l):
            issues.append(("W", n, f"leftover marker '{m.group(0)}'"))
    open_items = [(n, m.group(0), l.strip()) for n, l in lines for m in OPEN_ITEM_RX.finditer(l)]
    n_fig = sum(1 for _, l in lines if re.match(r"^!\[.*?\]\(\S+?\)", l.strip()))
    if args.docx:
        check_docx(Path(args.docx), extra, n_fig, issues)
    if args.set or args.previous or args.parity:
        if args.set:
            check_set(doc, [load_doc(Path(p), type_defs) for p in args.set], issues, pack)
        if args.previous:
            check_previous(doc, load_doc(Path(args.previous), type_defs), issues)
        for p in args.parity:
            check_parity(doc, load_doc(Path(p), type_defs), issues)

    errors = [i for i in issues if i[0] == "E"]
    warns = [i for i in issues if i[0] == "W"]
    out = [f"# Quality check: {src.name}", "",
           f"{len(errors)} error(s), {len(warns)} warning(s), {len(open_items)} open item(s), "
           f"{len(headings(lines))} headings, {n_fig} figures.", ""]
    for sev, title in (("E", "Errors"), ("W", "Warnings"), ("I", "Notes")):
        group = sorted((i for i in issues if i[0] == sev), key=lambda x: x[1])
        if group:
            out += [f"## {title}", ""] + [f"- line {n}: {msg}" if n else f"- {msg}" for _, n, msg in group] + [""]
    if open_items:
        out += ["## Open items (list them in the delivery message)", ""]
        out += [f"- line {n}: {txt[:160]}" for n, _, txt in open_items] + [""]
    report = "\n".join(out)
    if args.output:
        write_text(Path(args.output), report)
        print(f"{len(errors)} error(s), {len(warns)} warning(s): {Path(args.output).resolve()}")
    else:
        print(report)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
