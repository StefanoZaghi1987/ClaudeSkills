# The documentation profile

The skill is organization-neutral. Everything specific to one company or team — header fields,
references to tickets or inventories, file naming, depth policy, where code and documents live,
the transcription glossary, reusable descriptions of shared platforms, the house colours — lives
in an optional **profile**: one Markdown file, readable by people, kept by the team, outside the
skill. Without a profile the skill uses its defaults and asks only what it needs.

A starting template is in `assets/profile-template.md`. Copy it, fill what applies, delete the
rest.

## Finding the profile

Look in this order and use the first one found; say which one is in use:

1. a path or an attachment the user gives in the request;
2. `docs-profile.md` in the current working folder or repository root, or in its `docs/` folder;
3. `~/.claude/docs-profile.md` (personal default on a machine with a home folder);
4. a project's knowledge files, when the platform has projects;
5. none — defaults.

When the user describes a convention during the work that the profile does not hold yet, apply it,
and at delivery offer to add it to the profile.

## Sections

All sections are optional. Headings are matched loosely (English or Italian).

| Section | Used for | Read by |
|---|---|---|
| Organization | company or team name, departments, roles named in documents | agent |
| Languages | default document language(s); a language pack for a language the skill does not ship (path) | agent |
| Document types | which types the organization writes by default for "all"; extra rules per type; the organization's own type files, checked with `check_doc.py --type-def` | agent |
| Header fields | the cover fields, in order, with how to fill each (e.g. "Rif.: <ticket> – <inventory entry>") | agent |
| Classification and depth | when to use complete vs essential; the classification wording | agent |
| Audiences | standard reader groups and what each needs (e.g. Part A users, Part B technical staff) | agent |
| Naming convention | file name pattern per document type; versioning | agent |
| Locations | where code repositories, project folders, manuals, tickets live; how to reach them | agent |
| Transcription glossary | a two-column table `heard | correct` | `transcript.py` (apply, terms) |
| Reusable texts | short, maintained descriptions of shared components (an ERP API layer, an identity provider, certificates, a reporting service), with dates to keep current | agent |
| Policies | what must never appear (credentials, personal data), where secrets are kept, approval rules | agent |
| Secret patterns | extra detectors: list items with a regex in backticks | `extract_sources.py`, `check_doc.py` |
| Render style | a fenced block starting with `# render-style` (keys below) | `render.py --profile` |

### Render style keys

```yaml
# render-style
font: Calibri          # body and headings
mono: Consolas         # code
color: 1F3864          # headings, cover, part pages, badges
accent: D9E2F3         # table header and card label shading
muted: 595959          # subtitle and running header
body_size: 10.5
h1_size: 16            # heading sizes: h1_size … h4_size (16, 13, 11.5, 10.5)
table_size: 9.5
code_size: 8.5
h1_new_page: false     # start every chapter on a new page
margin_cm: 2.0
logo: logo.png         # path relative to the profile; empty = no logo
logo_width_cm: 3.0
logo_position: header  # header | cover | both
header_text: "{title} – {ref}"           # running header; placeholders below
footer_text: "Documento interno"         # left of the page number
page_format: "Pag. {page} di {pages}"    # default: "<page label> {page}"
cover_layout: lines    # lines ("Label: value") | form (a shaded two-column table, as in corporate templates)
labels:                # override single labels of the language pack
  tip: Buona pratica
```

Placeholders in `header_text`, `footer_text` and `page_format`: `{title}`, `{type}` (the type's
name in the document language), `{ref}`, `{version}`, `{date}` (front-matter keys), and in
`page_format` `{page}` and `{pages}` (Word fields, always current).

The block is read by the skill's own reader (the subset of `references/authoring-format.md`):
one nested level (`labels:`), `# comments` after values, quotes around values that contain `#` or
`:`. Values stay text: `color: 000000` is the colour, not a number.

## Keep it current

The reusable texts often carry dates (certificate and secret expiries). The profile is the one
place to update them; documents copy them at writing time and carry their own date.
