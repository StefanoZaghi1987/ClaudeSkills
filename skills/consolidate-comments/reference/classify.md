# Classifying comment units

Read at step 4 of the procedure. This file is also the whole rubric of a classification worker (`parallel.md`): everything needed to fill a stub is here.

## What you are filling

`record-shard` wrote two files per shard. The **brief** (`<master>.shard-k`) is read-only: one stub per **unit** — a group of whole-line comments on consecutive lines, or one block comment. Under the `comment-fine` unit rule, a comment sharing a line with code and a Python docstring are units too. Directives (`eslint-disable`, `@ts-ignore`, `# noqa`, `//go:build`…) and license headers are never units; the record cannot mention them. The stub's `id`, `file`, `lines`, `span`, `fingerprint`, `preview` and `facts` belong to the script.

The **judgement file** (`<master>.shard-k.j`) is the one you fill. It holds one block per unit of the brief, opened by a header line `@@ <id> <fingerprint>`. Keep each header line as written, and under it write only these fields:

| Field | When |
|---|---|
| `disposition` | always — exactly one, spelled as in the table below |
| `basis` | always, except where the table says `—` |
| `edit:` | the new text, for `condense`, `stale fragment → strip`, and optionally `ruled → apply` / `obsolete`; for `regenerable → delete`, a subset of the unit's whole lines |
| `claims:` | `condense` only — everything the new text keeps |
| `ruling:` | `ruled → apply` (the intake fingerprint) and `condense` (the `SR-…` id) |
| `adr_title`, `adr_text:` | `historical decision → ADR` only — the ADR's title and body ("The ADR text" below) |
| `escalate:` | rarely: an intake kind that overrides the one implied by the disposition |

Multi-line fields put each line after `| ` (a lone `|` for an empty line). The stub in the brief:

```
@@unit 7
file: src/pay/flush.js
lines: 40-42
span: 40:2-42:58
fingerprint: 9f2c14e8
preview: // TASK-0014.02 (2026-10-01): flush before close
```

Its block in the judgement file, filled:

```
@@ 7 9f2c14e8
disposition: stale fragment → strip
basis: ticket id and date are history; the reason stays
edit:
| // flush before close: the driver buffers writes
| // and drops them on an unflushed close
```

An `edit` holds the full new comment, markers included, without the leading indentation: `apply` re-indents it to the unit's column, and the edit keeps the unit's language. A comment sharing a line with code takes a one-line edit.

`record-fill` writes each block's fields into its unit and replaces the unit's earlier judgement. It refuses the whole fill, and writes nothing, for an unknown id, a fingerprint that differs from the stub's, a script-owned field, a unit given twice, or a working-tree change outside `.consolidation/` (an untracked `.consolidation.json` is the owner's input and passes). A correction file for a master record follows the same format and holds only the corrected units, each with its whole judgement.

## Facts

A stub may carry `facts:`, a script-owned line that `record-check` re-measures like `preview`. A fact is evidence to confirm, never a verdict: read the code before it supports a disposition, and a disposition it suggests still needs the basis the table asks for.

| Fact | What the script measured | What it suggests |
|---|---|---|
| `fragment=A,B` | text matching `fragment_patterns`: ticket ids, `#123` issue numbers, ISO and Italian dates | a stale fragment (step 8), when the reason around it stays |
| `absent=X,Y` | code-shaped names (backticked, camelCase, snake_case, dotted calls) that no code at the baseline names; comments and documentation files do not count | an obsolete subject (step 5): cite the absence claim for `X` |
| `code-like` | the comment's text parses as code in the file's language | commented-out code (step 5) |
| `separator` | no word characters | a banner line: `regenerable → delete` unless it groups sections the file needs |
| `long=N` | the unit spans N lines, from 5 | a candidate for `condense` (step 7) under a standing ruling; for every long unit not disposed `condense`, `escalate --from-record` prints one `question:` line counting them, and the agent puts it to the owner in the panel (SKILL.md step 6) |
| `narration` | the first body line opens with a step verb (`call`, `create`, `set`, `get`, `check`, …) | step narration (step 6) |
| `todo` | text matching `TODO`, `FIXME`, `XXX` or `HACK` | never a stale fragment: the work done is `obsolete` (step 5), the live intention `still true` (step 9) |
| `dup-of=3,7` | the ids of every other unit of the same file whose normalized text equals this unit's | a signal only: classify each twin on its own, by the stranger test against the code — a twin the code rebuilds is `regenerable → delete`, the basis naming the code, as for any unit. Duplication is no removal ground in a `comment` pass: `duplicate → delete` is a document disposition (ADR 0020) |

## The disposition table (`S54`, `S138`)

The *Requires* column states each disposition's demand; `record-check` enforces it for the dispositions its evidence set covers, and a bare disposition without it fails.

| Disposition | Pass kinds | Requires | Edit | Other |
|---|---|---|---|---|
| `ruled → apply` | comment | basis cites the ruling; `ruling:` names the intake entry (the entry's fingerprint, or its ref) | optional: absent removes the unit, present replaces it with the ruled text | counts toward the judgement cap (`S73`) |
| `contradicts code → suspected defect` | comment | basis = code citation (`path:line` + what is there) | never | frozen; the owner rules in the panel |
| `not verifiable` | comment | basis states what is external | never | frozen; escalated through the intake |
| `historical decision → ADR` | comment | basis = the decision in one line (title and reason); `adr_title`; `adr_text:` = the ADR body | never | the runner numbers the ADR and writes its file at `apply`; the unit is removed; `gate --unit` fails unless the unit adds exactly that file |
| `obsolete` | comment | basis = code citation or an absence claim naming the identifier | optional: only what the code at the cited location verifiably does | — |
| `regenerable → delete` | comment | basis names **which** signature, identifiers or control-flow structure rebuild it | optional: a subset of the unit's whole lines, line for line with leading and trailing whitespace ignored, with at least one line of the unit dropped | the stranger test below defines it (`S44`) |
| `condense` | comment | basis; `claims:` ledger; `ruling: SR-…` | required: the shorter text — or the pointer `see <spec path> §…` to the specification it restates | only under a standing ruling (`S179`); a pointer's path must name a file, not a directory, at the record's baseline |
| `stale fragment → strip` | comment | basis = which fragments are stale | required: the same text with the fragments deleted | only deletions pass the check (`S177`); fragments recorded in the commit message (`S49`) |
| `still true` | comment | basis = the code location that confirms it and what it says the code cannot | never | — |

## The stranger test

The reconstructor is **a competent engineer unfamiliar with this module, reading only this file, with no search and no graph** (`S44`) — never you, never someone who knows the repository. A comment is *regenerable* when that stranger could rebuild it from the signature, the identifiers and the control flow alone. If rebuilding it needs anything not in the file — a reason, a constraint, an external fact, a rejected alternative — it is not regenerable, however obvious it looks to you.

## The decision, top to bottom — first match wins (`S60`)

Ask the questions in this order and stop at the first *yes*.

1. **Has the owner ruled on this unit?** An owner ruling — a `suspected-defect` or `unverifiable-statement` intake entry that `escalate --rule` set to `ruled` — with this fingerprint, or whose explicit unit list (`units=…`, ADR 0009) names it, → `ruled → apply`, `ruling: <the entry's fingerprint>`. Apply only what the ruling text directs: a ruling to remove or replace is `ruled → apply` — without `edit` the unit is removed, with `edit` it becomes the ruled text. A ruling to keep is never `ruled → apply`; the unit stays, the basis citing the ruling (ADR 0008).
2. **Does it assert current behaviour that the code contradicts?** The subject exists, the text says what it does now, and the code does something else → `contradicts code → suspected defect`, basis = the code citation (`path:line`). The unit is *frozen*. You never rewrite the comment to match the code, and never the code to match the comment (`S50`).
3. **Does it assert a present fact whose truth is external?** Regulation, contract, business rule, third-party behaviour (a provider's API shape, a library's internals), measured environment facts → `not verifiable`. Frozen; basis states what is external. A unit whose intake entry is already `ruled-external` is `not verifiable` and is never escalated again (`S61`).
4. **Is it a decision with its reason or a rejected alternative?** Why X was chosen, which alternative failed and why, a past incident that explains a guard → `historical decision → ADR`. `basis` names the decision in one line; `adr_title` and `adr_text` carry the ADR itself (below). The runner numbers the ADR, writes its file and removes the unit at `apply`.
5. **Is its subject gone or superseded?** It names a function, path, flag or flow that no longer exists, or describes a completed intention or a revision note carrying no reason → `obsolete`, basis = a code citation, or an absence claim: "identifier `X` does not occur in the baseline tree" — `record-check` runs `git grep` at the baseline and fails a claim that code contradicts. The boundary (`S165`): where the subject exists, the statement asserts current behaviour, and the code implements something different, it is `contradicts code → suspected defect` (step 2), never `obsolete`. An `edit` is allowed only to state what the code at the cited location now verifiably does. Commented-out code is `obsolete`: basis "commented-out code; live equivalent at `path:line`", or, for commented-out debug code with no live equivalent, the absence claim for a name it calls. Disabled code kept with its reason is a decision (step 4), and a usage example someone needs is `still true`.
6. **Could the stranger rebuild all of it?** Step narration (`// call the API`), name paraphrases (`// the user id`), shape-only `@returns`, banners repeating the function name → `regenerable → delete`. The basis names **which** signature, identifiers or control-flow structure carry it. A basis that restates the comment fails review (`S47`). The removal may be partial: an `edit:` here keeps a subset of the unit's whole lines — each one of the unit's lines, in the unit's order, each used once, at least one line dropped — and the basis then names the rebuild source of the lines it drops; without an edit the unit is removed whole. A unit whose kept lines still carry stale fragments takes the trim now and the strip in a later pass (step 8). A heading or label carrying an id that also appears in the code or in assertion messages (`D-P2`, `Block-3 r1`, `3.3`) is the file's cross-reference system: it stays, `still true`, even where the assertion restates its words.
7. **Is it long, and does a standing ruling cover its class?** (`standing-rulings` lists them) → `condense`: `edit` = the shorter text, `claims` = every invariant, reason, external constraint and stable id it keeps, `ruling: SR-…`. A comment that restates a rule a specification states condenses to the pointer `see <spec path> §…`; its `claims` then cite that specification by path and section, and every pointer's path must name a file at the record's baseline. Without a standing ruling this disposition does not exist.
8. **Does it carry stale fragments around a reason that stays?** Ticket or bug ids, dates, review-round stamps, file:line anchors to code that moved — a chronicle word ("used to", "previously", "was changed", "Prima", "Era") attached to a reason that stays; the story of a superseded decision is step 4 or 5, not a fragment → `stale fragment → strip`: `edit` = the same text with the fragments deleted. Only deletions pass the check: drop words and repair punctuation, add none, reorder none. A TODO, FIXME, XXX or HACK mark is never a stale fragment: where the work it names is done the unit is `obsolete` (step 5), and where the intention is still live it is `still true` (step 9).
9. **Otherwise** → `still true`, basis = the code location that confirms it and what it says that the code cannot.

## What the stranger cannot rebuild — keep these

An invariant not expressed in types (ordering, idempotence, "called once per run"); a unit or encoding; a concurrency or reentrancy constraint; a security reason; why the obvious alternative is wrong; an external quirk the code works around; a label whose id an assertion or the code also carries; a JSDoc type in a project that type-checks JavaScript; a doctest or a usage example a test runs. When in doubt between a removal and a retention, retain: a redundant line costs tokens, a deleted invariant costs a defect (`S48`).

## Freezing

`contradicts code → suspected defect` and `not verifiable` freeze the whole unit, regenerable lines included. Do not split a frozen unit or edit part of it (`S52`). The intake carries the escalation; the source file carries no marker of any kind (`S51`).

## The ADR text (step 4 above)

One decision per unit. Write it at classification, while you hold the context: only what the removed comment says and what the code verifiably shows. Its body is never edited afterwards (`S32`).

- `adr_title:` the decision, in a few words.
- `adr_text:` the body, as `| ` lines: the sections `## Context` (the situation and the forces: what the removed text said about why), `## Decision` (what was chosen; the rejected alternative, where the text names one) and `## Consequences` (what follows for the code and the documents that remain).

The runner does the rest. It numbers the ADR (the next free number in `adr_dir` at the batch baseline, in unit order), names the file `<adr_dir>/<NNNN>-<slug>.md` from the title, and writes the header — `# NNNN — <title>`, `Status: accepted`, `Date:` the baseline's commit date — above your body. Leave `adr:` out: the runner derives the path.

```
@@ 12 4be01c92
disposition: historical decision → ADR
basis: flush is synchronous because the async flush lost writes on close
adr_title: Synchronous flush on close
adr_text:
| ## Context
|
| The driver buffers writes. An asynchronous flush raced the close and lost the last writes.
|
| ## Decision
|
| `close()` flushes synchronously before it releases the handle.
|
| ## Consequences
|
| `close()` blocks until the buffer is empty (`src/pay/flush.js`).
```

## Evidence, in one line each

- Code citation: `path:line` plus what is there (`auth/sign.js:12 signs with Ed25519`).
- Absence claim: `identifier legacyAuth does not occur in the baseline tree` — check it with a search before you write it.
- Regenerable basis: `restates def add(a, b): return a + b`.
