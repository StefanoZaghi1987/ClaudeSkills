# Prompt — Generate a Claude Project for Documentation & Spec Lifecycle Management in Spec-Driven Development

---

## Role

Act as a full-stack software engineer with 20+ years of experience, specialized in spec-driven development and in the practical use of generative AI coding agents (Claude Code and equivalents) on large, long-lived production codebases. You have direct experience with the failure modes of AI-assisted documentation at scale. You are opinionated, concise, and you flag disagreement rather than accommodating a premise you think is wrong.

## Task

Produce **three downloadable artifacts** that together configure a Claude Project dedicated to the theme described below. Do not produce a single combined document, and do not deliver the content inline in chat only — each of the three must be a separate downloadable file:

1. **`project-description.txt`** — a synthetic project description in plain text (`.txt`), suitable for pasting into the "What are you trying to achieve?" / project description field when setting up a Claude Project.
2. **`project-overview.md`** — a detailed and exhaustive description of the project in Markdown (`.md`), intended to be uploaded as the primary knowledge document of the project.
3. **`project-instructions.md`** — the project instructions in Markdown (`.md`), intended to be pasted into the Claude Project's custom instructions field, so that every conversation started inside the project inherits the right context, constraints, and behavior.

All three deliverables must be written in **English**.

---

## Domain Context — read fully before producing anything

### The workflow in use

Every development session follows this sequence:

1. **Brainstorming** — sharing and exploring ideas.
2. **Specification** — writing a design spec / feature spec.
3. **Implementation plan** — the spec is transformed into a detailed development plan.
4. **Implementation** — execution driven by the plan, frequently parallelized across sub-agents.
5. **Code review**, followed by bug fixing and subsequent modifications as needed.

This structure is deliberate and must be preserved. Any recommendation that requires abandoning or restructuring it is out of scope.

### Environment

- Claude Code as the primary coding agent, with a plugin-based workflow (`brainstorm → design spec → implementation plan → sub-agent execution`).
- A codebase knowledge graph built via Tree-sitter plus LLM semantic extraction, used for navigation and orientation, and queryable from the CLI.
- Large, long-lived enterprise codebase; any arbitrary technological stack.
- Significant amounts of accumulated project documentation, in-code comments, specs, implementation plans, and years of revisions and bug-fix history.
- All documentation and specification maintenance work is performed **by coding agents**, not by hand. This is a hard constraint: every recommendation must be executable by an agent and verifiable by a human reading a diff.

### The observed problem

On a large codebase with heavy documentation history, AI agents asked to change a business rule, a spec, or a comment consistently **append a revision** instead of **editing the existing content**. They add "Revision 3", "Update 2026-07-14", stacked layers of historical notes, and references to old bug fixes.

This has real upside: history is preserved, past problems remain traceable, and context is richer. But it also:

- inflates token consumption and fills the context window;
- injects obsolete and outdated information into the working context;
- produces documents in which multiple statements contradict each other, with no ordering signal telling the agent which one is current;
- makes the eventual consolidation pass increasingly expensive and increasingly risky.

The need is therefore **periodic consolidation**: collapsing accumulated revisions into a single, complete, current, non-contradictory statement of the truth — across project documentation, specs, implementation plans, and in-code comments — without silently losing information that still matters.

### Diagnosis to encode in the project

The append behavior is not a defect; it is a rational response to an incentive. Deleting information requires knowledge the agent does not have (*is this still true? does anything depend on it?*), while appending is always safe. Unless a document explicitly states where history lives, the agent assumes history lives in that document and preserves it.

The root cause is that documents are performing two incompatible functions simultaneously: **describing current state** and **recording history**. These have opposite lifecycles — the first must be rewritten, the second is immutable by definition. Keeping both in the same file guarantees accumulation.

### Artifact taxonomy (the primary intervention)

| Artifact | Function | Lifecycle |
|---|---|---|
| Spec / design doc | **State** | Present tense, describes the system as it is now. No "Revision N" sections. When a business rule changes, the sentence changes. Re-aligned to reality at merge time, not only before implementation. |
| Implementation plan | **Ephemeral** | Has a death date. Marked `status: completed` mechanically at merge; archived later at the author's discretion; **excluded from all retrieval** once archived (indexes, globs, knowledge graph). |
| ADR | **Append-only log** | One file per decision, immutable, with `status: accepted \| superseded-by ADR-NNN`. All historical rationale that currently pollutes specs belongs here. |
| Code comments | **State** | Explain why the code is the way it is *now*. Never "fix for bug #1234" — that is a commit message, already in git. |

### Positions already settled — treat these as decided, do not re-litigate

- The source of truth about *what the system does* is **the code itself**, not the comments. Comments can lie, and are the only artifact in the repository that can lie without immediate consequence — no test breaks. Comments must therefore be **compacted, not annotated**: they should carry only current truth.
- The operational rule for comments is not "keep comments true" but **"reduce the surface of what can lie."** A comment that restates the code must be **deleted, not compacted** — it adds nothing and can diverge. This category is large in AI-assisted codebases, because models comment generously by default.
- Only comments carrying what the code cannot say about itself survive: the reason for a non-obvious choice, an external constraint (SAP B1 / Service Layer behavior, a TwinCAT quirk), a rejected alternative and why, an invariant not expressible in the type system. This category must be **defended conservatively** during consolidation.
- Historical bug-fix references in comments are not to be compacted but **relocated** — to a commit message or an ADR.
- Implementation plans are **archived, not deleted** — but archived plans must be invisible to retrieval. A readable archived plan is worse than a deleted one: it carries the authority of a spec and the content of an intention.
- Plan status marking (`completed`) happens **at merge, immediately**; physical archiving happens **later, at the author's discretion**. These two events are deliberately decoupled. The reason: between merge and archiving, a live plan saying "I will do X" coexists with a spec saying "the system does Y", and if implementation diverged from the plan (it always does), the agent has two sources in conflict and no criterion for preferring one.
- If, at the end of a feature, the plan contains information that would be painful to lose, that information belonged in the spec or in an ADR and never made it there. It is a signal about a missed transfer, not a reason to keep the plan alive.
- **Default is implicit:** unmarked content is current. Annotating a paragraph as "still true" is noise that ages worse than the content itself — a six-month-old `verified: true` is a false claim wearing a guarantee.
- **No meta-annotation inside code comments, ever.** A comment describing the verification status of another comment is the bottom of the barrel.
- The only persistent marker worth defending is per-document, not per-paragraph: `last-verified-at: <commit-sha>` in the front matter. It costs nothing, ages informatively rather than deceptively, and gives the agent a signal about how much to trust the file.

### Rules vs. skills — the split to encode

These are not alternatives. **Rules prevent accumulation; skills repair what accumulated anyway.** Rules alone leave the pre-existing debt untouched (they do not apply retroactively); skills alone condemn the project to perpetual maintenance.

The assignment criterion is mechanical: a directive belongs in a **rule** if it must apply *always, at zero activation cost*; it belongs in a **skill** if it is a *rare, multi-phase procedure with risk of information loss*.

**Rules** (`CLAUDE.md`, deliberately kept under ~20 lines for this domain — a 300-line `CLAUDE.md` is no longer a rule set, it is documentation the agent dilutes):

- the artifact taxonomy;
- the no-append rule on specs, **stated with its justification** ("history lives in git and in ADRs") — the justification is what makes the agent willing to overwrite;
- the comment policy: only what the code cannot say about itself; no bug-fix references;
- the implicit default: unmarked = current;
- the obligation to **flag rather than rewrite** anything that is no longer verifiable.

**Skills — exactly two.** The division criterion is *not* the artifact type but **what truth is verified against, and who has the final word**:

1. **Comment consolidation.** Truth source: the code, inside the repository. The agent can decide autonomously — read the function, compare the comment, delete the redundant, collapse historical layers, relocate bug-fix references. High volume, per-file or per-module scope, output verifiable by reading the diff, little human judgment required.
2. **Spec and design-doc consolidation.** Truth source: the code **plus** business rules that live outside the repository. The agent cannot close the loop alone. It produces the exhaustive classification, rewrites what is verifiable, and hands over a `## To be confirmed` section. Low volume, high risk, human arbitration mandatory.

Merging these two into one skill costs twice: irrelevant instructions get loaded (half the procedure never applies), and — worse — the trigger description becomes generic, so the skill fires when it shouldn't and fails to fire when it should. Trigger precision is the real design constraint of skills. Fragmenting into five has the opposite problem: overlapping triggers, arbitrary selection, and loss of the ability to reason about what was actually done.

**Neither rule nor skill** — these are mechanical operations that must not consume a context load to perform what `sed` would do:

- marking a plan `completed` → a merge-checklist step or a hook;
- archiving plans and excluding them from retrieval → a script plus retrieval configuration;
- updating `last-verified-at` → a side effect of a skill, not a skill.

### The consolidation procedure

1. **Commit first.** Consolidation is always a separate commit, never mixed with functional changes. The diff must be readable as a semantic diff, which is what makes it reversible.
2. **Classify before rewriting.** Pass 1 labels every paragraph as `still true` / `obsolete` / `historical decision → ADR` / `not verifiable`. Only then rewrite. Without this forcing pass, the agent jumps straight to synthesis and that is where loss occurs.
3. The classification is **exhaustive but ephemeral**: it goes to a scratch report (e.g. `consolidation-report.md`, not committed) or to chat — never into the persisted document. Rationale: if the agent flags only what it believes obsolete, silence becomes ambiguous between "verified, current" and "never examined" — two radically different things the human cannot distinguish. And "never examined" is the common case, because attention over a long document is not uniform: agents work well at the beginning and the end and skim the middle. Exhaustive classification is a forcing function that makes **coverage** visible. The verdict per paragraph matters less than the guarantee that every paragraph was looked at.
4. **Verify against the code, not against the document.** Nothing survives unless it is verifiable in the current code or is a genuine decision, constraint, or rationale. The code is the truth about *what it does*; the unique value of documents is the *why* and what was rejected.
5. **`not verifiable` is the critical bucket.** It is never deleted silently: it goes into a `## To be confirmed` section in the document and escalates to the human. That section legitimately belongs in the persisted document, because it represents open work assigned to a person — not metadata.
6. **Review the removed lines, not the result.** Reading the final document does not reveal what was lost; reading the `-` lines does.

### Triggers

Correct:

- completion of a feature or epic (the plan dies; what it taught flows back into the spec);
- **at the start of brainstorming on an area touched in the past** — this grafts onto the existing workflow and yields clean context before the most token-expensive phase;
- whenever the agent is observed citing obsolete information — the most reliable diagnostic signal.

Wrong: **mid-implementation. Never.**

Calendar-based triggers are inferior to event-based ones. Doing it "by feel every once in a while" is the worst mode, because information loss happens precisely when no checklist is in play.

### The asymmetry that must be explicit

On technical details the agent may decide autonomously what is obsolete, because it can verify. **On business rules it may not**, because the source of truth lives outside the repository. This distinction has to be written explicitly into the skills, otherwise the outcome is technically impeccable consolidations that delete a regulatory constraint nobody had implemented yet.

### Critical positions to carry into the project — do not soften these

- **The optimization target is upstream, not downstream.** Reducing after the fact costs far more than not accumulating in the first place. If only one thing gets built, it is append-resistant documents by construction. The consolidation skills are maintenance, not the solution.
- **Many documents should not be compacted — they should be deleted.** A significant share of documentation in an AI-assisted codebase is write-once, read-never: produced because producing it was cheap. The question to ask of every file is "if this disappeared, what would break?" Aggressive deletion returns more than accurate compaction, and costs less.
- **The enemy is not length, it is contradiction.** A long, coherent, true document costs tokens. A short one with three conflicting statements costs correctness — and hours spent working out why the agent implemented the wrong rule. Optimize non-contradiction first, brevity second.
- **Both skills are, first and foremost, scoping problems.** The expensive part is not rewriting; it is deciding which files to work on. Blanket-consolidating a large module is the most reliable way to blow the context window and get a shallow pass through the middle. The target-set selection strategy must be defined before the procedure, and the existing knowledge graph is the natural instrument for it. This determines whether the skills are usable or merely elegant.
- **Recommended sequencing:** ship the rules first and build nothing else for roughly two weeks. Rules are the highest value-to-cost intervention and they are *diagnostic* — after two weeks of observation it becomes clear which of the two skills is actually needed and which was imagined for symmetry. Expected outcome (a prediction, worth less than the observation): rules absorb most of the problem on new documents, and the skill actually needed is the comment one, where pre-existing debt is largest and rules do not reach retroactively.

---

## Deliverable specifications

### 1. `project-description.txt`

- Plain text, no Markdown syntax, no headings, no bullet characters.
- Target 120–200 words, a single tight paragraph or two at most.
- Must state: what the project is for, the failure mode it addresses, the artifact taxonomy in one clause, the rules-vs-skills split, and the expected output types (rules, two skills, procedures, review checklists).
- Written so that a reader who has never seen this conversation understands the project's purpose immediately.
- No preamble, no "This project aims to…" filler — start with substance.

### 2. `project-overview.md`

The exhaustive knowledge document. It must be usable as the single reference that gives any future conversation in the project full context without re-explanation.

Required coverage:

- the workflow in use, and the fact that it is a fixed constraint;
- the environment: Claude Code, plugin-based workflow, knowledge graph, tech stack, codebase scale;
- the observed problem, stated precisely, including why the append behavior is rational rather than defective;
- the root-cause diagnosis (state vs. history conflation);
- the artifact taxonomy, as a table, with lifecycle rules per artifact;
- the settled positions listed above, presented as decisions rather than open questions;
- the rules-vs-skills split with the assignment criterion;
- the two skills, their scope boundaries, their truth sources, their automation levels, and why they are two and not one or five;
- the operations that belong to neither rules nor skills;
- the consolidation procedure, step by step, including the ephemeral-classification rationale;
- correct and incorrect triggers;
- the technical/business asymmetry;
- the critical positions, kept sharp;
- an explicit **open questions** section for what remains genuinely undecided (target-set selection heuristics via the knowledge graph; how to measure whether consolidation is actually reducing context cost; how to detect contradiction across documents rather than within one; where the boundary sits between an aggressively deleted document and lost institutional knowledge).

Constraints:

- Use tables where the content is genuinely tabular; do not force prose into tables.
- Do not pad. Every section must carry information that changes a decision.
- Distinguish clearly and typographically between *settled* and *open*.
- Do not invent facts, metrics, tool names, or file paths not present in this prompt. Where a detail is unknown, mark it as an open question rather than filling it in.

### 3. `project-instructions.md`

Behavioral instructions for Claude inside the project. This is the operative document — it governs how Claude responds, not what Claude knows.

Required content:

- **Role and stance:** senior full-stack engineer, spec-driven development specialist, AI-agent-workflow practitioner. Opinionated. States disagreement directly and explains the reasoning. Does not accommodate a flawed premise for the sake of agreeableness.
- **Standing assumptions:** the workflow is fixed; all documentation work is executed by coding agents; the settled positions in the overview are not to be re-litigated unless new evidence is presented.
- **Response discipline:** answer the question asked before broadening; do not restate the problem back before answering; prefer concrete procedure over principle; when a recommendation has a cost, name the cost.
- **Distinguish rule-shaped from skill-shaped:** whenever a new directive is proposed in conversation, classify it using the mechanical criterion (always-on and zero-cost → rule; rare, multi-phase, loss-prone → skill; mechanical → script or hook) and say so explicitly.
- **Deliverable conventions:** rules must be drafted with their justification attached; skills must specify trigger conditions, scope-selection strategy, and the human-arbitration boundary; procedures must specify what the human reviews and how (diff-based, removed lines first).
- **Anti-patterns to refuse:** proposing a single monolithic consolidation skill; recommending calendar-based triggers; adding per-paragraph verification metadata; adding meta-annotation to code comments; suggesting mid-implementation consolidation; expanding `CLAUDE.md` beyond a compact rule set; proposing anything that requires the human to review a rewritten document rather than a diff.
- **Escalation rule:** when a question touches a business rule whose truth source lies outside the repository, do not resolve it — surface it and ask.
- **Format preferences:** clear and complete explanations; no unnecessary caveats; no filler openings; Markdown headings and tables where they aid scanning; artifacts for anything intended to be saved, kept, or reused.

Constraints:

- Written as instructions addressed to Claude, in the imperative or second person — not as a description of the project.
- Length: substantive but scannable. Prefer tight directive statements over paragraphs of explanation.
- No overlap with `project-overview.md` beyond what is necessary: the overview holds knowledge, the instructions hold behavior.

---

## Global constraints

- All three files must be produced as **separate downloadable artifacts** in a single response.
- Language: English throughout.
- Do not summarize the three documents back at length after producing them; a brief note on what each file is for is sufficient.
- If any part of this prompt appears internally inconsistent or under-specified, state the issue explicitly before producing the artifacts rather than resolving it silently.
- Where you disagree with a position stated above, produce the artifacts as specified **and** add your objection separately in chat. Do not encode your disagreement into the artifacts without flagging it.
