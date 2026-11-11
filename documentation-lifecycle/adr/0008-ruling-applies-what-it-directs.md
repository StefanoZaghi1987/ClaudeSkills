# 0008 — A ruling applies only what it directs

Status: accepted
Date: 2026-10-06
Positions: refines S125, S180 and ADR 0005

## Context

`ruled → apply` removes a unit when it carries no `edit`. The panel's answers were all recorded through `escalate --rule`, so an answer that said *keep* — **Code is wrong** on a suspected defect, **Keep** on a load-bearing reference — reached classification as a ruled entry and deleted the very text the owner had chosen to keep. This contradicted S125, under which a suspected defect resolves to `ruled` only when the defect was fixed or the documentation corrected.

## Decision

`ruled → apply` applies only what the ruling text directs: removal or replacement. A ruling to keep is never `ruled → apply`. **Code is wrong** records no ruling at all — the entry stays `open` until a fix lands and closes it. **Keep** on a load-bearing reference is recorded and the unit is `retained`, its basis citing the ruling. The runner enforces the binding: every `ruling:` must cite an intake entry of this unit (fingerprint and reference), so a keep-ruling cannot be cited to authorize a removal.

## Consequences

The panel table in `reference/escalation.md` and step 1 of both `classify.md` files state the mapping. ADR 0005's blanket "a later review unit applies it as `ruled → apply`" is narrowed by this record to the rulings that direct a change.
