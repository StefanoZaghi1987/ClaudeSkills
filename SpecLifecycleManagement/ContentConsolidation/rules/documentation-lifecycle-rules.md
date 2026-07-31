# Documentation and specification lifecycle — rules

These lines are always in context. They are the whole rule set.

1. Spec / design doc — describes the system now; lifecycle: state.
2. Implementation plan — records an intention; lifecycle: ephemeral.
3. ADR — records one decision; lifecycle: append-only.
4. Code comments — explain the present code; lifecycle: state.
5. Never append a revision to a spec. Edit the sentence.
6. — Because history lives in version control and in ADRs, not in the spec.
7. Delete a comment that restates the code; keep only what the code cannot say about itself.
8. — Because a comment is the only artifact that can lie without a test breaking.
9. Unmarked content is current. Do not annotate a paragraph as verified.
10. Flag rather than rewrite: never resolve a documentation-versus-code divergence yourself.
11. Escalation intake — the single append-only destination for every flag — is at slot `INTAKE_PATH`, unfilled until `O7` closes; while it is unfilled, this line resolves to a guess and the flag obligation of the preceding line has no destination.
12. Lifecycle detail, and everything else, is in `~/.claude/documentation-lifecycle.md` — path conditional on the toolchain resolving a user-scope home path.

## The budget and its arithmetic

| Rule-set line | Lines |
|---|---|
| Taxonomy, one line per artifact | 4 |
| No-append rule on specs | 1 |
| — its justification | 1 |
| Comment policy | 1 |
| — its justification | 1 |
| Unmarked = current | 1 |
| Flag rather than rewrite | 1 |
| Escalation intake location | 1 |
| Pointer to the lifecycle detail | 1 |
| **Total** | **12** |

The line budget is a design constant fixed by fiat, not a calibration input, and is the sole numeric threshold anything in this bundle states as settled (`S116`, `S160`). Any headroom is deliberate slack, not an invitation. The table above is arithmetic, not a directive, and consumes no budget.

Justifications attach to the no-append rule and the comment policy and to nothing else, because those are the two directives that ask an agent to destroy information (`S117`). The remainder are declarative and self-enforcing.
