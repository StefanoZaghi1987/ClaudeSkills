# Document types and the shared frame

One method, several document types. Each type lives in its own file under `references/types/`:
its audiences, its chapters in order, its rules. The frame below — header, summary, depth, ID
scheme, document sets — is shared by all of them. A reader who knows one document of a type
knows them all, because every document of the same type has the same chapters in the same
order. Adapt the chapter list to the subject — drop what does not apply, never invent content
to fill a chapter — but keep the order and the names.

## The registry

| Key | Document | Answers | Readers | File |
|---|---|---|---|---|
| `troubleshooting` | troubleshooting manual (variants: application, scheduled process) | how to diagnose and repair | users (Part A), technical staff (Part B) | `types/troubleshooting.md` |
| `user-manual` | user manual | how to use | users | `types/user-manual.md` |
| `configuration` | configuration and maintenance guide | how to set up and maintain | administrators | `types/configuration.md` |
| `maintenance-procedure` | maintenance procedure (one task) | how to perform one periodic or occasional task | the person who performs it | `types/maintenance-procedure.md` |
| `solution-sheet` | solution sheet (one or two pages) | what it is, who owns it, what it depends on | management, newcomers, an inventory | `types/solution-sheet.md` |

Each type file opens with a machine-readable header: `key`, `audiences`, `default_prefix`,
`variants` and the ordered **chapter keys** per variant (`functional_area*` = one chapter per
area). The chapter *names* come from the language pack: `assets/i18n/<lang>.json`, map
`chapters`. Write `type:` (and `variant:` when not the default) in the document's front matter:
`check_doc.py` then checks the chapter order and names.

**Adding a type** takes one file with the same header, plus one name per new chapter key in the
language packs (`chapters`) and the type's names (`types.<key>`); a name that no pack carries
falls back to the chapter key itself. Where the file lives depends on who owns the type:

- **in the skill** (a type every organization can use): `references/types/<key>.md`, with the
  names added to the shipped packs;
- **in the organization** (a type only you write): a file beside the profile — or in the work
  folder when it is a one-off — passed to the gate with `check_doc.py --type-def <file>`. The
  chapter names come from your language pack (`--lang-pack`) or fall back to the keys. A
  `--type-def` file whose `key` matches a shipped type replaces it for that run, so an
  organization can slim a shipped type without forking the skill.

## Choosing the documents: one, some, or all

- The request names one or more types — write those.
- "All" / "the full documentation" / "a documentation set" = the set: **user manual,
  configuration guide, troubleshooting manual and solution sheet** (the profile may define its
  own "all"); a **maintenance procedure** for each periodic or occasional task the analysis finds
  — proposed at the checkpoint, not assumed; in automatic mode, listed in the delivery message as
  documents worth writing next.
- A subject with no direct users (a scheduled job, an integration) has no user manual: propose
  the troubleshooting manual (variant `scheduled-process`), the configuration guide when there
  are settings, and the solution sheet.
- Several subjects in one session (three scheduled jobs that depend on each other): one
  document per subject and type, each self-contained, each with its own card prefix, the
  others in "Related documents".

## Shared frame

### Header (front matter → cover page)

The labels come from the language pack (`fields`); the profile may define its own list and order.

| Field (pack key) | Content |
|---|---|
| title | `<Subject> – <type name>` (type name: `types.<key>.name`) |
| subtitle | one line: what the document covers (default: `types.<key>.subtitle`) |
| `reference` | request or ticket, inventory entry, project code (from the profile) |
| `written_by` | author |
| `version` | `version_line` of the pack (`1.0 del 11/11/2026`); a revision adds one line of what changed |
| `classification` | `depth.complete` or `depth.essential` – the type |
| `audience` | the readers, and which part is theirs |
| `sources` | the session(s) and the kinds of source cross-checked |
| `related` | the other documents of the set |
| `supersedes` | the document or version this one replaces, when there is one |
| notice | `fields.notice` of the pack (no credentials), unless the profile has its own |

Optional, when the profile's template has them: a revisions table (`revisions:`), document
status, confidentiality level, document type, contact person (`cover_layout: form` in the
profile renders them as a form).

Front-matter keys the scripts read: `title` (required), `subtitle`, `lang`, `type`, `variant`,
`version`, `date`, `ref`, `ids`, `fields`, `notice`, `revisions`, `header`, `author`, `toc`,
`toc_levels`, `toc_title`, `style`, `labels` (all in `references/authoring-format.md`).

### Summary chapter (first, except in a maintenance procedure and a solution sheet)

1. What the subject is and why it matters, in two or three paragraphs.
2. An identity table: solution, purpose, users, criticality, owners/contacts, classification,
   audience, sources.
3. "How to use this manual": who reads which chapters.
4. For troubleshooting: the **quick symptom index** (symptom → first action → card IDs).
5. One callout with the single most important thing to know, when there is one.

### Closing material (as applicable)

Periodic checks and checks after changes; deadlines to watch (certificates, secrets, licences,
with dates); glossary; references (where documents, code, folders and tickets are).

## Depth levels

| | Complete (default) | Essential |
|---|---|---|
| Purpose | the reader can work alone, understand why, and handle the unexpected | the reader can perform the documented tasks |
| Concepts | explained, with the reasons behind the rules | only what a step needs |
| Procedures | steps, checks, expected results, what to do when a step fails | steps and expected result |
| Troubleshooting | full card set, diagnosis method by levels, known behaviours, history | the frequent cards only, without diagnosis internals |
| Code references | appendix with files and methods | none |
| Tips and background | included | omitted |

Write the level in the classification field. Essential is not a lesser document: it is accurate
and well written, only shorter. The choice belongs to the user or the profile.

## Documentation sets

One analysis feeds every document of the set (`SKILL.md`, phases 2–5). Before writing, the
checkpoint shows a **distribution matrix**: every topic of the coverage map → the document that
carries it. The user manual says *how to use*, the configuration guide *how to set up and
maintain*, the troubleshooting manual *how to diagnose and repair*, the solution sheet *what it
is*. Cross-reference instead of repeating; repeat only what a reader of that document needs on
the spot (for example the session-expiry rule), in one sentence, with the reference.

A cross-reference names the other document and the section: "manuale utente, capitolo 5",
"scheda U03 del manuale utente". `check_doc.py --set` verifies both against the other masters.

A set can also grow later: a **continuation** adds a document the set does not have yet — a
type it lacks, or a further maintenance procedure — after the first documents were delivered
("Continuation of a set" in `SKILL.md`). Reuse the work folder's analysis when it survives;
otherwise the previous masters are sources. The new document takes a free card prefix and
passes `check_doc.py --set` against the existing masters, which stay inputs.

## IDs

| Prefix | Items | Notes |
|---|---|---|
| per-document letter + 2 digits | cards (`S01` for an application; for a scheduled process a letter from the job's name that no other ID family uses — never `S`, `A`, `Q`, `P`, `U`, `C`: `L01` for a price-list job, `B01` for another) | the **card prefix**: a different letter per document of a set — `check_doc.py --set` warns when two documents share it |
| `A01` | known behaviours | local to each document |
| `Q1` or `Q01` | diagnostic queries | local to each document |
| `P01`, `U01` (optional) | procedures, when they are not numbered sections | |

Declare the prefixes in the front matter, the card prefix first (`ids: [S, A, Q]`), so
`check_doc.py` validates every citation. A citation of another document's known behaviour or
query names that document ("A03 del manuale utente"). IDs are **stable**: a revision appends new IDs instead of renumbering, and keeps a
retired one with a note instead of reusing its number (`check_doc.py --previous`).
