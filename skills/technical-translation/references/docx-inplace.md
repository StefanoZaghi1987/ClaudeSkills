# Translating a Word file in place

Read this on the DOCX-to-DOCX branch of Phase 7, when the format has no document skill and
the source is a `.docx`: the rules that keep the copy's formatting, the reference
implementation, and what to name under "Formatting not preserved". The interpreter, the
packages and the PDF engines are in [local-python.md](local-python.md).

## Rules

Copy the source file, open the copy with `python-docx`, and for every paragraph — body,
tables, headers and footers — write only the text nodes (`w:t`): the translation goes into
the paragraph's first `w:t`, every other `w:t` is emptied, and no run is removed (their
styles hold the formatting). Never set `Run.text`: its setter deletes everything in the run
but its properties — an inline picture (`w:drawing`, `w:pict`), a field (`w:fldChar`,
`w:instrText`: the page number in a footer), a tab, a break, a footnote or endnote
reference. The runs are `paragraph.iter_inner_content()` flattened (`python-docx` 1.0 or
newer): a `Run` as it is, a `Hyperlink` as its `.runs` — `paragraph.runs` skips the runs
inside a link, whose source text would stay. A field's displayed result — the `w:t` between
its `separate` and `end` `fldChar`: a PAGE number, a TOC's entries — is left as it is,
except in a `HYPERLINK` field, whose result is the link text; a field inside a paragraph
splits it into pieces translated one by one, so "Pagina {PAGE} di {NUMPAGES}" becomes
"Page {PAGE} of {NUMPAGES}". A TOC field shows its source-language entries until Word
updates the fields: name it under "Formatting not preserved".

## Reference implementation

`translate` below returns the translation of one piece of text:

```python
from docx import Document
from docx.oxml.ns import qn
from docx.text.hyperlink import Hyperlink

XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"


def field_results(root):
    """The w:t that show a field's cached result: a PAGE number, TOC entries."""
    found, fields = set(), []  # one [instruction, past "separate"] per open field
    for el in root.iter(qn("w:fldChar"), qn("w:instrText"), qn("w:t")):
        kind = el.get(qn("w:fldCharType"))
        if kind == "begin":
            fields.append(["", False])
        elif kind == "separate" and fields:
            fields[-1][1] = True
        elif kind == "end" and fields:
            fields.pop()
        elif el.tag == qn("w:instrText") and fields:
            fields[-1][0] += el.text or ""
        elif el.tag == qn("w:t") and any(
            shown and not code.lstrip().startswith("HYPERLINK") for code, shown in fields
        ):
            found.add(el)
    return found


def text_groups(paragraph, skip):
    """The paragraph's w:t, split where a field sits ("Pagina {PAGE} di {NUMPAGES}")."""
    groups = [[]]
    for item in paragraph.iter_inner_content():
        for run in item.runs if isinstance(item, Hyperlink) else [item]:
            for el in run._r:  # children only: a text box's w:t is out of reach
                if el.tag == qn("w:fldChar"):
                    groups.append([])
                elif el.tag == qn("w:t") and el not in skip:
                    groups[-1].append(el)
    return groups


def translate_paragraph(paragraph, translate, skip):
    for texts in text_groups(paragraph, skip):
        source = "".join(t.text or "" for t in texts)
        if source.strip():
            head = source[: len(source) - len(source.lstrip())]
            tail = source[len(source.rstrip()):]
            texts[0].text = head + translate(source.strip()) + tail
            texts[0].set(XML_SPACE, "preserve")
            for t in texts[1:]:
                t.text = ""


def paragraphs(container):  # the body, a header or footer, a table cell
    yield from container.paragraphs
    for table in container.tables:
        cells = {cell._tc: cell for row in table.rows for cell in row.cells}  # a merged cell once
        for cell in cells.values():
            yield from paragraphs(cell)


def translate_story(container, translate):
    skip = field_results(container._element)
    for paragraph in paragraphs(container):
        translate_paragraph(paragraph, translate, skip)


doc = Document(copy_path)
translate_story(doc, translate)
for section in doc.sections:  # plus the first-page and even-page ones, as below
    for part in (section.header, section.footer):
        if not part.is_linked_to_previous:
            translate_story(part, translate)
doc.save(copy_path)
```

## What to check after translating

When the first `w:t` is inside a link the whole translated paragraph becomes link text,
which is right for a paragraph that is only a link; a link whose `w:t` are emptied keeps its
address but shows nothing: name it under "Formatting not preserved". Visit a section's
header or footer only when it is not `is_linked_to_previous` (a linked one is the previous
section's, already translated), the first-page ones only when
`section.different_first_page_header_footer` is set, and the even-page ones only when
`document.settings.odd_and_even_pages_header_footer` is set (reading an absent one adds it).
Footnotes, endnotes, text boxes, content controls, and a run wrapped in tracked changes
(`w:ins`) or a `w:smartTag` are out of `python-docx`'s reach: name any left untranslated in
the completion message. Styles, page geometry, tables, images and headers/footers stay
exactly the source's. Formatting inside one paragraph (a bold word mid-sentence) is lost
when the sentence is restructured, and a picture inside a sentence ends up after the
translated sentence: name that under "Formatting not preserved".
