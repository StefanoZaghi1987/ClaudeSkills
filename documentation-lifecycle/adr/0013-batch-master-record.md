# 0013 — A batch is classified once, in a master record cut into review units

Status: accepted
Date: 2026-10-06
Positions: adds S184, S185 and S186; refines S16, S180 and S181

## Context

The judgement cap (30 by default) splits an end-of-feature pass into many review units. Each unit re-read and re-classified its files, ran its own owner panel, and took about ten tool calls to init, gate, apply, commit, gate, close and pack. A split was found only when `bound-check` failed, and the manual `--carry-from` copied judgement onto the next unit with a guard that leaves a unit empty whenever an identical twin in its file was deleted, because the occurrence index in its fingerprint may then have shifted. A ruling from a unit's panel could only be applied by a later unit, so every ruling cost one more round. The controls did not need any of this repetition: one writer (`S8`), sequential units (`S9`), the bound per unit (`S81`), and a human review of each unit.

## Decision

A batch is classified once. `batch-init` writes a master record (`.consolidation/<B>-<sha7>.batch`, header `batch_master: yes`) over the whole batch scope at one baseline. Workers may shard its classification. `gate --pre --batch` runs every pre-rewrite check except the bound, and the owner panel runs once on it. Each change-directing ruling is written into the master as `ruled → apply`, and the gate is re-run. `apply` and `gate --unit` refuse a master record.

`batch-plan` cuts the gated master into review units under both caps before any gate runs. It packs whole files greedily. It cuts a file over a cap into contiguous ranges that never split a unit, run bottom-up, and keep the lines between ranges in the lower range. No cut falls below a `## To be confirmed` heading. Unchanged files form a final unit that commits only its record. The plan records a hash of the master record, so a master edited after planning stops the run.

`batch-next` runs one unit end to end. It checks that the unit's lines equal the batch baseline (the whole file, or lines 1 to the range's end), writes the unit's record at HEAD and carries the master's judgement onto units equal in file, lines, span and fingerprint. Then it runs `gate --pre`, `apply`, the commit with hooks, `gate --unit`, `escalate --close-applied` and `review-pack`, in that order. It stops with an `undo:` line at the first failure, at a stub without judgement, and at an ADR the record names that is not written yet; `--resume` continues the unit. `batch-status` prints the done and pending units and the next command.

## Consequences

Classification and the panel happen once per batch instead of once per unit, and a unit takes one command. Every unit is still an ordinary review unit with its own record, baseline, gates and review pack, so no control changes. The S16 sentence now says that a later unit of the same batch applies a panel ruling, and S180 and S181 name the master record. The carry is exact rather than guarded: bottom-up order keeps the occurrence indices of every pending range, so a twin above a deleted twin keeps its own judgement. A file whose `## To be confirmed` section sits above a range too large for the caps cannot be cut and must be narrowed by hand. The manual flow and `record-init --carry-from` remain for work outside a batch.
