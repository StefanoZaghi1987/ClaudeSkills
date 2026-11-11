#!/usr/bin/env python3
"""
selftest.py - checks every script of solution-docs-generator on throwaway data.

    python selftest.py            (python3 on Linux/macOS, py -3 on Windows)

Prints one 'ok' line per check and exits 0 when all pass. Checks that need an optional
library (python-docx, openpyxl, pypdf) or LibreOffice are skipped, with a note, when it is
missing. Nothing outside a temporary folder is written.
"""

from __future__ import annotations

import email.message
import importlib.util
import json
import re
import shutil
import sys
import tempfile
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import check_doc  # noqa: E402
import extract_sources  # noqa: E402
import render  # noqa: E402
import transcript  # noqa: E402
from common import REDACTED, configure_stdout, find_secrets, redact, split_front_matter  # noqa: E402

HAS_DOCX = importlib.util.find_spec("docx") is not None
HAS_XLSX = importlib.util.find_spec("openpyxl") is not None
HAS_PDF = importlib.util.find_spec("pypdf") is not None

RESULTS: list[tuple[str, str]] = []


def check(name):
    def deco(fn):
        def run(tmp: Path):
            try:
                msg = fn(tmp)
                RESULTS.append(("ok" if msg is None else "skip", name + ("" if msg is None else f" ({msg})")))
            except Exception:
                RESULTS.append(("FAIL", name + "\n" + traceback.format_exc()))
        run.__name__ = fn.__name__
        TESTS.append(run)
        return run
    return deco


TESTS = []


# ---------------------------------------------------------------- secrets
@check("redaction catches the usual secret shapes")
def t_redact_positive(tmp):
    samples = {
        '<add key="ClientSecret" value="abc8Q~qwertyuiopasdfghjklzxcvbnm12345678" />': "config-key-value",
        '"Password": "S3cr3t!x"': "named-value",
        "Server=hana;UID=SYSTEM;Pwd=Manager1;": "connection-string",
        "hdbsql -n host:30015 -u SYSTEM -p Passw0rd -I q.sql": "cli-password",
        "https://admin:topsecret@host.example.com/x": "url-credentials",
        "Authorization: Bearer abcdefghijklmnopqrstuvwxyz123456": "authorization-header",
        "token eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U": "jwt",
        "-----BEGIN RSA PRIVATE KEY-----\nMIIEow\n-----END RSA PRIVATE KEY-----": "private-key-block",
        "AccountKey=AbCdEfGhIjKlMnOpQrStUvWxYz0123456789==;": "azure-key",
        "ghp_abcdefghijklmnopqrstuvwxyz0123456789": "github-token",
    }
    for text, kind in samples.items():
        out, hits = redact(text)
        assert hits, f"no hit for {text!r}"
        assert REDACTED in out, f"not redacted: {text!r}"
        assert kind in {h["kind"] for h in hits}, f"{text!r}: {[h['kind'] for h in hits]} lacks {kind}"


@check("redaction leaves placeholders, prose and code expressions alone")
def t_redact_negative(tmp):
    for text in ['"ClientSecret": "<client-secret>"', '"Password": ""', "Password: archiviata nel password manager",
                 "PasswordHash = ComputeHash(pwd);", "password = config.Password;", "DB_PASSWORD=${DB_PASSWORD}",
                 "the password field is required", f'"Password": "{REDACTED}"']:
        assert not find_secrets(text), f"false positive on {text!r}: {find_secrets(text)}"


# ---------------------------------------------------------------- transcript
VTT = """WEBVTT

00:00:03.580 --> 00:00:07.390
<v Anna Bianchi>Oggi parliamo di ship level app e del servis leier.</v>

00:00:07.390 --> 00:00:12.000
<v Anna Bianchi>La ship level app legge la vista gam view label.</v>

00:00:12.500 --> 00:00:15.000
<v Luca Verdi>E i log dove sono?</v>
"""


@check("transcript: WebVTT is normalized to one line per speaker turn")
def t_vtt(tmp):
    f = tmp / "t.vtt"
    f.write_text(VTT, encoding="utf-8")
    out = transcript.normalize(f).strip().splitlines()
    assert len(out) == 2, out
    assert out[0].startswith("[00:00:03] Anna Bianchi: Oggi parliamo"), out[0]
    assert out[1].startswith("[00:00:12] Luca Verdi:"), out[1]


@check("transcript: SRT and 'Name  0:03' text exports are read")
def t_srt_plain(tmp):
    srt = tmp / "t.srt"
    srt.write_text("1\n00:00:01,000 --> 00:00:02,000\nAnna: primo\n\n2\n00:00:03,000 --> 00:00:04,000\nLuca: secondo\n",
                   encoding="utf-8")
    out = transcript.normalize(srt)
    assert "[00:00:01] Anna: primo" in out and "[00:00:03] Luca: secondo" in out, out
    txt = tmp / "teams.txt"
    txt.write_text("Anna Bianchi   0:03\nprima frase\nseconda riga\n\nLuca Verdi   1:15\nrisposta\n", encoding="utf-8")
    out = transcript.normalize(txt)
    assert "[00:00:03] Anna Bianchi: prima frase seconda riga" in out, out
    assert "[00:01:15] Luca Verdi: risposta" in out, out


@check("transcript: suggestions find misheard product names")
def t_suggest(tmp):
    text = "[00:00:03] Anna: Oggi parliamo di ship level app e del servis leier. La ship level app legge la vista."
    res = transcript.suggest(text, ["ShipLabelApp", "Service Layer", "GAM_VIEW_LABEL"])
    pairs = {(r["heard"].lower(), r["term"]) for r in res}
    assert ("ship level app", "ShipLabelApp") in pairs, res
    assert ("servis leier", "Service Layer") in pairs, res


@check("transcript: glossary rules from Markdown, CSV and arrows are applied")
def t_glossary(tmp):
    md = tmp / "profile.md"
    md.write_text("# Profile\n\n## Transcription glossary\n\n| Heard | Correct |\n|---|---|\n"
                  "| ship level app | ShipLabelApp |\n| servis leier | Service Layer |\n\n## Other\n\n"
                  "| a | b |\n|---|---|\n| no | never |\n", encoding="utf-8")
    pairs = transcript.glossary_pairs(md)
    assert pairs == [("ship level app", "ShipLabelApp"), ("servis leier", "Service Layer")], pairs
    csv = tmp / "g.csv"
    csv.write_text("gam view label;GAM_VIEW_LABEL\norbit erp -> OrbitERP\n", encoding="utf-8")
    pairs += transcript.glossary_pairs(csv)
    out, log = transcript.apply_glossary("La Ship-Level APP usa il servis leier e la gam view label su orbit erp.", pairs)
    assert out == "La ShipLabelApp usa il Service Layer e la GAM_VIEW_LABEL su OrbitERP.", out
    assert sum(n for _, _, n in log) == 4, log


@check("transcript: canonical terms are collected from chat and code")
def t_terms(tmp):
    code = tmp / "repo" / "src"
    code.mkdir(parents=True)
    (code / "ShipLabelApp.csproj").write_text("<Project/>", encoding="utf-8")
    (code / "Labels.cs").write_text("class LabelPrintService {} // LabelPrintService GAM_VIEW_LABEL GAM_VIEW_LABEL",
                                    encoding="utf-8")
    terms = transcript.terms_from_code(tmp / "repo")
    assert "ShipLabelApp" in terms and "LabelPrintService" in terms and "GAM_VIEW_LABEL" in terms, terms
    chat = transcript.terms_from_chat("[10:02] Anna Bianchi: ShipLabelApp\n[10:05] Anna Bianchi: si usa il \"Service Layer\" di SAP B1")
    assert "ShipLabelApp" in chat and "Service Layer" in chat, chat


def _norm_file(tmp, name, content, encoding="utf-8", **kw):
    p = tmp / name
    if isinstance(content, (dict, list)):
        content = json.dumps(content)
    p.write_text(content, encoding=encoding)
    report: list = []
    out = transcript.normalize(p, report=report, **kw)
    return report[0][1], out


@check("transcript: engine JSON (Whisper, AssemblyAI, Deepgram, Rev, Azure, AWS, Google, generic)")
def t_transcript_json(tmp):
    cases = {
        "whisper": ({"segments": [{"start": 0.0, "text": " Ciao", "speaker": "SPEAKER_00"},
                                  {"start": 65.2, "text": " stampa", "speaker": "SPEAKER_01"}]},
                    "[00:01:05] SPEAKER_01: stampa"),
        "assemblyai": ({"utterances": [{"speaker": "B", "start": 125000, "text": "Servizio fermo."}]},
                       "[00:02:05] B: Servizio fermo."),
        "deepgram": ({"results": {"channels": [{"alternatives": [{"paragraphs": {"paragraphs": [
            {"speaker": 0, "start": 1.2, "sentences": [{"text": "Primo."}, {"text": "Secondo."}]}]}}]}]}},
            "[00:00:01] Speaker 0: Primo. Secondo."),
        "rev": ({"monologues": [{"speaker": 1, "elements": [{"type": "text", "value": "Ciao", "ts": 3.5},
                                                          {"type": "punct", "value": " "},
                                                          {"type": "text", "value": "mondo"}]}]},
                "[00:00:03] Speaker 1: Ciao mondo"),
        "azure": ({"recognizedPhrases": [{"offsetInTicks": 600000000, "speaker": 2,
                                          "nBest": [{"display": "Controllare i log."}]}]},
                  "[00:01:00] Speaker 2: Controllare i log."),
        "aws": ({"results": {"audio_segments": [{"start_time": "12.5", "speaker_label": "spk_0",
                                                 "transcript": "Riavviare."}]}}, "[00:00:12] spk_0: Riavviare."),
        "google": ({"results": [{"alternatives": [{"transcript": "Aprire la console"}], "resultEndTime": "3.5s"}]},
                   "[00:00:03] Aprire la console"),
        "generic-json": ({"data": {"items": [{"startTime": "PT1M2S", "participant": "Anna", "content": "Testo"}]}},
                         "[00:01:02] Anna: Testo"),
    }
    for engine, (data, line) in cases.items():
        got, out = _norm_file(tmp, f"{engine}.json", data)
        assert got == engine, f"{engine}: detected as {got}"
        assert line in out, f"{engine}: {line!r} not in {out!r}"
    _, out = _norm_file(tmp, "named.json", cases["whisper"][0], speakers={"SPEAKER_00": "Stefano"})
    assert "Stefano: Ciao" in out, out


@check("transcript: TSV/CSV, SBV, 'Name (0:03):' and 'Name: text' lines, UTF-16, Markdown")
def t_transcript_tables_lines(tmp):
    got, out = _norm_file(tmp, "w.tsv", "start\tend\ttext\n0\t2000\tCiao\n900000\t902000\tFine\n")
    assert got == "whisper-tsv" and "[00:00:00] Ciao" in out and "[00:15:00] Fine" in out, (got, out)
    got, out = _norm_file(tmp, "x.csv", 'speaker,start,text\nAnna,00:00:03,Primo\nLuca,00:01:10,"Secondo, punto"\n')
    assert got == "table" and "[00:01:10] Luca: Secondo, punto" in out, out
    got, out = _norm_file(tmp, "y.sbv", "0:00:01.000,0:00:03.000\nCiao da YouTube\n\n0:20:04.000,0:20:06.000\nAltro\n")
    assert got == "sbv" and "[00:00:01] Ciao da YouTube" in out and "[00:20:04]" in out, out
    got, out = _norm_file(tmp, "p.txt", "Anna Bianchi (00:01:02): uno\nLuca Verdi (00:02:00): due\n", encoding="utf-16")
    assert got == "lines" and "[00:01:02] Anna Bianchi: uno" in out and "[00:02:00] Luca Verdi: due" in out, out
    got, out = _norm_file(tmp, "n.txt", "Anna: buongiorno\nLuca: ciao\nAnna: iniziamo\n")
    assert out.splitlines() == ["Anna: buongiorno", "Luca: ciao", "Anna: iniziamo"], out
    got, out = _norm_file(tmp, "m.md", "# Sessione\n\n**Anna**: punto uno\n\n- **Luca**: punto due\n")
    assert "Anna: punto uno" in out and "Luca: punto due" in out and "**" not in out, out


@check("transcript: plain prose keeps paragraphs and gets [¶n] anchors, never one single line")
def t_transcript_prose(tmp):
    para = ("Il servizio di stampa gira sul server delle etichette e va riavviato dopo gli aggiornamenti. " * 9).strip()
    text = "\n\n".join([para, "Le sessioni scadono dopo trenta minuti di inattività.", para]) + "\n"
    got, out = _norm_file(tmp, "w.txt", text)
    lines = out.splitlines()
    assert got == "prose" and len(lines) >= 3, (got, lines)
    assert all(re.match(r"^\[¶\d+\] ", l) for l in lines), lines
    assert all(len(l) <= transcript.PROSE_CHUNK + 120 for l in lines), [len(l) for l in lines]
    one_line = "Prima frase. " * 200
    _, out = _norm_file(tmp, "one.txt", one_line)
    assert len(out.splitlines()) >= 3, "a single long line must be split"
    try:
        _norm_file(tmp, "empty.json", {"foo": 1})
        raise AssertionError("a JSON without turns must be refused")
    except ValueError:
        pass


@check("transcript: Word and PDF transcripts are read; extract_sources routes --transcript inputs")
def t_transcript_containers(tmp):
    if HAS_DOCX:
        import docx
        d = docx.Document()
        for t in ("Anna Bianchi   0:03", "Prima frase", "Luca Verdi   1:15", "Risposta"):
            d.add_paragraph(t)
        d.save(str(tmp / "teams.docx"))
        report: list = []
        out = transcript.normalize(tmp / "teams.docx", report=report)
        assert "[00:00:03] Anna Bianchi: Prima frase" in out and "[00:01:15] Luca Verdi: Risposta" in out, out
    (tmp / "session.json").write_text(json.dumps({"segments": [{"start": 3, "text": "Ciao"}]}), encoding="utf-8")
    corpus = tmp / "corpus"
    assert extract_sources.main(["--out", str(corpus), "--transcript", str(tmp / "session.json")]) == 0
    files = list((corpus / "SRC-01").rglob("*"))
    text = "".join(f.read_text(encoding="utf-8") for f in files if f.is_file())
    assert "[00:00:03] Ciao" in text, text
    if not HAS_PDF:
        return "pypdf missing: PDF transcript not checked"
    pages = [["Trascrizione - Sessione", "Anna Bianchi   0:03", "Il servizio di stampa", "1"],
             ["Trascrizione - Sessione", "Luca Verdi   1:15", "si riavvia dal server", "2"],
             ["Trascrizione - Sessione", "Anna Bianchi   2:40", "dopo ogni aggiornamento", "3"]]
    (tmp / "t.pdf").write_bytes(minimal_pdf(pages))
    out = transcript.normalize(tmp / "t.pdf")
    assert "[00:01:15] Luca Verdi: si riavvia dal server" in out, out
    assert "Trascrizione - Sessione" not in out, "running header not removed"


def minimal_pdf(pages: list[list[str]]) -> bytes:
    """A small valid PDF with one line of Helvetica text per string, one page per list."""
    objs = ["<< /Type /Catalog /Pages 2 0 R >>", None, "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    kids = []
    for lines in pages:
        ops = "BT /F1 12 Tf 72 760 Td " + " ".join(
            f"({l}) Tj 0 -18 Td" for l in lines) + " ET"
        objs.append(f"<< /Length {len(ops)} >>\nstream\n{ops}\nendstream")
        objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
                    f"/Resources << /Font << /F1 3 0 R >> >> /Contents {len(objs)} 0 R >>")
        kids.append(f"{len(objs)} 0 R")
    objs[1] = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(kids)} >>"
    out, offsets = b"%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n{o}\nendobj\n".encode("latin-1")
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{o:010d} 00000 n \n".encode() for o in offsets)
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return out


# ---------------------------------------------------------------- extraction
@check("extract_sources: folder, mail and config become a redacted corpus with IDs")
def t_extract(tmp):
    repo = tmp / "repo"
    (repo / "src" / "bin").mkdir(parents=True)
    (repo / "src" / "appsettings.json").write_text('{"Db": "Server=x;Pwd=Hana123!;", "ApiKey": "3f9a8b7c6d5e4f3a2b1c"}',
                                                   encoding="utf-8")
    (repo / "src" / "Controller.cs").write_text("public class PickController {}", encoding="utf-8")
    (repo / "src" / "bin" / "app.dll").write_bytes(b"MZ\x00\x00")
    (repo / ".git").mkdir()
    (repo / ".git" / "config").write_text("[core]", encoding="utf-8")
    msg = email.message.EmailMessage()
    msg["From"], msg["To"], msg["Subject"], msg["Date"] = "a@example.com", "b@example.com", "Incidente stampa", "Mon, 3 Mar 2025 10:00:00 +0100"
    msg.set_content("La stampa non usciva: riavviato il pool.")
    msg.add_attachment(b"log line 1\n", maintype="text", subtype="plain", filename="app.log")
    mail = tmp / "incident.eml"
    mail.write_bytes(bytes(msg))
    out = tmp / "corpus"
    rc = extract_sources.main(["--out", str(out), str(repo), str(mail)])
    assert rc == 0
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    ids = [s["id"] for s in manifest["sources"]]
    assert ids == ["SRC-01", "SRC-02"], ids
    cfg = (out / "SRC-01" / "src" / "appsettings.json.txt").read_text(encoding="utf-8")
    assert "Hana123" not in cfg and "3f9a8b7c" not in cfg and cfg.count(REDACTED) == 2, cfg
    assert not (out / "SRC-01" / ".git").exists() and not (out / "SRC-01" / "src" / "bin").exists()
    mail_txt = (out / "SRC-02" / "incident.eml.txt").read_text(encoding="utf-8")
    assert "Subject: Incidente stampa" in mail_txt and "riavviato il pool" in mail_txt, mail_txt
    assert (out / "SRC-02" / "incident.eml.parts" / "app.log.txt").exists(), "attachment not extracted"
    index = (out / "INDEX.md").read_text(encoding="utf-8")
    assert "SRC-01" in index and "secret(s) redacted" in index, index


@check("extract_sources: Word and Excel files are read, pictures extracted")
def t_extract_office(tmp):
    if not (HAS_DOCX and HAS_XLSX):
        return "python-docx or openpyxl missing"
    import docx
    import openpyxl
    d = docx.Document()
    d.add_heading("Manuale", 1)
    d.add_paragraph("Testo del manuale.")
    t = d.add_table(rows=1, cols=2)
    t.cell(0, 0).text, t.cell(0, 1).text = "Server", "APP01"
    png = render_png(tmp / "x.png")
    d.add_picture(str(png))
    d.save(str(tmp / "old.docx"))
    wb = openpyxl.Workbook()
    wb.active.append(["Voce", "Criticità"])
    wb.active.append(["ShipLabelApp", "Alta"])
    wb.save(str(tmp / "list.xlsx"))
    out = tmp / "corpus"
    extract_sources.main(["--out", str(out), str(tmp / "old.docx"), str(tmp / "list.xlsx")])
    txt = (out / "SRC-01" / "old.docx.txt").read_text(encoding="utf-8")
    assert "# Manuale" in txt and "| Server | APP01 |" in txt and "[image]" in txt, txt
    assert any((out / "SRC-01" / "old.docx.parts").iterdir()), "picture not extracted"
    assert "ShipLabelApp\tAlta" in (out / "SRC-02" / "list.xlsx.txt").read_text(encoding="utf-8")


def render_png(path: Path) -> Path:
    """A valid 2x2 PNG without Pillow."""
    import struct
    import zlib

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + b"\xff\x00\x00" * 2 for _ in range(2))
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 2, 2, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))
    path.write_bytes(png)
    return path


# ---------------------------------------------------------------- render + check
SOURCE = """---
title: ShipLabelApp – Manuale di troubleshooting
subtitle: Manuale operativo
lang: it
fields:
  - Versione: 1.0 del 11/11/2026
  - Destinatari: ICT
notice: Documento interno.
---

# 1. Sintesi

Indice rapido: vedi scheda S01 e la procedura 3.1. Anomalia A01. [[SOLO TEST]]

| Sintomo | Scheda |
|---|---|
| Login fallito | S01 |

Table: Indice rapido

::: part Parte B – Guida tecnica
Per ICT.
:::

# 2. Schede

### S01 · Login fallito

::: card
Sintomo: "Login fallito" per tutti.
Cause probabili:
- Service Layer fermo (anomalia A01).
Come risolvere:
- Procedura 3.1.
:::

# 3. Procedure

## 3.1 Riavvio

1. Aprire la console.
2. Riavviare.

```sql
SELECT 1 FROM DUMMY;
```

::: warning
Solo lettura.
:::

| ID | Comportamento |
|---|---|
| A01 | Nessun rinnovo della sessione |

Table: Anomalie note

![Console](img/x.png)
"""


@check("render: Markdown output numbers captions and flattens extensions")
def t_render_md(tmp):
    (tmp / "img").mkdir()
    render_png(tmp / "img" / "x.png")
    src = tmp / "doc.md"
    src.write_text(SOURCE, encoding="utf-8")
    out = tmp / "out" / "doc.md"
    assert render.main([str(src), "--to", "md", "-o", str(out)]) == 0
    md = out.read_text(encoding="utf-8")
    for needle in ("*Tabella 1 – Indice rapido*", "*Tabella 2 – Anomalie note*", "*Figura 1 – Console*",
                   "**Sintomo:**", "> **Attenzione**", "**PARTE B – GUIDA TECNICA**", "**[SOLO TEST]**",
                   "- [1. Sintesi](#1-sintesi)"):
        assert needle in md, f"missing {needle!r}"
    assert ":::" not in md
    assert (tmp / "out" / "img" / "x.png").exists(), "image not copied next to the Markdown"


@check("render: DOCX has cover, TOC field, headings, card table, picture")
def t_render_docx(tmp):
    if not HAS_DOCX:
        return "python-docx missing"
    import docx
    (tmp / "img").mkdir()
    render_png(tmp / "img" / "x.png")
    src = tmp / "doc.md"
    src.write_text(SOURCE, encoding="utf-8")
    out = tmp / "doc.docx"
    assert render.main([str(src), "--to", "docx", "-o", str(out), "--no-paginate"]) == 0
    d = docx.Document(str(out))
    xml = d.element.xml
    assert "TOC \\o" in xml, "no TOC field"
    heads = [p.text for p in d.paragraphs if p.style.name.startswith("Heading")]
    assert heads[:2] == ["1. Sintesi", "2. Schede"], heads
    assert "S01 · Login fallito" in heads
    cells = [c.text for t in d.tables for r in t.rows for c in r.cells]
    assert "Sintomo" in cells and "Cause probabili" in cells, cells
    assert xml.count("<pic:pic") == 1
    texts = "\n".join(p.text for p in d.paragraphs)
    assert "Tabella 1 – Indice rapido" in texts and "Figura 1 – Console" in texts
    assert abs(d.sections[0].page_width - docx.shared.Cm(21.0)) < docx.shared.Cm(0.01), "page is not A4"


@check("render: PDF with measured TOC page numbers (LibreOffice)")
def t_render_pdf(tmp):
    if not (HAS_DOCX and HAS_PDF and render.soffice_binary()):
        return "LibreOffice, python-docx or pypdf missing"
    (tmp / "img").mkdir()
    render_png(tmp / "img" / "x.png")
    src = tmp / "doc.md"
    src.write_text(SOURCE, encoding="utf-8")
    out = tmp / "doc.pdf"
    assert render.main([str(src), "--to", "pdf", "-o", str(out)]) == 0
    from pypdf import PdfReader
    toc = PdfReader(str(out)).pages[1].extract_text()
    assert "Sintesi" in toc and any(ch.isdigit() for ch in toc.split("Sintesi")[1][:200]), toc


@check("check_doc: a consistent document passes")
def t_check_ok(tmp):
    (tmp / "img").mkdir()
    render_png(tmp / "img" / "x.png")
    src = tmp / "doc.md"
    src.write_text(SOURCE, encoding="utf-8")
    assert check_doc.main([str(src), "-o", str(tmp / "r.md")]) == 0, (tmp / "r.md").read_text(encoding="utf-8")


@check("check_doc: broken references, secrets, images and blocks are errors")
def t_check_bad(tmp):
    bad = SOURCE + ("\n# 5. Extra\n\nVedi S07, procedura 9.9 e la sezione 2. Password=Secr3t!9 TODO "
                    "[da confermare]\n\n![](img/none.png)\n\n::: note\naperto\n")
    src = tmp / "bad.md"
    src.write_text(bad, encoding="utf-8")
    assert check_doc.main([str(src), "-o", str(tmp / "r.md")]) == 1
    report = (tmp / "r.md").read_text(encoding="utf-8")
    for needle in ("S07 is cited", "points to 9.9", "possible secret", "image not found", "not closed",
                   "out of sequence (expected 4)", "leftover marker 'TODO'", "Open items"):
        assert needle in report, f"missing {needle!r} in report:\n{report}"
    assert "points to 2," not in report


@check("check_doc: 'SAP B1' is not a citation of card B01; other manuals' sections are skipped")
def t_check_widths(tmp):
    text = ("---\ntitle: T\n---\n\n# 1. A\n\n### B01 · Servizi fermi\n\nTesto su SAP B1 e Q1 2026. Vedi B01. "
            "Vedi il manuale di DockScanApp, procedura 9.4.\n")
    src = tmp / "w.md"
    src.write_text(text, encoding="utf-8")
    assert check_doc.main([str(src), "-o", str(tmp / "r.md")]) == 0, (tmp / "r.md").read_text(encoding="utf-8")


@check("front matter: fields list, nested map, flow list, empty values and table rows")
def t_front_matter(tmp):
    meta, body = split_front_matter("---\ntitle: X\nfields:\n  - Versione: v1\n  - Autore: A\ntoc: false\n---\nbody\n")
    assert meta["title"] == "X" and meta["fields"] == [{"Versione": "v1"}, {"Autore": "A"}], meta
    assert meta["toc"] is False and body == "body\n"
    from common import parse_simple_yaml
    m2 = parse_simple_yaml("title: X\nfields:\n  - Versione: 1.0\n  - Autore: A\ntoc: false\n")
    assert m2 == {"title": "X", "fields": [{"Versione": "1.0"}, {"Autore": "A"}], "toc": False}, m2
    m3 = parse_simple_yaml("ids: [S, A, Q]\nstyle:\n  color: 1F3864   # navy\n  labels: x\ntoc_levels: 2\n")
    assert m3 == {"ids": ["S", "A", "Q"], "style": {"color": "1F3864", "labels": "x"}, "toc_levels": 2}, m3
    m4 = parse_simple_yaml("ref:\ncolor: #1F3864\nrevisions:\n  - 1.10 | 12/11/2026 | Mario Rossi | Nota: aggiunta S12\n")
    assert m4["ref"] == "" and m4["color"] == "", m4
    assert m4["revisions"] == ["1.10 | 12/11/2026 | Mario Rossi | Nota: aggiunta S12"], m4
    st = render.load_style({"style": {"color": ""}}, None)
    assert st["color"] == render.DEFAULT_STYLE["color"], "an unreadable colour must fall back to the default"


# ---------------------------------------------------------------- language packs
@check("language packs: every pack has every key of en.json; fallback and overrides work")
def t_lang_packs(tmp):
    import json
    from common import I18N_DIR, _flat_keys, available_langs, format_date, load_lang
    import datetime as dt
    en = json.loads((I18N_DIR / "en.json").read_text(encoding="utf-8"))
    langs = available_langs()
    assert {"it", "en", "de", "fr", "es"} <= set(langs), langs
    for code in langs:
        pack = json.loads((I18N_DIR / f"{code}.json").read_text(encoding="utf-8"))
        missing = _flat_keys(en) - _flat_keys(pack)
        assert not missing, f"{code}.json lacks {sorted(missing)}"
        assert pack["lang"] == code
    it = load_lang("it-IT")
    assert it["labels"]["table"] == "Tabella" and it["chapters"]["cards"] == "Schede di troubleshooting"
    assert format_date(dt.date(2026, 11, 3), it) == "03/11/2026"
    assert format_date(dt.date(2026, 11, 3), load_lang("de")) == "03.11.2026"
    pt = load_lang("pt", quiet=True)
    assert pt["lang"] == "pt" and pt["labels"]["table"] == "Table", "unknown language must fall back to English"
    custom = tmp / "pt.json"
    custom.write_text(json.dumps({"lang": "pt", "labels": {"table": "Tabela"}}), encoding="utf-8")
    pt2 = load_lang("pt", custom, overrides={"tip": "Boa prática"}, quiet=True)
    assert pt2["labels"]["table"] == "Tabela" and pt2["labels"]["figure"] == "Figure"
    assert pt2["labels"]["tip"] == "Boa prática"


DE_SOURCE = """---
title: ShipLabelApp – Fehlerbehebungshandbuch
lang: de
type: troubleshooting
ref: TICKET 1234
version: "1.0"
fields:
  - Version: 1.0 vom 11.11.2026
  - Zielgruppe: IT
style:
  page_format: "Seite {page} von {pages}"
  footer_text: "{ref} · intern"
  cover_layout: form
  logo: img/x.png
  logo_position: both
labels:
  note: Merke
---

# 1. Zusammenfassung

Siehe Kapitel 2 und [zu bestätigen: Port des Dienstes].

::: verify
Eigentümer des Zertifikats prüfen.
:::

::: technical
Interne Details.
:::

::: note
Hinweis mit eigenem Titel.
:::

| A | B |
|---|---|
| 1 | 2 |

Tabelle: Beispiel

# 2. Karten

Text.
"""


@check("render: German pack, verify/technical callouts, 'Seite N von M', logo, form cover")
def t_render_furniture(tmp):
    if not HAS_DOCX:
        return "python-docx missing"
    import docx
    (tmp / "img").mkdir()
    render_png(tmp / "img" / "x.png")
    src = tmp / "de.md"
    src.write_text(DE_SOURCE, encoding="utf-8")
    out = tmp / "de.docx"
    assert render.main([str(src), "--to", "docx", "-o", str(out), "--no-paginate"]) == 0
    d = docx.Document(str(out))
    cells = [c.text for t in d.tables for r in t.rows for c in r.cells]
    texts = "\n".join(p.text for p in d.paragraphs) + "\n" + "\n".join(cells)
    for needle in ("Zu prüfen", "Technische Details", "Merke", "Tabelle 1 – Beispiel", "Inhalt"):
        assert needle in texts, f"missing {needle!r}"
    assert "Version" in cells and "Zielgruppe" in cells, "cover fields are not a form table"
    sec = d.sections[0]
    footer_xml = sec.footer._element.xml
    assert "NUMPAGES" in footer_xml and "PAGE" in footer_xml, "no 'page of pages' fields"
    footer = "".join(p.text for p in sec.footer.paragraphs)
    assert "TICKET 1234 · intern" in footer and "Seite" in footer and "von" in footer, footer
    assert "<pic:pic" in sec.header._element.xml, "no logo in the header"
    assert d.element.xml.count("<pic:pic") >= 1, "no logo on the cover"
    md = tmp / "de.out.md"
    assert render.main([str(src), "--to", "md", "-o", str(md)]) == 0
    assert "> **Zu prüfen**" in md.read_text(encoding="utf-8")


@check("check_doc: words of every language pack (es, de, fr) are recognized")
def t_check_languages(tmp):
    text = ("---\ntitle: T\nlang: es\n---\n\n# 1. Resumen\n\nVer el capítulo 2 y el apartado 9.9. "
            "[por confirmar: puerto]. Siehe Kapitel 7. Voir le manuel X, chapitre 9.\n\n"
            "| A |\n|---|\n| 1 |\n\nTabla: ejemplo\n\n# 2. Fichas\n\nTexto.\n")
    src = tmp / "es.md"
    src.write_text(text, encoding="utf-8")
    assert check_doc.main([str(src), "-o", str(tmp / "r.md")]) == 1
    report = (tmp / "r.md").read_text(encoding="utf-8")
    assert "points to 9.9" in report and "points to 7" in report, report
    assert "points to 9," not in report, "a section of another document was checked"
    assert "por confirmar" in report, "Spanish open item not listed"
    assert "without a 'Table:' caption" not in report, report


def _set_doc(tmp, name, title, type_, prefix, body, related=""):
    p = tmp / name
    p.write_text(f"---\ntitle: {title}\nlang: it\ntype: {type_}\nids: [{prefix}]\n"
                 f"fields:\n  - Documenti collegati: {related}\n---\n\n{body}", encoding="utf-8")
    return p


@check("check_doc --set: sections and IDs of another document of the set must exist")
def t_check_set(tmp):
    um = _set_doc(tmp, "um.md", "ShipLabelApp – Manuale utente", "user-manual", "U",
                  "# 1. Introduzione\n\nTesto.\n\n# 5. Stampa\n\n### U01 · Stampa\n\nVedi U01.\n",
                  "ShipLabelApp – Manuale di troubleshooting")
    good = _set_doc(tmp, "ts.md", "ShipLabelApp – Manuale di troubleshooting", "troubleshooting", "S",
                    "# 1. Sintesi\n\nVedi il manuale utente, capitolo 5, e la procedura U01.\n\n"
                    "### S01 · Errore\n\nVedi S01.\n", "ShipLabelApp – Manuale utente")
    assert check_doc.main([str(good), "--set", str(um), "-o", str(tmp / "r.md")]) == 0, \
        (tmp / "r.md").read_text(encoding="utf-8")
    bad = _set_doc(tmp, "ts2.md", "ShipLabelApp – Manuale di troubleshooting", "troubleshooting", "U",
                   "# 1. Sintesi\n\nVedi il manuale utente, capitolo 7, e la scheda U09.\n\n"
                   "### U02 · Errore\n\nVedi U02.\n")
    assert check_doc.main([str(bad), "--set", str(um), "-o", str(tmp / "r.md")]) == 1
    report = (tmp / "r.md").read_text(encoding="utf-8")
    for needle in ("points to 7 in 'ShipLabelApp – Manuale utente'", "is also the card prefix of",
                   "not named among the related documents"):
        assert needle in report, f"missing {needle!r}:\n{report}"


@check("check_doc --previous / --parity: stable IDs, higher version, same structure per language")
def t_check_revision_parity(tmp):
    def doc(name, version, cards, lang="it", revs=""):
        body = "".join(f"### S{n:02d} · {t}\n\nVedi S{n:02d}.\n\n" for n, t in cards)
        p = tmp / name
        p.write_text(f"---\ntitle: T\nlang: {lang}\nversion: \"{version}\"\nids: [S]\n{revs}---\n\n"
                     f"# 1. Schede\n\n{body}", encoding="utf-8")
        return p
    v1 = doc("v1.md", "1.0", [(1, "Login fallito"), (2, "Stampa ferma")])
    v11 = doc("v11.md", "1.1", [(1, "Login fallito"), (2, "Stampa ferma"), (3, "Nuovo")],
              revs="revisions:\n  - 1.1 | 12/11/2026 | A | Nuova scheda S03\n")
    assert check_doc.main([str(v11), "--previous", str(v1), "-o", str(tmp / "r.md")]) == 0, \
        (tmp / "r.md").read_text(encoding="utf-8")
    moved = doc("v12.md", "1.0", [(1, "Login fallito"), (3, "Stampa ferma")])
    assert check_doc.main([str(moved), "--previous", str(v1), "-o", str(tmp / "r.md")]) == 1
    report = (tmp / "r.md").read_text(encoding="utf-8")
    assert "S02 of the previous version is now S03" in report and "not greater" in report, report
    en = doc("en.md", "1.1", [(1, "Login failed"), (2, "Printing stopped"), (3, "New")], lang="en")
    assert check_doc.main([str(v11), "--parity", str(en), "-o", str(tmp / "r.md")]) == 0, \
        (tmp / "r.md").read_text(encoding="utf-8")
    en_bad = doc("en2.md", "1.1", [(1, "Login failed"), (2, "Printing stopped")], lang="en")
    assert check_doc.main([str(v11), "--parity", str(en_bad), "-o", str(tmp / "r.md")]) == 1
    assert "S03 is defined here but not in" in (tmp / "r.md").read_text(encoding="utf-8")



@check("check_doc: chapters follow the type's order with the pack's names; every type file parses")
def t_check_chapters(tmp):
    for p in sorted(check_doc.TYPES_DIR.glob("*.md")):
        t = check_doc.load_type(p.stem)
        assert t and t["key"] == p.stem and isinstance(t["chapters"], dict), (p.name, t)
        for variant, chs in t["chapters"].items():
            assert isinstance(chs, list) and chs, (p.name, variant)
            missing = [c for c in chs if c.rstrip("*") not in render.load_lang("it", quiet=True)["chapters"]]
            assert not missing, f"{p.name}: chapter keys without a pack name: {missing}"

    def doc(heads, extra=""):
        body = "".join(f"# {i}. {h}\n\nTesto.\n\n" for i, h in enumerate(heads, 1))
        p = tmp / "c.md"
        p.write_text(f"---\ntitle: T\nlang: it\ntype: user-manual\n{extra}---\n\n{body}", encoding="utf-8")
        return p
    good = doc(["Introduzione", "Concetti di base", "Funzioni di stampa", "Funzioni di spedizione",
                "Buone pratiche", "Appendici"])
    assert check_doc.main([str(good), "-o", str(tmp / "r.md")]) == 0
    report = (tmp / "r.md").read_text(encoding="utf-8")
    assert "out of the order" not in report and "is not a chapter" not in report, report
    assert "not present" in report and "Accesso, menu e sessione" in report, report
    bad = doc(["Concetti di base", "Introduzione", "Varie"])
    check_doc.main([str(bad), "-o", str(tmp / "r.md")])
    report = (tmp / "r.md").read_text(encoding="utf-8")
    assert "'2. Introduzione' is out of the order" in report and "'3. Varie' is not a chapter" in report, report
    sched = doc(["Sintesi", "Architettura e dipendenze", "Pianificazione", "Schede di troubleshooting",
                 "Interdipendenze con gli altri processi schedulati", "Appendici"]).read_text(encoding="utf-8")
    (tmp / "s.md").write_text(sched.replace("type: user-manual", "type: troubleshooting\nvariant: scheduled-process"),
                              encoding="utf-8")
    check_doc.main([str(tmp / "s.md"), "-o", str(tmp / "r.md")])
    report = (tmp / "r.md").read_text(encoding="utf-8")
    assert "out of the order" not in report and "is not a chapter" not in report, report



@check("check_doc: --type-def reads an organization's own type (and its variant of a shipped one)")
def t_type_def_external(tmp):
    tdef = tmp / "release-checklist.md"
    tdef.write_text(
        "---\n"
        "key: release-checklist\n"
        "audiences: [administrators]\n"
        "default_prefix: R\n"
        "ids: []\n"
        "variants: [default]\n"
        "chapters:\n"
        "  default: [purpose, prerequisites, procedure, verification, references, signoff]\n"
        "---\n\n# Release checklist\n\nOne file per chapter.\n",
        encoding="utf-8")
    heads = ["Scopo", "Prerequisiti", "Procedura", "Verifica",
             "Documentazione e riferimenti", "signoff"]
    body = "".join(f"# {i}. {h}\n\nTesto.\n\n" for i, h in enumerate(heads, 1))
    doc = tmp / "rc.md"
    doc.write_text(f"---\ntitle: RC\nlang: it\ntype: release-checklist\n---\n\n{body}",
                   encoding="utf-8")
    assert check_doc.main([str(doc), "--type-def", str(tdef), "-o", str(tmp / "r.md")]) == 0
    report = (tmp / "r.md").read_text(encoding="utf-8")
    assert "is not a chapter" not in report and "out of the order" not in report, report

    # without the flag the type is unknown, and the gate says how to pass it
    check_doc.main([str(doc), "-o", str(tmp / "r.md")])
    report = (tmp / "r.md").read_text(encoding="utf-8")
    assert "unknown document type 'release-checklist'" in report and "--type-def" in report, report

    # an extra file whose front-matter key matches a shipped type prevails over the registry
    variant = tmp / "short-form.md"
    variant.write_text(
        "---\n"
        "key: user-manual\n"
        "audiences: [users]\n"
        "default_prefix: U\n"
        "ids: []\n"
        "variants: [default]\n"
        "chapters:\n"
        "  default: [introduction, procedure, verification]\n"
        "---\n\n# User manual (short form)\n",
        encoding="utf-8")
    body = "".join(f"# {i}. {h}\n\nTesto.\n\n"
                   for i, h in enumerate(["Introduzione", "Procedura", "Verifica"], 1))
    doc2 = tmp / "short.md"
    doc2.write_text(f"---\ntitle: S\nlang: it\ntype: user-manual\n---\n\n{body}", encoding="utf-8")
    check_doc.main([str(doc2), "-o", str(tmp / "r.md")])
    assert "'2. Procedura' is not a chapter" in (tmp / "r.md").read_text(encoding="utf-8")
    assert check_doc.main([str(doc2), "--type-def", str(variant), "-o", str(tmp / "r.md")]) == 0
    assert "'2. Procedura' is not a chapter" not in (tmp / "r.md").read_text(encoding="utf-8")

    # a --type-def path that does not exist is refused, never silently ignored
    try:
        check_doc.main([str(doc), "--type-def", str(tmp / "nope.md"), "-o", str(tmp / "r.md")])
        raised = False
    except SystemExit:
        raised = True
    assert raised

    # the card prefix another document of a set takes from the type's default_prefix is
    # honoured for a custom type too (--set: two documents, same default card letter R)
    pair = "---\ntitle: %s\nlang: it\ntype: release-checklist\n---\n\n# 1. Scopo\n\nTesto.\n\n### %s · %s\n\nTesto.\n"
    (tmp / "ra.md").write_text(pair % ("A", "R01", "Primo"), encoding="utf-8")
    (tmp / "rb.md").write_text(pair % ("B", "R02", "Secondo"), encoding="utf-8")
    check_doc.main([str(tmp / "ra.md"), "--set", str(tmp / "rb.md"), "--type-def", str(tdef),
                    "-o", str(tmp / "r.md")])
    assert "card prefix R is also the card prefix of" in (tmp / "r.md").read_text(encoding="utf-8")


# ---------------------------------------------------------------- review regressions
@check("front matter: one reader everywhere — comments, quoted '#', nested labels, values stay text")
def t_yaml_subset(tmp):
    from common import parse_simple_yaml
    block = ('# render-style\n'
             'header_text: "{title} – {ref}"           # running header; placeholders below\n'
             'page_format: "Pag. {page} di {pages}"    # default: "<page label> {page}"\n'
             'footer_text: "Rif. #12 – interno"\n'
             'color: 000000\n'
             'version: 1.10\n'
             'toc_levels: 2\n'
             'labels:                # override single labels\n'
             '  tip: Buona pratica   # green box\n'
             'notes: |\n'
             '  a block\n')
    m = parse_simple_yaml(block)
    assert m["header_text"] == "{title} – {ref}", m
    assert m["page_format"] == "Pag. {page} di {pages}", m
    assert m["footer_text"] == "Rif. #12 – interno", m
    assert m["color"] == "000000" and m["version"] == "1.10" and m["toc_levels"] == 2, m
    assert m["labels"] == {"tip": "Buona pratica"}, m
    assert "a block" not in str(m), "a block scalar must be skipped, not read as a key"
    profile = tmp / "p.md"
    profile.write_text("# P\n\n```yaml\n" + block + "```\n", encoding="utf-8")
    st = render.load_style({}, profile)
    assert st["labels"] == {"tip": "Buona pratica"} and st["page_format"] == "Pag. {page} di {pages}", st


@check("check_doc: another document named by type or German compound is skipped; 'this document' and the type's own name are checked")
def t_check_other_docs(tmp):
    text = ("---\ntitle: T\nlang: it\n---\n\n# 1. A\n\n"
            "Vedi la procedura di manutenzione del secret, capitolo 4. "
            "Siehe Benutzerhandbuch, Kapitel 7. Nel manuale utente, capitolo 5. "
            "In questo documento al capitolo 99. Siehe in diesem Betriebshandbuch, Kapitel 98. "
            "Vedi questo stesso manuale, capitolo 97.\n")
    src = tmp / "o.md"
    src.write_text(text, encoding="utf-8")
    assert check_doc.main([str(src), "-o", str(tmp / "r.md")]) == 1
    report = (tmp / "r.md").read_text(encoding="utf-8")
    for ref in ("points to 99", "points to 98", "points to 97"):
        assert ref in report, f"{ref} not reported:\n{report}"
    for ref in ("points to 4,", "points to 7,", "points to 5,"):
        assert ref not in report, f"{ref} reported:\n{report}"
    # the type's own name is this document ("il manuale utente" inside the user manual);
    # the bare generic word ("il manuale") still names another document (documented limit)
    um = tmp / "um.md"
    um.write_text("---\ntitle: U\ntype: user-manual\nlang: it\nids: [U]\n---\n\n"
                  "# 1. Introduzione\n\nNel manuale utente, capitolo 5. Nel manuale, capitolo 6. "
                  "Vedi U01.\n\n### U01 · Stampa\n\nTesto.\n", encoding="utf-8")
    assert check_doc.main([str(um), "-o", str(tmp / "r2.md")]) == 1
    report = (tmp / "r2.md").read_text(encoding="utf-8")
    assert "points to 5, which is not a heading number" in report, \
        f"the own type name must be checked as this document:\n{report}"
    assert "points to 6" not in report, f"the bare generic word still names another document:\n{report}"
    # the same words, said by another document of the set, name that document (--set)
    ts = tmp / "ts.md"
    ts.write_text("---\ntitle: TS\ntype: troubleshooting\nlang: it\nids: [S]\n---\n\n"
                  "# 1. Sintesi\n\nVedi il manuale utente, capitolo 5.\n", encoding="utf-8")
    check_doc.main([str(ts), "--set", str(um), "-o", str(tmp / "r3.md")])
    report = (tmp / "r3.md").read_text(encoding="utf-8")
    assert "points to 5 in 'U'" in report, \
        f"from another document, the type name must be checked against that document:\n{report}"
    # a language the skill does not ship: the pack given with --lang-pack names the type there too
    nl = tmp / "nl.json"
    nl.write_text('{"types": {"user-manual": {"name": "gebruikershandleiding", '
                  '"file": "gebruikershandleiding"}}, "check": {"section_words": ["hoofdstuk"], '
                  '"document_words": ["handleiding"], "open_item": ["te bevestigen"], '
                  '"self_words": ["dit"]}}', encoding="utf-8")
    doc_nl = tmp / "nl.md"
    doc_nl.write_text("---\ntitle: NL\ntype: user-manual\nlang: nl\nids: [U]\n---\n\n"
                      "# 1. Inleiding\n\nDe gebruikershandleiding, hoofdstuk 5. Zie U01.\n\n"
                      "### U01 · Afdruk\n\nTekst.\n", encoding="utf-8")
    assert check_doc.main([str(doc_nl), "--lang-pack", str(nl), "-o", str(tmp / "r4.md")]) == 1
    report = (tmp / "r4.md").read_text(encoding="utf-8")
    assert "points to 5, which is not a heading number" in report, \
        f"the own type name from --lang-pack must be checked as this document:\n{report}"


@check("check_doc --set: model numbers are not IDs, two named documents are skipped, A/Q may be shared")
def t_check_set_edges(tmp):
    um = _set_doc(tmp, "um.md", "ShipLabelApp – Manuale utente", "user-manual", "U, A, Q",
                  "# 1. Introduzione\n\n### U01 · Stampa\n\nVedi U01 e Q01.\n\n| A01 | x |\n|---|---|\n\nTable: t\n\n"
                  "**Q01 – Etichette in coda**\n",
                  "ShipLabelApp – Manuale di troubleshooting")
    cfg = _set_doc(tmp, "cfg.md", "ShipLabelApp – Manuale di configurazione", "configuration", "C",
                   "# 1. Introduzione\n\n### C01 · Utenti\n\nVedi C01.\n", "")
    ts = _set_doc(tmp, "ts.md", "ShipLabelApp – Manuale di troubleshooting", "troubleshooting", "S, A",
                  "# 1. Sintesi\n\nIl modello A320 e la stampante Q100. Vedi U01. "
                  "Il manuale utente e il manuale di configurazione, capitolo 9.\n\n"
                  "### S01 · Errore\n\nVedi S01 e A01.\n\n| A01 | y |\n|---|---|\n\nTable: t\n",
                  "ShipLabelApp – Manuale utente, ShipLabelApp – Manuale di configurazione")
    check_doc.main([str(ts), "--set", str(um), str(cfg), "-o", str(tmp / "r.md")])
    report = (tmp / "r.md").read_text(encoding="utf-8")
    for bad in ("A320", "Q100", "points to 9", "card prefix"):
        assert bad not in report, f"{bad!r} reported:\n{report}"
    # without 'ids:', the card prefix is the type's default when used: two troubleshooting
    # manuals with S cards share it; known behaviours (A) alone never make a card prefix
    def plain(name, title, body):
        p = tmp / name
        p.write_text(f"---\ntitle: {title}\nlang: it\ntype: troubleshooting\n---\n\n{body}", encoding="utf-8")
        return p
    one = plain("p1.md", "App1 – Manuale di troubleshooting", "# 1. Sintesi\n\n| A01 | x |\n|---|---|\n\nTable: t\n")
    two = plain("p2.md", "App2 – Manuale di troubleshooting", "# 1. Sintesi\n\n| A01 | y |\n|---|---|\n\nTable: t\n")
    check_doc.main([str(one), "--set", str(two), "-o", str(tmp / "r.md")])
    assert "card prefix" not in (tmp / "r.md").read_text(encoding="utf-8")
    s1 = plain("s1.md", "App1 – Manuale di troubleshooting", "# 1. Sintesi\n\n### S01 · x\n\nVedi S01.\n")
    s2 = plain("s2.md", "App2 – Manuale di troubleshooting", "# 1. Sintesi\n\n### S01 · y\n\nVedi S01.\n")
    check_doc.main([str(s1), "--set", str(s2), "-o", str(tmp / "r.md")])
    assert "card prefix S is also" in (tmp / "r.md").read_text(encoding="utf-8")


@check("check_doc: a renumbered ID is an error, a repeated chapter and a role chapter are recognized")
def t_check_severities(tmp):
    def doc(name, cards, heads=None, version="1.0"):
        body = "".join(f"### S{n:02d} · {t}\n\nVedi S{n:02d}.\n\n" for n, t in cards)
        p = tmp / name
        p.write_text(f"---\ntitle: T\nlang: it\nversion: {version}\nids: [S]\n---\n\n# 1. Schede\n\n{body}",
                     encoding="utf-8")
        return p
    old = doc("old.md", [(1, "Login"), (2, "Stampa")])
    new = doc("new.md", [(1, "Login"), (3, "Stampa")], version="1.10")
    assert check_doc.main([str(new), "--previous", str(old), "-o", str(tmp / "r.md")]) == 1
    report = (tmp / "r.md").read_text(encoding="utf-8")
    errors = report.split("## Errors")[1].split("##")[0] if "## Errors" in report else ""
    assert "S02 of the previous version is now S03" in errors, report
    assert "not greater" not in report, "version 1.10 must be greater than 1.0"
    um = tmp / "um.md"
    um.write_text("---\ntitle: T\nlang: en\ntype: user-manual\n---\n\n# 1. Introduction\n\nx\n\n"
                  "# 2. Printing\n\nx\n\n# 3. Functions for warehouse supervisors\n\nx\n\n# 4. Appendices\n\nx\n\n"
                  "# 5. Good practices\n\nx\n\n# 6. Good practices\n\nx\n", encoding="utf-8")
    check_doc.main([str(um), "-o", str(tmp / "r.md")])
    report = (tmp / "r.md").read_text(encoding="utf-8")
    assert "'5. Good practices' is out of the order" in report, report
    assert "'6. Good practices' appears more than once" in report, report
    assert "Functions for" not in report.split("not present")[-1], "the role chapter was not recognized"
    um.write_text("---\ntitle: T\nlang: en\ntype: user-manual\n---\n\n# 1. Introduction\n\nx\n\n"
                  "# 2. Basic concepts\n\nx\n\n# 3. Basic concepts\n\nx\n", encoding="utf-8")
    check_doc.main([str(um), "-o", str(tmp / "r.md")])
    report = (tmp / "r.md").read_text(encoding="utf-8")
    assert "'3. Basic concepts' appears more than once" in report, report
    um.write_text("---\ntitle: T\nlang: en\ntype: user-manual\n---\n\n# 1. Introductoin\n\nx\n\n"
                  "# 2. Basic concepts\n\nx\n", encoding="utf-8")
    check_doc.main([str(um), "-o", str(tmp / "r.md")])
    report = (tmp / "r.md").read_text(encoding="utf-8")
    assert "did you mean 'Introduction'" in report and "out of the order" not in report, report


@check("transcript: prose with 'Nota:' lines and clock times stays prose; engine JSON variants; config refused")
def t_transcript_review_cases(tmp):
    got, out = _norm_file(tmp, "p.txt", "Il sistema stampa le etichette.\nNota: il servizio va riavviato.\n"
                          "Poi si controlla il log.\nAttenzione: non cancellare.\nEsempio: un collo.\n"
                          "Altro testo.\nIl backup termina alle 18:00\nFine.\n")
    assert got == "prose" and "[00:18:00]" not in out and "Nota: il servizio" in out, (got, out)
    got, out = _norm_file(tmp, "o.json", {"text": "Solo testo. " * 120})
    assert got == "text-json" and len(out.splitlines()) >= 2 and out.startswith("[¶1] "), (got, out)
    got, out = _norm_file(tmp, "aai.json", {"utterances": None, "audio_duration": 70,
                                            "words": [{"text": "Ciao", "start": 65000}, {"text": "mondo", "start": 65600}]})
    assert got == "assemblyai" and out.strip() == "[00:01:05] Ciao mondo", (got, out)
    got, out = _norm_file(tmp, "dg.json", {"results": {"channels": [{"alternatives": [
        {"transcript": "Ciao mondo", "words": [{"word": "ciao", "punctuated_word": "Ciao", "start": 61.0},
                                               {"word": "mondo", "punctuated_word": "mondo.", "start": 61.4}]}]}]}})
    assert got == "deepgram" and out.strip() == "[00:01:01] Ciao mondo.", (got, out)
    for name, data in (("vj.json", {"text": "Testo completo della sessione.", "words": [{"word": "Testo"}]}),
                       ("empty.json", {"text": "Testo completo della sessione.", "segments": []})):
        got, out = _norm_file(tmp, name, data)
        assert got == "text-json" and out.strip() == "[¶1] Testo completo della sessione.", (name, got, out)
    try:
        _norm_file(tmp, "cfg.json", {"settings": [{"name": "Archive", "value": "on"}, {"name": "Days", "value": "90"}]})
        raise AssertionError("a configuration file was accepted as a transcript")
    except ValueError:
        pass
    _, out = _norm_file(tmp, "long.txt", "parola " * 3000)
    lines = out.splitlines()
    assert len(lines) >= 20 and max(map(len, lines)) <= transcript.PROSE_CHUNK + 12, [len(l) for l in lines[:3]]
    # the invariant holds for every reader: a long untimed turn of a dialogue is split and anchored
    _, out = _norm_file(tmp, "d.txt", "Anna: " + "frase lunga della sessione. " * 120 + "\nLuca: ok\nAnna: fine\n")
    lines = out.splitlines()
    assert len(lines) >= 5 and lines[0].startswith("[¶1] Anna: ") and lines[-1] == "Anna: fine", lines[:2]
    assert max(map(len, lines)) <= transcript.PROSE_CHUNK + 20, [len(l) for l in lines]
    raw = "Anna: buongiorno a tutti\nLuca: ciao\nAnna: iniziamo\n".encode("utf-16-le") + b"\x00"  # odd length, no BOM
    (tmp / "u16.txt").write_bytes(raw)
    out = transcript.normalize(tmp / "u16.txt")
    assert out.splitlines()[:2] == ["Anna: buongiorno a tutti", "Luca: ciao"], out


GOLDEN = HERE.parent / "evals" / "samples" / "golden"


@check("golden master: passes the gate with no error and no warning, and renders to Markdown and Word")
def t_golden(tmp):
    masters = sorted(GOLDEN.glob("*.md"))
    if not masters:
        return "no golden master in evals/samples/golden"
    for master in masters:
        report = tmp / f"{master.stem}.check.md"
        assert check_doc.main([str(master), "-o", str(report)]) == 0, report.read_text(encoding="utf-8")
        text = report.read_text(encoding="utf-8")
        assert re.search(r"^0 error\(s\), 0 warning\(s\)", text, re.M), text
        assert "out of the order" not in text and "is not a chapter" not in text, text
        assert render.main([str(master), "--to", "md", "-o", str(tmp / "md" / master.name)]) == 0
        if HAS_DOCX:
            out = tmp / f"{master.stem}.docx"
            assert render.main([str(master), "--to", "docx", "-o", str(out), "--no-paginate"]) == 0
            assert check_doc.main([str(master), "--docx", str(out), "-o", str(report)]) == 0, \
                report.read_text(encoding="utf-8")


def main() -> int:
    configure_stdout()
    failed = 0
    for test in TESTS:
        tmp = Path(tempfile.mkdtemp(prefix="sdg-test-"))
        try:
            test(tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    for status, name in RESULTS:
        print(f"{status:4} {name}")
        failed += status == "FAIL"
    print(f"\n{len(RESULTS) - failed}/{len(RESULTS)} checks passed" + (f", {failed} FAILED" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
