# Code analysis

The code is the source of truth for *how the system behaves*. Reading it is what turns a
remembered description into a verified one, recovers logic nobody remembers, and reveals the
problems that have not happened yet. Read with a purpose: what the document needs, starting from
the features the transcript and the documents mention.

## 1. Map the solution

Produce a component table (it becomes the "Components" / "Architecture" section):

| Component | Technology | Where it runs | Role |
|---|---|---|---|
| Front-end | React 18 + Redux, PWA | browser on handhelds and PCs | UI, session state |
| Back-end | ASP.NET Core 6 on IIS | front-end server | gateway to the ERP API |
| … | | | |

Sources: solution and project files, `package.json`, Dockerfiles, deployment profiles
(`*.pubxml`), IIS/`web.config`, crontab and scheduler exports, connection strings (redacted), the
project's README. Note dependencies on shared libraries and other internal services.

## 2. Checklist per component

Go through every item that applies; skip the rest explicitly in your notes.

| Area | Look for | Becomes in the document |
|---|---|---|
| Environments | config files per environment, base URLs, server names, database or company names | environments table (test / production) |
| Configuration | keys and their meaning, defaults, where they are read | configuration section; keys table (never values of secrets) |
| Authentication and sessions | login modes, identity provider, tokens, cookies, timeouts, renewal | concepts for diagnosis; cards on login and sessions |
| Authorization | roles, groups, permission checks, menu visibility | user manual "who can do what"; configuration guide |
| Data read | queries, views, API endpoints read, caching | data section; diagnostic queries |
| Data written | which entities, through which API, transactional or step by step | concepts ("a chain of operations"); restore procedures |
| External calls | ERP/Service APIs, reporting, mail, printers, file shares | call flow table; call map appendix |
| Scheduled work | cron, Task Scheduler, hosted services, job tables, intervals | schedule section; "job did not run" cards |
| Printing and reports | report engine, layout codes, printer resolution per user | printing cards |
| Logging | logger setup, levels per environment, file paths, rotation, external monitoring | diagnosis method (where to look) |
| Messages | user-visible strings (UI, resources, exceptions mapped to messages) | "what to do when…" table; messages appendix |
| Error handling | what is caught, what is swallowed, HTTP status codes returned | known behaviours; diagnosis hints |
| Concurrency and limits | parallel edits, numbering computed client-side, pagination, timeouts, batch sizes | known behaviours; performance cards |
| Deployment | build output, publish profiles, caches (service workers, PWA), versioning | release section; post-release checklist |
| Certificates and secrets lifecycle | client secrets, certificates, their expiry (from docs or portal, not code) | "deadlines to watch" table |

Record each finding with its file and, where useful, the method or line range:
`src/Back/Services/PickService.cs – ReleaseAllocation()`. These references go to an appendix of
the troubleshooting manual, never into user-facing parts.

## 3. Known behaviours (from the code)

A known behaviour is something the code does that can surprise a user or an operator, that is not
(yet) a bug report, and that has a workaround. Examples: a list loaded before the user is known
and never refreshed; a search fired after 500 ms that rejects partial codes; an operation that
reports success even when nothing was sent; an error swallowed and logged only at debug level.

For each: ID (`A01`…), behaviour, effect, workaround, cards that cite it, code reference. Phrase
them neutrally: facts about the software, not judgements on its author.

## 4. Potential problems

For each component and each external dependency, ask: what happens when it is slow, down,
misconfigured, expired, full, or upgraded? When two users act at once? When the data is extreme
(very long lists, decimals, empty values, special characters)? When the environment is restored
from production? Keep the ones the code makes plausible; each becomes a card (symptom, causes,
how to verify, how to solve) even if it has never happened.

## 5. History

`git log` (dates, authors, messages) and dated backups help to date incidents, releases and
changes mentioned in the transcript or mails. Use them to complete historical cases, never to
judge people.

## 6. Security findings

While reading, note — without copying any value — credentials in code or config, passwords on
command lines, disabled certificate validation, administrative accounts used for routine work,
secrets shared between environments, sensitive data returned to the client. They are **not** part
of the document. Report them at delivery in the conversation, with the file and a suggested
remediation, so the user can handle them through the right channel.

## 7. Diagnostic queries

Queries proposed in the document are **read-only** (`SELECT` only), written for the actual
database dialect, with the schema or company noted and example values marked as such. Validate
the column and table names against the code or the view definitions; when a query cannot be
tested, say so in its caption.
