# 0019 — A batch ends at its final unit, re-baselines by carry, and runs in a loop

Status: accepted
Date: 2026-10-07
Positions: adds S189 and S190; refines S185, S186 and ADR 0015

## Context

ADR 0015 reads a batch's done units from git: every commit from the batch baseline to HEAD must be one `batch-next` made. The chain had no end. A fix committed after the batch was complete made `batch-status` stop and print an `undo:` line for work that was not the batch's. A narrowing at the plan, or a specs batch run before a comment batch on the same feature, moved HEAD away from a classified master record, and the only way forward was to classify again. Each review unit also cost one agent turn, although the run phase needs no judgement.

## Decision

- **A batch ends at its final unit.** The chain stops when the plan has no unit left. Inside the batch, from its baseline to its final unit, ADR 0015's rule is unchanged. Later commits are reported, never judged: `batch-next` and `batch-status` print `batch B complete; N later commit(s) after <sha7>` and exit 0, with no `undo:` line.
- **A master record is re-baselined by carry.** `batch-init … --carry-from OLD` (a record path or a batch id) writes a new master record at HEAD and copies the judgement onto units equal in file and fingerprint, the `record-init` carry rule. It lists the uncarried units to classify. `batch-init` refuses a batch id that already has a master record, and prints the next free id; `--force` reuses the id. One step serves a bound-driven narrowing, a second batch on the same feature, and a stale master.
- **Two batches on one feature.** Both master records are classified in one dispatch. The specs batch runs first: it changes documents only, so the code citations of the comment batch stay valid. Then the comment master is re-baselined with `--carry-from`.
- **`batch-run --batch B [--target-set T]`** runs `batch-next` in a loop and prints every unit's output. It stops at the first `STOP`, right after a unit whose `SUITE:` line says to run the suite now for a reason other than the batch end, and when the batch is complete.

## Consequences

A complete batch stays complete, whatever is committed after it. A narrowing or a second batch costs the classification of the changed units only. The run phase needs no agent turn between units, so it can run in a later session, by any model, with `batch-status` as the handoff; a gate stop is judgement again. Each unit is still gated, committed and packed one at a time, so no control changes (`S9`, `S13`).
