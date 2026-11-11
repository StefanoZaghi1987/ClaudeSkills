# 0003 — `stale fragment → strip`

Status: accepted
Date: 2026-10-06
Positions: S177 (amends S42, S49, S54, S60, S73, S89)

## Context

Real passes removed ticket identifiers, dates, review-round stamps and chronicle clauses from comments that otherwise had to stay. The v1 dispositions could only delete or keep a whole unit, so agents disposed such units `obsolete` and retyped them, which hid what changed and invited a rewrite under a removal disposition.

## Decision

Add `stale fragment → strip`, available to `comment` and `document` passes. The new text's words must be a subsequence of the old text's words: words may be dropped and punctuation repaired; nothing may be added, reordered or reworded. The stripped fragments are written into the consolidation commit's message, which is the relocation S49 asks for. It requires a basis and the new text and counts against the judgement cap at unit weight.

## Consequences

The most common real edit becomes provable by a script. Reviewers see exactly which words left and where they went. A strip never reaches into a frozen unit.
