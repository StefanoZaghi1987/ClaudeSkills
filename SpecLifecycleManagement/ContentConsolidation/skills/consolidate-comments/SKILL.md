---
name: consolidate-comments
description: Run a `comment` consolidation pass over in-code comments — classify every comment unit in a declared scope against the code, delete only what a competent stranger to the module could reconstruct from the file alone, freeze and escalate everything else. Use at feature or epic completion, or on entry into brainstorming on a previously-touched area. Never mid-implementation.
---

# `comment` consolidation

Pass kind: `comment`. Truth source: the code, inside the repository. External truth is a **stop condition** — the unit is frozen byte-for-byte, escalated through the intake, and the pass moves on (`S127`).

Reasoning for every cited entry is in `~/.claude/documentation-lifecycle.md`. This file is procedure. It cites; it does not explain.

**Read before running:** the preconditions `S1`–`S3` and the first-shipment prerequisite set `S167` are stated in the companion. Where a prerequisite is absent, this pass runs with a named control missing and says which. It is not described as controlled.

---

## Implementation — the best-effort runner

This skill ships a runner: `scripts/consolidate_comments.py` (stdlib-only Python 3). Invoke any gate as `python "<this skill's directory>/scripts/consolidate_comments.py" <gate>`. Each script the procedure names is a subcommand: `target-set`, `coverage-check`, `scope-cross-check`, `baseline-ancestry-check`, `bound-check`, `removal-authorization-check`, `floor-staleness-check`, `escalate`. Run `… self-test` to verify the install.

Two subcommands carry the procedure's step distinction in a flag. `bound-check --judgement --project-lines` is the step-five projection; `bound-check --measured` is the step-seven measurement against the tree; `bound-check` with no flag is the review-unit gate, enforcing both halves. `baseline-ancestry-check --unit-gate` adds step nine's parenthood clause to the ancestry check.

**Graceful degradation.** The runner is safe by construction — the regenerability test plus a human reading the removed lines is the real control (`S13`) — so it runs whether or not a project has the infrastructure the controlled tier assumes:

| Infrastructure in `.consolidation.json` | Behaviour |
|---|---|
| `knowledge_graph` set | `target-set` runs it for the file set; floor = `graph` |
| absent | `target-set --scope FILES` enumerates comment units from the declared files; floor = `self-report` (the cross-check loses its non-agent-authored floor, per scope selection) |
| caps set | `bound-check` enforces them |
| absent | `bound-check` reports counts against conservative shipped defaults; breach is advisory, never silent |

The controlled tier switches on automatically when configured; until then this is a best-effort, human-supervised pass.

**Slots, resolved by the runner** (each overridable via `<project>/.consolidation.json`; none invented as calibrated truth):

| Slot | Resolved to |
|---|---|
| `TARGET_SET_SCRIPT` | `consolidate_comments.py target-set` (graph if configured, else `--scope`) |
| `RECORD_PATH` / `RECORD_FORMAT` / `RECORD_CHANNEL` | `.consolidation/<short-baseline-sha>.record`, line-oriented key-value, committed file |
| `INTAKE_PATH` | `~/.claude/escalations.md` (already fixed by rule line eleven) |
| `INTAKE_FORMAT` | one dated line: `` - YYYY-MM-DD `path:line` — divergence; disposition `` |
| `INTAKE_REFERENCE_SCHEME` | `path:line` |
| `UNIT_RULE_ENUMERATION` | pragmatic per-language comment syntax — pure comment lines (grouped) and `/* */` blocks; trailing/inline comments and Python docstrings are **not** enumerated and are left untouched (O2 extension). Not the closed enumeration |
| `REVIEW_UNIT_IDENTITY` | the isolation commit's baseline sha |
| `MECHANICAL_REMOVAL_MARK` | commit subject prefix `mechanical:` |
| `CONSOLIDATION_COMMIT_MARK` | commit subject prefix `consolidation:`. With `mechanical:`, this is the pair the gate reads to tell a consolidation-class commit from a functional one, and therefore to delimit the review unit (`O9`) |
| `FLOOR_STALENESS_THRESHOLD` | 7 days (default) |

**Conservative cap defaults** (uncalibrated, `O8`): `REMOVED_LINE_CAP` 200, `REMOVAL_JUDGEMENT_CAP` 30, `SPOT_CHECK_RATE` 0.25, `FUNCTIONAL_DIFF_THRESHOLD` 400, `ADDED_LINE_CEILING` 200.

**Record format** — authored by the agent as it classifies, parsed by the gates:

```
baseline_sha: <sha>
floor: self-report
unit_rule: comment
scope: src/a.py,src/b.py
@@unit
file: src/a.py
lines: 10-12
disposition: regenerable → delete
basis: restates the assignment at line 11
@@unit
file: src/a.py
lines: 20
disposition: escalates (frozen)
basis: external rule, unverifiable from file
```

An optional `narrowing_reason:` header line records why a declared scope is narrower than the target set; `scope-cross-check` requires it when it is, so a silent narrowing is not indistinguishable from evasion (`S93`).

**Config** — `.consolidation.json` (optional, JSON), found by walking up from the working directory to the project root, so a gate invoked from a subdirectory does not silently run on defaults. Any cap key overrides its default; `knowledge_graph` (a command printing file paths) and `intake_path` are also read; an unrecognized key is reported rather than absorbed. Absent file = run on defaults = no graph, no calibrated caps.

---

## Trigger conditions

Admissible, and no others:

| Trigger | Note |
|---|---|
| Completion of a feature or epic | The host pull request case (`S34`) |
| Entry into brainstorming on an area touched in the past | The standalone case (`S35`) |
| An observed obsolete-citation event, **consumed at the next occurrence of either trigger above** | The event is a signal, not an authorization (`S140`) |

**Prohibited: mid-implementation. Never** (`S140`). An obsolete-citation observation made mid-implementation is appended to the intake when it happens and consumed later. It does not start a pass.

Do not fire on: a code review comment thread, a lint or formatting sweep, a rename or refactor, a merge conflict resolution, a dependency bump, or any request phrased as "tidy up the comments in this file while you are in there". The last is mid-implementation wearing a different hat.

Which pass kind runs is determined by the artifact types the target-set selection returns, not by a separate trigger vocabulary (`S167`).

---

## Scope selection

Invoke the shared target-set selection strategy. Do not re-derive it here and do not substitute a private heuristic — both skills use the one strategy and differ only in what they do with the target set (`S133`, `S135`).

- Run the shared script at slot `TARGET_SET_SCRIPT`. It reads the codebase knowledge graph and emits the target set together with the floor's provenance and its observation state (`S92`).
- Blanket scope is the failure mode, not the safe default (`S26`).
- The script's output is committed inside the review unit alongside the record, or the gate re-runs the script itself. Which of the two is `O11`.
- Selection heuristics are `O1`. Until `O1` closes, the strategy has no published heuristic and the target set is whatever the script emits.
- The floor is the knowledge graph, subject to `S2`. Where the graph is absent, the declared-scope cross-check loses its only non-agent-authored floor and declared scope degrades to self-report; say so rather than running the cross-check and reporting a pass.

---

## Bound

**Kind: numeric volume bound.** The binding constraint on this skill is the two-part bound per review unit, enforced at a gate that sees the whole unit (`S131`, `S83`).

| Part | Counts | Value |
|---|---|---|
| Line half | Removed lines across every consolidation-class commit in the review unit | placeholder `REMOVED_LINE_CAP` — **uncalibrated** |
| Judgement half | Entries carrying a disposition in the countable set below | placeholder `REMOVAL_JUDGEMENT_CAP` — **uncalibrated** |

Both parts are scoped to the review unit, not the commit. Splitting across commits does not raise them; splitting across review units is the remedy (`S75`).

**This skill ships as a best-effort, human-supervised runner, not as controlled.** A placeholder cap is not a bound (`S132`); the runner supplies conservative default caps (see *Implementation*) so the pass is runnable, while the calibrated values still require the review-capacity calibration exercise (`S155`, `S156`), whose design is open under `O8`. The controlled tier — graph floor plus calibrated caps — switches on automatically when that infrastructure is configured; until then the pass runs best-effort and says so in the record's floor field.

Also uncalibrated and therefore placeholders: `SPOT_CHECK_RATE` (`O8`), `FUNCTIONAL_DIFF_THRESHOLD` (`S25`, `O8`), `ADDED_LINE_CEILING` (`S69`, `O8`), `FLOOR_STALENESS_THRESHOLD` (`S6`, `O1`), `OBSERVATION_WINDOW_EVENTS` (`S154`, `O3`).

---

## Dispositions

All seven content-pass dispositions are available to a `comment` pass (`S54`). Exactly one per classifiable unit (`S53`).

| Disposition | Effect | Counts against the judgement cap | Evidence required |
|---|---|---|---|
| `ruled → apply` | Unit removed; the ruled content, where the ruling directs it, is emitted to an ADR as an output | No | The intake entry and its ruling sha |
| `contradicts code → suspected defect` | Frozen whole, escalated | No | Code citation |
| `not verifiable` | Frozen whole, escalated | No | — |
| `historical decision → ADR` | Relocated | Yes, unit weight; whether it should weigh more is `O8` | — |
| `obsolete` | Removed | Yes, unit weight | Code citation **or** a verifiable absence claim naming an identifier asserted not to occur in the baseline tree |
| `regenerable → delete` | Removed | Yes, unit weight | Regenerability basis per the standard below |
| `still true` | Retained | No | Code citation |

**Precedence order, most-conservative to least, first match wins** (`S60`):

`ruled → apply` **>** `contradicts code → suspected defect` **>** `not verifiable` **>** `historical decision → ADR` **>** `obsolete` **>** `regenerable → delete` **>** `still true`

Members unavailable to this pass kind are skipped, not substituted. `ruled → apply` is available only where an intake entry in state `ruled` exists for that unit; without that evidence the disposition is unavailable and the unit is classified on its merits (`S60`).

**Countable set for the judgement cap** in a `comment` pass: `obsolete`, `historical decision → ADR`, `regenerable → delete` (`S73`).

### The regenerability test

**Standard, fixed and named:** a competent engineer unfamiliar with this module, reading only this file, with no graph and no search (`S44`). Not the agent performing the pass. Not a reader with repository-wide context.

- If the comment could be reconstructed from the signature, the identifiers and the control flow alone, it is `regenerable → delete` (`S43`).
- If reconstructing it would require knowing something not present in the file, it is not regenerable, however obvious it looks.
- Every deletion on regenerability grounds records its basis in the entry — which signature, which identifiers, which control-flow structure — against that standard (`S47`). An entry whose basis amounts to restating the comment is not a basis and fails review.
- The test is scoped to comments. It is never extended to prose (`S46`).

### `still true` versus `regenerable → delete`

In a `comment` pass, `still true` means verifiable in the current code **and not** reconstructible under the fixed standard. `regenerable → delete` means verifiable **and** reconstructible (`S57`). The two are disjoint by construction, so the upward-resolving precedence order leaves the delete disposition reachable (`S166`).

### `obsolete` versus `contradicts code → suspected defect`

Where the subject no longer exists, or the statement describes a superseded state, a completed intention or a past revision — `obsolete`. Where the subject exists, the statement asserts current behaviour, and the code implements something different — `contradicts code → suspected defect` (`S165`).

**Never resolve a comment-versus-code divergence.** The agent can observe divergence but cannot distinguish intended behaviour from a defect. Rewriting the comment to match the code launders a bug into documentation, and the laundering is invisible in review precisely because the resulting comment is accurate about the code (`S50`).

### Freezing

Freezing happens at the declared unit and applies to both frozen dispositions. A unit labelled `not verifiable` or `contradicts code → suspected defect` is preserved whole, byte-for-byte, including any regenerable lines inside it. Do not reach into a frozen unit to compact part of it. A pass needing finer resolution declares a finer unit rule and accepts the higher entry count and larger spot-check surface (`S52`, `S31`).

### No in-file carrier

A `comment` pass writes **no marker of any kind** into a source file.

- No `## To be confirmed` section: a source file has no carrier for one, and none is invented (`S51`).
- No per-comment meta-annotation, ever (`S96`).
- No `last-verified-at`: a source file has no front matter, so this pass never writes the field (`S97`, `S100`).

The escalation travels entirely through the classification record and the intake. Consequence, accepted and not patched: an unverifiable comment is invisible to anyone who opens the file. Whether that is acceptable is `O16` (`S51`).

---

## Procedure

Each verification precedes the step it authorizes. The single exception is declared at step seven (`S149`).

1. **Isolate the working tree.** Consolidation is a separate commit, never mixed with functional changes: a separate commit within the same pull request in the merge-time case (`S34`), a standalone commit in the brainstorming-time case (`S35`). In the merge-time case bring the tree to a clean state by committing the functional work — never by stashing it (`S101`). Stashing is admissible only for a standalone pass with unrelated work in flight. **No functional commit follows from here to the end of the unit** (`S164`). Where the host pull request's functional diff exceeds `FUNCTIONAL_DIFF_THRESHOLD`, the pass moves out to a standalone review unit; where it rides along, admissible line volume is the residual after the functional diff, and the residual is defined against the line half only (`S25`).

2. **Record the verification baseline.** Capture the sha of the tree after isolation and before anything is read, into the record header field *Verification baseline sha* (`S98`).

3. **Scope before classifying, and declare the scope.** Run `TARGET_SET_SCRIPT`. Write the header: *Pass kind* `comment`; *Review-unit identity* from slot `REVIEW_UNIT_IDENTITY`; *Unit rule*, named from the closed enumeration at slot `UNIT_RULE_ENUMERATION`; *Declared scope*, with a narrowing reason where narrower than the target set; *Verification baseline sha*; *Floor provenance and its observation state*, instantiated as the knowledge graph's build state (`S137`). Commit the target-set output inside the review unit, or ensure the gate can re-run it (`S92`, `O11`).

4. **Classify. Do not rewrite yet.** Assign every classifiable unit in the declared scope, under the declared unit rule, exactly one disposition, applying the precedence order where more than one fits. Write each disposition with its churn-stable unit reference and required evidence into the record as the pass proceeds (`S138`). Exhaustiveness within the declared scope is what makes silence unambiguous: if only suspect units are flagged, silence becomes ambiguous between "verified, current" and "never examined", and the human cannot distinguish them.

5. **Gate before rewriting.** Run the pre-rewrite checks against the record. Each is a script, not an instruction the agent performs by reading.

   | Script | Reads | Against | Fails when |
   |---|---|---|---|
   | `coverage-check` | The record; the declared scope at the baseline sha under the declared unit rule | Recomputed unit count | Entry count differs from unit count in either direction (`S88`, `S170`) |
   | `scope-cross-check` | The record header; the committed target-set output | The target set | Declared scope is broader than the target set, or narrower without one of exactly two recorded reasons: a bound-driven split, or a freshness exclusion (`S93`) |
   | `floor-staleness-check` | The floor's observation state in the header | The verification baseline | The floor is older than the baseline by more than `FLOOR_STALENESS_THRESHOLD`; it refuses to pass rather than passing silently (`S6`) |
   | `baseline-ancestry-check` | The declared baseline | The isolated tree | Pre-rewrite this can only confirm the declared baseline is the tip of the isolated tree, since no consolidation-class commit exists yet (`S91`) |
   | `bound-check --judgement` | The record | `REMOVAL_JUDGEMENT_CAP` | Countable entries exceed the cap. This half is known at the end of classification and does not depend on the rewrite (`S80`) |
   | `bound-check --project-lines` | The record; the baseline tree | `REMOVED_LINE_CAP` | The summed baseline lines of all removal-authorizing units exceed the cap. This is an upper bound, not the value, so exceeding it is a re-scope decision surfaced to the author, not an automatic failure (`S80`) |

   **What this buys, precisely.** The count check defeats omission and duplication within the declared scope and nothing else. The cross-check raises the floor under scope plausibility without establishing that the scope was right. Neither defeats skimming: an agent that skims a long file can emit one plausible disposition per unit and pass the count perfectly. Skimming is addressed by the citation requirement in step four plus the human spot-check in step ten. A count-only check reported as coverage evidence is worse than no evidence, because it gets trusted (`S148`).

   These checks read a record in the author's working tree. They are cheap local gates whose purpose is to fail before the rewrite is paid for. They are **not** controls, because their input is visible to nothing but the author (`S82`).

6. **Rewrite.** Only now. Isolate any reflow or renumbering into its own commit marked `MECHANICAL_REMOVAL_MARK` inside the review unit; it contributes zero to both caps and is exempt from removal authorization (`S90`). How the gate distinguishes mechanical from content removal in a given toolchain is `O17`; the runner reads the mark and exempts a removed line whose content a mechanical commit also removed, reporting the count of exemptions applied. While `O17` is open that content match is the hole in the removal-authorization check, and it is named as one rather than hidden. A `comment` pass writes no front matter, so `S162` does not arise here.

7. **Measure the line half.** Run `bound-check --measured`. The measured removed-line count exists only after the rewrite. This is the single declared exception to check-before-step ordering, and the step-five projection reduces but does not eliminate it (`S149`). Lines removed by a `mechanical:` commit are excluded from the measurement, per the exemption at step six. **Remedies on failure, enumerated in advance and exhaustive:** split the pass across review units and re-run, or discard and re-scope. Raising the cap, redistributing across more commits inside the same unit, and fanning out across agents are not remedies (`S81`).

8. **Materialize the record inside the review unit** through the channel at slot `RECORD_CHANNEL` — either rendered into a commit message body in a fixed machine-readable format, placed in the last consolidation-class commit of the unit (`S169`), or committed as a retrieval-excluded file in its own commit, ordered after every content-removing commit (`S24`, `S139`). One of the two is mandatory: a pass materializing neither has no enforceable bound and no gate-verified coverage, whatever it claims (`S84`). Nothing crosses from the classification into the source file (`S51`).

9. **Run the review-unit gate.** It runs after materialization and before human review, and its failure **blocks** the review rather than accompanying it (`S163`).

   | Script | Recomputes | Fails when |
   |---|---|---|
   | `coverage-check` | The unit count itself, not a count the record asserts | Inequality in either direction (`S88`, `S170`) |
   | `removal-authorization-check` | Every removed line in every consolidation-class commit | A removed line falls in no classifiable unit whose entry carries `ruled → apply`, `historical decision → ADR`, `obsolete` or `regenerable → delete`; or falls inside a unit whose entry is `still true` or frozen (`S89`) |
   | `baseline-ancestry-check --unit-gate` | Whether the declared baseline is an ancestor of the unit's consolidation-class commits and the parent of the first one, read through `CONSOLIDATION_COMMIT_MARK` | Either fails; it is an invalidation, not a warning (`S91`). Ancestry alone is nearly free in a linear history — what the parenthood clause catches is a functional commit sitting between the declared baseline and the consolidation work (`S164`) |
   | `scope-cross-check` | Declared scope against the non-narrated target set | Either direction, per step five (`S93`) |
   | `bound-check` | The judgement half against the materialized record; the line half against the tree | Either half breached (`S82`) |

   The gate must be able to delimit the review unit. How review-unit identity is surfaced to it, and what gate observes a standalone multi-commit pass, is `O9`. Until `O9` closes for the toolchain in use, the bound cannot accumulate across a unit the gate cannot delimit, and the pass is not controlled.

10. **Review the removed lines, not the result.** Human step. Reading the final file does not reveal what was lost; reading the removed lines does, against the classification record.

---

## Record

Written during the pass to a structured record at slot `RECORD_PATH` in the format at slot `RECORD_FORMAT`, one entry per classifiable unit (`S136`). Both are `O10`. A coverage check specified against an input that does not exist is not a check — while `RECORD_PATH` and `RECORD_FORMAT` are unfilled, `coverage-check` has no input and this pass has no coverage control.

**Header — six fields, each of which a check would be undefined without** (`S137`):

| Field | Value in a `comment` pass |
|---|---|
| Pass kind | `comment` |
| Review-unit identity | From slot `REVIEW_UNIT_IDENTITY` (`O9`) |
| Unit rule | Named from the closed enumeration at slot `UNIT_RULE_ENUMERATION`; at least one rule with a counting implementation must exist for this pass kind or the coverage check does not exist (`S29`, `S30`) |
| Declared scope | The set of classifiable units the pass commits to examining, with a narrowing reason where narrower than the target set (`S26`) |
| Verification baseline sha | Captured at step two |
| Floor provenance and its observation state | The knowledge graph's build state |

**Entry — required contents** (`S138`): the churn-stable unit reference; the disposition; and the evidence that disposition requires, per the table above. A bare disposition is producible without reading anything. A citation is not.

**Materialization channel:** slot `RECORD_CHANNEL` (`O10`). The committed-file channel's cost claim is conditional on the toolchain being able to scope the agent's routine search tool, because a record carries the unit references and regenerability bases of what the pass removed, and an unscoped search tool reintroduces into retrieval much of what the pass just removed from it (`S171`, `O14`). Where that capability is absent, prefer the commit-message channel, which is outside retrieval by construction. Uncommitted scratch output is not a third channel, because it satisfies no gate (`S139`).

Outputs of the pass are not members of its declared scope and are not counted for coverage: an ADR written or extended by a relocation, and the record itself (`S27`). Output added lines are governed by no cap, which is accepted deliberately (`S69`).

---

## Human boundary

What the human reviews, in what order, against what:

1. The gate result. If any gate check failed, **stop**. A reviewer handed a diff whose coverage, removal-authorization, ancestry or bound checks failed is being asked to substitute attention for a control (`S163`).
2. The removed lines, first and in full, read against the classification record (`S13`).
3. A spot-check of entries at rate `SPOT_CHECK_RATE` — uncalibrated (`O8`) — concentrating on `regenerable → delete` entries, where the recorded basis is checked against the fixed standard rather than against the reviewer's own knowledge of the module.

This step and the entry spot-check together **are** the review budget of the unit, and they are the only real control on the regenerability test (`S13`, `S87`). `removal-authorization-check` mechanizes the crudest form of it — a removed line with no authorizing entry — and says nothing about whether an authorized removal was correct.

The review budget is a single quantity with several claims on it: removed lines to read, removal judgements to accept, entries to spot-check, the functional diff sharing the sitting, the unit rule's granularity, and the number of review units produced per week. Any proposal that tightens one by loosening another has not improved the design (`S150`).

Never parallelized: not within a review unit (`S8`), not across review units (`S9`). Where the admissible trigger rate exceeds review capacity, passes are deferred into a queue sequenced against capacity, never fanned out (`S10`).

---

## Tier assignment

| Tier | Truth source | Agent authority |
|---|---|---|
| Code-verifiable | The code, unambiguously | Decides autonomously |
| Code-visible, intent-ambiguous | The code shows a divergence, but not which side is correct | **Reports, does not resolve** |
| External truth | Business rules, regulation, contracts — outside the repository | **Escalates.** No autonomous deletion under any circumstance |

**Limitation, attached always and never presented separately** (`S94`, `S145`): the tiers are a partition of authority, not an independent control on the regenerability test. Tier assignment is itself a judgement the agent makes before it knows the answer, because it cannot know a comment states external truth until it has already decided the comment is not regenerable. A deleted regulatory constraint is an outer-tier item that was assigned to the top tier. What would reveal such a misassignment is not the tier table: it is a reviewer reading the removed line, or the constraint surfacing later as a defect. The only controls genuinely independent of the tier judgement are the two-part bound, `removal-authorization-check`, and citation plus spot-check.

The outer tier is not the rare case (`S144`). Both lower tiers terminate in the intake (`S143`).

---

## Escalation

Appending is done by a script, invoked by this skill. It is never a hand-written note in chat (`S119`).

| | |
|---|---|
| **Destination** | Slot `INTAKE_PATH`, format `INTAKE_FORMAT` — both `O7`, both prerequisites of the first shipment (`S118`, `S126`) |
| **Entry kinds this pass produces** | suspected defect; unverifiable statement; obsolete citation (`S119`) |
| **Dedup key** | The churn-stable unit reference **alone**, never the pair of reference and kind (`S122`) |
| **Terminal state** | `ruled-external`, meaningful only for the unverifiable-statement kind; it suppresses re-escalation indefinitely and the unit is disposed `not verifiable`, frozen, and not re-escalated (`S61`, `S66`) |
| **Counted, not suppressed** | The obsolete-citation kind. Each further observation increments the occurrence count and updates the latest-observation sha (`S124`) |

**Read before append.** The append is suppressed where any non-suppressed entry exists for that reference, and the script surfaces the existing entry so the pass can request reclassification instead of appending a duplicate (`S121`, `S122`). This is what gives a `comment` pass memory and what makes repeated passes idempotent — a frozen comment carries no marker, so a later pass re-encounters it and would otherwise re-escalate it.

Read-before-append is inert without a churn-stable unit reference. The scheme is slot `INTAKE_REFERENCE_SCHEME` (`O7`). While it is unfilled, or if it is filled with a structural or positional reference, the intake has no memory: the key both fails to suppress genuine duplicates and falsely suppresses new observations about different content (`S123`).

Required fields per entry (`S119`): what was observed; the churn-stable unit reference; the originating context; the sha in effect when the observation was made; the entry's state, one of `open`, `ruled`, `ruled-external`; the ruling sha where the state is resolved; the entry kind, reclassifiable in place by its consumer; and, for the obsolete-citation kind only, the occurrence count and latest-observation sha.

---

## What this skill's return is, honestly

High autonomy per pass; non-blocking, because external truth stops the unit rather than blocking the pass; **aggregate return to be measured** (`S128`). It is not a property to assert. Four compressions apply and point the same way: the conservative reconstructor collapses deletion authority toward the trivially tautological (`S45`); only comments carrying what the code cannot say about itself survive, defended conservatively because the failure modes are asymmetric (`S48`); whole-unit freezing preserves regenerable lines inside frozen units (`S52`); and comments are only ever read as part of a file the agent was going to read anyway, so consolidating them shortens files already in scope rather than removing anything from scope (`S153`).

Higher automation is not lower risk. This skill's characteristic failure — a deleted invariant — is the single most expensive outcome in the design, and it is invisible in the resulting file by construction (`S129`).

---

## To be confirmed

- This skill ships a **best-effort, human-supervised** runner. It diverges from the controlled bar defined above: the controlled tier requires a codebase knowledge graph (`S2`/`O1`) and the review-capacity calibration exercise (`O8`), neither of which the runner provides or invents. Caps ship as conservative defaults, not calibrated values; the graph is optional and detected, not assumed. Flagged rather than resolved, per rule line ten; the runner's floor field states which tier a given pass ran in.
- `CONSOLIDATION_COMMIT_MARK` is a slot the runner adds, not one the companion declares. The gate cannot delimit a review unit or falsify step nine's parenthood clause without a way to recognize a consolidation-class commit, so the runner reads a subject prefix. Whether commit-subject convention is the right carrier, or whether `O9` should close with a different mechanism, is for a person to rule.
- The mechanical exemption is matched by removed-line **content**, not by provenance. Two distinct removals of identical text — a genuine deletion and a reflow of the same line — are indistinguishable to it, so a content-identical unauthorized removal accompanying a mechanical commit would be exempted. This is the shape `O17` leaves open; the runner reports every exemption it applies so the hole is visible in the gate output.
