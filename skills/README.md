# The skills

This guide explains all eight skills in [ClaudeSkills](../README.md): what each one does, how it works, and what you get. The [main README](../README.md) is the catalog — installation, repository layout, releases. This page is the detail.

The skills form two families:

- **Six document generators** turn rough input — transcripts, requirements, whole websites — into finished documents.
- **The documentation-lifecycle toolkit** holds two skills that keep documentation truthful over time. They never rewrite it silently, and they run on Claude Code only.

Each skill's instructions live in its folder as `SKILL.md` (for example [usecase-extractor/SKILL.md](usecase-extractor/SKILL.md)). The entries below explain what each instructions file does.

## The six document generators

All six generators share the same shape:

1. They analyze the input.
2. They ask only for what they cannot infer. This is usually the output language and the file format.
3. They write a file: Word (`.docx`), PDF, or Markdown (`.md`). `usecase-extractor` also writes Excel (`.xlsx`), and it is the only one that does.
4. A dedicated quality-assurance phase checks the result before the file is written.

Where the file is built adapts to the environment. On claude.ai, the generators use the built-in document skills of that platform. On Claude Code, they build the same formats locally with Python. `python-docx` writes Word, `weasyprint` writes PDF, and `openpyxl` writes Excel. The skill then tells you the saved file's path. If a Python library is missing, the skill asks you before installing anything. The exception is `web-site-to-document`: on Claude Code it runs its own pipeline instead of this shared approach (see its section below).

Two kinds of bundled support appear in the entries below:

- A **reference file** is an extra document with examples, templates, or quality standards. The skill reads it only at the step that needs it, so the instructions stay short. All six generators bundle reference files. `web-site-to-document` bundles one — the browser-extraction workflow — and also ships a full Python pipeline (see its section below).
- An **evals harness** is a small set of test cases with the expected result. All six generators ship one: `meeting-review-generator`, `technical-summary-generator`, `training-manual-generator`, `technical-translation`, `usecase-extractor`, and `web-site-to-document`. Five include sample input material; the `web-site-to-document` cases are prompt-only, because the input is a site URL. To run one, follow the official eval loop. Give each case's prompt to a fresh session with the skill active. Run it once without the skill as a baseline. Then grade the `assertions` in `evals/evals.json` against the results. In Claude Code, the `skill-creator` plugin runs this loop for you. The file format is documented at [agentskills.io](https://agentskills.io/skill-creation/evaluating-skills).

Every generator also keeps its **provenance** under `provenance/<skill-name>/`: the prompts and specifications that generated the skill. If you want to know why a skill behaves the way it does, the source of that behavior is there. You can audit it, fork it, or generate your own variant.

### usecase-extractor

Extracts use cases and user stories from requirements documents, functional specifications, and business-analysis material. The skill first finds every actor and user role. It then extracts the use cases that the document states explicitly, and infers the ones that the functional requirements imply. Each use case is organized with:

- a code, a name, and a priority;
- its target;
- its main flow and variations;
- its inputs, outputs, and dependencies;
- its source section;
- a user story.

Use cases are grouped under the user role they belong to.

The input can be an uploaded file or text pasted into the chat. Accepted formats: PDF, Word, RTF, Excel, CSV, Markdown, and plain text. Several documents can be merged into one catalog, and they may be written in different languages. If an input cannot be read — for example, a scanned, image-only PDF — the skill says so and asks for a readable version. A verification step checks the catalog against the source before any file is written.

The source language and the document language are independent. The document follows the language of your request, when that request is Italian or English. For any other request language it is Italian. You can also name any language you want. The section a use case comes from always stays in the source language, so you can find it in the original file. The document's own vocabulary is translated, and carries the source term in brackets at first use — `Draft status (Bozza)`. Use case codes such as `ADM-001` never change.

**What you get:** a complete, actor-by-actor catalog of use cases as DOCX, XLSX, PDF, or Markdown. You can also ask for several of those formats at once, and the skill writes each one. Worked examples and per-format output templates ship as reference files, plus an evals harness with sample requirements documents, including spreadsheet and plain-text sources. *(Spec and prompts: [provenance](../provenance/usecase-extractor/).)*

### meeting-review-generator

Turns meeting transcripts into formal business reports. This includes Italian *verbali di riunione* (official meeting records) and SAL reports (Stato Avanzamento Lavori — work-progress reports). The skill analyzes participants and themes, and rates the relevance of each theme. It tracks decisions, actions, and open points, and maps dependencies between items. Across several meetings, it integrates history, so you can follow progress over time.

Some transcripts cannot be read: a scanned, image-only PDF, or a file type the platform cannot open. The skill says so and asks for a readable version. It does not invent a meeting.

**What you get:** a formal meeting report as DOCX, PDF, or Markdown. Italian is the default language; English and others are supported. Reference files define the report structure, the writing guidelines, the quality standards, and worked examples. An evals harness with sample transcripts and a sample previous report is included. *(Spec and prompts: [provenance](../provenance/meeting-review-generator/).)*

### technical-summary-generator

Builds structured summary reports from files (PDF, DOCX, TXT, MD, HTML) or URLs. It can merge several sources into one report. An 8-phase workflow drives the skill: retrieval, size evaluation, analysis, terminology preparation, user interaction, summarization, QA, and file output. Large documents are split into chunks, then consolidated into one report.

Every report has three mandatory sections — introduction, discussed topics, and summary — with headings written in the report's language.

**What you get:** a three-section summary report as DOCX, PDF, or Markdown, in several languages (Italian default), backed by an evals harness with sample material. *(Spec and prompts: [provenance](../provenance/technical-summary-generator/).)*

### training-manual-generator

Turns training-session transcripts into user manuals. Training content is usually lost after the session; this skill converts it into permanent documentation. The skill analyzes the content in depth, rates the relevance of each topic, and maps dependencies between topics. Chapter depth follows topic importance: important topics get full chapters, minor topics get less space. If a transcript is too large to analyze in one pass, the skill works through it in sections. It carries running notes forward and merges them into one analysis.

Three modes are available: semi-automatic (the default), fully-automatic (also invoked as "quick mode"), and interactive. Some sources cannot be read: a scanned, image-only PDF, or a file type the platform cannot open. The skill says so and asks for a readable version. It does not guess what the session covered.

**What you get:** a user manual as DOCX, PDF, or Markdown (Italian default), with chapter depth proportional to topic importance. Five reference files ship with the skill: content standards, worked examples, source examples, output formats, and quality checks. An evals harness with sample transcripts is included. *(Spec and prompts: [provenance](../provenance/training-manual-generator/).)*

### technical-translation

Translates industrial and manufacturing documentation into English or other languages: manuals, specifications, safety guides, and installation procedures. Any source language is accepted; Italian is the best-covered case. Document formatting is preserved, and terminology stays consistent across the whole document. Safety-critical content — ISO, IEC, and CE references — follows dedicated accuracy rules.

Several documents in one request are translated one at a time. You answer the configuration questions once, for all of them. Documents up to 30,000 tokens (about 45 pages) are translated in one pass. Larger documents are split at logical boundaries. A shared terminology database keeps the wording consistent across parts. A signal word — a printed safety label such as AVVISO, Italian for "notice" — is placed by hazard severity, never by word form. For right-to-left target languages, numbers keep their left-to-right order, and the PDF is built with `weasyprint`, which shapes that script correctly.

A 7-phase workflow drives the skill. Three reference files hold the terminology mappings, the safety-language rules, and the common translation patterns.

**What you get:** a translated document as DOCX, PDF, or Markdown that keeps the original formatting, plus an evals harness with sample documents. *(Spec and prompts: [provenance](../provenance/technical-translation/).)*

### web-site-to-document

Extracts the complete content of a public website and writes it into one structured, searchable document — Word, PDF, or Markdown. The skill ships its own Python pipeline. One script (`main.py`) runs it. The other scripts do the parts:

- a crawler fetches pages;
- a content extractor cleans the HTML;
- shared helpers connect them;
- one builder per format writes the file. Word uses `python-docx`; PDF uses LibreOffice in headless mode — without a window — or `weasyprint` as the fallback.

A separate helper extracts pages through a real Chrome browser. The pipeline needs `requests`, `beautifulsoup4`, and `lxml`, plus `python-docx` for Word. The exact prerequisites are listed in the [SKILL.md](web-site-to-document/SKILL.md).

You control how far the crawl goes:

- `--depth` sets how many levels of links the crawl follows from the start page (or `unlimited`).
- `--max-pages` caps the number of pages.
- `--include-path` / `--exclude-path` keep the crawl inside chosen URL paths, or outside them. This is how you archive one section of a site.
- `--rate-limit` sets the minimum wait between requests. The default is 1 second, and it covers images too. The browser-extraction helper takes the same flag, for the images it downloads from the site.
- `--allowed-domains` extends the crawl to other domains you name (only with custom domain scope).

The skill is polite by design. It reads each site's `robots.txt`, the public file that says which pages machines may fetch, and follows it in every mode and for every host. When a server answers HTTP 429 (too many requests), the crawl waits for the time the server names and retries once. A redirect that lands outside the agreed scope is rejected. A `<base href>` tag — common in modern web apps — resolves that page's relative links, as a browser would.

The extraction method adapts to the environment and to the site. JavaScript-rendered or bot-protected sites switch to a browser-based workflow (Chrome MCP — extraction through a real Chrome browser via a connector). The connector is an environment requirement on every platform. Without one, the skill says so plainly instead of returning a half-empty document, and suggests trying from your local machine.

Before the file is written, a verification step checks that the extraction is worth delivering. It checks six things:

- enough text on each page;
- the page count the crawl agreed to;
- A4 page size;
- the filename convention;
- the References section;
- no empty chapter.

On Claude Code the pipeline enforces these in code, and refuses to build a near-empty archive. On claude.ai the skill applies the same checks itself.

Reading direction is decided for each block, not for the whole document. A site written in Arabic or Hebrew keeps its right-to-left layout in the Word and PDF output. That covers three things: the direction of a paragraph, the side a list number sits on, and the column order of a table. The fixed English labels stay left-to-right: the cover, the Table of Contents, and the References section. Any code block stays left-to-right too.

**What you get:** one self-contained document that covers an entire site, plus an evals harness with prompt-only test cases. The spec and prompts behind this skill are in Italian; they are stored openly under [provenance](../provenance/web-site-to-document/).

## The documentation-lifecycle toolkit

Location: [`documentation-lifecycle/`](../documentation-lifecycle/) (rules and companion document) plus the two skills documented below. **Claude Code only.**

This is the flagship of the repository. It is a three-tier system that keeps documentation truthful over time. Its core promise: neither skill ever fixes a disagreement between documentation and code on its own. Every risky case becomes an *escalation* — one dated line in a file that waits for a human decision. The anatomy of that line is explained in [the core safety rule](#the-core-safety-rule) below.

### Tier 1 — Rules (always in context)

The [rules file](../documentation-lifecycle/documentation-lifecycle-rules.md) holds 12 rules. It is always loaded. It defines the basic taxonomy of artifacts:

- Specifications and code comments are **state**: they describe the system as it is now.
- Implementation plans are **ephemeral**: they record an intention and then expire.
- ADRs are **append-only**: they are never rewritten, only added to. An **ADR** (Architecture Decision Record) is a short document that records one design decision.

Two consequences follow:

- Never append a revision to a specification. Edit the sentence. History lives in version control and in ADRs, not in the spec.
- Delete a comment that merely restates the code. Keep only what the code cannot say about itself.

### Tier 2 — Companion reasoning (read on demand)

The [companion document](../documentation-lifecycle/documentation-lifecycle.md) is 600 lines. It holds the reasoning behind every rule, with stable identifiers: `S1`–`S172` for settled positions, `O1`–`O17` for open questions.

The skills cite these identifiers (`S50`, `O8`, …) instead of re-explaining. This keeps each skill short and the reasoning in one place.

### Tier 3 — Two gated skills

A **gate** is a script check that the procedure must pass before it may proceed. Each skill ships a gate runner in Python 3 that uses only the standard library — nothing to install. The gates enforce numeric bounds on how much may be removed without *human arbitration* (a person's judgment).

### consolidate-comments

Runs a `comment` consolidation pass over a declared scope — a set of files. Every comment unit is classified against the code into one of seven dispositions:

- *regenerable → delete*
- *obsolete*
- *historical decision → ADR*
- *still true*
- *contradicts code → suspected defect*
- *not verifiable*
- *ruled → apply*

The pass deletes only what a competent stranger to the module could rebuild from the file alone.

**What you get:** a minimal comment set, plus ADRs for the recovered decisions and escalation lines for every risky case. The gate runner has a `self-test` command. It runs every gate against a test file in a throwaway Git repository. A broken gate therefore fails there, and not on your documents. See [SKILL.md](consolidate-comments/SKILL.md).

### consolidate-specs

Runs `document` or `severance` passes. A *document* pass realigns a specification to the code it describes. A *severance* pass cuts the inbound references to a document that is being retired. Historical rationale moves to ADRs. Statements that cannot be resolved go to a human through a `## To be confirmed` section at the end of the document.

**What you get:** documents that match the code again, with every unresolvable statement collected in a visible to-do list for a human. See [SKILL.md](consolidate-specs/SKILL.md).

### The core safety rule

Neither skill ever resolves a documentation-versus-code divergence on its own. Every divergence is flagged, frozen byte for byte, and appended as one dated line to `~/.claude/escalations.md`:

```text
- 2026-08-27 `src/a.py:20` — external rule, unverifiable from file [kind=unverifiable-statement state=open observed=a1b2c3d fingerprint=9f2c14e8 context=consolidate-comments]
```

The parts are simple:

- the date, the file, and the line number;
- a short description of the problem;
- a category (`kind`);
- a state — `open` means no human has decided yet;
- the repository state when the problem was seen (`observed`), so you know which version of the code the line describes;
- a fingerprint of the flagged text itself (`fingerprint`). This is what the skill matches on, so an entry follows its text when the text moves, and a changed statement earns a fresh entry.

A human arbitrates. When you rule on a line, your ruling becomes the agent's permission to act on the next pass. There is one exception, for an entry about a stale reference. That entry only records that the reference was seen again, which is a sighting and not a judgement. The pass that answers it closes it itself, so the same sighting never authorizes a second pass. The file stays boring by design: one line per problem, no duplicates.

Run the passes at feature or epic completion, or when entering brainstorming on a previously-touched area. Never mid-implementation.

**Honest limits.** The toolkit is best-effort and human-supervised. It is not automated quality control. The gates reduce risk; the human remains the real control. The numeric limits are careful defaults, not measured values — measuring them is open question `O8` in the companion document.
