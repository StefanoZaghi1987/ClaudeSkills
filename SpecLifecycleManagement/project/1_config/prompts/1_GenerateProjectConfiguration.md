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

This structure is deliberate and must be preserved. Any recommendation that requires abandoning or restructuring it is out of scope. Interventions graft onto the existing phases; they do not add phases.

### Environment

- Claude Code as the primary coding agent, with a plugin-based workflow (`brainstorm → design spec → implementation plan → sub-agent execution`).
- A codebase knowledge graph built via Tree-sitter plus LLM semantic extraction, used for navigation and orientation, and queryable from the CLI.
- Large, long-lived enterprise codebase; any arbitrary technological stack.
- Significant amounts of accumulated project documentation, in-code comments, specs, implementation plans, and years of revisions and bug-fix history.
- All documentation and specification maintenance work is performed **by coding agents**, not by hand. This is a hard constraint: every recommendation must be executable by an agent and verifiable by a human reading a diff.

**Stack neutrality.** Nothing produced may depend on a specific technological stack. Where this prompt names concrete technologies (.NET, React, TypeScript, SQL, SAP B1, SAP B1 Service Layer, Beckhoff TwinCAT), they are **illustrations of a category** — "an external constraint the code cannot state about itself" — and must be presented as such in the deliverables, never as project facts or as a committed stack.

**Stack neutrality applies to mechanisms, not only to code.** Some interventions below (notably retrieval exclusion) are specified as required **capabilities** with named channels but no named tool, because every concrete implementation of them — ignore files, index configuration, glob patterns, graph exclusion lists — is toolchain-specific. Where a cost claim depends on such a mechanism existing, the deliverables must state that the claim is conditional on the toolchain providing it, rather than asserting the cost as known.

### The observed problem

On a large codebase with heavy documentation history, AI agents asked to change a business rule, a spec, or a comment consistently **append a revision** instead of **editing the existing content**. They add "Revision 3", "Update 2026-07-14", stacked layers of historical notes, and references to old bug fixes.

This has real upside: history is preserved, past problems remain traceable, and context is richer. But it also:

- inflates token consumption and fills the context window;
- injects obsolete and outdated information into the working context;
- produces documents in which multiple statements contradict each other, with no ordering signal telling the agent which one is current;
- makes the eventual consolidation pass increasingly expensive and increasingly risky.

The need is therefore **periodic consolidation**: collapsing accumulated revisions into a single, complete, current, non-contradictory statement of the truth — across project documentation, specs, implementation plans, and in-code comments — without silently losing information that still matters.

### Diagnosis to encode in the project

The append behavior is not a defect; it is a rational response to an incentive. Deleting information requires knowledge the agent does not have (*is this still true? does anything depend on it?*), while appending is always safe — it never loses anything, and the cost it imposes is paid later, by someone else, in a different session. Unless a document explicitly states where history lives, the agent assumes history lives in that document and preserves it.

A practical consequence: instructing agents to "be concise" or "avoid redundancy" does not fix this, because it does not change the incentive. Changing the incentive means telling the agent, in the artifact itself, where history belongs instead.

The root cause is that documents are performing two incompatible functions simultaneously: **describing current state** and **recording history**. These have opposite lifecycles — the first must be rewritten, the second is immutable by definition. Keeping both in the same file guarantees accumulation.

### Artifact taxonomy (the primary intervention)

| Artifact | Function | Lifecycle |
|---|---|---|
| Spec / design doc | **State** | Present tense, describes the system as it is now. No "Revision N" sections. When a business rule changes, the sentence changes. Re-aligned to reality at merge time, not only before implementation. |
| Implementation plan | **Ephemeral** | Has a death date. Marked `status: completed` mechanically at merge; archived later at the author's discretion; **excluded from all retrieval channels** once archived — indexes, globs, knowledge graph, **and inbound references from surviving documents**. |
| ADR | **Append-only log** | One file per decision, immutable, with `status: accepted \| superseded-by ADR-NNN`. All historical rationale that currently pollutes specs belongs here. |
| Code comments | **State** | Explain why the code is the way it is *now*. Never "fix for bug #1234" — that is a commit message, already in git. |

**Reconciliation of merge-time realignment with the separate-commit rule.** "Re-aligned to reality at merge time" and "consolidation is always a separate commit, never mixed with functional changes" are reconciled as follows: the realignment is **a separate commit inside the same pull request** as the functional change. Same PR, distinct commit, independently readable diff. State this resolution explicitly in the deliverables rather than leaving the reader to infer it.

### Positions already settled — treat these as decided, do not re-litigate

- The source of truth about *what the system does* is **the code itself**, not the comments. Comments can lie, and are the only artifact in the repository that can lie without immediate consequence — no test breaks. Comments must therefore be **compacted, not annotated**: they should carry only current truth.
- The operational rule for comments is not "keep comments true" but **"reduce the surface of what can lie."** A comment that restates the code must be **deleted, not compacted** — it adds nothing and can diverge. This category is large in AI-assisted codebases, because models comment generously by default.
- The bright line for "restates the code" is **regenerability**: if the comment could be reconstructed from the signature, the identifiers, and the control flow alone, it is redundant and is deleted. If reconstructing it would require knowing something not present in the file, it is not redundant, however obvious it looks. This test exists because "looks redundant" is exactly where an LLM misjudges — a one-line comment stating an invariant reads like a restatement.
- **Because the regenerability test is the weakest link, the volume it is applied to must be bounded.** The test is fallible in exactly the direction that costs a defect, and the only control on it is a human reading `-` lines. A consolidation commit whose removed-line count exceeds what a reviewer will actually read has no control at all — the diff-based review guarantee is nominal. Comment consolidation therefore carries a **hard cap on removed lines per commit**, splitting into multiple commits rather than exceeding it. The cap is a review-capacity constraint, not a quality metric; its numeric value is to be calibrated by observation and must not be invented in the deliverables.
- Only comments carrying what the code cannot say about itself survive: the reason for a non-obvious choice, an external constraint (illustratively: SAP B1 / Service Layer behavior, a TwinCAT quirk), a rejected alternative and why, an invariant not expressible in the type system. This category must be **defended conservatively** during consolidation. The failure modes are asymmetric: keeping one redundant line costs tokens, deleting one genuine invariant costs a defect.
- Historical bug-fix references in comments are not to be compacted but **relocated** — to a commit message or an ADR.
- **A comment that disagrees with the code is not automatically a stale comment.** The agent can observe divergence; it cannot determine which side is wrong, because it cannot distinguish intended behavior from a defect. Divergence is therefore **escalated as a suspected defect**, never silently resolved by rewriting the comment to match the code. Without this rule, the comment-consolidation skill launders bugs into documentation, and the laundering is invisible in review precisely because the resulting comment is accurate about the code.
- Implementation plans are **archived, not deleted** — but archived plans must be invisible to retrieval. A readable archived plan is worse than a deleted one: it carries the authority of a spec and the content of an intention.
- Plan status marking (`completed`) happens **at merge, immediately**; physical archiving happens **later, at the author's discretion**. These two events are deliberately decoupled. The reason: between merge and archiving, a live plan saying "I will do X" coexists with a spec saying "the system does Y", and if implementation diverged from the plan (it always does), the agent has two sources in conflict and no criterion for preferring one. The status field supplies the criterion at zero cost, independently of when the file physically moves.
- **The archiving script owns the archived-plan inventory.** Once a plan is excluded from the knowledge graph, the graph can no longer be queried to find plans that were archived but never status-marked, or status-marked but never archived. That reconciliation is therefore a responsibility of the archiving script, which maintains its own record of what it moved and when — it is not a knowledge-graph query and must not be specified as one.
- If, at the end of a feature, the plan contains information that would be painful to lose, that information belonged in the spec or in an ADR and never made it there. It is a signal about a missed transfer, not a reason to keep the plan alive. The correct response is to move the content to its proper artifact, then let the plan die on schedule.
- **Default is implicit:** unmarked content is current. Annotating a paragraph as "still true" is noise that ages worse than the content itself — a six-month-old `verified: true` is a false claim wearing a guarantee.
- **No meta-annotation inside code comments, ever.** A comment describing the verification status of another comment is the bottom of the barrel.
- The only persistent marker worth defending is per-document, not per-paragraph: `last-verified-at: <commit-sha>` in the front matter. It costs nothing, ages informatively rather than deceptively (a sha 400 commits behind is a real signal; a stale `verified: true` is a lie), and gives the agent a signal about how much to trust the file. It applies to documents with front matter; code comments have no such carrier, which is consistent with the prohibition above.
- **The sha recorded in `last-verified-at` is the commit the document was verified *against*** — the repository state the agent read while classifying, i.e. `HEAD` at the start of the pass — **not the consolidation commit that writes the field.** Recording the consolidation commit would be circular: its sha does not exist until after the file has been written. This resolution matters because the field's whole value is as a distance measure against the code, and the code state that was actually examined is the parent, not the child.
- **Retrieval exclusion is the primary lever; deletion is the secondary one.** The same mechanism that makes archived plans invisible to retrieval works on any low-value document, at near-zero risk and with no irreversible step. Deletion's marginal gain over exclusion is small; its downside is unrecoverable. Deletion is therefore a **two-phase operation**: exclude from retrieval first, delete later if nothing missed it.
- **Exclusion is only as strong as its weakest channel.** An excluded file remains reachable by direct path from cross-references in surviving documents, and remains findable by a full-text search of the working tree. Phase one is therefore **exclude *and* sever inbound references** — otherwise part of the context cost stays in place and the claim that deletion "buys almost nothing extra" does not hold. Channels to be closed explicitly: retrieval index, glob patterns, knowledge graph, inbound links from documents that remain in play. Reachability by a deliberate full-text search of the tree is accepted as residual and is not a reason to prefer deletion.

### Rules vs. skills — the split to encode

These are not alternatives. **Rules prevent accumulation; skills repair what accumulated anyway.** Rules alone leave the pre-existing debt untouched (they do not apply retroactively); skills alone condemn the project to perpetual maintenance.

The assignment criterion is mechanical: a directive belongs in a **rule** if it must apply *always, at zero activation cost*; it belongs in a **skill** if it is a *rare, multi-phase procedure with risk of information loss*; it belongs in a **script or hook** if a shell command could do it.

**Rules** (`CLAUDE.md`, deliberately kept under ~20 lines for this domain — a 300-line `CLAUDE.md` is no longer a rule set, it is documentation the agent dilutes):

- the artifact taxonomy;
- the no-append rule on specs, **stated with its justification** ("history lives in git and in ADRs") — the justification is what makes the agent willing to overwrite;
- the comment policy: only what the code cannot say about itself; no bug-fix references;
- the implicit default: unmarked = current;
- the obligation to **flag rather than rewrite** anything that is no longer verifiable.

**How the taxonomy fits the line budget.** Four artifacts, five rules and two justifications do not fit in ~20 lines if the taxonomy is reproduced with its lifecycle rules. In `CLAUDE.md` the taxonomy is therefore **one line per artifact, function plus a lifecycle keyword only** (state / ephemeral / append-only / state), with a pointer to the project overview for the lifecycle detail. The full table lives in the overview and is not duplicated in the rule set. Treat the line budget as binding and the taxonomy rule as a compressed index, not as an explanation.

**Scope of the justification requirement.** The line budget does not accommodate a justification on every rule, and attaching one to all five would break the budget. Justifications are attached to the **two rules the agent will otherwise rationalize its way around** — the no-append rule and the comment policy — because both ask the agent to destroy information. The remaining three are declarative and self-enforcing. Do not treat "rules carry their justification" as a universal that conflicts with the line budget; treat it as targeted.

**Skills — exactly two.** The division criterion is *not* the artifact type but **what truth is verified against, and who has the final word**:

1. **Comment consolidation.** Truth source: the code, inside the repository. The agent can decide autonomously on redundancy and on collapsing historical layers — read the function, compare the comment, delete the regenerable, collapse stacked notes, relocate bug-fix references. It may **not** decide autonomously when comment and code disagree; that escalates. High volume, per-file or per-module scope, output verifiable by reading the diff, little human judgment required — **subject to the removed-line cap per commit**, without which "verifiable by reading the diff" is a claim rather than a control.
2. **Spec and design-doc consolidation.** Truth source: the code **plus** business rules that live outside the repository. The agent cannot close the loop alone. It produces the exhaustive classification, rewrites what is verifiable, and hands over a `## To be confirmed` section. Low volume, high risk, human arbitration mandatory.

**Higher automation is not lower risk.** Comment consolidation is the more autonomous skill because its truth source is local, not because its errors are cheaper. Its characteristic failure — a deleted invariant — is the single most expensive outcome in this whole design, and it is invisible in the resulting document by construction. Do not let the automation gradient be read as a risk gradient in the deliverables; the two skills differ in *who arbitrates*, not in *how much a mistake costs*.

Merging these two into one skill costs twice: irrelevant instructions get loaded (half the procedure never applies), and — worse — the trigger description becomes generic, so the skill fires when it shouldn't and fails to fire when it should. Trigger precision is the real design constraint of skills. Fragmenting into five has the opposite problem: overlapping triggers, arbitrary selection, and loss of the ability to reason about what was actually done.

**Shared machinery, not duplicated prose.** Both skills face the same scoping problem, and the strategy for solving it must live in **one place both skills invoke** — a target-set selection script over the knowledge graph — not as two prose scoping sections inside two skill definitions. Two prose copies of the same strategy drift, and the drift is silent. The skills differ in what they do with the target set, not in how they choose it.

**Neither rule nor skill** — these are mechanical operations that must not consume a context load to perform what `sed` would do:

- marking a plan `completed` → a merge-checklist step or a hook;
- archiving plans, excluding them from retrieval, and maintaining the inventory that reconciles status marking with physical archiving → a script plus retrieval configuration;
- excluding low-value documents from retrieval and severing inbound references to them (phase one of deletion) → the same script and configuration;
- target-set selection for both consolidation skills → a single shared script over the knowledge graph, invoked by both;
- **coverage verification of the classification pass** → a script that counts the classifiable units in the pre-consolidation file (paragraphs, or comments) and compares that count against the number of classification entries the agent produced, failing the pass on mismatch;
- **enforcement of the removed-line cap** on a consolidation commit → a script or a pre-commit hook, not agent self-restraint;
- updating `last-verified-at` → a side effect of a skill, not a skill.

### The consolidation procedure

1. **Commit first.** Consolidation is always a separate commit, never mixed with functional changes. The diff must be readable as a semantic diff, which is what makes it reversible. At merge time this means a separate commit within the same pull request. A commit that would exceed the removed-line cap is split, not enlarged.
2. **Scope before classifying.** Run the shared target-set selection script. Blanket scope is the failure mode, not the safe default.
3. **Record the verification baseline.** Capture the sha the pass is being verified against before reading anything. It is what `last-verified-at` will carry, and it makes the pass reproducible.
4. **Classify before rewriting.** Pass 1 labels every paragraph — or every comment — as one of:
   - `still true`
   - `obsolete`
   - `historical decision → ADR`
   - `contradicts code → suspected defect`
   - `not verifiable`

   Only then rewrite. Without this forcing pass, the agent jumps straight to synthesis and that is where loss occurs.
5. **Verify coverage mechanically, do not trust the claim.** Exhaustive classification is self-reported, and the agent that skims the middle of a long document is the same agent that writes the classification of the middle of that document — so a self-reported exhaustive pass can be uniformly plausible and still have a hole. Run the coverage-count script: classifiable units in, classification entries out, counts must match. Without this check the exhaustiveness requirement produces the *appearance* of coverage evidence, which is worse than no evidence because it gets trusted.
6. The classification is **exhaustive but ephemeral relative to the document**: it never enters the persisted document. Its destination is the **body of the consolidation commit message**, which is immutable, outside retrieval, attached to the exact diff it describes, and still available in six months when someone asks what the pass actually looked at. A scratch report (e.g. `consolidation-report.md`, not committed) or chat output is an acceptable fallback where a commit message is impractical, but it discards the coverage evidence immediately after a single use. Rationale for exhaustiveness: if the agent flags only what it believes obsolete, silence becomes ambiguous between "verified, current" and "never examined" — two radically different things the human cannot distinguish. And "never examined" is the common case, because attention over a long document is not uniform: agents work well at the beginning and the end and skim the middle. Exhaustive classification is a forcing function that makes **coverage** visible. The verdict per paragraph matters less than the guarantee that every paragraph was looked at.
7. **Verify against the code, not against the document.** Nothing survives unless it is verifiable in the current code or is a genuine decision, constraint, or rationale. The code is the truth about *what it does*; the unique value of documents is the *why* and what was rejected.
8. **`contradicts code → suspected defect` is never resolved by the agent.** The comment or statement is left in place, unmodified, and the divergence is reported. Rewriting documentation to match code that may itself be wrong is the one failure mode that produces a clean diff and a worse system.
9. **`not verifiable` is the critical bucket.** It is never deleted silently: it goes into a `## To be confirmed` section in the document and escalates to the human. That section legitimately belongs in the persisted document, because it represents open work assigned to a person — not metadata. This is the sole exception to the no-per-paragraph-metadata rule, and it is an exception on those grounds specifically.
10. **Review the removed lines, not the result.** Reading the final document does not reveal what was lost; reading the `-` lines does. This step is the only real control on the regenerability test, which is why the cap in step 1 exists: a diff too large to read is a review that did not happen.

### Triggers

Correct:

- completion of a feature or epic (the plan dies; what it taught flows back into the spec);
- **at the start of brainstorming on an area touched in the past** — this grafts onto the existing workflow and yields clean context before the most token-expensive phase;
- whenever the agent is observed citing obsolete information — the most reliable diagnostic signal.

Wrong: **mid-implementation. Never.**

Calendar-based triggers are inferior to event-based ones. Doing it "by feel every once in a while" is the worst mode, because information loss happens precisely when no checklist is in play.

### The asymmetry that must be explicit

The naïve two-tier version — "technical details the agent decides, business rules it escalates" — is insufficient, because it hands the agent authority over cases where it can see a fact but not interpret it. Encode **three tiers**:

| Tier | Truth source | Agent authority |
|---|---|---|
| **Code-verifiable** | The code, unambiguously | Decides autonomously. Redundant comments deleted, obsolete statements rewritten, stacked layers collapsed. |
| **Code-visible, intent-ambiguous** | The code shows a divergence, but not which side is correct | **Reports, does not resolve.** A comment/spec statement that contradicts the code is a suspected defect, not a stale document. |
| **External truth** | Business rules, regulation, contracts — outside the repository | **Escalates.** No autonomous deletion under any circumstance. |

The middle tier is the one that gets omitted and the one that causes the most expensive failures. Without the top tier's boundary made explicit, the outcome is technically impeccable consolidations that delete a regulatory constraint nobody had implemented yet — a deletion invisible in review precisely because it is technically correct. Without the middle tier, the outcome is documentation quietly rewritten to describe a bug as intended behavior.

### Critical positions to carry into the project — do not soften these

- **The optimization target is upstream, not downstream.** Reducing after the fact costs far more than not accumulating in the first place. If only one thing gets built, it is append-resistant documents by construction. The consolidation skills are maintenance, not the solution.
- **Many documents should not be compacted — they should be removed from play.** A significant share of documentation in an AI-assisted codebase is write-once, read-never: produced because producing it was cheap. The question to ask of every file is "if this disappeared, what would break?" Aggressive removal returns more than accurate compaction, and costs less. Execute it as retrieval exclusion first and deletion second: the context-cost benefit is captured by exclusion **provided every channel is closed, inbound references included** — an excluded file still linked from a live document is still in play, and in that state the benefit has not been captured and the case for deletion is not answered.
- **The enemy is not length, it is contradiction.** A long, coherent, true document costs tokens. A short one with three conflicting statements costs correctness — and hours spent working out why the agent implemented the wrong rule. Optimize non-contradiction first, brevity second.
- **Both skills are, first and foremost, scoping problems.** The expensive part is not rewriting; it is deciding which files to work on. Blanket-consolidating a large module is the most reliable way to blow the context window and get a shallow pass through the middle. The target-set selection strategy must be defined before the procedure, must live in shared machinery rather than in each skill's prose, and the existing knowledge graph is the natural instrument for it. This determines whether the skills are usable or merely elegant.
- **Every control in this design must be mechanical or it is not a control.** Coverage checks, removed-line caps, plan status marking, retrieval exclusion: each is a place where the agent's self-report is not evidence. Where a script can verify a claim, the script is mandatory and the claim is not accepted on its own. This is the same reasoning that puts the mechanical operations outside rules and skills, applied to verification rather than to execution.
- **Recommended sequencing:** ship the rules first and build nothing else for roughly two weeks. Rules are the highest value-to-cost intervention and they are *diagnostic* — after two weeks of observation it becomes clear which of the two skills is actually needed and which was imagined for symmetry. Expected outcome (a prediction, worth less than the observation): rules absorb most of the problem on new documents, and the skill actually needed is the comment one, where pre-existing debt is largest and rules do not reach retroactively. **Read this as a prediction about demand, not about safety** — the comment skill is the likeliest to be needed first and simultaneously the one whose failure mode is most expensive, which is why the removed-line cap and the conservative reading of the regenerability test ship *with* it rather than after it.
- **Specified is not scheduled.** Both skills are fully specified in the project knowledge document; only the rules are scheduled first. Specifying both is cheap, sharpens the rules by forcing the boundaries to be drawn, and costs nothing as long as neither is built during the observation window. Do not read the sequencing advice as a reason to leave a skill under-specified.

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
- the environment: Claude Code, plugin-based workflow, knowledge graph, codebase scale, and explicit stack neutrality — including the fact that stack neutrality applies to mechanisms as well as to code, and that cost claims resting on a toolchain-specific mechanism are stated as conditional;
- the observed problem, stated precisely, including why the append behavior is rational rather than defective, and why exhortations to concision do not address it;
- the root-cause diagnosis (state vs. history conflation);
- the artifact taxonomy, as a table, with lifecycle rules per artifact, including the reconciliation of merge-time realignment with the separate-commit rule;
- the settled positions listed above, presented as decisions rather than open questions — including the regenerability test for redundant comments, the removed-line cap that bounds its application, the divergence-escalation rule, the retrieval-exclusion-before-deletion sequence with its full channel list, the `last-verified-at` baseline resolution, and the archiving script's ownership of the archived-plan inventory;
- the rules-vs-skills split with the assignment criterion, the targeted scope of the justification requirement against the `CLAUDE.md` line budget, and how the taxonomy is compressed to fit that budget;
- the two skills, their scope boundaries, their truth sources, their automation levels, their shared scoping machinery, why they are two and not one or five, and the explicit statement that the automation gradient is not a risk gradient;
- the operations that belong to neither rules nor skills, including the mechanical verification scripts (coverage count, removed-line cap);
- the consolidation procedure, step by step, including the verification baseline, the mechanical coverage check, the ephemeral-classification rationale, and the commit-message destination;
- correct and incorrect triggers;
- the three-tier verification asymmetry, as a table;
- the critical positions, kept sharp, including the requirement that controls be mechanical rather than self-reported;
- an explicit **open questions** section for what remains genuinely undecided: target-set selection heuristics via the knowledge graph; how to measure whether consolidation is actually reducing context cost; how to detect contradiction across documents rather than within one; where the boundary sits between an aggressively removed document and lost institutional knowledge; what happens to a suspected-defect report once escalated, given that the workflow has no defined intake for it; the numeric calibration of the removed-line cap; how retrieval exclusion is implemented in a given toolchain and therefore what it actually costs; whether severing inbound references is itself safely agent-executable or must be human-reviewed like any other destructive edit; what unit counts as a "classifiable unit" for the coverage check in documents without clean paragraph boundaries.

Constraints:

- Use tables where the content is genuinely tabular; do not force prose into tables.
- Do not pad. Every section must carry information that changes a decision.
- Distinguish clearly and typographically between *settled* and *open*.
- Do not invent facts, metrics, tool names, or file paths not present in this prompt. Where a detail is unknown — including any numeric threshold, such as the removed-line cap — mark it as an open question rather than filling it in.

### 3. `project-instructions.md`

Behavioral instructions for Claude inside the project. This is the operative document — it governs how Claude responds, not what Claude knows.

Required content:

- **Role and stance:** senior full-stack engineer, spec-driven development specialist, AI-agent-workflow practitioner. Opinionated. States disagreement directly and explains the reasoning. Does not accommodate a flawed premise for the sake of agreeableness.
- **Standing assumptions:** the workflow is fixed; all documentation work is executed by coding agents; the settled positions in the overview are not to be re-litigated unless new evidence is presented.
- **Response discipline:** answer the question asked before broadening; do not restate the problem back before answering; prefer concrete procedure over principle; when a recommendation has a cost, name the cost.
- **Distinguish rule-shaped from skill-shaped:** whenever a new directive is proposed in conversation, classify it using the mechanical criterion (always-on and zero-cost → rule; rare, multi-phase, loss-prone → skill; mechanical → script or hook) and say so explicitly.
- **Apply the three-tier asymmetry by default:** before endorsing any autonomous agent action on a document or comment, state which tier it falls in. Anything in the middle or outer tier is reported or escalated, not resolved.
- **Demand a mechanical check for every claim of coverage or restraint:** when a proposal relies on the agent having examined everything, or having removed only what was safe, ask what script verifies it. Treat an unverifiable self-report as absent evidence, not weak evidence.
- **Deliverable conventions:** rules must be drafted with their justification attached where the rule asks the agent to destroy information; skills must specify trigger conditions, the shared scope-selection strategy they invoke, their volume bound, and the human-arbitration boundary; procedures must specify what the human reviews and how (diff-based, removed lines first) and must keep the reviewable unit within what a human will actually read.
- **Anti-patterns to refuse:** proposing a single monolithic consolidation skill; recommending calendar-based triggers; adding per-paragraph verification metadata; adding meta-annotation to code comments; suggesting mid-implementation consolidation; expanding `CLAUDE.md` beyond a compact rule set; proposing anything that requires the human to review a rewritten document rather than a diff; producing a consolidation diff too large to be reviewed line by line; rewriting a comment or spec statement to match code when the two disagree, instead of reporting a suspected defect; duplicating the scope-selection strategy inside each skill instead of invoking shared machinery; treating a self-reported exhaustive classification as coverage evidence with no mechanical count check; recommending retrieval exclusion that leaves inbound references intact; recommending irreversible deletion where fully-executed retrieval exclusion captures the same benefit; inventing a numeric threshold in place of marking it for calibration.
- **Escalation rule:** when a question touches a business rule whose truth source lies outside the repository, do not resolve it — surface it and ask. Same for an observed divergence between documentation and code.
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
- **This prompt is itself subject to the taxonomy it describes.** It is a state document. Revisions edit it in place; they do not append a "Revision N" section. The record of what changed belongs in the commit message or in chat, never in the body.
