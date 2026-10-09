# Design notes — what the controls verify, and what they do not

Not needed to run a pass. Read when a gate result surprises you, when you are asked what this skill guarantees, or before changing the skill. Reasoning for every citation is in `~/.claude/documentation-lifecycle.md`.

## What each control verifies (`S148`)

| Control | Verifies | Does not verify |
|---|---|---|
| `record-check` / `coverage-check` | every unit (or reference occurrence) at the baseline has exactly one entry with its script-owned fields intact; each disposition is admissible for the pass kind and carries its evidence; strip only deletes words; every condense cites a ruled standing ruling, and every ruled → apply an owner ruling `escalate --rule` recorded on its unit and not yet applied to another unit (ADR 0014) | that a disposition is right |
| `replay-check` | every changed line in scope is what the record says — including the `## To be confirmed` items — and nothing else changed except declared outputs (the records, added ADRs, ADR status lines) — a `last-verified-at` line included, which the record's header names (ADR 0015); the unit adds every ADR file an `adr:` field names (v3 record), and for each `adr_text` unit exactly the file the runner derives, with exactly the rendered content | that the record is right; that an ADR states its decision faithfully |
| `removal-authorization-check` | every removed line sits in an enumerated unit whose entry authorizes a change | that the change was correct |
| `baseline-ancestry-check --unit-gate` | the baseline parents the unit, and no functional commit sits inside it | a functional commit landing after the unit (`S164`) |
| `bound-check` | judgement and removed-line volume against the caps | correctness; caps are uncalibrated (`O8`) |
| `batch-plan`, `batch-next` | every review unit stays under both caps by construction; done units and the master are read from git, and each unit re-checks the master — its gate and that no correction touched an applied unit (ADR 0015), and that none would renumber an ADR a review unit wrote, an ADR's number being fixed by its unit's rank among the master's `adr_text` units — one plus the highest number the directory holds at the baseline, plus the rank (ADR 0018); a unit's lines equal the batch baseline before its judgement is carried (ADR 0013) | that the master's judgement is right — each unit is still gated and reviewed |
| `scope-cross-check` | declared scope against the target set — for a `graph` or `exclusion-inventory` floor, the provider's output as the gate re-runs it (ADR 0011) | that the target set was right; a self-report floor, or a provider from an uncommitted config, floors nothing (`S2`) |
| `record-fill` | each judgement lands on the unit its block names by id and fingerprint; no script-owned field is written; no unit is filled twice; nothing outside `.consolidation/` changed (an untracked `.consolidation.json` is the owner's input, not a change — ADR 0022); every refusal writes nothing | that a judgement is right; an intake append, or a git command that leaves the tree identical |
| `batch-run` | nothing of its own: every unit passes each `batch-next` control, one at a time, and the loop stops at the first `STOP` and when the suite is due | the suite: it pauses for it |
| `config-bound-check` | an uncommitted config only tightens the gates (ADR 0012) | that the committed values are right (`O8`) |

The runner's caches are performance only, never controls. The git reads, configs and records it keeps within one command hold the same bytes a fresh read returns, and a check decides the same with or without them. The one cache kept across commands, the history walk's `consolidation-verified`, is trusted like the scripts, never as evidence (ADR 0016).

The binding constraint of this skill is the mandatory handover: the pass classifies, rewrites what is verifiable, and hands every unresolvable statement to a person (`S131`). Pass completion is the merge of the review unit with the `## To be confirmed` section written and the intake entries appended; arbitration runs on its own cadence (`S130`). A section that survives several passes unresolved is a finding about the intake's consumer (`S68`).

## The tier limitation, attached always (`S94`, `S145`)

| Tier | Truth source | Agent authority |
|---|---|---|
| Code-verifiable | the code, unambiguously | decides |
| Code-visible, intent-ambiguous | the code shows a divergence, not which side is right | reports, does not resolve |
| External truth | business rules, regulation, contracts | escalates; no autonomous removal |

Without the top tier's boundary, consolidations delete a regulatory constraint nobody implemented yet; without the middle tier, documentation is quietly rewritten to describe a bug as intended behaviour (`S142`).

## `last-verified-at`

Written only by a `document` pass whose declared scope is the whole document, as the verification baseline sha, never the consolidation commit; omitted where a squash or rebase merge would leave it dangling (`S98`–`S100`, `O12`). A subset pass, a severance pass and a comment pass never write it. The runner writes it in the review unit that verifies the document, when the committed config sets `last_verified_at: true`; the record's header names it and `replay-check` compares it exactly (ADR 0015).

## Severance

Disabled until an `exclusion_inventory` is configured or targets are given (`S107`). Whether severing is safely agent-executable is open (`O15`); its review is permanently human and non-authorial (`S106`). Severance of a widely-cited document is a multi-unit operation sequenced against review capacity (`S109`). The inventory is a provider's file, not a declared output of a pass: `S112`'s update lands in its own commit outside the review unit, where replay never sees it.

## Where the procedure comes from

`SKILL.md` keeps a citation only where the agent must read the companion. The positions behind the rest:

| Rule in `SKILL.md` | Positions |
|---|---|
| truth source; mandatory handover | `S127`, `S131` |
| single writer; script-owned identity and edits; read-only workers | `S8`, `S173`, `S181` |
| batch, master record, plan, one unit per command | `S184`–`S186`, ADR 0013 |
| judgement files and `record-fill`; the runner writes the ADRs | `S187`, `S188`, ADR 0017, ADR 0018 |
| the stub's facts are evidence, never a verdict | `S193` |
| the untracked `.consolidation.json` is the owner's input, not a worker's change | ADR 0022 |
| a batch ends at its final unit; re-baseline by `--carry-from`; `batch-run`; two sessions | `S189`, `S190`, ADR 0019 |
| reverting done units; the chain accepts the printed revert commit | `S194`, ADR 0015, ADR 0021 |
| triggers; severance preconditions | `S34`, `S35`, `S140`, `S103`, `S3`, `S106`, `S107` |
| what is not a pass | `S33`, `S46`, `S172` |
| isolate; the functional-diff threshold | `S101`, `S25` |
| scope narrowing; ranges; large documents | `S26`, `S36`, `S93` |
| panel and rulings; suppressed units | `S16`, `S61`, `S66`, `S180`, ADR 0008, ADR 0009, ADR 0014 |
| `last-verified-at` | `S98`–`S100`, `S162` |
| exclusion inventory update | `S112` |
| statement against code; `## To be confirmed`; unmarked content | `S50`, `S64`, `S95`, `S142` |
| completion; caps; sequential units | `S130`, `S9`, `S81` |

## To be confirmed

- `CONSOLIDATION_COMMIT_MARK` (`consolidation:` / `mechanical:` subject prefixes) is a slot the runner adds so the gate can delimit a review unit (`O9`); whether commit-subject convention is the right carrier is for a person to rule.
- `INTAKE_FORMAT` and `INTAKE_REFERENCE_SCHEME` (`O7`) are filled with a one-line-plus-bracket format keyed on a content fingerprint scoped to the file. This skill's bound *is* the handover, so its consumer is load-bearing: a format nobody consumes is where the append pathology reappears (`S68`).
- A severance occurrence is a path-segment match of the target's basename; two excluded targets sharing a basename over-count. The inventory's content is `S112`'s; its line format is the runner's, which reads the last tab-separated field of each line as the target.
- The caps ship as conservative defaults (`O8`); with no knowledge graph the floor is self-report (`S2`, `O1`).
