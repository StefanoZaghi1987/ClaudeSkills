---
name: consolidate-specs
description: Run a `document` or `severance` consolidation pass over specs and design docs — realign each statement to the code by editing the sentence, relocate decision history to an ADR, strip stale fragments, condense under the owner's standing ruling, and hand every statement the code cannot settle to the owner through an in-session panel and a `## To be confirmed` section; or sever inbound references to a document being excluded. Script-owned record, script-applied edits, replay gates. Use at feature or epic completion, on entry into brainstorming on a previously-touched area, or as phase one of an exclusion.
---

# Spec and design-doc consolidation

**Pass kinds:** `document` and `severance`. **Truth source:** the code **plus** business rules outside the repository. External truth is work to be arbitrated: the pass classifies, rewrites what the code verifies, and hands the rest to the owner.

**Single writer.** You own the baseline, the gates, the intake, the owner panel and every commit. The script owns unit identity, the record and every file edit, ADR files and `## To be confirmed` items included. You write judgement in *judgement files* (`.j`); `record-fill` writes it into the record, and the runner writes the files. Workers you dispatch only read and fill their own `.j` file.

**Batch.** Every pass is a *batch*: one *master record* classified once, one owner panel, then review units the runner cuts under the caps and runs one at a time. A small pass is a batch of one unit; there is no second procedure.

Runner: `python "<this skill's directory>/scripts/consolidate.py" <command>` — `python3` where `python` is absent; run from anywhere inside the repository. Below, `K` is the pass kind, `B` the batch id (`B-<n>`) and `T` the target-set file. `S…` citations point into `~/.claude/documentation-lifecycle.md`; read only the section cited. `ADR NNNN` is `~/.claude/documentation-lifecycle-adr/NNNN-*.md`.

## When

| Pass kind | Triggers |
|---|---|
| `document` | completion of a feature or epic; entry into brainstorming on an area touched in the past; an open obsolete-citation entry, consumed at the next of those |
| `severance` | phase one of an exclusion, and only that. It needs an `exclusion_inventory` (or `--target`) and a reviewer who is not its author; without a second reviewer it waits |

A pass runs between implementation phases. Writing a new spec or plan, marking a plan completed, changing an ADR's status, or "shorten this document" are not passes: status marking is a one-line `mechanical:` commit outside any review unit, and a verbose-but-true spec is shortened only under a standing ruling.

## Procedure

Each step ends on its completion criterion. Start a step only when the previous criterion holds.

1. **Isolate.** Commit the functional work; never stash it. Run `preflight`.
   *Done when* `preflight` exits 0 and you have read every foreign commit it lists. A functional diff above `FUNCTIONAL_DIFF_THRESHOLD` moves the realignment to its own batch, after the functional work merges.

2. **Scope.** Run `mkdir -p .consolidation` first.
   - `document`: the specs and design docs the feature touched or depends on — `target-set --pass-kind document --scope FILES… > .consolidation/B-<n>.targets`.
   - `severance`: `target-set --pass-kind severance > T` lists the surviving documents that reference the excluded targets. The inventory names them, so `--scope` is not accepted there; each line is `surviving-doc<TAB>…<TAB>target`. With no `exclusion_inventory` the command exits 2 printing `severance DISABLED`.

   The batch scope is the target set; narrow it only for a `bound-driven split` or a `freshness exclusion` (`--narrowing-reason`). Choose the unit rule once per document and keep it in every later pass: a unit's fingerprint, and so its intake entry, depends on the rule. Use `--unit-rule document-block` for a document made of lists and tables. Under either rule each `## To be confirmed` item is its own unit.
   *Done when* the scope and each document's unit rule are chosen.

3. **Master record.** `batch-init --pass-kind K --batch-id B-<n> --scope FILES… [--unit-rule R] [--narrowing-reason "…"] [--target PATH…]`. Add `--floor graph` when `knowledge_graph` selected the scope. A severance `--scope` is the surviving documents — the first field of each line of `T`; its floor is the inventory unless `--target` names the targets. The gate re-runs either provider.
   *Done when* `.consolidation/B-<n>-<sha7>.batch` exists; its baseline is HEAD.

4. **Classify.** `record-shard --record B --shards N` writes, for each shard, a read-only brief (the stubs) and a judgement file `<master>.shard-k.j`. Use `N = 1` when you classify alone. Shard across read-only workers ([`reference/parallel.md`](reference/parallel.md)) above about 40 units or at 3 or more files. Fill every block of each `.j` file following [`reference/classify.md`](reference/classify.md); the stub's `facts:` are evidence to confirm, never a verdict. Of two units of one document that state the same rule, one is `duplicate → delete`, its `of:` naming the other, which the record keeps. Then run `record-fill --record B --from <every .j file>`. The record changes only through `record-fill`.
   *Done when* `record-fill` exits 0 and reports 0 units still empty.

5. **Gate the master record.** `gate --pre --batch B --target-set T`. Omit `--target-set` when `--target` named the targets: `T` is built from the inventory, not from them.
   *Done when* the last line reads `GATE PASSED`. It runs no bound check: the caps apply to the review units of step 7.

6. **Panel.** `escalate --from-record B`, then present every frozen unit and every load-bearing reference to the owner in one panel — a unit carrying `conflicts:` as one question with both texts — and record each answer with `escalate --rule`, always with `--fingerprint` from the stub ([`reference/escalation.md`](reference/escalation.md)). A `question:` line it prints goes into the same panel; record a standing ruling (`escalate --standing`) only when the owner answers with one, in the owner's words. A unit `escalate --from-record` answered `suppressed` stays out of the panel: its entry is `open`, `ruled` or `ruled-external`, it is a `## To be confirmed` item, or it is the conflict partner of a unit carrying `conflicts:`. For a `ruled` entry, correct the unit to `ruled → apply` with the `ruling:` line the runner prints, as below. For each answer that directs an edit, write the unit's new judgement — `ruled → apply`, `ruling: <fingerprint>`, and `edit:` when the ruling gives new text — in a *correction file*: a `.j` file under `.consolidation/` that holds only the corrected units, each with its whole judgement. Run `record-fill --record B --from <correction file>`, then step 5 again.
   *Done when* every frozen unit has an intake entry, every answer the owner gave is recorded, and `gate --pre --batch B` passes again.

7. **Plan.** `batch-plan --batch B`. It prints the review units in run order: whole documents packed under the caps, a large document cut into line ranges run bottom-up (never between a unit and the unit its `of:` or `conflicts:` names, never below its `## To be confirmed` heading), and a final nil unit for the documents that do not change. A range that cannot fit the caps fails and names itself. Then narrow the batch scope and re-baseline with step 3's `batch-init` with the narrower `--scope`, `--carry-from <old master>` and `--narrowing-reason "bound-driven split: …"` (add `--force` to keep the same batch id). It carries every judgement whose unit is unchanged; classify only the units it lists as uncarried (step 4), then run steps 5–7 again. Keep the caps as they are (`S81`).
   *Done when* the plan is printed and no range fails.

8. **Run the units.** `batch-run --batch B --target-set T` (`--target-set` as at step 5) runs the review units one after another, until the batch is complete or a `STOP`. For each unit it derives the unit's record from the master record, gates it, applies it — sentences edited, units removed, ADR files and `## To be confirmed` items written, and `last-verified-at` on each whole document it completes when the committed config sets `last_verified_at: true` (`S98`–`S100`) — commits it with the repository's hooks, gates the unit, closes the rulings it applied and writes its review pack. `batch-next` with the same options runs a single unit the same way. On `STOP` it prints what to do:
   - a failing `gate --pre`: correct the master record with a correction file and `record-fill` (step 6) — the part records are derived from the master — run `gate --pre --batch B`, then `batch-run` again (with the same `--target-set`);
   - a failing commit or `gate --unit`: run the `undo:` line, correct the master record the same way, then `batch-run` again.

   Every commit from the batch baseline to the final unit is one the runner made or a mid-batch revert commit (`batch-revert`, below; ADR 0015, ADR 0021): commit your own work only after the batch is complete. Where the merge strategy does not keep shas resolvable, leave `last_verified_at` unset and state why the marker is omitted.
   *Done when* the runner prints `batch B complete`. After `/clear` or a handoff, `batch-status --batch B` shows where the batch stands and the next command.

9. **Batch end.** Hand the owner the review packs the runner listed, in order; a `severance` unit goes to a reviewer who is not its author. For a `severance` batch, then update the exclusion inventory with what was severed, in a commit of its own with a plain subject — neither `consolidation:` nor `mechanical:`: the inventory is the provider's file, not a declared output.
   *Done when* the owner has the packs (and, for severance, the inventory commit exists). The pass is complete when its units merge with their `## To be confirmed` items written and their intake entries appended; the rulings follow on their own cadence.

A complete batch stays complete. Commits made after its final unit are reported — `batch B complete; N later commit(s) after <sha7>` — and never undo it. Reverting done units is `batch-revert --batch B --from <k>`: it prints the git line that reverts units k..n and re-opens the rulings they applied; the runner never runs destructive git: the owner runs the printed line.

## Two sessions

Steps 1–7 are judgement: run them in session A, at your own model tier. Steps 8–9 are mechanical: session B may run them with any model. A gate `STOP` in session B is judgement again — correct the master record at the tier of session A. `batch-status --batch B` is the handoff between the two sessions.

## A specs batch and a comment batch on one feature

Classify both master records in one worker dispatch (`parallel.md`). Run the specs batch first: it changes documents only, so the code citations of the comment batch stay valid. Then re-baseline the comment master at the new HEAD: run its `batch-init` with `--carry-from <comment master>` (it takes the next free batch id: a new baseline is a new batch), classify the units it lists as uncarried, and run its steps 5–9 (`consolidate-comments`).

## Invariants

- Edit the sentence; never append a revision, never add a dated update note (rule line five).
- A statement that disagrees with the code is `contradicts code → suspected defect` until the owner rules. It is never rewritten to describe the code on the agent's own judgement.
- `## To be confirmed` holds the open items and only those. A resolved item disappears — into a body sentence, an ADR, or nothing — and is never relabelled or annotated.
- Every change to a file in scope goes through the runner. Caps, standing rulings and rulings belong to the owner; record a ruling only in the owner's words.
- Never annotate a paragraph as verified; unmarked content is current.
- Review units run one at a time and each is reviewed; nothing fans out but read-only classification.

## Reference

| File | Read it |
|---|---|
| [`reference/classify.md`](reference/classify.md) | at step 4 — the `.j` file, dispositions and facts for `document` and `severance`, precedence, evidence, the ADR text. It is also the worker rubric |
| [`reference/parallel.md`](reference/parallel.md) | at step 4, when you shard: above about 40 units or at 3 or more files |
| [`reference/escalation.md`](reference/escalation.md) | at step 6 — intake, owner panel, rulings, standing rulings |
| [`reference/runner.md`](reference/runner.md) | for a command's options, the record format, `.consolidation.json`, and the manual unit-by-unit flow |
| [`reference/design-notes.md`](reference/design-notes.md) | when asked what the pass guarantees, about `last-verified-at` or severance, or before changing the skill |
