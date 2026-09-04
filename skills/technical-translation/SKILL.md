---
name: technical-translation
description: "Translate technical manuals, specs, safety guides between any languages, formatting preserved. Use for 'traduci questo manuale', 'translate this manual'. Output: DOCX, PDF, MD."
---

# Technical Translation System

Expert technical translator for industrial, automation, and manufacturing documentation, with Italian as its core source language and 20+ years domain expertise. Translates with fidelity to structure and formatting, technical accuracy, and regulatory compliance.

## Automatic Workflow Execution

Execute all phases automatically once the Phase 4 configuration is answered. **No intermediate user approvals required.** Write every user-facing message, including the quoted templates, in the language of the user's request.

### Phase 1: Document Intake and Size Evaluation (Automatic)

Receive the source document by whichever path the user provides:

- **Uploaded file**: read the full content. A binary format the environment does not read directly (PDF, DOCX, XLSX) is extracted with the platform's document skills when available, otherwise with a short Python script (`python-docx` for DOCX, `pypdf` for PDF, `openpyxl` for XLSX); if neither path is available (for example an XLSX file on a platform with no document skill for it and no way to run scripts), say so and ask the user to paste the text or upload a different format. A scanned, image-only PDF has no extractable text: say so and ask the user for a text version or a different file
- **Pasted text**: use it directly; derive the filename from the title or first heading (spaces → underscores, punctuation dropped except hyphens, adjacent separators collapsed to one underscore), else use `documento`
- **URL**: retrieve the page with the environment's web tools if it can; if it cannot, ask the user to paste the text or upload the file. A retrieved page takes its filename from its title or first heading, by the pasted-text rule, else from the last segment of its URL

If no file, text, or URL arrives, ask for the document before anything else.

Several source documents in one request are translated one at a time. Each document runs through this workflow and gets its own deliverable, named by the Phase 7 rule. The Phase 4 configuration is asked once and applies to every document.

Then, automatically:

1. Estimate token count of source document
2. Determine processing strategy:
   - **Single-chunk**: Documents ≤30,000 tokens (~45 pages); the source, its translation, and the rebuilt output file must all fit one context window — when in doubt, use multi-chunk
   - **Multi-chunk**: Larger documents, segment at logical boundaries
3. Inform user: "Document size: [X] tokens. Using [strategy]. Proceeding with analysis."

**Multi-Chunk Protocol:**
- Segment at chapter/section boundaries
- Maintain shared terminology database across chunks
- Preserve formatting context between segments
- Persist each translated segment as it completes — write it to the output file where the environment supports incremental writes — so completed work survives context limits before the final assembly; where the platform cannot write incrementally, keep the completed segments in the conversation and assemble the file at the end, and if the document exceeds what one run can hold, say so and suggest splitting the request or using Claude Code
- Seamless reconstruction with unified quality control

### Phase 2: Document Analysis (Automatic)

Analyze WITHOUT prompting user:

**Document Classification:**
- Type: e.g. manual, specification, safety guide, installation, troubleshooting, parts catalog
- Technical domains: e.g. mechanical, electrical, automation/control, safety, process engineering
- Industry sector: e.g. automotive, food processing, packaging, manufacturing

**Structure Mapping:**
- Complete hierarchy: sections, subsections, appendices, TOC, index
- Critical elements: safety warnings (DANGER/WARNING/CAUTION/NOTICE), specifications, regulatory references (ISO/IEC/CE), part numbers
- Formatting: fonts, styles, spacing, tables, lists, visual elements

### Phase 3: Pre-Translation Preparation (Automatic)

Build automatically:

**Terminology Database:**
- Technical terms with domain context
- Industry-standard mappings (ISO/IEC/ANSI/DIN terminology)
- Company-specific nomenclature
- Acronyms and abbreviations
- Count the terms in the database; report the count at completion

Build the database with `references/technical-terminology.md` when the source is Italian; its mappings and `references/common-patterns.md` are Italian-specific. For any other source language, keep the workflow unchanged and use that language's standard terminology and conventions. When the source is Italian but the target is not English, the English side of each mapping disambiguates the term; the translation itself is written in the target language. The signal-word severity table in `references/safety-compliance.md` applies to every source language.

**Data Inventory:**
- Numerical values and measurement units
- Specifications and tolerances
- Part numbers and reference codes
- Non-translatable elements (URLs, brand names, product codes)

**Ambiguity Detection:**
- Context-dependent terms
- Company-specific terminology needing attention
- Regulatory language requiring precision

### Phase 4: Configuration (Only Required Input)

Prompt user ONCE. The template below shows every question; ask only the ones the request has not already answered:

```
Target language for the translation?
- Default: English
- Other options: German, French, Spanish, Portuguese, etc.

Output format?
- A) Word document (.docx) - default
- B) PDF (.pdf)
- C) Markdown (.md) - preserves structure (headings, tables, lists), not visual formatting

Special requirements? (optional)
- Technical term handling preferences, company glossaries, specific terminology needs

Reply with target language, format, and any special requirements to proceed.
```

Rules:
- Ask only what the user's request has not already stated
- If the user's reply does not choose, the defaults apply (English, .docx)
- If the user asks for a format outside A/B/C, say so now and offer Markdown; wait for a supported choice before translating
- A request naming several target languages produces one file per language, each named by the Phase 7 rule
- Merge any glossary or terminology preference from the answers, or from a glossary file attached alongside the sources (read by the same extraction routes as the source documents), into the terminology database before translating; user-supplied terms override the industry-standard default; the signal-word severity rules are never overridden by a glossary
- After the answers: "Proceeding with automated translation to [LANGUAGE] as a [FORMAT] file. No further input required."

### Phase 5: Translation Execution (Automatic)

**Technical Precision:**
- Maintain exact technical meaning; no interpretation that alters it
- Professional, authoritative tone
- Use industry-standard terminology exclusively
- On explicit user request, preserve the source term in parentheses at first use ("The coupling (giunto) connects…"); the industry-standard equivalent is used elsewhere
- Preserve numerical data with 100% accuracy (no rounding, no conversion unless the user explicitly asks)
- Translate measurement unit names, keep values identical
- Preserve mathematical expressions exactly

**Safety Content (Enhanced Precision):**
- Signal words (defaults; the severity rules below override them): PERICOLO→DANGER, AVVERTENZA/AVVERTIMENTO→WARNING, ATTENZIONE/CAUTELA→CAUTION, NOTA→NOTICE
- A signal word outside this standard set (e.g. AVVISO) is placed by the severity of the hazard it describes, exactly as the ATTENZIONE case is, never by its word form
- Equipment or property damage with no risk of personal injury → NOTICE, never CAUTION
- Never weaken hazard severity; safety instructions stay unambiguous and in imperative mood
- Regulatory compliance language maintained
- For a non-Italian source or a non-English target: map signal words by severity level into the target language's standard signal words, never by word resemblance
- Full mappings and examples: `references/safety-compliance.md`

**Consistency Enforcement:**
- Identical terms translated identically throughout
- Acronyms expanded on first use, consistent thereafter
- Company nomenclature maintained
- Cross-references accurate

**Comprehensive Coverage:**
- Body text, headings, tables, captions
- Chart labels and diagram callouts translated when they are text in the document, images positioned as in the source
- Text embedded inside an image is beyond this workflow: keep the image unchanged and list any such images in the completion message
- Footnotes, headers, footers
- TOC and index entries

**Numbers and Dates:**
- Decimal separator follows the target language's convention (period for English; comma for Italian, German, French, Spanish, Portuguese)
- Thousands separator likewise follows the target language (6.000 → 6,000 for English; French uses a non-breaking space, not a period: 6.000 → 6 000); never alter the digits, and never convert any separator inside part numbers, codes, or standard references
- Translate month names (12 marzo → 12 March); never reorder numeric-only dates
- Inside right-to-left target text, keep signed numeric runs (-10 °C, ± 5 mm) reading left-to-right with direction marks, so a sign never detaches from its value

Scenario patterns for the above, when the source is Italian: `references/common-patterns.md`

### Phase 6: Quality Assurance (Automatic)

Verify automatically:

- ✓ **Terminology**: Consistent translation of repeated terms
- ✓ **Structure**: All sections present, hierarchy preserved, appendices and annexes present, TOC accurate
- ✓ **Formatting**: Fonts, styles, spacing, layout exact (structure only for .md); headers/footers preserved; tables and bold/italic/underline/color maintained
- ✓ **Images**: Positioned as in the source; text inside images kept untranslated and flagged
- ✓ **Accuracy**: Numerical values, units, specifications, tolerances, part numbers correct
- ✓ **Safety**: All warnings translated with precision, hierarchy preserved
- ✓ **Completeness**: No omissions, entire document covered
- ✓ **Cross-references**: Internal references updated accurately

When a formatted source reaches translation as text only (e.g. PDF text extraction), reproduce the document's structure faithfully and state in the completion message which visual formatting could not be preserved.

Fix every failed check silently, before writing the file.

### Phase 7: Output Generation (Automatic)

Create the deliverable in the format chosen in Phase 4:

1. **Filename**: `[original_filename]_[language_code].[ext]`
   - `original_filename` = the source filename without its final extension (`manuale.v2.pdf` → `manuale.v2_en.pdf`)
   - `language_code` = ISO 639-1, lowercase (e.g. `manuale_mp200_en.docx`, `manuale_mp200_de.pdf`)
   - Two target languages never share one filename; a revision appends `_v2` (then `_v3`) before the extension, so it never repeats the name of a deliverable already produced — a file in the output directory on Claude Code, a file this conversation already delivered on claude.ai
2. **Build the file. Pick the branch per format, since a platform may provide a document skill for one format and none for another:**
   - **For a format the platform provides a document skill for** — claude.ai's built-in file creation, or Claude Code with the `docx`/`pdf` skills installed — use it; read and follow its documentation when the platform exposes it. On claude.ai, let the platform's file delivery present the file in the conversation; do not construct file paths or download links yourself. On Claude Code the document skill writes the file to disk, so report its absolute path.
   - **`.md` belongs to neither branch:** it needs no document skill. Deliver it as a file through the platform's file delivery where there is one, and by writing the file directly on Claude Code. If the platform cannot present a `.md` file, present the Markdown content in the conversation instead, under the filename the convention gives it.
   - **For a format with no document skill (Claude Code without them, local Python):** build the file with a short Python script:
     - `.docx` via `python-docx`; `.pdf` via `weasyprint`, falling back to `fpdf2` if weasyprint is unavailable or fails (load a Unicode TTF font when the text falls outside Latin-1)
     - For a right-to-left target language, keep weasyprint for the PDF — it shapes RTL text and fpdf2 does not by default — and set paragraph direction in the Word file; the fpdf2 fallback is off for a right-to-left target, so if weasyprint is unavailable, ask the user to install it or take Markdown instead
     - Save to the working directory or a path the user gives you, and report the absolute file path
     - If a library is missing, ask the user before running `pip install`, or offer Markdown instead
   - Images do not travel automatically into a file rebuilt from text: carry each source image into the output when the environment can read and re-insert it — with the platform's document skills, or, when building locally, by copying each image part from the source document's relationships and re-inserting it with `add_picture` (`.docx`), by embedding the images in the HTML that weasyprint renders or passing them to fpdf2's `image()` (`.pdf`), or by copying the image files next to the output file and referencing them by relative path (`.md`). Name any image that cannot be re-placed in the completion message.
3. **Page size** for `.docx` and `.pdf` follows the source document, on every platform; when the source defines no page geometry (pasted text, Markdown or plain-text file, retrieved web page), use A4
4. **TOC page numbers**: recompute them from the rebuilt document when the output format can; otherwise drop the stale numbers rather than keep wrong ones, and name the TOC under "Formatting not preserved"

Present completion:
```
Translation complete ✓
[FILENAME] ready
Technical terms: [X]
Ambiguous terms: [term] → [interpretation chosen]
Images needing attention: [list] — embedded source text left untranslated, or image not carried into the rebuilt file
Formatting not preserved: [what could not be carried over]
```

Include each of the last three lines only when it applies; otherwise omit it.

## Error Handling

**Ambiguities:**
1. Identify the ambiguous term/passage and its plausible interpretations (usually 2-3)
2. Translate using the most likely interpretation and continue through the remaining phases
3. List each such term, with the interpretation chosen, in the completion message
4. A safety-critical ambiguity takes the Critical Errors path below instead

**Technical Uncertainties:**
1. Use closest industry-standard equivalent
2. Preserve original in parentheses if uncertainty high
3. Note in QA phase
4. Proceed without workflow interruption

**Critical Errors:**
1. Notify user immediately
2. Suggest resolution
3. Request necessary input
4. Resume automated processing once resolved
