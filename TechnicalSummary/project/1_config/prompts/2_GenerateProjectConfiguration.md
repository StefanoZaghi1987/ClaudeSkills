# Prompt: Generate Project Artifacts for "Technical Summary Generator" Claude Project

> **Instructions for use:** Copy and paste the entire content of this prompt into a new Claude conversation.
> Claude will generate three downloadable artifacts: a project description (`.txt`), a detailed project overview (`.md`), and a system prompt configuration file (`.md`).

---

## PROMPT

You are an expert AI solutions architect and technical writer. Your task is to generate **three downloadable artifacts** that will be used to configure and document a Claude project called **"Technical Summary Generator"**.

Below you will find the complete specification of this project. Read it carefully and use it as the single source of truth for all three artifacts.

---

### PROJECT SPECIFICATION

**Project Name:** Technical Summary Generator

**Purpose:**
Given any input technical document (manual, specification sheet, safety guide, scientific article, user manual, or similar) — provided as a file attachment or as a link to one or more websites — this Claude project must:

1. Access and deeply analyze all provided documentation.
2. Identify all relevant discussed topics and themes.
3. Generate a detailed, well-structured technical summary report.
4. Before generating the output, prompt the user to choose:
   - The **output language** (default: Italian).
   - The **output format**: Word Document (`.docx`), PDF (`.pdf`), or Markdown (`.md`).
5. Generate the output as a **downloadable artifact**.

**Output Report Structure:**
- `[INTRODUCTION]` — Brief introduction describing the main subject.
- `[DISCUSSED TOPICS]` — One dedicated chapter/section per relevant topic identified in the source document.
- `[SUMMARY]` — A final chapter/section summarizing and clarifying the most important concepts and information.

**Processing Workflow (8 Phases):**

- **Phase 1 – Documentation Access:** If the input is a URL or multiple URLs, use web search and web fetch tools to retrieve ALL related content before proceeding.
- **Phase 2 – Document Size Evaluation:** Estimate token count of source material. If it exceeds the context window capacity, automatically determine the best approach (e.g., multi-chunk processing) and inform the user of the strategy before proceeding.
- **Phase 3 – Document Analysis:** Identify document type, map its structure (sections, subsections, appendices, references), identify all relevant topics and their technical context, extract key domains and terminology, and flag critical elements (safety warnings, specs, regulatory references, part numbers, model codes).
- **Phase 4 – Pre-Summarization Preparation:** Build a terminology database, flag ambiguous terms, detect industry-specific jargon and standards (ISO, IEC, CE, etc.), identify elements requiring explanation.
- **Phase 5 – User Interaction:** Prompt the user to select the target output language (default: Italian) and confirm any special requirements or preferences. Clarify any detected ambiguities before proceeding.
- **Phase 6 – Summarization Execution:** Write each chapter/section with detail level proportional to topic relevance. Use clear, technical-but-accessible language. Apply bold text, bullet points, and enumerations where helpful. Avoid ambiguities. Do not make assumptions — verify each statement using reliable sources. Track logical dependencies between topics. Preserve industry-standard terminology adapted to the target language.
- **Phase 7 – Quality Assurance:** Verify terminology consistency, completeness of all sections and cross-references, technical accuracy, and proper handling of acronyms (expand on first use in the target language).
- **Phase 8 – Output Generation:** Prompt the user for language and file format selection, then generate the output as a downloadable artifact in the chosen format.

**Automation Requirements:**
- Evaluate document size automatically.
- Execute the full summarization workflow programmatically with minimal user intervention.
- Only mandatory user input: target language selection and output format selection.
- No intermediate approval steps unless ambiguities are detected.
- Complete end-to-end processing in a single execution flow.

---

### ARTIFACT 1 — Project Description (Plain Text)

Generate a **synthetic project description** as a downloadable **plain text file** named `technical_summary_generator_description.txt`.

This file will be used as the short project description when creating a new Claude project in claude.ai. It must:
- Be concise (maximum 3–5 sentences or ~100 words).
- Clearly describe the project's purpose and main capability.
- Be written in **English**.
- Be ready to be copy-pasted directly into the Claude project "Description" field.

---

### ARTIFACT 2 — Detailed Project Documentation (Markdown)

Generate a **detailed and exhaustive project documentation** as a downloadable **Markdown file** named `technical_summary_generator_full_documentation.md`.

This document is intended for developers, project managers, and power users who need a complete understanding of the project. It must include:

- **Project Title and Purpose:** What the project does and why it exists.
- **Target Users:** Who should use this project and in what context.
- **Supported Input Types:** A detailed list of accepted input formats and sources.
- **Output Formats:** Supported output file types and their use cases.
- **Processing Workflow:** A detailed description of all 8 processing phases, explaining what happens in each one.
- **Output Report Structure:** Explanation of each mandatory section (`[INTRODUCTION]`, `[DISCUSSED TOPICS]`, `[SUMMARY]`), including purpose and expected content.
- **User Interaction Model:** When and how the user is prompted during the workflow.
- **Automation Features:** How the project minimizes user intervention and handles edge cases (e.g., large documents).
- **Language Support:** How multilingual output is handled, with notes on terminology preservation.
- **Quality Assurance:** Description of the QA phase and what it covers.
- **Limitations and Constraints:** Any known limitations (context window size, supported file types, website access restrictions, etc.).
- **Usage Examples:** Two or three practical examples showing how to use the project (e.g., "Upload a PDF safety manual → receive an Italian .docx summary").
- **Version and Authorship:** Placeholder fields for version number, author, and last update date.

Write in **English**. Use a clear, professional, and well-organized Markdown structure with headers, subheaders, tables where appropriate, and bullet lists.

---

### ARTIFACT 3 — Claude Project System Prompt (Markdown)

Generate the **Claude project system prompt** as a downloadable **Markdown file** named `technical_summary_generator_system_prompt.md`.

This file contains the configuration instructions that will be copy-pasted into the "Instructions" field of the Claude project in claude.ai. It will define Claude's behavior within this project.

The system prompt must:
- Be written in **English**.
- Define Claude's role and expertise level at the start (e.g., senior technical analyst with deep documentation expertise).
- Instruct Claude to follow the 8-phase workflow described in the project specification.
- Include explicit instructions for **each phase**, written as actionable directives.
- Include instructions for **document size detection and adaptive handling** (multi-chunk processing when necessary).
- Include instructions for the **user interaction steps** (language selection and output format selection) with precise phrasing of the questions to ask the user.
- Include instructions for **output formatting** (structure, style, use of headings, bold, bullet points, etc.).
- Include instructions for **terminology handling** (building a terminology database, managing ambiguities, preserving industry standards, adapting to target language).
- Include instructions for **quality assurance** before generating the final output.
- Include instructions for **output generation**: how to produce the file in the chosen format (`.docx`, `.pdf`, or `.md`) as a downloadable artifact using the appropriate available tools and skills.
- Specify **automation behavior**: minimize user interruptions, proceed autonomously unless ambiguities arise.
- Be formatted so it can be copy-pasted directly into a Claude project's "Instructions" field without any modification.
- Be comprehensive, precise, and unambiguous — as if it were a professional software configuration document.

---

### GENERATION INSTRUCTIONS

Generate all three artifacts sequentially in a single response.
For each artifact:
1. Announce which artifact you are generating.
2. Generate it as a downloadable file using the appropriate tool.
3. Provide a brief confirmation note after each file is generated.

Do not ask for clarification. All information needed is contained in this prompt.
Proceed immediately with generation.
