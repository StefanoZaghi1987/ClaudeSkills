# consolidate-comments

`consolidate-comments` runs a consolidation pass over the in-code comments of a declared scope. It deletes what a stranger to the module could rebuild from the file alone, strips stale fragments — ticket ids, dates, chronicle words — condenses long comments under your standing ruling, recovers design decisions into ADRs, and freezes and escalates everything it cannot settle against the code.

This README is for people: it explains the structure, the logic, and the functioning of the skill. The operational procedure for the AI agent is [`SKILL.md`](SKILL.md) — this page narrates it and never replaces it. The reasoning behind every rule lives in the toolkit's companion document (see [Where to read more](#where-to-read-more)).

**What you get** from a pass: a minimal comment set that keeps only what the code cannot say about itself; ADR files for the decisions the pass recovers from comment history; one dated escalation line for every risky case; and a review pack for every review unit, listing every removed line against its reason.

## When to run a pass

Run a `comment` pass:

- at the completion of a feature or an epic;
- on entry into brainstorming on an area touched in the past;
- when an open obsolete-citation entry in the intake waits to be consumed.

A pass runs between implementation phases, never in the middle of one. An observation made mid-implementation — a stale comment noticed during a fix, a review thread, a lint sweep, "tidy the comments while you are in there" — goes into the intake as one line and waits for the next trigger.

## The model in one page

Three actors run a pass, and each owns a distinct set of things:

- **The agent** (Claude) owns the judgement. It chooses the scope, classifies every unit, holds the owner panel, and runs the commands.
- **The runner** (the Python script this skill ships) owns the mechanics. It identifies the units, writes the record, applies every file edit, writes the ADR files, and makes every commit.
- **The owner** (you) owns the decisions the code cannot make. Caps, rulings, and standing rulings belong to you, recorded only in your words.

This division is the **single writer** principle: the agent never edits a file in scope and never edits the record. It writes its judgement in small *judgement files*; the command `record-fill` is the only path from there into the record; and the runner is the only thing that ever writes the files.

Every pass is a **batch**: one *master record* classified once, one owner panel, then *review units* that the runner cuts under the caps and runs one at a time. A small pass is a batch of one unit — there is no second, simpler procedure.

The **truth source** is the code in the repository, alone. A comment is judged against what the code verifiably does. External truth — a business rule, a provider's API shape, a security constraint — is a *stop condition*: the unit is frozen byte for byte, escalated through the intake, and the pass moves on. (This is the deliberate contrast with `consolidate-specs`, where external truth is work to be arbitrated with you. Here, a comment that needs outside knowledge is simply not the pass's business.)

A source file receives **no marker of any kind**: no annotation, no `## To be confirmed`, no `last-verified-at`. What the pass cannot settle stays exactly as it was, and the intake carries the question.

The runner **never runs destructive git**. When units must be reverted, it prints the exact git line, and you run it.

## Vocabulary

| Term | Meaning |
|---|---|
| unit | the smallest thing a pass judges: a group of whole-line comments on consecutive lines, or one block comment; under `comment-fine`, also a comment sharing a line with code and a Python docstring |
| unit rule | the closed rule that enumerates units: `comment`, or the finer `comment-fine` |
| fingerprint | a unit's content key (path + occurrence + text); identical units never share one |
| baseline | the commit the record is built at — HEAD when the batch starts |
| record | the script-owned file in `.consolidation/` holding one stub per unit plus the judgement; format version 3 |
| master record | the batch-level record, classified once, never applied itself |
| review unit | the slice one human review reads: whole files packed under the caps, or bottom-up line ranges of a large file; ids run `B.1`, `B.2`, … |
| nil unit | the final review unit, carrying the files that do not change |
| brief | the read-only stubs the runner writes for the classifier |
| judgement file (`.j`) | the only file the agent (or a worker) fills: one block per unit, `disposition` plus the fields it requires |
| correction file | a `.j` file holding only the units a panel answer corrected |
| `record-fill` | the only command that writes judgement into a record |
| facts | script-measured evidence lines on a stub — evidence to confirm, never a verdict |
| disposition | the judgement label for a unit (see the table below) |
| basis | the one-line evidence behind a disposition: a code citation, an absence claim, or the rebuild source |
| stranger test | the standard that defines *regenerable*: could a competent engineer unfamiliar with the module rebuild the comment from this file alone? |
| frozen | a unit that stays byte for byte: a suspected defect or a not-verifiable statement is never edited, split, or annotated |
| gate | a script check the procedure must pass; `gate --pre` guards the master record, `gate --unit` guards each review unit |
| caps | the review limits: by default 200 removed lines and 30 removal judgements per review unit |
| floor | what selected the scope: `self-report` or `graph` (a knowledge-graph command) |
| owner panel | the one in-session set of questions that covers every frozen unit |
| the intake | `~/.claude/escalations.md` by default (the `intake_path` key can move it): one dated line per observation |
| ruling | your recorded answer on an intake entry; it authorizes `ruled → apply` once |
| standing ruling (`SR-…`) | your class-level ruling; the only authority for `condense` |
| review pack | the per-unit report you read: the gate verdict first, then every removed line against its basis, then the spot-check entries |
| `batch-revert` | the command that prints the git line reverting done units and re-opens their rulings — you run the line |
| record channel | how a unit's record travels: in the unit's last commit message (default, `commit-message`) — and, under `file`, also as a committed record file |

## The workflow

The procedure has nine phases. Here is what happens in each, and who does it.

**Isolate.** The functional work is committed — never stashed — and `preflight` checks the tree is clean, the upstream is read, and every foreign commit is seen. A large functional diff moves the pass to a batch of its own, after the functional work merges.

**Scope.** The agent lists the files the feature touched (or a knowledge-graph command selects them), and `target-set` writes the target set. Every file must be enumerable: an unsupported file type fails rather than yielding a silent zero. The scope's size does not matter — the plan phase cuts it under the caps.

**Master record.** `batch-init` writes the master record over the whole batch scope, at HEAD. From here on, git is the batch's only state: the master record is committed with every review unit, and the runner reads the done units back from the commits.

**Classify.** `record-shard` writes, per shard, a read-only brief (the stubs) and a judgement file. The agent fills every `.j` block following `reference/classify.md` — one disposition, one basis, and the fields the disposition requires. Above about 40 units, or at three or more files, the work is sharded across read-only workers, one group of files each (see `reference/parallel.md`). Then `record-fill` writes the judgement into the record — the only path in. A worked example, from `reference/classify.md`:

```text
@@unit 7
file: src/pay/flush.js
lines: 40-42
span: 40:2-42:58
fingerprint: 9f2c14e8
preview: // TASK-0014.02 (2026-10-01): flush before close
```

becomes, in the judgement file:

```text
@@ 7 9f2c14e8
disposition: stale fragment → strip
basis: ticket id and date are history; the reason stays
edit:
| // flush before close: the driver buffers writes
| // and drops them on an unflushed close
```

The ticket id and the date are history the version-control system already holds; the reason is what the code cannot say about itself, so it stays.

**Gate the master record.** `gate --pre` re-checks the whole record: identity, admissibility, evidence, scope. It runs no bound check — the caps apply to the review units, not to the master.

**Panel.** `escalate --from-record` appends every frozen unit to the intake. Then the agent presents, in one panel, every frozen unit: file, line, the unit's text, and the agent's basis. Each answer is recorded with `escalate --rule`, always against the unit's fingerprint. An answer that directs an edit goes back into the master record as `ruled → apply` through a correction file — then the master gate runs again. A `question:` line the runner prints (long units no standing ruling covers) goes into the same panel.

**Plan.** `batch-plan` cuts the review units: whole files packed under the caps, a large file cut into line ranges run bottom-up, and a final nil unit for the files that do not change. If a range cannot fit the caps, the scope is narrowed and the master re-baselined with `--carry-from`, which carries every judgement whose unit is unchanged.

**Run the units.** `batch-run` (or `batch-next` for one unit) runs each review unit end to end: derive the unit's record from the master, gate it, apply it (ADR files included), commit it with the repository's hooks, gate the unit, close the rulings it applied, and write its review pack. Before each unit's verdict, the gate prints a `SUITE:` line saying when to run the test suite — now, or at the batch end — and the loop pauses when it says now. Every commit from the batch baseline to the final unit is one the runner made or a mid-batch revert: your own work waits until the batch is complete.

**Batch end.** The full test suite runs, and it is judged from its log, never from a wrapper's exit code. A red suite is **reverted, not patched forward**: `git bisect` over the unit commits finds the culprit unit, and `batch-revert --from <k>` prints the git line that reverts units k..n and re-opens the rulings they applied — you run the line. Then you read the review packs, in order.

## Dispositions

Every unit gets exactly one disposition. The questions are asked in a fixed order and the first match wins — an owner ruling before everything, a contradiction before an absence, a decision before a rebuild.

| Disposition | Meaning |
|---|---|
| `ruled → apply` | apply a decision you recorded; the ruling names the intake entry — with `edit:` it becomes the ruled text, without it the unit is removed |
| `contradicts code → suspected defect` | asserts current behaviour the code contradicts; frozen byte for byte until you rule — the comment is never rewritten to match the code, and never the code to match the comment |
| `not verifiable` | a present fact whose truth is external (regulation, contract, third-party behaviour); frozen, escalated, never asked twice once ruled external |
| `historical decision → ADR` | a decision with its reason, or a rejected alternative, or a past incident that explains a guard; the runner writes the ADR file and removes the unit |
| `obsolete` | its subject is gone or superseded — commented-out code included; an `edit:` may state what the code now verifiably does |
| `regenerable → delete` | a stranger to the module could rebuild it from the file alone; the basis names which signature, identifiers, or control-flow structure carry it |
| `condense` | long, under one of your standing rulings; the shorter text keeps a `claims:` ledger — or becomes the pointer `see <spec path> §…` to the specification it restates |
| `stale fragment → strip` | ticket or bug ids, dates, review-round stamps, chronicle words around a reason that stays; only deletions pass the check, and the fragments are recorded in the commit message |
| `still true` | confirmed by the code location its basis cites — and it says something the code cannot |

Two refinements matter in practice. A removal may be **partial**: the `edit:` keeps a subset of the unit's own whole lines, line for line, when only some of them are regenerable. And a **label whose id the code or the assertions also carry** (`D-P2`, `Block-3 r1`) is the file's cross-reference system: it stays, `still true`, even where an assertion restates its words.

## The stranger test

The reconstructor is **a competent engineer unfamiliar with this module, reading only this file, with no search and no graph** — never you, never someone who knows the repository. A comment is *regenerable* when that stranger could rebuild it from the signature, the identifiers, and the control flow alone. If rebuilding it needs anything not in the file — a reason, a constraint, an external fact, a rejected alternative — it is not regenerable, however obvious it looks to you.

What the stranger cannot rebuild is the keep list: an invariant not expressed in types (ordering, idempotence, "called once per run"); a unit or encoding; a concurrency or reentrancy constraint; a security reason; why the obvious alternative is wrong; an external quirk the code works around; a doctest or usage example a test runs. When in doubt between a removal and a retention, retain: a redundant line costs tokens, a deleted invariant costs a defect.

## Facts are evidence, never a verdict

Each stub may carry `facts:` — lines the script measured. They point the classifier's attention; they decide nothing. A disposition still needs the basis its row demands, and `record-check` re-measures every fact at the baseline.

| Fact | The script measured | It suggests |
|---|---|---|
| `fragment=A,B` | text matching the fragment patterns: ticket ids, issue numbers, ISO and Italian dates | a stale fragment, where the reason around it stays |
| `absent=X,Y` | code-shaped names that no code at the baseline names | an obsolete subject: cite the absence claim for `X` |
| `code-like` | the comment's text parses as code in the file's language | commented-out code |
| `separator` | no word characters at all | a banner line — deletable unless it groups sections the file needs |
| `long=N` | the unit spans N lines (counted from 5) | a candidate for `condense` — the long units not condensed are counted in the runner's one `question:` line for the panel |
| `narration` | the first body line opens with a step verb (`call`, `create`, `set`, …) | step narration — the "narrate-all-steps" comment the pass exists to remove |
| `todo` | text matching `TODO`, `FIXME`, `XXX`, `HACK` | never a stale fragment: the done work is `obsolete`, the live intention `still true` |
| `dup-of=3,7` | other units of the same file with equal normalized text | a signal only — each twin is judged on its own, by the stranger test; duplication is a removal ground in document passes only, never here |

## What the runner writes

- **The source files.** Comment edits and removals — nothing else. The **code-invariance check** proves that no non-comment token changed; it is certain for the languages whose fixes are tested (Python, JavaScript, C/C++, Java, C#, CSS, SQL, PHP), and where a lexer is heuristic the gate reports "cannot prove" and the unit runs the test suite instead. A frozen unit's lines are never touched, and no marker of any kind is added.
- **ADR files.** For each `historical decision → ADR` unit the classifier writes `adr_title` and `adr_text` (Context, Decision, Consequences). The runner numbers the ADR — the first takes one plus the highest number the ADR directory holds at the batch baseline, each later one the next number — names the file from the title, and writes the header (`# NNNN — <title>`, `Status: accepted`, `Date:`) above the body. The replay gate demands exactly that file, with exactly that content.
- **Commit messages.** The runner commits each review unit (`consolidation:` prefix) with the unit's record in its last commit message; under the `file` record channel the record is also committed as a file, in a record commit of its own. A strip's removed fragments are recorded in the commit message.
- **Review packs.** One per review unit, opening with the unit gate's verdict.

The lexer understands strings, regex literals, heredocs, and template literals in some thirty languages — from Python and the C/Java families to SQL, HTML with inline script, Razor, ASP.NET, shell, and YAML. Lint and compiler directives (`eslint-disable`, `@ts-ignore`, `# noqa`, `//go:build`…) and license headers are never units: the record cannot even mention them.

## Escalation, the owner panel, and rulings

Every risky case becomes one dated line in the intake — `~/.claude/escalations.md` by default:

```text
- 2026-10-06 `src/a.py:20` — PCI-DSS rule, unverifiable from file (frozen unit, byte-for-byte) [kind=unverifiable-statement state=open observed=a1b2c3d fingerprint=9f2c14e8 context=consolidate-comment-U-C1]
```

The kinds are `suspected-defect`, `unverifiable-statement`, `load-bearing-reference`, `obsolete-citation`, and `standing-ruling`; the state runs `open → ruled → applied` (with `ruled-external` as the terminal state of a True you confirmed with `--external`). The runner appends under a lock, and reads before appending, keyed on the fingerprint: repeated passes never duplicate a question, and a reworded comment earns a fresh entry.

The panel asks with a fixed option set per kind:

- suspected defect → **Code is right** (rewrite the comment to the code) · **Code is wrong** (the entry stays open until the code is fixed) · **Leave open**;
- unverifiable statement → **True** · **False or stale** · **Leave open**;
- load-bearing reference → **Sever** · **Rewrite to a surviving target** · **Keep** · **Leave open**.

A ruling binds once. The review unit that applies it passes its gate, and the entry is closed to `applied` — an identical comment elsewhere cannot reuse your answer. A ruling to Keep is never `ruled → apply` (nothing you chose to keep is removed), and a ruling may name further units of the same file (`--also-fingerprint`). A **standing ruling** authorizes a class of edits — for example, *"comment units of 12 or more lines are condensed; keep every invariant, its reason and every ruling id; recast chronicle in the present tense"* — and it is the only authority a `condense` can cite. Your words are recorded verbatim; the agent phrases nothing you did not say.

## Two sessions, and pairing the two skills

The judgement phases — scope, classification, panel, plan — belong to session A, at its own model tier. The mechanical phases — running the units, closing the batch — can run on any model. `batch-status` is the handoff between the two sessions; after a `/clear` it shows where the batch stands and the next command. A gate `STOP` in the mechanical session is judgement again: the master record is corrected at the judgement tier.

When one feature needs both this skill and `consolidate-specs`, both master records are classified in one worker dispatch, and the **specs batch runs first** — it changes documents only, so this skill's code citations stay valid. This skill's master is then re-baselined with `--carry-from`, which carries every judgement whose unit survived.

## Gates, and what they do not prove

`gate --pre` (the master record) runs the identity, admissibility, evidence, scope, floor-staleness, and baseline-ancestry checks — and no bound check, because a master record is not a review unit. `gate --unit` (each review unit) adds the provenance check (the record is one this unit materialized), the tree check, the **replay gate** — the record is re-applied to the baseline and the result must equal the commit, with nothing else changed — the removal-authorization check, the code-invariance check, the bound check, and the unit-level ancestry check. An `ADVISORY` line never blocks; a `FAIL` exits 1 and stops the unit.

The gates prove the record was applied, exactly, and nothing else. They do not prove the regenerability judgement was right. That control is you, reading the review packs: the gate verdict first, then every removed line against its basis, then the spot-check entries.

## Honest limits

The toolkit is best-effort and human-supervised. The caps are careful defaults, not measured values (open question `O8`); a pass never raises a cap to get through a gate. Without a knowledge graph, the floor is self-report — the scope cross-check has nothing independent to check against (`S2`, `O1`). The lexers for some languages (shell, YAML, Ruby/Perl/R, PowerShell, batch, VB, Lua, Haskell, Lisp, Razor, ASP.NET) are heuristic: invariance reports "cannot prove" there, and the suite decides. The directive list is a default; a repository with its own tool comments extends it (`directive_patterns`). Workers in a sharded pass judge as well as the model they run. A standing ruling is as safe as its keep-rules: a broad ruling licenses broad condensing. And the pass's characteristic failure — a deleted invariant — is invisible in the resulting file by construction; that is why the review pack exists, and why the tie always goes to retention.

## Where to read more

- [`SKILL.md`](SKILL.md) — the agent's procedure, step by step.
- [`reference/classify.md`](reference/classify.md) — the judgement file, the dispositions, the facts, the stranger test, the decision order, the ADR text. Also the whole rubric of a classification worker.
- [`reference/runner.md`](reference/runner.md) — every command with its options, the record format, the `.consolidation.json` keys, the supported languages, and the manual unit-by-unit flow.
- [`reference/escalation.md`](reference/escalation.md) — the intake, the owner panel, rulings, standing rulings.
- [`reference/parallel.md`](reference/parallel.md) — sharding classification across read-only workers.
- [`reference/design-notes.md`](reference/design-notes.md) — what each control verifies and what it does not; the honest return; residual risks.
- The companion document (`documentation-lifecycle/documentation-lifecycle.md` in this repository; `~/.claude/documentation-lifecycle.md` when installed) — the settled positions and open questions, stable `S` and `O` identifiers, behind every rule.
- The ADRs (`documentation-lifecycle/adr/` in this repository; `~/.claude/documentation-lifecycle-adr/` when installed) — 22 accepted decisions, `0001`–`0022`.
