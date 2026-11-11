# Documentation profile – ACME Components · ICT

<!-- Fictional profile for the evals of solution-docs-generator. -->

## Organization

- Company / team: ACME Components S.r.l. – ICT
- Departments that appear in documents: ICT, Magazzino spedizioni
- Support channel named in "how to report a problem": ticket to helpdesk@acme-components.example

## Languages

- Default document language: it

## Header fields

| Field | How to fill it |
|---|---|
| Tipo documento | the type name |
| Redatto da | ICT – Ufficio applicazioni |
| Versione | <x.y> del <dd/mm/yyyy> |
| Stato documento | BOZZA until approved |
| Riservatezza | INTERNO |
| Referente | Marco Neri |
| Documenti collegati | the other documents of the set |

## Naming convention

- Troubleshooting: `<App> - troubleshooting - manuale operativo - v<x.y>.docx`
- User manual: `<App> - manuale utente - v<x.y>.docx`

## Transcription glossary

| Heard | Correct |
|---|---|
| ship level app | ShipLabelApp |

## Policies

- Never write credentials: they are in the company password manager.

## Render style

```yaml
# render-style
font: Calibri
color: 1F3864
accent: D9E2F3
logo: acme-logo.png
logo_position: both
header_text: "{title} – ACME Components"
footer_text: "Documento interno – ICT"
page_format: "Pag. {page} di {pages}"
cover_layout: form
```
