# 0010 — The runner binds the citation, not the direction

Status: accepted
Date: 2026-10-06
Positions: narrows ADR 0008 and S180

## Context

ADR 0008 closed the failure where a panel answer to *keep* reached classification as `ruled → apply` and deleted the kept text. Its Decision says the runner enforces this: "every `ruling:` must cite an intake entry of this unit … so a keep-ruling cannot be cited to authorize a removal." The citation half is true; the "so" is not. A ruling recorded with `--ruling-text "Keep the comment exactly as it is"` — state `ruled`, right kind, bound to the unit — is accepted by `ruled → apply` with no `edit`: the runner never reads the ruling's direction, because the text is free-form and no script can parse it for keep versus remove without becoming the judge the design assigns to the owner.

## Decision

The runner's enforcement is exactly the citation binding: the entry exists, is in state `ruled`, is of a ruling kind (a consumed citation or a standing ruling authorizes nothing), and is bound to this unit by fingerprint, reference or the `units=` list (ADR 0009). Keep versus apply remains an instruction the operational documents carry — the panel table in `reference/escalation.md` and step 1 of both `classify.md` files — backed by the owner reading the removed lines, not by a gate.

## Consequences

A keep-ruling cited for a removal is a mislabelling the review catches, not a gate failure. Storing the directed action in the ruling entry (`action=remove|replace|keep`) would close it mechanically; that is an owner decision, not assumed here. ADR 0008's enforcement sentence is narrowed by this record.
