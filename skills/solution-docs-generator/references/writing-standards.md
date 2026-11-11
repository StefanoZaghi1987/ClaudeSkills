# Writing standards

## Voice and style

- Clear and technically correct. Short sentences, active voice, present tense, one idea per
  paragraph. Explain a concept the first time it is needed, then use the term consistently.
- Address the reader by the task: "Premere **Logout** e accedere di nuovo", not "l'utente
  dovrebbe…". Use the impersonal or infinitive form the document language prefers for procedures
  (Italian: infinitive — "Aprire", "Verificare").
- UI labels, menu paths and messages exactly as on screen: labels in **bold**, messages in
  quotation marks, paths with `›` (**Etichette › Stampa etichette**).
- Code identifiers, file names, paths, commands, table and view names in `code`.
- Numbers with units; dates in the document language's format; times in 24 h.
- No filler, no marketing, no blame. The history of a problem describes facts, not people.
- Every chapter starts with one or two sentences that say what it contains and who needs it.

## Terminology

- The profile's glossary and the chat messages decide spelling; the code decides identifiers;
  the vendor's documentation decides platform terms (Service Layer, SLD, Application Pool).
- One term per concept across the whole document set. Keep a glossary appendix of the terms a
  newcomer would not know.
- Translate the prose, never the identifiers, the UI labels of a product that is not localized,
  or quoted messages ("Languages" below).

## Traceability

- Every non-obvious statement has a source in the claims register (`analysis.md`). The document
  itself cites sources only where the reader benefits: ticket numbers in historical cases, file
  references in the code appendix, the references appendix.
- The header's "Sources" field and the references appendix list what was used.
- A statement no source confirms and the user did not settle carries the open-item marker
  `[da confermare: …]` (English: `[to be confirmed: …]`). `check_doc.py` lists them; the delivery
  message reports them. Never resolve doubt by inventing.

## Conflicts between sources

| Question | Prevails | Because |
|---|---|---|
| How the software behaves | the code (the deployed version) | it is what runs; check that the checkout matches production |
| How people work, business rules, priorities | the session and the user's answers | the code cannot say why |
| Configuration of an environment | the most recent evidence (screenshot, export, console) | configuration drifts |
| Platform behaviour | the vendor's documentation for the installed version | |
| Dates, ticket numbers, who solved what | mails and tickets | written at the time |

A conflict that changes what a reader will do goes to the checkpoint as a question. When an old
document is contradicted, the new document says what it supersedes (in the notice or the
references), never silently.

## Credentials and sensitive data

- Never write a password, client secret, key, token, connection string with credentials, or a
  personal access code. Write **where** it is kept ("credentials in the company password
  manager") and **who** can obtain it.
- Server names, URLs, ports, account *names* and paths are documentation, not secrets, unless the
  profile says otherwise.
- Personal data: names of contacts and their roles are fine; nothing about people beyond their
  role in the process.
- Security weaknesses found in the analysis are reported to the user in the conversation, not in
  the document.

## Procedures

- Numbered steps; one action per step; the expected result after the step or at the end.
- Prerequisites first (rights, tools, environment, a backup when the procedure changes data).
- Mark irreversible or risky steps with a `::: warning` callout before the step, not after.
- Prefer the supported route (the application, the vendor's API or console) to direct database
  writes; when a direct intervention is the only way, say so and require a backup.
- Test environment first whenever the procedure allows it.

## Tables, figures and callouts

- Tables for comparisons, mappings and repeated structures (environments, components,
  symptom → action). Every table has a caption (`Table: …`). Keep cells short.
- Figures only when they show something text cannot: a screen to find a command, a console
  state, a diagram. Every figure has a caption that says what to look at. Crop to the relevant
  area; hide personal data and credentials visible in a screenshot (or ask for a new one).
- Callouts sparingly: `note` (useful context), `tip` (good practice), `warning` (risk of damage
  or data loss), `important` (a rule whose violation causes a known problem), `verify` (a point
  still to check), `technical` (details a non-technical reader may skip).

## Languages

- **Document language** — chosen at intake (default Italian; the profile may set another). Every
  fixed text comes from its language pack, `assets/i18n/<lang>.json`: chapter names (`chapters`),
  cover labels (`fields`), card labels (`card`), depth wording (`depth`), badges, the open-item
  marker, the date format, the type names. `render.py` takes captions, page label, contents title
  and callout titles from the same pack. Never translate these ad hoc: the same type has the same
  chapter names in every document of the language.
- **A language without a pack** — copy `en.json` to the work folder, translate every value (keep
  the keys and the `{area}`/`{version}`/`{date}` placeholders), set `lang`, and pass it with
  `--lang-pack` to `render.py` and `check_doc.py`. Offer it at delivery for the profile or the skill.
- **Sources in another language** — the facts move, the identifiers do not. Translate the prose;
  keep in the original: code identifiers, configuration keys, file and object names, UI labels of
  a product that is not localized, quoted messages and log lines. At first use, give the
  translation beside an original term a reader must recognize on screen: **Stampa** (Print).
  Glossary entries keep both.
- **Several languages** — write and settle the master in the first language; then translate the
  master into `<name>.<lang>.md`. Same IDs, same heading numbers, same figures and tables:
  `check_doc.py --parity` verifies it. Never write two languages independently from the analysis.
- **A right-to-left target language** — the renderer builds left-to-right layout only
  (`references/authoring-format.md`): deliver Markdown, or use the platform's own route, and say
  so at delivery.
