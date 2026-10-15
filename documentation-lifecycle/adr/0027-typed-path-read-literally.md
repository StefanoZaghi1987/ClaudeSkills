# 0027 — A typed path is read literally and must match git's spelling

Status: accepted
Date: 2026-10-15
Positions: adds the rule for a typed path; refines ADR 0001 — a path in a record names the same file on every OS

## Context

The runner turned every path the user types — a scope file, `--target`, a record, `--out`, `escalate --file` — into a root-relative path with `Path.resolve()`. On Windows `resolve()` returns the on-disk case, so `Src/Foo.py` became `src/foo.py` without a word. On macOS it keeps the typed case: the disk read succeeds on the case-insensitive file system, and `git show sha:Src/Foo.py` then finds nothing. On Linux the file is simply not found. `resolve()` also followed a tracked symlink to its target. A path outside the repository came back relative to the directory the user typed it in, not to the root. A `~` the shell left unexpanded created a directory named `~`.

## Decision

The repository root is found top-down among the typed path's ancestors, and only the part above it is resolved, which absorbs 8.3 short names and a symlinked temporary directory. Below the root the path is read as typed: no symlink is followed — not even one that points back to the root — and no file system corrects its spelling. A path is refused on every OS, the refusal naming the right spelling, when git or the disk spells it otherwise:

- a tracked path whose spelling is not one the index holds for it, compared in Unicode NFC and case-insensitively with `lower()` — two tracked paths only case apart are both git's, and each is accepted as spelled; `casefold()` is not used, since no file system folds `ß` into `ss`;
- an existing path whose part is not spelled as its directory lists it, in another case or as a Windows alias such as an 8.3 short name.

Outside a repository only the disk is asked. A path outside the repository comes back absolute, from both helpers that print root-relative paths. A leading `~` — typed and left unexpanded, or in the configured `intake_path` — is the home directory.

## Consequences

A path means the same file on Windows, macOS and Linux. A miscased or aliased path that Windows used to correct silently is now refused, with the spelling to use. A symlink in scope is judged as the link git tracks, not as its target.
