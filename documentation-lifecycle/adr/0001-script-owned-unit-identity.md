# 0001 — Script-owned unit identity and the replay check

Status: accepted
Date: 2026-10-06
Positions: S173, S174 (amends the reading of S85, S88, S89)

## Context

The v1 runners checked agent-written data against agent-written data. The agent wrote each entry's line range; coverage compared entry counts per file; removal authorization trusted the ranges. A single entry `lines: 1-7, regenerable → delete` authorized deleting a whole file of code, and every gate passed. Omission plus duplication passed the count. Added lines were checked by no gate. In real use (GammaBot TASK-0014) agents wrote a driver script per review unit to produce records and edits, and repeatedly failed gates on ranges computed after an edit, wrong baselines, lost indentation, merged lines and swallowed blank separators.

## Decision

The script owns unit identity and file edits; the agent owns only judgement. `record-init` enumerates the units at the baseline and writes the header and one stub per unit (reference, lines, span, fingerprint). The agent fills disposition, basis and, where required, new text, claims, ruling and the To-be-confirmed item. `apply` performs the rewrite from the record. Coverage compares the record with a fresh enumeration field by field. The replay check — HEAD equals apply(baseline, record) in scope, and nothing else changed except declared outputs — is the primary review-unit gate.

## Consequences

Every gate now compares agent output with a recomputation, so each is a control rather than a self-report. Added lines are covered. Per-unit driver scripts are no longer written. Reflow commits no longer arise for comment passes. The agent can no longer hand-tune an edit outside what a disposition expresses; a need the dispositions cannot express is a design question, not a workaround.
