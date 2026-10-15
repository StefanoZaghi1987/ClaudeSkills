# 0014 — A ruling binds once: the `applied` state

Status: accepted
Date: 2026-10-06
Positions: adds S183; refines S66, S119 and S125; sibling of ADR 0009

## Context

A `ruled → apply` binds to its intake entry by fingerprint, a content key: the file path, the unit's text and its occurrence index among identical units. Once the ruled unit is removed or rewritten, an identical comment or paragraph elsewhere in the file shifts its occurrence index and inherits the ruled fingerprint. A later unit could then cite the ruling and remove text the owner never ruled on, and every gate would pass, because the entry was still `ruled` and the fingerprint matched. Nothing in the intake recorded that the ruling had already been used.

## Decision

An entry records the units that applied it. After a review unit passes `gate --unit`, `escalate --close-applied --record-from-commit C` writes `applied=<fingerprint>:<unit id>@<baseline7>` on every entry its `ruled → apply` units cite. When the entry's own unit and every unit on its `units=` list are there, the entry's state becomes `applied`. The ruling binding accepts a citation only from a unit already written on the entry, or from a unit with a fingerprint the entry has not yet seen while the entry is still `ruled`. An entry without a fingerprint binds by line, and another unit may occupy that line next, so it closes at once. A `## To be confirmed` item keeps binding to the entry of its paragraph in any answered state, `applied` included (`S65`).

## Consequences

A ruling authorizes exactly the units it was applied to, and re-running the gate of an applying unit still passes. A twin that inherits a ruled fingerprint is refused and must be escalated afresh, which costs one panel question in exchange for never removing text on a borrowed authority. The intake gains a fourth state; `S66`, `S119` and `S125` name it. The skills add one command after each unit gate.
