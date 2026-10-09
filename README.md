# ClaudeSkills

[![License: Apache 2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Skills: 8](https://img.shields.io/badge/skills-8-8A2BE2.svg)](#skills-at-a-glance)
[![Platform: Claude Code | claude.ai](https://img.shields.io/badge/platform-Claude%20Code%20%7C%20claude.ai-D97757.svg)](#where-the-skills-run)
[![validate-skills](https://github.com/StefanoZaghi1987/ClaudeSkills/actions/workflows/validate-skills.yml/badge.svg)](https://github.com/StefanoZaghi1987/ClaudeSkills/actions/workflows/validate-skills.yml)

8 production-ready **Claude skills** by [Stefano Zaghi](https://github.com/StefanoZaghi1987). Six of them turn rough input into finished documents. Two of them keep documentation truthful over time — and they never rewrite it silently.

This page is the catalog. Every skill is explained in detail in the dedicated guide: **[skills/README.md](skills/README.md)**.

## Contents

- [What is a skill?](#what-is-a-skill)
- [Skills at a glance](#skills-at-a-glance)
- [The skills in this repository](#the-skills-in-this-repository)
- [Installation](#installation)
- [Why this repository exists](#why-this-repository-exists)
- [Where the skills run](#where-the-skills-run)
- [Repository layout](#repository-layout)
- [Building, releases, and CI](#building-releases-and-ci)
- [Provenance: how each skill was built](#provenance-how-each-skill-was-built)
- [Languages](#languages)
- [Feedback](#feedback)
- [License](#license)

## What is a skill?

A *skill* is a folder of instructions that teaches Claude a repeatable procedure. The folder always contains a file called `SKILL.md`. When your task matches the skill's description, Claude loads the instructions and follows them step by step.

A skill can also bundle extra files. Common examples are reference documents, Python scripts, and test cases. Claude reads these files only when the procedure needs them. This keeps the skill fast and its instructions short.

Skills run in two places:

- **Claude Code** — Anthropic's coding tool for the terminal and the IDE.
- **claude.ai** — the Claude web app.

One exception: the documentation toolkit runs on Claude Code only. The reason is simple. It reads and writes files on your machine, and the web app cannot do that.

## Skills at a glance

| Skill | Input | Output | File formats | Runs on |
| --- | --- | --- | --- | --- |
| [`usecase-extractor`](skills/README.md#usecase-extractor) | Requirements documents | Use cases and user stories, grouped by actor | DOCX, XLSX, PDF, MD — or several at once | Both |
| [`meeting-review-generator`](skills/README.md#meeting-review-generator) | Meeting transcripts | Formal meeting reports (verbali, SAL) | DOCX, PDF, MD | Both |
| [`technical-summary-generator`](skills/README.md#technical-summary-generator) | Technical documents / URLs | 3-section summary reports | DOCX, PDF, MD | Both |
| [`training-manual-generator`](skills/README.md#training-manual-generator) | Training transcripts | User manuals with relevance-weighted chapters | DOCX, PDF, MD | Both |
| [`technical-translation`](skills/README.md#technical-translation) | Technical documents, any source language | English or other-language translation, formatting preserved | DOCX, PDF, MD | Both |
| [`web-site-to-document`](skills/README.md#web-site-to-document) | Any public website | One self-contained document | DOCX, PDF, MD | Both |
| [`consolidate-comments`](skills/README.md#consolidate-comments) | In-code comment debt | Minimal comment set + ADRs + escalations + review packs | — | Claude Code only |
| [`consolidate-specs`](skills/README.md#consolidate-specs) | Drifted specs and design docs | Realigned documents + ADRs + to-be-confirmed list + escalations + review packs | — | Claude Code only |

The format names are short: **DOCX** is Microsoft Word, **XLSX** is Microsoft Excel, and **MD** is Markdown, a plain-text format. The last two rows have no format, because those two skills do not produce a new document. They edit the files you already have.

Two more terms in the last two rows: an **ADR** (Architecture Decision Record) is a short document that records one design decision. An **escalation** is a problem recorded for a human, who makes the final decision. And a **review pack** is the per-unit report the human reads: the gate verdict first, then every changed or removed line with its reason.

## The skills in this repository

The repository holds two families. The complete guide — what each skill does, how it works, and what you get — is [skills/README.md](skills/README.md).

**Six document generators** turn rough input into finished documents:

- Transcripts become reports and manuals.
- Requirements become use cases.
- Technical documents in any language become the language you need.
- Whole websites become one document.

They share the same shape:

1. They analyze the input.
2. They ask only for what they cannot infer. This is usually the output language and the file format.
3. They write a file: Word, PDF, or Markdown. The use-case skill also writes Excel, and it can deliver several formats from one request.
4. They run a quality check before writing the file.

The website skill adds crawl controls. You set how deep it follows links, how many pages it may fetch, and how fast. It also respects each site's `robots.txt` — a public file that says which pages machines may fetch.

**The documentation-lifecycle toolkit** (two skills, Claude Code only) keeps documentation truthful over time. It is a three-tier system: 12 rules always in context, a long reasoning document read on demand, and two skills that do the actual passes. Its core safety rule: never resolve a documentation-versus-code difference alone. Freeze it, and hand it to a human.

Every pass runs as one batch. The skill classifies the whole scope once into a script-owned record, asks you — in one in-session panel — about every frozen case, and then applies the work in review units the script edits, commits, and reports one at a time, each with a review pack. `consolidate-specs` can also sever the inbound references to a document being retired. And the script never runs destructive git: when units must be reverted, it prints the git line and you run it.

## Installation

### Claude Code (terminal or IDE)

1. Copy the skill folder into your personal skills directory (`~/.claude/skills/`) or a project's (`.claude/skills/`):

   ```bash
   mkdir -p ~/.claude/skills
   cp -r skills/<skill-name> ~/.claude/skills/
   # or install everything at once
   cp -r skills/* ~/.claude/skills/
   ```

2. Start a new Claude Code session. Type `/` and check that the skill appears.

   Note: `skills/README.md` is documentation for humans. Copying it into your skills directory is harmless — Claude Code ignores files that are not skill folders — but you can skip it. Each of the two toolkit skill folders also carries its own `README.md`, the full human-facing explanation of that skill; the agent loads only `SKILL.md` and the files it points to, so these travel harmlessly too.

### claude.ai (web app)

All six document generators work on claude.ai:

1. Download the skill's `.skill` file — or the identical `.zip` — from [GitHub Releases](https://github.com/StefanoZaghi1987/ClaudeSkills/releases).
2. Open **Settings → Features → Skills** (or your Project's settings → Skills).
3. Click **Upload skill** and select the downloaded file.

A `.skill` file is an ordinary zip archive. Use the `.zip` file if your upload dialog only accepts `.zip` files. Both contain the same bytes.

The lifecycle toolkit cannot run on claude.ai. It needs local files and local Python gates, and the web sandbox has neither.

### The toolkit's global files

The two consolidation skills reference these files by absolute path. Neither the skill folders nor the `dist/` archives contain them, so copy them from a clone of this repository — also when you installed the skills from a release archive:

```bash
cp documentation-lifecycle/documentation-lifecycle.md ~/.claude/
mkdir -p ~/.claude/rules && cp documentation-lifecycle/documentation-lifecycle-rules.md ~/.claude/rules/
mkdir -p ~/.claude/documentation-lifecycle-adr && cp documentation-lifecycle/adr/*.md ~/.claude/documentation-lifecycle-adr/   # the ADRs the skills cite
touch ~/.claude/escalations.md   # the escalation intake the passes append to
```

If your claude.ai organization syncs skills into Claude Code (`~/.claude/skills/synced/`), an older consolidation skill uploaded there is a second copy under the same name. Replace it in the organization's skills with the current build, or remove it there.

If your Claude Code build does not load `~/.claude/rules/`, paste the 12 rule lines into `~/.claude/CLAUDE.md` (or the project's `CLAUDE.md`). The effect is identical: the rules stay in context.

The escalation intake defaults to `~/.claude/escalations.md`. You can move it with the `intake_path` key in `.consolidation.json`.

### Check your installation

Both skills ship the same gate runner (CI checks that the two copies are identical). It has a self-test:

```bash
python3 skills/consolidate-comments/scripts/consolidate.py self-test
```

It builds throwaway Git repositories and runs the whole pipeline in them — record, classification, gates, apply, replay — plus a regression check for every defect the runner was rebuilt to close. It prints one `ok` line per check and exits with code 0 when they all pass. On Windows, the command may be `python` instead of `python3`.

## Why this repository exists

Documentation rots as code moves. A specification describes the system as it was written. Then the code changes. Now the specification is quietly wrong.

AI agents add a new danger. An agent may "helpfully" rewrite a specification so it matches the code. The rewrite can hide a real problem. A bug then looks like an agreement that never existed.

The lifecycle toolkit in this repository takes the opposite position:

- It never resolves a documentation-versus-code difference on its own.
- It freezes the difference, byte for byte.
- It appends one dated line to an *escalation file*. **Escalation** means: recorded for a human, who makes the final decision.

The six document generators solve the other half of the problem. They turn rough input — transcripts, requirements, whole websites — into documents you can actually use.

## Where the skills run

Six generators run on both platforms. Each one contains a capability check, written as two branches:

- **If the environment provides the built-in document skills (claude.ai):** the generator uses them, and the platform's file delivery presents the file in the conversation.
- **If it does not (Claude Code, local Python):** the generator builds the file with local Python scripts and reports the absolute file path. It asks you before installing any missing library. Five generators use a short script for this. `web-site-to-document` ships a full local pipeline instead — a crawler, a content extractor, and one builder per output format (see its [guide section](skills/README.md#web-site-to-document)).

This is why the skills are not tied to one platform. They ask what the environment can do, and then they use it.

The two consolidation skills are the exception. They need local files, a local git repository, and local Python gates. The web sandbox has none of these, so they are labeled **Claude Code only** — honestly and in every place they are described.

## Repository layout

```text
├── README.md                   # This page: the catalog
├── skills/                     # The deliverable: 8 skill folders + README.md (the guide)
├── documentation-lifecycle/    # Toolkit companions: rules, the long reasoning doc (settled positions and open questions, stable S/O identifiers), 22 ADRs, escalations stub
├── provenance/                 # The prompts and specs that generated each skill (README inside)
├── build_skills.py             # Builds dist/<name>.skill and dist/<name>.zip from each skill folder
├── .github/workflows/          # validate-skills (every push) and release-skills (on v* tags)
├── dist/                       # Build output (not tracked in git)
└── LICENSE                     # Apache License 2.0
```

Every skill folder contains a `SKILL.md` with the instructions. What sits beside it depends on the skill. The six generators add reference files and a set of test cases, and `web-site-to-document` adds a Python pipeline as well. The two toolkit skills add their shared gate runner (`scripts/`, identical in both), a `reference/` folder the procedure points into, and a `README.md` — the full, human-facing explanation of that skill.

The six generator skills ship their **provenance**: the prompts and project specifications that generated them, stored under `provenance/<skill-name>/`. The toolkit's origin material is under `provenance/documentation-lifecycle/`. You can audit how each skill was built, and regenerate it.

## Building, releases, and CI

Build the distributable files yourself (the build needs PyYAML: `pip install pyyaml`):

```bash
python build_skills.py                    # build all 8
python build_skills.py technical-translation   # build one (or several, by name)
```

The output lands in `dist/`, each skill as both `<name>.skill` and `<name>.zip`. That folder is disposable: delete it and rebuild anytime.

The build is also a validation pass. It fails when:

- a skill folder has no `SKILL.md`.
- the frontmatter is not closed. The **frontmatter** is the small block of settings at the top of `SKILL.md`. It opens with a `---` line and must close with a second one.
- the frontmatter is not valid YAML, or it is not a plain list of `key: value` settings.
- the frontmatter `name` does not match the folder name.
- the name breaks the official format: lowercase letters, digits, and hyphens, at most 64 characters.
- the name contains the reserved words `claude` or `anthropic`.
- the `description` is missing, or is longer than 200 characters. The 200-character limit is claude.ai's upload limit. The two Claude Code-only skills may use up to 1024 characters.
- a bundled `.json` file cannot be read as JSON. The evals files are JSON, so a missing comma stops the build here instead of breaking the skill later.
- a skill file hard-codes a path or a tool name that exists in only one environment. The check reads every `.md`, `.json`, and `.py` file in the skill. It rejects the sandbox paths `/mnt/` and `computer://`, and the invented tool names `present_files` and `create_file`. Any of them would break the skill on the other platform.

Two GitHub Actions workflows protect the repository:

- **validate-skills** runs on every push and pull request. It builds all eight skills. It checks that the two copies of the shared gate runner are identical and runs its self-test. It also runs the web-site-to-document test suite (`skills/web-site-to-document/scripts/test_scrape.py`). Before that suite starts, the workflow installs `weasyprint` and the system graphics libraries it depends on. Those libraries cannot be installed with `pip` on Windows. So this is the only place where the PDF output path is tested from end to end, and it happens on every push. A broken skill fails here, days before release day.
- **release-skills** runs when you push a tag starting with `v` (for example `v1.4.0`). It builds all files and attaches them to a GitHub Release automatically.

Release files are always built by `build_skills.py`, never by hand.

## Provenance: how each skill was built

Every generator skill keeps its origin material under `provenance/<skill-name>/`: the project configuration prompts, the knowledge-generation prompts, and the documents they produced. The [provenance README](provenance/README.md) explains the folder layout and how to audit a skill step by step.

If you want to know why a skill behaves the way it does, the source of that behavior is in the repo. You can audit it, fork it, or generate your own variant.

## Languages

The skills and the toolkit are written in English. Some supporting material is Italian: the web-site-to-document spec and prompts.

Output languages differ per skill. Three generators default to Italian and ask you before writing. `usecase-extractor` reads a source in any language. It writes the document in the language of your request, when that request is Italian or English. For any other request language it writes Italian. `technical-translation` accepts any source language; Italian is its best-covered case, and English its default target. Every skill accepts other languages on request.

## Feedback

Problems, questions, or ideas? [Open an issue](https://github.com/StefanoZaghi1987/ClaudeSkills/issues).

## License

[Apache License 2.0](LICENSE) — © Stefano Zaghi.
