# 0006 — Directives and license headers are not units

Status: accepted
Date: 2026-10-06
Positions: S176

## Context

The v1 enumerator treated `eslint-disable`, `@ts-ignore`, `# noqa`, encoding cookies, build constraints, coverage exclusions and bundler annotations as ordinary comments, so a removal disposition could delete them. Deleting one changes a build, lint or test outcome without changing a code token, so no token comparison sees the loss. License headers are legal notices.

## Decision

The lexer never enumerates a directive or a license header as a unit, like the shebang. A directive splits its comment group; a group with a license marker is excluded whole. The directive list is extensible per repository (`directive_patterns` in `.consolidation.json`) and a pass never shortens it.

## Consequences

The class of edits the code-invariance proof cannot see is out of the agent's reach by construction.
