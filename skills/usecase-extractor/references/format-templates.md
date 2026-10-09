# Output Format Templates

This reference provides detailed templates for each supported output format.

## Common Structure (All Formats)

Every format renders the same organization: a title and metadata block, an Executive Summary with counts and key insights, one section per role (role description plus its use cases), then Dependencies Map, Flagged Items, and Appendix where the format can express them. The Executive Summary's Coverage Assessment value is the confidence level Step 8 reports in the conversation, so the file and the chat state the same judgement. Every use case carries the Step 5 fields in this order: Code, Name, Title, Priority, Target, Main Flow, Variations, Input Data (mandatory and optional), Output Data, Dependencies, Source, User Story, and — for a High-priority use case only — Acceptance Criteria. The sections below give the exact rendering per format.

A section with nothing to record is omitted: the Appendix's Glossary when the source document defines no domain terms, the Appendix's Non-Functional Requirements subsection (the workbook's Non-Functional Requirements table) when the source states none, the Dependencies Map's High-Level Workflow Sequences when no chain exists, a legend with no entries. Flagged Items is the exception, because an empty one is itself a finding about the source — the section always appears, an empty subsection inside it is omitted, and when nothing is flagged at all the section carries one line saying so in the output language. The Excel workbook always keeps its four sheets, and a sheet with no rows keeps its header row. This rule stops at the section level: inside a use case, a field with nothing to record follows the Step 5 none-rule.

The metadata block is the same in every format: Document Version, Analysis Date, Analyzed Document(s), Source Language(s), Output Language, Prepared By. Document Version starts at 1.0 and follows the regeneration counter: the `_v2` file prints 2.0, `_v3` prints 3.0. Analysis Date is the day this file was generated, so a `_v2` made later carries a later date than the filename's, which stays on the first deliverable's.

The headings and field labels below are printed in English because this file is written in English. In the deliverable they are written in the output language, while codes, prefixes, and `Source` citations follow the Languages section of `SKILL.md`.

## Markdown Format Template

```markdown
# [Project Name] - Use Cases and User Stories Analysis

**Document Version**: 1.0  
**Analysis Date**: [Current Date]  
**Analyzed Document(s)**: [List of source documents]  
**Source Language(s)**: [Language of each source document]  
**Output Language**: [Language of this document]  
**Prepared By**: Claude Use Case Extractor

---

## Executive Summary

- **Total Roles Identified**: X
- **Total Use Cases Extracted**: X
- **Total User Stories**: X
- **Coverage Assessment**: [High/Medium/Low]
- **Sections Analyzed**: [the source's own units — sections, sheets, or sentences]

### Key Insights

- Most Complex Role: [Role Name] with X use cases
- Critical Dependencies: X entries, one per Critical Dependencies Matrix row
- High-Priority Use Cases: X
- Medium-Priority Use Cases: X
- Low-Priority Use Cases: X

---

## Role: [Role Name] ([PREFIX])

**Description**: [2-3 sentence description of the role, its responsibilities, and its position in the system]

**Use Cases Count**: X

---

### Use Case [PREFIX]-001: [Use Case Name]

**Code**: [PREFIX]-001

**Name**: [Descriptive Action-Oriented Name]

**Title**: [PREFIX]-001: [Descriptive Action-Oriented Name]

**Priority**: [High/Medium/Low]

**Target**: [Goal description explaining what the user wants to accomplish, the business value, and relevant context; sentence count follows the assigned priority]

**Main Flow**:
1. [Actor action or system response]
2. [Next step]
3. [Continue to the outcome]

**Variations**:
- **[N]a. [Condition]**: [alternative path]
- **[N]b. [Error condition]**: [exception path]

**Input Data**:

*Mandatory*:
- [Required input item 1 with brief description if needed]
- [Required input item 2]
- [Required input item 3]
- [Additional required inputs...]

*Optional*:
- [Optional input item 1 with brief description]
- [Optional input item 2]
- [Additional optional inputs...]

**Output Data**:
- [Output item 1 - data created or modified]
- [Output item 2 - results or calculations]
- [Output item 3 - notifications or alerts]
- [Output item 4 - side effects like logs]
- [Output item 5 - status changes]
- [Additional outputs...]

**Dependencies**:
- [CODE-XXX]: [Use Case Name] (prerequisite)
- [CODE-YYY]: [Use Case Name] (data dependency)
- [CODE-ZZZ]: [Use Case Name] (workflow sequence)

**Source**: [§section in the document's own wording, plus its requirement ID when it has one; `(inferred)` when the section only implies the use case; with multiple sources, document name before the §section]

**User Story**: As a [role], I want to [goal], so that [benefit].

**Acceptance Criteria**:
1. Given [precondition], when [action], then [expected outcome]
2. Given [precondition], when [action], then [expected outcome]
3. [Additional criteria as appropriate]

---

[Repeat use case structure for each use case in this role]

---

## Role: [Next Role Name] ([NEXT-PREFIX])

[Continue with same structure for each role]

---

## Dependencies Map

### High-Level Workflow Sequences

Each chain follows `workflow sequence` and `triggering` dependencies in the direction the use
cases list them, so every arrow is an edge the Critical Dependencies Matrix already carries; a
chain adds no edge of its own.

1. **[Workflow Name]**:
   - [CODE-001]: [Use Case Name]
   - → [CODE-002]: [Use Case Name]
   - → [CODE-003]: [Use Case Name]

2. **[Another Workflow]**:
   - [CODE-XXX]: [Use Case Name]
   - → [CODE-YYY]: [Use Case Name]

### Critical Dependencies Matrix

| Use Case | Related Use Case | Relationship Type |
|----------|------------------|-------------------|
| [CODE-XXX] | [CODE-YYY] | prerequisite |
| [CODE-AAA] | [CODE-BBB] | data dependency |

---

## Flagged Items for Clarification

### Ambiguous Requirements
1. **[Requirement ID/Section]**: [Description of ambiguity] - *Suggestion: [How to clarify]*
2. [Additional ambiguous items...]

### Missing Information
1. **[Topic/Area]**: [What's missing] - *Impact: [Why it matters]* - *Where to look: [Where the answer could be found]*
2. [Additional missing items...]

### Contradictory Requirements
1. **Requirement A vs B**: [Description of contradiction] - *Recommendation: [Suggested resolution]*
2. [Additional contradictions...]

---

## Appendix

### Role Identifier Legend
- **[PREFIX]** = [Role name] — one line per prefix used in this analysis

### Relationship Type Legend
- One line per relationship type used, giving the term this document uses for it:
  prerequisite, data dependency, workflow sequence, shared resource, triggering
- The type is read outward from the use case that lists it, and from the first column
  of the Critical Dependencies Matrix
- Two use cases may list the same relationship, each from its own side, so one pair can
  appear in the matrix twice, once per direction

### Non-Functional Requirements
- **[Requirement]** — [§section]; constrains [CODE-XXX], [CODE-YYY] — one line per
  non-functional requirement the source states: performance, security, usability, compliance

### Glossary
- **Term 1**: Definition
- **Term 2**: Definition

### Analysis Methodology
Brief description of the extraction approach and any assumptions made.
```

---

## Word Document (.docx) Format Guidelines

### Document Structure

**Title Page**:
- Project Name
- Document Title: "Use Cases and User Stories Analysis"
- The shared metadata block named under Common Structure

**Table of Contents**:
- Automatically generated with heading styles
- Include page numbers recomputed when the builder supports it; otherwise drop the numbers rather than keep wrong ones
- Link to sections where the builder supports it

**Executive Summary** (Heading 1):
- Summary statistics in a formatted table — the same statistics as the Markdown Executive Summary
- Key insights in bullet points — the same insights as the Markdown template's Key Insights

**Each Role Section** (Heading 1):
- Role name and identifier
- Role description paragraph
- Use Cases Count line, as in the Markdown template

**Each Use Case** (Heading 2):
- Use structured tables for consistent layout:

| Field | Content |
|-------|---------|
| **Code** | [PREFIX]-XXX |
| **Name** | [Descriptive Name] |
| **Title** | [Full Title] |
| **Priority** | [High/Medium/Low] |
| **Target** | [Goal description] |
| **Main Flow** | [Numbered steps 1..N] |
| **Variations** | [Numbered alternative and exception paths] |

**Input Data Table**:

| Category | Input Item |
|----------|------------|
| Mandatory | [Item 1] |
| Mandatory | [Item 2] |
| Optional | [Item 3] |

**Output Data** (Bulleted list)

**Dependencies** (Formatted list with links if possible)

**Source** (Section reference line)

**User Story** (One-line standard format)

**Acceptance Criteria** (High-priority use cases: Given/When/Then list)

**Trailing sections** (after the last role): Dependencies Map, Flagged Items, Appendix — same content as the Markdown template, rendered with Word headings and tables

**Styling Requirements**:
- Heading 1: Role sections (Arial, 16pt, Bold, Navy Blue)
- Heading 2: Use case titles (Arial, 14pt, Bold, Dark Gray)
- Body text: Arial, 11pt
- Tables: Light gray header, alternating row colors
- Page breaks: Before each role section
- Margins: 1 inch all sides
- Line spacing: 1.15

---

## Excel Spreadsheet (.xlsx) Format Guidelines

The workbook renders the Appendix's content in three places — role identifiers in Sheet 1's Roles Summary Table, relationship types under the Sheet 3 matrix, and the non-functional requirements in Sheet 1's Non-Functional Requirements table. It carries no Glossary and no Analysis Methodology section, and it drops the Dependencies Map's High-Level Workflow Sequences, because Sheet 3 already carries the same edges as one row per dependency. It renders the "most complex role" insight through the Roles Summary Table's Use Case Count column, which the reader can sort, rather than as a separate statistics row. Where the platform's builder cannot express anything in this workbook, approximate it and name the approximation in the completion message, rather than claiming a feature the file does not carry.

### Sheet 1: Summary

**Title Row** (top of the sheet): `[Project Name] - Use Cases and User Stories Analysis`,
in the output language, as the Markdown template's title renders it

**Document Info Block** (below the title row):

| Field | Value |
|-------|-------|
| Document Version | 1.0 |
| Analysis Date | [Current Date] |
| Analyzed Document(s) | [List of source documents] |
| Source Language(s) | [Language of each source document] |
| Output Language | [Language of this workbook] |
| Prepared By | Claude Use Case Extractor |

**Statistics Table**:
| Metric | Value |
|--------|-------|
| Total Roles | X |
| Total Use Cases | X |
| Total User Stories | X |
| High Priority | X |
| Medium Priority | X |
| Low Priority | X |
| Dependency Entries (one per matrix row) | X |
| Coverage Assessment | [High/Medium/Low] |
| Sections Analyzed | [the source's own units — sections, sheets, or sentences] |

**Roles Summary Table**:
| Role Code | Role Name | Role Description | Use Case Count |
|-----------|-----------|------------------|----------------|
| ADM | Administrator | [2-3 sentence role description] | X |
| USR | End User | [2-3 sentence role description] | X |
| ... | ... | ... | ... |

**Non-Functional Requirements Table** (below the Roles Summary Table; omitted when the
source states none):

| Requirement | Source | Constrains |
|-------------|--------|------------|
| [Requirement as stated] | [§section or Sheet!ID, in the source language] | [CODE-XXX], [CODE-YYY] |

One row per non-functional requirement — the same content as the Appendix's Non-Functional
Requirements subsection in the document formats; the codes name the use cases it constrains.

### Sheet 2: Use Cases

**Column Headers** (Row 1, Frozen, Bold, Background Color):
1. Code
2. Role (the role's name)
3. Name
4. Title
5. Priority
6. Target
7. Main Flow
8. Variations
9. Input Data (Mandatory)
10. Input Data (Optional)
11. Output Data
12. Dependencies
13. Source
14. User Story

**Data Rows** (Starting Row 2):
- Each use case occupies one row
- Multi-line text where needed (wrap text enabled)
- High-priority rows carry their acceptance criteria inside the User Story cell, separated by newlines
- Data validation for Priority column (High/Medium/Low dropdown)
- Conditional formatting on the Priority column:
  - High Priority: Light red background
  - Medium Priority: Light yellow background
  - Low Priority: Light green background

**Column Widths**:
- Code: 12
- Role: 12
- Name: 25
- Title: 30
- Priority: 10
- Target: 50
- Main Flow: 40
- Variations: 40
- Input Data columns: 40 each
- Output Data: 40
- Dependencies: 35
- Source: 20
- User Story: 50

**Features**:
- AutoFilter enabled on header row
- Freeze panes on row 2
- Color-code rows by role (subtle background colors)
- Borders on all cells (light gray)

### Sheet 3: Dependencies Matrix

**One row per dependency** — the same lean table as the Markdown template's Critical Dependencies Matrix:

| Use Case | Related Use Case | Relationship Type |
|----------|------------------|-------------------|
| [CODE-XXX] | [CODE-YYY] | prerequisite |

**Relationship Type Legend** (under the matrix — this workbook's legend, as the Languages section requires): the same legend as the document formats' Appendix — one line per relationship type used, giving the term this workbook uses for it, with the type read outward from the first column of the matrix

### Sheet 4: Flagged Items

**Columns** — one row per flagged item:
1. Item Type (Ambiguous/Missing/Contradictory)
2. Reference (Document section or requirement ID)
3. Description (what is flagged and why it matters)
4. Recommendation (how to clarify the item, or where the answer could be found)

---

## PDF Document (.pdf) Format Guidelines

The PDF follows the Word Document guidelines — same title page, table of contents, role sections, use-case field tables, and styling — rendered as a PDF:

- Page size: A4, on every platform
- Fonts embedded in the file
- TOC page numbers recomputed when the builder supports it; otherwise drop the stale numbers rather than keep wrong ones
- Multi-line text wraps inside table cells with visible borders

---

## Format Selection Logic

**Recommend Word (.docx) when**:
- User needs stakeholder-facing documentation
- Professional presentation is priority
- Document will be printed or shared externally
- User mentions "report", "document", "presentation"

**Recommend Excel (.xlsx) when**:
- User needs to track, filter, or sort use cases
- Multiple team members will collaborate
- Integration with project management tools needed
- User mentions "spreadsheet", "tracking", "filtering", "analysis"

**Recommend PDF (.pdf) when**:
- The document must look the same everywhere and must not be edited
- It will be printed or attached to formal correspondence
- User mentions "PDF", "print", or "official copy"

**Recommend Markdown (.md) when**:
- User is developer or technical team
- Version control (Git) integration needed
- Documentation lives in code repository
- User mentions "GitHub", "GitLab", "repository", "version control"

**Recommend Multiple formats when**:
- Mixed audience (technical and business stakeholders)
- Different use cases (presentation + tracking)
- User explicitly requests multiple formats
- Project requires comprehensive documentation package
