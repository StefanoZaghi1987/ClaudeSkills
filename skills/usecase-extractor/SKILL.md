---
name: usecase-extractor
description: "Turn a requirements document or spec into use cases and user stories grouped by actor, with codes, flows and dependencies. Use for 'estrai i casi d'uso', 'extract the use cases'. DOCX/XLSX/PDF/MD."
---

# Use Case Extractor

Transform requirements documents and functional specifications into structured, role-based use case documentation following established business-analysis practice.

## Languages

Source and output languages are independent: a source may be in any language, and
several sources may each be in a different one.

- **Output language**: whatever the request states. When the request states none, ask in
  Step 2 and apply this default to a reply that still does not choose: the language of the
  request if that is Italian or English, Italian otherwise. User-facing messages always
  follow the language of the request, including Step 2's question.
- **Written in the output language**: section headings, sheet names, field labels, priority
  values, the Coverage Assessment value, the five relationship-type words, and the
  flagged-item categories — one fixed term per relationship type across the whole document,
  listed in a legend: the Appendix in the document formats, under the dependencies matrix in
  the Excel workbook.
- **Kept in the source language**: the `Source` citation, which quotes the document's
  own section wording and identifier. The `(inferred)` marker beside it is the analysis's
  own annotation rather than part of the quotation, so it follows the output language.
- **Translated with the source term kept**: the document's own vocabulary — entity,
  status, screen, and field names — written as the output-language term with the
  source's term in parentheses at first use, as in `Draft status (Bozza)` (English
  output citing an Italian source's `Bozza`); later mentions use the output-language
  term alone. Descriptive prose — Target, Main Flow, Variations, User Story — is
  written fully in the output language.
- **Never translated**: use case codes and role prefixes. A prefix follows the source,
  the way a citation does: the ten standard prefixes are a fixed vocabulary in every
  language, and a custom prefix takes three letters from the role name as the source
  document writes it (`Medico` gives `MED`); when that script is not Latin, the three
  letters come from a standard romanization of the role name (`医師` gives `ISH`). The
  same analysis therefore carries the same codes in every output language, and the
  legend gives each prefix its role name in the output language — the Appendix in the
  document formats, Sheet 1's Roles Summary Table in the Excel workbook.

## Reference files — read each when its step runs

- `references/examples.md` (Steps 4–5) — worked extraction examples across domains and languages. Read it before extracting and structuring use cases.
- `references/format-templates.md` (Steps 2, 7) — exact output templates for each format, and the format-selection logic. Read its Format Selection Logic section when Step 2 must recommend a format, and the whole file before generating the output file(s).

## Workflow

### Step 1: Comprehensive Document Analysis

Read all source documents thoroughly before extracting anything — uploaded files and requirements text supplied in the conversation. Then say in a sentence or two what kind of document it is and what it appears to cover. Accepted inputs: PDF, Word (`.doc`/`.docx`), Rich Text (`.rtf`), Excel (`.xlsx`), CSV (`.csv`), Markdown, and plain text. If a file's text cannot be read on this platform — a scanned, image-only PDF, or an attachment type the platform cannot parse, such as legacy `.doc` on claude.ai — handle it under Unreadable Input (see Edge Cases).

Identify:
- Business domain and context
- Project scope and objectives
- All functional and technical requirements
- Non-functional requirements — performance, security, usability, compliance (they feed the non-functional requirements section)
- Stakeholder needs and expectations
- Constraints and assumptions
- Explicitly stated use cases
- Implicitly described use cases (inferred from requirements)
- Ambiguities, contradictions, and missing information (they feed Flagged Items)

### Step 2: Output Configuration

The output language decides the words of every field extracted in Steps 4–5, so settle it
here, before any of that prose is written.

Ask only after Step 1 has produced readable requirements content. A source whose text cannot
be read takes the Unreadable Input path, and a source that carries no requirements content
takes the Source Without Requirements Content path — neither reaches a configuration question
or a deliverable.

Prompt user ONCE. The template below shows every question; ask only the ones the request has not already answered:

```
Language for the output document?
- 1) Italian
- 2) English
- 3) Other (please specify)
No choice means [the default that applies to this request].

Output format?
- A) Word document (.docx) - default
- B) Excel spreadsheet (.xlsx)
- C) PDF document (.pdf)
- D) Markdown file (.md)
- E) Multiple formats - name the combination

Reply with language and format, or just say "proceed" for those defaults.
Special requirements are welcome.
```

Rules:
- Ask only what the user's request has not already stated
- Compute the default language from the Languages section and name it in the question, rather
  than printing the placeholder
- Apply any special requirement from the answers to the deliverable where the format allows it; name anything that could not be applied in the completion message
- A special requirement that narrows the analysis — one role only, one section only — applies
  from Step 3 onward, rather than as a filter over a finished extraction
- If the user's reply does not choose, the defaults apply — the Languages section's output language, and `.docx`
- If the user asks for a format outside A-E, say so and offer the closest supported format; wait for a supported choice before generating
- When the user is undecided or asks for a recommendation, recommend one format using the selection logic at the end of `references/format-templates.md`, and wait for the user's choice before generating

After the answers: "Proceeding with the use case documentation in [LANGUAGE] as [FORMAT]. No further questions unless the source or the environment forces one."

### Step 3: Actor and Role Identification

Extract and categorize all actors:
- **Explicit actors**: Users, roles, and stakeholders mentioned directly
- **Implicit actors**: Roles inferred from actions and requirements
- **System actors**: External systems, APIs, automated processes

Assign clear identifier prefixes (3 letters, uppercase):
- **ADM** = Administrator
- **USR** = End User / General User
- **DEV** = Developer
- **OPR** = Operator
- **MGR** = Manager
- **SYS** = System (automated processes)
- **API** = API Consumer / External System
- **AUD** = Auditor
- **SUP** = Support Staff
- **CST** = Customer
- Create custom prefixes for domain-specific roles as needed (e.g., DOC for Doctor, NUR for Nurse)
- Each prefix must be unique across the analysis; if two roles suggest the same three letters, differentiate one of them

Write a 2-3 sentence description of each role — its responsibilities and its position in the system. Every output format carries it.

### Step 4: Use Case Extraction and Numbering

For each identified role:
1. Extract explicit use cases already defined in document
2. Infer use cases from functional requirements, business processes, user needs, and data flows
3. Assign sequential numbering starting at 001 for each role prefix
   - Format: `[PREFIX]-[NUMBER]` (e.g., ADM-001, ADM-002, USR-001)
4. Maintain logical order based on workflow or document structure

Granularity:
- An entity the source creates, reads, updates and deletes yields one use case per operation,
  rather than one use case that manages the entity
- An interaction with an external system splits into the initiating role's use case and a
  system-role use case that handles the response, rather than one use case spanning both
  sides; the failure of that response is a `Variations` entry, not a third use case

Each use case belongs to exactly one owning role — the role that performs it. A role that only takes part in it reaches it through Dependencies, never as a second copy under its own prefix. A role that inherits another role's access states that in its description, rather than re-listing that role's use cases.

An actor that owns no use case — one the document names only as the receiver of an output — gets no section, no prefix, and no place in the role count. Name it in the description of the role it interacts with, and under Flagged Items when the source implies it should act but never says how.

### Step 5: Detailed Information Extraction

For each use case (worked examples: `references/examples.md`), extract and structure the
fields below, written in the output language Step 2 settled. A field with nothing to
record carries the output language's word for none — one fixed term across the whole
document — the way `Dependencies` does, rather than being dropped or filled with invented
content. `Acceptance Criteria` is the one exception, stated at the field itself.

**Code**: `[PREFIX]-[NUMBER]`

**Name**: Concise, action-oriented name (3-7 words)
- Use verbs: Create, Update, Delete, View, Generate, Approve, Configure, Process
- Example: "Register New User", "Generate Monthly Report", "Approve Purchase Order"

**Title**: `[PREFIX]-[NUMBER]: [Name]`
- Example: `ADM-001: Configure System Settings`

**Priority**: High, Medium, or Low
- Follows the priority the source states, when it states one: a MoSCoW rating maps
  `Must have` to High, `Should have` to Medium, and `Could have` to Low
- A `Won't have` requirement is outside the release's scope, so it reaches Flagged Items
  rather than a use case (see Edge Cases)
- A numbered scale — `P1`–`P4`, `1`–`5`, or any other the source uses — maps its most critical
  tier to High, its least critical tier to Low, and every tier between them to Medium
  - The source's own legend names the most critical tier; with no legend, the lower number is the
    more critical one, so `P1` outranks `P4` and `1` outranks `5`, and that reading goes under
    Flagged Items as an ambiguity, since inverting it would re-rank every use case
- Otherwise assign it from business criticality and expected frequency of use together: a High
  use case is core functionality that is both frequently used and business-critical, so a
  frequently used supporting step stays Medium
- Drives the detail level applied to this use case (see Quality Guidelines)

**Target**: Clear goal description — length follows the assigned Priority (see Quality Guidelines)
- Explain what user wants to accomplish
- Describe business value and purpose
- Include relevant context

**Main Flow**: Numbered steps of the primary path (3-7 steps)
- One actor action or system response per step
- Example: 1. Customer selects a product 2. System checks availability 3. System adds the item to the cart 4. System updates the cart totals

**Variations**: Alternative and exception paths, each numbered against the main-flow step it branches from
- Example: `2a. Product unavailable: system suggests similar products and keeps the customer on the page`
- High and Medium priority use cases: alternative and exception paths; Low priority: exception paths only

**Input Data**: Comprehensive list categorized as:

*Mandatory* (required):
- Authentication/authorization credentials
- Primary data fields and values
- Required documents or files
- Preconditions
- Configuration parameters
- Validation criteria

*Optional* (enhance functionality):
- Additional data fields
- Optional documents or attachments
- Preferences and settings
- Contextual information
- Historical data

**Output Data**: Complete list of all outputs, results, and effects:
- Data created/modified (records, documents, files)
- Results (calculations, reports, analytics)
- Artifacts (documents, exports, printouts)
- Notifications (emails, alerts, messages)
- Events (triggered processes, workflow steps)
- Side effects (logs, audit records, cache updates)
- Status changes (state transitions, flags)
- User feedback (confirmations, error messages)

**Dependencies**: Related use cases with relationship type:
- Format: `CODE-XXX: Name (relationship type)`
- Relationship types: prerequisite, data dependency, workflow sequence, shared resource, triggering
- The type reads from this use case outward:
  - `prerequisite` — the listed use case must complete first
  - `data dependency` — this use case reads data the listed one produces or holds
  - `workflow sequence` — the listed use case is the next step of the same process
  - `shared resource` — both use the same resource, in no fixed order
  - `triggering` — this use case automatically starts the listed one
- `workflow sequence` and `triggering` point forward, so a listed use case is not always one this use case waits for
- The two use cases at the ends of one relationship may each list it, with the type that
  reads true from their own side: `TEC-001` lists `CAP-001: Approve Closed Service Ticket
  (workflow sequence)` while `CAP-001` lists `TEC-001: Open Service Ticket (prerequisite)`.
  The Critical Dependencies Matrix carries one row per listed entry, so that pair appears
  in it twice, once per direction
- Example: `USR-001: User Authentication (prerequisite)`, `ADM-005: View Audit Log (shared resource)`
- With no dependency, write the output language's word for none, followed by the reason where
  it carries information: `None — triggered automatically by every use case that touches patient data`.
  `triggering` and `data dependency` have no opposite among the five types, so a use case on
  the receiving end of one writes that none line rather than inventing a sixth type

**Source**: Section of the requirements document this use case comes from, quoted in the document's own wording, with the document's own requirement or use-case identifier when it has one; with several documents, name the document before the section
- Example: `Source: §3.2 User management (REQ-101)`
- Example with several documents: `Source: core-spec.pdf, §3.2 User management`
- With a spreadsheet source, the sheet name and the requirement identifier stand in for the section: `Source: Requirements!REQ-101`; a sheet-less CSV counts as a spreadsheet source and names the file instead: `Source: requirements.csv!REQ-101`
- With a source that has no sections — pasted text, or an uploaded section-less file such as a plain-text file — cite the sentence itself, quoted in its own wording: `Source: «A member can reserve a spot in a class up to 7 days in advance»`
- An inferred use case cites the section or sentence that implies it, marked `(inferred)`

**User Story**: One per use case, in the standard format
- Example: `As a customer, I want to save items in a cart, so that I can buy them in one order later.`
- For a use case with no human actor (system roles), write the story as the role that benefits from the automation, and name that role in the story; it need not be a registered actor

**Acceptance Criteria**: 2-3 criteria in Given/When/Then form
- High-priority use cases only; the field is absent from a Medium or Low use case,
  rather than carrying the word for none

### Step 6: Pre-Delivery Verification

Before writing the file(s), verify silently:

- Numbering starts at 001 for each role prefix and is sequential
- Every role prefix is unique across the analysis
- Each use case code appears under exactly one role prefix; a role that inherits
  another's access states that in its description, without re-listing the inherited use cases
- Every use case carries every Step 5 field, with Priority assigned and a User Story written;
  `Acceptance Criteria` is the exception — a High-priority use case carries its 2-3 criteria,
  and the field is absent below High
- Every role carries its 2-3 sentence description
- Target length and input/output item counts match each use case's Priority (see Quality
  Guidelines); Main Flow has 3-7 steps, and a Low-priority use case's Variations carry
  exception paths only
- Dependencies use only the five declared relationship types and reference codes that exist in
  the analysis (anything else goes to Flagged Items)
- The Critical Dependencies Matrix (Excel: the Dependencies Matrix sheet) matches the use
  cases' Dependencies lists — the same code pairs with the same relationship types, in the
  same direction
- Headings, field labels, and priority values are in the output language, while codes,
  prefixes, and `Source` citations follow the source, as the Languages section requires
- Executive Summary counts match the body: roles, use cases, user stories, the High,
  Medium and Low priority counts, and the dependency count, which is the number of rows
  in the Critical Dependencies Matrix
- Ambiguities and contradictions found in Step 1 or Step 5 appear under Flagged Items
- Every functional requirement of the source is cited by at least one use case's `Source`, named
  under Flagged Items, or excluded by a special requirement the user gave — counted in the unit the
  source states them in, the same unit `Source` cites: a section in a document, a row in a
  spreadsheet, a sentence in pasted text or another section-less source
- Every non-functional requirement of the source is listed in the format's non-functional
  requirements section — the Appendix's subsection in the document formats, the Non-Functional
  Requirements table on Sheet 1 in the Excel workbook — or named under Flagged Items
- Word and PDF output is set to A4, and the filename to write follows the convention below

Fix every failed check silently, before writing the file.

### Step 7: Output Generation

Generate the deliverable(s) in the selected format(s) with role-based organization, following
the matching template in `references/format-templates.md`. Pick the branch per format, since a
platform may provide a document skill for one format and none for another:

- **For a format the platform provides a document skill for** — claude.ai's built-in file creation,
  or Claude Code with the `docx`/`xlsx`/`pdf` skills installed — use it; for `.docx` / `.xlsx` /
  `.pdf`, read and follow its documentation when the platform exposes it. On claude.ai, let the
  platform's file delivery present the file in the conversation — that delivery is the only
  reference to the file, so give no path and no download link. On Claude Code the document skill
  writes the file to disk, so report its absolute path, as the local-Python branch below does.
- **`.md` belongs to neither branch:** it needs no document skill. Deliver it as a file through
  the platform's file delivery where there is one, and by writing the file directly on Claude
  Code. If the platform cannot present a `.md` file, present the Markdown content in the
  conversation instead, under the filename the convention gives it.
- **For a format with no document skill (Claude Code without them, local Python):** build that file with a short Python script —
  `.docx` via `python-docx`, `.xlsx` via `openpyxl`, `.pdf` via `weasyprint`, falling back to
  `fpdf2` if weasyprint is unavailable or fails (load a Unicode TTF font when the text falls
  outside Latin-1). For a right-to-left output language,
  keep weasyprint for the PDF — it shapes RTL text and fpdf2 does not by default — and set
  paragraph direction in the Word file and sheet direction in the workbook (`openpyxl` exposes
  `sheet_view.rightToLeft`); the fpdf2 fallback is off for a right-to-left language,
  so if weasyprint is unavailable, ask the user to install it or take Markdown instead. Save to
  the working directory or a path the user gives you, and report the absolute file path. If a
  library is missing, ask the user before running `pip install`, or offer Markdown as a fallback.
- Page size: A4 for the Word and PDF files, on every platform
- With several formats, every file renders the same analysis: the same use cases, the same
  counts, the same flagged items

**Filename convention:** `Use_Cases_[Source_Name]_[LANG]_[YYYY-MM-DD].[ext]` — underscores
as field separators, ISO date, LANG = the uppercase ISO 639-1 code of the output language (EN, IT,
AR), or the shortest ISO code the language has when it has no two-letter one (`SCN` for Sicilian);
in the source name, spaces and every character outside letters, digits, hyphens and underscores
become underscores, and `[Source_Name]` is shortened to at most 60 characters so the whole filename
stays under 100; two languages must never share one filename. With one source file, `[Source_Name]`
is its name without the extension. With multiple source documents, it is a short combined name or
the project name; a source that never enters the analysis — unreadable, or carrying no requirements
content — does not count among them. With pasted text and no file, use the project or domain name. On regeneration,
append `_v2`, `_v3`, … before the extension when the filename would otherwise repeat, so the
earlier file is never overwritten; the filename keeps the first deliverable's date.

### Step 8: Final Summary

After delivering the output file(s), provide:

**Statistics**:
- Total roles identified
- Total use cases extracted
- Total user stories
- Dependency entries mapped, one per Critical Dependencies Matrix row

**Coverage Assessment**:
- Sections analyzed — the source's own units: document sections, spreadsheet sheets (the file
  itself for a sheet-less CSV), or the sentences of pasted text or another section-less source
- Confidence level — the first of these that applies: low when any source could not be read or
  carried no requirements, or most use cases rest on inference; medium when Flagged Items carry
  ambiguities or contradictions, or a share of the use cases is `(inferred)`; high when every
  functional requirement of the source reached a use case, no source was lost, and nothing is
  flagged
- Areas needing clarification

**Key Insights**:
- Most complex roles
- Critical dependencies
- Potential gaps or risks

**Next Steps Recommendation**:
- Follow-up questions, including every decision a Flagged Item leaves to the user
- Stakeholder review areas
- Integration suggestions

## Quality Guidelines

### Relevance-Based Detail Level

Detail level follows the Priority assigned in Step 5; input item counts cover the mandatory and
optional lists together:

**High-Priority Use Cases** (core functionality, frequently used, critical for business):
- Detailed Target descriptions (3-5 sentences)
- Comprehensive Input/Output lists (5-15 items each)
- Thorough dependency documentation

**Medium-Priority Use Cases** (supporting functionality, moderate use):
- Moderate Target descriptions (2-3 sentences)
- Essential Input/Output lists (3-8 items each)
- Important dependencies

**Low-Priority Use Cases** (edge cases, administrative tasks, infrequent use):
- Concise Target descriptions (1-2 sentences)
- Core Input/Output lists (2-5 items each)
- Critical dependencies only

### Writing Standards

- **Business language**: Name actions and data in the actor's business terms, not in implementation terms
- **Evidence-based**: Base all statements on actual document content
- **Inference marked**: Where a use case is inferred, give the reasoning and mark it `(inferred)`
- **Consistent terminology**: Use same terms throughout for same concepts
- **Defined acronyms**: Spell out each acronym the first time it appears
- **Numbers inside right-to-left text**: in a right-to-left output language, keep numeric runs — use case codes such as `ADM-001`, step numbers, dates, signed or unit-bearing values — reading left-to-right with direction marks, so a code or a unit never breaks apart

## Edge Cases

### Unclear, Incomplete, or Missing Information
- Extract with confidence what you can, and continue with the available information
- Create a "Flagged Items" section: name what is unclear or missing, explain why it matters,
  and suggest where the answer could be found
- A prerequisite dropped because a special requirement narrowed the analysis, a
  requirement the source itself rates `Won't have`, and — with several sources, where
  other sources keep the run alive — a source excluded because it cannot be read or
  carries no requirements, are recorded as Missing Information; the three flagged-item
  categories stay as they are
- Provide best-effort inferences with clear notation, and suggest clarifying questions

### Contradictory Requirements
- Note both contradictory statements and explain the conflict
- Suggest possible resolutions
- Record all of that under Flagged Items and continue to the deliverable; the user's decision
  belongs in Step 8's follow-up questions, rather than gating the file

### Source Without Requirements Content
- A document with no functional or requirements content — a brochure, a meeting transcript,
  a price list — yields no use cases
- Say what the document appears to be, and ask for the requirements document before extracting
- With several sources this applies per document: continue with the sources that carry
  requirements, name the one that does not under Flagged Items and in the completion message,
  and stop only when no source carries requirements content
- Never invent a catalog from material that describes no system behaviour

### Unreadable Input (Scanned or Image-Only PDF, Unparsable Attachment)
- A scanned, image-only PDF has no extractable text; some platforms also cannot parse other attachment types, such as legacy `.doc` on claude.ai
- Say plainly that the file's text cannot be read on this platform
- On Claude Code, offer to convert the file locally if a suitable tool is available (for example LibreOffice for legacy `.doc`), and continue from the converted copy
- Otherwise, ask for a text version, a searchable PDF, or a different format
- With several sources, continue from the readable ones, name the unreadable file under Flagged
  Items and in the completion message, and stop only when no source can be read
- Never guess or invent the document's content

### Very Large Documents

A source beyond roughly 100 pages, or a pasted, Markdown or spreadsheet source of comparable
length where pages do not exist:

- Offer to process in sections
- Create summary structure first
- Generate detailed use cases per section
- Continue each role's numbering across sections rather than restarting at 001 in a new section
- Write each section's completed use cases to the output file before generating the next section, where the environment supports incremental writes, so progress survives context limits
- Combine into final output
