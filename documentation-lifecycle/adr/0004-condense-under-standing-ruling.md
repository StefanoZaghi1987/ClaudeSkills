# 0004 — `condense` under a standing ruling

Status: accepted
Date: 2026-10-06
Positions: S178, S179 (amends S42, S46, S54, S60, S73, S89, S119)

## Context

The owner directed on 2026-10-05 that long comments be condensed, keeping invariants, reasons and ruling identifiers. No disposition expressed this; the run created a class-level intake entry and cited it as `ruled → apply`, which cost zero judgements for rewrites that were the agent's judgement. Free rewriting can lose an invariant, and no script can prove it did not.

## Decision

Add `condense`, available only under a standing ruling: an intake entry of kind `standing-ruling`, state `ruled`, with a stable identifier and the keep-rules in its body, created only on the owner's explicit decision. The entry cites the ruling, carries the new text and a claims ledger of everything kept, and counts against the judgement cap at unit weight. In a `comment` pass the new text must be comment text only.

## Consequences

Condensing is possible without per-unit arbitration and without presenting each text as a human ruling. The reviewer checks the new text against the claims ledger. A verbose-but-true spec can be shortened only where the owner ruled the class.
