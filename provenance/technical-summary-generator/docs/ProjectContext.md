# Technical Summary Generator — Full Project Documentation

> **Version:** 1.0.0
> **Author:** *(placeholder)*
> **Last Updated:** *(placeholder)*

---

## 1. Project Title and Purpose

**Project Name:** Technical Summary Generator

**Purpose:**
The Technical Summary Generator is a Claude AI project designed to automate the end-to-end process of reading, analyzing, and summarizing technical documentation. Given any technical source — uploaded as a file or provided as one or more URLs — the project produces a detailed, professionally structured summary report in the user's language of choice and preferred file format.

The project exists to save time for engineers, technical writers, QA analysts, project managers, and knowledge workers who regularly need to extract, organize, and communicate the essential content of complex technical documents.

---

## 2. Target Users

| User Profile | Context of Use |
|---|---|
| Engineers & Technicians | Rapidly understanding specifications, installation manuals, or safety guides |
| Technical Writers | Extracting source material to produce derivative documentation |
| Project Managers | Getting a structured overview of complex technical deliverables |
| Quality & Compliance Teams | Reviewing regulatory and standards-based documentation |
| R&D Analysts | Synthesizing scientific articles and research documents |
| Procurement / Supply Chain | Reviewing product data sheets and supplier documentation |

---

## 3. Supported Input Types

### 3.1 File Attachments
- PDF documents (`.pdf`)
- Word documents (`.docx`, `.doc`)
- Plain text files (`.txt`)
- Markdown files (`.md`)
- HTML files (`.html`)

### 3.2 Web Sources
- Single URL pointing to a webpage, article, or online document
- Multiple URLs (the project fetches and aggregates all content before processing)
- Online PDFs and documentation portals (where publicly accessible)

> **Note:** Pages behind authentication walls, paywalls, or bot-detection systems may not be accessible. The project will inform the user if a URL cannot be retrieved.

---

## 4. Output Formats

| Format | Extension | Best Use Case |
|---|---|---|
| Word Document | `.docx` | Editable reports for internal sharing, further editing, or printing |
| PDF Document | `.pdf` | Read-only finalized reports for archiving, distribution, or compliance |
| Markdown | `.md` | Developer-friendly output, documentation systems, version-controlled repos |

---

## 5. Processing Workflow — 8 Phases

### Phase 1 — Documentation Access
If the input includes one or more URLs, the project uses web search and web fetch tools to retrieve the full content of every linked page before any analysis begins. All retrieved content is consolidated into a single working corpus.

### Phase 2 — Document Size Evaluation
The project estimates the token count of the full source corpus. If the content exceeds the available context window:
- The project automatically determines the optimal multi-chunk processing strategy (e.g., sequential chunk analysis with rolling context summarization).
- The user is informed of the strategy and estimated processing time before execution begins.
- No user approval is required unless the strategy involves trade-offs that affect output completeness.

### Phase 3 — Document Analysis
- Identify the document type (manual, spec sheet, safety guide, scientific article, etc.)
- Map the document's structure: sections, subsections, appendices, references, figures, tables
- Identify all relevant topics and their technical context
- Extract key technical domains and terminology
- Flag critical elements: safety warnings, technical specifications, regulatory references, part numbers, model codes, and compliance marks (CE, ISO, IEC, etc.)

### Phase 4 — Pre-Summarization Preparation
- Build an internal terminology database mapping source terms to their target-language equivalents
- Flag ambiguous terms or phrases that require clarification
- Detect industry-specific jargon, standards references, and abbreviations
- Identify all elements that may require contextual explanation in the output

### Phase 5 — User Interaction
The project prompts the user with exactly two questions before generating the output:
1. **Language selection:** "In which language would you like the output report? (Default: Italian)"
2. **Format selection:** "In which format would you like the output file? Options: Word (.docx), PDF (.pdf), or Markdown (.md)"

If ambiguities were detected in Phase 4, additional clarification questions are asked at this point — one at a time, clearly explained.

### Phase 6 — Summarization Execution
- Write each chapter with detail proportional to the topic's relevance and depth in the source document
- Use clear, technical-but-accessible language appropriate for the target audience
- Apply formatting aids: **bold text** for key terms, bullet points for lists, numbered lists for sequential processes
- Track logical dependencies between topics to maintain coherent narrative flow
- Preserve industry-standard terminology, adapted to the target language
- Do not make assumptions — every factual statement must be traceable to the source material

### Phase 7 — Quality Assurance
Before generating the final output, the project performs an internal review:
- **Terminology consistency:** Ensure the same term is used uniformly throughout the report
- **Section completeness:** Verify all three mandatory sections are present and fully populated
- **Cross-reference accuracy:** Validate that references between sections are correct
- **Technical accuracy:** Double-check numerical values, specifications, and standards citations
- **Acronym handling:** Confirm every acronym is expanded on first use in the target language
- **Language quality:** Review grammar, fluency, and register for the target language

### Phase 8 — Output Generation
The project generates the final report as a downloadable artifact in the format chosen by the user in Phase 5. The file is named using the pattern:
`summary_[source_document_name]_[language_code].[extension]`

---

## 6. Output Report Structure

Every generated report follows this mandatory structure:

### `[INTRODUCTION]`
A concise introduction describing the main subject of the source document. It answers: *What is this document about? What is its purpose? Who is it intended for?*

### `[DISCUSSED TOPICS]`
One dedicated section per relevant topic identified during analysis. Each section:
- Has a clear, descriptive heading
- Explains the topic in technical but accessible language
- Includes relevant specifications, values, warnings, or standards where applicable
- Is ordered logically (following source document order or by topic relevance)

### `[SUMMARY]`
A final section that synthesizes and reinforces the most critical concepts and information. It provides a high-level takeaway for readers who need to quickly grasp the document's key content.

---

## 7. User Interaction Model

The project is designed for **minimal user intervention**:

| Step | User Action Required |
|---|---|
| Input | Provide file(s) or URL(s) |
| Phase 5 | Confirm output language (or accept default: Italian) |
| Phase 5 | Select output format (.docx / .pdf / .md) |
| Phase 4 (if triggered) | Answer clarification questions about ambiguous terms |

All other phases execute automatically without requiring user input or approval.

---

## 8. Automation Features

- **Automatic document type detection:** No need to specify the document type manually.
- **Adaptive size handling:** Large documents are automatically split and processed in chunks.
- **Terminology database:** Built automatically from source content; no manual input required.
- **End-to-end execution:** From input to downloadable output in a single conversation flow.
- **Edge case handling:** URL retrieval failures, oversized documents, and ambiguous terminology are handled gracefully with user notification.

---

## 9. Language Support

- **Default output language:** Italian
- **Any language supported:** The user can specify any language at Phase 5
- **Terminology adaptation:** Industry-standard terms are preserved in their internationally recognized form when no widely accepted target-language equivalent exists (e.g., ISO codes, model numbers, part references)
- **Acronym policy:** All acronyms are expanded on first use in the target language, with the original acronym retained in parentheses where useful

---

## 10. Quality Assurance

The QA phase (Phase 7) is a systematic internal review executed before output generation. It covers:
- Terminology consistency across the entire document
- Structural completeness (all three mandatory sections present)
- Technical accuracy of all cited values and specifications
- Proper cross-referencing within the report
- Acronym expansion on first use
- Language quality for the target output language

No manual QA steps are required from the user. The project self-corrects detected issues before generating the final file.

---

## 11. Limitations and Constraints

- **Context window:** Extremely large documents (e.g., thousands of pages) will be processed in chunks; this may increase processing time and, in rare edge cases, may result in minor loss of cross-document coherence.
- **URL access:** Authenticated pages, paywalls, and bot-protected sites cannot be accessed. The project notifies the user if a URL is inaccessible.
- **Supported file types:** Non-text formats such as scanned image-only PDFs (without OCR text layer) may have limited or no extractable content.
- **Language quality:** Output language quality depends on the richness of Claude's multilingual training data; rare or highly specialized languages may produce lower-quality translations.
- **No real-time data:** The project summarizes provided source material only; it does not independently search for additional context unless explicitly instructed to verify a claim.

---

## 12. Usage Examples

### Example 1 — Safety Manual Summary
> **Input:** Upload a PDF safety manual for industrial machinery (Italian source)
> **Language:** Italian
> **Format:** Word (.docx)
> **Output:** A structured `.docx` report with sections covering safety warnings, PPE requirements, emergency procedures, and regulatory compliance — ready for internal distribution.

### Example 2 — Technical Specification from a Website
> **Input:** Provide a URL to a product specification page on a manufacturer's website
> **Language:** English
> **Format:** Markdown (.md)
> **Output:** A `.md` file summarizing product features, technical parameters, certifications, and compatibility information — ready to be committed to a documentation repository.

### Example 3 — Scientific Article Review
> **Input:** Upload a scientific article in PDF format
> **Language:** Italian
> **Format:** PDF (.pdf)
> **Output:** A `.pdf` summary with an introduction to the research topic, sections for methodology, findings, and conclusions, and a final synthesis section — suitable for management briefing or knowledge-sharing.

---

## 13. Version and Authorship

| Field | Value |
|---|---|
| Project Name | Technical Summary Generator |
| Version | 1.0.0 |
| Author | *(to be filled)* |
| Last Updated | *(to be filled)* |
| Claude Project Type | Document Analysis & Summarization |
