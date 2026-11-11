---
key: configuration
audiences: [administrators]
default_prefix: C
ids: []
variants: [default]
chapters:
  default: [introduction, model, config_area*, operating_procedures, scheduled_components, infrastructure, appendices]
appendices: [checklists, config_keys, glossary, references]
---

# Configuration and maintenance guide

For administrators: what can be configured, what each setting does, which periodic or occasional
maintenance tasks exist, and how to perform them safely. It answers *how to set up and
maintain*.

Chapter names come from the language pack (`chapters.<key>`); `config_area*` means one chapter
per configuration area, named with the pack's pattern (`Configurazione di {area}`).

## Chapters

| Key | Content |
|---|---|
| introduction | purpose; audience and prerequisites (rights, tools, accesses); environments; what is configured where |
| model | the concepts the settings act on (authorization model, configuration model), with combined examples; when changes take effect |
| config_area* | per area: pages, fields, effect, when changes take effect |
| operating_procedures | numbered, self-contained procedures (new user, change of department, user leaving, yearly calendar, renew a secret…): prerequisites, steps, verification, rollback |
| scheduled_components | what runs, when, configuration and logs, manual run |
| infrastructure | servers, web server settings (keys, never secret values), identity-provider registration and secret renewal, database, source code, scripts, release and rollback |
| appendices | checklists; configuration keys table; glossary; references |

## Rules of this type

- Every procedure: prerequisites → numbered steps → verification → rollback. A `::: warning`
  callout comes *before* a risky or irreversible step.
- Prefer the supported route (the application, the vendor's console or API) to direct database
  writes; when a direct intervention is the only way, say so and require a backup.
- Separate a good organizational practice ("deactivate, do not delete") from what the system
  enforces, and say where the behaviour was verified (code, database).
- Keys tables give names, meaning and where they are read — never the value of a secret.

A procedure that stands alone (one task, one occasion) is a **maintenance procedure** instead
(`references/types/maintenance-procedure.md`).
