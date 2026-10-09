---
name: consolidate-comments
description: Run a `comment` consolidation pass over in-code comments — delete what a stranger to the module could rebuild from the file, strip stale fragments (ticket ids, dates, chronicle), condense under the owner's standing ruling, freeze and escalate everything else — through a script-owned record, script-applied edits and replay gates. Use at feature or epic completion, or on entry into brainstorming on a previously-touched area, between implementation phases.
---

# `comment` consolidation pass

**Truth source:** the code in the repository. External truth is a stop condition: the unit is *frozen* byte-for-byte, escalated through the intake, and the pass moves on.

**Single writer.** You own the baseline, the gates, the intake, the owner panel and every commit. The script owns unit identity, the record and every file edit, ADR files included. You write judgement in *judgement files* (`.j`); `record-fill` writes it into the record, and the runner writes the files. Workers you dispatch only read and fill their own `.j` file.

**Batch.** Every pass is a *batch*: one *master record* classified once, one owner panel, then review units the runner cuts under the caps and runs one at a time. A small pass is a batch of one unit; there is no second procedure.

Runner: `python "<this skill's directory>/scripts/consolidate.py" <command>` — `python3` where `python` is absent; run from anywhere inside the repository. Below, `B` is the batch id (`B-<n>`) and `T` the target-set file. `S…` citations point into `~/.claude/documentation-lifecycle.md`; read only the section cited. `ADR NNNN` is `~/.claude/documentation-lifecycle-adr/NNNN-*.md`.

## When

- At the completion of a feature or epic.
- On entry into brainstorming on an area touched in the past.
- An open obsolete-citation entry in the intake is consumed by the next pass of either kind, with `escalate --consume`.

A pass runs between implementation phases. An observation made mid-implementation — a stale comment noticed during a fix, a review thread, a lint sweep, "tidy the comments while you are in there" — goes into the intake as one line and waits for the next trigger.

## Procedure

Each step ends on its completion criterion. Start a step only when the previous criterion holds.

1. **Isolate.** Commit the functional work; never stash it. Run `preflight`.
   *Done when* `preflight` exits 0 and you have read every foreign commit it lists. A functional diff above `FUNCTIONAL_DIFF_THRESHOLD` moves the pass to its own batch, after the functional work merges.

2. **Scope.** List the files the feature touched (or let `knowledge_graph` select them), then `mkdir -p .consolidation` and `target-set --pass-kind comment --scope FILES… > .consolidation/B-<n>.targets`. The batch scope is the target set; narrow it only for a `bound-driven split` or a `freshness exclusion` (`--narrowing-reason`). Size does not matter here: step 7 cuts the batch under the caps.
   *Done when* every file in scope enumerates (no `unsupported` line).

3. **Master record.** `batch-init --pass-kind comment --batch-id B-<n> --scope FILES… [--narrowing-reason "…"]` — add `--floor graph` when `knowledge_graph` selected the scope, so the gate re-runs it.
   *Done when* `.consolidation/B-<n>-<sha7>.batch` exists; its baseline is HEAD.

4. **Classify.** `record-shard --record B --shards N` writes, for each shard, a read-only brief (the stubs) and a judgement file `<master>.shard-k.j`. Use `N = 1` when you classify alone. Shard across read-only workers ([`reference/parallel.md`](reference/parallel.md)) above about 40 units or at 3 or more files. Fill every block of each `.j` file following [`reference/classify.md`](reference/classify.md); the stub's `facts:` are evidence to confirm, never a verdict. A removal may keep a subset of a unit's lines and a condense may end in a pointer to the specification the comment restates; classify.md says when. Then run `record-fill --record B --from <every .j file>`. The record changes only through `record-fill`.
   *Done when* `record-fill` exits 0 and reports 0 units still empty.

5. **Gate the master record.** `gate --pre --batch B --target-set T`.
   *Done when* the last line reads `GATE PASSED`. It runs no bound check: the caps apply to the review units of step 7.

6. **Panel.** `escalate --from-record B`, then present every frozen unit to the owner in one panel — leave out those it answered `suppressed`; for a `ruled` entry, correct the unit to `ruled → apply` with the `ruling:` line the runner prints, as below — and record each answer with `escalate --rule`, always with `--fingerprint` from the stub ([`reference/escalation.md`](reference/escalation.md)). A `question:` line it prints goes into the same panel; record a standing ruling (`escalate --standing`) only when the owner answers with one, in the owner's words. For each answer that directs an edit, write the unit's new judgement — `ruled → apply`, `ruling: <fingerprint>`, and `edit:` when the ruling gives new text — in a *correction file*: a `.j` file under `.consolidation/` that holds only the corrected units, each with its whole judgement. Run `record-fill --record B --from <correction file>`, then step 5 again.
   *Done when* every frozen unit has an intake entry, every answer the owner gave is recorded, and `gate --pre --batch B` passes again.

7. **Plan.** `batch-plan --batch B`. It prints the review units in run order: whole files packed under the caps, a large file cut into line ranges run bottom-up, and a final nil unit for the files that do not change. A range that cannot fit the caps fails and names itself. Then narrow the batch scope and re-baseline with step 3's `batch-init` with the narrower `--scope`, `--carry-from <old master>` and `--narrowing-reason "bound-driven split: …"` (add `--force` to keep the same batch id). It carries every judgement whose unit is unchanged; classify only the units it lists as uncarried (step 4), then run steps 5–7 again. Keep the caps as they are (`S81`).
   *Done when* the plan is printed and no range fails.

8. **Run the units.** `batch-run --batch B --target-set T` runs the review units one after another, until the batch is complete or a `STOP`. For each unit it derives the unit's record from the master record, gates it, applies it (ADR files included), commits it with the repository's hooks, gates the unit, closes the rulings it applied and writes its review pack. It also pauses after a unit whose `SUITE:` line says to run the suite now: run the test suite, then `batch-run` again. `batch-next --batch B --target-set T` runs a single unit the same way. On `STOP` it prints what to do:
   - a failing `gate --pre`: correct the master record with a correction file and `record-fill` (step 6) — the part records are derived from the master — run `gate --pre --batch B --target-set T`, then `batch-run` again;
   - a failing commit or `gate --unit`: run the `undo:` line, correct the master record the same way, then `batch-run` again.

   Every commit from the batch baseline to the final unit is one the runner made or a mid-batch revert commit (`batch-revert`, step 9; ADR 0015, ADR 0021): commit your own work only after the batch is complete.
   *Done when* the runner prints `batch B complete`. After `/clear` or a handoff, `batch-status --batch B` shows where the batch stands and the next command.

9. **Batch end.** Run the full test suite and judge it from its log, never from a wrapper's exit code. A red suite is reverted, not patched forward: `git bisect run <suite>` over the unit commits finds the culprit unit, and `batch-revert --batch B --from <k>` prints the git line that reverts units k..n and re-opens the rulings they applied — the runner never runs destructive git: the owner runs the printed line. Then hand the owner the review packs the runner listed, in order.
   *Done when* the suite is green and the owner has the packs. The owner reads each pack's gate verdict first, then every removed line against its basis, then the ★ spot-check entries.

A complete batch stays complete. Commits made after its final unit are reported — `batch B complete; N later commit(s) after <sha7>` — and never undo it.

## Two sessions

Steps 1–7 are judgement: run them in session A, at your own model tier. Steps 8–9 are mechanical: session B may run them with any model. A gate `STOP` in session B is judgement again — correct the master record at the tier of session A. `batch-status --batch B` is the handoff between the two sessions.

## A comment batch and a specs batch on one feature

Classify both master records in one worker dispatch (`parallel.md`). Run the specs batch first: it changes documents only, so the code citations of the comment batch stay valid. Then re-baseline the comment master at the new HEAD: run step 3's `batch-init` with `--carry-from <comment master>` (it takes the next free batch id: a new baseline is a new batch), classify the units it lists as uncarried, and run steps 5–9 for it.

## Invariants

- Every change to a file in scope goes through the runner. An edit the dispositions cannot express is a question for the owner, not a hand edit.
- A comment that disagrees with the code is `contradicts code → suspected defect`. The comment is never rewritten to match the code, and the code is never changed to match the comment.
- A source file receives no marker of any kind: no annotation, no `## To be confirmed`, no `last-verified-at`.
- Directives and license headers stay untouched; the record never contains them.
- Caps, standing rulings and rulings belong to the owner. Record a ruling only in the owner's words.
- Review units run one at a time and each is reviewed; nothing fans out but read-only classification.

## Reference

| File | Read it |
|---|---|
| [`reference/classify.md`](reference/classify.md) | at step 4 — the `.j` file, dispositions, facts, the stranger test, precedence, evidence, the ADR text. It is also the worker rubric |
| [`reference/parallel.md`](reference/parallel.md) | at step 4, when you shard: above about 40 units or at 3 or more files |
| [`reference/escalation.md`](reference/escalation.md) | at step 6 — intake, owner panel, rulings, standing rulings |
| [`reference/runner.md`](reference/runner.md) | for a command's options, the record format, `.consolidation.json`, languages, and the manual unit-by-unit flow |
| [`reference/design-notes.md`](reference/design-notes.md) | when asked what the pass guarantees, or before changing the skill |
