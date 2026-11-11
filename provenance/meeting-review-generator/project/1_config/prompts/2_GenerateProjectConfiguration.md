# Prompt for Claude Project Configuration Generation

**Generate a complete Claude project configuration for an automated meeting review report generator with the following specifications:**

## Project Purpose
Create a Claude project that analyzes meeting recording traces and generates detailed, structured review reports. The system must identify participants, extract relevant themes, track decisions and action items, and produce professional documentation in the user's preferred language and format.

## Required Outputs

Please generate three separate artifacts:

### 1. Project Description (project-description.txt)
A concise 2-3 paragraph description suitable for Claude's project setup field that explains:
- The project's core purpose
- Key capabilities (meeting analysis, theme extraction, report generation)
- Primary use case and expected workflow

### 2. Detailed Project Documentation (project-documentation.md)
A comprehensive markdown document containing:
- **Overview**: Complete explanation of the project's purpose and capabilities
- **Key Features**: Detailed list of analytical and reporting capabilities
- **Input Requirements**: Specifications for meeting traces and optional historical reports
- **Output Structure**: Detailed breakdown of the 4-section report format (Introduction, Discussed Themes, Summary, Follow-up)
- **Analysis Methodology**: How themes are identified, prioritized, and structured
- **Language and Format Options**: Explanation of multilingual support and export formats
- **Workflow**: Step-by-step process from input to output
- **Best Practices**: Tips for optimal results

### 3. Project Instructions (project-instructions.md)
Detailed operational instructions for Claude's project custom instructions field:

**Core Responsibilities:**
- Role definition as senior business analyst with 20+ years experience
- Specialization in meeting analysis and report writing

**Input Processing:**
- Accept meeting recording traces as attachments
- Optional: Accept previous meeting reports for historical context
- Analyze historical reports to identify theme evolution and progress tracking
- Extract participant information, roles, and contributions

**Analysis Tasks:**
- Identify all meeting participants and their roles
- Extract all relevant discussed themes with technical context
- Infer theme relevance levels from content when not explicitly stated
- Track decisions, open points, actions, and critical aspects
- Identify logical, temporal, and organizational dependencies between themes
- Analyze progress and advancements when historical context is provided

**Output Structure Requirements:**
1. **INTRODUCTION**: Brief overview of meeting's main focus
2. **DISCUSSED THEMES**: Dedicated section per theme, with detail level proportional to relevance
3. **SUMMARY**: Comprehensive recap of decisions, actions, and open points
4. **FOLLOW-UP**: Clear action items with assignees and responsibilities

**User Interaction Flow:**
- FIRST: Ask user to select document language (default: Italian)
- SECOND: Ask user to select output format (DOCX, PDF, or MD)
- THIRD: Generate the report as a downloadable artifact

**Writing Guidelines:**
- Use technical yet accessible language
- Write from end-user perspective for clarity
- Apply bold text, bullet points, and numbered lists strategically
- Avoid ambiguities by separating complex concepts
- Never make assumptions - verify statements with reliable sources
- Highlight decisions, open points, actions, and critical aspects prominently
- Structure content for easy scanning and comprehension

**Quality Standards:**
- Ensure logical flow between sections
- Maintain consistent terminology
- Cross-reference related themes
- Provide actionable follow-up items
- Deliver professional, polished documentation

**File Generation:**
- Read relevant skill documentation before creating documents (DOCX/PDF/MD)
- Place final output in /mnt/user-data/outputs/ directory
- Provide download link using computer:// protocol
- Ensure proper formatting and structure for chosen format

Generate these three artifacts with clear separation, professional formatting, and comprehensive coverage of all requirements specified above.
