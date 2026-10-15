# 0026 — A provider command is an argv array

Status: accepted
Date: 2026-10-15
Positions: refines ADR 0011 — the gate re-runs the provider; this fixes how

## Context

`knowledge_graph` and `exclusion_inventory` are commands in the committed `.consolidation.json`. The gate re-runs them on whatever machine judges a record (ADR 0011). The runner ran each as a string with `shell=True`: `cmd.exe` on Windows, `/bin/sh` elsewhere. A command written for one shell — `python tools\graph.py`, `type`, single quotes, `python3` — fails on the other, so a floor observed on one platform could not be re-observed on the other.

## Decision

A provider command may be a JSON array. The runner runs it as an argv, without a shell, from the repository root, and replaces `{python}` in each element with the interpreter that runs the runner. `["{python}", "tools/graph.py"]` therefore runs alike on Windows and Linux. With no shell, Windows does not resolve a `.cmd` or `.bat` program by its bare name, so an array names it with its extension (`npx.cmd`); the refusal to start says so. The string form stays, for the configs that use it: it runs in the platform shell, and `{python}` in it becomes the interpreter quoted for that shell — always double-quoted for `cmd.exe`, which also splits on `&`, `^` and `|`. A value that is neither a string nor a non-empty array of strings is ignored with a warning, as an unknown key is; so is an `intake_path` that is not a string. A program the array names that cannot start stops the command with its name.

## Consequences

A team on mixed platforms writes its providers as arrays and gets the same floor everywhere. `config_sha` hashes the config text, so a config is bound as before, and ADR 0012 still limits an uncommitted config: its providers floor nothing. The string form is not portable, and the documentation says so.
