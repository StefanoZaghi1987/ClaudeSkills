# 0023 — The runner requires Python 3.12 or newer

Status: accepted
Date: 2026-10-15
Positions: refines ADR 0001 — a script-owned identity is the same on every machine that judges the record

## Context

The runner enumerates Python comment units with the standard `tokenize` module, and proves code invariance on the token stream it gives. Python 3.12 changed how `tokenize` reads f-strings (PEP 701): before 3.12 an f-string is one `STRING` token; from 3.12 it is split into its parts, the expressions in its replacement fields included. A file holding `f"""{a  # note\n}"""` gives one comment unit on 3.12 and none on 3.11, and two different token streams. A record written on one interpreter and checked on another then fails its identity check, or proves code invariance against a different stream. The runner stated "Python 3" and checked no version.

## Decision

The runner refuses to start on an interpreter older than 3.12. It names the version it found and the reason, before it imports the lexer. The three scripts keep to syntax that older interpreters still compile, so the refusal is the message the user sees rather than a `SyntaxError`. CI runs the self-test with Python 3.12 and with the latest Python, on Linux and on Windows.

## Consequences

Every machine that judges a record lexes Python the same way. A system whose `python3` is older needs a newer interpreter (a venv, `uv`, or the distribution's newer package) before it can run a pass. Syntax newer than 3.12 stays a known limit: a file that uses a construct the 3.12 grammar rejects is lexed by each interpreter as it can, and ADR 0024 keeps the parse-based verdicts on the 3.12 grammar.
