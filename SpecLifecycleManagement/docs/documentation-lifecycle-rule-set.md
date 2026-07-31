# Rule set

This file is the artifact that occupies the rule-set location. Its twelve lines are the rule set itself, not a description of one.

---

## The twelve lines

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
11. Append every flag to the escalation intake at `‹intake path — O7›`.
12. Lifecycle detail, and everything else, is in the project overview (`ProjectContext.md`).

---

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
| Pointer to the overview for lifecycle detail | 1 |
| **Total** | **12** |

Per `S116`, the arithmetic is shown rather than asserted. Per `S160`, this budget is the sole numeric threshold stated anywhere in this deliverable; the numerals in the table above are its constituent line counts.

---

## Line composition

Per `S115`, the contents are the artifact taxonomy, the no-append rule on specs, the comment policy, the implicit default, the flag-rather-than-rewrite obligation, and the location of the escalation intake — and nothing else.

| Line | Kind | Source of its content |
|---|---|---|
| 1–4 | Declarative | Compressed index per `S116`: function plus a lifecycle keyword only. The full table is not duplicated. |
| 5 | Directive, destroys information | `S17` `S18` `S19` `S21` |
| 6 | Justification attached to line 5 | `S117` |
| 7 | Directive, destroys information | `S41` `S42` `S43` `S48` |
| 8 | Justification attached to line 7 | `S117` |
| 9 | Declarative | `S95` |
| 10 | Declarative | `S50` `S142` `S143` |
| 11 | Declarative | `S119` `S118` |
| 12 | Pointer | `S116` |

Per `S117`, justifications attach to exactly lines 5 and 7 — the two rules that ask the agent to destroy information — and to no others. Lines 1–4, 9, 10, 11 and 12 are declarative and self-enforcing.

---

## Placeholder

| Placeholder | Open question | What is undecided |
|---|---|---|
| `‹intake path — O7›` on line 11 | `O7` | The intake's concrete path, its format, and its churn-stable unit reference scheme |

No path is invented. Per `S118`, the flag-rather-than-rewrite obligation of line 10 is inert while line 11 resolves to a guess, and a rule that resolves to a guess resolves differently every session.

**Shipping status: this rule set is not shippable until `O7` closes.** `O7`'s three decisions — path, format, reference scheme — are prerequisites of the first shipment per `S118`, `S126`, `S157` and `S167`, decided before the rules ship rather than alongside them.

---

## Single source

This file is the single source for the rule-set location. The project custom-instructions field is replaced by the content of the twelve lines above, verbatim, rather than maintained alongside it.

Two copies of twelve lines, each editable, with no ordering signal between them, is the failure of `S19` and `S20` reproduced inside the artifact whose purpose is to prevent it: two statements of the same rule that can diverge, where the reader has no criterion for preferring one. `S20` fixes the priority — non-contradiction first, brevity second — so the duplication is removed rather than reconciled.

**[toolchain-conditional per `S5`]** Whatever mechanism installs these twelve lines into the rule-set location — a file at a fixed path, a settings field, a frontmatter block, a directory convention — is toolchain-specific. Any cost or capability claim about that mechanism is conditional on the toolchain providing it, and is not asserted here as known.
