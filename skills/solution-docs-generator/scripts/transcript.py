#!/usr/bin/env python3
"""
transcript.py - normalize a meeting transcript and fix systematic speech-to-text errors.

Subcommands:

  normalize <input> [<input> ...] [-o out.txt] [--format F] [--speakers LABEL=NAME,...]
      Any transcript -> one line per turn, "[hh:mm:ss] Speaker: text". The format is detected
      from the content, not the extension:
        subtitles  WebVTT (Teams, Zoom, Meet, Whisper), SRT, SBV (YouTube)
        json       Whisper / WhisperX / OpenAI verbose_json, AssemblyAI, Deepgram, Rev, Azure
                   Speech, Amazon Transcribe, Google Speech-to-Text, any list of objects with a
                   text field and a start time or a speaker; else the top-level "text" as prose
        table      Whisper .tsv (milliseconds), CSV/TSV with a text column
        lines      Teams/Zoom/Otter text exports: "Name  0:03", "[0:03] Name: text",
                   "Name (0:03): text", "Name: text"
        prose      plain text with neither speakers nor times: paragraphs kept, long ones split,
                   each chunk anchored "[¶n]" so the coverage map can point at it
      Containers: .vtt .srt .sbv .json .tsv .csv .txt .md .docx .pdf .html, and .doc .rtf .odt
      through LibreOffice. Consecutive turns of the same speaker are merged.

  terms [--chat FILE ...] [--code DIR ...] [--profile FILE] [--extra FILE ...] [-o terms.txt]
      Build the list of canonical terms (correct spellings): chat messages posted during the
      session, identifiers found in the source code, the profile's glossary, any extra list.

  suggest <transcript> --terms terms.txt [--min-ratio 0.75] [-o suggestions.md]
      Find passages that sound like a canonical term but are spelled differently
      ("ship level app" ~ "ShipLabelApp"). Output is a review list, not a fix:
      the agent decides which suggestions become glossary entries.

  apply <transcript> --glossary FILE [FILE ...] [-o clean.txt] [--log log.md]
      Apply "heard -> correct" rules (Markdown table, CSV/TSV, or "a -> b" lines),
      case-insensitively and on word boundaries, and log every rule with its count.

Standard library only (python-docx for a .docx transcript, pypdf for a .pdf one).
"""

from __future__ import annotations

import argparse
import collections
import csv
import difflib
import io
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import configure_stdout, read_text, write_text  # noqa: E402

TIME_RX = r"(?:\d{1,2}:)?\d{1,2}:\d{2}(?:[.,]\d{1,3})?"
CUE_RX = re.compile(rf"^\s*({TIME_RX})\s*-->\s*({TIME_RX})")
SBV_RX = re.compile(rf"^\s*({TIME_RX}),({TIME_RX})\s*$")
SPEAKER_TIME_RX = re.compile(rf"^(?P<speaker>[^\d\[\]<>][^<>]{{0,80}}?)\s+(?P<time>{TIME_RX})\s*$")
TIME_SPEAKER_RX = re.compile(rf"^\[?(?P<time>{TIME_RX})\]?\s+(?P<speaker>[^:]{{1,80}}?):\s*(?P<text>.*)$")
# "Anna Bianchi (00:01:02): text", "Anna Bianchi [0:03]", "[Anna Bianchi] 10:01:02"
SPEAKER_PAREN_RX = re.compile(rf"^\[?(?P<speaker>[^\d\[\]()<>:][^\[\]()<>:]{{0,60}}?)\]?\s*[(\[]?(?P<time>{TIME_RX})[)\]]?"
                              r"\s*[:\-–]?\s*(?P<text>.*)$")
# "Anna Bianchi: text" (no time): a capitalized name of at most four words
NAME_COLON_RX = re.compile(r"^(?P<speaker>(?:[A-ZÀ-Ý][\w'.\-]*|SPEAKER_\d+|Speaker \d+)(?: [A-ZÀ-Ý][\w'.\-]*){0,3}):\s+(?P<text>\S.*)$")
VOICE_RX = re.compile(r"<v(?:\.[^ >]+)?\s+([^>]+)>")
PROSE_CHUNK = 700

Turn = tuple[str, str, str]  # (time "hh:mm:ss" or anchor "¶n" or "", speaker, text)
FORMATS = ("auto", "json", "subtitles", "sbv", "table", "lines", "prose")


# --------------------------------------------------------------------------------------
# normalize: any transcript format -> turns -> one line per turn
# --------------------------------------------------------------------------------------

def _hms(t: str) -> str:
    t = t.replace(",", ".").split(".")[0]
    parts = [int(p) for p in t.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0)
    h, m, s = parts[-3:]
    return f"{h:02d}:{m:02d}:{s:02d}"


def _secs_to_hms(sec: float) -> str:
    sec = max(0, int(sec))
    return f"{sec // 3600:02d}:{sec % 3600 // 60:02d}:{sec % 60:02d}"


def _time_value(v, unit: str = "s") -> str:
    """A time in any common shape -> 'hh:mm:ss' ('' when absent or unreadable).

    Numbers are seconds (unit 's'), milliseconds ('ms') or 100-ns ticks ('ticks'); strings may be
    numbers, '1.5s', 'PT1M2.5S' (ISO 8601) or 'hh:mm:ss[.mmm]'.
    """
    if v is None or v == "":
        return ""
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return _secs_to_hms(v / {"s": 1, "ms": 1000, "ticks": 10_000_000}[unit])
    s = str(v).strip()
    if re.fullmatch(r"-?\d+(?:\.\d+)?", s):
        return _time_value(float(s), unit)
    m = re.fullmatch(r"(\d+(?:\.\d+)?)s", s)
    if m:
        return _secs_to_hms(float(m.group(1)))
    m = re.fullmatch(r"P?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?", s, re.I)
    if m and any(m.groups()):
        return _secs_to_hms(int(m.group(1) or 0) * 3600 + int(m.group(2) or 0) * 60 + float(m.group(3) or 0))
    if re.fullmatch(TIME_RX, s):
        return _hms(s)
    return ""


def _strip_tags(s: str) -> str:
    return re.sub(r"</?[^>]+>", "", s).strip()


# ---- subtitles: WebVTT, SRT, SBV ------------------------------------------------------
def parse_cues(text: str) -> list[Turn]:
    """WebVTT / SRT / SBV -> turns."""
    turns = []
    for block in re.split(r"\r?\n\s*\r?\n", text):
        lines = [l for l in block.splitlines() if l.strip()]
        idx = next((i for i, l in enumerate(lines) if CUE_RX.match(l) or SBV_RX.match(l)), None)
        if idx is None:
            continue
        m = CUE_RX.match(lines[idx]) or SBV_RX.match(lines[idx])
        time = _hms(m.group(1))
        speaker, words = "", []
        for l in lines[idx + 1:]:
            v = VOICE_RX.search(l)
            if v:
                speaker = v.group(1).strip()
            words.append(_strip_tags(l))
        joined = " ".join(w for w in words if w)
        if not speaker:  # "Name: text" or ">> Name: text" convention of some exporters
            m = re.match(r"^(?:>>\s*)?([A-Z][\w.' \-]{1,60}):\s+(.*)$", joined)
            if m:
                speaker, joined = m.group(1), m.group(2)
        if joined:
            turns.append((time, speaker, joined))
    return turns


# ---- JSON: speech-to-text engines and services ---------------------------------------
TEXT_KEYS = ("text", "transcript", "display", "content", "sentence", "value", "utterance")
START_KEYS = (("start", "s"), ("start_time", "s"), ("startTime", "s"), ("begin", "s"), ("ts", "s"),
              ("offset", "s"), ("start_ms", "ms"), ("startMs", "ms"), ("offsetInTicks", "ticks"),
              ("offsetMilliseconds", "ms"))
SPEAKER_KEYS = ("speaker", "speaker_label", "speakerLabel", "speaker_name", "speakerName", "speakerTag",
                "participant", "name", "channel_tag")


def _speaker(v) -> str:
    if v is None or v == "":
        return ""
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return f"Speaker {int(v)}"
    return str(v).strip()


def _first(d: dict, keys):
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return k, d[k]
    return None, None


def _generic_items(items: list, unit: str | None = None) -> list[Turn]:
    turns = []
    for it in items:
        if not isinstance(it, dict):
            continue
        _, text = _first(it, TEXT_KEYS)
        if text is None:
            alts = it.get("alternatives") or it.get("nBest")
            if isinstance(alts, list) and alts and isinstance(alts[0], dict):
                _, text = _first(alts[0], TEXT_KEYS)
        if not isinstance(text, str) or not text.strip():
            continue
        k, start = _first(it, [k for k, _ in START_KEYS])
        u = unit or dict(START_KEYS).get(k, "s")
        _, spk = _first(it, SPEAKER_KEYS)
        turns.append((_time_value(start, u), _speaker(spk), text.strip()))
    return turns


def _largest_item_list(node, depth: int = 0):
    """The longest list of objects carrying a text field, anywhere in a JSON document."""
    best = None
    if depth > 6:
        return None
    if isinstance(node, list):
        if node and all(isinstance(x, dict) for x in node[:20]) and \
                any(_first(x, TEXT_KEYS)[1] is not None or "alternatives" in x or "nBest" in x for x in node[:20]):
            best = node
        for x in node[:50]:
            cand = _largest_item_list(x, depth + 1)
            if cand is not None and (best is None or len(cand) > len(best)):
                best = cand
    elif isinstance(node, dict):
        for v in node.values():
            cand = _largest_item_list(v, depth + 1)
            if cand is not None and (best is None or len(cand) > len(best)):
                best = cand
    return best


def parse_json(text: str) -> tuple[str, list[Turn]]:
    """(engine, turns) for the JSON outputs of the common speech-to-text engines. When the
    engine's structure gives no turn (empty segments, word lists without times) but the output
    has the whole text, the text is read as prose."""
    engine, turns = _parse_json_engines(text)
    if not turns:
        data = json.loads(text)
        if isinstance(data, dict) and isinstance(data.get("text"), str) and data["text"].strip():
            return "text-json", parse_prose(data["text"])
    return engine, turns


def _parse_json_engines(text: str) -> tuple[str, list[Turn]]:
    data = json.loads(text)
    if isinstance(data, dict):
        res = data.get("results")
        # OpenAI Whisper (CLI, API verbose_json), WhisperX, faster-whisper exports
        if isinstance(data.get("segments"), list):
            return "whisper", _generic_items(data["segments"], "s")
        # AssemblyAI: utterances (with speaker labels) or words, times in milliseconds
        if "utterances" in data or ("words" in data and "audio_duration" in data):
            if isinstance(data.get("utterances"), list) and data["utterances"]:
                return "assemblyai", _generic_items(data["utterances"], "ms")
            if isinstance(data.get("words"), list) and data["words"]:
                return "assemblyai", _generic_items(data["words"], "ms")
            return "assemblyai", parse_prose(str(data.get("text") or ""))
        # Rev.ai: monologues of elements
        if isinstance(data.get("monologues"), list):
            turns = []
            for mono in data["monologues"]:
                els = mono.get("elements") or []
                words = "".join(str(e.get("value", "")) for e in els)
                ts = next((e.get("ts") for e in els if e.get("ts") is not None), None)
                spk = mono.get("speaker_name") or mono.get("speaker")
                if words.strip():
                    turns.append((_time_value(ts), _speaker(spk), re.sub(r"\s+", " ", words).strip()))
            return "rev", turns
        # Azure Speech batch transcription
        if isinstance(data.get("recognizedPhrases"), list):
            return "azure", _generic_items(data["recognizedPhrases"], "ticks")
        if isinstance(res, dict):
            # Deepgram: utterances, or paragraphs of the first alternative
            if isinstance(res.get("utterances"), list):
                return "deepgram", _generic_items(res["utterances"], "s")
            try:
                alt = res["channels"][0]["alternatives"][0]
            except (KeyError, IndexError, TypeError):
                alt = None
            if isinstance(alt, dict):
                paras = (alt.get("paragraphs") or {}).get("paragraphs")
                if isinstance(paras, list) and paras:
                    turns = [(_time_value(p.get("start")), _speaker(p.get("speaker")),
                              " ".join(s.get("text", "") for s in p.get("sentences", [])).strip()) for p in paras]
                    return "deepgram", [t for t in turns if t[2]]
                words = alt.get("words")
                if isinstance(words, list) and words and all(isinstance(w, dict) for w in words[:5]):
                    items = [{"text": w.get("punctuated_word") or w.get("word", ""), "start": w.get("start"),
                              "speaker": w.get("speaker")} for w in words]
                    return "deepgram", _generic_items(items, "s")
                if isinstance(alt.get("transcript"), str):
                    return "deepgram", parse_prose(alt["transcript"])
            # Amazon Transcribe: audio segments with speaker labels
            if isinstance(res.get("audio_segments"), list):
                return "aws", _generic_items(res["audio_segments"], "s")
            if isinstance(res.get("transcripts"), list):
                joined = " ".join(t.get("transcript", "") for t in res["transcripts"] if isinstance(t, dict))
                return "aws", parse_prose(joined)
        # Google Speech-to-Text: results[].alternatives[0].transcript
        if isinstance(res, list) and res and isinstance(res[0], dict) and "alternatives" in res[0]:
            turns = []
            for r in res:
                alt = (r.get("alternatives") or [{}])[0]
                if alt.get("transcript", "").strip():
                    turns.append((_time_value(r.get("resultEndTime") or r.get("result_end_time")), "",
                                  alt["transcript"].strip()))
            return "google", turns
    items = _largest_item_list(data)
    # a list of objects is a transcript only when its items carry a time or a speaker: a
    # configuration file ({"name": …, "value": …}) does not
    if items and sum(1 for it in items[:50] if isinstance(it, dict) and (
            _first(it, [k for k, _ in START_KEYS])[0] or _first(it, SPEAKER_KEYS[:-2])[0])) >= len(items[:50]) / 2:
        return "generic-json", _generic_items(items)
    return "json-text", []


# ---- tables: Whisper TSV, CSV/TSV exports with headers -------------------------------
def parse_table(text: str) -> tuple[str, list[Turn]]:
    first = text.lstrip("﻿").splitlines()[0] if text.strip() else ""
    delim = "\t" if "\t" in first else (";" if first.count(";") > first.count(",") else ",")
    rows = list(csv.DictReader(io.StringIO(text.lstrip("﻿")), delimiter=delim))
    if not rows:
        return "table", []
    cols = {c.strip().lower(): c for c in rows[0].keys() if c}
    text_col = next((cols[k] for k in ("text", "transcript", "content", "utterance", "sentence", "testo") if k in cols), None)
    if text_col is None:
        return "table", []
    start_col = next((cols[k] for k in ("start", "start_time", "starttime", "begin", "time", "timestamp",
                                         "start_ms", "inizio", "ora") if k in cols), None)
    spk_col = next((cols[k] for k in ("speaker", "speaker_label", "name", "participant", "relatore") if k in cols), None)
    # Whisper's TSV writes start and end in milliseconds as integers
    whisper = delim == "\t" and set(cols) == {"start", "end", "text"}
    unit = "ms" if whisper or (start_col and "ms" in start_col.lower()) else "s"
    turns = []
    for r in rows:
        t = (r.get(text_col) or "").strip()
        if t:
            turns.append((_time_value(r.get(start_col), unit) if start_col else "",
                          (r.get(spk_col) or "").strip() if spk_col else "", t))
    return ("whisper-tsv" if whisper else "table"), turns


# ---- line layouts: Teams/Zoom/Otter text exports, "Name: text" ------------------------
NAME_PARTICLES = {"de", "di", "da", "del", "della", "dei", "van", "von", "der", "den", "le", "la", "du", "y"}


def _is_name(s: str) -> bool:
    """'Anna Bianchi', 'Luca De Rossi', 'Speaker 1', 'SPEAKER_00', 'A' — not 'Il backup termina alle'."""
    s = s.strip().strip("[]").strip()
    if re.fullmatch(r"SPEAKER_\d+|Speaker \d+|spk_\d+|[A-Z]", s):
        return True
    words = s.split()
    return 1 <= len(words) <= 5 and words[0][:1].isupper() and \
        all(w[:1].isupper() or w.lower() in NAME_PARTICLES for w in words)


def recurring_labels(lines: list[str]) -> set[str]:
    """The 'Label: text' labels that are speakers. A dialogue shows turn-taking — a label
    recurs — and its label lines are a large share of the text (at least 30%). Prose with a
    few 'Nota:' or 'Attenzione:' lines shows neither."""
    nonempty = [l.strip() for l in lines if l.strip()]
    found = [m.group("speaker") for l in nonempty for m in [NAME_COLON_RX.match(l)] if m]
    counts = collections.Counter(found)
    if not counts or max(counts.values()) < 2 or len(found) < 0.3 * len(nonempty):
        return set()
    return set(counts)


def _turn_header(line: str, labels: set[str]) -> tuple[str, str, str] | None:
    """(time, speaker, text after the header) when the line opens a speaker turn, else None."""
    m = TIME_SPEAKER_RX.match(line)
    if m and _is_name(m.group("speaker")):
        return _hms(m.group("time")), m.group("speaker").strip(), m.group("text").strip()
    m = SPEAKER_TIME_RX.match(line)
    if m and _is_name(m.group("speaker")):
        return _hms(m.group("time")), m.group("speaker").strip(), ""
    m = SPEAKER_PAREN_RX.match(line)
    if m and _is_name(m.group("speaker")):
        return _hms(m.group("time")), m.group("speaker").strip(), m.group("text").strip()
    m = NAME_COLON_RX.match(line)
    if m and m.group("speaker") in labels:
        return "", m.group("speaker").strip(), m.group("text").strip()
    return None


def parse_lines(lines: list[str]) -> list[Turn]:
    """'Speaker  0:03' header lines, '[0:03] Speaker: text', 'Speaker (0:03): text', and
    'Speaker: text' when the label recurs. Other lines continue the current turn."""
    turns: list[Turn] = []
    cur_time, cur_speaker, buf = "", "", []
    labels = recurring_labels(lines)

    def flush():
        if buf:
            turns.append((cur_time, cur_speaker, " ".join(buf)))
            buf.clear()

    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        head = _turn_header(line, labels)
        if head:
            flush()
            cur_time, cur_speaker, text = head
            if text:
                buf.append(text)
            continue
        if CUE_RX.match(line):
            flush()
            cur_time = _hms(CUE_RX.match(line).group(1))
            continue
        buf.append(line)
    flush()
    return turns


def _line_layout_share(lines: list[str]) -> float:
    """Share of non-empty lines that are a speaker turn (see _turn_header)."""
    nonempty = [l.strip() for l in lines if l.strip()]
    if not nonempty:
        return 0.0
    labels = recurring_labels(nonempty)
    hits = sum(1 for l in nonempty if _turn_header(l, labels))
    return hits / len(nonempty) if hits >= 2 else 0.0


# ---- prose: a transcript with no speakers and no times ---------------------------------
def parse_prose(text: str) -> list[Turn]:
    """Paragraphs kept; long paragraphs split at sentence ends; each chunk anchored '¶n'.

    Plain-text engine outputs (Whisper .txt, a pasted transcript) have no timestamps: the
    anchors give the coverage map something to point at.
    """
    paras = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(paras) <= 1:  # one sentence per line, or one huge line
        paras = [l for l in text.splitlines() if l.strip()]
    chunks: list[str] = []
    buf = ""
    for p in paras:
        for s in split_text(p):
            if buf and len(buf) + len(s) + 1 > PROSE_CHUNK:
                chunks.append(buf)
                buf = ""
            buf = f"{buf} {s}".strip()
        if len(buf) >= PROSE_CHUNK // 3:  # a paragraph end is a natural boundary
            chunks.append(buf)
            buf = ""
    if buf:
        chunks.append(buf)
    return [(f"¶{i}", "", c) for i, c in enumerate(chunks, 1)]


def split_text(text: str, limit: int = PROSE_CHUNK) -> list[str]:
    """Chunks of at most `limit` characters made of whole sentences; a sentence longer than the
    limit is cut at a word boundary, a word longer than the limit inside the word."""
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return [text] if text else []
    pieces: list[str] = []
    for sentence in re.split(r"(?<=[.!?…])\s+", text):
        while len(sentence) > limit:
            cut = sentence.rfind(" ", 0, limit + 1)
            cut = cut if cut > limit // 2 else limit
            pieces.append(sentence[:cut].strip())
            sentence = sentence[cut:].strip()
        if sentence:
            pieces.append(sentence)
    chunks: list[str] = []
    for p in pieces:
        if chunks and len(chunks[-1]) + 1 + len(p) <= limit:
            chunks[-1] += " " + p
        else:
            chunks.append(p)
    return chunks


# ---- loading any file as text ----------------------------------------------------------
def _markdown_to_text(text: str) -> str:
    out = []
    for line in text.splitlines():
        s = line.rstrip()
        s = re.sub(r"^\s{0,3}#{1,6}\s+", "", s)                 # headings
        s = re.sub(r"^\s*(?:[-*+]|\d+[.)])\s+", "", s)          # list markers
        s = re.sub(r"^\s*>\s?", "", s)                          # quotes
        s = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", s)        # links and images
        s = re.sub(r"(\*\*|__|\*|_|`)(.+?)\1", r"\2", s)        # emphasis and code
        if re.fullmatch(r"\s*(?:[-*_]\s*){3,}", s) or re.fullmatch(r"\s*\|?[-:| ]+\|?\s*", s or "x"):
            s = ""
        out.append(s)
    return "\n".join(out)


def _pdf_to_text(path: Path) -> str:
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError:
        sys.exit("reading a .pdf transcript needs pypdf (<interpreter> -m pip install pypdf), "
                 "or export the transcript as .vtt/.docx/.txt")
    pages = [(p.extract_text() or "") for p in PdfReader(str(path)).pages]
    # lines repeated on most pages (running header, footer, page number) are not speech
    counts = collections.Counter(l.strip() for pg in pages for l in set(pg.splitlines()) if l.strip())
    repeated = {l for l, c in counts.items() if len(pages) >= 3 and c >= 0.6 * len(pages)}
    lines = []
    for pg in pages:
        for l in pg.splitlines():
            s = l.strip()
            if s in repeated or re.fullmatch(r"(?:page|pag\.?|pagina|seite|página)?\s*\d+(?:\s*(?:/|of|di|von|de|sur)\s*\d+)?",
                                              s, re.I):
                continue
            lines.append(l.rstrip())
    text = "\n".join(lines)
    return re.sub(r"(\w)-\n(\w)", r"\1\2", text)  # words hyphenated across lines


def load_transcript_text(path: Path) -> str:
    """The text of a transcript file of any supported container."""
    ext = path.suffix.lower()
    if ext in (".doc", ".rtf", ".odt"):
        from extract_sources import convert_legacy  # LibreOffice
        import shutil
        import tempfile
        tmp = Path(tempfile.mkdtemp(prefix="sdg-tr-"))
        try:
            conv = convert_legacy(path, "docx", tmp)
            if conv is None:
                sys.exit(f"reading a {ext} transcript needs LibreOffice; save it as .docx or .txt")
            return load_transcript_text(conv)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    if ext == ".docx":
        try:
            import docx  # type: ignore
        except ImportError:
            sys.exit("reading a .docx transcript needs python-docx "
                     "(<interpreter> -m pip install python-docx), or export the transcript as .vtt")
        d = docx.Document(str(path))
        lines = [p.text for p in d.paragraphs]
        for t in d.tables:  # some exports put turns in a table: speaker | time | text
            for row in t.rows:
                lines.append(" ".join(c.text.strip() for c in row.cells if c.text.strip()))
        return "\n".join(lines)
    if ext == ".pdf":
        return _pdf_to_text(path)
    text = read_text(path)
    if ext in (".html", ".htm"):
        from extract_sources import html_to_text
        return html_to_text(text)
    if ext in (".md", ".markdown"):
        return _markdown_to_text(text)
    return text


def detect_format(text: str) -> str:
    s = text.lstrip("﻿ \t\r\n")
    if s[:1] in "{[":
        try:
            json.loads(s)
            return "json"
        except ValueError:
            pass
    head = s[:4000]
    if re.search(r"(?m)^\s*" + TIME_RX + r"\s*-->\s*" + TIME_RX, head.replace("\r", "")):
        return "subtitles"
    if re.search(r"(?m)^" + SBV_RX.pattern.strip("^$") + r"\s*$", head):
        return "sbv"
    first = s.splitlines()[0].lower() if s else ""
    if ("\t" in first or "," in first or ";" in first) and \
            re.search(r"(?:^|[\t,;])\s*(?:text|transcript|content|utterance|sentence|testo)\s*(?:[\t,;]|$)", first):
        return "table"
    if _line_layout_share(s.splitlines()) >= 0.15:
        return "lines"
    return "prose"


def turns_of(text: str, fmt: str = "auto") -> tuple[str, list[Turn]]:
    """(detected format, turns) of a transcript text."""
    fmt = detect_format(text) if fmt == "auto" else fmt
    if fmt == "json":
        engine, turns = parse_json(text.lstrip("﻿"))
        return engine, turns
    if fmt in ("subtitles", "sbv"):
        return fmt, parse_cues(text)
    if fmt == "table":
        return parse_table(text)
    if fmt == "lines":
        return "lines", parse_lines(text.splitlines())
    return "prose", parse_prose(text)


def _seconds(t: str) -> int | None:
    m = re.fullmatch(r"(\d+):(\d{2}):(\d{2})", t or "")
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3)) if m else None


def merge_turns(turns: list[Turn], max_chars: int = PROSE_CHUNK, max_span: int = 120) -> list[Turn]:
    """Join consecutive cues of one speaker, keeping a timestamp every ~max_chars characters
    and at least every max_span seconds (a passage keeps a time the coverage map can cite)."""
    out: list[list[str]] = []
    for t, s, x in turns:
        anchored = t.startswith("¶")
        if out and not anchored and out[-1][1] == s and len(out[-1][2]) + len(x) <= max_chars:
            a, b = _seconds(out[-1][0]), _seconds(t)
            if a is None or b is None or b - a <= max_span:
                out[-1][2] += " " + x
                continue
        out.append([t, s, x])
    return [tuple(o) for o in out]  # type: ignore[misc]


def speaker_map(specs: list[str]) -> dict[str, str]:
    """['SPEAKER_00=Anna', 'B=Luca,C=Marco'] -> {'SPEAKER_00': 'Anna', 'B': 'Luca', 'C': 'Marco'}."""
    out = {}
    for spec in specs or []:
        for part in spec.split(","):
            if "=" in part:
                k, v = part.split("=", 1)
                out[k.strip()] = v.strip()
    return out


def anchor_long_turns(turns: list[Turn], limit: int = PROSE_CHUNK) -> list[Turn]:
    """The output invariant, whatever the format: no turn without a time is longer than about
    `limit` characters. A longer one is split; the pieces keep the speaker and get '¶n' anchors
    (numbered after the anchors the turns already have), so the coverage map can cite them."""
    used = [int(t[1:]) for t, _, _ in turns if t.startswith("¶") and t[1:].isdigit()]
    n = max(used, default=0)
    out: list[Turn] = []
    for t, s, x in turns:
        if t or len(x) <= limit * 1.2:
            out.append((t, s, x))
            continue
        for piece in split_text(x, limit):
            n += 1
            out.append((f"¶{n}", s, piece))
    return out


def normalize(path: Path, fmt: str = "auto", speakers: dict[str, str] | None = None,
              report: list | None = None) -> str:
    """One line per turn: '[hh:mm:ss] Speaker: text' ('[¶n] text' when the source has no times)."""
    detected, turns = turns_of(load_transcript_text(path), fmt)
    if not turns:
        raise ValueError(f"{path.name}: no transcript turns found (format {detected}); "
                         "try --format prose, or export the transcript as .vtt/.txt")
    speakers = speakers or {}
    turns = [(t, speakers.get(s, speakers.get(s.replace("Speaker ", ""), s)), x) for t, s, x in turns]
    turns = anchor_long_turns(merge_turns(turns))
    if report is not None:
        report.append((path.name, detected, len(turns)))
    out = []
    for t, s, x in turns:
        x = re.sub(r"\s+", " ", x).strip()
        prefix = f"[{t}] " if t else ""
        out.append(f"{prefix}{s + ': ' if s else ''}{x}")
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------------------------
# terms
# --------------------------------------------------------------------------------------
CAMEL_RX = re.compile(r"\b[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]+)+[A-Za-z0-9]*\b")
SQL_OBJ_RX = re.compile(r"\b@?[A-Z][A-Z0-9]*_[A-Z0-9_]{3,}\b")
ACRONYM_RX = re.compile(r"\b[A-Z]{2,}[0-9]*\b")
CODE_EXT = {".cs", ".vb", ".ts", ".tsx", ".js", ".jsx", ".py", ".java", ".kt", ".go", ".rb", ".php",
            ".sql", ".xml", ".json", ".config", ".yaml", ".yml", ".cshtml", ".razor", ".vue",
            ".csproj", ".sln", ".ps1", ".sh", ".bash"}
SKIP_DIRS = {".git", ".svn", ".hg", ".vs", ".idea", "bin", "obj", "node_modules", "packages",
             "dist", "build", "out", "target", "__pycache__", ".venv", "venv", "coverage",
             "TestResults", ".next", "wwwroot"}


def terms_from_code(root: Path, limit: int = 400) -> list[str]:
    counts: collections.Counter = collections.Counter()
    names: set[str] = set()
    for p in root.rglob("*"):
        if any(part in SKIP_DIRS for part in p.parts) or not p.is_file():
            continue
        if p.suffix.lower() in (".sln", ".csproj", ".vbproj", ".fsproj"):
            names.add(p.stem)
        if p.suffix.lower() not in CODE_EXT or p.stat().st_size > 1_000_000 or p.name.endswith(".min.js"):
            continue
        txt = read_text(p)
        counts.update(CAMEL_RX.findall(txt))
        counts.update(m.lstrip("@") for m in SQL_OBJ_RX.findall(txt))
        if p.name == "package.json":
            m = re.search(r'"name"\s*:\s*"([^"]+)"', txt)
            if m:
                names.add(m.group(1))
    frequent = [t for t, c in counts.most_common() if c >= 2 and len(t) >= 6][:limit]
    return sorted(names) + frequent


def terms_from_chat(text: str) -> list[str]:
    out = []
    for line in text.splitlines():
        line = re.sub(r"^\s*(?:\[[^\]]*\]\s*)?(?:[^:]{1,60}:\s+)?", "", line).strip()  # drop "[time] Name:"
        if not line:
            continue
        for piece in re.split(r"\s+[–—-]\s+|[,;()]", line):  # "OrbitERP – Orbit Data API (prod)"
            piece = piece.strip(" .;,:")
            # a name, code or path, not an ordinary lowercase word ("produzione")
            if piece and len(piece.split()) <= 6 and re.search(r"[A-Z0-9_\\/.@#]", piece):
                out.append(piece)
        out += CAMEL_RX.findall(line) + SQL_OBJ_RX.findall(line) + ACRONYM_RX.findall(line)
        out += re.findall(r"[\"“«']([^\"”»']{3,60})[\"”»']", line)
    return out


def glossary_pairs(path: Path) -> list[tuple[str, str]]:
    """'heard -> correct' pairs from a Markdown table, CSV/TSV, or arrow lines.

    In a Markdown file only the table(s) under a heading containing 'glossar' are read,
    so a whole documentation profile can be passed as the glossary.
    """
    text = read_text(path)
    pairs: list[tuple[str, str]] = []
    if path.suffix.lower() in (".md", ".markdown"):
        in_section = False
        for line in text.splitlines():
            h = re.match(r"^#{1,6}\s+(.*)$", line)
            if h:
                in_section = "glossar" in h.group(1).lower() or "transcri" in h.group(1).lower()
                continue
            if in_section and line.strip().startswith("|"):
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if len(cells) >= 2 and cells[0] and cells[1] and not re.fullmatch(r":?-{2,}:?", cells[0]):
                    pairs.append((cells[0].strip("`"), cells[1].strip("`")))
            elif in_section:
                m = re.match(r"^\s*[-*]?\s*(.+?)\s*(?:->|→|=>)\s*(.+?)\s*$", line)
                if m:
                    pairs.append((m.group(1).strip("`\"'"), m.group(2).strip("`\"'")))
        # drop the header row of each table ("Heard | Correct")
        pairs = [p for p in pairs if not re.search(r"(?i)^(trascritt|heard|errat|wrong|sentit|come compare)", p[0])]
        return pairs
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = re.match(r"^\s*(.+?)\s*(?:->|→|=>)\s*(.+?)\s*$", line)
        if m:
            pairs.append((m.group(1), m.group(2)))
            continue
        delim = "\t" if "\t" in line else (";" if ";" in line else ",")
        row = next(csv.reader(io.StringIO(line), delimiter=delim))
        if len(row) >= 2 and row[0].strip() and row[1].strip():
            pairs.append((row[0].strip(), row[1].strip()))
    return pairs


# --------------------------------------------------------------------------------------
# suggest
# --------------------------------------------------------------------------------------
def _norm(s: str) -> str:
    return re.sub(r"[^0-9a-zà-ÿ]", "", s.lower())


_PHON = str.maketrans({"p": "b", "v": "b", "f": "b", "c": "k", "q": "k", "g": "k",
                       "t": "d", "z": "s", "x": "s", "w": "u", "y": "i"})


def _skeleton(n: str) -> str:
    """Rough phonetic key: similar consonants merged, vowels and doubles dropped.

    Speech-to-text engines mishear names in a consistent way ("label" -> "level",
    "pick" -> "big"); comparing skeletons as well as spellings catches those.
    """
    s = re.sub(r"[aeiouàèéìòù]|h", "", n.translate(_PHON))
    return re.sub(r"(.)\1+", r"\1", s)


def similarity(a: str, b: str) -> float:
    r = difflib.SequenceMatcher(None, a, b).ratio()
    ka, kb = _skeleton(a), _skeleton(b)
    if len(ka) >= 3 and len(kb) >= 3:
        r = max(r, (r + difflib.SequenceMatcher(None, ka, kb).ratio()) / 2)
    return r


def _humps_align(heard: str, term: str) -> bool:
    """For a CamelCase term heard as separate words, each word must resemble its hump.

    "ship level app" ~ Ship|Label|App passes; "documenti di" ~ Document|Dto does not.
    A different number of words than humps is accepted only when the whole spelling is close.
    """
    words = [_norm(w) for w in heard.split() if _norm(w)]
    humps = [_norm(h) for h in re.findall(r"[A-Z][a-z0-9]*|[a-z0-9]+", term)]
    if len(words) != len(humps):
        return difflib.SequenceMatcher(None, _norm(heard), _norm(term)).ratio() >= 0.85
    return all(difflib.SequenceMatcher(None, w, h).ratio() >= 0.5 for w, h in zip(words, humps))


def _trigrams(s: str) -> set[str]:
    s = f"  {s} "
    return {s[i:i + 3] for i in range(len(s) - 2)}


def suggest(transcript: str, terms: list[str], min_ratio: float = 0.75) -> list[dict]:
    body = "\n".join(re.sub(r"^\s*\[[^\]]*\]\s*(?:[^:]{1,80}:\s*)?", "", l)
                     for l in transcript.splitlines())  # drop "[hh:mm:ss] Speaker:" prefixes
    tokens = re.findall(r"[^\W_]+", body)
    canon: dict[str, str] = {}
    camel: dict[str, bool] = {}
    for t in terms:
        n = _norm(t)
        if len(n) >= 5:
            canon.setdefault(n, t)
            camel.setdefault(n, bool(CAMEL_RX.fullmatch(t)))
    if not canon:
        return []
    max_words = 5
    windows: dict[str, list[int]] = collections.defaultdict(list)
    for i in range(len(tokens)):
        for k in range(1, max_words + 1):
            if i + k > len(tokens):
                break
            w = " ".join(tokens[i:i + k])
            windows[w].append(i)
    keys = list(windows)
    norm_keys = [_norm(k) for k in keys]
    index: dict[str, list[int]] = collections.defaultdict(list)
    for idx, nk in enumerate(norm_keys):
        if len(nk) >= 4:
            for g in _trigrams(nk):
                index[g].append(idx)
    common = {g for g, ids in index.items() if len(ids) > 4000}
    exact = set(norm_keys)
    results = []
    for n, term in canon.items():
        grams = _trigrams(n) - common
        if not grams:
            continue
        cnt: collections.Counter = collections.Counter()
        for g in grams:
            cnt.update(index.get(g, ()))
        need = max(2, int(len(grams) * 0.3))
        for idx, c in cnt.most_common(60):
            if c < need:
                break
            nk = norm_keys[idx]
            if nk == n:
                if keys[idx] == term:
                    continue
                r = 1.0  # same letters, different form: "gam view pkl2" for GAM_VIEW_PKL2
            elif not (0.6 * len(n) <= len(nk) <= 1.5 * len(n)) or n in nk or nk in canon:
                continue  # too different in length, the term plus neighbouring words, or another term
            elif " " not in keys[idx] and keys[idx].islower() and camel.get(n):
                # one ordinary word against a code identifier ("documento" ~ DocumentDto):
                # spelling must be close on its own, sound-alike is not enough
                r = difflib.SequenceMatcher(None, n, nk).ratio()
                if r < 0.92:
                    continue
            else:
                r = similarity(n, nk)
                if camel.get(n) and not _humps_align(keys[idx], canon[n]):
                    continue
            if r >= min_ratio:
                results.append({"heard": keys[idx], "term": term, "ratio": round(r, 2),
                                "count": len(windows[keys[idx]]), "term_present": n in exact,
                                "first_pos": windows[keys[idx]][0]})
    # keep the best window per (term, position) and drop windows nested in a better one
    results.sort(key=lambda r: (-r["ratio"], -len(r["heard"])))
    taken: dict[str, list[tuple[int, int]]] = collections.defaultdict(list)
    kept = []
    for r in results:
        width = len(r["heard"].split())
        span = (r["first_pos"], r["first_pos"] + width)
        if any(span[0] < e and s < span[1] for spans in taken.values() for s, e in spans):
            continue  # overlaps a better window already kept (for this or another term)
        taken[r["term"]] += [(pos, pos + width) for pos in windows[r["heard"]]]
        r["context"] = " ".join(tokens[max(0, r["first_pos"] - 6): r["first_pos"] + len(r["heard"].split()) + 6])
        kept.append(r)
    return kept


# --------------------------------------------------------------------------------------
# apply
# --------------------------------------------------------------------------------------
def phrase_regex(heard: str) -> re.Pattern:
    words = [re.escape(w) for w in re.split(r"[\s\-]+", heard.strip()) if w]
    return re.compile(r"(?<![\w])" + r"[\s\-]+".join(words) + r"(?![\w])", re.I)


def apply_glossary(text: str, pairs: list[tuple[str, str]]) -> tuple[str, list[tuple[str, str, int]]]:
    # One pass over the text with every rule at once: a replacement is never re-read by another
    # rule, and at each position the longest phrase wins ("ship level app server" before
    # "ship level app").
    rules = []
    seen = set()
    for heard, correct in sorted(pairs, key=lambda p: -len(p[0])):
        key = heard.strip().lower()
        if not key or key == correct.strip().lower() or key in seen:
            continue
        seen.add(key)
        rules.append((heard, correct))
    if not rules:
        return text, []
    combined = re.compile("|".join(f"(?P<r{i}>{phrase_regex(h).pattern})" for i, (h, _) in enumerate(rules)),
                          re.I)
    counts = [0] * len(rules)

    def repl(m: re.Match) -> str:
        i = int(m.lastgroup[1:])
        counts[i] += 1
        return rules[i][1]

    text = combined.sub(repl, text)
    return text, [(h, c, counts[i]) for i, (h, c) in enumerate(rules)]


# --------------------------------------------------------------------------------------
def main(argv=None) -> int:
    configure_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("normalize")
    a.add_argument("inputs", nargs="+", help="one or more transcripts (several sessions: in order)")
    a.add_argument("-o", "--output")
    a.add_argument("--format", choices=FORMATS, default="auto",
                   help="force the reader when detection by content is wrong")
    a.add_argument("--speakers", action="append", default=[], metavar="LABEL=NAME[,LABEL=NAME]",
                   help="rename anonymous speakers (SPEAKER_00=Anna, A=Luca, 'Speaker 1'=Marco)")

    a = sub.add_parser("terms")
    a.add_argument("--chat", nargs="*", default=[])
    a.add_argument("--code", nargs="*", default=[])
    a.add_argument("--profile")
    a.add_argument("--extra", nargs="*", default=[])
    a.add_argument("-o", "--output")

    a = sub.add_parser("suggest")
    a.add_argument("transcript")
    a.add_argument("--terms", required=True)
    a.add_argument("--min-ratio", type=float, default=0.75)
    a.add_argument("-o", "--output")

    a = sub.add_parser("apply")
    a.add_argument("transcript")
    a.add_argument("--glossary", nargs="+", required=True)
    a.add_argument("-o", "--output")
    a.add_argument("--log")

    args = ap.parse_args(argv)

    if args.cmd == "normalize":
        report: list = []
        parts = []
        try:
            for path in map(Path, args.inputs):
                text = normalize(path, args.format, speaker_map(args.speakers), report)
                parts.append(f"=== {path.name} ===\n{text}" if len(args.inputs) > 1 else text)
        except ValueError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        out = "\n".join(parts)
        summary = "; ".join(f"{name}: {fmt}, {n} turns" for name, fmt, n in report)
        if args.output:
            write_text(Path(args.output), out)
            print(f"normalized transcript: {Path(args.output).resolve()} ({summary})")
        else:
            sys.stdout.write(out)
            print(summary, file=sys.stderr)
        return 0

    if args.cmd == "terms":
        terms: list[str] = []
        for f in args.chat:
            terms += terms_from_chat(read_text(Path(f)))
        for d in args.code:
            terms += terms_from_code(Path(d))
        if args.profile:
            terms += [c for _, c in glossary_pairs(Path(args.profile))]
        for f in args.extra:
            terms += [l.strip() for l in read_text(Path(f)).splitlines() if l.strip()]
        seen, uniq = set(), []
        for t in terms:
            t = t.strip()
            if len(_norm(t)) >= 3 and t.lower() not in seen:
                seen.add(t.lower())
                uniq.append(t)
        out = "\n".join(uniq) + "\n"
        if args.output:
            write_text(Path(args.output), out)
            print(f"{len(uniq)} canonical terms: {Path(args.output).resolve()}")
        else:
            sys.stdout.write(out)
        return 0

    if args.cmd == "suggest":
        terms = [l.strip() for l in read_text(Path(args.terms)).splitlines() if l.strip()]
        res = suggest(read_text(Path(args.transcript)), terms, args.min_ratio)
        lines = ["# Possible transcription errors", "",
                 "Review each row: keep the true errors as glossary rules (heard -> correct).", "",
                 "| Heard | Probably | Similarity | Occurrences | Context |", "|---|---|---|---|---|"]
        for r in res:
            ctx = r["context"].replace("|", "/")
            lines.append(f"| {r['heard']} | {r['term']} | {r['ratio']} | {r['count']} | …{ctx}… |")
        out = "\n".join(lines) + "\n"
        if args.output:
            write_text(Path(args.output), out)
            print(f"{len(res)} suggestions: {Path(args.output).resolve()}")
        else:
            sys.stdout.write(out)
        return 0

    if args.cmd == "apply":
        pairs: list[tuple[str, str]] = []
        for g in args.glossary:
            pairs += glossary_pairs(Path(g))
        if not pairs:
            print("warning: no glossary rule found", file=sys.stderr)
        text, log = apply_glossary(read_text(Path(args.transcript)), pairs)
        if args.output:
            write_text(Path(args.output), text)
        else:
            sys.stdout.write(text)
        report = ["| Heard | Correct | Replacements |", "|---|---|---|"]
        report += [f"| {h} | {c} | {n} |" for h, c, n in log]
        total = sum(n for _, _, n in log)
        if args.log:
            write_text(Path(args.log), "\n".join(report) + "\n")
        print(f"{len(log)} rules, {total} replacements"
              + (f"; cleaned transcript: {Path(args.output).resolve()}" if args.output else ""),
              file=sys.stderr if not args.output else sys.stdout)
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
