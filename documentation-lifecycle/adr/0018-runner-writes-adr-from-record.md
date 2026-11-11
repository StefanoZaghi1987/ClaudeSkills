# 0018 — The runner writes the ADR from the record

Status: accepted
Date: 2026-10-07
Positions: adds S188; refines S173, S186 and ADR 0015

## Context

A `historical decision → ADR` unit named the path of an ADR file, and the single writer wrote that file by hand when `batch-next` stopped for it. The file was the one output of a pass that the runner did not write. The writer chose the number, so two units of one batch could take the same number. The stop cost one more agent turn per ADR, and the writer wrote the ADR long after classification, when the context was gone.

## Decision

The classifier writes the ADR in the record at classification: `adr_title` (the decision, in a few words) and `adr_text` (the body: Context, Decision, Consequences). Such a unit carries no `adr:` path.

The runner derives the path `<adr_dir>/<NNNN>-<slug>.md`. The slug is the title lower-cased, every run of characters outside `a-z` and `0-9` (accented letters included) turned into one `-`, trimmed, at most 60 characters. NNNN is 1 + the highest four-digit number among the files in `adr_dir` at the batch baseline (outside a batch, the record's baseline), plus the unit's rank among the `adr_text` units of the master record (outside a batch, of the record) in unit-id order. `apply` writes the file: `# NNNN — <title>`, `Status: accepted`, `Date:` the baseline commit's date, then the body. `replay-check` fails unless the unit adds exactly that file with exactly that content. `batch-next` never stops for such a unit.

A unit with `adr:` and no `adr_text` keeps the older flow: a hand-written file at that path, which the unit must add.

## Consequences

The runner writes every file a pass changes, ADRs included. ADR numbers of one batch cannot collide, because the master record fixes them. The ADR is written while the classifier holds the context. The replay proves that the file equals the record text. The body is still never edited afterwards (`S32`).
