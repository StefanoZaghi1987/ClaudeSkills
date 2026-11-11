---
key: troubleshooting
audiences: [users, technical]
default_prefix: S
ids: [S, A, Q]
variants: [application, scheduled-process]
chapters:
  application: [summary, good_use, what_to_do, report_problem, architecture, key_concepts, diagnosis_method, cards, restore_procedures, known_behaviours, historical_cases, periodic_checks, appendices]
  scheduled-process: [summary, architecture, schedule, processing_logic, key_concepts, diagnosis_method, cards, restore_procedures, known_behaviours, interdependencies, historical_cases, periodic_checks, appendices]
appendices: [app_queries, app_call_map, app_messages, app_code_refs, glossary, references]
---

# Troubleshooting manual

For the people who keep a solution running: the users who must react to errors (Part A) and
the technical staff who diagnose and repair (Part B). It answers *how to diagnose and repair*;
how to use the solution belongs to the user manual, how to set it up to the configuration guide.

Chapter names come from the language pack (`chapters.<key>`); the shared frame (header, summary,
depth, IDs) is in `references/document-types.md`.

## Variants

| Variant | When | Differences |
|---|---|---|
| `application` (default) | people use the solution | two audiences: a `::: part` divider (`part_a`) before *good_use*, another (`part_b`) before *architecture* |
| `scheduled-process` | a job, an integration, a service with no direct users | one audience, no parts; *schedule* and *processing_logic* describe when and how it runs; *interdependencies* gives the chain with the other processes |

Write the variant in the front matter (`variant: scheduled-process`). A scheduled process takes
its own card letter, from the job's name (`L` for a price-list job, `T` for exchange rates): the
first letter of the name that no other ID family uses — never `S`, `A`, `Q`, `P`, `U` or `C`
(`ArchiveShippedLabels` → `R`, from "aRchive"). Several linked processes from one session: one
document each, each with its own letter (see the shared frame).

## Chapters

| Key | Content |
|---|---|
| summary | the shared summary frame, with the **quick symptom index** (symptom → first action → card IDs) |
| good_use | grouped rules; each one avoids a known problem (the reason is in Part B) |
| what_to_do | table: situation or message → what to do now → when to call support |
| report_problem | table: information → why it is needed |
| architecture | components; environments, servers, addresses; call flow; data (tables, views); source code and releases |
| schedule | *scheduled-process*: when it runs, where it is scheduled, how long it takes, how to run it by hand |
| processing_logic | *scheduled-process*: what it reads, computes and writes, step by step |
| key_concepts | the internal mechanisms behind most problems (state machines, chains of operations, sessions, caches, platform services) |
| diagnosis_method | levels from cheap to invasive (information and reproduction → client console → application logs → platform consoles and logs → database), each with where to look and what it tells |
| cards | grouped by area; one card per symptom (below) |
| restore_procedures | numbered step procedures the cards refer to, from the least to the most invasive |
| known_behaviours | table: ID, behaviour, effect, workaround (cards) — derived from the code |
| interdependencies | *scheduled-process*: dependency chain and timing with the other processes |
| historical_cases | dated cases: symptom, diagnosis, solution, lesson (ticket numbers) |
| periodic_checks | deadlines to watch; checks after a platform upgrade, after a release, on a new or restored test environment; periodic checks |
| appendices | A diagnostic queries (read-only) · B call map · C messages and error codes · D code references of the known behaviours · E glossary · F documentation and references |

## The card

Every card has the same fields, in this order; the label words come from the document language
(Italian shown):

```markdown
### S12 · "Il lotto non è disponibile"

::: card
Sintomo: what the user or operator sees, with the exact message.
Chi interviene: Operatore (prima azione), poi ICT.
Cause probabili:
- most likely first; cite known behaviours (A02) and other cards (S07)
Come verificare:
- concrete checks: console, log path, query Q8, platform console
Come risolvere:
- concrete actions; procedures by number (procedura 9.3)
Riferimenti:
- optional: ticket, code reference, related document
:::
```

English labels: Symptom · Who acts · Probable causes · How to verify · How to solve · References.
"Who acts" may be dropped when one team does everything — say so once in the chapter
introduction. "References" is optional.

## Depth

*Essential* keeps the frequent cards only, without the diagnosis internals, the code references
appendix and the historical detail (see the depth table in the shared frame).
