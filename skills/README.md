# The skills

This guide explains all eight skills in [ClaudeSkills](../README.md): what each one does, how it works, and what you get. The [main README](../README.md) is the catalog — installation, repository layout, releases. This page is the detail.

The skills form two families:

- **Six document generators** turn rough input — transcripts, requirements, whole websites — into finished documents.
- **The documentation-lifecycle toolkit** holds two skills that keep documentation truthful over time. They never rewrite it silently, and they run on Claude Code only.

Each skill's instructions live in its folder as `SKILL.md` (for example [usecase-extractor/SKILL.md](usecase-extractor/SKILL.md)). The entries below explain what each instructions file does. The two toolkit skills each carry a `README.md` beside it — the full, human-facing explanation of that skill ([consolidate-comments/README.md](consolidate-comments/README.md), [consolidate-specs/README.md](consolidate-specs/README.md)); this page stays the overview of both.

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

The [rules file](../documentation-lifecycle/documentation-lifecycle-rules.md) holds 12 numbered lines, two of them rationale dashes. It is always loaded. It defines the basic taxonomy of artifacts:

- Specifications and code comments are **state**: they describe the system as it is now.
- Implementation plans are **ephemeral**: they record an intention and then expire.
- ADRs are **append-only**: they are never rewritten, only added to. An **ADR** (Architecture Decision Record) is a short document that records one design decision.

Two consequences follow:

- Never append a revision to a specification. Edit the sentence. History lives in version control and in ADRs, not in the spec.
- Delete a comment that merely restates the code. Keep only what the code cannot say about itself.

### Tier 2 — Companion reasoning (read on demand)

The [companion document](../documentation-lifecycle/documentation-lifecycle.md) holds the reasoning behind every rule, with stable identifiers — `S` numbers for settled positions, `O` numbers for open questions. Each design decision also has an ADR in [`documentation-lifecycle/adr/`](../documentation-lifecycle/adr/) — 22 accepted decisions, `0001`–`0022`.

The skills cite these identifiers (`S50`, `O8`, …) instead of re-explaining. This keeps each skill short and the reasoning in one place.

### Tier 3 — Two gated skills

A **gate** is a script check that the procedure must pass before it may proceed. Both skills ship the same gate runner, in Python 3, using only the standard library — nothing to install.

The runner is built on one principle: **the script owns the units and the edits; the agent owns only the judgement.** Every pass, small or large, runs as one batch:

1. **Master record.** The script enumerates every unit (a comment block, a paragraph, a reference occurrence) and writes the *master record* of read-only stubs; sharding then adds one empty *judgement file* (`.j`) per shard for the classifier.
2. **Classification.** The agent fills the judgement files — one decision with one line of evidence per unit. Above about 40 units, or at three or more files, read-only workers classify in parallel, one group of files each. `record-fill` is the only path from a judgement file into the record, and the stubs' `facts:` lines are evidence to confirm, never a verdict.
3. **Gate and panel.** `gate --pre` checks the whole record. Then one in-session **owner panel** covers every frozen unit; each answer becomes a *ruling*, and only a *standing ruling* authorizes `condense`.
4. **Plan.** `batch-plan` cuts the classified scope into **review units** under the caps (by default 200 removed lines and 30 removal judgements each): whole files packed, a large file cut into bottom-up line ranges, and a final nil unit for what does not change.
5. **Run.** Each review unit runs end to end on its own: the script derives its record, gates it, applies it — the files in scope, ADR files, `## To be confirmed` items where the pass writes them, the commit message — commits it, gates it again, closes the rulings it applied, and writes its **review pack**.
6. **Batch end.** You read the packs in order. Where a test suite guards the change (comment passes), a red suite is reverted, never patched forward: `batch-revert` prints the one-line git revert and you run it — the runner never runs destructive git.

So an agent cannot delete code, add code or change a unit it did not classify, and no per-pass edit scripts are needed. The judgement phases and the mechanical phases can also split across two sessions: the stronger model classifies and holds the panel, any model runs the units, and `batch-status` is the handoff. The SKILL.md of each skill is a short step list; the details live in its `reference/` folder, and each skill folder carries its own README with the full explanation.

### consolidate-comments

Runs a `comment` consolidation pass over a declared scope — a set of files. Every comment unit is classified against the code into one of nine dispositions:

- *regenerable → delete* — a competent stranger to the module could rebuild it from the file alone
- *stale fragment → strip* — remove ticket ids, dates and history from a comment that otherwise stays; the script checks that only words were deleted, and the removed fragments go into the commit message
- *condense* — shorten a long comment, only under a standing ruling from you, keeping a listed set of claims
- *obsolete*, *historical decision → ADR*, *still true*
- *contradicts code → suspected defect*, *not verifiable* — frozen byte for byte and escalated
- *ruled → apply* — apply a decision you recorded

Lint and compiler directives (`eslint-disable`, `@ts-ignore`, `# noqa`…) and license headers are never units. The lexer understands strings, regex literals, heredocs and template literals in some thirty languages, including HTML, PHP, SQL, C#, Razor and shell.

Classification runs through the judgement files described in Tier 3, and the stubs' `facts:` point without deciding: a `dup-of` twin is a signal only — duplication is a removal ground in document passes, never here. *Regenerable* is defined by the stranger test: "a competent engineer unfamiliar with this module, reading only this file, with no search and no graph". A removal may be partial, keeping a subset of the unit's own lines, line for line. On comment passes the gates add a code-invariance check — no non-comment token changes — and each unit's gate says when the test suite runs. A source file receives no marker of any kind: what the pass cannot settle stays exactly as it was, and the intake carries the question.

**What you get:** a minimal comment set, plus ADRs for the recovered decisions, escalation lines for every risky case, and a review pack listing every removed line against its reason. See [SKILL.md](consolidate-comments/SKILL.md) and [README.md](consolidate-comments/README.md).

### consolidate-specs

Runs `document` or `severance` passes. A *document* pass realigns a specification or design document to the code it describes. Every unit — a paragraph, or under `document-block` also a list item or a table row — is classified against the code, and a drifted statement is fixed by editing the sentence, never by appending a revision. The truth source is the code **plus** the business rules outside the repository: statements about the code are verified and rewritten, everything external is frozen and arbitrated by you (in comments, by contrast, external truth is a stop condition).

The dispositions beyond the shared ones:

- *duplicate → delete* — two units of one document state the same rule; one goes, its `of:` naming the kept twin (duplication is a removal ground here, never in comments)
- *historical decision → ADR* — the decision and its reason move into an ADR file that the runner itself numbers, names, and writes
- *severed* / *retained* — the two dispositions of a *severance* pass

The stranger test is never applied to prose. Statements the code cannot settle are frozen byte for byte and go to you in one in-session panel; the open ones are collected in a `## To be confirmed` section at the end of the document, which holds open items only — a resolved item disappears. When the committed config asks for it, each whole document a pass verifies also gets a `last-verified-at` marker naming the baseline. Writing a new spec, marking a plan completed, or "shorten this document" is not a pass.

A *severance* pass cuts the inbound references to a document that is being retired. It needs two preconditions: an exclusion inventory declared in `.consolidation.json` (without it the runner refuses the scope, printing `severance DISABLED`) and a reviewer who is not its author. Each reference occurrence — the unit of a severance pass — is severed, the line rewritten or deleted, or retained.

**What you get:** documents that match the code again, ADRs for the relocated decisions, every unresolvable statement collected in a visible `## To be confirmed` section, escalation lines for the risky cases, and a review pack per review unit. See [SKILL.md](consolidate-specs/SKILL.md) and [README.md](consolidate-specs/README.md).

### The core safety rule

Neither skill ever resolves a documentation-versus-code divergence on its own. Every divergence is flagged, frozen byte for byte, and appended as one dated line to `~/.claude/escalations.md`:

```text
- 2026-08-27 `src/a.py:20` — external rule, unverifiable from file (frozen unit, byte-for-byte) [kind=unverifiable-statement state=open observed=a1b2c3d fingerprint=9f2c14e8 context=consolidate-comment-U-C1]
```

The parts are simple:

- the date, the file, and the line number;
- a short description of the problem;
- a category (`kind`);
- a state — `open` means no human has decided yet;
- the repository state when the problem was seen (`observed`), so you know which version of the code the line describes;
- a fingerprint of the flagged text itself (`fingerprint`). This is what the skill matches on, so an entry follows its text when the text moves, and a changed statement earns a fresh entry.

A human arbitrates. In a pass, the frozen units do not wait for you to find the file: the agent brings them all to you in one in-session panel, with a fixed option set per kind — a suspected defect is asked as *Code is right / Code is wrong / Leave open* — and records your answer verbatim. When you rule on a line, your ruling becomes the agent's permission to act on the next pass — once. After the pass that applied it passes its gate, the entry is marked `applied`, so identical text elsewhere in the file cannot reuse your ruling. There is one exception, for an entry about a stale reference. That entry only records that the reference was seen again, which is a sighting and not a judgement. The pass that answers it closes it itself, so the same sighting never authorizes a second pass. The file stays boring by design: one line per problem, no duplicates.

Run the passes at feature or epic completion, or when entering brainstorming on a previously-touched area. Never mid-implementation.

**Honest limits.** The toolkit is best-effort and human-supervised. It is not automated quality control. The gates reduce risk; the human remains the real control. The numeric limits are careful defaults, not measured values — measuring them is open question `O8` in the companion document.
