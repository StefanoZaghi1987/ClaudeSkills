---
key: maintenance-procedure
audiences: [administrators]
default_prefix: P
ids: []
variants: [default]
chapters:
  default: [introduction, prerequisites, affected_items, procedure, verification, rollback, if_skipped, references]
appendices: []
---

# Maintenance procedure

A short guide for **one** periodic or occasional task — renewing application client secrets,
renewing a certificate, the yearly calendar, restoring a test environment. It is read by the
person who performs the task, often a year after the previous time, so it must stand alone.

Chapter names come from the language pack (`chapters.<key>`).

## Chapters

| Key | Content |
|---|---|
| introduction | what the task is, why it is needed, when (frequency, trigger, deadline), who performs it, time needed |
| prerequisites | rights, tools, accesses, people to involve, a backup when data changes, a maintenance window |
| affected_items | every item the task touches, with its deadline (table: item · where · expires · owner) |
| procedure | numbered steps, one action per step, expected result after each step; `::: warning` before a risky step; test environment first when possible |
| verification | how to prove the task worked (what to open, what to look for) |
| rollback | how to go back when a step fails |
| if_skipped | what breaks, when, and how it shows (the symptoms the troubleshooting manual lists) |
| references | related documents, vendor pages, tickets |

## Rules of this type

- Typically 3–8 pages; no summary chapter: the introduction carries the identity of the task.
- Deadlines come from the sources or the profile's "Deadlines to watch" — with the date they were
  verified. A deadline the sources do not give is an open item.
- Never a secret value: write where it is kept and who can obtain it, and where the new value is
  configured.
- When the task belongs to a solution that has a configuration guide, the guide points here
  instead of repeating the steps.
