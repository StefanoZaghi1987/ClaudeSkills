# 0022 — An untracked `.consolidation.json` is an owner input, not dirt

Status: accepted
Date: 2026-10-08
Positions: narrows the refusal "any working-tree change outside `.consolidation/`" of ADR 0017

## Context

ADR 0017 has `record-fill` refuse "any working-tree change outside `.consolidation/`", and the refusal counted an untracked `.consolidation.json`. That file is the owner's, present on purpose: the owner's workflows run untracked configs to tighten the gates (ADR 0012), and `preflight` and the unit gate's tree check left it out of the dirt they refuse on. `record-fill` alone refused a classification for a file no worker wrote. Commit b1236fa ("record-fill accepts an untracked .consolidation.json, as preflight does") added the exemption.

## Decision

`record-fill` exempts an untracked `.consolidation.json`: the file joins the judgement files it names among the paths allowed to differ from HEAD, and the refusal of ADR 0017 covers what remains — a working-tree change outside `.consolidation/` that is neither. Exactly that path, and only untracked: the exemption is the `??` status line of `.consolidation.json` and nothing else, so a tracked `.consolidation.json` modified in the worktree stays a refusal, in `record-fill` and in the unit gate's tree check alike.

An untracked config is the owner tightening the gates (ADR 0012: an uncommitted config may only tighten), and the record header's `config_sha` binds the record to it; it is never a worker's edit, so the fill treats it as an input, not dirt. ADR 0017's body is append-only, so the exception is recorded here rather than edited there.

## Consequences

A worker classifies in a worktree that carries the owner's untracked config without a refusal no worker action explains. The exemption carries no edit of a committed file: only the untracked config is exempt, and ADR 0012 still bounds what it can do — it tightens, never loosens. The operational restatements — the `runner.md` record-fill row, the `parallel.md` worker step, the design-notes control row — cite this ADR.
