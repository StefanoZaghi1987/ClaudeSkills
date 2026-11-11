# Output formats — training-manual-generator

Format-specific generation, file saving, and delivery. Applied during PHASE 5
(File Generation and Delivery).

## For Word Documents (.docx)

**Layout spec (every platform):** A4, 1" margins, Arial; body 12pt;
headings bold — level 1 at 16pt, level 2 at 14pt, level 3 at 13pt, level 4
at 12pt; real list numbering, never unicode bullets in text; one paragraph
per line break. For a right-to-left manual language, set paragraph direction
to right-to-left, as the "Right-to-left text" section of
[`local-python.md`](local-python.md) shows.

- **claude.ai, or Claude Code with the `docx` skill:** if the platform exposes
  document-skill documentation, read it BEFORE generation and follow it; the
  layout spec above applies on every platform.
- **Claude Code / local Python:** build the document with a short
  `python-docx` script implementing the layout spec above. If `python-docx`
  is missing, ask the user before running `<interpreter> -m pip install python-docx`
  ([`local-python.md`](local-python.md)), or offer Markdown as a fallback.

Reference implementation of the layout spec (python-docx, every platform with local Python):

```python
from docx import Document
from docx.shared import Mm, Pt

# style_font(): paste it from the "Word (.docx)" section of local-python.md
doc = Document()
for section in doc.sections:            # A4, 1" margins
    section.page_width, section.page_height = Mm(210), Mm(297)
    section.top_margin = section.bottom_margin = Mm(25.4)
    section.left_margin = section.right_margin = Mm(25.4)

style_font(doc.styles["Normal"], "Arial", Pt(12))
for name, size in (("Heading 1", 16), ("Heading 2", 14), ("Heading 3", 13), ("Heading 4", 12)):
    style_font(doc.styles[name], "Arial", Pt(size))
    doc.styles[name].font.bold = True

doc.add_paragraph("Training User Manual: [Topic]", style="Heading 1")
doc.add_paragraph("Introduction", style="Heading 2")
doc.add_paragraph("Content paragraphs are separate add_paragraph calls, never \\n in text.")
doc.add_paragraph("A bullet", style="List Bullet")      # the style owns the marker:
doc.add_paragraph("Another bullet", style="List Bullet")  # never type • into the text
doc.add_paragraph("A step", style="List Number")
```

Interpreter, fonts and encoding for this branch follow [`local-python.md`](local-python.md).

Critical rules:
- ✗ NEVER use `\n` for line breaks → use separate Paragraph elements
- ✗ NEVER type bullet characters into paragraph text → use the list styles above
- ✓ ALWAYS set page size explicitly
- ✓ ALWAYS use Arial font
- ✓ ALWAYS validate after creation

Optional for manuals >10 pages: a table of contents as a plain list of headings.
A live Word TOC field needs low-level field XML and a manual refresh in Word before
it shows anything — build the field only when the user asks for it; otherwise use
the plain list.

## For PDF Documents (.pdf)

- **claude.ai, or Claude Code with the `pdf` skill:** if the platform exposes
  document-skill documentation, read it BEFORE generation and follow it; the markdown
  content below is the same on every platform.
- **Claude Code / local Python:** build the PDF through the engine order in
  [`local-python.md`](local-python.md): LibreOffice converting the `.docx` built to the layout
  spec above first, then `weasyprint` rendering the same markdown content below, then
  `fpdf2` for left-to-right languages only. With weasyprint, the page-break HTML below works
  unchanged; with fpdf2, start a new page with its own page-break call. If a library is
  missing, ask the user before running `<interpreter> -m pip install`, or offer Markdown as a fallback.

```python
content = """
# Training User Manual: [Topic]

## Introduction
[Content with **bold** and *italic*]

## Topic Name

### Subtopic

Content with formatting:
- Bullet point
- Bullet point

**Key Concept**: Important info in bold.

### Another Subtopic

1. First step
2. Second step
3. Third step

## Summary
[Summary content]
"""

import markdown
from weasyprint import HTML, CSS

# A right-to-left language wraps the body in <html dir="rtl" lang="..."> (local-python.md)
HTML(string=markdown.markdown(content, extensions=["tables", "fenced_code"])).write_pdf(
    "Training_Manual_[Topic]_[LANG]_[YYYY-MM-DD].pdf",
    stylesheets=[CSS(string="@page { size: a4; margin: 1in; } body { font-family: Arial, sans-serif; font-size: 12pt; }")],
)
```

Page breaks:
```html
<div style="page-break-before: always;"></div>
```

## For Markdown Files (.md)

Structure:
```markdown
# Training User Manual: [Topic Name]

---

## Introduction

[Content with **bold** for emphasis, *italic* for definitions]

Key objectives:
- First objective
- Second objective

---

## [Topic Name]

### Key Concept A

Detailed explanation with **bold** and *italic*.

**Important**: Critical information.

#### Specific Detail

1. First step
2. Second step

---

## Summary

### Key Concepts Recap

- **Concept 1**: Explanation
- **Concept 2**: Explanation

### Critical Takeaways

1. First takeaway
2. Second takeaway

### Important Details

- Specific parameters, thresholds, and tools

### Closing Perspective

[1-2 paragraphs tying the manual together]

---

**End of Manual**
```

Best practices:
- One # for title (only one per document)
- ## for major sections
- ### for subsections
- #### for details
- Never skip levels
- Use --- for visual breaks
- Consistent list format (- or *)
- Blank lines before/after lists

## File saving

**Location:** wherever the platform saves generated files on claude.ai (let the platform deliver the file; do not construct paths); the working directory or a user-specified path on Claude Code (report the absolute path)

**Filename Convention:**
```
Training_Manual_[Primary_Topic]_[LANG]_[YYYY-MM-DD].[ext]
```
Example: `Training_Manual_Python_Fundamentals_IT_2026-08-27.docx`

Guidelines:
- Use underscores (not spaces)
- Include primary topic
- LANG = ISO 639-1 code of the manual's language (IT, EN, …), or the shortest ISO code the
  language has when it has no two-letter one (`SCN` for Sicilian) — two languages must
  never share one filename
- ISO date format (YYYY-MM-DD) — the day the manual is generated; a revision
  keeps the original date and changes only the version suffix
- Appropriate extension
- Under 100 characters
- Letters, digits, and underscores (the date keeps its hyphens)

**Revisions:** keep the convention and append `_v2`, `_v3`, … before the extension, so a
name already produced is never repeated — a file in the output directory on Claude Code,
a file this conversation already delivered on claude.ai.
