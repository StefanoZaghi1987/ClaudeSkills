# 0021 — The batch chain accepts exactly the revert commit `batch-revert` printed

Status: accepted
Date: 2026-10-08
Positions: adds S194; refines S186 and S189; narrows the claim "any other commit stops the batch" of ADR 0015; refines the history walk of ADR 0016

## Context

ADR 0015 gave the batch its authority in git: from the batch baseline to its final unit, every commit on the first-parent line is one the runner made, and any other commit stops the batch. Wave 2 added the revert: a red suite at the batch end is reverted, not patched forward — `git bisect run` over the unit commits finds the culprit unit (`S182`), and `batch-revert --batch B --from <k>` prints the one line the owner runs verbatim, `git -C <root> revert --no-commit <c_k> <c_k+1> … <c_n> && git -C <root> checkout HEAD -- .consolidation && git -C <root> commit -m "consolidation: revert batch <bid> units <k>..<n>"` — the done units' own commits, each unit's content commit and record commit in the committed-file channel, named one by one and never a range, so a revert commit the chain holds between two units is never re-applied, `git -C <root>` so the line runs from any directory, and the `git checkout` step present mid-batch and under `record_channel: file` whenever HEAD holds `.consolidation` — and never runs the revert itself. `batch-revert` also refuses while the record directory differs from HEAD: the revert and the restore step together would discard an uncommitted record change, and the correction and the bookkeeping are lines of one file no path-spec can tell apart. The commit that line makes sits on the first-parent line the chain reads, usually while the batch is still open, and ADR 0015's rule stops the batch at any commit the runner did not make. The revert arrived with wave 2 (51a45f2, merged at 2216cde, the wave closing at 69975dc); the tightness of its acceptance came in the fix round after it — a revert that changes a file under `.consolidation/` is refused (3c2cb47), `batch-revert` refuses while a content commit awaits its record commit (162708b), and the history walk skips only a recordless revert commit (122257e).

## Decision

The chain accepts the revert commit `batch-revert` printed, and nothing looser. A commit on the first-parent line is accepted as a revert when all of these hold.

- **The subject is exact.** It is `consolidation: revert batch <bid> units <k>..<n>`, with nothing before or after it, `<bid>` equal to this batch's id, and `<k>`, `<n>` integers with 1 ≤ k ≤ n ≤ the units the chain has already read from the line.
- **It is recordless in the sense the code checks.** It materializes no record — none embedded in its message, none as a record file under `.consolidation/` — and no file under `.consolidation/` differs between its parent and it. A revert that does is refused: the printed line carries the restore (`git checkout HEAD -- .consolidation` between the revert and the commit) for that, and a revert committed without it would silently discard the master's corrections to the units still to run (3c2cb47).
- **It never sits between a content commit and its record commit.** `batch-revert` refuses while a content commit awaits its record (162708b); in the chain such a revert dies as "not review unit", like any other commit.

The accepted revert is not a unit and not `pending`: the next unit's record names it as its baseline.

The history walk (ADR 0016) holds no batch context. It skips only the recordless commit with that subject, cannot check the batch id or the bounds, and judges every record-carrying commit whatever its subject: a revert subject over a record is replayed like any unit's (122257e).

## Consequences

The owner's revert needs no change to `batch-next` or `batch-status`: mid-batch it is the accepted subject and the next unit's baseline names it; after a completed batch it is a later commit, reported and never judged (ADR 0019). Nothing looser passes: a subject naming another batch, a range beyond the units done, a revert that touches `.consolidation/`, and a revert between a content commit and its record commit all stop the batch, as ADR 0015 requires of any commit the runner did not make. The runner still runs no destructive git: the acceptance covers the owner's commit, and the trigger stays in the owner's hand.
