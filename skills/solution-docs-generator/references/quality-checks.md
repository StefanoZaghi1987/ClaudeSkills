# Quality gate

Nothing is delivered before this gate passes. Silent when clean; when something cannot be fixed,
report it in the delivery message instead of hiding it.

## 1. Automatic checks

```bash
<python> scripts/check_doc.py doc.md --docx doc.docx [--profile profile.md] -o work/check.md
<python> scripts/check_doc.py ts.md --set um.md cfg.md          # a documentation set
<python> scripts/check_doc.py ts.en.md --parity ts.md            # a translation
<python> scripts/check_doc.py ts.md --previous old/ts.md         # a revision
```

- **Errors** (exit code 1) — fix all of them: a cited ID that is never defined or defined twice;
  "procedure 9.4" / "chapter 8" pointing to a missing heading; a possible secret; a missing image;
  an unclosed `:::` block; a `.docx` that does not open, lacks pictures or contains a secret.
  With `--set`: "manuale utente, capitolo 5" or an ID of another document that does not exist
  there. With `--parity`: different IDs or heading numbers from the other language. With
  `--previous`: an ID renumbered, a version not increased.
- **Warnings** — review each: heading numbers out of sequence, IDs never cited (a card nobody
  reaches from the quick index or another card), gaps in an ID sequence, empty sections, tables
  without caption or with uneven rows, leftover `TODO`/`TBD`/`«REDACTED»`, chapters out of the
  order of the type or not named as the language pack names them; two documents of a set sharing
  an ID prefix; a document of the set missing from "Related documents"; an ID of the previous
  version gone.
- **Notes** — the chapters of the type the document does not have: confirm each was dropped
  because the sources give nothing for it.
- **Open items** — the open-item markers of every language pack (`[da confermare …]`,
  `[to be confirmed …]`, …): list them at delivery, with the `verify` callouts.

A reference to a section of *another* document ("manuale di DockScanApp, procedura 9.4") is
recognized from the words before it — read on the same line, up to 90 characters back. Keep a
cross-document reference on one line with the document's name: a line break between the name
and the number makes the gate read the reference as pointing at this document. Without `--set`
such a reference is not checked; with `--set`, a sentence that names a document of the set (by
title or type name) is checked against that document.

## 2. Content checks (by reading)

- [ ] **Coverage:** every row of the coverage map has a destination that exists in the document,
      or an exclusion reason.
- [ ] **Traceability:** every non-obvious statement in the claims register has a source; nothing
      in the document comes from general knowledge alone.
- [ ] **Code agreement:** behaviours, messages, configuration keys, URLs, schedules match the code
      and configuration that run in production (or the gap is stated).
- [ ] **Conflicts:** each one resolved by the rules in `writing-standards.md` or by the user, and
      superseded documents named.
- [ ] **Structure:** chapters in the order of the document type; summary with identity table;
      quick index (troubleshooting) pointing to existing cards; part dividers when there are two
      audiences.
- [ ] **Depth:** the classification in the header matches the content (essential documents carry
      no internals, no code references, no tips).
- [ ] **Procedures:** prerequisites, numbered steps, expected result, warnings before risky steps,
      test-first when possible, read-only diagnostic queries.
- [ ] **Terminology:** glossary spellings everywhere; identifiers untranslated; UI labels exact.
- [ ] **Credentials:** none in text, tables, code blocks, figures (look at the screenshots), file
      names or document properties.
- [ ] **Language:** every heading, caption, label and fixed text in the document language, with
      the language pack's wording; a translation matches its master (`--parity`).
- [ ] **Header:** reference, author, version and date, classification, audience, sources, related
      documents, notice — as the profile requires.
- [ ] **Set:** each topic in the document the distribution matrix gives it; the other documents
      referenced, not repeated; every document lists the others (`--set` clean). A document
      added later to the set (a continuation) passes the same checks.
- [ ] **Revision:** the revision row says what changed; retired IDs kept and marked; nothing of the
      previous version lost without a decision (`--previous` clean).

## 3. File checks

- [ ] The file opens (the `.docx` check above); page size A4; TOC present and numbered where
      LibreOffice was available.
- [ ] Look at the rendered pages when the platform can show them (PDF pages as images): cover,
      TOC, a part divider, a page of cards, a page with a wide table and one with a figure.
      Fix overflowing tables (column widths, shorter cells) and oversized figures.
- [ ] File name follows the profile's convention, or `<Subject> - <file word of the type> -
      v<version>[ - <LANG>].<ext>`; no existing file overwritten.
- [ ] The `.md` masters (and translations) and their images are kept with the working files.

## 4. Edge cases

| Situation | Handling |
|---|---|
| No transcript, only code and documents | Allowed: the session is not mandatory. Say that people-knowledge (practice, history) may be missing and ask the checkpoint questions that matter. |
| Only a transcript, no code access | Allowed: mark behaviour statements that need code confirmation as open items, and say so at delivery. |
| Checkout older than production | Ask for the production version or state the commit/date analysed in the references. |
| A source is unreadable (scanned PDF, unsupported format) | Name it in the inventory and at delivery; continue with the rest. |
| Very large sources | Work by component and by topic with running notes; the coverage map and the claims register carry continuity. |
| Several subjects in one session | One document per subject, cross-linked (see document types). |
| Transcript without times or speakers | Allowed: the coverage map cites the `¶n` anchors; speakers stay unnamed unless the user names them. |
| Document language without a pack | Write the pack in the work folder from `en.json`; pass it with `--lang-pack`; offer to keep it. |
| Only an old `.docx`/`.pdf` of the document to revise | Extract it, rebuild the master keeping numbering and IDs, then revise. |
| The user asks to include a credential | Decline; write where it is kept instead. |
| Screenshots show personal data or secrets | Ask for a cropped or masked version; do not include the original. |
| A right-to-left target language (Arabic, Hebrew, …) | The renderer builds left-to-right layout only: deliver Markdown, or use the platform's document skill and say so. |
| A gate warning points at "another document" that is this one | The gate treats the document's own type name as this document: "il manuale utente, capitolo 5" said inside the user manual is checked against its own chapters (a set holds one document of each type). A same-type manual of another product gets the same reading ("il manuale utente della stampante Zebra, capitolo 3" is checked against this document): name that manual by its title, or judge the error as false. Known limit: a bare generic word ("il manuale, capitolo 5") or an adjective reading ("manuale operativo") still names another document — unless the document's own title is exactly that word. Judge each warning; the gate advises, you decide. |
| Adding a document to an existing set (continuation) | Reuse the work folder and its analysis when present; otherwise the old masters are sources. A free card prefix; `--set` clean against every existing master; the Related-documents update of the old masters is offered at delivery, never done silently ("Continuation of a set" in `SKILL.md`). |
