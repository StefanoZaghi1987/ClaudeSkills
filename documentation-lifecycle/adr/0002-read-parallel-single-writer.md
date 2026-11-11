# 0002 — Read-parallel classification, single writer

Status: accepted
Date: 2026-10-06
Positions: S181 (rewords S8; S9 and S81 unchanged)

## Context

S8 forbade parallelism within a review unit because two concurrent sub-agents produce two baselines, two scopes and two bound counters. Classification — reading every file in scope and judging every unit — is the slowest step of a pass and is read-only. A parallel attempt was declined on 2026-10-06 for three reasons: checking other agents' deletions costs as much as making them; parallel lanes serialize on the test suite; interleaved commits had already caused two incidents.

## Decision

Shard classification across read-only workers under one header. The single writer takes the baseline, writes all stubs (ADR 0001), and splits them by file. Workers fill judgement fields in their own shard only, at the orchestrator's capability tier. `record-merge` rejects changed stubs, unfilled or duplicated stubs, and any source-file change, before any gate reads the record. An optional worker may only downgrade removal-authorizing entries to a retaining disposition. Gates, `apply`, escalation and commits stay with the single writer.

## Consequences

One baseline, one scope, one record and one bound counter: S8's failure cannot arise. The three objections do not apply: no one re-verifies workers beyond the existing gates and human review; workers run no suite; workers write nothing to git. Classification wall-clock drops roughly by the number of shards, bounded by the largest file, and the orchestrator's context stays small. S9 still forbids fanning out across review units.
