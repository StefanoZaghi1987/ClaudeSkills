# 0028 — What the runner keeps never crosses the shell

Status: accepted
Date: 2026-10-15
Positions: refines ADR 0025 — the printed lines stay POSIX sh; this decision covers what flows into the runner. Serves S180: a ruling is recorded in the owner's words

## Context

ADR 0025 fixed the lines the runner prints. Two inputs still reached it through the shell, and the shell changed them.

- **The target set.** The procedure saved it with a redirect: `target-set … > .consolidation/B-<n>.targets`. PowerShell decodes a native program's output with the console code page and writes it again in its own encoding, so a path holding `è` reached the file changed, and `scope-cross-check` then failed with "declared scope not in the target set". A redirect typed in a subdirectory also wrote the file outside the record directory, where every gate counts it as a change to the tree.
- **The owner's prose.** Rulings were passed as `--ruling-text "<the owner's words>"`. Inside double quotes bash and PowerShell both expand `$` and the backtick, so a ruling that names `` `TODO` `` was recorded without that word while `escalate` exited 0 — and the record claims the owner's words verbatim. `--divergence` and `--narrowing-reason` take prose the same way.

A rule telling the agent to avoid these shells works only while the agent obeys it every time.

## Decision

What the runner keeps reaches it through a file, written by the runner itself or by the agent's file tools, never through a shell redirect or a quoted argument.

- `target-set --batch-id B` writes `.consolidation/B.targets` at the repository root itself, from any directory, and prints `wrote: <path>`; `--out PATH` names another file under `.consolidation/` only. Without either the command prints to stdout, as before.
- `--ruling-text-file`, `--divergence-file` and `--narrowing-reason-file` read the prose from a UTF-8 or UTF-16 file (`read_text_file`, the reader for files a user's shell or editor wrote). A line break becomes a space, as the intake holds one entry per line. Each refuses its inline twin and an empty file. The procedure writes the owner's words with the Write tool to a file under `.consolidation/`, which the gates exclude.
- `--scope-file FILE` takes the scope one entry per line wherever `--scope` is taken, past the 32,767-character command line of Windows.
- The runner's own commits pin `i18n.commitEncoding=UTF-8`, and every git call it reads pins `i18n.logOutputEncoding=UTF-8`, so a user's legacy encoding setting cannot relabel or re-encode the record a commit message carries.

The inline flags stay and still work; the documented path is the file form. The skills tell the agent to run the runner and every printed line with the Bash tool — Git Bash on Windows — and name the launcher for each OS: `python3` on Linux and macOS, `py -3` on Windows.

## Consequences

A path with non-ASCII characters and a ruling with `$` or backticks are recorded byte for byte on every OS and from any shell. The procedure no longer needs `mkdir -p` or a redirect, and step 2 works from a subdirectory. The self-test checks each case: the target set written at the root from a subdirectory with a non-ASCII path, a ruling file in UTF-8 and in UTF-16, both refusals, a BOM'd intake, and the commit and log encodings under a legacy configuration.
