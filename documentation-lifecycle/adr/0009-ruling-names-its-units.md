# 0009 — A ruling names the units it covers

Status: accepted
Date: 2026-10-06
Positions: refines S16, S55 and S180; sibling of ADR 0008

## Context

`S64` and `S16` direct that a ruling resolving an open item writes its sentence into the body of the document. But the record's replay check admits no line that no unit's entry carries (`S174`): the body paragraph and the `## To be confirmed` item are two units with two fingerprints, and the A1 binding lets a `ruling:` cite only an entry bound to that one unit. One owner answer — the panel is one question — therefore could not authorize both the item's removal and the paragraph's rewrite, and `S55` spoke of lines "emitted outside the unit", which no record can express.

## Decision

A ruling's intake entry carries an explicit list of the unit fingerprints it covers, written as `units=…` by `escalate --rule` through its repeatable `--also-fingerprint`. A unit whose fingerprint is the entry's own, or is on that list, cites the ruling; every other unit is refused exactly as before. The list extends the binding, it does not weaken it: the kind and state checks are unchanged, so a consumed citation or a standing ruling still authorizes nothing, and the list is written only by the panel flow, never by the record.

## Consequences

`S55` now states that new body text is the edit of a unit. `reference/escalation.md` records the flag, and step 1 of both `classify.md` files accepts a listed unit's citation. One panel answer can direct a change across several units without duplicating entries, and the record stays the single authority for every written line.
