---
key: release-checklist
audiences: [technical]
default_prefix: ""
ids: []
variants: [default]
chapters:
  default: [introduction, prerequisites, procedure, verification, rollback, references]
appendices: []
---

# Release checklist (an organization's own type)

One document per release of a solution: two to four pages, written by whoever releases, read
by whoever releases next. Front matter: `type: release-checklist`, `toc: false`. The chapter
names come from the Italian pack (Introduzione, Prerequisiti, Procedura, Verifica,
Ripristino in caso di problemi, Documentazione e riferimenti).

| Key | Content |
|---|---|
| introduction | what is released, which version, the date, who releases, the downtime window |
| prerequisites | green build, tests run, backup taken, the ticket of the release |
| procedure | numbered steps: stop, deploy, start, smoke check |
| verification | what to open and what to look for after the release |
| rollback | how to return to the previous version, and when to decide it |
| references | the solution's manuals, the ticket, the build |

Rules of this type:

- Every step carries its expected result; a `::: warning` callout precedes the stop of a service.
- File name: `<Solution> - release checklist - v<x.y>.<ext>`.
- Pass this file to the gate: `check_doc.py <doc>.md --type-def release-checklist.md`.
