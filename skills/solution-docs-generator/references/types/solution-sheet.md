---
key: solution-sheet
audiences: [management, technical]
default_prefix: ""
ids: []
variants: [default]
chapters:
  default: [purpose, users, criticality, owners, architecture_summary, environments, dependencies, deadlines, documentation]
appendices: []
---

# Solution sheet

The identity card of a solution, one or two pages: what it is, who uses it, how critical it is,
who owns it, what it is made of and depends on, what expires, and where the rest of the
documentation is. It suits a tool inventory (one sheet per entry), an onboarding pack, or the
first page of a documentation set.

Chapter names come from the language pack (`chapters.<key>`). Front matter: `toc: false`.

## Chapters

| Key | Content |
|---|---|
| purpose | two or three sentences: what the solution does and for which business process |
| users | who uses it, how often, in which department; peak periods |
| criticality | business and technical criticality with a one-line reason each (what stops when it stops) |
| owners | functional owner, technical owner, supplier or partner; the support channel |
| architecture_summary | one small table of components (component · technology · where it runs) — no internals |
| environments | test and production: addresses, how to tell them apart |
| dependencies | the systems it needs (ERP, identity provider, database, printers…) and the systems that need it |
| deadlines | certificates, secrets, licences, contracts — with dates and the procedure that renews them |
| documentation | the other documents of the set and where they are; source code location; project folder |

## Rules of this type

- Short sentences and tables; no procedures, no cards, no history.
- Criticality is a fact the user or the profile states, never an estimate of the agent: ask at
  the checkpoint when the sources do not give it.
- When a set is written, the sheet is written last, from the same analysis, and lists the other
  documents.
