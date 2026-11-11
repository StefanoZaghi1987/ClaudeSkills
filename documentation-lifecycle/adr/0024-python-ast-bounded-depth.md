# 0024 — A Python file the 3.12 grammar cannot parse within 1000 levels is never proved

Status: accepted
Date: 2026-10-15
Positions: refines ADR 0001 — the `facts:` field and the certainty of a scan are script-owned, so they are the same on every platform and every supported Python

## Context

Three runner verdicts rest on parsing Python: the `code-like` fact of a comment, the docstring scan of a `comment-fine` pass, and the check that an applied Python file still compiles. Each used the interpreter's own grammar and treated a `RecursionError` as "does not parse". Both vary between machines:

- CPython stops at a depth that depends on the operating system's stack, the version and the caller's own depth: a chain of unary minus parses to 2994 levels on Windows with 3.13 and to 5968 on Linux with 3.14; an attribute chain to 2994 and 130388. The self-test check "a deeply nested expression is not code-like" passed on Windows and failed on Linux.
- A newer interpreter accepts syntax an older one rejects: `except A, B:` compiles on 3.14 and not on 3.12, so the compile check put an obligation on the applied file on one machine and none on another.

`facts:` is script-owned and re-measured by `record-check` and by the history walk, so a record written on one machine could fail identity on another.

## Decision

The runner parses Python with the 3.12 grammar (`feature_version=(3, 12)`), from the file's bytes, and measures the depth of the tree without recursion. One rule then covers every verdict:

- A Python file that does not parse, or nests deeper than 1000 AST levels, cannot be proved: its code-invariance result is `equal-uncertain`, and its unit runs the test suite — the escape every language the runner cannot prove already takes. Under `comment-fine` such a file is also scanned line by line, as before.
- A comment body nested deeper than 100 AST levels, or that only a newer grammar accepts, is not code-like.
- The applied file's compile check uses the same grammar and the same bound; a baseline that does not compile under it is no proof obligation, and the suite stands in for it.

When the interpreter itself stops on a deeper text, the verdict is the same. The caps sit far below every limit measured (2994 at the lowest, 200 for brackets, which the parser fixes everywhere) and far above real code: over 4090 files the deepest tree was 89 levels, the 99.9th percentile 33. The self-test parses a chain of every kind at exactly 1000 levels on every platform of the CI matrix.

## Consequences

The same text gets the same `code-like` fact, the same certainty and the same compile verdict on Windows and Linux, and on every supported Python. Every Python file is now parsed once, in a `comment` pass too. A file that uses syntax newer than 3.12, or has a syntax error at the baseline, runs the suite instead of the compile check: the safety net stays, on every interpreter alike. A committed record whose fact came from a parse deeper than the caps, or from newer syntax, fails the history walk once after the upgrade; such a comment is pathological, and the pass that made it runs again. `feature_version` is best-effort: a construct a future CPython adds without a version check would still parse.
