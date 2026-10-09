# 0017 — Judgement has one path into a record: `record-fill`

Status: accepted
Date: 2026-10-07
Positions: adds S187; refines S181 and S173

## Context

A record had two ways in. A single classifier edited the record by hand, and workers filled shard files that `record-merge` put back together. In both cases the agent wrote out the whole record, script-owned fields included, and a check then had to prove those fields unchanged. In real sessions, writing the record took about a third of the time. A correction at a `batch-next` stop was again a hand edit of the master record, where any unit could change.

## Decision

`record-shard --record R --shards N`, with N of 1 or more, writes for each shard a read-only brief, which holds the stubs, and a judgement file, which holds one block per unit: a header line `@@ <id> <fingerprint>` and nothing else. The agent or the worker writes only judgement fields under each header, in the record's own field syntax.

`record-fill --record R --from J…` writes those fields into the named units of `R`, replaces their earlier judgement, and leaves every other unit as it was. It refuses an unknown id, a fingerprint that differs from the stub's, a script-owned field, a unit given twice across the files, and any working-tree change outside `.consolidation/`; on a refusal it writes nothing. It prints how many units it filled and how many are still empty.

The same command serves the first classification (every shard's file) and every later correction (a file with only the corrected units). `R` may be a batch id. `record-merge` stays as a legacy command.

## Consequences

Nobody edits a record by hand. The agent writes less text, because it never copies the script-owned fields. A single classifier and many workers follow one procedure (one shard or several). A correction can reach only the units it names, and a forged script-owned field is refused before any gate reads the record. The worker prompt in `reference/parallel.md` names the one file a worker may edit.
