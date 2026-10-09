# 0020 — Duplicates and contradictions within one document are consolidation grounds

Status: accepted
Date: 2026-10-08
Positions: reverses part of S46 — the removal grounds of a `document` pass gain `duplicate → delete`, and frozen units gain `conflicts:`; refines S54, S60, S73, S89, S173 and S185

## Context

`S46` held every removal in a `document` pass to four grounds plus `condense` under a ruling, because the regenerability test must not reach prose. Real passes met two situations that ground set cannot name. A document states a rule it already states elsewhere — a paragraph kept beside the rewrite that replaced it — and the pass can neither delete the twin nor honestly call it `obsolete`: its subject is present and current. And two frozen units of one document contradict each other; the panel received the same question twice, once per unit, and the owner's answer could land on only one of them.

## Decision

- **`duplicate → delete`, within one document.** A `document` pass may delete a unit because another unit of the same file states its rule and the batch keeps that one. It requires a basis naming the duplicated rule and the field `of:` — the kept unit's id, a unit of the same record and file whose disposition retains it — and takes no edit: the unit is removed whole. The ground is duplication against a unit the record can name, not rebuildability; the reconstructor standard stays out of prose (`S46`).
- **`conflicts:` on a frozen unit.** A frozen unit (`contradicts code → suspected defect`, `not verifiable`) may name one other unit of the same record and file it disagrees with, which itself carries no `conflicts:`. `escalate --from-record` raises one panel entry carrying both texts, and raises the partner none. The owner rules once; the ruling may name both units (`--also-fingerprint`, ADR 0009).
- **Cross-document stays outside.** Between two documents neither ground reaches: one dated plain intake line names both files and lines, and no disposition follows from it (`O5`).

## Consequences

`S46`'s removal-grounds sentence names the new ground and its panel question; the core of `S46` stands — the test fixed for a reader of a source file still classifies nothing in prose. A duplicate costs one judgement and no edit, and the pair stays inspectable in the record: the kept unit carries its own disposition, classified on its own merits. One contradiction is one panel question, and the answer binds both texts.
