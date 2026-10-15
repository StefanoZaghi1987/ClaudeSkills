# 0011 — The gate observes a provider floor itself

Status: accepted
Date: 2026-10-06
Positions: resolves O11; refines S92, S2 and S6

## Context

`S92` credits the scope cross-check as a floor only when the target set it compares against did not arrive by way of the agent's narration, and left open (`O11`) whether the gate re-runs the selection or reads a committed copy of its output. The runner read a file passed as `--target-set` and took the floor's observation state from the record header's `floor_observed`. Both are written by the agent: the second review round showed a hand-written target set agreeing with a widened scope, and a header `floor: graph` with a fresh `floor_observed`, passing the cross-check and the staleness check. A committed copy narrows this but does not close it — the file is still the agent's until it is committed, and a commit date is not the floor's build state.

## Decision

For a `graph` or `exclusion-inventory` floor the gate re-runs the provider itself — `knowledge_graph` or `exclusion_inventory`, from the config the record is judged with — and cross-checks the declared scope against that output; a `--target-set` file is then ignored. The floor's observation state is the provider's own `# observed: <ISO date or sha>` output line: present, it is the date `floor-staleness-check` measures against the baseline (`S6`); absent, the build state is not observable (`S2`) and the staleness check is advisory, never ok. The header's `floor_observed` no longer evidences anything for a provider floor. A provider taken from an uncommitted config is agent-authored and floors nothing: the cross-check still runs, as an advisory. A self-report floor keeps the `--target-set` file, whose cross-check was never credited as a floor.

## Consequences

`S92` names the re-run, and `O11` is closed. The runner's `target-set` output stays the agent's working list for choosing a scope. A provider must be cheap and deterministic enough to run once per gate, and it is responsible for reporting its own build state; one that reports none leaves every pass with a provider floor carrying a staleness advisory. A severance pass whose targets were typed with `--target` declares a self-report floor, since its inventory was not the source.
