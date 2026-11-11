# 0016 — The history walk fails closed over git; its verified cache is local and trusted like the scripts

Status: accepted
Date: 2026-10-07
Positions: narrows the claim "the history walk fails closed" of ADR 0015

## Context

ADR 0015 says the history walk fails closed and that an agent that edits the state changes nothing the gates accept. The walk has no cap, so it keeps a cache: `consolidation-verified` in the git common directory, one line per commit whose records passed the walk, `<sha> <hash of consolidate.py and lexer.py>`. The walk skips a commit the cache lists under the running scripts' hash. A fresh review showed that the agent can compute both values: a line appended for a failed consolidation commit makes the walk skip it, and `preflight` and `record-init` then build on it.

No local cache resists this. Any key the scripts compute, the agent can compute, and the agent can also edit the scripts. Without the cache, every `preflight` and `record-init` replays every record-carrying commit in the history, at a cost that grows without limit.

## Decision

The cache stays. The history walk fails closed over what git holds: the commits, their records and the tree at each commit. The verified cache is local to one clone and has the same trust as the scripts that wrote it: an entry is a speed aid, never evidence. A clone without the cache, or a change of the scripts, replays every record-carrying commit.

## Consequences

ADR 0015's guarantee holds against a shortcut through the files a pass uses — the plan, a part record, the master record, the chain — and not against an agent that forges the cache or edits the scripts; that is tampering with the runner itself, which no check inside the repository can stop. A walk the owner wants to trust without the local cache runs in a fresh clone, or after the cache file is deleted.
