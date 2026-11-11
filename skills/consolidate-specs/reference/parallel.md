# Sharding classification across workers

Read at step 4 when you shard: above about 40 units, or at 3 or more files. Classification is read-only and independent per file, so it can run in parallel; everything else in the pass keeps **one writer** — you (`S181`).

| You (single writer) | Workers |
|---|---|
| baseline, header, stubs (`batch-init`) | read files at the baseline |
| `record-shard`, `record-fill` | fill their own judgement file (`.j`) |
| gates, `escalate`, the owner panel | — |
| `apply`, every commit | — |

## Steps

1. `record-shard --record B --shards N`, where `B` is the batch id or the master record's path — N of 2 or more; the runner warns above 6, where each worker's fixed cost (the rubric, the precedents) outweighs its share, and never makes more shards than files. It splits by file, never inside a file, balanced by size. For each shard it writes a read-only brief `<master>.shard-k` (the stubs) and a judgement file `<master>.shard-k.j` (one `@@ <id> <fingerprint>` line per unit), and prints one line per shard.
2. Dispatch **N workers in one message**, one Agent call each, with the prompt below. Use your own model tier for workers: this is the judgement the design defends, not a lookup. Give every worker the owner's precedents from earlier units — keep-rules stated in rulings, task notes or the panel — because a worker sees none of your session. A comment batch and a specs batch taken at the same baseline share one dispatch: every worker is read-only.
3. When all have returned, `record-fill --record B --from <every .j file>`. It refuses, and writes nothing, for an unknown id, a fingerprint that differs from the stub's, a script-owned field, a unit given in two files, and any change to a file outside `.consolidation/` (an untracked `.consolidation.json` is the owner's input, not a change — ADR 0022). On a refusal, re-dispatch only the failing shard, then run `record-fill` again with every `.j` file.
   *Done when* `record-fill` exits 0 and reports 0 units still empty.
4. Optional, for large removal counts: one more worker re-reads only the entries whose disposition removes or edits text, against `classify.md`. It writes a correction file — a `.j` file under `.consolidation/` with only the units it changes, each to the retaining disposition (`still true` / `retained`) with its whole judgement, never the reverse. Then `record-fill --record B --from <correction file>`.
5. Continue at step 5 of the procedure (`gate --pre --batch`).

## Worker prompt

Fill the placeholders; send the rest verbatim.

```
You classify units for a consolidation pass. You are read-only except for one file.

Rubric: read <SKILL_DIR>/reference/classify.md and follow it exactly.
Your brief (read-only stubs): <BRIEF_PATH>
Your judgement file: <J_PATH>  (repository: <REPO_ROOT>, baseline <BASELINE_SHA>)
Standing rulings in force (cite their ids only for `condense`):
<OUTPUT OF: standing-rulings, or "none">
Ruled intake entries for units in your files (for `ruled → apply`):
<FINGERPRINT — RULING, or "none">
Owner precedents from earlier units of this repository (follow them):
<ONE LINE EACH, e.g. "labels mirrored by assert strings are kept", or "none">

For every `@@ <id> <fingerprint>` block in your judgement file, keep the header line as
written and fill `disposition`, `basis` and the fields the rubric requires. Read each file
in full before classifying its units; a unit's meaning depends on the code around it.

You may read any file and search the repository. You may edit only <J_PATH>: no other
file, your brief included. You may not run a git command that changes state, append to the
intake, or write a script-owned field (id, file, lines, span, fingerprint, preview, in_tbc,
facts). The fill rejects every one of these it can see — any working-tree change outside
.consolidation/ (an untracked .consolidation.json is the owner's, not a change — ADR 0022),
any script-owned field, any changed id or fingerprint. An intake append or a
git command that leaves the tree identical it cannot see: those rest on your word.

Return: the count per disposition, every frozen unit with one line on why, and any unit you
were unsure of.
```

## Why this is safe

One baseline, one scope, one record and one bound counter — the failure `S8` names cannot arise. `record-fill` enforces worker isolation mechanically: a worker writes only judgement, and only on the units it names by id and fingerprint. The control on each judgement is unchanged: the gates, then the owner reading the removed lines (`S13`).
