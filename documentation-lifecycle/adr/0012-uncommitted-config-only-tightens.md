# 0012 — An uncommitted config only tightens the gates

Status: accepted
Date: 2026-10-06
Positions: refines S81

## Context

Gates judge a record with the `.consolidation.json` of its baseline (A4). An untracked config cannot be read from the baseline, so the record header's `config_sha` binds the record to it — but that binds the record to the config, not the config to the owner. The second review round raised both caps to 9999 and widened `document_exts` to `.py`, so a `document` pass rewrote code through the full gate, which runs no code invariance on documents; re-stamping the header together with the config passed. The owner's own workflows use untracked configs on purpose — a scratch `intake_path` in a replay worktree, the self-test's repositories — so refusing them outright would cost real use.

## Decision

A config that is not the committed one — untracked, or a tracked file modified in the worktree — may tighten the gates and never loosen them. A cap above its default (`REMOVED_LINE_CAP`, `REMOVAL_JUDGEMENT_CAP`, `FUNCTIONAL_DIFF_THRESHOLD`, `ADDED_LINE_CEILING`, `FLOOR_STALENESS_THRESHOLD_DAYS`), a `SPOT_CHECK_RATE` below its default, a non-numeric value, or a `document_exts` entry outside the default list falls back to the default, and `config-bound-check` — part of `gate --pre` and `gate --unit` — fails, naming each value. Loosening a gate takes a committed config. Options that only change procedure or tighten (`intake_path`, `record_channel`, `suite_cadence`, `directive_patterns`) are unaffected; a provider command from an uncommitted config floors nothing (ADR 0011).

## Consequences

Raising a cap without a commit is refused at the gate, which keeps `S81`'s rule that raising the cap is no remedy from having a side door. A replay worktree with a scratch `intake_path` works unchanged. `adr_dir` stays unbounded: a different output directory admits new Markdown files there but no change to an existing one beyond its status line, and bounding it would break the projects whose ADRs live elsewhere.
