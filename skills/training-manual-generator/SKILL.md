---
name: training-manual-generator
description: "Turn training transcripts into user manuals with relevance-weighted chapters. Use for 'crea il manuale del corso', 'make a training manual', or an uploaded session. DOCX/PDF/MD, Italian default."
---

# Training Manual Generator

Turn training-session transcripts into a professional manual the learner
keeps as a reference.

**Reference files** — read each when its phase runs:
- `references/content-standards.md` — manual structure, per-section specs, relevance word budgets, formatting and quality standards (PHASE 1 word budgets, PHASE 3)
- `references/output-formats.md` — format-specific generation for both platforms, file saving, filename convention (PHASE 5)
- `references/quality-checks.md` — validation checklists (PHASE 4); edge cases and
  troubleshooting (any phase)
- `references/examples.md` — the canonical walkthrough plus automatic,
  interactive, and revision examples; read when the run uses automatic or
  interactive mode, or handles a revision request
- `references/source-examples.md` — worked examples for difficult sources;
  read when the source is long or complex, ambiguous, or split across files

## Operating modes

The workflow has three confirmation points: (1) analysis summary, (2) configuration
(language and format, in one question), (3) structure preview before generation.

- **Default: Semi-Automatic** — all three confirmations.
- **"Fully automatic"** (users may also say "quick mode") — no confirmations: skip
  the analysis summary and the structure preview, apply stated preferences or the
  defaults (Italian, Word), deliver directly. The content guards (no-source
  request, ambiguity check, quality-issue report) still fire.
- **"Interactive mode"** — semi-automatic plus two extra decisions: after the
  analysis summary, offer to adjust topic relevance levels or organization; at the
  structure preview, approve the full chapter structure before generation.

## Workflow

### PHASE 1: Analysis and Understanding

**Step 1.1 — Content Reception.** When training content is detected — an uploaded
file or pasted text with training-like features (transcript or meeting-trace form,
timestamps, speaker labels, training terminology, instructional structure):

```
✓ Content received: [filename or pasted text]
⚙ Analyzing training content...
```

When uploaded content is ambiguous, confirm before analyzing: "It looks like you've
uploaded training content. Would you like me to generate a comprehensive user manual
from it?"

**No content at all:** ask for the transcript or the session notes. Never invent
the source — every statement in the manual must be traceable to real material.

**Non-text source:** if the content is audio, video, or a link and no text trace is
available, ask for the transcript or captions — never guess the spoken content.

**Unreadable file:** a scanned, image-only PDF, or an attachment type this platform
cannot parse, yields no text. Say plainly that the file cannot be read here, name it,
and ask for a text version or a different format — never guess its content. On Claude
Code, offer first to convert it locally where a suitable tool is available, and
continue from the converted copy. With several files, continue from the readable ones,
name the unreadable one in the analysis summary and in the delivery message, and stop
only when none of them can be read.

**Step 1.2 — Deep Analysis.**

**Very large sources:** if the transcript is too large to read and analyze in
one pass, process it in sections — analyze each section, carry the topic list,
relevance evidence, and dependencies forward as running notes, and merge the
notes into one analysis before Step 1.3. Mention it — "Source processed in [N]
sections." — in the analysis summary, or in the delivery message when fully
automatic mode skips the summary.

**A. Topic Identification** — read the entire transcript systematically; extract all
topics, themes, and concepts; note technical terminology and methodologies; identify
learning objectives and target audience.

**B. Relevance Assessment** — multi-factor analysis.

Explicit indicators (when present): direct emphasis ("This is critical", "Key point"),
repetition frequency, time allocation, instructor emphasis.

Inference criteria (otherwise): duration, depth, number of examples, discussion volume,
introduction order, cross-references from other topics.

Classification and per-topic depth:
- **HIGH**: core concepts, critical procedures
- **MEDIUM**: supporting concepts, useful procedures
- **LOW**: supplementary topics, tangential discussions

Word budgets per tier: `references/content-standards.md` (Discussed Topics). Page
estimates in templates and previews: ~400 words per page.

**C. Dependency Mapping** — identify logical (prerequisites), temporal (learning flow),
and organizational (thematic grouping) relationships.

**Step 1.3 — Analysis Summary.** Present to the user:

```markdown
📋 ANALYSIS COMPLETE

Main Focus: [2-3 sentence description]

Primary Topics Identified:
1. [Topic name] - HIGH relevance
2. [Topic name] - HIGH relevance
3. [Topic name] - MEDIUM relevance
...

Target Audience: [Identified audience]
Estimated Manual Length: ~[X] pages

⚠ Issues Detected: [If any: gaps, unclear sections, undefined terms]

Ready to proceed with manual generation?
```

If the user asks for changes (topics, relevance levels), apply them, then present
the revised summary once more before continuing.

**Internal self-check before presenting the summary:** all topics identified; relevance
levels assigned; dependencies mapped; no critical gaps in understanding.

Report issues only if found: missing context for technical terms, incomplete sections,
ambiguous content requiring user input.

### PHASE 2: User Configuration

**Step 2.1 — Configuration.** Ask for everything still missing in a single message —
omit any question the user's request has already answered, and acknowledge a stated
value instead of asking (✓ Language: Italian (as requested)):

```
⚙ Configuration

Before generating your manual, please choose:

1. Language
   Italian (default — confirm or specify another)

2. Output format
   A) Word Document (.docx) - Editable, professional formatting [RECOMMENDED]
   B) PDF Document (.pdf) - Fixed layout, print-ready
   C) Markdown File (.md) - Plain text, version control friendly
```

Wait for the response before generating anything. No response or "skip" → apply the
default for each still-unanswered question (language: Italian; format: Word .docx).
If the requested format is outside Word, PDF, and Markdown, say so at this step,
offer Markdown as the fallback, and wait for a supported choice before continuing.
Apply the language to ALL content: headings, text, labels.

### PHASE 3: Content Generation

**Step 3.0 — Structure Preview (final checkpoint).** Before writing, present the
planned structure in one block and ask to proceed — the third confirmation of
semi-automatic mode. In interactive mode, expand it into explicit approval of the
full chapter structure.

```markdown
📋 STRUCTURE PREVIEW

[Manual-language headings, one line per chapter with tier and page estimate:]
- Introduction (~1 page)
- [Topic 1] — HIGH (~2 pages)
- [Topic 2] — MEDIUM (~1 page)
- ...
- Summary (~1 page)

Proceed with this structure?
```

If the user asks for changes, apply them, then present the revised structure once more
before generating.

**Step 3.1 — Generation.** Generate the manual with three main sections —
Introduction, Discussed Topics (core), Summary — following the structure,
depth, formatting, and quality standards in `references/content-standards.md`.
For a manual too long to generate in one pass, write each completed chapter to
the output file before generating the next — where the environment supports
incremental writes — so progress survives context limits; the delivered manual
still reads as one unified document.

### PHASE 4: Quality Assurance (Automated)

Run the internal validation checklist (content, accuracy, structure, formatting,
format-specific, language) before delivery — full checklists in
`references/quality-checks.md`. Silent validation when clean; report and ask
"Proceed anyway? [Y/n]" only when issues are found.

### PHASE 5: File Generation and Delivery

Pick the branch per format, since a platform may provide a document skill for one format and
none for another (full implementation details in `references/output-formats.md`, which
carries the same split per format):

- **For a format the platform provides a document skill for** — claude.ai's built-in file
  creation, or Claude Code with the `docx`/`pdf` skills installed — use it; read and follow
  its documentation when the platform exposes it. On claude.ai, let the platform's file
  delivery present the file; do not construct file paths or download links yourself. On
  Claude Code the document skill writes the file to disk, so report its absolute path.
- **`.md` belongs to neither branch:** it needs no document skill. Deliver it as a file
  through the platform's file delivery where there is one, and by writing the file directly
  on Claude Code. If the platform cannot present a `.md` file, present the Markdown content
  in the conversation instead, under the filename the convention gives it.
- **For a format with no document skill (Claude Code without them, local Python):** build
  the file with a short Python script following the same layout spec — libraries,
  fallbacks, and install-consent rules in `references/output-formats.md`.
  Save to the working directory or a path the user gives you, and report the
  absolute file path.
- A format outside Word, PDF, and Markdown: explain it is not supported and offer
  Markdown as the fallback.

Filename: follow the convention in `references/output-formats.md` (File saving).

Before delivering, verify the saved file: filename per the convention, complete
and uncorrupted — re-open it where the platform allows (on Claude Code, also
confirm the saved location).

Deliver with confirmation — the platform's file delivery on claude.ai, the absolute file
path on Claude Code:

```
✅ MANUAL READY

Format: [Word/PDF/Markdown]
Language: [Selected Language]
Length: ~[X] pages across [N] main sections

Content:
• Comprehensive introduction with learning objectives
• [N] topic chapters with adaptive detail levels
• Professional formatting with clear structure
• Detailed summary with key takeaways

📥 [filename — delivered by the platform / saved at absolute path]

Review and let me know if you'd like adjustments!
```

In fully automatic mode, deliver a short version instead: format, language, length,
filename (Example 5).

## Communication guidelines

- Write every user-facing message in the language of the user's request; the
  templates in this skill show the content, not the language.
