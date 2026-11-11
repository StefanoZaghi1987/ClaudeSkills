---
name: solution-docs-generator
description: "Write user manuals, configuration guides, troubleshooting manuals, maintenance procedures and solution sheets from transcripts, docs, mails and code. DOCX/PDF/MD, Italian default."
---

# Solution Docs Generator

Produce operational documentation for a software solution, an integration or an IT tool by
cross-checking every source the user can point to: recorded brainstorming or knowledge-transfer
sessions (transcribed by any tool), the chat messages posted during them, existing documents,
historical mails, screenshots, vendor portals and — above all — the source code, wherever it is.
The result is a document a colleague can use alone: complete, verified against the code,
consistent in structure with every other document of its type, and free of credentials.

Use this skill — not `training-manual-generator` — whenever the document describes how a
system works, how it is used, configured, maintained or repaired. Use `training-manual-generator`
for a course whose only source is the lesson itself.

## The model

A request is a point on six independent axes; the intake asks only for the ones the request,
the profile and the defaults leave open.

| Axis | Values | Default |
|---|---|---|
| Subject | one solution or process (or several linked ones) | — (asked) |
| Document types | `troubleshooting`, `user-manual`, `configuration`, `maintenance-procedure`, `solution-sheet` — one, some, or all; a type of the profile's own counts too (`references/document-types.md`) | — (asked) |
| Variant | troubleshooting: `application` (Part A + B) or `scheduled-process` | from the analysis |
| Depth | complete or essential | profile, else complete |
| Languages | one or more; the first is the master's | profile, else Italian |
| Formats | DOCX, PDF, Markdown — one or more | DOCX |

One pipeline serves every combination. Each step reads files and writes files, so a step can be
resumed, checked, or given to a worker:

```
sources ─extract─▶ corpus/ (SRC-nn) ─analyse─▶ work/analysis.md       (once per subject)
  ─write─▶ one master .md per document type, first language
  ─translate─▶ one copy per extra language (same IDs and numbers)
  ─render─▶ one file per format     ─check─▶ each document, the set, the languages
```

A **revision** is the same pipeline with the previous master as one more input.

Three layers, never mixed: the **skill** holds the method; the **profile** (optional, outside
the skill) holds an organization's conventions; the **work folder** holds one subject's state.

**Reference files** — read each when its phase runs:

- `references/profile.md` — the documentation profile and how to find it (Phase 1)
- `references/document-types.md` — the registry, the shared frame, depth, sets, IDs (Phases 1, 5, 6)
- `references/types/<type>.md` — one per document type: chapters, variants, rules (Phases 5, 6)
- `references/sources.md` — source kinds, access in each environment, inventory (Phase 2)
- `references/transcript.md` — any transcript format, cleaning, glossary, coverage map (Phase 3)
- `references/code-analysis.md` — what to extract from the code, per component (Phase 4)
- `references/writing-standards.md` — style, languages, traceability, conflicts, credentials (Phase 6)
- `references/authoring-format.md` — the Markdown dialect the renderer builds from (Phase 6)
- `references/quality-checks.md` — the delivery gate (Phase 7)
- `references/parallel.md` — when and how to use workers (Phases 4, 6, 7)
- `references/local-python.md` — interpreter, packages, encodings, PDF engines (any phase that runs Python)

**Language packs** — `assets/i18n/<lang>.json` (it, en, de, fr, es): chapter names, cover
labels, card labels, captions, callout titles, badges, open-item marker, date format, file-name
words. Scripts and agent read the same pack, so a document has the same fixed texts in every
run. A language without a pack: write one in the work folder from `en.json` and pass it with
`--lang-pack`; at delivery offer to add it to the skill or the profile.

**Scripts** (Python 3.10+, standard library plus the readers each format needs; run them from
the skill folder's `scripts/`, with the interpreter `references/local-python.md` names):

| Script | Purpose |
|---|---|
| `extract_sources.py` | Mixed files and folders → one redacted text corpus with source IDs and an index |
| `transcript.py` | Any transcript format → one line per turn; canonical terms; suggested and applied corrections |
| `render.py` | Authored Markdown → DOCX (house style, TOC with page numbers), PDF, or clean Markdown |
| `check_doc.py` | Delivery gate: IDs, section links, chapters of the type, secrets, images; across a set, a revision, languages |
| `selftest.py` | Checks the scripts themselves; run it once when the environment is new |

Optional packages, each needed only for its format: `python-docx` (Word in and out), `pypdf`
(PDF in, TOC page numbers), `openpyxl` (Excel), `python-pptx` (slides), `extract-msg` (Outlook
`.msg`); LibreOffice for PDF output, legacy Office files and measured TOC page numbers. Ask
before installing anything (`references/local-python.md`). A missing package degrades one
format, never the whole run.

## Operating modes

- **Default — semi-automatic (guided):** two exchanges with the user: the intake (Phase 1, only
  for what is missing) and one checkpoint after the analysis (Phase 5). Everything else runs
  without stops.
- **"Automatic"** (also "quick mode"): no checkpoint. Apply stated preferences, the profile and the
  defaults; record every assumption and list it in the delivery message. The content guards still
  fire: no sources → ask; nothing readable → stop.
- **"Interactive":** guided, plus the outline is approved before writing and each conflict
  between sources is decided by the user.

**Parallel work** follows one rule in every mode (`references/parallel.md`): use workers when the
environment has a subagent tool and a step has two or more independent units — components to
analyse, documents to write, languages to translate, documents to verify; otherwise work
sequentially. The user can say "sequential".

## Workflow

### PHASE 1 — Intake

1. Find the documentation profile (`references/profile.md`, "Finding the profile"). When one is
   found, read it fully and say which profile is in use.
2. **New, continuation, regeneration or revision.** A **revision** changes an existing document
   and gives it a new version ("update", "revise", "add…", "v1.1", a previous
   `.md`/`.docx`/`.pdf` to change): see "Revisions" below. A **continuation** adds a document
   the set does not have yet to a subject that already has documents: see "Continuation of a
   set" below. A **regeneration** ("generate again", "rebuild", the same version) runs the
   normal workflow and keeps the version; delivery never overwrites the earlier file. When unsure,
   ask which one.
3. Establish the six axes from the request, the profile and the defaults, and ask in **one
   message** only for what is still missing:
   - **document types:** one, some, or all (`references/document-types.md`, "Choosing the
     documents"); several subjects in one session → one document per subject, linked;
   - **subject**, **audience(s)** and **depth** (complete by default);
   - **languages** (one or more; default Italian) and **formats** (one or more; DOCX default);
   - **sources:** where transcripts, documents, code and mails are. Say that chat messages posted
     during the session, historical mails and screenshots can be added at Phase 3.
   Use the environment's question tool when it has one; otherwise ask in plain text. Acknowledge
   values already given instead of asking again.
4. **No source at all:** ask for one and stop. Never write from general knowledge: every statement
   must be traceable to a source or to the user's answers.

### PHASE 2 — Source acquisition and inventory

Follow `references/sources.md`. Keep every working file in one folder, `docs-work/<subject>/`
inside the folder the user chooses (or the session's workspace): `corpus/`, `work/` (transcript,
chat, glossary, `analysis.md`), `images/`, the `.md` masters and the outputs. In short:

- Reach each source with the means this environment has — local or network paths, connected
  folders, uploads, git or the hosting platform's CLI, web tools for portals. Work **read-only**
  on every source: never modify, commit to, or delete anything the user owns.
- Run `extract_sources.py` on documents, mail folders and repository checkouts; pass session
  transcripts with `--transcript` (any format). The result is a redacted corpus with IDs
  `SRC-nn` and an `INDEX.md`. When the scripts cannot run, read the files with the platform's own
  tools and keep the same IDs by hand.
- Present the **source inventory** (template in `references/sources.md`). Name every source that
  could not be read and why; continue with the rest. Stop only when nothing is readable.

### PHASE 3 — Transcript and terminology

Follow `references/transcript.md`:

1. `transcript.py normalize` each session's transcript — subtitles, engine JSON (Whisper and
   others), TSV/CSV, text, Markdown, Word or PDF: the format is detected from the content.
   Rename anonymous speakers with `--speakers` when the user names them.
2. Ask for the chat messages posted during the session (if not already given) and any mail about
   historical problems, when the request says they exist or the profile says the method uses
   them. Add them to the corpus.
3. Build the canonical terms (`transcript.py terms`), get the suggestions (`suggest`), decide each
   one, then `apply` the glossary. Keep the original transcript: the cleaned copy is a working file.
4. Draw the **coverage map**: every topic of the transcript, in order (by time, or by `¶n` anchor
   when the transcript has no times), with its destination, or "excluded" with the reason.
   Nothing discussed on topic may be lost.

### PHASE 4 — Analysis

One analysis for every document to be written.

- **Code** (`references/code-analysis.md`): architecture and components, environments and
  configuration (without secret values), data read and written, external calls, authentication
  and sessions, scheduled jobs, printing and reporting, logging, user-visible messages, error
  handling. Turn behaviours that can surprise a user or an operator into **known behaviours**
  (with file references) and derive the **potential problems** the code makes possible. With two
  or more components or repositories, apply the parallel rule (`references/parallel.md`).
- **Documents and portals:** extract only what the documents need; prefer the most recent and
  the most authoritative; note what the new documents supersede.
- **Mails and tickets:** each solved incident becomes a historical case (symptom, diagnosis,
  solution, lesson).
- Keep in `work/analysis.md`: the **claims register** (statement → source IDs), the **conflicts
  register** (rules in `references/writing-standards.md`), and the coverage map.
- **Security findings** (credentials in code or config, disabled certificate checks, excessive
  privileges): never in a document. Collect them for the delivery message.

### PHASE 5 — Checkpoint

Present, in one message:

- the sources used and the ones that could not be read;
- the **documents to write**: type (and variant), language(s), format(s), file names; for a set,
  the **distribution matrix** (topic → document) and the ID prefix of each document;
- the proposed outline of each document: chapters of its type with their depth, the ID scheme,
  the figures planned; maintenance procedures the analysis suggests;
- the coverage map summary and the segments excluded;
- the open conflicts and gaps, as **3–4 concrete questions** at most — the ones whose answer
  changes the content;
- that security findings exist (count only), to be reported at delivery.

Wait for the answer, apply it, record the decisions in `work/analysis.md`, and do not ask again
unless the answer opens a new conflict. Skip this phase in automatic mode.

### PHASE 6 — Writing

- One **master** per document, in the first language, as Markdown in the dialect of
  `references/authoring-format.md`, with `type:` and `lang:` in the front matter (`variant:` when
  it is not the type's default). Follow
  the chapters of `references/types/<type>.md` with the names of the language pack, and the rules
  of `references/writing-standards.md`. The cover fields are those the profile asks for, labelled
  from the pack. The golden example `evals/samples/golden/` shows the expected level.
- A **set**: write each document from the same analysis, following the distribution matrix;
  cross-reference the others by name and section instead of repeating them; fill "Related
  documents". Two or more documents → the parallel rule. The solution sheet is written last,
  because it lists the others.
- Long documents: write section by section into the file, so progress survives context limits;
  keep the running ID counters and the claims register up to date as you go.
- Screenshots: use those the user supplied or that the sources contain; caption every figure;
  never invent a screen. A missing one is an open item.
- Every statement the sources could not confirm and the user did not settle carries the pack's
  open-item marker (`[da confermare: …]`, `[to be confirmed: …]`).
- **Other languages:** when the master is final, translate it into `<name>.<lang>.md` — prose
  translated; IDs, heading numbers, identifiers, untranslated UI labels, quoted messages and code
  unchanged; chapter names and labels from the target pack.

### PHASE 7 — Build and quality gate

1. For each master and each translation: `render.py <doc>.md --to docx` (or `pdf`, `md`;
   `--profile` when there is one; `--lang-pack` for a language without a pack). For this skill
   the local renderer takes precedence over a platform document skill — every document of a
   series must keep one house style; `references/local-python.md` states the generic rule
   (platform document skill first) and this skill inverts that order on purpose. The platform
   document skill is the fallback on a platform whose Python cannot run python-docx: build the
   same structure with it, and say so. PDF needs LibreOffice: without it, use the platform's own
   PDF route when it has one; otherwise deliver the DOCX and say that the PDF could not be built
   here.
2. `check_doc.py <doc>.md --docx <doc>.docx` (`--lang-pack` as for the render; `--type-def
   <file>` when the type is the profile's or the work folder's own), plus
   `--set <the other masters>` for a set, `--parity <first-language master>` for a translation,
   `--previous <old master>` for a revision. Fix every error; review the warnings and the
   chapter notes.
3. Run the manual checks of `references/quality-checks.md`. With workers available, a fresh
   verifier per document checks the statements against the corpus first (`references/parallel.md`).
   Where the platform can render pages, look at the cover, the TOC and a few dense pages.

### PHASE 8 — Delivery

Name each file by the profile's convention; otherwise
`<Subject> - <file word of the type> - v<version>.<ext>` with the file word from the language pack
(`types.<type>.file`; e.g. `ShipLabelApp - troubleshooting - manuale operativo - v1.0.docx`). When
several languages are delivered, each file takes the file word of its own language and ` - <LANG>`
before the extension (`… - operations manual - v1.0 - EN.docx`). **Never overwrite**: when
the name exists in the output folder, or a file of this conversation already has it, ask (guided)
or add `_2`, `_3` (automatic). Deliver with the platform's file delivery, or write to the folder
the user chose and report the absolute paths. Keep the masters (and their images) with the working
files: they are the base of the next revision. Then report, in the user's language:

- files delivered (type, format, language, pages or sections, figures);
- sources used, and sources not readable;
- open items and the decisions taken on conflicts;
- **security findings**, in the conversation only, with a suggestion to handle them separately;
- new glossary entries, conventions and language packs worth adding to the profile (offer to
  update it);
- which steps ran in parallel, if any; related documents worth writing next.

## Revisions

A revision changes an existing document and keeps its identity:

1. Load the previous master (`.md`). Only a `.docx`/`.pdf` exists → run `extract_sources.py` on it
   and rebuild a master from the text, keeping its numbering and IDs exactly.
2. Run Phases 2–4 on the **new or changed** sources only (a new session, new mails, code changed
   since the date of the previous version — `git log` gives it), plus whatever the user asks to
   change.
3. Checkpoint: what changes, chapter by chapter; what is added; what is retired.
4. Write the new version: version increased, one `revisions:` row saying what changed, `supersedes`
   when the profile asks for it. IDs are stable: new cards take new numbers; a retired card stays,
   marked as retired, and its number is never reused.
5. `check_doc.py --previous <old master>` must pass; deliver under the new version's name.

## Continuation of a set

A continuation adds a document the set does not have yet — a type it lacks (the user manual,
when the troubleshooting manual already exists), or a further maintenance procedure for a task
found since. It is neither a revision (same document, new version) nor a regeneration (same
documents, same version): the new document is new, and starts at version 1.0.

1. Reuse the work folder `docs-work/<subject>/` when it exists: `work/analysis.md`, the
   glossary and the coverage map stay; analyse only the sources that are new or changed since.
   When it is gone, the previous masters become sources (`extract_sources.py`, `SRC-nn`) and
   the analysis runs again on them plus the new sources.
2. The new document takes a card prefix no existing document of the set uses (read the `ids:`
   of their front matter) and declares it in its own front matter.
3. Gate with `check_doc.py <new>.md --set <every existing master of the set>`, and list the
   others under "Related documents".
4. The existing masters are inputs, never outputs. At delivery, offer to add the new document
   to their "Related documents" field; when the user accepts, touch only that cover field — no
   version increase, unless the profile asks for one.

## Communication guidelines

- Write every user-facing message in the language of the user's request; the templates in this
  skill and its references show the content, not the language.
- Ask only what cannot be inferred; never ask twice for the same thing.
- Never paste a credential into a message, a file or a command line the user will read.
