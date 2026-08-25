# ClaudeSkills

[![License: Apache 2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Skills: 8](https://img.shields.io/badge/skills-8-8A2BE2.svg)](#skills)
[![Platform: Claude Code | claude.ai](https://img.shields.io/badge/platform-Claude%20Code%20%7C%20claude.ai-D97757.svg)](#installation)

A curated collection of **8 production-ready [Claude skills](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview)** by [Stefano Zaghi](https://github.com/StefanoZaghi1987), covering two families:

- **Document-generation skills** — turn requirements documents, meeting transcripts, technical material, and entire websites into professional, structured deliverables (use case specifications, meeting reports, summaries, training manuals, translations).
- **A documentation-lifecycle toolkit** — rules and gated consolidation skills that keep specifications and code comments aligned with the code they describe, with explicit human escalation instead of silent rewrites.

Every project ships not only the skill itself but also the *prompts and specs that generated it* (see [Repository layout](#repository-layout)), so each skill is reproducible and auditable.

## Skills

| Skill | Family | Turns … into … | Output |
|---|---|---|---|
| [`usecase-extractor`](BusinessAnalysis/skills/INSTALLATION_GUIDE.md) | Document generation | Requirements documents | Structured use cases & user stories by actor |
| [`meeting-review-generator`](MeetingReview/skills/README.md) | Document generation | Meeting traces / transcripts | Formal meeting review reports (verbali, SAL) |
| [`technical-summary-generator`](TechnicalSummary/skills/technical-summary-skill/SKILL.md) | Document generation | Technical documents / URLs | 3-section summary reports |
| [`training-manual-generator`](TrainingLessonUserManual/skills/training-manual-generator/SKILL.md) | Document generation | Training-session transcripts | User manuals with relevance-weighted chapters |
| [`technical-translation`](Translation/skills/technical-translation.skill) | Document generation | Italian technical/industrial docs | English translations, formatting preserved |
| [`web-site-to-document`](WebExtractor/skills/web-site-to-document.skill) | Document generation | Any public website | One self-contained document (DOCX/PDF/MD) |
| [`consolidate-comments`](SpecLifecycleManagement/ContentConsolidation/skills/consolidate-comments/SKILL.md) | Lifecycle management | In-code comment debt | Minimal comment set + ADRs + escalations |
| [`consolidate-specs`](SpecLifecycleManagement/ContentConsolidation/skills/consolidate-specs/SKILL.md) | Lifecycle management | Drifted specs / design docs | Realigned documents + escalations |

## Document-generation skills

All six generators share the same shape: they analyze the input, ask only for what they cannot infer (typically output language and file format), and emit a downloadable file — Word (`.docx`), PDF, Excel (`.xlsx`), or Markdown. Multi-phase workflows with quality-assurance checks built in.

### usecase-extractor — [BusinessAnalysis](BusinessAnalysis/skills/INSTALLATION_GUIDE.md)

Extracts and structures use cases and user stories from requirements documents, functional specifications, and business analysis material. Identifies all actors and user roles, extracts explicitly defined use cases, infers the ones implied by functional requirements, and organizes each with code, name, target, inputs, outputs, and dependencies — grouped by user role. Built on 20+ years of business-analysis practice. Output: DOCX / XLSX / MD, multi-language. See the [quick reference](BusinessAnalysis/skills/QUICK_REFERENCE.md).

### meeting-review-generator — [MeetingReview](MeetingReview/skills/README.md)

Transforms meeting recording traces and transcripts into professional business reports — including formal *verbali di riunione* and SAL (Stato Avanzamento Lavori) progress reports. Analyzes participants, extracts themes with relevance levels, tracks decisions, actions and open points, maps dependencies, and integrates historical context across multiple meetings for progress tracking. Output: DOCX / PDF / MD; Italian default, English and others supported. *(Guide in Italian.)*

### technical-summary-generator — [TechnicalSummary](TechnicalSummary/skills/technical-summary-skill/SKILL.md)

Generates structured summary reports from uploaded files (PDF, DOCX, TXT, MD, HTML) or URLs, aggregating multiple sources into one corpus. An 8-phase workflow — retrieval, size evaluation, analysis, terminology preparation, user interaction, summarization, QA, file output — produces reports with mandatory `[INTRODUCTION]`, `[DISCUSSED TOPICS]`, and `[SUMMARY]` sections. Output: DOCX / PDF / MD, multilingual (Italian default).

### training-manual-generator — [TrainingLessonUserManual](TrainingLessonUserManual/skills/training-manual-generator/SKILL.md)

Bridges ephemeral training content and permanent knowledge documentation: transforms training-session recording traces into comprehensive user manuals. Performs deep content analysis, identifies topics with relevance assessment, maps dependencies, and writes chapters whose depth is proportional to topic importance. Ships an [evals harness](TrainingLessonUserManual/skills/training-manual-generator/evals/evals.json) with sample transcripts, plus [examples](TrainingLessonUserManual/skills/training-manual-generator/EXAMPLES.md) and a [quickstart](TrainingLessonUserManual/skills/training-manual-generator/QUICKSTART.md). Output: DOCX / PDF / MD; Italian default. Semi-automatic by default, with fully-automatic / interactive / quick modes.

### technical-translation — [Translation](Translation/skills/technical-translation.skill)

Automated translation of Italian industrial and manufacturing documentation — manuals, specifications, safety guides, installation procedures — primarily into English. Preserves document formatting completely, keeps terminology consistent across the document, and treats safety-critical content (ISO/IEC/CE references) with dedicated accuracy rules. 7-phase workflow. Output: DOCX / PDF. *(The `.skill` file is a zip archive — see [Installation](#installation).)*

### web-site-to-document — [WebExtractor](WebExtractor/skills/web-site-to-document.skill)

Extracts the complete content of any public website and reproduces it as a single structured, searchable document — Word, PDF, or Markdown — with user-selectable crawl depth. Ships its own stdlib-friendly Python pipeline (`scrape.py`, Chrome-based `chrome_extract.py`, and per-format builders). *(Spec and prompts in Italian.)*

## Documentation-lifecycle toolkit

Location: [`SpecLifecycleManagement/ContentConsolidation/`](SpecLifecycleManagement/ContentConsolidation/)

The flagship of this repository: a three-tier system that keeps documentation truthful over time.

1. **[Rules](SpecLifecycleManagement/ContentConsolidation/rules/documentation-lifecycle-rules.md)** (12 lines, always in context) — the artifact taxonomy: specs and code comments are ***state*** (they describe the present), implementation plans are ***ephemeral***, ADRs are ***append-only***. Never append a revision to a spec — edit the sentence, because history lives in version control and in ADRs. Delete comments that merely restate the code.
2. **[Companion reasoning](SpecLifecycleManagement/ContentConsolidation/.claude/documentation-lifecycle.md)** (600 lines, read on demand) — settled positions `S1`–`S172` and open questions `O1`–`O17` with stable identifiers, so the skills can cite (`S50`, `O8`, …) instead of re-explaining.
3. **Two gated skills** (rare, deliberate repair procedures) — each ships a stdlib-only Python 3 gate runner and enforces numeric bounds on how much may be removed without human arbitration:

   - **[`consolidate-comments`](SpecLifecycleManagement/ContentConsolidation/skills/consolidate-comments/SKILL.md)** — classifies every comment unit in a declared scope against the code into seven dispositions (*regenerable → delete*, *obsolete*, *historical decision → ADR*, *still true*, *contradicts code → suspected defect*, *not verifiable*, *ruled*). Deletes only what a competent stranger to the module could reconstruct from the file alone.
   - **[`consolidate-specs`](SpecLifecycleManagement/ContentConsolidation/skills/consolidate-specs/SKILL.md)** — `document` and `severance` passes that realign specs and design docs to the code they describe, relocate historical rationale to ADRs, and hand unresolvable statements to a human via a `## To be confirmed` section.

**The core safety rule:** neither skill ever resolves a documentation-versus-code divergence on its own. Divergences are flagged, frozen byte-for-byte, and appended as dated lines to `~/.claude/escalations.md` — a human arbitrates. Run the passes at feature or epic completion, or when entering brainstorming on a previously-touched area; never mid-implementation.

## Repository layout

Most project areas follow the same pattern:

```
<Area>/
├── docs/                 # Project context, instructions, and generated analysis
├── project/
│   ├── 1_config/         # Phase-1 prompts: project configuration
│   └── 2_knowledge/      # Phase-2 prompts: knowledge/skill generation
└── skills/               # The deliverable: installable skill (.skill / .zip + sources)
```

Two areas deviate: [`WebExtractor/`](WebExtractor/) keeps just `prompts/` + `skills/`, and [`SpecLifecycleManagement/`](SpecLifecycleManagement/) carries the [`ContentConsolidation/`](SpecLifecycleManagement/ContentConsolidation) bundle (rules, companion doc, two skills) as its deliverable.

> `.skill` files are ordinary zip archives containing the skill folder (`SKILL.md` + references). Where both a `.skill` and a `.zip` exist they are identical; either can be installed.

## Installation

### Claude Code (CLI / IDE)

Copy the skill folder into your personal skills directory (`~/.claude/skills/`) or a project's (`.claude/skills/`):

```bash
# e.g. for the consolidation toolkit
cp -r SpecLifecycleManagement/ContentConsolidation/skills/consolidate-comments ~/.claude/skills/
cp -r SpecLifecycleManagement/ContentConsolidation/skills/consolidate-specs    ~/.claude/skills/
```

For the packaged skills (`.skill` / `.zip`), unzip into the same directory:

```bash
unzip WebExtractor/skills/web-site-to-document.skill -d ~/.claude/skills/
```

The consolidation toolkit also expects its rules and companion doc — see each `SKILL.md` for the exact placement.

### claude.ai (web / Projects)

1. Open **Settings → Capabilities → Skills** (or your Project's settings → Skills).
2. **Upload skill** and select the `.skill` file (e.g. `Translation/skills/technical-translation.skill`).
3. The skill is now available in that project.

### Notes

- The three generators default to **Italian** output and ask for language/format before writing; `technical-translation` is Italian → English by design. All skills accept other languages on request.
- The two consolidation skills ship Python 3 gate runners with **no third-party dependencies** — verify an install anytime with `python <skill>/scripts/consolidate_comments.py self-test`.

## Languages

Core skills and the lifecycle toolkit are written in English. Some supporting material is Italian: the WebExtractor spec and prompts, and the MeetingReview guide. Output languages are per skill (see above).

## License

[Apache License 2.0](LICENSE) — © Stefano Zaghi.
