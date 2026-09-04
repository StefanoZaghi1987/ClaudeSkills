# Output formats — training-manual-generator

Format-specific generation, file saving, and delivery. Applied during PHASE 5
(File Generation and Delivery).

## For Word Documents (.docx)

**Layout spec (every platform):** A4, 1" margins, Arial; body 12pt;
headings bold — level 1 at 16pt, level 2 at 14pt, level 3 at 13pt, level 4
at 12pt; real list numbering, never unicode bullets in text; one paragraph
per line break. For a right-to-left manual language, set paragraph direction
to right-to-left.

- **claude.ai, or Claude Code with the `docx` skill:** if the platform exposes
  document-skill documentation, read it BEFORE generation and follow it; the
  layout spec above applies on every platform.
- **Claude Code / local Python:** build the document with a short
  `python-docx` script implementing the layout spec above. If `python-docx`
  is missing, ask the user before running `pip install python-docx`, or offer
  Markdown as a fallback.

Reference implementation of the layout spec (docx-js on claude.ai):
```javascript
const { Document, Packer, Paragraph, TextRun, 
        HeadingLevel, AlignmentType, LevelFormat } = require('docx');

// Page setup: A4, 1" margins
sections: [{
  properties: {
    page: {
      size: { width: 11906, height: 16838 },
      margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
    }
  }
}]

// Typography: Arial, proper sizing
styles: {
  default: { 
    document: { 
      run: { font: "Arial", size: 24 } // 12pt
    } 
  },
  paragraphStyles: [
    { 
      id: "Heading1",
      run: { size: 32, bold: true, font: "Arial" }, // 16pt
      paragraph: { spacing: { before: 240, after: 240 }, outlineLevel: 0 }
    },
    { 
      id: "Heading2",
      run: { size: 28, bold: true, font: "Arial" }, // 14pt
      paragraph: { spacing: { before: 180, after: 180 }, outlineLevel: 1 }
    },
    {
      id: "Heading3",
      run: { size: 26, bold: true, font: "Arial" }, // 13pt
      paragraph: { spacing: { before: 120, after: 120 }, outlineLevel: 2 }
    },
    {
      id: "Heading4",
      run: { size: 24, bold: true, font: "Arial" }, // 12pt
      paragraph: { spacing: { before: 100, after: 100 }, outlineLevel: 3 }
    }
  ]
}

// Lists: NEVER use unicode bullets
numbering: {
  config: [
    { 
      reference: "bullets",
      levels: [{ 
        level: 0, 
        format: LevelFormat.BULLET,
        text: "•",
        style: { paragraph: { indent: { left: 720, hanging: 360 } } }
      }]
    },
    { 
      reference: "numbers",
      levels: [{ 
        level: 0,
        format: LevelFormat.DECIMAL,
        text: "%1.",
        style: { paragraph: { indent: { left: 720, hanging: 360 } } }
      }]
    }
  ]
}
```

Critical rules:
- ✗ NEVER use `\n` for line breaks → use separate Paragraph elements
- ✗ NEVER type bullet characters into paragraph text → use the numbering config above
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
- **Claude Code / local Python:** render the same markdown content to PDF with a short
  `markdown` + `weasyprint` script (fall back to `fpdf2` if weasyprint is unavailable,
  fails to install, or fails to run, loading a Unicode TTF font from the system — for
  example `arial.ttf` on Windows or DejaVuSans on Linux — when the manual text falls
  outside Latin-1). For a right-to-left manual language, keep weasyprint — it shapes RTL
  text and fpdf2 does not by default; the fpdf2 fallback is off for a right-to-left
  language, so if weasyprint is unavailable, ask the user to install it or take Markdown
  instead. With weasyprint, the page-break HTML below works unchanged;
  with fpdf2, start a new page with its own page-break call. If a library is missing,
  ask the user before running `pip install`, or offer Markdown as a fallback.

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

HTML(string=markdown.markdown(content)).write_pdf(
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
- LANG = ISO 639-1 code of the manual's language (IT, EN, …) — two languages must
  never share one filename
- ISO date format (YYYY-MM-DD) — the day the manual is generated; a revision
  keeps the original date and changes only the version suffix
- Appropriate extension
- Under 100 characters
- Letters, digits, and underscores (the date keeps its hyphens)

**Revisions:** keep the convention and append `_v2`, `_v3`, … before the extension, so a
name already produced is never repeated — a file in the output directory on Claude Code,
a file this conversation already delivered on claude.ai.
