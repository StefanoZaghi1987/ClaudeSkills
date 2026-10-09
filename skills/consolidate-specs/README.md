# consolidate-specs

`consolidate-specs` runs a consolidation pass over specifications and design documents. It realigns every statement to the code, moves decision history into ADRs, and hands every statement the code cannot settle to you — the owner — through one in-session panel and a `## To be confirmed` section. It can also sever the inbound references to a document that is being retired.

This README is for people: it explains the structure, the logic, and the functioning of the skill. The operational procedure for the AI agent is [`SKILL.md`](SKILL.md) — this page narrates it and never replaces it. The reasoning behind every rule lives in the toolkit's companion document (see [Where to read more](#where-to-read-more)).

**What you get** from a pass: documents that match the code again, edited sentence by sentence and never by appended revisions; ADR files for the decisions the pass relocates; a `## To be confirmed` section that holds the open questions; one dated escalation line for every risky case; and a review pack for every review unit, listing every change against its reason.

## When to run a pass

| Pass kind | Run it |
|---|---|
| `document` | at the completion of a feature or an epic; on entry into brainstorming on an area touched in the past; when an open obsolete-citation entry waits to be consumed |
| `severance` | as phase one of an exclusion, and only that — cutting the references that point into a document being retired |

A pass runs between implementation phases, never in the middle of one. Some work nearby is not a pass at all: writing a new spec, marking a plan completed, changing an ADR's status, or "shorten this document". A verbose-but-true document is shortened only under a standing ruling from you.

A severance pass has two preconditions. The repository must declare an exclusion inventory (the `exclusion_inventory` key in `.consolidation.json`, or explicit targets), and someone who did not author the severance must review it. Without the inventory, the runner refuses the scope and prints `severance DISABLED`.

## The model in one page

Three actors run a pass, and each owns a distinct set of things:

- **The agent** (Claude) owns the judgement. It chooses the scope, classifies every unit, holds the owner panel, and runs the commands.
- **The runner** (the Python script this skill ships) owns the mechanics. It identifies the units, writes the record, applies every file edit, writes the ADR files and the `## To be confirmed` items, and makes every commit.
- **The owner** (you) owns the decisions the code cannot make. Caps, rulings, and standing rulings belong to you, recorded only in your words.

This division is the **single writer** principle: the agent never edits a file in scope and never edits the record. It writes its judgement in small *judgement files*; the command `record-fill` is the only path from there into the record; and the runner is the only thing that ever writes the files.

Every pass is a **batch**: one *master record* classified once, one owner panel, then *review units* that the runner cuts under the caps and runs one at a time. A small pass is a batch of one unit — there is no second, simpler procedure.

The **truth source** is the code plus the business rules that live outside the repository. Statements about the code are verified against the code and rewritten where they drifted. Everything else — regulation, contracts, customer agreements — is work to be arbitrated: the pass freezes the statement, asks you in the panel, and records the outcome. Nothing is ever rewritten silently.

The runner **never runs destructive git**. When units must be reverted, it prints the exact git line, and you run it.

## Vocabulary

| Term | Meaning |
|---|---|
| unit | the smallest thing a pass judges: one paragraph, or (under `document-block`) also one list item or table row; headings and fenced blocks are always units; in a severance pass, one reference occurrence |
| unit rule | the closed rule that enumerates units for a document: `document-paragraph` or `document-block` (severance: `reference-occurrence`); chosen once per document and kept in every later pass |
| fingerprint | a unit's content key (path + occurrence + text); identical units never share one |
| baseline | the commit the record is built at — HEAD when the batch starts |
| record | the script-owned file in `.consolidation/` holding one stub per unit plus the judgement; format version 3 |
| master record | the batch-level record, classified once, never applied itself |
| review unit | the slice one human review reads: whole documents packed under the caps, or bottom-up line ranges of a large document; ids run `B.1`, `B.2`, … |
| nil unit | the final review unit, carrying the documents that do not change |
| brief | the read-only stubs the runner writes for the classifier |
| judgement file (`.j`) | the only file the agent (or a worker) fills: one block per unit, `disposition` plus the fields it requires |
| correction file | a `.j` file holding only the units a panel answer corrected |
| `record-fill` | the only command that writes judgement into a record |
| facts | script-measured evidence lines on a stub — evidence to confirm, never a verdict |
| disposition | the judgement label for a unit (see the table below) |
| basis | the one-line evidence behind a disposition: a code citation, an absence claim, or a named external source |
| frozen | a unit that stays byte for byte: a suspected defect or a not-verifiable statement is never edited, split, or annotated |
| gate | a script check the procedure must pass; `gate --pre` guards the master record, `gate --unit` guards each review unit |
| caps | the review limits: by default 200 removed lines and 30 removal judgements per review unit |
| floor | what selected the scope: `self-report`, `graph` (a knowledge-graph command), or `exclusion-inventory` |
| owner panel | the one in-session set of questions that covers every frozen unit |
| the intake | `~/.claude/escalations.md` by default (the `intake_path` key can move it): one dated line per observation |
| ruling | your recorded answer on an intake entry; it authorizes `ruled → apply` once |
| standing ruling (`SR-…`) | your class-level ruling; the only authority for `condense` |
| review pack | the per-unit report you read: the gate verdict first, then every change against its reason |
| `batch-revert` | the command that prints the git line reverting done units and re-opens their rulings — you run the line |
| record channel | how a unit's record travels: in the unit's last commit message (default, `commit-message`) — and, under `file`, also as a committed record file |

## The workflow

The procedure has nine phases. Here is what happens in each, and who does it.

**Isolate.** The functional work is committed — never stashed — and `preflight` checks the tree is clean, the upstream is read, and every foreign commit is seen. A large functional diff moves the realignment to a batch of its own, after the functional work merges.

**Scope.** The agent lists the documents the feature touched or depends on, and `target-set` writes the target set. For severance, the target set comes from the exclusion inventory instead: it lists the surviving documents that reference the excluded targets. Each document gets its unit rule, chosen once.

**Master record.** `batch-init` writes the master record over the whole batch scope, at HEAD. From here on, git is the batch's only state: the master record is committed with every review unit, and the runner reads the done units back from the commits.

**Classify.** `record-shard` writes, per shard, a read-only brief (the stubs) and a judgement file. The agent fills every `.j` block following `reference/classify.md` — one disposition, one basis, and the fields the disposition requires. Above about 40 units, or at three or more files, the work is sharded across read-only workers, one group of files each (see `reference/parallel.md`). Of two units of one document that state the same rule, one becomes `duplicate → delete`, its `of:` naming the kept twin. Then `record-fill` writes the judgement into the record — the only path in. A worked example, from `reference/classify.md`:

```text
@@unit 3
file: docs/auth.md
lines: 12-14
span: 12:0-14:41
fingerprint: 5d0c1a77
preview: Tokens are requested through POST /v1/login and rotated
```

becomes, in the judgement file:

```text
@@ 3 5d0c1a77
disposition: obsolete
basis: POST /v1/login does not occur in the baseline tree; auth/session.js:14 issues tokens through POST /v2/session; auth/keys.js:31 schedules rotateKeys() every 24 hours
edit:
| Tokens are requested through POST /v2/session (`auth/session.js`)
| and rotated every 24 hours by `rotateKeys()`.
```

The statement drifted; the code is the truth; the sentence is edited — never appended to.

**Gate the master record.** `gate --pre` re-checks the whole record: identity, admissibility, evidence, scope. It runs no bound check — the caps apply to the review units, not to the master.

**Panel.** `escalate --from-record` appends every frozen unit to the intake. Then the agent presents, in one panel, every frozen unit and every load-bearing reference: file, line, the unit's text, and the agent's basis. Two units that conflict become one question showing both texts. Each answer is recorded with `escalate --rule`, always against the unit's fingerprint. An answer that directs an edit goes back into the master record as `ruled → apply` through a correction file — then the master gate runs again. A `question:` line the runner prints (long units no standing ruling covers) goes into the same panel.

**Plan.** `batch-plan` cuts the review units: whole documents packed under the caps, a large document cut into line ranges run bottom-up — never separating a unit from the twin its `of:` or `conflicts:` names, never below a `## To be confirmed` heading — and a final nil unit for the documents that do not change. If a range cannot fit the caps, the scope is narrowed and the master re-baselined with `--carry-from`, which carries every judgement whose unit is unchanged.

**Run the units.** `batch-run` (or `batch-next` for one unit) runs each review unit end to end: derive the unit's record from the master, gate it, apply it — sentences edited, units removed, ADR files and `## To be confirmed` items written, and `last-verified-at` written on each whole document when the committed config asks for it — commit it with the repository's hooks, gate the unit, close the rulings it applied, and write its review pack. Every commit from the batch baseline to the final unit is one the runner made or a mid-batch revert: your own work waits until the batch is complete.

**Batch end.** You receive the review packs, in order; a severance unit goes to a reviewer who is not its author. For a severance batch, the exclusion inventory is then updated in a commit of its own, outside the review units. A complete batch stays complete: commits made after its final unit are reported and never undo it.

## Dispositions

Every unit gets exactly one disposition. The questions are asked in a fixed order and the first match wins — an owner ruling before everything, a contradiction before an absence, a decision before a duplicate.

| Disposition | Meaning |
|---|---|
| `ruled → apply` | apply a decision you recorded; the ruling names the intake entry — with `edit:` it becomes the ruled text, without it the unit is removed |
| `contradicts code → suspected defect` | asserts current behaviour the code contradicts; frozen byte for byte until you rule |
| `not verifiable` | a present fact whose truth is external (business rule, regulation, contract); frozen, and its one-line question goes to `## To be confirmed` |
| `historical decision → ADR` | a decision with its reason, or a rejected alternative; the runner writes the ADR file and removes the unit |
| `duplicate → delete` | states a rule another unit of the same document also states; `of:` names the kept twin, which is judged on its own merits |
| `obsolete` | its subject is gone or superseded; with `edit:` the sentence is rewritten to the current state — this is how a spec is realigned |
| `condense` | verbose under one of your standing rulings; the shorter text keeps a `claims:` ledger of everything it keeps |
| `stale fragment → strip` | ticket ids, dates, chronicle words around a reason that stays; only deletions pass the check |
| `still true` | confirmed by the code location its basis cites |

A severance pass has only two: `severed` (the reference goes, the line rewritten or deleted) and `retained` (the reference stays — by basis, or by your ruling).

Two boundaries are worth knowing. The stranger test of the comments skill is never applied to prose: `regenerable → delete` does not exist here. And `duplicate → delete` reaches only within one document; two documents that contradict each other become one plain intake line for you, not a disposition.

## Facts are evidence, never a verdict

Each stub may carry `facts:` — lines the script measured. They point the classifier's attention; they decide nothing. A disposition still needs the basis its row demands, and `record-check` re-measures every fact at the baseline.

| Fact | The script measured | It suggests |
|---|---|---|
| `fragment=A,B` | text matching the fragment patterns: ticket ids, issue numbers, ISO and Italian dates | a stale fragment, where the statement around it stays |
| `absent=X,Y` | code-shaped names that no code at the baseline names | a gone subject: cite the absence claim for `X` |
| `separator` | no word characters at all | a thematic break: `still true` while it separates sections |
| `long=N` | the unit spans N lines (counted from 5) | a candidate for `condense` — the long units not condensed are counted in the runner's one `question:` line for the panel |
| `dup-of=3,7` | other units of the same file with equal normalized text | the same rule stated twice: the duplicate question |

## What the runner writes

- **The documents.** Sentence edits, removals, and `## To be confirmed` items — nothing else. A frozen unit adds only its `tbc:` item (the one-line open question for `## To be confirmed`); the unit itself is never annotated.
- **ADR files.** For each `historical decision → ADR` unit the classifier writes `adr_title` and `adr_text` (Context, Decision, Consequences). The runner numbers the ADR — the first takes one plus the highest number the ADR directory holds at the batch baseline, each later one the next number — names the file from the title, and writes the header (`# NNNN — <title>`, `Status: accepted`, `Date:`) above the body. The replay gate demands exactly that file, with exactly that content.
- **The `## To be confirmed` section.** It holds the open items and only those. A resolved item disappears — into a body sentence, an ADR, or nothing — and is never relabelled.
- **Commit messages.** The runner commits each review unit (`consolidation:` prefix) with the unit's record in its last commit message; under the `file` record channel the record is also committed as a file, in a record commit of its own.
- **Review packs.** One per review unit, opening with the unit gate's verdict.
- **`last-verified-at`.** Only on a whole-document scope, only in a `document` pass, and only when the committed config sets `last_verified_at: true`: the verification marker naming the baseline sha — your word that the merge strategy keeps that sha resolvable. Where it would dangle (a squash or rebase merge), it is omitted and the omission is stated.

## Escalation, the owner panel, and rulings

Every risky case becomes one dated line in the intake — `~/.claude/escalations.md` by default:

```text
- 2026-10-06 `docs/spec.md:20` — PCI-DSS retention period, unverifiable from the code (frozen unit, byte-for-byte) [kind=unverifiable-statement state=open observed=a1b2c3d fingerprint=9f2c14e8 context=consolidate-document-U-C1 tbc=4e7a90c1]
```

The kinds are `suspected-defect`, `unverifiable-statement`, `load-bearing-reference`, `obsolete-citation`, and `standing-ruling`; the state runs `open → ruled → applied` (with `ruled-external` as the terminal state of a True you confirmed with `--external`). The runner appends under a lock, and reads before appending, keyed on the fingerprint: repeated passes never duplicate a question, and a reworded statement earns a fresh entry.

The panel asks with a fixed option set per kind:

- suspected defect → **Code is right** (rewrite the text to the code) · **Code is wrong** (the entry stays open until the code is fixed) · **Leave open**;
- unverifiable statement → **True** · **False or stale** · **Leave open**;
- load-bearing reference → **Sever** · **Rewrite to a surviving target** · **Keep** · **Leave open**.

A ruling binds once. The review unit that applies it passes its gate, and the entry is closed to `applied` — identical text elsewhere cannot reuse your answer. A ruling to Keep is never `ruled → apply` (nothing you chose to keep is removed), and a ruling may name further units of the same file (`--also-fingerprint`). A **standing ruling** authorizes a class of edits — for example, how paragraphs of a given length are condensed — and it is the only authority a `condense` can cite. Your words are recorded verbatim; the agent phrases nothing you did not say.

## Two sessions, and pairing the two skills

The judgement phases — scope, classification, panel, plan — belong to session A, at its own model tier. The mechanical phases — running the units, closing the batch — can run on any model. `batch-status` is the handoff between the two sessions; after a `/clear` it shows where the batch stands and the next command. A gate `STOP` in the mechanical session is judgement again: the master record is corrected at the judgement tier.

When one feature needs both this skill and `consolidate-comments`, both master records are classified in one worker dispatch, and the **specs batch runs first** — it changes documents only, so the comment batch's code citations stay valid. The comment master is then re-baselined with `--carry-from`, which carries every judgement whose unit survived.

## Gates, and what they do not prove

`gate --pre` (the master record) runs the identity, admissibility, evidence, scope, floor-staleness, and baseline-ancestry checks — and no bound check, because a master record is not a review unit. `gate --unit` (each review unit) adds the provenance check (the record is one this unit materialized), the tree check, the **replay gate** — the record is re-applied to the baseline and the result must equal the commit, with nothing else changed — the removal-authorization check, the bound check, and the unit-level ancestry check. An `ADVISORY` line never blocks; a `FAIL` exits 1 and stops the unit.

The gates prove the record was applied, exactly, and nothing else. They do not prove the judgement was right. That control is you, reading the review packs: the gate verdict first, then every changed line against its basis, then the spot-check entries.

## Honest limits

The toolkit is best-effort and human-supervised. The caps are careful defaults, not measured values (open question `O8`); a pass never raises a cap to get through a gate. Without a knowledge graph, the floor is self-report — the scope cross-check has nothing independent to check against (`S2`, `O1`). Whether severance is safely agent-executable is open (`O15`); its review is permanently human, and never the author's. The in-session panel and the intake are the load-bearing controls: a format nobody consumes is where the old append pathology comes back.

## Where to read more

- [`SKILL.md`](SKILL.md) — the agent's procedure, step by step.
- [`reference/classify.md`](reference/classify.md) — the judgement file, the dispositions, the facts, the decision order, the ADR text. Also the whole rubric of a classification worker.
- [`reference/runner.md`](reference/runner.md) — every command with its options, the record format, the `.consolidation.json` keys, and the manual unit-by-unit flow.
- [`reference/escalation.md`](reference/escalation.md) — the intake, the owner panel, rulings, standing rulings.
- [`reference/parallel.md`](reference/parallel.md) — sharding classification across read-only workers.
- [`reference/design-notes.md`](reference/design-notes.md) — what each control verifies and what it does not; `last-verified-at`; severance.
- The companion document (`documentation-lifecycle/documentation-lifecycle.md` in this repository; `~/.claude/documentation-lifecycle.md` when installed) — the settled positions and open questions, stable `S` and `O` identifiers, behind every rule.
- The ADRs (`documentation-lifecycle/adr/` in this repository; `~/.claude/documentation-lifecycle-adr/` when installed) — 22 accepted decisions, `0001`–`0022`.
