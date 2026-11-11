# Prompt — Generate a Claude Project for Documentation & Spec Lifecycle Management in Spec-Driven Development

## 0. How to read this prompt

This prompt is a **state** document, governed by the taxonomy it specifies. Revisions edit it in place. It carries no revision notes and no references to earlier drafts of itself. Its change history lives in version control and in chat.

- **Settled positions** are numbered `S1`–`S172`. They are decided. Do not re-litigate them.
- **Open questions** are numbered `O1`–`O17`. They are undecided.
- **Identifiers are stable and are never reused or renumbered.** A revision that adds a position gives it the next free number and places it in its thematic section. Numbers therefore need not appear in ascending order, and a gap or a jump is not an omission.
- §19 (deliverable specifications) references these identifiers instead of restating them. Nothing in this prompt is stated twice.
- **Anti-patterns are not enumerated.** An anti-pattern is the negation of a settled position. Refusals are derived from the register.
- Where this prompt, or the conversation around it, names a concrete technology or product, it illustrates a **category** and is never a project fact or a committed stack.
- Precedence among the deliverables: `project-instructions.md` governs behaviour, `project-overview.md` governs knowledge, `project-description.txt` governs neither and introduces nothing absent from the other two.

---

## 1. Role

Act as a full-stack software engineer with two decades of experience, specialized in spec-driven development and in the practical use of generative AI coding agents (Claude Code and equivalents) on large, long-lived production codebases. You have direct experience with the failure modes of AI-assisted documentation at scale. You are opinionated and concise. You flag disagreement rather than accommodating a premise you think is wrong.

## 2. Task

Produce **three separate downloadable artifacts** in one response. Do not deliver a single combined document, and do not deliver the content inline in chat only.

| File | Format | Destination |
|---|---|---|
| `project-description.txt` | plain text | the Claude Project description field |
| `project-overview.md` | Markdown | the project's primary knowledge document |
| `project-instructions.md` | Markdown | the project's custom instructions field |

All three are written in **English**.

---

## 3. Environment and preconditions

**Environment.** Claude Code as primary coding agent, with a plugin-based workflow (`brainstorm → design spec → implementation plan → sub-agent execution`). A codebase knowledge graph built via Tree-sitter plus LLM semantic extraction, used for navigation and orientation, queryable from the CLI. A large, long-lived enterprise codebase on an arbitrary stack. Significant accumulated documentation, in-code comments, specs, implementation plans, and years of revision and bug-fix history.

### Preconditions

Three environment properties are **preconditions of this design**, not stack-neutral mechanisms.

| # | Precondition | Must provide | Consequence of absence |
|---|---|---|---|
| **S1** | Version control | Commit-level diffs, immutable commit identifiers resolvable after the fact, a review construct that groups commits | Nothing in the design works. Commits, commit messages, pull requests, stashing, merge strategies and diffs are load-bearing throughout. |
| **S2** | Codebase knowledge graph | Queryable, rebuildable, with an **observable build state** | The declared-scope cross-check loses its only non-agent-authored floor; declared scope degrades to self-report. The design still functions; one control does not. |
| **S3** | Two people able to review a consolidation diff | An author and a reviewer who are not the same person | Inbound-reference severance is unavailable, because self-review of one's own deletions is the self-report failure this design refuses everywhere. Phase-one exclusion then reduces to its configuration half **only where `S161`'s first case holds**, with a correspondingly lower first-shipment return; where it does not hold, phase-one exclusion is unavailable outright. |

`S3` is the one most likely to be silently assumed. The design's highest return-per-unit-risk item requires two humans. A single-maintainer project cannot execute it as specified.

### Scope of stack neutrality

- **S4** — Neutrality is bounded by `S1`–`S3` and by nothing else.
- **S5** — Neutrality applies to **mechanisms, not only to code**. Retrieval exclusion, review-unit identification, gate-readability of the classification record, post-merge sha resolvability and full-text search scoping are specified as required **capabilities** with named channels and no named tool, because every concrete implementation is toolchain-specific. Where a cost claim or a control depends on such a mechanism, state the claim as **conditional on the toolchain providing it** rather than asserting it as known.
- **S6** — A **stale** non-agent-authored floor **invalidates** the control it floors; it does not weaken it. A cross-check against a stale floor is a second self-report with an extra hop. Every check that depends on a floor refuses to pass, rather than passing silently, when the floor's observation state is older than the pass's verification baseline by more than a threshold (`O1`).

---

## 4. Workflow, parallelism, and division of labour

### The workflow (fixed)

1. Brainstorming. 2. Specification. 3. Implementation plan. 4. Implementation, frequently parallelized across sub-agents. 5. Code review, then bug fixing and subsequent modifications.

- **S7** — This structure is a fixed constraint. Interventions graft onto existing phases. They do not add phases, and any recommendation requiring the workflow to be restructured is out of scope.

### Parallelism

- **S8** — **No parallelism within a review unit (structural ground).** The two-part bound accumulates across a review unit; the coverage count is taken against one declared scope at one baseline sha; the classification record carries one header. Two concurrent sub-agents on one review unit produce two baselines, two declared scopes and two independently-passing bound counters over one unit — the evadable-by-arithmetic failure the bound exists to prevent, arriving through concurrency instead of commit splitting.
- **S9** — **No fan-out across distinct review units (capacity ground).** `S8` alone would permit several agents on disjoint units. That is barred separately: every review unit consumes the same single human review budget, and producing units faster than one reviewer absorbs them makes a queue of unreviewed deletions the default state. Oversized passes are **split across review units and sequenced against review capacity**, never fanned out.
- **S10** — **Trigger rate is bounded by the same budget as fan-out.** Ordinary feature throughput produces review units without anyone fanning anything out: two features merging in one week carry two realignments. Where the admissible trigger rate exceeds review capacity, realignments are **deferred out of their host pull requests into a queue of standalone passes sequenced against capacity**. The cost is the partial-realignment cost of `S36`, knowingly incurred. Admitting unreviewed consolidation is not an option.

### Who executes what

- **S11** — All documentation and specification maintenance is **agent-executed and human-verifiable**: every recommendation is executable by an agent and verifiable by a human reading a diff. This is a constraint on *how work is specified*, not a claim that no human performs a step. During the first shipment the human-executed set is temporarily larger than the table below, per `S168`.

**Human-executed steps inside a consolidation pass.** This table is not an enumeration of every human act in the design.

| # | Step | Status | Why not agent-executable |
|---|---|---|---|
| **S12** | Arbitration of `## To be confirmed` items — the **ruling**, not its application | Permanent | The truth source lies outside the repository. |
| **S13** | Review of removed lines plus the entry spot-check | Permanent | It is the only control on the regenerability test. An agent reviewing its own deletions is the self-report failure this design refuses everywhere. |
| **S14** | Severance of inbound references | First shipment only | Whether it is safely agent-executable is `O15`. Its review is permanently human and permanently non-authorial. |

`S12` and `S13` are not exceptions to `S11`; they are the verification half of it. Only `S14` is a scoping concession, and it is temporary.

- **S15** — **Two human acts sit outside any pass** and are not carve-outs from `S11`: (a) **observing an agent citing obsolete information** and recording it in the escalation intake, which happens in session, mid-implementation, and is an observation rather than a step of a pass; (b) **deciding phase two of an exclusion**, where a miss signal has been defined.
- **S16** — **Arbitration produces a ruling; a later agent-executed pass applies it.** The person records the ruling and its **ruling sha** in the intake and sets the entry's state to `ruled`. They do not perform the resulting edit. The edit — a sentence into the body, a relocation to an ADR, or a deletion — is performed by a subsequent agent-executed pass carrying its own record, baseline, coverage check and bound. The intake entry, cited in the classification entry, is that pass's **non-agent-authored authority** for the removal.
- **S168** — **The first shipment's human-executed set is larger than `S12`–`S14`, and its passes are reviewed non-authorially.** `S156` places hand-run content passes in the first shipment, so during it a human authors removals as well as reviewing them. Self-review of one's own deletions is precisely the failure `S13` exists to prevent. A hand-run pass is therefore reviewed by someone other than its author, or deferred until one is available — the same rule `S106` imposes on severance, and a second claim on the second person of `S3`.

---

## 5. The problem and its diagnosis

**Observed.** On a large codebase with heavy documentation history, agents asked to change a business rule, a spec or a comment **append a revision** instead of **editing the existing content**: "Revision 3", "Update 2026-07-14", stacked historical notes, references to old bug fixes. The upside is real — history is preserved and context is richer. The costs are token inflation, a context window filled with obsolete information, documents whose statements contradict each other with no ordering signal telling the agent which is current, and a consolidation pass that grows more expensive and more risky the longer it is deferred.

- **S17** — **The append behaviour is a rational response to an incentive, not a defect.** Deleting requires knowledge the agent lacks (*is this still true? does anything depend on it?*). Appending is always safe: it loses nothing, and its cost is paid later, by someone else, in another session. Unless an artifact states where history lives, the agent assumes history lives there and preserves it.
- **S18** — **Instructing agents to "be concise" or "avoid redundancy" does not work**, because it does not change the incentive. Changing the incentive means telling the agent, in the artifact itself, where history belongs instead.
- **S19** — **Root cause: documents perform two incompatible functions at once** — describing current state and recording history. Their lifecycles are opposite: the first must be rewritten, the second is immutable by definition. Keeping both in one file guarantees accumulation.
- **S20** — **The enemy is contradiction, not length.** A long, coherent, true document costs tokens. A short one with three conflicting statements costs correctness. Optimize non-contradiction first, brevity second.

The need is therefore **periodic consolidation**: collapsing accumulated revisions into a single, complete, current, non-contradictory statement of the truth — across documentation, specs, implementation plans and in-code comments — without silently losing information that still matters.

---

## 6. Units of account

Fix these terms before anything else. The design is unreadable if they are conflated.

### Pass kinds

- **S21** — There are exactly three pass kinds, always named by keyword: `document`, `comment`, `severance`. "A `document` pass" is a pass kind. "A pass on a document" is not a term. `document` and `comment` are **content passes**.

### The review unit

- **S22** — A **review unit** is everything a single human review pass is expected to read *as consolidation*: in the merge-time case, the set of consolidation-class commits within one pull request; in the brainstorming-time case, the standalone commit or commit set constituting one pass. Commits subdivide a review unit for readability. They do not create additional review capacity. Because bounds are enforced against it, a review unit carries an identity a script can read, declared in the record header (`O9`).
- **S23** — A **consolidation-class commit** is any commit in the review unit that the design attributes to the pass: the realignment commit, the severance commit, the record commit where the committed-record channel is used, and the mechanical commit of `S90`. Neither the functional commit nor a mechanical status-marking commit (`S172`) is consolidation-class, and neither is part of the review unit.
- **S24** — **Commit ordering inside a review unit is fixed at both ends**, because the ancestry check is otherwise ambiguous. The declared baseline's child is **the first consolidation-class commit in the unit**. Content-removing commits precede the record commit; the record commit is first only where the unit contains no content-removing commit at all. Where both realignment and severance are present, realignment precedes severance. The constraint governs the record commit of the committed-file channel; the commit-message channel has no record commit and is governed by `S169`.
- **S164** — **No functional commit follows the first consolidation-class commit inside a review unit.** `S91` makes the declared baseline the parent of that first commit, which in the merge-time case is the last functional commit. A functional commit landing afterwards leaves the document realigned to a tree that lacks the later behaviour, while every ancestry check still passes and the diff still reads as correct. Where further functional work proves necessary, the realignment is redone against the new baseline or moved out of the unit under `S10`.
- **S25** — **The review unit is not the whole of what the reviewer reads.** In the merge-time case the same person, in the same sitting, also reads the functional diff. Four consequences:
  - the functional diff's volume is **not** counted against the consolidation bound — they are different judgements, and mixing them would make the cap unreadable;
  - a pull request whose functional diff is itself large **moves its realignment out**, into a standalone pass under `S35`. The threshold for "large" is a calibration input (`O8`);
  - where a realignment rides along, the admissible consolidation volume is the **residual** budget after the functional diff, not the full cap;
  - the residual is defined against the **line** half of the bound only. A functional diff consumes reading attention while emitting none of the removal judgements the judgement cap counts. The control that covers the functional diff's own review judgements is the threshold above, which moves the realignment out entirely. Whether the judgement half should carry a residual is a calibration input (`O8`).

### The declared scope

- **S26** — The **declared scope** of a pass is the set of classifiable units the pass commits to examining: normally a set of whole files, and, where a single file alone would exceed the bounds of a review unit, an explicitly enumerated subset of one file. It is stated in the record header and is what the coverage check counts against. **Coverage is a claim about the declared scope, never about the file system.**
- **S27** — **Outputs of a pass are not members of its declared scope.** Three things are outputs: an ADR written or extended by a relocation, items added to a `## To be confirmed` section, and the classification record itself. None is classified or counted for coverage, because each is a **product** of the pass rather than something it examined — not because none exists at the baseline, which is false for a pre-existing ADR and for a pre-existing `## To be confirmed` section. Items already present in such a section at the baseline are in scope and are classified per `S65`; only the items this pass adds are outputs. Output added lines fall under `S69`.

### The classifiable unit

- **S28** — The **classifiable unit** is the smallest thing a classification entry refers to. It has no global definition, because document structures differ and source files differ from prose. It is fixed **per pass** by the unit rule declared in the record header.
- **S29** — **The unit rule is drawn from a closed, machine-evaluable enumeration, not written freely.** The coverage check counts units according to the declared rule, and a script can only count under a rule it can evaluate. The toolchain publishes a closed enumeration of supported unit rules, each with a counting implementation; a pass declares one by name. Illustrations of the category: a Markdown block-level element, a comment block, a single comment line, a numbered list item.
- **S30** — **The enumeration must contain at least one rule for every pass kind.** A `severance` pass's unit rule is "one inbound reference occurrence". Without that member and its counting implementation, a `severance` pass cannot declare a rule the gate can evaluate, and its coverage check does not exist. Which further rules the enumeration should contain is `O2`.
- **S31** — **Choosing the rule is a review-budget decision, not a free per-pass preference.** A coarse rule reduces entry count and spot-check surface and freezes more redundancy along with frozen content. A fine rule recovers those deletions and raises entry count, removal-judgement count and spot-check surface. Both sides draw on the single review budget of `S150`.

---

## 7. Artifact taxonomy

| Artifact | Function | Lifecycle |
|---|---|---|
| Spec / design doc | **State** | Present tense, describes the system as it is now. No "Revision N" sections. When a business rule changes, the sentence changes. Re-aligned to reality at merge time, not only before implementation. |
| Implementation plan | **Ephemeral** | Has a death date. Marked completed mechanically at merge; archived later at the author's discretion; **excluded from all retrieval channels** once archived. |
| ADR | **Append-only log** | One file per decision. **The body is immutable; the status field is the single mutable field** — accepted, or superseded by a named ADR. All historical rationale currently polluting specs belongs here. |
| Code comments | **State** | Explain why the code is the way it is *now*. Never a bug-ticket reference — that is a commit message, already in version control. |

- **S32** — **ADR immutability carve-out.** The body — decision, context, rationale, consequences — is never edited. The status field is the one line a supersession rewrites, and that rewrite is a mechanical operation, not a consolidation.
- **S33** — **Mechanical status marking is exempt from the separate-commit rule, for plans and ADRs alike.** Marking a plan completed and rewriting an ADR's status remove nothing, require no judgement, and produce one-line diffs. The isolation rule governs edits that **remove content on the strength of a judgement**; mechanical status marking is neither.
- **S172** — **A mechanical status-marking commit is not consolidation-class and sits outside the review unit.** It rewrites one line, which is a removal in the diff and a removal in no classifiable unit, so leaving it inside the unit would fail the removal-authorization check of `S89` on a commit that authorizes nothing and needs no authority. It contributes to neither cap, carries no entry, and does not enter `S24`'s ordering.
- **S34** — **Merge-time realignment is by default a separate commit inside the same pull request** as the functional change. Same PR, distinct commit, independently readable diff. It moves out of the host PR where `S25`, `S36` or `S10` requires it. The invariant that never relaxes is *never mixed with functional changes*.
- **S35** — **Consolidation without a host PR.** A consolidation triggered at the start of brainstorming has no functional change to accompany and no host pull request. It stands alone as its own commit and, where review requires it, its own pull request. The invariant is *never mixed with functional changes*, not *always inside a feature PR*.
- **S36** — **An oversized merge-time realignment is split, and the split has a stated cost.** The portion that fits — measured against the residual of `S25`, not the full cap — rides in the host PR as its own commit. The remainder becomes one or more standalone passes. The cost: the spec is knowingly left **partially realigned** to code that has already merged and, per `S100`, carries **no verification marker** in the interim. Tracking the outstanding remainder is `O13`. Raising the bound and mixing the realignment into the functional commit are not resolutions.

### Plans

- **S37** — Plans are **archived, not deleted** — and archived plans are invisible to retrieval. A readable archived plan is worse than a deleted one: it carries the authority of a spec and the content of an intention.
- **S38** — **Status marking happens at merge, immediately; physical archiving happens later, at the author's discretion.** The decoupling is deliberate. Between merge and archiving, a live plan saying "I will do X" coexists with a spec saying "the system does Y"; where implementation diverged from the plan, the agent has two sources in conflict and no criterion for preferring one. The status field supplies the criterion at zero cost, independently of when the file moves.
- **S39** — **The archiving script owns the archived-plan inventory.** Once a plan is excluded from the knowledge graph, the graph cannot be queried to find plans archived but never status-marked, or status-marked but never archived. That reconciliation is the archiving script's responsibility, against its own record of what it moved and when. It is not a knowledge-graph query and must not be specified as one.
- **S40** — **A plan containing information that would be painful to lose is a signal about a missed transfer**, not a reason to keep the plan alive. That information belonged in the spec or in an ADR. Move it to its proper artifact, then let the plan die on schedule.

---

## 8. Comments, the regenerability test, and dispositions

### Comments

- **S41** — The source of truth about *what the system does* is **the code**, not the comments. Comments are the only artifact in the repository that can lie without immediate consequence: no test breaks.
- **S42** — The operational rule is not "keep comments true" but **"reduce the surface of what can lie."** A comment that restates the code is **deleted, not compacted**. This category is large in AI-assisted codebases, because models comment generously by default.
- **S43** — **The bright line for "restates the code" is regenerability.** If the comment could be reconstructed from the signature, the identifiers and the control flow alone, it is redundant and is deleted. If reconstructing it would require knowing something not present in the file, it is not redundant, however obvious it looks. The test exists because "looks redundant" is exactly where an LLM misjudges: a one-line comment stating an invariant reads like a restatement.
- **S44** — **The test names its reconstructor, and the reconstructor is not the agent.** The standard is fixed: **a competent engineer unfamiliar with this module, reading only this file, with no graph and no search.** Not the agent performing the pass; not a reader with repository-wide context. Unfixed, the test optimizes the repository for the agent and degrades it for the person paged in the middle of the night — and the deletion is invisible in review, because the reviewer also has context.
- **S45** — **The conservative reconstructor compresses the comment skill's expected yield.** Under `S44`, most comments in a codebase with mediocre naming are *not* regenerable, so the deletion authority collapses toward the trivially tautological. This is the correct outcome under `S48`, and it is a prediction about return that the observation window should confirm or falsify.
- **S46** — **The regenerability test is scoped to comments and is not extended to prose.** The reconstructor standard was fixed for a reader of a source file; there is no equivalent for a specification, and inventing one would extend the design's weakest judgement to its highest-value artifact. The removal grounds available to a `document` pass are therefore `ruled → apply`, `obsolete` and `historical decision → ADR` only. Stated cost: **a verbose-but-true spec is not shortened by consolidation.** It is shortened by rewriting the statements that are false, or removed from play by exclusion. Contradiction across documents is none of these grounds and has no consolidation-pass treatment; its detection is deferred to `O5`.
- **S47** — **Every deletion on regenerability grounds records its basis** — which signature, which identifiers, which control-flow structure — **against the standard in `S44`**. This costs one clause per entry and converts the weakest link in the design from an unexaminable judgement into a spot-checkable claim. An entry whose basis amounts to restating the comment is not a basis and fails review.
- **S48** — **Only comments carrying what the code cannot say about itself survive**: the reason for a non-obvious choice, an external constraint, a rejected alternative and why, an invariant not expressible in the type system. This category is **defended conservatively**. The failure modes are asymmetric: keeping one redundant line costs tokens; deleting one genuine invariant costs a defect.
- **S49** — Historical bug-fix references in comments are **relocated**, not compacted — to a commit message or an ADR.
- **S50** — **A comment that disagrees with the code is not automatically a stale comment.** The agent can observe divergence; it cannot determine which side is wrong, because it cannot distinguish intended behaviour from a defect. Divergence is **escalated as a suspected defect**, never resolved by rewriting the comment to match the code. Without this rule, the comment skill launders bugs into documentation, and the laundering is invisible in review precisely because the resulting comment is accurate about the code.
- **S51** — **In a `comment` pass the `not verifiable` bucket has no in-file carrier, and none is invented.** A source file has no front matter and no place for a `## To be confirmed` section; per-comment meta-annotation is prohibited outright. The unit is **left in place, byte-for-byte unmodified**, and the escalation travels entirely through the classification record and the intake. Consequence: an unverifiable comment is invisible to anyone who opens the file. That consequence is `O16`, not something to patch with an annotation.
- **S52** — **Freezing happens at the declared unit, and applies to both frozen dispositions.** A unit labelled `not verifiable` **or** `contradicts code → suspected defect` is preserved whole, including any regenerable lines inside it. The pass does not reach into a frozen unit to compact part of it. A pass needing finer resolution declares a finer unit rule and accepts the higher entry count and larger spot-check surface, which is a claim on the review budget. The freeze resolves in the cheap direction of `S48`: a frozen redundant line costs tokens, while reaching into a frozen unit risks the deletion the label exists to prevent.

### Dispositions

- **S53** — **Exactly one disposition per classifiable unit.** A count of entries against a count of units is meaningful only if the mapping is one-to-one.
- **S54** — The disposition set for content passes has **seven members**, of which **six are available to a `document` pass** and **all seven to a `comment` pass**; `severance` passes use a **disjoint two-member set**.

| Disposition | Applies to | Effect | Judgement cap | Requires |
|---|---|---|---|---|
| `ruled → apply` | content passes | Unit removed; the ruled content, where the ruling directs it, is emitted to the body or to an ADR as an output | **Zero** | The intake entry and its ruling sha |
| `contradicts code → suspected defect` | content passes | Frozen whole, escalated | Zero | Code citation |
| `not verifiable` | content passes | Frozen whole, escalated | Zero | — |
| `historical decision → ADR` | content passes | Relocated | Counts, weight open (`O8`) | — |
| `obsolete` | content passes | Removed | Counts, unit weight | Code citation **or** a verifiable absence claim, bounded by `S165` |
| `regenerable → delete` | `comment` passes only | Removed | Counts, unit weight | Regenerability basis per `S44` |
| `still true` | content passes | Retained | Zero | Code citation |
| `severed` | `severance` passes only | Reference removed | Counts, unit weight | The exclusion-inventory entry for the target |
| `retained` | `severance` passes only | Reference kept | Zero | Reason |

- **S55** — **`ruled → apply` applies to `document` and `comment` passes alike.** Its authority is a recorded human ruling, which is artifact-independent. Without this, a comment a person has already ruled on would have to be forced into `obsolete` — demanding a code citation and consuming judgement-cap weight the ruling should have made free. The disposition always removes the unit; whether it also emits a sentence, an ADR entry or nothing is what the ruling determines, and the emitted lines are outputs under `S27` and `S69`.
- **S56** — **`obsolete` may be evidenced by absence.** Obsolescence is normally established by something no longer being there, and a removed subject has no code location to cite. A verifiable absence claim names an identifier and asserts it does not occur in the baseline tree, which the gate can check.
- **S57** — **`still true` is defined per pass kind, and each definition is disjoint by construction from the removal dispositions available to that kind.** In a `comment` pass it means *verifiable in the current code and not reconstructible under `S44`* — therefore retained; `regenerable → delete` means *verifiable and reconstructible* — therefore removed. Defined loosely in the comment case, every regenerable comment would also satisfy `still true`, and an upward-resolving precedence order would make the delete disposition unreachable. In a `document` pass, where the regenerability test does not apply (`S46`), it means *verifiable in the current code* and nothing more.
- **S165** — **The boundary between `obsolete` and `contradicts code → suspected defect` is whether the statement asserts current behaviour.** Where the subject no longer exists — the absence claim of `S56` — or the statement describes a superseded state, a completed intention or a past revision, it is `obsolete`. Where the subject exists, the statement asserts current behaviour, and the code implements something different, it is a suspected defect, because the agent cannot establish which side is wrong (`S50`). Without this line the precedence order of `S60` makes `obsolete` unreachable for anything the code still touches, since a stale statement about live code always also reads as a contradiction. The line over-reports into the defect channel, consistently with `S62`.
- **S166** — **A disposition definition that makes a lower-precedence disposition unreachable is a defect in the definition, not a question for the precedence order.** `S57` and `S165` are two instances of one requirement: because `S60` resolves upward and first match wins, every member must be defined so that every member below it remains reachable. Any new or amended disposition is checked against this before it is admitted.
- **S58** — **A `severance` pass needs both of its dispositions, or its coverage check is unfalsifiable.** If every entry is a severance, entry count equals occurrence count by construction and the check verifies nothing. `retained` records a decision *not* to sever a particular occurrence, counts for coverage, and shows the reviewer its reason.
- **S59** — **A precedence order is mandatory**, because a unit can genuinely satisfy more than one disposition: a stacked revision note is both obsolete as state and historically meaningful; a contradicting statement may also be unverifiable. Absent a tie-break, the disposition is whichever the agent reached first, the classification is non-reproducible, and the count keeps passing.
- **S60** — **The order runs most-conservative to least, first match wins:**

  `ruled → apply` **>** `contradicts code → suspected defect` **>** `not verifiable` **>** `historical decision → ADR` **>** `obsolete` **>** `regenerable → delete` **>** `still true`

  Members unavailable to the pass kind are skipped, not substituted. Evidence before judgement; freeze before escalate; escalate before relocate; relocate before delete. Every step down the list transfers more authority to the agent, so the tie-break resolves upward. `ruled → apply` heads the list because it transfers **no** authority to the agent. The agent may apply it **only** where an intake entry in state `ruled` exists for that unit; without that evidence the disposition is unavailable and the unit is classified on its merits.
- **S61** — **A unit whose intake entry is in the terminal state `ruled-external` is disposed `not verifiable`, frozen, and not re-escalated.** The terminal state suppresses escalation; it does not change the disposition.
- **S62** — **The precedence order deliberately over-reports into the suspected-defect channel.** A unit both unverifiable and apparently divergent is labelled a suspected defect, even though the agent cannot establish that the statement is wrong rather than merely unconfirmable. This resolves upward, correctly, but routes arbitration requests into the channel with the most expensive consumer. The intake therefore supports **reclassification of an open entry between kinds by its consumer**, updating the existing entry rather than appending a new one.

---

## 9. The `## To be confirmed` section

- **S63** — **The section is excepted on state-versus-open-work grounds, not metadata grounds.** It is not per-paragraph verification metadata and does not touch that prohibition. The rule it excepts is *documents describe current state only*: open work assigned to a person is not current state, and it earns its place in the file because the next reader must see it.
- **S64** — **Open work is resolved by deletion.** A person rules, and the item then becomes a sentence in the body (it was true), moves to an ADR (it was a decision), or disappears (it was neither). It is never re-labelled, never annotated with its resolution, and never kept as a record of having once been uncertain. That record is the intake entry and the commit message.
- **S65** — **A later pass over the same document treats existing items as classifiable units, with a defined disposition in every case.** Unresolved → `not verifiable`, frozen, no intake append where a suppressing entry exists. Entry in `ruled` → `ruled → apply`, removed; its removed lines count against the line cap and it contributes **zero** to the judgement cap, because nobody is being asked to accept the agent's reasoning — only to observe that a person ruled, which the cited ruling sha makes checkable. Entry terminal → `S61`.
- **S66** — **Three intake states, not two, because a true-but-unconfirmable statement would otherwise loop forever.** A person rules an item true; it becomes a sentence in the body; the next pass classifies it `not verifiable` and returns it to the section. Since nothing in the file may record that a ruling was made, suppression lives in the intake: `open`, `ruled`, `ruled-external`. The last is terminal and **suppresses re-escalation of the same unit indefinitely**. Without it, the intake's open set grows monotonically with the amount of legitimate outer-tier content in the repository, and the first evidence about how often that tier fires is dominated by permanent residents.
- **S67** — **Suppression lapses when the content changes, and this is correct.** Because the unit reference is churn-stable by being anchored to content, editing the statement produces a new reference and the suppression no longer matches. A changed statement is a new statement and deserves a fresh ruling. The alternative — anchoring the reference to position — destroys the dedup key.
- **S68** — **A section surviving several passes unresolved is a finding about the intake's consumer**, not a reason to let it grow. The design's one sanctioned in-document carrier is the one place the append pathology can reappear, and it reappears exactly when nobody is consuming the intake.
- **S69** — **The caps govern removals, not additions, and this asymmetry is accepted deliberately.** Items added to a `## To be confirmed` section and lines added to a relocation target are added lines a reviewer must read, and no cap governs them. Accepted on the grounds that each item is open work assigned to a person and that unresolved growth is the diagnostic signal of `S68`. Whether added-line volume needs its own ceiling is `O8`.
- **S70** — **A `severance` pass never writes a `## To be confirmed` section.** Its declared scope is reference occurrences, not document content; it has verified no statement in the file. A reference that turns out to be load-bearing is disposed `retained` with its reason, and the arbitration request travels through the intake alone, as an entry of the load-bearing-reference kind (`S119`).

---

## 10. Bounds, gates, and mechanical checks

### The two-part bound

- **S71** — **Because the regenerability test is the weakest link, the volume it is applied to is bounded.** The test is fallible in exactly the direction that costs a defect, and its only control is a human reading `-` lines. A consolidation whose removed content exceeds what a reviewer will actually read has no control at all.
- **S72** — **The bound has two parts, because two different things exhaust the reviewer.** Reading volume is exhausted by removed lines; judgement volume by the number of independent removal judgements the reviewer must accept. They do not move together: one long removed block is one judgement, while the same number of lines removed as individual one-line comments is as many judgements as there are lines, and a line-only cap treats the two as equivalent. Every consolidation review unit carries **both** caps and may breach neither. Both numeric values are calibrated by observation (`O8`) and are never invented.
- **S73** — **It is a removal-judgement cap, and its countable set is defined once against the disposition table**: `obsolete`, `historical decision → ADR`, `regenerable → delete`, `severed`. It excludes the two frozen dispositions, `still true`, `retained`, and `ruled → apply` — the last because its authority is a recorded human ruling rather than an agent judgement. Defined against the regenerability basis alone, the cap would bind on `comment` passes and go slack on `document` passes, where removals are authorized by `obsolete` and carry no basis at all — leaving judgement volume unbounded in the pass type where a single deleted paragraph costs the most.
- **S74** — **An ADR relocation is counted, and not at a discount.** Verifying it requires reading two diffs — the removal from the source and the addition to the ADR — and judging the transfer faithful. It costs *more* reviewer attention than a plain deletion. Whether it should carry more than unit weight is `O8`.
- **S75** — **Both parts are scoped to the review unit, not the commit, and splitting does not raise them.** A per-commit bound is evadable by arithmetic: several commits each individually satisfying a per-commit cap present their sum to the reviewer. A pass exceeding either part is split across review units — separate PRs, or separate passes on separate days — not across more commits in the same unit and not across concurrent agents. Subdividing into commits within a unit remains encouraged for diff readability and remains subject to the same totals.
- **S76** — **Every consolidation-class commit counts against the totals, including the severance commit.** Severance removes lines from live documents on the strength of a judgement, so it is consolidation for the purposes of the cap. An exemption would let the one mechanism the design calls low-risk carry unbounded deletions.
- **S77** — **The record commit is consolidation-class for identity and contributes zero to both caps.** Where the committed-record channel is used, the record is committed **in its own commit inside the review unit**, never inside a content-removing commit. Otherwise the consolidation diff contains something other than consolidation, and that is the property making it reviewable. It removes nothing and authorizes nothing.
- **S78** — **The bound applies to every consolidation review unit, not only to `comment` passes.** Its justification is review capacity, which is a property of the human, not of the artifact type: a spec consolidation removing a given volume is exactly as unreviewable as a comment consolidation removing the same volume. Whether the *numeric values* should differ by pass kind is `O8`. The bound is a review-capacity constraint, not a quality metric.
- **S79** — **The bound and the spot-check draw on the same budget and are calibrated as one decision.** The review budget of a unit is one quantity with the several claims `S150` enumerates. The numbers are calibrated together or not at all.
- **S80** — **The two halves are gated at different times.** The **judgement half is a pre-rewrite gate**: the removal-authorizing entry count is known at the end of classification and does not depend on the rewrite. The **line half admits a pre-rewrite projection and a post-rewrite measurement**: the summed lines of all removal-authorizing units at the baseline is a computable **upper bound** on removed lines before any file is written. Because it is an upper bound and not the value, exceeding it is a **re-scope decision surfaced to the author**, not an automatic failure; the measured count after the rewrite is the gate.
- **S81** — **On failure of the post-rewrite measurement, the admissible remedies are enumerated in advance**: split the pass across review units and re-run, or discard and re-scope. Raising the cap, redistributing across more commits inside the same unit, and fanning out across agents are not remedies.
- **S82** — **Both halves are re-checked at the review-unit gate, and the pre-rewrite checks do not substitute for that.** A pre-rewrite check reads a record in the author's working tree. It is a cheap local gate whose purpose is to fail before the rewrite is paid for. It is not a control, because its input is visible to nothing but the author. The gate that observes the whole review unit re-checks both halves against the **materialized** record.

### Gates and materialization

- **S83** — **Enforcement runs at a gate that can see the whole review unit.** A pre-commit hook cannot see a pull request, so in the merge-time case it is insufficient by construction: it can only enforce a per-commit total, which is the evadable bound of `S75`. Enforcement runs at whatever gate observes the complete unit — a PR-level check in the merge-time case, a pass-level check reading the review-unit identity from the record header in the standalone case (`O9`).
- **S84** — **A gate can only read committed content, so the record is materialized inside the review unit through one of exactly two channels**: (a) **rendered into a commit message body in a fixed machine-readable format**, which makes that body a parsed contract rather than prose and constrains the format accordingly, with placement fixed by `S169`; or (b) **committed as a file excluded from every retrieval channel**, in its own commit within the unit. Which a toolchain supports is `O10`. That one of them is mandatory is settled: a pass materializing neither has no enforceable bound and no gate-verified coverage, whatever it claims.
- **S169** — **The commit-message channel places the record in the last consolidation-class commit of the unit.** Channel (a) has no record commit, so `S24`'s ordering constraint on the record commit governs channel (b) alone. The record describes the whole unit and must be complete when the gate reads it, so it rides in the message of the unit's final consolidation-class commit. Where a unit would otherwise contain no commit at all, channel (b) is mandatory.
- **S163** — **The review-unit gate runs after materialization and before human review, and its failure blocks the review rather than accompanying it.** A reviewer handed a diff whose coverage, removal-authorization, ancestry or bound checks failed is being asked to substitute attention for a control, which is the substitution this design refuses everywhere. The procedure of §13 therefore carries an explicit step for the gate, placed before the step it authorizes.

### What the gate can and cannot recompute

- **S85** — **Recomputable from the repository and the diff:** the classifiable-unit count within the declared scope at the declared baseline under the declared unit rule; the removed-line count; the baseline's ancestry; the declared scope against a non-narrated target set. For a `severance` pass, the unit count is recomputed by searching the declared scope at baseline for references to the targets the exclusion inventory enumerates.
- **S86** — **Not recomputable:** the removal-judgement count, because it is derived from dispositions the agent wrote. No script can independently determine that a removed paragraph was genuinely `obsolete` rather than mislabelled to keep the count down. Do not claim universal recomputation.
- **S87** — **What floors the non-recomputable half:** the coverage check of `S88`, the removal-authorization check of `S89`, and the human spot-check of `S13`. Residual exposure, stated plainly: a pass can under-count judgements by mislabelling a removal, and the control on that is a reviewer reading `-` lines against the record.
- **S88** — **Coverage check.** A script counts the classifiable units **within the declared scope, as they exist at the verification baseline sha**, under the declared unit rule, and compares that count against the number of classification entries. Counting against the working tree at commit time would be incoherent, because consolidation removes classifiable units. It runs twice: locally before the rewrite as a gate on proceeding, and at the review-unit gate against the materialized record, **recomputing the unit count itself rather than reading a count the record asserts**.
- **S170** — **Coverage requires equality and fails in both directions.** Fewer entries than units in the declared scope is omission, which is the failure the check was built for. More entries than units is duplication, or classification of something outside the declared scope, and destroys the one-to-one mapping `S53` requires. Neither is reported as a warning.
- **S89** — **Removal-authorization coverage is mechanical and is not left to human attention.** Every removed line in every consolidation-class commit must fall within a classifiable unit whose entry carries a removal-authorizing disposition (`ruled → apply`, `historical decision → ADR`, `obsolete`, `regenerable → delete`, `severed`). A removed line with no entry is an unrecorded removal. A removed line inside a unit whose entry is `still true`, `retained` or frozen is a mislabelling. Both fail the gate. Two categories of removed line are outside the check by construction: those in the mechanical commit of `S90` and `S162`, and those in commits outside the review unit (`S23`, `S172`).
- **S90** — **Reflow and renumbering are isolated, or `S89` fails on correct passes.** Deleting a list item renumbers those following it; deleting a paragraph reflows wrapped prose. Those removed lines sit inside units that authorize no removal. A pass therefore does not reflow or renumber content outside removal-authorizing units in the same commit. Where reflow is unavoidable, it goes in its own **mechanical commit** inside the review unit, contributing zero to both caps and exempt from removal authorization. How the gate distinguishes mechanical from content removal in a given toolchain is `O17`.
- **S162** — **Front-matter writes are exempt from removal authorization and travel in the mechanical commit.** Refreshing an existing `last-verified-at` replaces a line, and that removed line sits in no classifiable unit under any unit rule, so `S89` would otherwise fail on every correct whole-document pass that updates a marker. Front matter is outside the classifiable-unit space; its removed lines carry no authorizing entry, contribute zero to both caps, and share the mechanical commit of `S90` and its `O17` conditionality.
- **S91** — **The declared baseline has its own floor.** The gate verifies that the declared baseline **is an ancestor of the unit's consolidation-class commits and is the parent of the first consolidation-class commit in the unit** (per `S24`). In the merge-time case the declared baseline **is** the last functional commit, so the check resolves to: the first consolidation-class commit's parent is that sha. A baseline failing this test invalidates the pass; it is not a warning. `S164` supplies the constraint the check cannot see, because a functional commit landing after the realignment passes ancestry while invalidating the verification.
- **S92** — **The target set the cross-check compares against does not arrive by way of the agent's narration.** The target-set selection script's output — with the floor's provenance and observation state — is either **committed inside the review unit** alongside the record or **re-run by the gate itself** (`O11`). That the compared-against side is non-agent-authored is the entire basis on which the cross-check is credited as a floor.
- **S93** — **The scope cross-check fails in both directions, with enumerated narrowing reasons.** It fails where the declared scope is **broader** than the target set, since blanket scope is the named failure mode and an uncaught expansion is how a pass acquires it. It fails where the declared scope is **narrower** unless the header records one of exactly two reasons: a **bound-driven split**, or a **freshness exclusion** — a target-set member omitted because its `last-verified-at` is close enough to the baseline that re-verifying it would spend review budget for nothing. Without the second reason, the only compliant response to a partly-fresh target set is to declare it all in scope and pay to re-verify, which `S150` forbids.
- **S94** — **The three tiers are a partition of authority, not an independent control on the regenerability test.** Tier assignment is itself a judgement the agent makes before it knows the answer: it cannot know a comment states external truth until it has already decided the comment is not regenerable. A deleted regulatory constraint *is* an outer-tier item misclassified as top-tier. The only controls genuinely independent of that judgement are the two-part bound, the removal-authorization check, and citation plus spot-check.

---

## 11. Markers, exclusion, and deletion

### Markers

- **S95** — **Default is implicit: unmarked content is current.** Annotating a paragraph as "still true" is noise that ages worse than the content itself. An old verification boolean is a false claim wearing a guarantee.
- **S96** — **No meta-annotation inside code comments, ever.** A comment describing the verification status of another comment is the bottom of the barrel.
- **S97** — **The only persistent marker worth defending is per-document:** `last-verified-at`, carrying a commit sha, in the front matter. It costs nothing, ages informatively rather than deceptively, and tells the agent how much to trust the file. A document whose format cannot carry front matter is treated like a source file: no marker, and none invented for it.
- **S98** — **The recorded sha is the commit the document was verified *against*** — the repository state the agent read while classifying, i.e. the verification baseline recorded in §13 step 2 — **not the consolidation commit that writes the field.** Recording the consolidation commit would be circular: its sha does not exist until after the file is written.
- **S99** — **The recorded sha must remain resolvable in the integration branch after merge.** A sha the reader cannot resolve is the same class of lie as a stale verification boolean. In the merge-time case the baseline is a feature-branch commit, which a squash or rebase merge destroys. The field is admissible only where the toolchain and merge strategy guarantee resolvability, or where a mechanical post-merge step maps the recorded sha to a surviving one (`O12`). A dangling sha is not an acceptable outcome; the field is omitted rather than written unresolvable.
- **S100** — **`last-verified-at` is written by exactly one pass kind under exactly one scope condition: a `document` pass whose declared scope is the whole document.** Three exclusions: a **subset** `document` pass does not write it, because that would assert verification of content never examined; a **`comment`** pass never writes it, because a source file has no carrier; a **`severance`** pass never writes it, because its scope is reference occurrences and it edits a spec without verifying a single statement in it. Corollary: a document consolidated across several review units carries no marker until the last completes, and the outstanding remainder is tracked per `O13` — deliberately not by inventing a partial-verification marker.
- **S101** — **Isolation by commit is mandatory whenever the pass realigns a document to a functional change; stashing is admissible only for a standalone pass.** If the functional work is stashed, the captured baseline predates the change the document is being realigned to, so the agent verifies the document against code that does not yet contain the behaviour in question. It is also what `S91` requires, since a stashed change leaves no commit for the baseline to be the parent of. Reserve stashing for a brainstorming-time consolidation with unrelated work in flight, where the captured baseline and the tree the agent reads coincide.

### Exclusion and deletion

- **S102** — **Retrieval exclusion is the primary lever; deletion is the secondary one.** The mechanism that makes archived plans invisible works on any low-value document, at far lower risk and with no unrecoverable step. Deletion is a **two-phase operation**: exclude from retrieval first, delete later if nothing missed it.
- **S103** — **Exclusion is only as strong as its weakest channel, and unrestricted full-text search is a channel, not a residual.** Phase one is **exclude *and* sever inbound references**. The channel list: retrieval index, glob patterns, knowledge graph, inbound links from documents remaining in play, and the scope of any search tool the agent routinely uses. Reachability by a *deliberate* human search of the tree is accepted residual and is not a reason to prefer deletion. Reachability by the agent's routine search tool is a channel that must be closed; where the toolchain cannot scope that tool, the exclusion cost claim is conditional and is stated as such (`O14`).
- **S161** — **Where severance is unavailable, configuration-only exclusion is admissible in exactly one of two toolchain cases.** An unsevered inbound reference from a document still in play is a channel under `S103`, and `S103` makes exclusion only as strong as its weakest channel — so "reduced benefit" has to be earned rather than assumed. Where the toolchain refuses to resolve a reference to an excluded path, the residual is the reference text alone, and configuration-only exclusion is admissible with a benefit stated as conditional (`O14`). Where the toolchain follows the reference and pulls the target back into context, configuration-only exclusion closes nothing and is not exclusion; the target stays in play until severance is available. `S3`'s reduced first-shipment return describes the first case only.
- **S104** — **Exclusion is recoverable, but not costlessly.** Restoring an excluded file is a configuration change. Restoring the severed inbound references is a revert against documents that have themselves been edited since, so recovery cost rises with elapsed time and with the churn of those documents. The property is *no unrecoverable step, with recovery cost rising after the fact* — not *no irreversible step*.
- **S105** — **Phase two has no trigger unless one is defined.** The exclusion inventory is the only enumeration of the candidate set, so phase two is a review of that inventory and nothing else. Absent a defined miss signal, the correct default is **exclusion is permanent and phase two never runs**, which costs a retained file nobody retrieves and forfeits almost nothing, since the benefit was captured in phase one. What constitutes evidence that nothing missed an excluded document is `O6`.
- **S106** — **Severing inbound references is a destructive edit on documents that stay in play, and is governed as one.** It is a separate commit; it counts against the bounds of its review unit; it is reviewed by reading the `-` lines **by someone other than its author**, with deferral rather than self-review where no second reviewer is available. Whether an agent may perform it autonomously is `O15`, and the first shipment is scoped accordingly.
- **S107** — **A `severance` pass carries a classification record, and its floor is the exclusion inventory.** Fixed shape: pass kind `severance`; unit rule "one inbound reference occurrence", declared by name from the closed enumeration; declared scope the set of surviving documents holding references to the excluded target; one entry per occurrence, disposed `severed` or `retained`. The non-agent-authored floor is the inventory's enumeration of inbound references, not the knowledge graph — which cannot see the excluded target — and the header's floor-provenance field records the inventory's observation state.
- **S108** — **A `severance` pass is a pass kind of the document-consolidation skill, not a third skill.** It operates on documents, produces a record, obeys the same procedure, and needs arbitration only where a reference is load-bearing. This is what keeps "exactly two skills" true while giving the pass an owner. Leaving it inside the exclusion script would make it the silent side effect the design forbids it from being.
- **S109** — **Severance of a heavily-referenced target is slow, and that is accepted.** Under `S72` and `S73`, each occurrence is a judgement, so excluding a widely-cited document becomes a multi-unit operation sequenced against review capacity. Whether occurrences of one target within one document should count as a single judgement is `O8`.
- **S110** — **The exclusion machinery has a second, non-destructive use.** It is the mechanism that lets a record be kept in the repository without being kept in the context: committed, versioned, reachable by a human who goes looking, invisible to retrieval. Exclusion is a general lever for separating *retained* from *retrievable*, not solely a disposal step.
- **S171** — **The committed record inherits the exclusion conditionality, and this bears on the channel choice.** A record carries the unit references and regenerability bases of what the pass removed, so an unscoped routine search tool reintroduces into retrieval much of what the pass just removed from it. The committed-file channel's cost claim is therefore conditional on the same capability as `S103` (`O14`); where that capability is absent, the commit-message channel is preferred, because commit messages are outside retrieval by construction.
- **S111** — **A newly committed record has no inbound references to sever.** Where the classification record is materialized as a committed file, the exclusion step is *configuration only*. The pointer in the commit message is not an inbound reference in the relevant sense, because commit messages are outside retrieval by construction.
- **S112** — **The exclusion script owns the exclusion inventory, and the severance step updates it regardless of who performs the severance.** The inventory records what was excluded, **when — with a timestamp and a sha** — which inbound references existed at that moment, and which of them were severed. The inbound-reference enumeration is captured **at exclusion time, before the target leaves the graph and the retrieval index**: afterwards no channel can produce it, and `S107`'s floor would not exist. It is not a knowledge-graph query for the same reason. Because `S14` assigns severance to a human in the first shipment, an inventory written only by the script would be missing the severed-reference set during exactly the phase in which a human does the severing, losing the recovery data of `S104` when it is most likely to be needed. Specify the inventory as an artifact with a mandatory update step attached to the severance itself. Without the timestamps, the retrieval-composition series of `S154` cannot be read against the intervention that changed it.

---

## 12. Division of labour: rules, skills, mechanical operations

- **S113** — **Rules prevent accumulation; skills repair what accumulated anyway.** They are not alternatives. Rules alone leave pre-existing debt untouched, because they do not apply retroactively. Skills alone condemn the project to perpetual maintenance.
- **S114** — **The assignment criterion is mechanical.** A directive belongs in a **rule** if it must apply *always, at zero activation cost*; in a **skill** if it is a *rare, multi-phase procedure with risk of information loss*; in a **script or hook** if a shell command could do it.

### Rules (`CLAUDE.md`)

- **S115** — The rule set is kept compact. A rule set that has grown to the length of a document is no longer a rule set; it is documentation the agent dilutes. Contents: the artifact taxonomy; the no-append rule on specs; the comment policy; the implicit default; the flag-rather-than-rewrite obligation; the location of the escalation intake.
- **S116** — **The taxonomy in `CLAUDE.md` is a compressed index, not an explanation**: one line per artifact, function plus a lifecycle keyword only (state / ephemeral / append-only / state), with a pointer to the overview for lifecycle detail. The full table lives in the overview and is not duplicated. The arithmetic is shown, not asserted:

| Rule-set line | Lines |
|---|---|
| Taxonomy, one line per artifact | 4 |
| No-append rule on specs | 1 |
| — its justification | 1 |
| Comment policy | 1 |
| — its justification | 1 |
| Unmarked = current | 1 |
| Flag rather than rewrite | 1 |
| Escalation intake location | 1 |
| Pointer to the overview for lifecycle detail | 1 |
| **Total** | **12** |

  The line budget is a **design constant fixed by fiat**, not a calibration input, and is the sole numeric threshold the deliverables may state (`S160`). Remaining headroom is deliberate slack, not an invitation.
- **S117** — **Justifications attach to the two rules the agent will otherwise rationalize its way around** — the no-append rule ("history lives in version control and in ADRs") and the comment policy — because both ask the agent to destroy information. The remainder are declarative and self-enforcing. "Rules carry their justification" is targeted, not universal, and does not conflict with the line budget.
- **S118** — **The intake's location is a rule line, and its path is a prerequisite of the first shipment.** The flag-rather-than-rewrite obligation is inert if the agent must guess where the flag goes, and a rule that resolves to a guess resolves differently every session. The intake's path, format and churn-stable reference scheme are decided **before the rules ship**, not alongside them (`O7`).

### The escalation intake

- **S119** — The intake is **a convention plus a location** — a single append-only destination for suspected defects, unverifiable statements, load-bearing references awaiting arbitration, and observed obsolete-citation events. It is not a skill and not a rule; it is a file convention and, at most, a script that appends to it. Required fields:

| Field | Notes |
|---|---|
| What was observed | — |
| Where — the unit reference | **In a form stable under file churn** |
| Originating context | The pass that produced it, or the session in which it was noticed |
| The sha in effect when the observation was made | Exists for every kind; required, not conditional |
| The entry's state | `open` \| `ruled` \| `ruled-external` |
| The ruling sha, for a resolved state | The sha at which the ruling was made, distinct from the observation sha |
| The entry kind | Suspected defect, unverifiable statement, load-bearing reference, or obsolete citation. Reclassifiable **in place** by its consumer |
| Occurrence count and latest-observation sha | **Obsolete-citation kind only** |

- **S120** — **The ruling sha is required for the same reason `last-verified-at` records a sha rather than a boolean.** A terminal `ruled-external` is a durable statement that a person once ruled a unit acceptable. Without a repository state attached it becomes precisely the stale verification boolean this design refuses, relocated out of the file where it is harder to notice. The ruling sha is also what a later `ruled → apply` disposition cites.
- **S121** — **The intake is what gives a `comment` pass memory, and what makes repeated passes idempotent.** Because a frozen comment carries no marker, a later pass re-encounters it, re-judges it, and would re-escalate it. The escalation step therefore **reads before it appends**. Without this, the intake accumulates duplicates proportional to how many times a file has been passed over, and the observation window's first evidence about the outer tier is inflated by re-runs.
- **S122** — **The dedup key is the churn-stable unit reference alone, not the pair of reference and kind.** Keying on the pair breaks against `S62`: if a consumer reclassifies an entry, a later pass observing the same unit under the original kind finds no suppressing entry and appends a duplicate. The append is suppressed where **any** non-suppressed entry exists for that reference, and the script surfaces the existing entry so the pass can request reclassification instead.
- **S123** — **Read-before-append is inert without a churn-stable unit reference.** Structural or positional references — a block index, a comment line number, a heading path — move under consolidation and under every unrelated edit. A key built on a moving reference both fails to suppress genuine duplicates and falsely suppresses new observations about different content. The reference is anchored to content or to a durable identifier (`O7`). The intake is the design's only memory, and an intake whose keys drift has no memory at all.
- **S124** — **The obsolete-citation kind is exempt from suppression and is counted instead.** Suppressing the second observation of the same stale statement destroys the frequency signal the observation window exists to measure. Each further observation increments the count and updates the latest-observation sha. This keeps the no-duplicates discipline and the measurement simultaneously. Reclassification under `S62` preserves the accumulated count; a reclassification that resets it destroys the same signal by another route.
- **S125** — **Admissible states differ by kind.** `ruled-external` is meaningful only for the unverifiable-statement kind, where a person has ruled a statement true but unconfirmable in the repository. A suspected defect resolves to `ruled` — the defect was fixed, or the documentation was corrected on human authority. A load-bearing reference resolves to `ruled`, the ruling determining whether the reference is severed, rewritten to a surviving target, or kept. An obsolete-citation event resolves to `ruled` when a consolidation pass consumes it.
- **S126** — **The intake's shape is settled; only its path, format and reference scheme are open** (`O7`), and those three are prerequisites of the first shipment.

### Skills — exactly two

- **S127** — **The division criterion is what external truth does to the pass.** It is not the artifact type, and it is not that one skill deals in local truth: both skills encounter external truth routinely.

| Skill | Pass kinds | Truth source | External truth is | Autonomy |
|---|---|---|---|---|
| Comment consolidation | `comment` | The code, inside the repository | A **stop condition**: the unit is frozen byte-for-byte, escalated through the intake, and the pass moves on | High per pass; may **not** decide when comment and code disagree (`S50`) |
| Spec and design-doc consolidation | `document`, `severance` | The code **plus** business rules outside the repository | **Work to be arbitrated**: the pass produces the classification, rewrites what is verifiable, and hands over a `## To be confirmed` section | Bounded by a mandatory human-arbitration handover |

- **S128** — **"High-volume" is the wrong word for the comment skill.** Autonomy per pass is not throughput in aggregate. Both skills are bounded by the same single review budget, so neither produces more reviewed consolidation per week than the reviewer absorbs. What differs is that the `comment` pass does not *block* on arbitration. Combined with `S45`, `S52` and `S72`, the comment skill's aggregate return is a measurement question, not a property to assert. State it as: *high autonomy per pass, non-blocking, aggregate return to be measured.*
- **S129** — **Higher automation is not lower risk.** The comment skill is more autonomous because external truth stops it rather than blocking it, not because its errors are cheaper. Its characteristic failure — a deleted invariant — is the single most expensive outcome in this design, and it is invisible in the resulting file by construction.
- **S130** — **Pass completion is merge of the review unit, and requires the handover, not the ruling.** A `document` pass completes when its review unit merges with the `## To be confirmed` section written and the intake entries appended. Arbitration is asynchronous, on its own cadence, and its non-performance surfaces as `S68`. "Blocking" describes the *item*, not the pass. Without this, unresolved items could not persist across passes, which `S65` requires them to do.
- **S131** — **Each skill states its bound, and the bounds are not the same kind of thing.** For comment consolidation the binding constraint is numeric and mechanical: the two-part bound per review unit, enforced at a gate that sees the whole unit. For spec consolidation the binding constraint is the mandatory arbitration handover, with the two-part bound applying on top as a review-capacity ceiling. Each skill definition names its bound and says which kind it is.
- **S132** — **A placeholder cap is not a bound.** A skill shipped before the review-capacity calibration of `S155` has a placeholder where its numeric bound should be. That calibration is therefore a **blocking prerequisite of shipping either skill**, not a parallel activity.
- **S133** — **Shared machinery, not duplicated prose.** Both skills face the same scoping problem, and the strategy lives in **one place both skills invoke** — a target-set selection script over the knowledge graph — not as two prose scoping sections in two skill definitions. The skills differ in what they do with the target set, not in how they choose it.
- **S134** — **Why two and not one or five.** Merging them costs twice: irrelevant instructions get loaded, and the trigger description becomes generic, so the skill fires when it should not and fails to fire when it should. Trigger precision is the real design constraint of skills. Fragmenting into five produces overlapping triggers, arbitrary selection, and loss of the ability to reason about what was actually done.
- **S135** — **Both skills are, first and foremost, scoping problems.** The expensive part is not rewriting; it is deciding which files to work on. The target-set strategy is defined before the procedure, lives in shared machinery, and uses the knowledge graph as its instrument — subject to `S2`, `S6` and `S92`.

### Neither rule nor skill — mechanical operations

None of these may consume a context load to perform what a shell command would do.

| Operation | Mechanism |
|---|---|
| Marking a plan completed; rewriting an ADR status | Merge-checklist step or hook; exempt per `S33`, outside the review unit per `S172` |
| Archiving plans, excluding them from retrieval, maintaining the reconciliation inventory | Script plus retrieval configuration (`S39`) |
| Excluding low-value documents (phase one), maintaining the timestamped exclusion inventory with its inbound-reference enumeration | Same script and configuration; captured at exclusion time and updated by the severance step per `S112` |
| Target-set selection for both skills | One shared script over the knowledge graph, recording the floor's provenance and observation state alongside its output, per `S92` |
| Coverage verification | Per `S88`, `S170` |
| Removal-authorization coverage | Per `S89` |
| Cross-checking declared scope, baseline, and floor freshness | Per `S6`, `S91`, `S93` |
| Enforcement of the two-part bound | Per `S80`, `S82`, `S83`, `S163` |
| Appending to the escalation intake | Script invoked by either skill, per `S121`–`S125`; never a hand-written note in chat |
| Updating `last-verified-at` | A side effect of a skill, not a skill; only per `S100`, `S99` and `S162` |
| Capturing the observation window's baseline measurement | Script plus, where retrieval channels are not introspectable, a defined manual sampling procedure (`O3`); shipped with the rules and executed **before the first exclusion** |

### The classification record

- **S136** — **The classification is written, during the pass, to a structured record at a conventional path in a fixed line-oriented or key-value format**, one entry per classifiable unit. That record is the coverage script's input, the source from which the gate-readable form is materialized, and the thing the human reads alongside the diff. Its path and format are `O10`. A coverage check specified against an input that does not exist is not a check.
- **S137** — **The header declares six things, each of which a check would be undefined without.**

| Header field | The check that depends on it |
|---|---|
| Pass kind (`document` \| `comment` \| `severance`) | Which floor, which disposition set, and which cap values apply |
| Review-unit identity | The bound cannot accumulate across a unit it cannot delimit |
| Unit rule, named from the closed enumeration | The coverage count cannot count units without an evaluable rule |
| Declared scope, with a narrowing reason where narrower than the target set | Coverage would fail by construction on every split pass; narrowing could not be distinguished from evasion |
| Verification baseline sha | The count would be taken against the wrong tree; the ancestry check would have nothing to floor |
| Floor provenance and its observation state | The scope cross-check cannot know whether its own floor is sound. Instantiated as the graph's build state for `document` and `comment`, the exclusion inventory's state for `severance` |

- **S138** — **Required contents of an entry:** the churn-stable unit reference, the disposition, and the evidence that disposition requires. The evidence is the *Requires* column of `S54`, read together with `S44`, `S56` and `S165`; it is not re-listed here. A bare disposition is producible without reading anything. A citation is not.
- **S139** — **The record is materialized in the review unit; the working-tree copy is transient.** The working-tree copy is not swept into a content-removing commit unless the committed-file channel was chosen deliberately. Where that channel is chosen, the record goes in its own commit, ordered per `S24` — after every content-removing commit, and first only where the unit contains none — contributing zero to both caps. Where the commit-message channel is chosen, placement is per `S169`. Where the toolchain cannot reliably keep a transient file out of a commit, choose the committed-and-excluded channel outright (`O10`). Uncommitted scratch output is not a third channel; it satisfies no gate.

---

## 13. The consolidation procedure

1. **Isolate the working tree.** Consolidation is always a separate commit, never mixed with functional changes: a separate commit within the same pull request in the merge-time case (`S34`), a standalone commit in the brainstorming-time case (`S35`). Bring the tree to a clean state — in the merge-time case by **committing** the functional work, never stashing it (`S101`); in the standalone case by committing or stashing unrelated work in flight. No functional commit follows from here to the end of the unit (`S164`). Where the host PR's functional diff is large, the realignment moves out (`S25`); where it rides along, admissible line volume is the residual.
2. **Record the verification baseline.** Capture the sha the pass is verified against — the tree state after isolation and before anything is read — into the record header. Capturing it before the functional work is committed would record a state the agent never examined; capturing it after classification would record a state including the pass's own writes.
3. **Scope before classifying, and declare the scope.** Run the shared target-set selection script. Blanket scope is the failure mode, not the safe default. Record the declared scope with a narrowing reason where applicable, plus the pass kind, review-unit identity, unit rule and floor provenance (`S137`). Commit the target-set output inside the review unit, or ensure the gate can re-run it (`S92`). Where a single file alone would exceed the bound, the declared scope is an enumerated subset and the pass does not write `last-verified-at` (`S100`).
4. **Classify. Do not rewrite yet.** Assign every classifiable unit in the declared scope, under the declared unit rule, exactly one disposition from the set applicable to the pass kind, applying the precedence order where more than one fits. Write each disposition with its churn-stable unit reference and required evidence into the record as the pass proceeds.
5. **Gate before rewriting.** Run against the record: the coverage count, in both directions (`S88`, `S170`); the bidirectional scope cross-check with its narrowing reason (`S93`); the floor's staleness (`S6`); the baseline ancestry (`S91`); the judgement half of the bound (`S80`); and the **projected** removed-line upper bound, surfaced to the author as a re-scope decision where it exceeds the line cap. Be precise about what this buys: the count check defeats **omission within the declared scope** and nothing else. The cross-check raises the floor under scope plausibility without establishing the scope was *right*. Neither defeats **skimming** — an agent that skims a long document can emit one plausible disposition per unit and pass the count perfectly. Skimming is addressed by the citation requirement in step 4 plus the human spot-check in step 10. A count-only check reported as coverage evidence is worse than no evidence, because it gets trusted.
6. **Rewrite.** Only now. Without the forcing pass in step 4 and the gates in step 5, the agent jumps to synthesis, and that is where loss occurs. Isolate any reflow, renumbering or front-matter write per `S90` and `S162`.
7. **Measure the line half, and treat failure as re-scoping.** The measured count exists only after the rewrite; the projection in step 5 is an upper bound, not a substitute. Remedies are those enumerated in `S81` and no others.
8. **Materialize the record inside the review unit**, through one of the two channels of `S84`, placed per `S169` or `S139`, and kept out of the persisted document. The record is thereby attached to the exact diff it describes, outside retrieval, and still available in six months when someone asks what the pass looked at. **The sole content crossing from the classification into the document is the `not verifiable` bucket**, as the `## To be confirmed` section — items, not the record, and only that bucket.
9. **Run the review-unit gate.** Re-check the coverage count, the removal authorization of every removed line, the baseline ancestry, the scope cross-check and both halves of the bound against the **materialized** record, recomputing rather than reading asserted values (`S82`, `S88`, `S89`, `S163`). A failure here blocks step 10 rather than being reported alongside it.
10. **Review the removed lines, not the result.** Reading the final document does not reveal what was lost; reading the `-` lines does, against the classification record. `S89` mechanizes the crudest form of this — a `-` line with no authorizing entry — but cannot judge whether an authorized removal was correct, which is what the human is for. This step and the entry spot-check together constitute the review budget of the unit, and they are the only real control on the regenerability test.

**Standing rules inside every pass**

- **Verify against the code, not against the document.** Nothing survives unless it is verifiable in the current code or is a genuine decision, constraint or rationale.
- **Exhaustiveness within the declared scope is what makes silence unambiguous.** If the agent flags only what it believes obsolete, silence becomes ambiguous between "verified, current" and "never examined" — two radically different things the human cannot distinguish. "Never examined" is the common case, because attention over a long document is not uniform. The verdict per unit matters less than the guarantee that every unit in scope was looked at.
- **`contradicts code → suspected defect` is never resolved by the agent** (`S50`), the boundary against `obsolete` is `S165`, and the freeze is whole-unit (`S52`).
- **`not verifiable` is never deleted silently** (`S51`, `S65`, `S70`), and escalation is subject to read-before-append against a churn-stable reference.

---

## 14. Triggers

**Correct:**

- completion of a feature or epic — the plan dies, and what it taught flows back into the spec;
- **at the start of brainstorming on an area touched in the past** — this grafts onto the existing workflow and yields clean context before the most token-expensive phase, and is the case where the consolidation commit stands alone;
- whenever the agent is observed citing obsolete information — the most reliable diagnostic signal.

**Wrong: mid-implementation. Never.**

- **S140** — **The obsolete-citation trigger is a signal, not an authorization.** It arrives mid-implementation more often than not, which is precisely where consolidation is prohibited. The observation is **recorded into the intake when it happens** — incrementing the occurrence count where an entry exists (`S124`) — **and consumed at the next admissible boundary**: feature completion, or the next entry into brainstorming on that area.
- **S141** — **Calendar-based triggers are inferior to event-based ones**, and "by feel every once in a while" is the worst mode, because information loss happens precisely when no checklist is in play.
- **S167** — **The trigger list governs content passes; `severance` is triggered by an exclusion.** All three triggers above admit `document` and `comment` passes alike, and which kind runs is determined by the artifact types the target-set selection returns, not by a separate trigger vocabulary. A `severance` pass has one trigger and one only: phase one of an exclusion (`S103`), which is why it is sequenced against review capacity rather than against feature events. **The first shipment's prerequisite set is enumerated here, because §13 and `S107` depend on machinery the sequencing of `S157` does not otherwise schedule.** Before the first hand-run content pass or human severance pass: the intake's path, format and reference scheme (`O7`); the classification record's path, format and materialization channel (`O10`); at least one unit rule, with its counting implementation, for each pass kind the shipment exercises (`S29`, `S30`); the coverage check (`S88`, `S170`), the removal-authorization check (`S89`), the baseline-ancestry check (`S91`) and the gate that reads them (`S83`, `S163`); and, for hand-run content passes, the shared target-set selection script with its floor-provenance output (`S92`). Where any of these is absent, the affected pass runs with a named control missing, and the deliverables say which — they do not describe it as controlled.

---

## 15. The three-tier asymmetry

| Tier | Truth source | Agent authority |
|---|---|---|
| **Code-verifiable** | The code, unambiguously | Decides autonomously. Redundant comments deleted, obsolete statements rewritten, stacked layers collapsed. |
| **Code-visible, intent-ambiguous** | The code shows a divergence, but not which side is correct | **Reports, does not resolve.** A statement contradicting the code is a suspected defect, not a stale document. |
| **External truth** | Business rules, regulation, contracts — outside the repository | **Escalates.** No autonomous deletion under any circumstance. |

- **S142** — The middle tier is the one that gets omitted and the one that causes the most expensive failures. Without the top tier's boundary made explicit, the outcome is technically impeccable consolidations that delete a regulatory constraint nobody had implemented yet. Without the middle tier, the outcome is documentation quietly rewritten to describe a bug as intended behaviour.
- **S143** — **Both lower tiers terminate in the escalation intake.** A tier distinction that does not end in a durable destination is a taxonomy, not a control.
- **S144** — **The outer tier is not the rare case.** Both skills meet it routinely and differ only in what it does to the pass (`S127`).
- **S145** — Present the table with the limitation of `S94` attached.

---

## 16. Controls doctrine

- **S146** — **Every control must be mechanical or it is not a control.** Where a script can verify a claim, the script is mandatory and the claim is not accepted on its own. A control whose input does not exist — a coverage check with nothing to count, an escalation with nowhere to land, a gate check reading a record never materialized — is the same failure in a more flattering shape. So is a control whose parameters are supplied by the party being controlled, unless something not agent-authored floors them; so is a control whose floor is stale; so is a control that compares two numbers the controlled party produced.
- **S147** — **Where a quantity is not mechanically recomputable, say so** (`S86`) **and name what floors it** (`S87`). A design asserting universal recomputation has one unexamined self-report at its centre.
- **S148** — **Mechanical is necessary and not sufficient: a check must also measure the property it is credited with.** Every control states what it verifies **and what it does not**. The count check catches omission and duplication within the declared scope, not skimming. The target-set cross-check raises the floor under scope plausibility without establishing the scope was right, and only where the floor is fresh and did not arrive by narration. The baseline ancestry check floors which tree was counted, says nothing about whether it was read, and cannot see a functional commit landing afterwards — which is why `S164` is stated as a constraint rather than a check. The removal-authorization check catches unrecorded and mislabelled removals and says nothing about whether an authorized removal was correct. The removed-line cap bounds reading volume and the removal-judgement cap bounds judgement volume, neither saying anything about correctness. `last-verified-at` measures distance from the verified state, not the quality of the verification; it is absent rather than approximate after a subset pass, absent for `comment` and `severance` passes entirely, and absent rather than dangling where the sha would not survive merge. The tier table partitions authority and does not validate tier assignment.
- **S149** — **Check ordering is part of a control's specification.** Every check is placed before the step it authorizes, with exactly one exception — the *measured* removed-line count, which cannot exist before the rewrite, and whose pre-rewrite projection reduces but does not eliminate the exception. That exception ships with the enumerated remedies of `S81`, precisely so that the pressure to reconcile the work to the check has a pre-agreed answer.
- **S150** — **Human review capacity is a single budget with several claims on it:** removed lines to read, removal judgements to accept, entries to spot-check, the functional diff sharing the sitting, the unit rule's granularity (`S31`), and the number of review units produced per week (`S9`, `S10`). Any proposal that tightens one by loosening another has not improved the design. **The severance reviewer's non-authorship is a claim on a second person's budget**, as is the non-authorial review of a hand-run pass (`S168`), which is why `S3` is stated as a precondition.

### Optimization priorities

- **S151** — **The optimization target is upstream, not downstream.** Reducing after the fact costs far more than not accumulating. If only one thing gets built, it is append-resistant documents by construction. The consolidation skills are maintenance, not the solution.
- **S152** — **Many documents should not be compacted; they should be removed from play.** A significant share of documentation in an AI-assisted codebase is write-once, read-never. Ask of every file: "if this disappeared, what would break?" Aggressive removal returns more than accurate compaction and costs less. Execute it as retrieval exclusion first and deletion second; the context-cost benefit is captured by exclusion **provided every channel of `S103` is closed**, and provided `S161` admits the case at hand.
- **S153** — **The return on comment consolidation is bounded in a way the return on document exclusion is not.** Excluding a document removes it from retrieval entirely. Comments are only ever read as part of a file the agent was going to read anyway, so consolidating them shortens files already in scope rather than removing anything from scope. The saving is real but second-order, while the characteristic failure — a deleted invariant — is first-order. Three further compressions apply to comment passes specifically: `S45`, `S48` and `S52`. The parallel limit on `document` passes is `S46`. Confirm the demand *and* the yield by measurement.

---

## 17. Measurement and sequencing

- **S154** — **The observation window is instrumented before it opens, and the instrumentation is not confounded by the intervention it is meant to prioritize.**
  - **Unconditional capture:** intake entry counts by kind and state, plus obsolete-citation occurrence counts. Implementable the day the rules ship.
  - **Conditional capture:** the composition of retrieved context per session by artifact type, dependent on the retrieval channels being introspectable. Where they are not, a **defined manual sampling procedure** is the fallback, and the comment-versus-exclusion priority is calibrated from a sample rather than a census — not silently dropped while the claim is kept (`O3`).
  - **Capture precedes intervention.** Exclusion ships in the first shipment, so applying it during the window changes retrieval composition as the window runs. The baseline is captured **before the first document is excluded**, and every exclusion is timestamped in the inventory (`S112`) so the composition series can be read against the intervention. Shipping the machinery is not the same as running it. Without this, the window measures the intervention and calls the result a baseline.
  - **The window is defined in events, not weeks.** The design's triggers are event-based, and a calendar window may contain no admissible trigger at all. The window is a number of admissible trigger events — feature completions and brainstorming entries on previously-touched areas — with calendar time as a floor rather than the definition (`O3`).
- **S155** — **None of that calibrates the review budget.** Intake counts and retrieval composition say nothing about how many removed lines a reviewer reads before quality falls off. The review-budget numbers require their own exercise: a small number of deliberately measured review passes over consolidation-shaped diffs, recording volume, time and defects caught (`O8`). It is a **blocking prerequisite of shipping either skill** (`S132`), and the observation window does not produce it.
- **S156** — **The calibration exercise's diffs come from the first shipment, not from a skill.** The exercise needs consolidation-shaped diffs, and no skill exists to produce them. Its instruments are the first shipment's **human-executed severance passes** (`S14`) and hand-run passes following §13 without a packaged skill, subject to the prerequisite set of `S167` and the non-authorial review of `S168`. Two consequences follow. Those passes are bounded not by a calibrated cap but by a **per-unit volume the reviewer declares in advance and undertakes to read**. And that mechanism is explicitly provisional: a measurement scaffold that does not survive into either skill, where the bound must be a calibrated number enforced at a gate (`S83`). Without this, the first shipment ships a bounded pass kind with no bound, and the calibration blocks on the skills that block on it.
- **S157** — **Recommended sequencing.** Ship the rules first, together with the escalation intake they depend on, the retrieval-exclusion and plan-archiving machinery, the verification machinery of `S167`, and the baseline measurement capture. Build neither skill for the duration of the observation window. Four ordering dependencies are load-bearing:
  - the intake's path, format and reference scheme are decided **before** the rules ship (`S118`, `O7`);
  - the record format, unit rules and verification checks of `S167` are in place **before** the first hand-run or severance pass;
  - the baseline capture runs **before** the first exclusion is applied (`S154`);
  - phase-one exclusion requires severance, so in the first shipment the severance is **performed by a human, reviewed by a different human, and carries its own classification record** (`S14`, `S106`, `S107`). The exclusion benefit therefore accrues at human throughput until `O15` closes, which qualifies the return-per-unit-risk claim without overturning it and makes closing `O15` the highest-value item on the open list. Where no second reviewer exists, the severance half does not ship at all (`S3`).

  The exclusion benefit is additionally conditional on the agent's routine search scope being constrainable (`S103`, `S161`, `O14`); where it is not, the first shipment's headline claim is weaker than stated and the deliverables say so. Rules are the highest value-to-cost intervention and they are *diagnostic*.
- **S158** — **Expected outcome, as a prediction worth less than the observation:** rules absorb most of the problem on new documents; exclusion absorbs much of the remaining context cost; and the skill actually needed is the comment one, where pre-existing debt is largest and rules do not reach retroactively. **Read this as a prediction about demand, not about safety and not about yield.**
- **S159** — **Specified is not scheduled.** Both skills are fully specified in the knowledge document; only the rules, the intake, the mechanical machinery and the measurement capture are scheduled first. Specifying both is cheap and sharpens the rules by forcing the boundaries to be drawn. The sequencing advice is not a reason to leave a skill under-specified.
- **S160** — **Numeric and naming discipline.**
  - **No numeric threshold is invented anywhere in the deliverables**: not either part of the two-part bound, the spot-check sampling rate, the functional-diff threshold, the added-line ceiling, the staleness threshold, or the observation window's event count. Unknown quantities are marked as open questions.
  - **Cardinalities this register fixes are not thresholds and are stated plainly**: three pass kinds, two skills, three intake states, four intake kinds, the disposition counts, the six header fields.
  - **The labels, field names, section headings, state names and disposition names this register fixes are part of the design and are reproduced verbatim.** What may not be invented is any path, format or tool name the register leaves open — which is every one governed by `O7`, `O10` and `O14`.
  - **Illustrative arithmetic used in this register to make an argument is not carried into the deliverables**, in any form, as it would arrive there indistinguishable from a calibrated value.
  - The sole numeric threshold the deliverables may state is the rule-set line budget of `S116`.

---

## 18. Open questions

Genuinely undecided. Each states the narrowing already imposed by the settled register.

1. **`O1`** — Target-set selection heuristics via the knowledge graph; the staleness threshold beyond which a floor no longer floors the scope check; and the metric in which staleness is measured — intervening commits, elapsed time, or both. The threshold applies identically to the graph and to the exclusion inventory (`S6`).
2. **`O2`** — Which further unit rules the closed enumeration should contain beyond the one each pass kind requires, and which is actually good for documents without clean paragraph boundaries. Narrowed by `S29`–`S31`.
3. **`O3`** — The observation window and its instrumentation: how many admissible trigger events constitute the window; how to analyze the baseline measurement into a confirmation or falsification of `S158`; whether the retrieval channels are introspectable enough to measure retrieved-context composition at all; and, where they are not, what the manual sampling fallback looks like. Narrowed by `S154`, which fixes that capture precedes intervention and that the window is counted in events.
4. **`O4`** — Whether exhaustive per-unit classification is the right cost structure at all, or whether a sampled classification with a mechanical count over coarser units would defeat the truncated pass at materially lower cost. Narrowed by the settled position that exhaustiveness within the declared scope is what makes silence unambiguous (§13), so any replacement must preserve that property, and by the requirement that the evidence be measured record-production cost rather than an argument. With `O16`, this is one of only two open questions whose resolution would amend settled positions — here `S53`, `S73`, `S88`, `S170` and the unambiguous-silence property all rest on exhaustiveness — so it is resolved by measurement before either skill's second iteration rather than left open indefinitely.
5. **`O5`** — How to detect contradiction *across* documents rather than within one. Narrowed by the register's per-document, per-pass model: a review unit (`S22`) and a declared scope (`S26`) examine one document at a time, and every disposition (`S54`) classifies a unit against the code or a recorded ruling, never against a statement in another document — so, per `S46`, no consolidation pass as specified detects it. What this question defers is a detection mechanism that crosses that boundary, if one is wanted at all.
6. **`O6`** — Where the boundary sits between an aggressively removed document and lost institutional knowledge; and what constitutes evidence that nothing missed an excluded document. Narrowed by `S105`.
7. **`O7`** — The concrete path, format and churn-stable unit reference scheme of the escalation intake, and what process consumes its suspected-defect, unverifiable-statement and load-bearing-reference entries, given that the workflow has no defined intake phase. Narrowed by `S119`–`S126`, so this is a decision rather than a design, and settled as a prerequisite of the first shipment (`S157`, `S167`).
8. **`O8`** — The joint numeric calibration, as one review budget, of: the removed-line cap; the removal-judgement cap; the spot-check sampling rate; the functional-diff threshold above which a realignment moves out; whether values should differ between `document`, `comment` and `severance` passes; whether `historical decision → ADR` should weigh more than unit weight; whether the judgement half should carry a residual in the merge-time case; whether occurrences of one severance target within one document should count as a single judgement (`S109`); whether added-line volume needs a ceiling of its own (`S69`); and how the budget interacts with several review units in the same week (`S10`) and with the second reviewer (`S3`, `S168`). Also the design of the calibration exercise itself, whose instruments are fixed by `S156` and which blocks shipping either skill.
9. **`O9`** — How the review-unit identity is surfaced to the enforcement gate in a given toolchain, and what gate observes a standalone multi-commit pass.
10. **`O10`** — The path and format of the structured classification record; which of its two materialization channels a given toolchain supports; whether the toolchain can reliably keep the transient working-tree copy out of a commit; and the size threshold at which the committed retrieval-excluded channel beats the commit message body. Narrowed by `S171`, which makes the committed channel conditional on the same capability as `O14`, and settled as a prerequisite of the first shipment (`S167`).
11. **`O11`** — Whether the gate should re-run the target-set selection script or read a committed copy of its output. Narrowed by `S92`.
12. **`O12`** — How the recorded baseline sha is kept resolvable under a squash or rebase merge strategy, and whether the answer is a merge-strategy constraint, a post-merge mapping step, or restricting `last-verified-at` to standalone passes.
13. **`O13`** — How the outstanding remainder of a file consolidated across several review units is tracked, given that `last-verified-at` is withheld until the last completes (`S100`) and that no partial-verification marker is to be invented.
14. **`O14`** — How retrieval exclusion is implemented in a given toolchain; whether the agent's routine search scope is constrainable at all; whether the toolchain resolves references to excluded paths, which is what decides between `S161`'s two cases; and therefore what exclusion actually costs and actually buys.
15. **`O15`** — Whether severing inbound references is safely agent-executable at all. Non-authorial review is settled (`S106`); the first shipment assigns it to a human (`S14`); it carries a classification record either way (`S107`); closing this is what lets the exclusion benefit accrue at machine throughput.
16. **`O16`** — Whether source files need any in-file marker at all. Two sub-questions, one decision: whether an unverifiable comment being invisible in the file it lives in is an acceptable cost or warrants the one narrow carrier this design currently forbids (`S51`); and whether `comment` passes need any persistent verification marker, given that `last-verified-at` has no carrier in a source file (`S100`) and comment debt therefore cannot be prioritized by staleness. The distinction to rule on is whether the prohibition of `S95`–`S96` targets verification-status annotations, which age deceptively, or all in-file markers including open-work markers, which are resolved by deletion and cannot age deceptively. `S63` makes this sharper rather than softer. Further consideration: any such marker is an added line adjacent to a frozen unit, trading the byte-for-byte auditability of the freeze for visibility. With `O4`, this is one of only two open questions whose resolution would amend a settled position.
17. **`O17`** — How the gate distinguishes mechanical from content removal in a given toolchain — reflow, renumbering and front-matter marker writes alike — given that `S90` and `S162` isolate them into a mechanical commit but the distinction must still be machine-recognizable, or the exemption becomes a hole in `S89`.

---

## 19. Deliverable specifications

The register above is the source. **These specifications reference it; they do not restate it.**

### 19.1 `project-description.txt`

- Plain text. No Markdown syntax, no headings, no bullet characters.
- 120–200 words. One tight paragraph, two at most.
- Must state: what the project is for; the failure mode it addresses (`S17`–`S19`); the artifact taxonomy in one clause (§7); the rules-vs-skills split (`S113`); the expected output types — rules, two skills, procedures, mechanical verification scripts, review checklists.
- Comprehensible to a reader who has never seen this prompt.
- No preamble and no "This project aims to…" filler. Start with substance.

### 19.2 `project-overview.md`

The exhaustive knowledge document: the single reference that gives any future conversation in the project full context without re-explanation.

**Coverage rule.** Every settled position `S1`–`S172` is **stated** exactly once, and every open question `O1`–`O17` is stated exactly once. Cross-references between entries are expected and are not restatements. Organize the entries for a reader — grouped by theme, in tables where the content is genuinely tabular — rather than transcribing the register in its numeric order; the identifiers are the contract, the ordering is not.

**Additional requirements.**

- Distinguish *settled* from *open* typographically and unmistakably.
- No position is stated both as settled and as open. Where this prompt narrows an open item without closing it, the narrowing is stated inside the open entry.
- Every control states what it verifies **and what it does not** (`S148`).
- Every claim resting on a toolchain-specific mechanism is stated as conditional (`S5`).
- Observe `S160` in full: no invented numbers, no invented open paths, formats or tool names, no illustrative arithmetic carried over — and the register's fixed vocabulary reproduced verbatim.
- Do not pad. Every section carries information that changes a decision.
- The document is itself a **state** document under §7: no revision notes, no reference to earlier drafts of anything, no narration of what this prompt changed.

### 19.3 `project-instructions.md`

Behavioural instructions addressed to Claude, in the imperative or second person. The operative document: it governs how Claude responds, not what Claude knows. No overlap with `project-overview.md` beyond what is necessary.

**Required content.**

**Role and stance.** Senior full-stack engineer; spec-driven development specialist; AI-agent-workflow practitioner. Opinionated. State disagreement directly and explain the reasoning. Do not accommodate a flawed premise for the sake of agreeableness.

**Rules.** Carry the compact rule set of `S115`–`S118` within the `S116` line budget: the taxonomy as a compressed index, the no-append rule on specs with its justification, the comment policy with its justification, the implicit default, the flag-rather-than-rewrite obligation, the escalation-intake location, and the pointer to the overview. This file is the Project's custom-instructions field — the `CLAUDE.md`-equivalent those rules occupy — so any directive later classified into a rule (`S114`) displaces a line within this same budget.

**Standing assumptions.** The workflow is fixed (`S7`). The three preconditions hold; where one does not, name the control that is lost (`S1`–`S3`, `S6`, `S161`) rather than proceeding as if it held. Consolidation is never parallelized, within or across review units (`S8`–`S10`). Documentation work is agent-executed and human-verifiable (`S11`), with the human-executed steps as enumerated, only severance temporary, and the first shipment's set temporarily larger (`S168`). Settled positions are not re-litigated unless new evidence is presented, where **new evidence means an observation, not a fresh argument**.

**Response discipline.** Answer the question asked before broadening. Do not restate the problem back before answering. Prefer concrete procedure over principle. When a recommendation has a cost, name the cost.

**Classify every proposed directive** using `S114` — always-on and zero-cost → rule; rare, multi-phase, loss-prone → skill; mechanical → script or hook — and say so explicitly. Where it lands in `CLAUDE.md`, say what it displaces from the line budget and show the new arithmetic (`S116`).

**Apply the tier asymmetry by default.** Before endorsing any autonomous agent action on a document or comment, state which tier it falls in. Anything in the middle or outer tier is reported or escalated, not resolved — and name the destination and the entry kind, not merely the fact of escalation (`S119`, `S143`). State also what would reveal a top-tier assignment to have belonged in the outer tier (`S94`).

**Interrogation duties.** Run these before endorsing any proposal. Each is a duty, not a suggestion; the register entry holds the reasoning.

| Ask | Refuse when | Entry |
|---|---|---|
| What script verifies this? What does it read, against which state, and can the checking gate see it? | The input does not exist, or exists only in the author's working tree | `S146`, `S82` |
| Was either side of the comparison produced by the agent? | Both sides are agent-authored. That is a consistency test, not a control | `S146` |
| Is the scope, unit rule, baseline or threshold supplied entirely by the agent? | Nothing non-agent-authored, fresh and un-narrated floors it | `S6`, `S92`, `S93` |
| Can this quantity be recomputed at all? | Recomputation is claimed for an agent-authored quantity. Name its floors instead | `S86`, `S87`, `S147` |
| What does this check *not* verify, and what covers that? | The blind spot is unnamed | `S148` |
| Does the check precede the step it authorizes? What is already written on failure? | It runs after the irreversible step; a computable pre-step projection is omitted; remedies are unenumerated; a failed gate is reported to the reviewer instead of blocking them | `S149`, `S81`, `S163` |
| Which unit is the bound scoped to, and which gate sees the whole of it? | Scoped to something the agent can multiply — commits, agents, review units per week | `S75`, `S83`, `S10` |
| Are reading volume and judgement volume both bounded? | Only one is, and the risk is per-judgement; the cap counts a quantity this pass kind does not produce; a two-diff relocation is counted at a discount or not at all (`S74`); a line-derived residual is applied to the judgement half | `S72`–`S74`, `S25` |
| Does every label the procedure assigns exist in its taxonomy, and does every taxonomy member remain reachable? | A cap's countable set names something no label produces; an exemption has no label to attach to; a definition makes a lower-precedence disposition unreachable | `S53`, `S54`, `S73`, `S166` |
| Which removed lines does this produce that no entry authorizes? | Reflow, renumbering or a front-matter write rides in a content-removing commit, or a mechanical exemption is claimed with no machine-recognizable boundary | `S89`, `S90`, `S162`, `O17` |
| What does this displace from the review budget? | A review obligation is added with nothing named as displaced | `S150` |
| Where does the flag land, under which kind, who consumes it, what stops a duplicate, what lets it stop? | No destination; no kind for the observation being recorded; a dedup key that file churn or a reclassification destroys; no terminal state; blanket suppression of a kind whose frequency is the signal, which is counted instead | `S119`–`S125` |
| What destroys this recorded reference? | It will dangle. Prefer omission | `S99` |
| What is captured, when relative to the first intervention, and is the window in events or weeks? | Capture starts after the intervention it baselines; it depends on an unconfirmed toolchain capability; it measures a quantity other than the one being calibrated | `S154`–`S156` |
| Does this ship a control whose machinery is not yet scheduled? | A pass is described as controlled while a prerequisite of `S167` is absent | `S167`, `S157` |

**Deliverable conventions.** Rules carry their justification where the rule asks the agent to destroy information (`S117`). Skills specify trigger conditions, the shared scope-selection strategy they invoke (`S133`), their bound — stating whether it is a numeric volume bound or a mandatory arbitration handover, and whether its numbers are calibrated or placeholders (`S131`, `S132`) — and the human-arbitration boundary. Procedures specify what the human reviews and how (diff-based, removed lines first, read against the classification record), place each verification before the step it authorizes or declare and justify the exception, and keep the reviewable unit within what a human will actually read and actually adjudicate.

**Refusals are derived, not listed.** Refuse any proposal that negates a settled position, and **name the entry it negates**. Do not maintain a separate anti-pattern list: it duplicates the register, ages independently of it, and is the accumulation pathology this design exists to prevent. Where a proposal negates nothing in the register, engage with it on the merits.

**Escalation rule.** When a question touches a business rule whose truth source lies outside the repository, do not resolve it: surface it and ask. Same for an observed divergence between documentation and code.

**Format preferences.** Clear and complete explanations. No unnecessary caveats. No filler openings. Markdown headings and tables where they aid scanning. Artifacts for anything intended to be saved, kept or reused.

**Length.** Substantive but scannable. Prefer tight directive statements over paragraphs of explanation.

---

## 20. Acceptance checks on the deliverables

Run these before returning the artifacts. Report any that fail rather than silently repairing the register.

1. Each of `S1`–`S172` is **stated** in `project-overview.md`, and none is stated more than once. Being cited by another entry is not a statement of it.
2. Each of `O1`–`O17` is **stated** in `project-overview.md`, in the open-questions section only. Settled entries may cite open identifiers; that is expected and is not a second statement.
3. No position is stated both as settled and as open.
4. No numeric threshold appears anywhere in the three files except the rule-set line budget, whose table sums to its stated total. Cardinalities the register fixes are not thresholds, and no illustrative arithmetic from this prompt has been carried over.
5. No sentence in any deliverable refers to an earlier version of anything — not of this prompt, not of the design, not of a taxonomy or label set.
6. Every control named states its blind spot.
7. Every cost or capability claim resting on a toolchain-specific mechanism is marked conditional.
8. `project-description.txt` contains no Markdown syntax and falls within 120–200 words.
9. `project-instructions.md` contains no enumerated anti-pattern list.
10. No sentence exceeds roughly 50 words. Where an idea needs more, split it.
11. Every identifier cited anywhere in the three files resolves to an entry that exists. No dangling reference, and no reference to an identifier this prompt does not define.
12. Every disposition named in a countable set, an exemption or an authorization list exists in the disposition table, and every disposition in that table is reachable under the precedence order applicable to its pass kind (`S60` for content passes; the `S58` pair for `severance`).

---

## 21. Global constraints

- Produce all three files as **separate downloadable artifacts** in a single response.
- English throughout.
- Do not summarize the three documents back at length. A brief note on what each file is for is sufficient.
- If any part of this prompt appears internally inconsistent or under-specified, state the issue explicitly before producing the artifacts rather than resolving it silently.
- Where you disagree with a position above, produce the artifacts as specified **and** state your objection separately in chat. Do not encode disagreement into the artifacts without flagging it.
