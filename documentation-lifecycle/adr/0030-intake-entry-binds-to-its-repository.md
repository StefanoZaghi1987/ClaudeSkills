# 0030 — An intake entry binds to the repository that raised it

Status: accepted
Date: 2026-10-15
Positions: refines ADR 0014 — a ruling binds once — by naming *where* it binds. Serves the
shared intake (`intake_path`, one `~/.claude/escalations.md` for every repository of the owner).

## Context

An entry's fingerprint hashes the repository-relative path, the occurrence index and the text.
A fork or a template repository holds the same paragraph at the same path with the same text,
so with one shared intake:

- a ruling given in repository A authorized `ruled → apply` in repository B, sight unseen;
- `escalate --from-record` in B printed "suppressed", so the owner was never asked;
- B's `close_applied` then consumed A's ruling, and A's next twin unit had nothing to cite.

Standing rulings (`SR-…`) are the owner's words about a class of edit, deliberately global; the
binding is for the per-line entries.

## Decision

- Every new per-line entry carries **`repo=<first 8 hex of the repository's first commit>`**
  (`git rev-list --max-parents=0 HEAD`). The first commit is the boundary: a fork or template
  shares its paragraphs with the original while owning its own history, and the root commit
  survives every later rebase.
- **A lookup answers an entry only when its `repo` is empty or equals the current repository's.**
  One predicate, `find_intake`, serves every reader: the raise (`suppressed` or a new entry),
  `--rule`, `close_applied`, `batch-revert`'s re-opening and the record checks. The same
  paragraph in two repositories is two questions and two rulings.
- **An entry without `repo` is legacy and answers everywhere**, for as long as the intake holds
  it: an existing shared intake keeps working, and its rulings keep their meaning.
- Standing rulings carry no `repo`, and a directory with no commits yet binds none.
- A ruling consumed by a twin is re-asked once in each repository; it is not applied twice
  (ADR 0014 keeps holding per repository).

## Consequences

A fork or template repository now asks its own panel question for a paragraph the original
already ruled — the conservative direction, one question per repository. Rewriting a
repository's history down to its first commit (an import squash, `filter-repo`) changes its
identity: its earlier entries read as another repository's and are asked once again. The
self-test raises, rules and looks up the same paragraph across two repositories sharing one
intake, checks the legacy entry still answers, and checks a `## To be confirmed` item of
another repository never suppresses this one's question.
