# 0007 — Test-suite cadence when code invariance is proven

Status: accepted
Date: 2026-10-06
Positions: S175, S182

## Context

In real use the full suite ran after every comment unit. It was the slowest and least stable step: environment timeouts, a shared database tier, and a wrapper that reported success on failure. A comment pass changes no code by intent, but nothing proved it.

## Decision

`code-invariance-check` proves, per file, that the non-comment token stream is identical at baseline and head; `apply` refuses any edit that would change it. When every file in a unit is proven, the suite runs once per batch (`suite_cadence: batch`, the default) rather than per unit; `suite_cadence: unit` restores per-unit runs. A file the lexer cannot prove puts its unit back on the per-unit suite.

## Consequences

The suite leaves the per-unit critical path for proven units. A test that reads source text or line numbers is still caught by the batch run, and per-unit commits locate the culprit.
