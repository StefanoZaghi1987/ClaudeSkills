# 0029 — The runner's commits stay recognizable under the owner's commit conventions

Status: accepted
Date: 2026-10-15
Positions: answers the open question `CONSOLIDATION_COMMIT_MARK` in the design notes (O9) — the subject prefix is a configurable slot, and recognition no longer rests on the subject alone. Refines ADR 0015: the chain reads the runner's commits from git history.

## Context

Every commit the runner makes carries a fixed `consolidation:` subject, and every gate that
delimits a review unit — the ancestry check, the history walk, the batch chain — recognizes the
runner's commits by that prefix. Two ordinary repository setups break it:

- **commitlint under husky** rejects `git commit` outright: `consolidation` is not an allowed
  type, so `batch-next` dies with "git commit failed (a hook?)" and the printed undo advice can
  never fix it.
- **A `prepare-commit-msg` hook** that prefixes a ticket id (`[PROJ-1] consolidation: …`) lets
  the commit through and then fails `baseline-ancestry-check`, whose first-commit test is a
  `startswith` on the subject.

Nothing let an owner change the prefix, and no commit was recognized without it.

## Decision

- **`commit_prefix`** is a `.consolidation.json` key (default `consolidation:`). One word, ending
  in `:`, naming consolidation; anything else is refused for the default. Only the committed
  config may set it — an uncommitted one falls back to the default and fails
  `config-bound-check`, like every other loosening (ADR 0012): the prefix decides which commits
  the gates take for the runner's, so a local override could hide a functional commit inside a
  review unit. The prefix opens every subject the runner composes: the unit's commit and the
  `batch-revert` line's.
- **A commit is recognized by its message, not its subject alone.** A commit is the runner's
  when its message embeds a record, or carries the `Consolidation-Unit:` trailer (the content
  commit of the `file` record channel carries it; the record commit embeds the record as
  before). Whatever a commit hook does to the subject leaves both in place.
- The revert subject is matched also **after a leading tag** (`[PROJ-1] consolidation: revert
  batch …`), for the same hook reason.
- `mechanical:` stays as it is: a subject prefix on commits the owner makes by hand.

## Consequences

A repository under commitlint types the runner's commits (`chore(consolidation):`); a
ticket-prefixing hook no longer breaks the unit gate or the chain. The default subjects are
unchanged, and history written before this decision reads as before: the old prefix remains a
recognition mark, and old commits embed their records. A subject that neither carries a
recognized prefix nor sits on a runner-composed message is what it always was — a functional
commit inside the review unit, refused (S164). The self-test runs the prefixed flow, the
hook-tagged flow and every refused `commit_prefix` value.
