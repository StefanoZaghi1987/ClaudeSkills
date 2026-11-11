# Authoring format

The document is written once, as Markdown with a few extensions, and `render.py` builds the
delivered file from it: Word (A4, fixed house style, real table of contents), PDF (the Word file
converted by LibreOffice), or plain Markdown. The `.md` source is the master for every later
revision: keep it with its images.

The layout the renderer builds is left-to-right only: a right-to-left target language (Arabic,
Hebrew, …) is outside it — see `references/quality-checks.md` for what to deliver instead.

```bash
<python> scripts/render.py doc.md --to docx [--profile profile.md]   # doc.docx next to doc.md
<python> scripts/render.py doc.md --to pdf  -o "out/Name - v1.0.pdf"
<python> scripts/render.py doc.md --to md   -o out/doc.md             # extensions flattened
<python> scripts/render.py doc.pt.md --to docx --lang-pack work/pt.json   # a language without a pack
```

Fixed texts — "Tabella/Table", "Figura", "Pag.", "Sommario", callout titles, the revisions table —
come from the language pack of the front matter's `lang` (`assets/i18n/<lang>.json`). The
profile can override single labels (`labels:` in its render-style block).

The table of contents is a Word field. When LibreOffice and pypdf are available, `render.py`
renders a copy, measures the page of every entry and pre-fills the numbers; Word also refreshes
the field when the file is opened (it may ask to update fields — answer yes). `--no-paginate`
skips the measurement, `--no-update-fields` skips the refresh request.

## Front matter

```yaml
---
title: ShipLabelApp – Manuale di troubleshooting
subtitle: Manuale operativo · Diagnosi e risoluzione dei problemi
lang: it                      # language pack: it, en, de, fr, es (others with --lang-pack)
type: troubleshooting         # references/types/<type>.md: check_doc.py checks the chapters
variant: application          # when the type has variants (default: the first)
version: "1.0"                # read by check_doc.py --previous and by {version} in header/footer
date: 11/11/2026              # {date} in header/footer
ref: TICKET 1234              # {ref} in header/footer
header: ShipLabelApp – Manuale di troubleshooting   # running header (default: title)
author: Mario Rossi           # document properties
fields:                       # cover lines, in order: "Label: value"
  - Rif.: Ticket 1234 – voce C-12
  - Redatto da: Mario Rossi
  - Versione: 1.0 del 11/11/2026
  - Classificazione: guida completa – manutenzione e troubleshooting
  - Destinatari: Logistica (Parte A) · ICT (Parte B)
  - Fonti: sessione registrata del 10/11/2026, codice sorgente, documentazione di progetto, mail storiche
  - Documenti collegati: ShipLabelApp – Manuale utente
notice: Documento interno. Non riportare mai in questo documento password, client secret o altre credenziali.
revisions:                    # optional table on the cover: version | date | author | notes
  - 1.0 | 11/11/2026 | Mario Rossi | Prima stesura
ids: [S, A, Q]                # ID prefixes check_doc.py validates; the first is the card prefix
toc: true                     # false: no table of contents
toc_levels: 2                 # heading levels in the TOC
toc_title: Sommario           # default: the pack's label
style:                        # optional overrides of the house style (usually in the profile)
  color: 1F3864               # keys: references/profile.md, "Render style keys"
labels:                       # optional overrides of single labels of the language pack
  tip: Buona pratica
---
```

The front matter is read by the skill's own reader, the same on every machine: `key: value`,
`key: [a, b]`, a list of `- item` / `- Label: value` lines, or one nested level of `sub: value`
lines; `# comments` after a value are ignored. Values stay text (`version: 1.10` is "1.10"), except
`true`/`false` and whole numbers. Multi-line blocks and deeper nesting are not read.

## Body

Standard Markdown:

- `#`, `##`, `###`, `####` headings. Write the numbers yourself — `# 8. Schede di troubleshooting`,
  `## 8.1 Accesso e sessione`, `### S01 · Nessuno riesce ad accedere`. `check_doc.py` verifies the
  sequence and every reference to it. Appendices are `## A. Query diagnostiche`.
- Paragraphs; **bold**, *italic*, `code`, [links](https://example.com), `<https://auto.link>`.
- Bullet lists (`-`) and numbered lists (`1.`), one nested level (indent by 2–4 spaces).
- Pipe tables. Use `<br>` for a line break inside a cell, `\|` for a literal pipe.
- Fenced code blocks (```` ```sql ````): monospace, shaded box, spaces kept.
- `\newpage` on its own line: page break.
- `<!-- comments -->` are not rendered: use them for source notes while writing.

Extensions:

| Syntax | Result |
|---|---|
| `Table: caption` on the line after a table | numbered caption "Tabella N – caption" under the table |
| `Table: caption {widths=10,60,30}` | the same, with relative column widths |
| `![caption](images/file.png)` on its own line | centered figure, scaled to the page, numbered caption "Figura N – caption" |
| `![caption](images/file.png){width=12cm}` | the same, at most 12 cm wide |
| `[[SOLO TEST]]` | inline badge (environment or role markers) |
| `::: note` … `:::` (also `tip`, `warning`, `important`, `info`, `verify`, `technical`) | callout box with a default title from the language pack |
| `::: warning Solo lettura` … `:::` | callout with a custom title |
| `::: card` … `:::` | two-column card table: each `Label: text` line starts a row; `- items` and other lines belong to the row above |
| `::: part Parte A – Guida per gli operatori` … `:::` | part divider page; the paragraphs inside are its introduction |

Callouts and their use (titles: the pack's `labels`):

| Kind | Colour | Use |
|---|---|---|
| `note`, `info` | blue | useful context |
| `tip` | green | good practice ("Buona pratica") |
| `warning` | orange | risk of damage or data loss — before the step |
| `important` | red | a rule whose violation causes a known problem |
| `verify` | amber | a point that still needs checking ("Da verificare"); list it at delivery like an open item |
| `technical` | purple | technical details a non-technical reader may skip ("Dettagli tecnici") |

Card rows use the pack's `card` labels: Sintomo · Chi interviene · Cause probabili · Come verificare ·
Come risolvere, and optionally Riferimenti (ticket, code reference, related document).

Headings inside callouts and cards are rendered as bold lines. Images are resolved relative to the
`.md` file.

## Example

````markdown
# 8. Schede di troubleshooting

Ogni scheda riporta sintomo, cause, verifiche e soluzione.

## 8.1 Accesso e sessione

### S04 · Errori di sessione dopo una pausa

::: card
Sintomo: dopo una pausa ogni operazione restituisce "Invalid session".
Chi interviene: Operatore
Cause probabili:
- Sessione scaduta dopo 30 minuti di inattività (6.5).
- Riavvio notturno del Service Layer.
Come verificare:
- F12 › Network: risposta 401 sulle chiamate al back-end.
Come risolvere:
- **Logout** e nuovo accesso; nessun dato già registrato va perso.
:::

::: tip
Dopo una pausa lunga conviene uscire e rientrare prima di riprendere il lavoro.
:::

| Livello | Strumento | Cosa si scopre |
|---|---|---|
| 1 | Raccolta informazioni | chi, quando, quale operazione |
| 2 | Console del browser | quale chiamata fallisce |

Table: Livelli di diagnosi {widths=12,38,50}

![Scheda Network durante un login in test](images/network-login.png){width=15cm}
````
