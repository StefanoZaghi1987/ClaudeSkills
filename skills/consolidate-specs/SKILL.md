---
name: consolidate-specs
description: Run a `document` or `severance` consolidation pass over specs and design docs — realign a document to the code it describes, relocate historical rationale to an ADR, hand unresolvable statements to a person through a `## To be confirmed` section, or sever inbound references to a document being excluded from retrieval. Use at feature or epic completion, on entry into brainstorming on a previously-touched area, or as phase one of an exclusion. Never mid-implementation.
---

# Spec and design-doc consolidation

Pass kinds: `document` and `severance`. Truth source: the code **plus** business rules outside the repository. External truth is **work to be arbitrated** — the pass produces the classification, rewrites what is verifiable, and hands over a `## To be confirmed` section (`S127`).

Reasoning for every cited entry is in `~/.claude/documentation-lifecycle.md`. This file is procedure. It cites; it does not explain.

**Read before running:** the preconditions `S1`–`S3` and the first-shipment prerequisite set `S167` are stated in the companion. `S3` is the one most likely to be silently assumed here: a `severance` pass requires a reviewer who is not its author, and where no second reviewer exists the `severance` half of this skill does not run at all. Where any prerequisite is absent, this pass runs with a named control missing and says which.

---

## Implementation — the best-effort runner

This skill ships a runner: `scripts/consolidate_specs.py` (stdlib-only Python 3). Invoke any gate as `python "<this skill's directory>/scripts/consolidate_specs.py" <gate>`. If `python` is not on PATH (common on Linux), use `python3`. Each script the procedure names is a subcommand: `target-set`, `record-check`, `coverage-check`, `scope-cross-check`, `baseline-ancestry-check`, `bound-check`, `removal-authorization-check`, `floor-staleness-check`, `escalate`. `target-set` takes `--pass-kind document|severance`. Run `… self-test` to verify the install.

The gates read `pass_kind` from the record header and switch on it: a `severance` record's coverage is counted in reference occurrences, `severed` is the disposition that authorizes a removal, and `record-check` enforces the disjoint two-member disposition set rather than the document one — so a `still true` in a severance record, or a `regenerable → delete` in a document record, fails rather than reading as a considered retention. Where the inventory is unavailable, `coverage-check --target PATH…` names the excluded targets directly.

Two subcommands carry the procedure's step distinction in a flag. `bound-check --judgement --project-lines` is the step-five projection; `bound-check --measured` is the step-seven measurement against the tree; `bound-check` with no flag is the review-unit gate, enforcing both halves. `baseline-ancestry-check --unit-gate` adds step nine's parenthood clause to the ancestry check.

**Graceful degradation.** The runner is safe by construction — conservative deletion plus a human reading the removed lines is the real control (`S13`) — so it runs whether or not a project has the infrastructure the controlled tier assumes:

| Infrastructure in `.consolidation.json` | Behaviour |
|---|---|
| `knowledge_graph` set | `document` `target-set` uses it; floor = `graph` |
| absent | `document` `target-set --scope FILES` enumerates doc paragraphs; floor = `self-report` |
| caps set | `bound-check` enforces them |
| absent | `bound-check` reports counts against conservative shipped defaults; advisory, never silent |
| `exclusion_inventory` set | `severance` `target-set` runs it for inbound references |
| absent | **`severance` is disabled** — the runner emits a disabled message and the pass does not proceed (`O14`) |

The controlled tier switches on automatically when configured; until then this is a best-effort, human-supervised pass.

**Slots, resolved by the runner** (overridable via `<project>/.consolidation.json`; none invented as calibrated truth):

| Slot | Resolved to |
|---|---|
| `TARGET_SET_SCRIPT` | `consolidate_specs.py target-set` (graph if configured, else `--scope`) |
| `RECORD_PATH` / `RECORD_FORMAT` / `RECORD_CHANNEL` | `.consolidation/<short-baseline-sha>.record`, line-oriented key-value, committed file |
| `INTAKE_PATH` | `~/.claude/escalations.md` (already fixed by rule line eleven) |
| `INTAKE_FORMAT` | one dated line, with the `S119` fields in a trailing bracket: `` - YYYY-MM-DD `path#anchor` — divergence [kind=… state=… observed=… fingerprint=… context=…] ``. The bracket is what read-before-append parses, so the dedup rule and the obsolete-citation count have something to read |
| `INTAKE_REFERENCE_SCHEME` | Two halves, because one string cannot do both jobs. **Displayed:** `path:line` (in-file) / `path#anchor` (doc), which is what a human needs to reach the unit. **Keyed:** `fingerprint=`, the first eight hex digits of a SHA-1 over the whitespace-flattened text of the paragraph that contains the cited line, located with the same enumeration `coverage-check` counts. The script computes it; the pass never supplies it. An anchor carries no line to read, so it carries no fingerprint and falls back to the displayed reference |
| `UNIT_RULE_ENUMERATION` | `document`: paragraphs (blank-line blocks); `severance`: one inbound reference occurrence — pragmatic, not closed (`O2`) |
| `REVIEW_UNIT_IDENTITY` | the isolation commit's baseline sha |
| `MECHANICAL_REMOVAL_MARK` | commit subject prefix `mechanical:` |
| `CONSOLIDATION_COMMIT_MARK` | commit subject prefix `consolidation:`. With `mechanical:`, this is the pair the gate reads to tell a consolidation-class commit from a functional one, and therefore to delimit the review unit (`O9`) |
| `FLOOR_STALENESS_THRESHOLD` | 7 days (default) |

**Conservative cap defaults** (uncalibrated, `O8`): `REMOVED_LINE_CAP` 200, `REMOVAL_JUDGEMENT_CAP` 30, `SPOT_CHECK_RATE` 0.25, `FUNCTIONAL_DIFF_THRESHOLD` 400, `ADDED_LINE_CEILING` 200.

**Record format** — authored by the agent as it classifies, parsed by the gates (`pass_kind` selects the disposition set the gates enforce):

```
baseline_sha: <sha>
floor: self-report
floor_observed: <sha or YYYY-MM-DD>
pass_kind: document
unit_rule: document-paragraph
scope: docs/auth.md
@@unit
file: docs/auth.md
lines: 3
disposition: obsolete
basis: legacy HMAC path removed
```

`disposition` is a member of the pass kind's set below, spelled as it appears there — `record-check` rejects anything else, so a frozen unit is disposed `not verifiable` or `contradicts code → suspected defect` by name and not by a shorthand naming where it went. `floor_observed` carries the second half of header field six, the floor's observation state, and is what `floor-staleness-check` ages against the baseline.

An optional `narrowing_reason:` header line records why a declared scope is narrower than the target set; `scope-cross-check` requires it when it is, so a silent narrowing is not indistinguishable from evasion (`S93`). The line opens with one of the two reasons `S93` admits — `bound-driven split` or `freshness exclusion` — and may carry free prose after it; the gate rejects any other opening, because a reason it cannot recognize tells it nothing.

**Config** — `.consolidation.json` (optional, JSON), found by walking up from the working directory to the project root, so a gate invoked from a subdirectory does not silently run on defaults. Any cap key a gate reads overrides its default; `knowledge_graph`, `exclusion_inventory` (commands), and `intake_path` are also read; an unrecognized key is reported rather than absorbed. Three declared placeholders are read by no gate and change nothing when set: `FUNCTIONAL_DIFF_THRESHOLD` and `ADDED_LINE_CEILING` are bounds a human applies at steps one and eight, and `SPOT_CHECK_RATE` is the human boundary's sampling rate, which `bound-check` prints as a count of entries to read rather than enforcing. Absent file = run on defaults = no graph, no calibrated caps, severance disabled.

---

## Trigger conditions

| Pass kind | Admissible triggers |
|---|---|
| `document` | Completion of a feature or epic (`S34`); entry into brainstorming on an area touched in the past (`S35`); an observed obsolete-citation event, **consumed at the next occurrence of either of those** (`S140`) |
| `severance` | **One trigger and one only:** phase one of an exclusion (`S103`, `S167`). It is sequenced against review capacity, not against feature events |

**Prohibited: mid-implementation. Never** (`S140`).

Do not fire on: authoring a new spec, writing an implementation plan, marking a plan completed, rewriting an ADR status field, or a request to "shorten this document". Mechanical status marking is a merge-checklist step or hook, not a pass, and sits outside the review unit (`S33`, `S172`). A verbose-but-true spec is not shortened by consolidation; it is shortened by rewriting statements that are false, or removed from play by exclusion (`S46`).

Which pass kind a content trigger runs is determined by the artifact types the target-set selection returns, not by a separate trigger vocabulary (`S167`).

---

## Scope selection

Invoke the shared target-set selection strategy — the same one the `comment` skill invokes. The skills differ in what they do with the target set, not in how they choose it (`S133`, `S135`).

- **`document` pass:** run the shared script at slot `TARGET_SET_SCRIPT`. Its floor is the codebase knowledge graph, subject to `S2`. Its output carries the floor's provenance and observation state (`S92`). Heuristics are `O1`.
- **`severance` pass:** the target set is the set of surviving documents holding references to the excluded target. The floor is **the exclusion inventory's enumeration of inbound references, not the knowledge graph**, which cannot see the excluded target (`S107`). That enumeration is captured at exclusion time, before the target leaves the graph and the retrieval index, because afterwards no channel can produce it (`S112`).
- Blanket scope is the failure mode, not the safe default (`S26`).
- Where the graph is absent, or where the exclusion inventory is stale beyond `FLOOR_STALENESS_THRESHOLD`, the cross-check loses its floor. A stale floor invalidates the control it floors; it does not weaken it (`S6`). Say so rather than running the cross-check and reporting a pass.
- Whether the gate re-runs the selection script or reads a committed copy of its output is `O11`.

---

## Bound

**Kind: mandatory arbitration handover.** The binding constraint on this skill is not a number. It is the handover: the pass classifies, rewrites what is verifiable, and hands every unresolvable statement to a person (`S131`).

The two-part bound applies **on top**, as a review-capacity ceiling, and its numbers are placeholders:

| Part | Counts | Value |
|---|---|---|
| Line half | Removed lines across every consolidation-class commit in the review unit | placeholder `REMOVED_LINE_CAP` — **uncalibrated** |
| Judgement half | Entries carrying a disposition in the countable set below | placeholder `REMOVAL_JUDGEMENT_CAP` — **uncalibrated** |

The bound applies to every consolidation review unit, not only to `comment` passes: its justification is review capacity, which is a property of the human rather than of the artifact type (`S78`). Whether the values should differ by pass kind is `O8`. Both halves are scoped to the review unit, not the commit; splitting across commits does not raise them (`S75`).

Every consolidation-class commit counts against the totals, **including the severance commit** (`S76`). The record commit is consolidation-class for identity and contributes zero to both caps (`S77`). The mechanical commit contributes zero (`S90`, `S162`).

**This skill ships as a best-effort, human-supervised runner, not as controlled** on its numeric half. A placeholder cap is not a bound (`S132`); the runner supplies conservative default caps (see *Implementation*) so the pass is runnable, while the calibrated values still require the review-capacity calibration exercise (`S155`, `S156`), whose design is open under `O8`.

Also uncalibrated: `SPOT_CHECK_RATE` (`O8`), `FUNCTIONAL_DIFF_THRESHOLD` (`S25`, `O8`), `ADDED_LINE_CEILING` (`S69`, `O8`), `FLOOR_STALENESS_THRESHOLD` (`S6`, `O1`), `OBSERVATION_WINDOW_EVENTS` (`S154`, `O3`), which sizes the observation window and is not a `.consolidation.json` key — set there it is reported as unknown, like any other key no gate reads.

Severance of a heavily-referenced target is slow, and that is accepted: each occurrence is a judgement, so excluding a widely-cited document becomes a multi-unit operation sequenced against review capacity (`S109`). Whether occurrences of one target within one document should count as a single judgement is `O8`.

---

## Dispositions

Exactly one per classifiable unit (`S53`).

### `document` pass — six of the seven content-pass dispositions

| Disposition | Effect | Counts against the judgement cap | Evidence required |
|---|---|---|---|
| `ruled → apply` | Unit removed; the ruled content, where the ruling directs it, is emitted to the body or to an ADR as an output | No | The intake entry and its ruling sha |
| `contradicts code → suspected defect` | Frozen whole, escalated | No | Code citation |
| `not verifiable` | Frozen whole, escalated; the item goes to `## To be confirmed` | No | — |
| `historical decision → ADR` | Relocated | Yes, unit weight; whether it should weigh more is `O8` | — |
| `obsolete` | Removed | Yes, unit weight | Code citation **or** a verifiable absence claim naming an identifier asserted not to occur in the baseline tree |
| `still true` | Retained | No | Code citation |

`regenerable → delete` is **unavailable** to a `document` pass. The regenerability test is scoped to comments and is not extended to prose; there is no equivalent reconstructor standard for a specification, and inventing one would extend the design's weakest judgement to its highest-value artifact (`S46`). The removal grounds available here are therefore `ruled → apply`, `obsolete` and `historical decision → ADR` only.

In a `document` pass, `still true` means verifiable in the current code and nothing more (`S57`).

**Countable set for the judgement cap** in a `document` pass: `obsolete`, `historical decision → ADR` (`S73`).

### `severance` pass — a disjoint two-member set

| Disposition | Effect | Counts against the judgement cap | Evidence required |
|---|---|---|---|
| `severed` | Reference removed | Yes, unit weight | The exclusion-inventory entry for the target |
| `retained` | Reference kept | No | Reason |

Both members are needed or the coverage check is unfalsifiable: if every entry is a `severed`, entry count equals occurrence count by construction and the check verifies nothing. `retained` records a decision not to sever a particular occurrence, counts for coverage, and shows the reviewer its reason (`S58`).

**Countable set for the judgement cap** in a `severance` pass: `severed` (`S73`).

### Precedence order — content passes

Most-conservative to least, first match wins (`S60`):

`ruled → apply` **>** `contradicts code → suspected defect` **>** `not verifiable` **>** `historical decision → ADR` **>** `obsolete` **>** `regenerable → delete` **>** `still true`

Members unavailable to the pass kind are skipped, not substituted. `ruled → apply` is available only where an intake entry in state `ruled` exists for that unit (`S60`).

### `obsolete` versus `contradicts code → suspected defect`

Where the subject no longer exists, or the statement describes a superseded state, a completed intention or a past revision — `obsolete`. Where the subject exists, the statement asserts current behaviour, and the code implements something different — `contradicts code → suspected defect`, because the agent cannot establish which side is wrong (`S165`, `S50`). The line over-reports into the defect channel, deliberately (`S62`).

Freezing is whole-unit and applies to both frozen dispositions (`S52`).

Contradiction **across** documents is none of these grounds and has no treatment in this pass. Its detection is `O5`.

---

## The `## To be confirmed` section

Written by a `document` pass only. A `severance` pass **never** writes one: its declared scope is reference occurrences rather than document content, and it has verified no statement in the file (`S70`).

- The heading is exactly `## To be confirmed`.
- It carries the `not verifiable` bucket, and only that bucket. Items, not the record (`S51` inverse; the sole content crossing from classification into the document).
- It is excepted from *documents describe current state only* on state-versus-open-work grounds, not metadata grounds: open work assigned to a person is not current state, and it earns its place because the next reader must see it (`S63`).
- **Open work is resolved by deletion.** A person rules; the item then becomes a sentence in the body because it was true, moves to an ADR because it was a decision, or disappears because it was neither. It is never re-labelled, never annotated with its resolution, and never kept as a record of having once been uncertain. That record is the intake entry and the commit message (`S64`).
- A later pass over the same document treats existing items as classifiable units with a defined disposition in every case: unresolved becomes `not verifiable`, frozen, with no intake append where a suppressing entry exists; an entry in `ruled` becomes `ruled → apply` and is removed, its removed lines counting against the line cap and contributing zero to the judgement cap; a terminal entry is disposed `not verifiable`, frozen, and not re-escalated (`S65`, `S61`).
- Items already present in the section at the baseline are **in scope** and are classified. Only the items this pass adds are outputs (`S27`).
- A section surviving several passes unresolved is a finding about the intake's consumer, not a reason to let it grow (`S68`). This is the one place the append pathology can reappear, and it reappears exactly when nobody is consuming the intake.
- Added items are governed by no cap. Whether added-line volume needs a ceiling of its own is `O8`; the placeholder is `ADDED_LINE_CEILING` (`S69`).

---

## Procedure

Each verification precedes the step it authorizes. The single exception is declared at step seven (`S149`).

1. **Isolate the working tree.** Separate commit, never mixed with functional changes: a separate commit within the same pull request in the merge-time case (`S34`), a standalone commit and, where review requires it, its own pull request in the brainstorming-time case (`S35`). In the merge-time case commit the functional work — never stash it (`S101`). **No functional commit follows from here to the end of the unit** (`S164`). Where the host pull request's functional diff exceeds `FUNCTIONAL_DIFF_THRESHOLD`, the realignment moves out (`S25`); where it rides along, admissible line volume is the residual after the functional diff, defined against the line half only. Where the realignment is oversized and must split, the portion that fits rides in the host pull request and the remainder becomes standalone passes — at the stated cost that the spec is knowingly left partially realigned to merged code and carries no marker in the interim, with the outstanding remainder tracked per slot `REMAINDER_TRACKING` (`S36`, `O13`). Raising the bound and mixing the realignment into the functional commit are not resolutions.

2. **Record the verification baseline.** Capture the sha of the tree after isolation and before anything is read (`S98`).

3. **Scope before classifying, and declare the scope.** Run the shared selection for a `document` pass, or take the target set from the exclusion inventory for a `severance` pass. Write the six header fields (`S137`). Commit the target-set output inside the review unit, or ensure the gate can re-run it (`S92`, `O11`). Where a single file alone would exceed the bound, the declared scope is an explicitly enumerated subset of that file, and the pass does not write `last-verified-at` (`S26`, `S100`).

4. **Classify. Do not rewrite yet.** Assign every classifiable unit in the declared scope, under the declared unit rule, exactly one disposition, applying the precedence order. Write each disposition with its churn-stable unit reference and required evidence into the record as the pass proceeds (`S138`). Exhaustiveness within the declared scope is what makes silence unambiguous.

5. **Gate before rewriting.** Scripts, not instructions performed by reading.

   | Script | Reads | Fails when |
   |---|---|---|
   | `record-check` | The record, against the header field set and the pass kind's disposition set | A header field is missing; an entry carries no disposition, or one outside this pass kind's set — which is where `S46` becomes mechanical; or a disposition requiring evidence carries no basis (`S53`, `S137`, `S138`) |
   | `coverage-check` | The record; the declared scope at the baseline sha under the declared unit rule | Entry count differs from recomputed unit count in either direction (`S88`, `S170`) |
   | `scope-cross-check` | The record header; the committed floor output | Declared scope broader than the target set, or narrower without one of exactly two recorded reasons — a bound-driven split, or a freshness exclusion (`S93`) |
   | `floor-staleness-check` | The floor's observation state | Older than the baseline by more than `FLOOR_STALENESS_THRESHOLD` (`S6`) |
   | `baseline-ancestry-check` | The declared baseline | Pre-rewrite, only that it is the tip of the isolated tree (`S91`) |
   | `bound-check --judgement` | The record | Countable entries exceed `REMOVAL_JUDGEMENT_CAP` (`S80`) |
   | `bound-check --project-lines` | The record; the baseline tree | Summed baseline lines of removal-authorizing units exceed `REMOVED_LINE_CAP`; an upper bound, so a re-scope decision surfaced to the author rather than an automatic failure (`S80`) |

   For a `severance` pass, `coverage-check` recomputes the unit count by searching the declared scope at baseline for references to the targets the exclusion inventory enumerates (`S85`). The runner counts an occurrence per appearance of a target's basename, which catches a path reference and a bare filename alike; two excluded targets sharing a basename over-count, and the distinguishing reference text is then passed as `--target`.

   **What this buys, precisely.** `record-check` makes the count worth taking: it establishes that each thing counted is a disposition admissible for this pass kind, carrying the evidence that disposition requires. The count check then defeats omission and duplication within the declared scope and nothing else. The cross-check raises the floor under scope plausibility without establishing that the scope was right. Neither defeats skimming; skimming is addressed by the citation requirement in step four plus the human spot-check in step ten (`S148`). These pre-rewrite checks read a record in the author's working tree and are therefore **not** controls (`S82`).

6. **Rewrite.** Only now. `document` pass: edit the sentence; never append a revision. Relocate historical rationale to an ADR — one file per decision, body immutable, status the single mutable field (`S32`). Write the `## To be confirmed` section from the `not verifiable` bucket. Isolate reflow, renumbering and any front-matter write into their own commit marked `MECHANICAL_REMOVAL_MARK` inside the review unit, contributing zero to both caps and exempt from removal authorization (`S90`, `S162`); how the gate recognizes mechanical removal is `O17` — the runner reads the mark and exempts a removed line whose content a mechanical commit also removed, reporting the count of exemptions applied, and while `O17` is open that content match is the hole in the removal-authorization check. `severance` pass: remove the reference occurrences disposed `severed` and update the exclusion inventory with what was severed — a mandatory step attached to the severance itself, performed regardless of who performs the severance, because otherwise the recovery data is missing during exactly the phase in which a human does the severing (`S112`, `S104`).

7. **Measure the line half.** Run `bound-check --measured`. The measured count exists only after the rewrite — the single declared exception to check-before-step ordering (`S149`). Lines removed by a `mechanical:` commit are excluded from the measurement, per the exemption at step six. **Remedies, enumerated in advance and exhaustive:** split across review units and re-run, or discard and re-scope. Raising the cap, redistributing across more commits inside the same unit, and fanning out across agents are not remedies (`S81`).

8. **Materialize the record inside the review unit** through slot `RECORD_CHANNEL` (`S84`, `O10`): a commit message body in a fixed machine-readable format placed in the last consolidation-class commit of the unit (`S169`), or a retrieval-excluded committed file in its own commit ordered after every content-removing commit and first only where the unit contains none (`S24`, `S139`). Where both realignment and severance are present in one unit, realignment precedes severance (`S24`). Where a unit would otherwise contain no commit at all, the committed-file channel is mandatory (`S169`).

9. **Run the review-unit gate.** After materialization, before human review; its failure **blocks** the review (`S163`).

   | Script | Recomputes | Fails when |
   |---|---|---|
   | `record-check` | The header field set and every entry's disposition and evidence, against the materialized record | Any of the step-five conditions, now against the record the reviewer will read (`S53`, `S137`, `S138`) |
   | `coverage-check` | The unit count itself | Inequality in either direction (`S88`, `S170`) |
   | `removal-authorization-check` | Every removed line in every consolidation-class commit | A removed line falls in no classifiable unit whose entry carries `ruled → apply`, `historical decision → ADR`, `obsolete` or `severed`; or falls inside a unit whose entry is `still true`, `retained` or frozen (`S89`) |
   | `baseline-ancestry-check --unit-gate` | Ancestry, and parenthood of the first consolidation-class commit, read through `CONSOLIDATION_COMMIT_MARK` | Either fails; an invalidation, not a warning (`S91`). Ancestry alone is nearly free in a linear history — what the parenthood clause catches is a functional commit sitting between the declared baseline and the consolidation work (`S164`) |
   | `scope-cross-check` | Declared scope against the non-narrated target set | Either direction (`S93`) |
   | `bound-check` | The judgement half against the materialized record; the line half against the tree | Either half breached (`S82`) |

   How review-unit identity is surfaced to the gate, and what gate observes a standalone multi-commit pass, is `O9`.

10. **Review the removed lines, not the result.** Human step. For a `severance` pass this review is **non-authorial**: performed by someone other than the author, or deferred until such a person is available (`S106`, `S168`).

**Pass completion is merge of the review unit, and requires the handover rather than the ruling.** A `document` pass completes when its review unit merges with the `## To be confirmed` section written and the intake entries appended. Arbitration is asynchronous, on its own cadence, and its non-performance surfaces as an unresolved section (`S130`, `S68`).

Arbitration itself is a human act outside this pass: the person records the ruling and its ruling sha in the intake and sets the entry's state to `ruled`. They do not perform the resulting edit. A subsequent agent-executed pass carrying its own record, baseline, coverage check and bound applies it, citing the intake entry as its non-agent-authored authority for the removal (`S12`, `S16`).

---

## Record

Written during the pass to slot `RECORD_PATH` in format `RECORD_FORMAT`, one entry per classifiable unit (`S136`); both stay `O10` as design questions, and the runner fills them (see *Implementation*) so `coverage-check` has an input at all (`S146`).

**Header — six fields** (`S137`):

| Field | `document` pass | `severance` pass |
|---|---|---|
| Pass kind | `document` | `severance` |
| Review-unit identity | Slot `REVIEW_UNIT_IDENTITY` (`O9`) | Same |
| Unit rule | Named from the closed enumeration at slot `UNIT_RULE_ENUMERATION` (`S29`) | **Fixed:** "one inbound reference occurrence", declared by name from that enumeration. Without that member and its counting implementation, the coverage check does not exist (`S30`, `S107`) |
| Declared scope | The set of classifiable units committed to, with a narrowing reason where narrower than the target set (`S26`) | **Fixed:** the set of surviving documents holding references to the excluded target (`S107`) |
| Verification baseline sha | Captured at step two; header field `baseline_sha`, which also carries review-unit identity per slot `REVIEW_UNIT_IDENTITY` | Same |
| Floor provenance and its observation state | The knowledge graph's build state | **The exclusion inventory's observation state** (`S107`) |

The last field is two header lines: `floor` names the provenance, `floor_observed` its observation state as a sha or an ISO date. `record-check` requires both; `floor-staleness-check` ages the second against the baseline.

**Entry — required contents** (`S138`): the churn-stable unit reference; the disposition; the evidence that disposition requires. For a `severance` pass, one entry per occurrence, disposed `severed` or `retained` (`S107`).

Choosing the unit rule is a review-budget decision, not a free per-pass preference: a coarse rule reduces entry count and spot-check surface and freezes more redundancy; a fine rule recovers those removals and raises entry count, removal-judgement count and spot-check surface (`S31`). Which further rules the enumeration should contain is `O2`.

**Materialization channel:** slot `RECORD_CHANNEL`. The committed-file channel's cost claim is conditional on the toolchain being able to scope the agent's routine search tool (`S171`, `O14`); where that capability is absent, prefer the commit-message channel, which is outside retrieval by construction. Uncommitted scratch output is not a third channel (`S139`). A newly committed record has no inbound references to sever, so its exclusion step is configuration only (`S111`).

Outputs of the pass are not members of its declared scope and are not counted for coverage: an ADR written or extended by a relocation, items this pass adds to `## To be confirmed`, and the record itself (`S27`).

---

## `last-verified-at`

Written by **exactly one pass kind under exactly one scope condition**: a `document` pass whose declared scope is the whole document (`S100`).

Three exclusions:

| Case | Why not |
|---|---|
| A subset `document` pass | It would assert verification of content never examined |
| A `comment` pass | A source file has no carrier |
| A `severance` pass | Its scope is reference occurrences; it edits a spec without verifying a single statement in it |

Further conditions:

- The recorded sha is the **verification baseline** captured at step two — the repository state the agent read while classifying — never the consolidation commit that writes the field, which does not exist until after the file is written (`S98`).
- The field is admissible only where the toolchain and merge strategy guarantee the sha remains resolvable in the integration branch after merge, or where a mechanical post-merge step maps it to a surviving one. A squash or rebase merge destroys a feature-branch sha. **A dangling sha is not an acceptable outcome; the field is omitted rather than written unresolvable** (`S99`). The mapping step is slot `BASELINE_RESOLVABILITY` (`O12`).
- A document whose format cannot carry front matter is treated like a source file: no marker, and none invented for it (`S97`).
- A document consolidated across several review units carries no marker until the last completes. No partial-verification marker is invented; the remainder is tracked per slot `REMAINDER_TRACKING` (`S100`, `O13`).
- The field measures distance from the verified state, not the quality of the verification (`S148`).
- Refreshing the field replaces a line that sits in no classifiable unit, so it travels in the mechanical commit and is exempt from removal authorization (`S162`).

Never annotate a paragraph as verified. Unmarked content is current (`S95`).

---

## Human boundary

1. The gate result. If any gate check failed, **stop** (`S163`).
2. The removed lines, first and in full, read against the classification record (`S13`).
3. An entry spot-check at rate `SPOT_CHECK_RATE` — uncalibrated (`O8`). For an ADR relocation, the reviewer reads **two** diffs — the removal from the source and the addition to the ADR — and judges the transfer faithful. It costs more reviewer attention than a plain deletion and is counted at full unit weight, not at a discount (`S74`).

For a `severance` pass the reviewer is **not** the author (`S106`). Where no second reviewer exists, the pass is deferred, not self-reviewed (`S3`, `S168`). During the first shipment a human authors removals as well as reviewing them, so a hand-run pass is likewise reviewed by someone other than its author or deferred (`S168`).

The review budget is a single quantity with several claims on it (`S150`). Never parallelized within a review unit (`S8`) or across review units (`S9`); excess trigger rate is queued and sequenced against capacity, at the partial-realignment cost of `S36`, knowingly incurred (`S10`).

---

## Tier assignment

| Tier | Truth source | Agent authority |
|---|---|---|
| Code-verifiable | The code, unambiguously | Decides autonomously |
| Code-visible, intent-ambiguous | The code shows a divergence, but not which side is correct | **Reports, does not resolve** |
| External truth | Business rules, regulation, contracts — outside the repository | **Escalates.** No autonomous deletion under any circumstance |

**Limitation, attached always** (`S94`, `S145`): the tiers partition authority and do not validate tier assignment. Tier assignment is itself a judgement made before the answer is known. A deleted regulatory constraint is an outer-tier item assigned to the top tier; what would reveal the misassignment is a reviewer reading the removed line, or the constraint surfacing later as a defect — not the table. The only controls genuinely independent of the tier judgement are the two-part bound, `removal-authorization-check`, and citation plus spot-check. The outer tier is not the rare case (`S144`); both lower tiers terminate in the intake (`S143`).

The middle tier is the one that gets omitted and the one that causes the most expensive failures: without the top tier's boundary made explicit, the outcome is technically impeccable consolidations that delete a regulatory constraint nobody had implemented yet; without the middle tier, the outcome is documentation quietly rewritten to describe a bug as intended behaviour (`S142`).

---

## Escalation

Appending is done by a script invoked by this skill, never a hand-written note in chat (`S119`).

Invoke it as `… escalate --file PATH --anchor ANCHOR --kind KIND --divergence TEXT` (`--line N` for an in-file reference). `--kind` is required, one of `suspected-defect`, `unverifiable-statement`, `load-bearing-reference`, `obsolete-citation` — the dedup rule switches on it, so an entry without one has no defined suppression behaviour. `--state` defaults to `open`; `--observed` defaults to the short HEAD sha; `--context` defaults to this skill's name; `fingerprint` is computed from `--file` and `--line` and cannot be passed. A pass consuming an obsolete-citation event invokes `… escalate --file PATH --anchor ANCHOR --consume` instead, with neither `--kind` nor `--divergence`: it resolves the existing entry to `ruled` and records the pass's sha as the ruling sha, and it refuses every other kind, because those are ruled by a human editing the intake (`S125`). The script writes one dated line carrying the required fields in a trailing bracket:

```
- 2026-08-03 `docs/auth.md#retention` — GDPR Art. 5 unverifiable in repo [kind=unverifiable-statement state=open observed=a1b2c3d context=consolidate-specs]
- 2026-08-03 `docs/auth.md:41` — cites the removed HMAC path [kind=obsolete-citation state=open observed=a1b2c3d fingerprint=9f2c14e8 context=consolidate-specs occurrences=2 latest=d4e5f60]
```

An obsolete-citation entry additionally carries `occurrences=` and `latest=`, which the script increments in place rather than appending a second line.

| | |
|---|---|
| **Destination** | Slot `INTAKE_PATH`, format `INTAKE_FORMAT`. Both stay `O7` as design questions, and the runner fills them (see *Implementation*), which is what discharges the first-shipment prerequisite (`S118`, `S126`) |
| **Entry kinds this skill produces** | suspected defect; unverifiable statement; load-bearing reference; obsolete citation (`S119`) |
| **Dedup key** | The churn-stable unit reference **alone**, never the pair of reference and kind, because a consumer reclassification would otherwise let a duplicate through (`S122`) |
| **Terminal state** | `ruled-external`, meaningful only for the unverifiable-statement kind; the unit is then disposed `not verifiable`, frozen, and not re-escalated (`S61`, `S66`) |
| **Counted, not suppressed** | The obsolete-citation kind; each further observation increments the occurrence count and updates the latest-observation sha, and a reclassification preserves the accumulated count (`S124`) |

A `severance` pass's load-bearing reference travels through the intake **alone**, as an entry of the load-bearing-reference kind, and the occurrence is disposed `retained` with its reason. It does not go into a `## To be confirmed` section (`S70`).

Resolution by kind (`S125`): a suspected defect resolves to `ruled`, meaning the defect was fixed or the documentation was corrected on human authority; a load-bearing reference resolves to `ruled`, the ruling determining whether the reference is severed, rewritten to a surviving target, or kept; an obsolete-citation event resolves to `ruled` when a consolidation pass consumes it, which the pass records with `escalate --consume`; `ruled-external` is admissible only for the unverifiable-statement kind.

**Read before append**, suppressed where any non-suppressed entry exists for that reference, with the existing entry surfaced so the pass can request reclassification instead (`S121`, `S122`). Suppression lapses when the content changes, and that is correct: a changed statement is a new statement and deserves a fresh ruling (`S67`). That is what the fingerprint half of slot `INTAKE_REFERENCE_SCHEME` buys: keyed on `path:line` alone the intake would have no memory, failing to suppress a paragraph that only moved and falsely suppressing a new statement at a reused line (`S123`). An anchor has no line to fingerprint, so it falls back to the displayed reference; `O7` stays open on whether the intake should be a line-oriented file at all.

Required fields per entry (`S119`): what was observed; the churn-stable unit reference; the originating context; the sha in effect when the observation was made; the state, one of `open`, `ruled`, `ruled-external`; the ruling sha where resolved; the entry kind, reclassifiable in place by its consumer; the unit's content fingerprint where one could be computed; and, for the obsolete-citation kind only, the occurrence count and latest-observation sha. A field the script does not know is the arbitrating human's and is carried through untouched when a line is re-rendered.

---

## Severance — open status and what it costs

Whether severing inbound references is safely agent-executable **at all** is `O15`. It is open. Settled around it: the review is permanently human and permanently non-authorial (`S106`); the first shipment assigns the severance itself to a human (`S14`); and it carries a classification record either way (`S107`). In the runner, `severance` is disabled outright until an `exclusion_inventory` is configured (see *Implementation*).

Severance is a destructive edit on documents that stay in play, and is governed as one: separate commit, counted against the bounds of its review unit, reviewed by reading the removed lines (`S106`, `S76`).

It is a pass kind of this skill rather than a third skill, because it operates on documents, produces a record, obeys the same procedure, and needs arbitration only where a reference is load-bearing. Leaving it inside the exclusion script would make it a silent side effect (`S108`).

Exclusion is recoverable but not costlessly: restoring an excluded file is a configuration change, while restoring the severed inbound references is a revert against documents that have themselves been edited since, so recovery cost rises with elapsed time and churn (`S104`).

**Conditional claims, stated in the sentences that make them.** Exclusion is only as strong as its weakest channel, and the agent's routine search tool is a channel rather than a residual — where the toolchain cannot scope that tool, the exclusion cost claim is conditional and is stated as such (`S103`, `O14`, slot `SEARCH_SCOPING`). Where severance is unavailable, configuration-only exclusion is admissible **only** where the toolchain refuses to resolve a reference to an excluded path, in which case the residual is the reference text alone and the benefit is conditional; where the toolchain follows the reference and pulls the target back into context, configuration-only exclusion closes nothing, is not exclusion, and the target stays in play until severance is available (`S161`, `O14`).

Phase two of an exclusion has no trigger unless one is defined. Absent a defined miss signal — slot `MISS_SIGNAL`, `O6` — the correct default is that exclusion is permanent and phase two never runs (`S105`). Where the boundary sits between an aggressively removed document and lost institutional knowledge is also `O6`.

---

## To be confirmed

- *About this skill as shipped, not the target-document section described above.* This skill ships a **best-effort, human-supervised** runner. It diverges from the controlled bar: the controlled tier requires a codebase knowledge graph (`S2`/`O1`), the review-capacity calibration exercise (`O8`), and an exclusion inventory (`O14`), none of which the runner provides or invents. Caps ship as conservative defaults, not calibrated values; `severance` is disabled until an inventory is configured. Flagged rather than resolved, per rule line ten; the runner's floor field states which tier a given pass ran in.
- `CONSOLIDATION_COMMIT_MARK` is a slot the runner adds, not one the companion declares. The gate cannot delimit a review unit or falsify step nine's parenthood clause without a way to recognize a consolidation-class commit, so the runner reads a subject prefix. Whether commit-subject convention is the right carrier, or whether `O9` should close with a different mechanism, is for a person to rule.
- The mechanical exemption is matched by removed-line **content**, not by provenance. Two distinct removals of identical text are indistinguishable to it, so a content-identical unauthorized removal accompanying a mechanical commit would be exempted. This is the shape `O17` leaves open; the runner reports every exemption it applies so the hole is visible in the gate output.
- `INTAKE_REFERENCE_SCHEME` is `O7`-open, and the runner now fills it with two halves: `path:line` displayed, a content fingerprint keyed. A positional key alone leaves the intake with no memory (`S123`), so the fingerprint is what makes read-before-append work at all — but choosing the unit's text as the identity of a ruling is a design decision, not a bug fix. Its residual: a unit rewritten with the same meaning in different words earns a fresh entry and loses the earlier ruling, which is the conservative direction and is stated rather than hidden. Whether the identity of a ruling should be the text, or something the toolchain supplies, is for a person to rule alongside `O7`.
- `INTAKE_FORMAT` is `O7`-open, and the runner fills it with a one-line-plus-bracket form of its own choosing. It satisfies rule line eleven and carries every `S119` field, but whether the intake should be a line-oriented file at all — rather than a tracker the arbitrating human already reads — is for a person to rule alongside `O7`. This skill's bound *is* the handover, so its consumer is load-bearing in a way the `comment` skill's is not, and a format nobody consumes is where the append pathology reappears (`S68`).
- `escalate --consume` is a subcommand flag the runner adds so a pass can perform `S125`'s resolution of an obsolete-citation event, which nothing implemented and which left a consumed event `open` and re-authorizing the next pass. It records the consuming pass's sha as the ruling sha, because no human ruled. That is the conservative reading — the event is a sighting, not a judgement — but whether a pass may write `ruled` at all, or whether the state should be a fourth one naming consumption rather than arbitration, is for a person to rule. Every other kind is refused, so the human-arbitration boundary is unchanged.
- `floor_observed` is **transcribed by the agent** into the record header, not read out of the graph or the inventory. `floor-staleness-check` therefore ages a self-reported observation state, which is the same standing every header field has pre-rewrite (`S82`) and is materialized at the step-nine gate. Closing `O1` and `O14` with floors that can be introspected for their own capture state would remove the transcription step; until then the staleness check is only as sound as the header line.
- A `severance` occurrence is counted by target **basename**. It is a counting rule the design does not specify: the inventory's format is `O14`-open, so the runner reads the last tab-separated field of each inventory line as the target. Whether the inventory should carry an explicit reference text per occurrence is for a person to rule alongside `O14`.
