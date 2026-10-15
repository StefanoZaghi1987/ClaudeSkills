# Classifying document units and reference occurrences

Read at step 4 of the procedure. This file is also the whole rubric of a classification worker (`parallel.md`).

## What you are filling

`record-shard` wrote two files per shard. The **brief** (`<master>.shard-k`) is read-only: one stub per **unit**. In a `document` pass a unit is a paragraph (`document-paragraph`) or, under `document-block`, also each list item and table row; a heading and a fenced block are always units of their own, and front matter never is. Units under `## To be confirmed` carry `in_tbc: yes`, and each item there is a unit of its own under either rule. In a `severance` pass a unit is one occurrence of a reference to an excluded target. The stub's `id`, `file`, `lines`, `span`, `fingerprint`, `preview`, `in_tbc` and `facts` belong to the script.

The **judgement file** (`<master>.shard-k.j`) is the one you fill. It holds one block per unit of the brief, opened by a header line `@@ <id> <fingerprint>`. Keep each header line as written, and under it write only `disposition`, `basis`, and where the disposition needs them `edit:`, `claims:`, `ruling:`, `tbc:`, `of:`, `conflicts:`, `adr_title`, `adr_text:`, `escalate:`.

Multi-line fields put each line after `| ` (a lone `|` for an empty line). A document `edit` is the unit's full new text, verbatim. The stub in the brief:

```
@@unit 3
file: docs/auth.md
lines: 12-14
span: 12:0-14:41
fingerprint: 5d0c1a77
preview: Tokens are requested through POST /v1/login and rotated
```

Its block in the judgement file, filled:

```
@@ 3 5d0c1a77
disposition: obsolete
basis: POST /v1/login does not occur in the baseline tree; auth/session.js:14 issues tokens through POST /v2/session; auth/keys.js:31 schedules rotateKeys() every 24 hours
edit:
| Tokens are requested through POST /v2/session (`auth/session.js`)
| and rotated every 24 hours by `rotateKeys()`.
```

`record-fill` writes each block's fields into its unit and replaces the unit's earlier judgement. It refuses the whole fill, and writes nothing, for an unknown id, a fingerprint that differs from the stub's, a script-owned field, a unit given twice, or a working-tree change outside `.consolidation/` (an untracked `.consolidation.json` is the owner's input and passes). A correction file for a master record follows the same format and holds only the corrected units, each with its whole judgement.

## Facts

A stub may carry `facts:`, a script-owned line that `record-check` re-measures like `preview`. A fact is evidence to confirm, never a verdict: read the code before it supports a disposition, and a disposition it suggests still needs the basis the table asks for.

| Fact | What the script measured | What it suggests |
|---|---|---|
| `fragment=A,B` | text matching `fragment_patterns`: ticket ids, `#123` issue numbers, ISO and Italian dates | a stale fragment (step 8), when the statement around it stays |
| `absent=X,Y` | code-shaped names (backticked, camelCase, snake_case, dotted calls) that no code at the baseline names; comments and documentation files do not count | a gone subject (step 6): cite the absence claim for `X` |
| `separator` | no word characters | a thematic break: `still true` while it separates sections |
| `long=N` | the unit spans N lines, from 5 | a candidate for `condense` (step 7) under a standing ruling; for every long unit not disposed `condense`, `escalate --from-record` prints one `question:` line counting them, and the agent puts it to the owner in the panel (SKILL.md step 6) |
| `dup-of=3,7` | the ids of every other unit of the same file whose normalized text equals this unit's | the same rule stated twice in this document: the duplicate question (step 5) |

## The disposition table (`S54`, `S138`)

The *Requires* column states each disposition's demand; `record-check` enforces it for the dispositions its evidence set covers, and a bare disposition without it fails.

| Disposition | Pass kinds | Requires | Edit | Other |
|---|---|---|---|---|
| `ruled → apply` | document | basis cites the ruling; `ruling:` names the intake entry (the entry's fingerprint, or its ref) — for a `## To be confirmed` item, the entry of the paragraph that raised it | optional: absent removes the unit, present replaces it with the ruled text | counts toward the judgement cap (`S73`) |
| `contradicts code → suspected defect` | document | basis = code citation (`path:line` + what is there) | never | frozen; the owner rules in the panel |
| `not verifiable` | document | basis states what is external; `tbc:` item text unless an intake entry on this fingerprint is already `open` or `ruled-external` | never | frozen; `apply` writes the `## To be confirmed` item |
| `historical decision → ADR` | document | basis = the decision in one line (title and reason); `adr_title`; `adr_text:` = the ADR body | never | the runner numbers the ADR and writes its file at `apply`; the unit is removed; `gate --unit` fails unless the unit adds exactly that file |
| `duplicate → delete` | document | basis = the rule two units of this file state; `of:` = the kept unit's id, a unit whose disposition retains it | never — the unit is removed whole | within one document (ADR 0020); the kept unit is classified on its own merits |
| `obsolete` | document | basis = code citation or an absence claim naming the identifier | optional: every claim of the new text verifiable at a cited code location | this is the realignment disposition (`S50`) |
| `condense` | document | basis; `claims:` ledger; `ruling: SR-…` | required: the shorter text | only under a standing ruling (`S179`) |
| `stale fragment → strip` | document | basis = which fragments are stale | required: the same text with the fragments deleted | only deletions pass the check (`S177`) |
| `still true` | document | basis = the code location that confirms it | never | — |
| `severed` | severance | basis = the inventory entry | exactly one severed entry per line carries `edit:` = the line's full new text (empty deletes the line) | the target no longer occurs on the line |
| `retained` | severance | basis = why it stays, or the owner's ruling | never | a load-bearing reference also carries `escalate: load-bearing-reference` and goes to the panel |

## `document` pass — the decision, top to bottom, first match wins (`S60`)

The truth is the code plus business rules outside the repository. Statements about the code are verified against the code; everything else is handed to the owner.

1. **Has the owner ruled on this unit?** An owner ruling — a `suspected-defect` or `unverifiable-statement` intake entry that `escalate --rule` set to `ruled` — with this fingerprint, or whose explicit unit list (`units=…`, ADR 0009) names it, → `ruled → apply`, `ruling: <the entry's fingerprint>`. Apply only what the ruling text directs: a ruling to remove or replace is `ruled → apply` — with `edit` the unit becomes the ruled text, without it the unit is removed. A ruling to keep is never `ruled → apply`: the statement stays `not verifiable` (its entry is `ruled-external`, step 3) and a reference stays `retained`, the basis citing the ruling (ADR 0008). A `## To be confirmed` item (`in_tbc: yes`) whose paragraph's entry the owner has answered — state `ruled`, `ruled-external` or `applied` — is `ruled → apply` without `edit`, citing that entry: the answered question leaves the section (`S64`, `S65`).
2. **Does it assert current behaviour that the code contradicts?** → `contradicts code → suspected defect`, basis = code citation. Frozen. You never rewrite the document to describe what the code does when the document states what it *should* do (`S50`, `S142`); the owner rules in the panel.
3. **Does it assert a present fact whose truth is external?** Business rules, regulation, contracts, customer agreements, external systems → `not verifiable`, frozen, with `tbc:` — the one-line open question the owner must answer. `apply` adds it to `## To be confirmed`. An existing item under that heading (`in_tbc: yes`) that is still unresolved is `not verifiable` without `tbc:`. Omit `tbc:` — and expect `escalate --from-record` to answer `suppressed` — also when the unit's fingerprint already has an intake entry in state `open` or `ruled-external`: the question was asked in an earlier panel. A `ruled-external` unit is `not verifiable`, stays out of the panel and is never asked again (`S61`).
4. **Is it a decision with its reason or a rejected alternative?** "We chose X because…", "Y was tried and rejected because…", a superseded design kept for context → `historical decision → ADR`. `basis` names the decision in one line; `adr_title` and `adr_text` carry the ADR itself (below). The runner numbers the ADR, writes its file and removes the unit at `apply`.
5. **Does it state a rule another unit of this file also states?** Where the batch keeps that unit — its disposition retains it: never `historical decision → ADR`, `duplicate → delete`, nor `obsolete` or `ruled → apply` without an edit — → `duplicate → delete`, basis = the duplicated rule, `of:` = the kept unit's id. The unit is removed whole; it takes no edit (ADR 0020). The kept unit is classified on its own merits.
6. **Is its subject gone or superseded?** It describes a removed endpoint, a past layout, a completed plan, a revision note carrying no reason → `obsolete`, basis = code citation or an absence claim: "identifier `X` does not occur in the baseline tree", which `record-check` verifies with `git grep` at the baseline. The boundary (`S165`): where the subject exists, the statement asserts current behaviour, and the code implements something different, it is `contradicts code → suspected defect` (step 2), never `obsolete`. With `edit`, the unit is rewritten to the current state; every claim of the new text must be verifiable at a cited code location. This is how a stale statement is realigned: **edit the sentence, never append a revision** (rule line five).
7. **Does a standing ruling cover its class, and is it verbose?** (`standing-rulings` lists them) → `condense`: `edit`, `claims` (everything kept), `ruling: SR-…`. Without a standing ruling, a verbose but true paragraph stays as it is (`S46`).
8. **Does it carry stale fragments around statements that stay?** Ticket ids, dates, "as of round 3", links to retired documents — a chronicle word ("previously", "used to") attached to a reason that stays; the story of a superseded decision is step 4 or 6, not a fragment → `stale fragment → strip`: `edit` = the same text with the fragments deleted; only deletions pass the check.
9. **Otherwise** → `still true`, basis = the code location that confirms it. A heading is `still true` while its section exists.

`regenerable → delete` does not exist in a `document` pass: the stranger test is for comments, never for prose (`S46`).

Two statements in different documents that contradict each other, or state the same rule, are not a ground for any disposition here: `duplicate → delete` reaches only within one document, where the record can name the kept unit (ADR 0020). Note them for the owner as one dated line in the intake naming both files and lines (rule line eleven): a plain line, not an `escalate` entry, because no ruling follows from it (`O5`).

## `severance` pass — two dispositions only (`S58`)

| Disposition | When | Fields |
|---|---|---|
| `severed` | the reference to the excluded target goes | basis = the inventory entry; on each line, exactly one severed entry carries `edit:` = the line's full new text (empty to delete the line) |
| `retained` | the reference stays | basis = why, or the owner's ruling (*Keep* in the panel); never `ruled → apply`. A load-bearing reference also gets `escalate: load-bearing-reference` and goes to the panel |

A `severance` pass never writes `## To be confirmed` and never verifies a statement (`S70`). Its review is non-authorial: someone other than its author reviews it, or it waits (`S106`).

## Freezing

`contradicts code → suspected defect` and `not verifiable` freeze the whole unit — paragraph, list item or table row — byte for byte. Do not split a frozen unit or edit part of it (`S52`); a pass that needs finer units declares `document-block` for the whole document. The intake carries the escalation, and the only text a frozen unit adds to the document is its `tbc:` item under `## To be confirmed`. The unit itself receives no annotation (`S95`).

A frozen unit may carry `conflicts:` — one other unit id of this record and the same file, which itself carries no `conflicts:`. `escalate --from-record` then raises one panel entry with both texts, the carrier's followed by ` | conflicts with unit <id> (<file>:<lines>): <the target's basis or preview>`, and raises the partner none: it answers `suppressed`. The owner rules once, with `escalate --rule` as for any frozen unit, and the ruling may name both units (`--also-fingerprint`, ADR 0009).

## The ADR text (step 4 above)

One decision per unit. Write it at classification, while you hold the context: only what the removed unit says and what the code verifiably shows. Its body is never edited afterwards (`S32`).

- `adr_title:` the decision, in a few words.
- `adr_text:` the body, as `| ` lines: the sections `## Context` (the situation and the forces: what the removed text said about why), `## Decision` (what was chosen; the rejected alternative, where the text names one) and `## Consequences` (what follows for the code and the documents that remain).

The runner does the rest. It numbers the ADR (the next free number in `adr_dir` at the batch baseline, in unit order), names the file `<adr_dir>/<NNNN>-<slug>.md` from the title, and writes the header — `# NNNN — <title>`, `Status: accepted`, `Date:` the baseline's commit date — above your body. Leave `adr:` out: the runner derives the path.

```
@@ 9 c81d5f02
disposition: historical decision → ADR
basis: sessions use opaque tokens because JWT revocation needed a deny list
adr_title: Opaque session tokens instead of JWT
adr_text:
| ## Context
|
| Logout had to revoke a session at once. A signed JWT stays valid until it expires, so revocation needed a deny list on every request.
|
| ## Decision
|
| Sessions use opaque tokens stored server-side. JWT was rejected for the revocation cost.
|
| ## Consequences
|
| Every request reads the session store (`auth/session.js`).
```

## Evidence, in one line each

- Code citation: `path:line` plus what is there.
- Absence claim: `identifier legacyAuth does not occur in the baseline tree` — search before you write it.
- External: name the source of truth (`GDPR Art. 5`, `customer contract §4`, `SAP Business One API`).
