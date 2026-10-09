# Escalation, the owner panel, and rulings

The intake is `~/.claude/escalations.md` (or `intake_path` in `.consolidation.json`): one dated line per observation, fields in a trailing bracket. Only the runner writes structured lines; it holds a lock while it writes, so parallel sessions are safe.

```
- 2026-10-06 `src/a.py:20` — PCI-DSS rule, unverifiable from file (frozen unit, byte-for-byte) [kind=unverifiable-statement state=open observed=a1b2c3d fingerprint=9f2c14e8 context=consolidate-comment-U-C1]
```

| Field | Meaning |
|---|---|
| `kind` | `suspected-defect`, `unverifiable-statement`, `load-bearing-reference`, `obsolete-citation`, `standing-ruling` |
| `state` | `open`, `ruled`, `ruled-external` (unverifiable only: true but unconfirmable here), `applied`. An entry is always created `open`; only `escalate --rule` rules it, appending the owner's words after a `— RULED <date> (owner…):` marker; only `escalate --close-applied` closes a `ruled` entry to `applied` |
| `fingerprint` | the unit's content key at the baseline. The entry follows its text when the file above it changes; a reworded text earns a fresh entry |
| `ruling` | the sha the ruling was recorded at; when the intake lives inside the repo, it must name a commit there |
| `units` | the further units a ruling covers (ADR 0009), all of the entry's own file; the marker reads `(owner, units=<digest>)`, and a list that no longer matches its digest binds nothing |
| `applied` | `fingerprint:unit-id@baseline7` for each unit that applied the ruling and passed its gate (ADR 0014) |
| `tbc` | the key of the `## To be confirmed` item the unit's `tbc:` raised. The item binds to this entry by its text (`S65`) and gets no entry of its own (`S66`) |

A `ruled → apply` cites only an owner ruling: a `suspected-defect` or `unverifiable-statement` entry in state `ruled` that carries the marker. An entry of any other kind, or a ruled entry without the marker, authorizes nothing. A `## To be confirmed` item cites the entry of the paragraph that raised it, in state `ruled`, `ruled-external` or `applied`: the owner answered its question, so the item is removed (`S64`).

Read-before-append keys on the fingerprint (or the reference where none exists): an entry already present suppresses a second one, so repeated passes are idempotent. An `obsolete-citation` is counted instead (`occurrences=`, `latest=`).

## Commands

Pass `--fingerprint FP` from the record stub wherever a command names an entry. Without it the runner fingerprints the line under the default unit rule, which misses an entry raised under `document-block` or `comment-fine`.

| Need | Command |
|---|---|
| Escalate every frozen unit of the record (step 6) | `escalate --from-record R` |
| One observation by hand | `escalate --file F --line N --baseline SHA --kind K --divergence TEXT` |
| Record the owner's ruling on an open entry | `escalate --rule --file F --line N --fingerprint FP --ruling-text "<the owner's words>"` (add `--external` for ruled-external; repeat `--also-fingerprint FP` for each further unit the ruling covers, ADR 0009) |
| Close the rulings a review unit applied, after its `gate --unit` passed | `escalate --close-applied --record-from-commit C` — `C` is the unit's record-carrying commit |
| Record a standing (class) ruling | `escalate --standing --ruling-text "<the owner's words>"` → prints `SR-xxxxxxxx` |
| List standing rulings | `standing-rulings` |
| Consume an obsolete-citation event at the next pass | `escalate --file F --line N --fingerprint FP --consume` |

## The owner panel (step 6)

After `escalate --from-record`, present every frozen unit of the master record (in the manual flow, of the review unit) to the owner in one panel of AskUserQuestion calls (up to four questions per call; repeat for more). Leave out every unit for which `escalate --from-record` answered `suppressed`: its question was already asked. A `ruled-external` entry is terminal (`S61`); an `open` entry waits for the owner or for a fix; a `ruled` entry has its answer — when it directs an edit, set the unit to `ruled → apply` with the `ruling:` line the runner prints; a `## To be confirmed` item is the open question of its paragraph's entry (`S66`). None of them is asked again. An `applied` entry never suppresses: its ruling is spent, and the unit gets a fresh entry. Each question shows `file:line`, the unit text and your basis, with these options:

| Kind | Options |
|---|---|
| suspected defect | **Code is right** — the text is rewritten to the code (`ruled → apply` with the new text) · **Code is wrong** — keep the text: record nothing, the entry stays `open` until the code is fixed · **Leave open** |
| unverifiable statement | **True** — the statement stays as it is (`--external`: `ruled-external`, never asked again); a True that moves the sentence — out of `## To be confirmed` into the body — directs edits and is recorded without `--external` · **False or stale** — remove it (`ruled → apply`) · **Leave open** |
| load-bearing reference | **Sever** · **Rewrite to a surviving target** · **Keep** — the reference stays (`retained`, basis cites the ruling; never `ruled → apply`) · **Leave open** |

For each answer that directs a change — removal, rewrite, sever, rewrite-to-target — run `escalate --rule … --ruling-text "<the owner's choice and any note, verbatim>"`. **Code is wrong** records no ruling: the entry stays `open`, and a fix that lands closes it later. A ruling to **Keep** is recorded but is never `ruled → apply`, which would remove what the owner chose to keep (ADR 0008). A pure **True** is the one keep recorded with `--external`. When one answer directs edits beyond its own unit — a **True** whose sentence goes into the body, so the section item is removed *and* a body unit is rewritten — record it as `ruled`, never `ruled-external`: `ruled-external` authorizes no `ruled → apply`, and `--rule` refuses `--external` together with `--also-fingerprint`. Record the further unit's fingerprint with repeated `--also-fingerprint` — a unit of the same file, which `--rule` verifies: the entry then carries `units=…`, and each listed unit cites the ruling (ADR 0009). Phrase nothing the owner did not say. In a batch, write each unit an answer directs as `ruled → apply`, with `ruling: <fingerprint>` (and `edit:` when the ruling gives new text), in a correction file, put it into the master record with `record-fill` (SKILL.md step 6), and run `gate --pre --batch` again: a later review unit of the same batch applies the ruling (ADR 0013). In the manual flow, the next review unit cites it.

## Closing a ruling

A ruling binds once (ADR 0014). `batch-next` closes the rulings a unit applied as soon as its `gate --unit` passes. In the manual flow, after the review unit that applied a ruling passes `gate --unit`, run `escalate --close-applied --record-from-commit C`. For every entry the record's `ruled → apply` units cite, it adds each unit to `applied=`; it sets the entry to `applied` when the entry's own unit and every unit on its `units=` list are there. An entry without a fingerprint binds by line, which another unit may occupy next, so it closes at once.

Then a later unit with the same fingerprint — an identical comment whose occurrence index shifted onto the ruled one — fails `record-check` when it cites the ruling: escalate it afresh — `escalate` opens a fresh `open` entry for it, and a lookup by fingerprint then finds that entry, not the closed one. The unit that applied the ruling still passes when its gate re-runs.

## Standing rulings

A standing ruling authorizes a class of edits — for example *"comment units of 12 or more lines are condensed; keep every invariant, its reason and every ruling id; recast chronicle in the present tense"*. Record one only on the owner's explicit decision, in the owner's words. Every `condense` entry cites it (`ruling: SR-…`); a `condense` without a ruled standing ruling fails `record-check` (`S178`, `S179`).

## Rule line eleven

Every flag goes to the intake as one dated line naming the file and the divergence. For a spec the project owns, the divergence also goes into that document's `## To be confirmed` section, which `apply` writes from `not verifiable` entries in a `document` pass.
