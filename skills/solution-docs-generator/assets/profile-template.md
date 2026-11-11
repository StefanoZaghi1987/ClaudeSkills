# Documentation profile – <Organization or team>

<!-- Template for solution-docs-generator. Save a filled copy as docs-profile.md in the working
folder or repository root, or as ~/.claude/docs-profile.md. Every section is optional: delete
what does not apply. Keep this file outside public repositories if it names internal systems. -->

## Organization

- Company / team: <name>
- Departments that appear in documents: <e.g. ICT, Logistics, Production>
- Support channel named in "how to report a problem": <helpdesk address or ticket system>

## Languages

- Default document language: <it | en | de | fr | es | other>
- Extra language pack (a language the skill does not ship): <path to xx.json, or delete this line>

## Document types

- "All" means: <user manual, configuration guide, troubleshooting manual, solution sheet>
- Rules per type: <e.g. "scheduled processes: troubleshooting manual only, card prefix per job">
- Own type files: <path to each `<key>.md` of the organization; pass it to check_doc.py with `--type-def`>

## Header fields

In this order on the cover (`fields:` in the front matter):

| Field | How to fill it |
|---|---|
| Rif. | <request or ticket> – <inventory entry, e.g. "voce C-02 (AppName)"> |
| Redatto da | <author> |
| Versione | <x.y> del <dd/mm/yyyy> |
| Classificazione | guida completa / guida essenziale – <document type> |
| Destinatari | <audience>; with two audiences: "<users> (Parte A) · <technical staff> (Parte B)" |
| Fonte | sessione di brainstorming registrata del <date>, integrata con <kinds of source> |
| Documenti collegati | <other documents of the set> |

Notice line: "Documento interno. Non riportare mai in questo documento password, client secret o
altre credenziali."

## Classification and depth

- Default depth: complete.
- Use essential for: <kinds of document or audience, if any>.

## Audiences

| Group | Needs | Part |
|---|---|---|
| <users / key users> | good-use rules, first actions, how to report | Part A |
| <technical staff> | architecture, diagnosis, cards, procedures | Part B |

## Naming convention

- Troubleshooting: `<App> - troubleshooting - manuale operativo - v<x.y>.docx`
- User manual: `<App> - manuale utente - v<x.y>.docx`
- Configuration: `<App> - configurazione - manuale - v<x.y>.docx`
- Maintenance procedure: `<Task> - procedura di manutenzione - v<x.y>.docx`
- Solution sheet: `<App> - scheda della soluzione - v<x.y>.docx`
- Several languages: ` - <IT|EN|…>` before the extension

## Locations

| What | Where | How to reach it |
|---|---|---|
| Source code | <hosting platform / organization / project> | <clone URL pattern, CLI> |
| Project folders | <share path pattern, e.g. \\server\share\PRJ\<code>> | <mapped drive / mount> |
| Published manuals | <folder> | |
| Tickets and mails | <system> | |
| Credentials | <password manager name> (never copy values) | |

## Transcription glossary

| Heard | Correct |
|---|---|
| <ship level app> | <ShipLabelApp> |
| <orbit data appy> | <Orbit Data API> |

## Reusable texts

### <Shared component, e.g. ERP API layer>

<Short maintained description: what it is, where it runs, consoles, logs, typical problems.
Last reviewed: <date>.>

### Deadlines to watch

| Item | Expires | Renewal procedure |
|---|---|---|
| <TLS certificate *.example.com> | <dd/mm/yyyy> | <document / owner> |
| <client secrets of app registrations> | <dd/mm/yyyy> | <document / owner> |

## Policies

- Never write credentials; write where they are kept and who can obtain them.
- <Rules about personal data, external distribution, approvals>.

## Secret patterns

Extra detectors for organization-specific secrets (Python regular expressions):

- `<MYORG-[A-Z0-9]{24}>`

## Render style

```yaml
# render-style
font: Calibri
mono: Consolas
color: 1F3864
accent: D9E2F3
# logo: logo.png                       # relative to this file
# logo_position: header                # header | cover | both
# header_text: "{title} – {ref}"
# footer_text: "<Company> – documento interno"
# page_format: "Pag. {page} di {pages}"
# cover_layout: form                   # lines | form
# labels:
#   tip: Buona pratica
```
