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
11. Append every flag to `~/.claude/escalations.md`, one dated line naming the file and the divergence; when the divergence concerns a spec the project owns, also add it to that document's `## To be confirmed` section.
12. Lifecycle detail is in `~/.claude/documentation-lifecycle.md` — 600 lines, so read the section you need, never the whole file.
