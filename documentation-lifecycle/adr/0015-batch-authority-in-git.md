# 0015 — A batch's authority lives in git, and a batch range holds only runner commits

Status: accepted
Date: 2026-10-07
Positions: refines S184, S185 and S186; supersedes the plan hash, the state file, `--resume` and the agent-written `last-verified-at` commit of ADR 0013

## Context

A fresh review of the batch flow (ADR 0013) got changes past the gates with files the agent can write:

- an edited `done` commit in the state file buried an amended review unit that carried code;
- a re-plan while a unit was started made `--resume` apply the old record;
- a part record edited after a stop was committed with `GATE PASSED`, against the master record the owner's panel saw;
- a line deleted from the plan dropped a review unit, and the batch still reported complete.

The plan hash only proved that the master record matched a hash the agent could recompute. The `mechanical:` commit that wrote `last-verified-at` between units was accepted by its subject. The history walk stopped after 200 commits and then passed, so 200 empty `mechanical:` commits hid one that added code. It also skipped a `mechanical:` commit below any unit commit, even one outside that unit's range.

## Decision

Git is the batch's only authority.

- **The master record is committed.** Every review unit commits the master record (under `.consolidation/`) with its own record. The part record's header names it (`batch:`).
- **A part record is derived, never edited.** `batch-next` writes it from the master record, the review unit's scope and its baseline. `gate --unit` runs `batch-carry-check`: the master record committed with the unit holds exactly the unit's units, with the same judgement. A judgement is corrected in the master record, never in a part record.
- **The plan is recomputed.** `batch-next` cuts the plan from the master record and from what the done review units cover; the `.plan` file is a display copy. A correction of the master record is allowed on units no done review unit applied: the master record passes its gate again, and the rest is re-planned. A correction that touches an applied unit stops the batch.
- **The chain is read from git.** From the batch baseline to HEAD, every commit on the first-parent line is a review unit `batch-next` made, in order, each record naming as its baseline the commit that ended the previous unit. Any other commit stops the batch. There is no state file and no `--resume`: after a stop, `batch-next` runs again. Each run replays the last done review unit, and the last run replays every review unit at its own commit with the full unit gate before it reports the batch complete.
- **The runner writes `last-verified-at`.** When the committed `.consolidation.json` sets `last_verified_at: true`, the owner's word that the merge strategy keeps shas resolvable (`S99`), the record header names the sha and the whole documents it verifies (`last_verified_at:`). The sha is the baseline the agent classified against (`S98`): the record's baseline, or in a batch the master record's. In a batch, the review unit that runs a whole document's last range writes it (`S100`). The replay of a v3 record is exact, so a marker the record does not name fails the gate. A batch range therefore holds no `mechanical:` commit.
- **The history walk fails closed.** It has no cap. It replays every record-carrying commit at itself. It treats a commit as covered only when it lies between a unit's baseline and that unit's commit. A `mechanical:` commit may change `last-verified-at` only in a document file.

## Consequences

An agent that edits the state, the plan or a part record changes nothing the gates accept. A review unit's link to the master record, and so to the panel, is checked by every `gate --unit` and by the history walk. Re-planning after a correction cannot move a done unit. The batch end costs one more full gate per review unit. The `stubs without judgement` stop of ADR 0013 disappears: a unit of the plan that matches no classified master unit means the plan no longer holds. The manual unit-by-unit flow keeps `record-init --carry-from`. It also gets `last_verified_at` from `record-init` on a whole-document scope, so no pass needs a `mechanical:` commit for the marker. A `mechanical:` commit stays for an ADR status line, and for a post-merge sha mapping (`O12`).
