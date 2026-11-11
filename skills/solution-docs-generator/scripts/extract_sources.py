#!/usr/bin/env python3
"""
extract_sources.py - turn a mixed set of sources into one redacted, citable text corpus.

    python extract_sources.py --out <corpus-dir> [--profile profile.md] [--label NAME=PATH ...] \
                              <file-or-folder> [<file-or-folder> ...]

Every input (a file, or a whole folder such as a repository checkout, a project folder on a
network share, or an export of mails) becomes one source with a stable ID (SRC-01, SRC-02, ...).
Each file inside it is converted to UTF-8 text under <corpus-dir>/<ID>/, keeping its relative
path, with secrets replaced by «REDACTED». Images are copied as they are, and the pictures
embedded in Word files are extracted, so screenshots can be reused.

Outputs:
    <corpus-dir>/INDEX.md       one table row per source, then per-file warnings
    <corpus-dir>/manifest.json  the same data, machine-readable
    <corpus-dir>/<ID>/...       extracted text (.txt appended), copied images and code

Readers: plain text and code (always), .docx (python-docx), .pdf (pypdf), .xlsx/.xlsm (openpyxl),
.pptx (python-pptx), .msg (extract-msg), .eml (standard library), .html. Transcripts (.vtt, .srt,
.sbv; files named *transcri*/*trascri*; every --transcript input) are normalized by transcript.py,
whatever their format (subtitles, engine JSON, TSV/CSV, text, Word, PDF). Legacy .doc/.rtf/.odt/.xls/.ppt are converted with LibreOffice when it is
installed. A missing optional library produces a warning, never a crash.

The script never modifies its inputs and never makes network requests.
"""

from __future__ import annotations

import argparse
import datetime as dt
import email
import email.policy
import hashlib
import html
import html.parser
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (compile_extra_patterns, configure_stdout, read_text, redact,  # noqa: E402
                    write_text)

SKIP_DIRS = {".git", ".svn", ".hg", ".vs", ".idea", ".vscode", "bin", "obj", "node_modules",
             "packages", "dist", "build", "out", "target", "__pycache__", ".venv", "venv", "env",
             "coverage", "TestResults", ".next", ".nuget", ".gradle", ".terraform", "bower_components"}
SKIP_FILES = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "Thumbs.db", ".DS_Store",
              "desktop.ini", "packages.lock.json"}
BINARY_EXT = {".dll", ".exe", ".pdb", ".so", ".dylib", ".lib", ".a", ".o", ".obj", ".class", ".jar",
              ".war", ".nupkg", ".zip", ".7z", ".rar", ".tar", ".gz", ".tgz", ".bz2", ".iso", ".msi",
              ".cab", ".bin", ".dat", ".db", ".sqlite", ".mdf", ".ldf", ".bak", ".suo", ".cache",
              ".woff", ".woff2", ".ttf", ".otf", ".eot", ".ico", ".mp3", ".mp4", ".wav", ".m4a",
              ".avi", ".mov", ".mkv", ".webm", ".snk", ".pfx", ".p12", ".keystore", ".rpt", ".crt",
              ".cer", ".der", ".lnk"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tif", ".tiff", ".svg", ".emf", ".wmf"}
LEGACY_OFFICE = {".doc": "docx", ".rtf": "docx", ".odt": "docx", ".xls": "xlsx", ".ods": "xlsx",
                 ".ppt": "pptx", ".odp": "pptx"}
CODE_EXT = {".cs", ".vb", ".fs", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".py", ".java", ".kt",
            ".go", ".rb", ".php", ".rs", ".c", ".h", ".cpp", ".hpp", ".swift", ".m", ".scala",
            ".cshtml", ".razor", ".vue", ".svelte", ".html", ".css", ".scss", ".less", ".sql",
            ".ps1", ".psm1", ".sh", ".bash", ".bat", ".cmd", ".abap", ".bas", ".vbs", ".lua", ".r",
            ".dart", ".groovy", ".pl", ".asax", ".aspx", ".ascx", ".master", ".xaml", ".tf"}
CONFIG_EXT = {".json", ".xml", ".config", ".yaml", ".yml", ".ini", ".env", ".properties", ".toml",
              ".csproj", ".vbproj", ".fsproj", ".sln", ".props", ".targets", ".gradle", ".pubxml",
              ".resx", ".settings", ".conf", ".cfg", ".editorconfig", ".gitignore", ".dockerignore"}
TEXT_EXT = {".txt", ".md", ".markdown", ".rst", ".adoc", ".csv", ".tsv", ".log", ".text"}
ENTRY_FILES = {"Program.cs", "Startup.cs", "Global.asax", "Global.asax.cs", "web.config", "Web.config",
               "appsettings.json", "package.json", "Dockerfile", "docker-compose.yml", "pom.xml",
               "build.gradle", "requirements.txt", "pyproject.toml", "go.mod", "Cargo.toml",
               "crontab", "README.md", "CLAUDE.md", "AGENTS.md"}
MAX_ROWS_PER_SHEET = 5000


# --------------------------------------------------------------------------------------
# readers: each returns (text, warnings, extra_files) where extra_files are (name, bytes)
# --------------------------------------------------------------------------------------
class _HTMLText(html.parser.HTMLParser):
    BLOCK = {"p", "div", "section", "article", "li", "tr", "br", "h1", "h2", "h3", "h4", "h5", "h6",
             "pre", "table", "ul", "ol", "header", "footer", "blockquote"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.skip = 0
        self.href: str | None = None

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript", "svg"):
            self.skip += 1
        if tag in self.BLOCK:
            self.out.append("\n")
        if re.fullmatch(r"h[1-6]", tag):
            self.out.append("#" * int(tag[1]) + " ")
        if tag == "li":
            self.out.append("- ")
        if tag == "a":
            self.href = dict(attrs).get("href")
        if tag in ("td", "th"):
            self.out.append(" | ")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "svg") and self.skip:
            self.skip -= 1
        if tag == "a" and self.href and not self.href.startswith(("#", "javascript:")):
            self.out.append(f" <{self.href}>")
            self.href = None
        if tag in self.BLOCK:
            self.out.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.out.append(data)


def html_to_text(raw: str) -> str:
    p = _HTMLText()
    p.feed(raw)
    text = "".join(p.out)
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n\n", text).strip() + "\n"


def read_docx(path: Path):
    try:
        import docx  # type: ignore
        from docx.oxml.ns import qn  # type: ignore
    except ImportError:
        return None, ["python-docx not installed: .docx not read"], []
    d = docx.Document(str(path))
    lines: list[str] = []
    body = d.element.body
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            para = docx.text.paragraph.Paragraph(child, d)
            text = para.text.strip()
            style = (para.style.name if para.style is not None else "") or ""
            m = re.match(r"(?i)(?:heading|titolo)\s*(\d)", style)
            if text:
                lines.append(("#" * int(m.group(1)) + " " if m else ("- " if "List" in style else "")) + text)
            if child.findall(".//" + qn("w:drawing")):
                lines.append("[image]")
        elif child.tag == qn("w:tbl"):
            table = docx.table.Table(child, d)
            for row in table.rows:
                cells = []
                for c in row.cells:
                    t = " / ".join(p.text.strip() for p in c.paragraphs if p.text.strip())
                    if not cells or cells[-1] != t:  # merged cells repeat
                        cells.append(t)
                lines.append("| " + " | ".join(cells) + " |")
            lines.append("")
    images = []
    for rel in d.part.rels.values():
        if "image" in rel.reltype:
            try:
                blob = rel.target_part.blob
                images.append((Path(rel.target_ref).name, blob))
            except Exception:  # external images
                pass
    for section in d.sections:  # header/footer text often carries document id and version
        for part in (section.header, section.footer):
            t = " ".join(p.text.strip() for p in part.paragraphs if p.text.strip())
            if t and t not in lines:
                lines.insert(0, f"[header/footer] {t}")
                break
    return "\n".join(lines) + "\n", [], images


def read_pdf(path: Path):
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError:
        return None, ["pypdf not installed: .pdf not read"], []
    try:
        reader = PdfReader(str(path))
    except Exception as e:
        return None, [f"PDF cannot be opened: {e}"], []
    pages = []
    for i, page in enumerate(reader.pages, 1):
        try:
            t = page.extract_text() or ""
        except Exception as e:
            t = f"[page {i}: text extraction failed: {e}]"
        pages.append(f"--- page {i} ---\n{t.strip()}")
    text = "\n".join(pages) + "\n"
    warnings = []
    chars = sum(len(p) for p in pages) - 15 * len(pages)
    if len(reader.pages) and chars < 40 * len(reader.pages):
        warnings.append("little or no text layer: probably a scanned PDF (needs OCR or a text version)")
    return text, warnings, []


def read_xlsx(path: Path):
    try:
        import openpyxl  # type: ignore
    except ImportError:
        return None, ["openpyxl not installed: workbook not read"], []
    try:
        wb = openpyxl.load_workbook(str(path), data_only=True, read_only=True)
    except Exception as e:
        return None, [f"workbook cannot be opened: {e}"], []
    out, warnings = [], []
    for ws in wb.worksheets:
        out.append(f"## Sheet: {ws.title}")
        for n, row in enumerate(ws.iter_rows(values_only=True), 1):
            if n > MAX_ROWS_PER_SHEET:
                warnings.append(f"sheet {ws.title!r} truncated at {MAX_ROWS_PER_SHEET} rows")
                break
            if any(v is not None and str(v).strip() for v in row):
                out.append("\t".join("" if v is None else str(v) for v in row))
        out.append("")
    return "\n".join(out), warnings, []


def read_pptx(path: Path):
    try:
        from pptx import Presentation  # type: ignore
    except ImportError:
        return None, ["python-pptx not installed: .pptx not read"], []
    prs = Presentation(str(path))
    out, images = [], []
    for i, slide in enumerate(prs.slides, 1):
        out.append(f"## Slide {i}")
        for shape in slide.shapes:
            if getattr(shape, "has_text_frame", False) and shape.text_frame.text.strip():
                out.append(shape.text_frame.text.strip())
            if shape.shape_type == 13:  # picture
                try:
                    images.append((f"slide{i}-{shape.shape_id}.{shape.image.ext}", shape.image.blob))
                except Exception:
                    pass
        if slide.has_notes_slide and slide.notes_slide.notes_text_frame.text.strip():
            out.append("Notes: " + slide.notes_slide.notes_text_frame.text.strip())
    return "\n".join(out) + "\n", [], images


def _mail_text(headers: dict, body: str, attachments: list[str]) -> str:
    head = "\n".join(f"{k}: {v}" for k, v in headers.items() if v)
    att = ("\nAttachments: " + ", ".join(attachments)) if attachments else ""
    return f"{head}{att}\n\n{body.strip()}\n"


def read_eml(path: Path):
    msg = email.message_from_bytes(path.read_bytes(), policy=email.policy.default)
    body_part = msg.get_body(preferencelist=("plain", "html"))
    body = ""
    if body_part is not None:
        body = body_part.get_content()
        if body_part.get_content_type() == "text/html":
            body = html_to_text(body)
    files = []
    for part in msg.iter_attachments():
        name = part.get_filename() or "attachment"
        try:
            files.append((name, part.get_payload(decode=True) or b""))
        except Exception:
            pass
    headers = {k: str(msg.get(k, "")) for k in ("From", "To", "Cc", "Date", "Subject")}
    return _mail_text(headers, body, [n for n, _ in files]), [], files


def read_msg(path: Path):
    try:
        import extract_msg  # type: ignore
    except ImportError:
        return None, ["extract-msg not installed: .msg not read (install it, or save the mail as .eml/.pdf)"], []
    m = extract_msg.Message(str(path))
    try:
        body = m.body or ""
        if not body.strip() and getattr(m, "htmlBody", None):
            raw = m.htmlBody
            body = html_to_text(raw.decode("utf-8", "replace") if isinstance(raw, bytes) else raw)
        files = []
        for a in m.attachments:
            name = getattr(a, "longFilename", None) or getattr(a, "shortFilename", None) or "attachment"
            data = getattr(a, "data", None)
            if isinstance(data, bytes):
                files.append((name, data))
        headers = {"From": m.sender, "To": m.to, "Cc": m.cc, "Date": m.date, "Subject": m.subject}
        return _mail_text(headers, body, [n for n, _ in files]), [], files
    finally:
        try:
            m.close()
        except Exception:
            pass


def read_transcript(path: Path):
    """Any transcript format (see transcript.py normalize); None when no turn is found."""
    from transcript import normalize
    report: list = []
    try:
        text = normalize(path, report=report)
    except ValueError as e:
        return None, [str(e)], []
    except SystemExit as e:  # a reader library is missing
        return None, [str(e)], []
    return text, [f"transcript read as {report[0][1]}, {report[0][2]} turns"] if report else [], []


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


def convert_legacy(path: Path, target: str, workdir: Path) -> Path | None:
    exe = soffice_binary()
    if not exe:
        return None
    try:
        subprocess.run([exe, "--headless", "--convert-to", target, "--outdir", str(workdir), str(path)],
                       check=True, capture_output=True, timeout=180)
    except Exception:
        return None
    out = workdir / (path.stem + "." + target)
    return out if out.exists() else None


# --------------------------------------------------------------------------------------
def classify(path: Path) -> str:
    ext = path.suffix.lower()
    name = path.name.lower()
    if ext in (".vtt", ".srt", ".sbv") or (ext in (".json", ".tsv", ".csv") and re.search(r"transcri|trascri", name)):
        return "transcript"
    if ext in (".msg", ".eml"):
        return "mail"
    if ext in IMAGE_EXT:
        return "image"
    if ext in (".docx", ".pdf", ".pptx", ".xlsx", ".xlsm") or ext in LEGACY_OFFICE:
        if re.search(r"transcri|trascri", name):
            return "transcript"
        return "document"
    if ext in (".html", ".htm", ".mhtml") and not any(p in path.parts for p in ("src", "wwwroot")):
        return "web"
    if ext in TEXT_EXT:
        return "transcript" if re.search(r"transcri|trascri", name) else "text"
    if ext in CONFIG_EXT or name in ("dockerfile", "crontab", "makefile"):
        return "config"
    if ext in CODE_EXT:
        return "code"
    if ext in BINARY_EXT:
        return "binary"
    return "other"


def read_any(path: Path, kind: str, tmp: Path):
    ext = path.suffix.lower()
    if ext in LEGACY_OFFICE:
        conv = convert_legacy(path, LEGACY_OFFICE[ext], tmp)
        if conv is None:
            return None, [f"{ext} needs LibreOffice to be read (not found or conversion failed)"], []
        path, ext = conv, conv.suffix.lower()
    if kind == "transcript":
        text, warnings, files = read_transcript(path)
        if text is not None or ext in (".vtt", ".srt", ".sbv"):
            return text, warnings, files
        kind = "document"  # named like a transcript but not one: read it as what it is
    if ext == ".docx":
        return read_docx(path)
    if ext == ".pdf":
        return read_pdf(path)
    if ext in (".xlsx", ".xlsm"):
        return read_xlsx(path)
    if ext == ".pptx":
        return read_pptx(path)
    if ext == ".eml":
        return read_eml(path)
    if ext == ".msg":
        return read_msg(path)
    if ext in (".html", ".htm") and kind == "web":
        return html_to_text(read_text(path)), [], []
    return read_text(path), [], []


def safe_name(s: str) -> str:
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", s).strip() or "_"


class Corpus:
    def __init__(self, out: Path, extra_patterns, max_bytes: int, do_redact: bool):
        self.out = out
        self.extra = extra_patterns
        self.max_bytes = max_bytes
        self.do_redact = do_redact
        self.sources: list[dict] = []
        self.tmp = Path(tempfile.mkdtemp(prefix="sdg-"))

    def add_input(self, path: Path, label: str | None, kind: str | None = None):
        sid = f"SRC-{len(self.sources) + 1:02d}"
        src = {"id": sid, "label": label or path.name, "origin": str(path), "type": "folder" if path.is_dir() else "file",
               "files": [], "kinds": {}, "entry_points": [], "warnings": [], "redactions": 0,
               "force_kind": kind}
        self.sources.append(src)
        if path.is_dir():
            for root, dirs, files in os.walk(path):
                dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith("."))
                for f in sorted(files):
                    fp = Path(root) / f
                    self._add_file(src, fp, fp.relative_to(path))
        elif path.is_file():
            self._add_file(src, path, Path(path.name))
        else:
            src["warnings"].append("not found or not readable")
        return src

    def _add_file(self, src: dict, fp: Path, rel: Path, depth: int = 0):
        entry = {"path": rel.as_posix(), "kind": "", "chars": 0, "status": "ok", "warnings": []}
        if fp.name in SKIP_FILES or fp.name.endswith((".min.js", ".min.css", ".map")):
            return
        kind = src.get("force_kind") or classify(fp)
        if kind == "transcript" and fp.suffix.lower() in IMAGE_EXT | BINARY_EXT:
            kind = classify(fp)
        entry["kind"] = kind
        if fp.name in ENTRY_FILES or fp.suffix.lower() in (".sln", ".csproj"):
            src["entry_points"].append(rel.as_posix())
        try:
            size = fp.stat().st_size
        except OSError as e:
            entry.update(status="unreadable", warnings=[str(e)])
            src["files"].append(entry)
            return
        dest_dir = self.out / src["id"]
        if kind == "binary":
            return  # compiled output, archives, media: listed in the summary count only
        src["kinds"][kind] = src["kinds"].get(kind, 0) + 1
        if kind == "image":
            target = dest_dir / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(fp, target)
            entry["status"] = "copied"
            src["files"].append(entry)
            return
        if size > self.max_bytes:
            entry.update(status="skipped", warnings=[f"larger than {self.max_bytes // 1_000_000} MB"])
            src["files"].append(entry)
            return
        try:
            text, warnings, extra_files = read_any(fp, kind, self.tmp)
        except Exception as e:  # one bad file must not stop the corpus
            text, warnings, extra_files = None, [f"read failed: {type(e).__name__}: {e}"], []
        entry["warnings"] += warnings
        if text is None:
            entry["status"] = "unreadable"
            src["files"].append(entry)
            return
        if "\x00" in text[:4096]:
            entry.update(status="skipped", warnings=entry["warnings"] + ["binary content"])
            src["files"].append(entry)
            return
        if self.do_redact:
            text, hits = redact(text, self.extra)
            if hits:
                kinds = sorted({h["kind"] for h in hits})
                entry["warnings"].append(f"{len(hits)} secret(s) redacted ({', '.join(kinds)})")
                src["redactions"] += len(hits)
        entry["chars"] = len(text)
        suffix = "" if rel.suffix.lower() in (".txt", ".md") else ".txt"
        write_text(dest_dir / (rel.as_posix() + suffix), text)
        src["files"].append(entry)
        # attachments and embedded pictures, one level deep
        for name, blob in extra_files:
            sub_rel = Path(rel.as_posix() + ".parts") / safe_name(name)
            if Path(name).suffix.lower() in IMAGE_EXT or depth >= 1:
                target = dest_dir / sub_rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(blob)
                src["files"].append({"path": sub_rel.as_posix(), "kind": "image" if Path(name).suffix.lower() in IMAGE_EXT else "attachment",
                                     "chars": 0, "status": "copied", "warnings": []})
            else:
                tmpf = self.tmp / safe_name(name)
                tmpf.write_bytes(blob)
                self._add_file(src, tmpf, sub_rel, depth + 1)

    def write_index(self):
        manifest = {"generated": dt.datetime.now().isoformat(timespec="seconds"),
                    "redaction": self.do_redact, "sources": self.sources}
        write_text(self.out / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        lines = ["# Source corpus", "",
                 f"Generated {manifest['generated']}. Secrets redacted: {'yes' if self.do_redact else 'NO'}.",
                 "Cite a source by its ID (and file path inside it).", "",
                 "| ID | Source | Origin | Files by kind | Text chars | Redactions | Warnings |",
                 "|---|---|---|---|---|---|---|"]
        for s in self.sources:
            kinds = ", ".join(f"{k} {v}" for k, v in sorted(s["kinds"].items())) or "-"
            chars = sum(f["chars"] for f in s["files"])
            nwarn = len(s["warnings"]) + sum(1 for f in s["files"] if f["warnings"] or f["status"] in ("unreadable", "skipped"))
            lines.append(f"| {s['id']} | {s['label']} | `{s['origin']}` | {kinds} | {chars:,} | {s['redactions']} | {nwarn} |")
        for s in self.sources:
            if s["entry_points"]:
                lines += ["", f"## {s['id']} - entry points and project files", ""]
                lines += [f"- `{p}`" for p in s["entry_points"][:80]]
            problems = [f for f in s["files"] if f["warnings"] or f["status"] in ("unreadable", "skipped")]
            if problems or s["warnings"]:
                lines += ["", f"## {s['id']} - warnings", ""]
                lines += [f"- {w}" for w in s["warnings"]]
                lines += [f"- `{f['path']}` ({f['status']}): {'; '.join(f['warnings'])}" for f in problems[:200]]
        write_text(self.out / "INDEX.md", "\n".join(lines) + "\n")
        shutil.rmtree(self.tmp, ignore_errors=True)


def secret_patterns_from_profile(profile: Path) -> list[str]:
    """Lines of the profile's 'Secret patterns' section written as `regex` list items."""
    pats, in_sec = [], False
    for line in read_text(profile).splitlines():
        h = re.match(r"^#{1,6}\s+(.*)$", line)
        if h:
            in_sec = bool(re.search(r"(?i)secret|credenzial|segret", h.group(1)))
            continue
        m = re.match(r"^\s*[-*]\s+`(.+)`\s*$", line)
        if in_sec and m:
            pats.append(m.group(1))
    return pats


def main(argv=None) -> int:
    configure_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="*", help="files or folders (local, mapped drive, UNC path, mount point)")
    ap.add_argument("--transcript", action="append", default=[], metavar="PATH",
                    help="a session transcript in any format (or a folder of them), whatever its name")
    ap.add_argument("--out", required=True, help="corpus folder to create (outside the sources)")
    ap.add_argument("--profile", help="documentation profile: its 'Secret patterns' section adds detectors")
    ap.add_argument("--label", action="append", default=[], metavar="NAME=PATH",
                    help="human label for an input, e.g. --label 'Repository ShipLabelApp=./src'")
    ap.add_argument("--max-file-mb", type=float, default=25)
    ap.add_argument("--no-redact", action="store_true", help="keep secrets (never for documentation work)")
    args = ap.parse_args(argv)
    if not args.inputs and not args.transcript:
        ap.error("give at least one input (a file, a folder, or --transcript PATH)")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    patterns = compile_extra_patterns(secret_patterns_from_profile(Path(args.profile))) if args.profile else []
    labels = {}
    for item in args.label:
        if "=" in item:
            name, p = item.split("=", 1)
            labels[str(Path(p).resolve())] = name
    corpus = Corpus(out, patterns, int(args.max_file_mb * 1_000_000), not args.no_redact)
    for inp in args.inputs:
        p = Path(inp)
        corpus.add_input(p, labels.get(str(p.resolve())))
    for inp in args.transcript:
        p = Path(inp)
        corpus.add_input(p, labels.get(str(p.resolve())), kind="transcript")
    corpus.write_index()
    total = sum(len(s["files"]) for s in corpus.sources)
    red = sum(s["redactions"] for s in corpus.sources)
    print(f"{len(corpus.sources)} sources, {total} files, {red} secrets redacted")
    print(f"index: {(out / 'INDEX.md').resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
