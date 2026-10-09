# Design notes — what the controls verify, and what they do not

Not needed to run a pass. Read when a gate result surprises you, when you are asked what this skill guarantees, or before changing the skill. Reasoning for every citation is in `~/.claude/documentation-lifecycle.md`.

## What each control verifies (`S148`)

| Control | Verifies | Does not verify |
|---|---|---|
| `record-check` / `coverage-check` | every unit at the baseline has exactly one entry with its script-owned fields intact; each disposition is admissible and carries its evidence; strip only deletes words; no edit changes a code token | that a disposition is right |
| `replay-check` | every changed line in scope is what the record says, and nothing else changed except declared outputs; the unit adds every ADR file an `adr:` field names (v3 record), and for each `adr_text` unit exactly the file the runner derives, with exactly the rendered content | that the record is right; that an ADR states its decision faithfully |
| `code-invariance-check` | no non-comment token changed (certain lexers) | a directive the directive list does not name; a test that reads source text or line numbers |
| `removal-authorization-check` | every removed line sits in an enumerated unit whose entry authorizes a change | that the authorized change was correct |
| `baseline-ancestry-check --unit-gate` | the baseline parents the unit, and no functional commit sits inside it | a functional commit landing after the unit (`S164` is a constraint, not a check) |
| `bound-check` | judgement volume and removed-line volume against the caps | correctness; the caps are uncalibrated (`O8`) |
| `scope-cross-check` | declared scope against the target set — for a `graph` or `exclusion-inventory` floor, the provider's output as the gate re-runs it (ADR 0011) | that the target set was right; with a self-report floor, or a provider from an uncommitted config, it floors nothing (`S2`) |
| `batch-plan`, `batch-next` | every review unit stays under both caps by construction; done units and the master are read from git, and each unit re-checks the master — its gate and that no correction touched an applied unit (ADR 0015), and that none would renumber an ADR a review unit wrote, an ADR's number being fixed by its unit's rank among the master's `adr_text` units — one plus the highest number the directory holds at the baseline, plus the rank (ADR 0018); a unit's lines equal the batch baseline before its judgement is carried (ADR 0013) | that the master's judgement is right — each unit is still gated and reviewed |
| `record-fill` | each judgement lands on the unit its block names by id and fingerprint; no script-owned field is written; no unit is filled twice; nothing outside `.consolidation/` changed (an untracked `.consolidation.json` is the owner's input, not a change — ADR 0022); every refusal writes nothing | that a judgement is right; an intake append, or a git command that leaves the tree identical |
| `batch-run` | nothing of its own: every unit passes each `batch-next` control, one at a time, and the loop stops at the first `STOP` and when the suite is due | the suite: it pauses for it |
| `config-bound-check` | an uncommitted config only tightens the gates (ADR 0012) | that the committed values are right (`O8`) |

The runner's caches are performance only, never controls. The git reads, configs and records it keeps within one command hold the same bytes a fresh read returns, and a check decides the same with or without them. The one cache kept across commands, the history walk's `consolidation-verified`, is trusted like the scripts, never as evidence (ADR 0016).

The only controls on the regenerability judgement itself are the evidence requirement and the owner reading the removed lines with the spot-check (`S13`, `S87`). A gate failure stops the review: a reviewer is never asked to substitute attention for a control (`S163`).

## The tier limitation, attached always (`S94`, `S145`)

| Tier | Truth source | Agent authority |
|---|---|---|
| Code-verifiable | the code, unambiguously | decides |
| Code-visible, intent-ambiguous | the code shows a divergence, not which side is right | reports, does not resolve |
| External truth | regulation, contracts, business rules, third-party behaviour | escalates; no autonomous removal |

Tier assignment is itself a judgement made before the answer is known: a deleted regulatory constraint is an outer-tier item assigned to the top tier. What reveals it is the owner reading the removed line, or the constraint surfacing later as a defect.

## The return, honestly (`S128`, `S153`)

High autonomy per pass, non-blocking, aggregate return to be measured. The conservative reconstructor collapses deletion authority toward the tautological (`S45`); frozen units keep their redundant lines (`S52`); comments are read only inside files already in scope, so a pass shortens files rather than removing anything from retrieval. Its characteristic failure — a deleted invariant — is the most expensive outcome in the design and invisible in the resulting file by construction (`S129`).

## Residual risks of this implementation

- Lexers for shell, YAML, Ruby/Perl/R, PowerShell, batch, VB, Lua, Haskell, Lisp, Razor and ASP.NET are heuristic: invariance reports "cannot prove" there and the suite decides.
- The directive list is a default; a repository with its own tool comments extends it (`directive_patterns`).
- Workers in a sharded pass judge as well as the model they run; a weaker model is a weaker pass, which is why workers run at the orchestrator's tier.
- A standing ruling is as safe as its keep-rules: a broad ruling licenses broad condensing.

## Where the procedure comes from

`SKILL.md` keeps a citation only where the agent must read the companion. The positions behind the rest:

| Rule in `SKILL.md` | Positions |
|---|---|
| truth source; frozen units | `S127`, `S52` |
| single writer; script-owned identity and edits; read-only workers | `S8`, `S173`, `S181` |
| batch, master record, plan, one unit per command | `S184`–`S186`, ADR 0013 |
| judgement files and `record-fill`; the runner writes the ADRs | `S187`, `S188`, ADR 0017, ADR 0018 |
| the stub's facts are evidence, never a verdict; a partial removal; a condense that ends in a pointer to a specification | `S193`, `S191`, `S192` |
| the untracked `.consolidation.json` is the owner's input, not a worker's change | ADR 0022 |
| a batch ends at its final unit; re-baseline by `--carry-from`; `batch-run`; two sessions | `S189`, `S190`, ADR 0019 |
| a red suite is reverted, not patched forward; the chain accepts the printed revert commit | `S194`, ADR 0015, ADR 0021 |
| triggers; consuming an obsolete citation | `S34`, `S35`, `S140` |
| isolate; the functional-diff threshold | `S101`, `S25` |
| scope narrowing; ranges | `S26`, `S93` |
| panel and rulings | `S16`, `S179`, `S180`, ADR 0008, ADR 0009, ADR 0014 |
| comment against code; no markers in source; directives | `S50`, `S51`, `S96`, `S97`, `S176` |
| caps; sequential units | `S9`, `S81` |
| suite cadence; review order | `S182`, `S13` |

## To be confirmed

- `CONSOLIDATION_COMMIT_MARK` (`consolidation:` / `mechanical:` subject prefixes) is a slot the runner adds so the gate can delimit a review unit (`O9`); whether commit-subject convention is the right carrier is for a person to rule.
- `INTAKE_FORMAT` and `INTAKE_REFERENCE_SCHEME` (`O7`) are filled with a one-line-plus-bracket format keyed on a content fingerprint scoped to the file. A reworded unit earns a fresh entry and loses an earlier ruling — the conservative direction. Whether the intake should be a line-oriented file at all, rather than a tracker the owner already reads, is for a person to rule.
- The floor defaults to `self-report`: with no knowledge graph (`S2`, `O1`) the scope cross-check has no non-agent-authored floor; with one, the gate re-runs it and takes its observation state from its output (ADR 0011). `floor_observed` defaults to the baseline sha and is informational.
- The caps ship as conservative defaults, not calibrated values (`O8`). The controlled tier requires the calibration exercise and a knowledge graph; until both exist this is a best-effort, human-supervised pass, and the record's floor field says so.
