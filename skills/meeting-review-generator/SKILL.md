---
name: meeting-review-generator
description: "Turn meeting transcripts into formal reports: Italian verbali di riunione, SAL, or meeting minutes. Use for 'genera il verbale', 'crea il SAL', 'write meeting minutes'. DOCX/PDF/MD, Italian default."
---

# Meeting Review Generator

## Role

Act as a senior business analyst writing for executives, project managers, and team members.

## Workflow

### Phase 1: Document Analysis

**STEP 1.1** - Read ALL attached or pasted documentation completely (meeting transcripts, historical reports if provided)

**STEP 1.2** - If no meeting transcript is attached or pasted, ask the user — in the language of their request — to provide it and wait. Do not ask report preferences yet.

---

### Phase 2: Meeting Transcript Analysis

**STEP 2.1** - Analyze the meeting transcript(s) you read in Phase 1

**STEP 2.2** - Extract key information:
- **Participants**: Full names, roles, affiliations, contribution patterns
- **Themes**: Distinct topics with technical context and terminology
- **Relevance levels** (infer from discussion depth, decisions made, action items, technical complexity):
  - **High**: Extended discussion, multiple decisions, critical actions, explicit importance markers, executive-level attention
  - **Medium**: Moderate discussion, some decisions/actions, standard follow-up, team-level interest
  - **Low**: Brief mention, informational only, minimal discussion

**STEP 2.3** - Track critical elements:
- **Decisions**: Conclusions reached, choices made, directions set
- **Open Points**: Unresolved issues, questions requiring further discussion
- **Action Items**: Tasks assigned with assignees and deadlines (when specified)
- **Critical Aspects**: Risks, priorities, constraints, urgent items
- **Dependencies**: Logical, temporal, and organizational relationships between themes

**STEP 2.4** - If historical reports provided (optional):
- Analyze theme evolution and progress tracking
- Identify recurring themes and advancement over time
- Maintain narrative continuity across reporting periods

---

### Phase 3: User Preferences

**BEFORE GENERATING OUTPUT:**

**STEP 3.1** - Ask for **everything still missing in a single message**, written in the language of the user's request (the template below shows the content, not the language) — this is your first message once the transcript(s) are available. Omit any question the user has already answered; ask the third question only when multiple transcripts are attached:
> "I've analyzed your meeting transcript(s). Before generating the report, please select:
>
> **1. What language should the report be written in?**
> - Italian (default — confirm or specify another)
> - English
> - Other (please specify)
>
> **2. What format would you like?**
> - DOCX (Microsoft Word) - Best for collaborative editing
> - PDF (Portable Document Format) - Best for formal distribution
> - MD (Markdown) - Best for version control
> - Other (please specify)
>
> **3. One consolidated report, or a separate report per meeting?**"

**WAIT for the user's response before generating anything.**

Default to Italian if the user gives no language preference, and to DOCX if the user gives no format preference. If language and format are settled — and, when multiple transcripts are attached, so is the consolidated/separate choice — send no question and go straight to Phase 4.

---

### Phase 4: Report Generation

**STEP 4.1** - Acknowledge selections, in the language of the user's request (the template shows the content, not the language): "Perfect! I'll generate your meeting review report in [LANGUAGE] as a [FORMAT] file" (or "one report per meeting in [LANGUAGE] and [FORMAT]" if separate reports were chosen)

**STEP 4.2** - Read detailed references:
- `references/output-structure.md` - Complete 4-section report structure
- `references/writing-guidelines.md` - Language, tone, formatting rules
- `references/quality-standards.md` - Quality assurance checklist
- `references/examples.md` - Worked examples of every report component

**STEP 4.3** - Generate report following all specifications

**STEP 4.4** - Quality gate: verify the finished report against the **Final Quality Gate** checklist in `references/quality-standards.md` and fix every failed check silently, before writing the file

**STEP 4.5** - Create the output file:
- Filename: `meeting-review-report-[YYYY-MM-DD]-[LANG].[extension]` — meeting date from the
  transcript (today's date if absent; a consolidated multi-meeting report uses the most recent
  meeting date), LANG = ISO language code (IT, EN, …); when a report would repeat the name of
  one already produced — a separate report on the same meeting date, or a regeneration
  of the same one — append `-2`, `-3`, … before the extension and take the first free
  counter, so an earlier report is never replaced. On Claude Code that means a file in
  the output directory; on claude.ai, a file this conversation already delivered
- Pick the branch per format, since a platform may provide a document skill for one format
  and none for another
- **For a format the platform provides a document skill for** — claude.ai's built-in file
  creation, or Claude Code with the `docx`/`pdf` skills installed — use it; read and follow
  its documentation when the platform exposes it. On claude.ai, let the platform's file
  delivery present the file in the conversation; do not construct file paths or download
  links yourself. On Claude Code the document skill writes the file to disk, so report its
  absolute path
- **`.md` belongs to neither branch:** it needs no document skill. Deliver it as a file
  through the platform's file delivery where there is one, and by writing the file directly
  on Claude Code. If the platform cannot present a `.md` file, present the Markdown content
  in the conversation instead, under the filename the convention gives it.
- **For a format with no document skill (Claude Code without them, local Python):** build the file with a short Python script —
  DOCX via `python-docx`, PDF via `weasyprint` (fall back to `fpdf2` if weasyprint is
  unavailable, fails to install, or fails to run, loading a Unicode TTF font from the
  system — for example `arial.ttf` on Windows or DejaVuSans on Linux — when the report
  text falls outside Latin-1). For a right-to-left report
  language, keep weasyprint for the PDF — it shapes RTL text and fpdf2 does not by default —
  and set paragraph direction in the Word file; the fpdf2 fallback is off for a right-to-left
  language, so if weasyprint is unavailable, ask the user to install it or take Markdown
  instead. Save to the working directory or a path the user gives you, and report the
  absolute file path. If a library is missing, ask the user before running `pip install`,
  or offer Markdown as a fallback.
- Any other format the user chose: generate the content the same way, deliver it with the best
  mechanism the platform offers, and offer MD if the exact format is not achievable
- Page size: A4 for the Word and PDF files, on every platform

**STEP 4.6** - Include brief summary (1-2 sentences about report contents)

## Core Principles

- **Detail proportional to relevance**: the relevance levels assigned in STEP 2.2 set how much detail each theme receives — full lengths and content in `references/output-structure.md`
- **Strategic formatting, professional language**: bolding, lists, tone, and clarity rules in `references/writing-guidelines.md`
- **Numbers inside right-to-left text**: in a right-to-left report language, keep numeric runs — dates, times, percentages, signed or unit-bearing values — reading left-to-right with direction marks, so a sign or a unit never detaches from its value

## Special Handling

**Incomplete transcripts**: Work with what's provided, note missing information, never fabricate details
**Unreadable transcript**: a scanned, image-only PDF, or an attachment type this platform cannot parse, has no extractable text. Say plainly that the file's text cannot be read here, name the file, and ask for a text version or a different format — never guess the meeting's content. On Claude Code, offer first to convert the file locally where a suitable tool is available, and continue from the converted copy. With several transcripts, continue from the readable ones and name the unreadable one in your closing summary, which is where it belongs — the four sections carry the meeting, not the analysis's own gaps — and stop only when none of them can be read.
**Conflicting information**: Note both perspectives, state conflict as open point
**No clear decisions**: State meeting was informational, focus on information shared
**SAL (Stato Avanzamento Lavori) request**: Same four-section structure. If a previous report is provided or available, use it and give full weight to Overall Progress (3.5) and to the completion status of previous actions. If none is available, generate the standard report — never block or ask for one.
**Multiple transcripts**: Ask consolidated-or-separate in the Phase 3 message (consolidated layout: see `references/output-structure.md`)
**Very long transcripts**: Prioritize high-relevance themes; compress low-relevance coverage further; still capture every decision, action, and open point in the Summary
**Ambiguous theme boundaries**: Group by best judgment; sub-themes allowed; keep each point in one theme only
