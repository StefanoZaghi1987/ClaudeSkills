# Transcript cleaning and coverage

A brainstorming or knowledge-transfer session recorded with an automatic transcription engine is
the richest source and the least reliable one. Engines that are not tuned on the domain mishear
product names, acronyms and codes in consistent ways ("ship level app" for ShipLabelApp,
"lable print servis" for LabelPrintService, "orbit data appy" for Orbit Data API). The cleaning below fixes
those errors systematically before any analysis, so the document never inherits them.

## 1. Normalize

```bash
<python> scripts/transcript.py normalize session.vtt -o work/transcript.txt
<python> scripts/transcript.py normalize session.json --speakers "SPEAKER_00=Anna,SPEAKER_01=Luca" -o work/transcript.txt
<python> scripts/transcript.py normalize day1.vtt day2.docx -o work/transcript.txt   # two sessions, in order
```

One line per speaker turn: `[hh:mm:ss] Speaker: text`. The skill does not depend on the tool that
made the transcript: the format is detected **from the content**, not from the extension.

| Family | Formats | Typical producers |
|---|---|---|
| Subtitles | WebVTT, SRT, SBV | Teams, Zoom, Meet, Webex, Whisper (`--output_format vtt/srt`), YouTube |
| Engine JSON | `segments[]`, `utterances[]`, `monologues[]`, `recognizedPhrases[]`, `results…`, any list of objects with a text field and a start time or a speaker, else the top-level `text` as prose | Whisper / faster-whisper / WhisperX, OpenAI API `verbose_json`, AssemblyAI, Deepgram, Rev, Azure Speech, Amazon Transcribe, Google Speech-to-Text |
| Tables | Whisper `.tsv` (start/end in ms), CSV/TSV with a `text` column (and `start`, `speaker`) | Whisper, spreadsheet exports |
| Text lines | `Name  0:03` headers, `[0:03] Name: text`, `Name (0:03): text`, `Name: text` | Teams/Zoom/Otter text exports, pasted transcripts |
| Prose | plain text with no speaker and no time | Whisper `.txt`, notes dictated to a phone |

Containers: `.vtt .srt .sbv .json .tsv .csv .txt .md .docx .pdf .html`, and `.doc .rtf .odt` through
LibreOffice; UTF-8 or UTF-16. A PDF loses its repeated running header and page numbers.

- **No times in the source** (prose): paragraphs are kept, long ones split at sentence ends, and
  each chunk gets an anchor `[¶n]`. The coverage map cites `¶n` instead of a time.
- **Anonymous speakers** (`SPEAKER_00`, `A`, `Speaker 1`): rename them with `--speakers` once the
  user says who is who; otherwise keep the labels and never guess names.
- **Wrong detection** (rare): force the reader with `--format json|subtitles|sbv|table|lines|prose`.
- Several sessions: give them in chronological order; each starts with a `=== <file> ===` line.
- A recording without a transcript: see `references/sources.md`.

## 2. Collect the correct spellings

The user often types the correct names in the meeting chat while speaking. Ask for those
messages (pasted as text) when they exist. Then build the canonical terms:

```bash
<python> scripts/transcript.py terms --chat work/chat.txt --code <checkout> \
    --profile <profile.md> --extra work/extra-terms.txt -o work/terms.txt
```

- `--chat`: short lines and quoted strings of the chat, CamelCase names, codes, acronyms.
- `--code`: solution and project names, frequent CamelCase identifiers, database objects.
- `--profile`: the right-hand column of the profile's transcription glossary.
- `--extra`: any list you build from the documents (product names, server names, menu labels).

## 3. Suggest, decide, apply

```bash
<python> scripts/transcript.py suggest work/transcript.txt --terms work/terms.txt -o work/suggestions.md
```

The suggestions compare every short passage with every term by spelling and by a rough phonetic
key. They are candidates, not fixes. For each row decide: a true transcription error (add
`heard -> correct` to `work/glossary.md` under a "Transcription glossary" heading), a correct
ordinary word (discard), or a different product (discard). Add the errors you notice while reading
that the script did not propose. Then:

```bash
<python> scripts/transcript.py apply work/transcript.txt --glossary <profile.md> work/glossary.md \
    -o work/transcript.clean.txt --log work/replacements.md
```

Rules apply case-insensitively, on word boundaries, longest first, tolerant of hyphens and extra
spaces. Read the log: a rule with an unexpected count (hundreds of replacements) is probably too
broad — narrow it and re-apply from the original transcript.

Errors that no rule can catch (a misheard number, a wrong verb) are corrected while reading,
using the code and the documents as reference. When a passage stays ambiguous, it becomes an
open item or a checkpoint question — never a guess.

## 4. Read for content

Brainstorming is non-linear: the same topic returns several times, corrections come later ("no,
actually it is the other server"), digressions interrupt. Read the whole cleaned transcript before
structuring, then:

- merge repeated passages on the same topic, keeping the latest correction;
- separate facts (how it works), practice (what people do), history (what happened), opinions and
  intentions (what should change) — each goes to a different place in the document;
- note the explicit emphasis ("this is critical", "always check…"): it raises the topic's weight;
- treat the speaker's uncertainty ("I think", "if I remember well") as a claim to verify in the
  code or documents, or as an open item.

## 5. Coverage map

Keep it in `analysis.md`; it is what proves nothing on-topic was lost.

```markdown
| # | Time | Topic (from the transcript) | Destination | Notes |
|---|---|---|---|---|
| 1 | 00:02 | Purpose of the app, users | 1. Sintesi, 2. … | |
| 2 | 00:07 | Sessions expiring after a pause | 2.1, S04, A12 | confirmed in code |
| 3 | 00:19 | Old printer model in G5 | excluded | off-topic (hardware purchase) |
| 4 | 00:31 | 2024 incident with batches | 11.2 | mail SRC-05 adds the ticket number |
| 5 | ¶14 | Monthly certificate check | user manual 8.2 · configuration 6.3 | set: two documents |
```

Every row needs a destination or an exclusion reason. For a documentation set, the destination
names the document; the same table, grouped by document, is the distribution matrix of the
checkpoint. Personal remarks, jokes, and talk about
colleagues are excluded without being reported. At the checkpoint, summarize the exclusions in one
line.

## 6. Feed the profile

Recurring errors are recurring for the next session too. At delivery, list the new glossary rules
and offer to add them to the profile's transcription glossary.
