---
key: user-manual
audiences: [users]
default_prefix: U
ids: []
variants: [default]
chapters:
  default: [introduction, basic_concepts, access, common_functions, functional_area*, role_functions, good_practices, what_to_do, appendices]
appendices: [glossary, env_differences, menu_map]
---

# User manual

For the people who use the solution. Task-oriented: a reader looks for "how do I…". It answers
*how to use*; problems point to the troubleshooting manual, settings to the configuration guide.

Chapter names come from the language pack (`chapters.<key>`); `functional_area*` means one
chapter per functional area, named with the pack's pattern (`Funzioni di {area}`), as many as
the solution has.

## Chapters

| Key | Content |
|---|---|
| introduction | what it is and why it exists; who it is for (profile → what they do → chapters, with reading time); identity table; environments and how to tell them apart; how to use the manual; essential terms |
| basic_concepts | the domain model in the user's words: objects, states and life cycle, dates, priorities, roles |
| access | how to open it, first access, profile, menu, session expiry, logout |
| common_functions | what works the same on every page (grids, search, filters, export, save/cancel) |
| functional_area* | each page: purpose, layout (figure), fields and columns, commands, step-by-step procedures, rules |
| role_functions | what only some roles do |
| good_practices | per role |
| what_to_do | situation → what to do → whom to ask; points to the troubleshooting manual |
| appendices | glossary; differences between environments; menu → page → permission map |

## Rules of this type

- Procedures are numbered steps, one action per step, with the UI labels in **bold** exactly as
  on screen and menu paths with `›`, followed by the expected result.
- A feature present only in one environment carries a badge — `[[SOLO TEST]]`, `[[PRODUZIONE]]`
  (texts from the pack's `badges`) — in its heading and in the text; the introduction explains the
  badges once.
- Separate what the system enforces from good organizational practice, and say which is which.
- Screenshots: those the user supplied or the sources contain, captioned; a missing one is an
  open item, never an invented screen.
- No architecture internals (servers, logs, views) beyond what a user needs.

Optional IDs: `U01` for numbered procedures referred to from other documents of the set.
