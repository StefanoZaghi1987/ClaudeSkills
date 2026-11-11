# Report structure and quality standards

Reference for Phase 6 (report writing) and Phase 7 (quality assurance) of `SKILL.md`.

## Writing rules

- **Detail level**: proportional to topic relevance. Major topics get full sections; minor
  topics may be grouped under a broader heading.
- **Summarize, don't reproduce**: retell each topic in the report's own words. Keep verbatim
  only what must stay exact: definitions, warnings, and specification values.
- **Language register**: technical but accessible. Explain domain-specific terms on first use.
- **Factual integrity**: every statement must be directly traceable to the source. Do not
  infer, assume, or fabricate. If something is not stated in the source, do not include it.
- **Terminology**: apply the Phase 4 terminology database. Preserve internationally
  recognized terms (ISO codes, part numbers, model codes). Adapt all other terminology to
  the target language.
- **Acronyms**: expand every acronym on its first use. Format: *Full Name (ACRONYM)* or
  *ACRONYM (Full Name)* depending on which form appears first in the source.
- **Numbers inside right-to-left text**: in a right-to-left report language, keep numeric
  runs — specification values, tolerances, part numbers, standard references, dates —
  reading left-to-right with direction marks, so a sign or a unit never detaches from its
  value.

## Formatting within the report

- `##` headings for the three mandatory top-level sections
- `###` subheadings for individual topics within the topics section
- **Bold** for key technical terms, critical values, and important warnings
- Bullet points (`-`) for lists of properties, features, or items
- Numbered lists for sequential steps or processes
- Tables for comparing multiple values, parameters, or specifications

## Mandatory report structure

The report must contain exactly these three top-level sections, in this order. Write each
heading plain (no brackets, no all-caps) in the report's language: *Introduction /
Discussed Topics / Summary* in English, *Introduzione / Argomenti trattati / Sintesi* in
Italian; other languages follow the same pattern.

### Introduction

A concise introduction (1–3 paragraphs) answering:

- What is this document about?
- What is its main purpose?
- Who is the intended audience?
- What technical domains does it cover?

### Discussed Topics

One `###` subsection per relevant topic identified in the source. Each subsection:

- Has a clear, descriptive title
- Thoroughly explains the topic as presented in the source
- Includes all relevant technical details, values, warnings, standards references, specs
- Is ordered logically (following source order, or by relevance if the source lacks structure)

### Summary

A final synthesis section (2–5 paragraphs, or a structured list of key takeaways) that:

- Reinforces the most critical concepts and information
- Provides a high-level takeaway for quick understanding
- Highlights safety-critical information, compliance requirements, or actionable
  recommendations

## Quality Assurance Checklist

Check and silently correct, before the output file is written:

1. **Terminology consistency**: same term used uniformly throughout.
2. **Section completeness**: all three mandatory sections present and fully populated.
3. **Technical accuracy**: all numerical values, specs, part numbers, standards citations
   match the source exactly.
4. **Cross-reference integrity**: internal references point to sections that exist.
5. **Acronym policy**: every acronym expanded on first occurrence.
6. **Language quality**: grammatical correctness, fluency, appropriate register.
7. **Compression**: the report retells the source; no long passages are copied verbatim.
8. **Topic coverage**: every topic Phase 3 identified reaches Discussed Topics, on its own
   or grouped under a broader heading — none is silently dropped. Where Phase 2 chunked the
   corpus, every chunk is represented, since a chunk can fall out of the rolling summary.
