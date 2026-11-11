# 0025 — Printed command lines target POSIX sh

Status: accepted
Date: 2026-10-15
Positions: refines S194 and the printed line of ADR 0021 — the revert subject the chain accepts is unchanged

## Context

The runner prints command lines for the agent or the owner to run: the `next:` and `undo:` lines of `apply` and `batch-next`, and the line of `batch-revert`. The quoting helper claimed to quote "for Git Bash and PowerShell alike" and wrapped a word in double quotes, escaping `"` as `\"`. Neither shell reads that form safely: inside double quotes both expand `$` and the backtick, and PowerShell does not take `\"` as an escape; the lines join commands with `&&`, which Windows PowerShell 5.1 rejects. The self-test ran the lines through `shell=True`, which is `cmd.exe` on Windows and `dash` on Linux, so neither target shell was exercised.

## Decision

Every printed line is for POSIX sh. That is the shell Claude Code's Bash tool runs: Git Bash on Windows, bash or sh elsewhere. A word that needs quoting is single-quoted as `shlex.quote` does, the `batch-revert` commit subject included. The self-test runs each printed line under a POSIX sh on every platform — the one on `PATH`, else the one Git for Windows installs — and checks that a path holding `$`, a backtick and both quote characters reaches the command byte for byte.

## Consequences

A printed line runs verbatim in Git Bash and in any POSIX shell, whatever the path holds. It is not a PowerShell or `cmd.exe` line: a user in those shells runs it through Git Bash. The revert commit's subject, which the batch chain accepts (ADR 0021), is the same text; only its quoting in the printed line changed.
