# The local-Python branch

Read "Picking the output branch" on every run of a generator skill: it decides which of the
three routes builds each output format. Read the rest on Claude Code when a format has no
document skill: the `docx`, `pdf` or `xlsx` skill is not installed, or it is installed but
its own tools are missing — Node with the `docx` package, or LibreOffice. Build that format
here instead. The same file ships in every document-generator skill of this repository.

## Picking the output branch

Pick the branch per format, since a platform may provide a document skill for one format and
none for another:

- **For a format the platform provides a document skill for** — claude.ai's built-in file
  creation, or Claude Code with the `docx`, `pdf` or `xlsx` skill installed — use it; read
  and follow its documentation when the platform exposes it. On claude.ai, let the platform's
  file delivery present the file in the conversation, and do not construct file paths or
  download links yourself. On Claude Code the document skill writes the file to disk, so
  report its absolute path.
- **`.md` belongs to neither branch:** it needs no document skill. Deliver it as a file
  through the platform's file delivery where there is one, and by writing the file directly
  on Claude Code. If the platform cannot present a `.md` file, present the Markdown content
  in the conversation instead, under the filename the convention gives it.
- **For a format with no document skill (Claude Code without them, local Python):** build
  the file with a short Python script, as the sections below direct. Save to the working
  directory or a path the user gives you, and report the absolute file path. If a library
  is missing, ask the user before running `pip install`, or offer Markdown as a fallback.
  A document skill whose own toolchain is missing (Node with the `docx` package,
  LibreOffice) counts as no document skill too: use this branch for that format.

## Interpreter and shell

- Run every command with the Bash tool: Git Bash on Windows.
- The interpreter is `python` where that runs Python 3. Otherwise use `python3` on Linux and
  macOS, and `py -3` on Windows. On Windows `python` can be the Microsoft Store stub, which
  prints "Python was not found" and exits 9009.
- Install a missing package only after the user agrees, and as
  `<interpreter> -m pip install <package>`, so the package goes into the interpreter that runs
  the script. If the user does not agree, offer Markdown. This rule also applies to the
  packages that read the input (`pypdf`, `python-docx`, `openpyxl`).
- If pip refuses with `externally-managed-environment` (PEP 668: Debian 12+, Ubuntu 23.04+,
  Homebrew Python), ask the user, then create a virtual environment outside the project —
  `<interpreter> -m venv ~/.venvs/claude-skills` — and install into it with its own
  interpreter, `~/.venvs/claude-skills/bin/python -m pip install <package>`
  (`Scripts/python.exe` in place of `bin/python` on Windows). That interpreter then runs every
  script. If the venv cannot be created for lack of `ensurepip`, Debian and Ubuntu need the
  `python3-venv` package: ask before installing it. Never pass `--break-system-packages`.
- When `~/.venvs/claude-skills` already exists, run the scripts with its interpreter.

## Text encoding

- Open every text file with `encoding="utf-8"`. Use `"utf-8-sig"` for a CSV file or a file
  that can start with a BOM. Without an explicit encoding, Python on Windows uses cp1252:
  `è`, `—`, `µ` and `³` then come out wrong, or the read fails.
- Write document text to the file, not to the console. If a script must print it, run the
  script with `PYTHONUTF8=1`.

## Reading the input

| Input | Route |
|---|---|
| PDF | `pypdf`. A scanned, image-only PDF has no text: the skill's unreadable-input rule applies |
| Word `.docx` | `python-docx`: the paragraphs, then the tables (`document.tables`) |
| Legacy `.doc`, `.rtf` | convert with LibreOffice — `soffice --headless --convert-to docx --outdir <dir> <file>` — then read the `.docx` |
| Excel `.xlsx` | `openpyxl`: `load_workbook(path, data_only=True)`, every sheet |
| A file behind a URL that the web tools do not return as text (for example a PDF) | download it with Python `urllib.request` into the working directory, then read it as above |

## Word (.docx)

Use `python-docx`. A document built from scratch is A4 on every section:
`section.page_width = Mm(210)` and `section.page_height = Mm(297)`. A document edited in place
keeps its own page geometry. python-docx cannot fill a table of contents. Write a plain
list of the headings, unless the user asks for a Word TOC field, which Word fills when the
file opens.

The heading styles of python-docx's default template name a theme font (`w:asciiTheme` and
its siblings in `w:rFonts`) and a theme colour. A theme font outranks the font that
`font.name` writes, so a heading set to Arial that way still renders in the theme's font.
Set a style's font, size and colour with this helper; it also writes the font and size that
right-to-left text takes:

```python
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import RGBColor


def style_font(style, name, size, rgb=RGBColor(0, 0, 0)):
    style.font.name, style.font.size, style.font.color.rgb = name, size, rgb
    rpr = style.element.rPr
    for theme in ("asciiTheme", "hAnsiTheme", "eastAsiaTheme", "cstheme"):
        rpr.rFonts.attrib.pop(qn(f"w:{theme}"), None)  # a theme font outranks w:ascii
    rpr.rFonts.set(qn("w:cs"), name)  # right-to-left text takes its font from w:cs
    for old in rpr.findall(qn("w:szCs")):  # and its size from w:szCs
        rpr.remove(old)
    rpr.sz.addnext(OxmlElement("w:szCs", {qn("w:val"): str(round(size.pt * 2))}))
```

For example `style_font(doc.styles["Heading 1"], "Arial", Pt(16))`.

## Right-to-left text

For Arabic, Hebrew, Persian or Urdu, python-docx has no direction API; write the elements
yourself:

- **Paragraph:** `<w:bidi/>` in each paragraph's `w:pPr`, table cells included. It also
  aligns the paragraph to the right. Do not also set `alignment = WD_ALIGN_PARAGRAPH.RIGHT`:
  on a right-to-left paragraph Word reads `right` as the end edge, which is the left.
- **Run:** `<w:rtl/>` in the `w:rPr` of each run of right-to-left script —
  `run.font.rtl = True`. A run holding only Latin text or a number stays without it.
- **Table:** `<w:bidiVisual/>` in the table's `w:tblPr`, so the first column is on the right.

Word can report a file as corrupt when its elements are out of schema order, so insert each
one before its successors:

```python
AFTER_BIDI = ("w:adjustRightInd", "w:snapToGrid", "w:spacing", "w:ind", "w:contextualSpacing",
              "w:mirrorIndents", "w:suppressOverlap", "w:jc", "w:textDirection",
              "w:textAlignment", "w:textboxTightWrap", "w:outlineLvl", "w:divId",
              "w:cnfStyle", "w:rPr", "w:sectPr", "w:pPrChange")


def set_rtl(paragraph):
    ppr = paragraph._p.get_or_add_pPr()
    if ppr.find(qn("w:bidi")) is None:
        ppr.insert_element_before(OxmlElement("w:bidi"), *AFTER_BIDI)


def set_rtl_table(table):
    tbl_pr = table._tbl.tblPr
    if tbl_pr.find(qn("w:bidiVisual")) is None:
        tbl_pr.insert_element_before(
            OxmlElement("w:bidiVisual"), "w:tblStyleRowBandSize", "w:tblStyleColBandSize",
            "w:tblW", "w:jc", "w:tblCellSpacing", "w:tblInd", "w:tblBorders", "w:shd",
            "w:tblLayout", "w:tblCellMar", "w:tblLook", "w:tblCaption", "w:tblDescription",
            "w:tblPrChange")
```

LibreOffice converts the `.docx` with these directions. On the weasyprint route, render the
HTML as `<html dir="rtl" lang="ar">` (the document's language code in place of `ar`):
direction and alignment follow, as long as the CSS sets no `text-align: left`.

## PDF — one engine order

Build the PDF from the Word file, so both formats share one layout. Try the engines in this
order, and use the first one that works:

1. **LibreOffice** converts the `.docx`:
   `soffice --headless --convert-to pdf --outdir <dir> <file.docx>`. Find it on `PATH`
   (`soffice`, `libreoffice`). If it is not there, look at
   `C:\Program Files\LibreOffice\program\soffice.exe` on Windows — the path holds a space,
   so quote it in Git Bash: `"C:/Program Files/LibreOffice/program/soffice.exe" --headless ...`
   — and at `/Applications/LibreOffice.app/Contents/MacOS/soffice` on macOS. LibreOffice shapes
   right-to-left text. It is the PDF route on Windows.
2. **weasyprint**, from HTML, when LibreOffice is not available. It shapes right-to-left text.
   On Windows it needs the GTK runtime, which `pip` does not install: `pip install weasyprint`
   succeeds, and `import weasyprint` then fails with `OSError`. Treat any exception on import
   as "not available".
3. **fpdf2**, last, and for left-to-right text only. fpdf2 does not search the system font
   folders, so register a Unicode TrueType font by its full path, both the regular and the
   bold face (`set_font(style="B")` fails without a bold face):
   - Windows: `C:\Windows\Fonts\arial.ttf` and `arialbd.ttf`. Write a Windows path in Python
     as a raw string or with forward slashes — `r"C:\Windows\Fonts\arial.ttf"` or
     `"C:/Windows/Fonts/arial.ttf"`: in a plain string `\a` is a control character
   - Linux: `/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf` and `DejaVuSans-Bold.ttf`
     (`fc-list` finds another one)
   - macOS: `/System/Library/Fonts/Supplemental/Arial.ttf` and `Arial Bold.ttf`
   - Chinese, Japanese or Korean text: a CJK font, such as Noto Sans CJK, or
     `C:\Windows\Fonts\msyh.ttc` on Windows. Arial and DejaVu have no CJK glyphs.

A right-to-left document uses route 1 or 2 only. When no route is available, tell the user
which engines are missing. Offer Word or Markdown. Ask before you install LibreOffice:
`winget install TheDocumentFoundation.LibreOffice` on Windows, or the package manager on
Linux and macOS.

## Saving

Save to the working directory or to a path the user gives. Report the absolute path of the
file.
