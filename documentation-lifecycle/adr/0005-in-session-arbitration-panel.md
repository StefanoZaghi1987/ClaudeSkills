# 0005 — In-session arbitration panel

Status: accepted
Date: 2026-10-06
Positions: S180 (operationalizes S12, S16)

## Context

Frozen and escalated units wait for a human ruling; a later pass applies it. Across sessions this latency dominated `document` passes. In practice the owner already ruled in panels during the session, and the agent transcribed the rulings into the intake by hand.

## Decision

At the end of classification the agent presents every frozen and escalated unit of the review unit to the owner in one batch, with evidence and a closed set of rulings. `escalate --rule` records each answer in the owner's words, with state and ruling sha. A later review unit applies it as `ruled → apply`. Unanswered items stay `open`.

## Consequences

Same-session turnaround, with the human still the arbiter. The agent never phrases a ruling the owner did not give. Asynchronous arbitration remains available.
