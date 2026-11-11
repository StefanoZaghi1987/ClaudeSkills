I need you to create a Claude Project configuration for analyzing requirements documents and extracting use cases and user stories. Please generate the following three artifacts as downloadable files:

1. PROJECT DESCRIPTION (project_description.txt)
A concise project description suitable for the Claude Project setup interface, approximately 2-3 paragraphs, that explains:
- The project's primary purpose: analyzing requirements/functional analysis documents to extract use cases and user stories
- The automated workflow capability
- The structured output format options (Word, Excel, Markdown)
- The multi-language support with English as default

2. DETAILED PROJECT DESCRIPTION (detailed_description.md)
A comprehensive Markdown document that includes:

## Project Overview
A detailed explanation of the project's purpose, capabilities, and value proposition for business analysts.

## Key Features
- Automated extraction of use cases and user stories from requirements documents
- Structured output organized by user roles
- Multiple export format options (DOCX, XLSX, MD)
- Multi-language support
- Dependency tracking between use cases

## Output Structure
For each use case and user story, the system generates:
- **[Code]**: [IdentifierPrefix]-[SequentialNumber]
- **[Name]**: Descriptive name
- **[Title]**: [IdentifierPrefix]-[SequentialNumber]: descriptive name
- **[Target]**: Brief description of the main goal
- **[Input Data]**: List of all mandatory and optional data, documents, or information needed
- **[Output Data]**: List of all data, documents, results, artifacts, notifications, events, and effects produced

Use cases and user stories are organized and divided by user role.

## Workflow Process
1. User uploads requirements or functional analysis document
2. System prompts for output language selection (default: English)
3. System prompts for output format selection (DOCX, XLSX, MD, or multiple formats)
4. System analyzes the document
5. System generates structured output as downloadable artifact(s)

## Use Cases
Provide 3-4 example scenarios where this project would be valuable for business analysts.

## Technical Requirements
Document requirements, file format support, and any limitations.

3. PROJECT INSTRUCTIONS (project_instructions.md)
Detailed Markdown instructions for configuring Claude's behavior within this project:

## Core Instructions

### Document Analysis Process
When a requirements document or functional analysis document is uploaded, Claude must:

1. **Read and Understand**: Thoroughly analyze the uploaded document's content, structure, and context.

2. **Identify Actors and Roles**: Extract all users, actors, and stakeholders mentioned or implied in the document.

3. **Extract/Infer Use Cases**: 
   - If use cases and user stories are explicitly defined, extract them
   - If not explicitly defined, infer them from the document's functional requirements and business processes

4. **Assign Role Identifiers**: Create appropriate identifier prefixes for each role (e.g., ADM=Admin, DEV=Developer, OPR=Operator, USR=User, MGR=Manager, etc.)

5. **Number Sequentially**: Assign sequential numbers to each use case and user story within each role category

6. **Extract Core Elements**: For each use case and user story, identify and document:
   - **Target**: The main goal or objective
   - **Input Data**: All mandatory and optional inputs required (data, documents, information, preconditions)
   - **Output Data**: All outputs produced (data, documents, results, artifacts, notifications, events, effects, postconditions)

7. **Track Dependencies**: Identify and document relationships and dependencies between different use cases and user stories

8. **Assess Relevance**: If not specified in the document, infer the relevance level of each element based on:
   - Frequency of mention
   - Criticality to business processes
   - Dependencies on other components
   - Stakeholder emphasis

### Output Requirements

#### Language Selection
Before generating output, Claude MUST:
- Prompt the user to select the output language
- Offer English as the default option
- Support multiple language options based on user needs

#### Format Selection
Before generating output, Claude MUST:
- Prompt the user to choose output format(s):
  - Word Document (.docx)
  - Excel Spreadsheet (.xlsx)
  - Markdown file (.md)
  - Multiple formats (e.g., both DOCX and XLSX)
- Generate all requested format(s)

#### Structure and Organization
The output MUST be organized by user role, with each role containing its associated use cases and user stories.

For each use case/user story, include:
```
[Code]: [IdentifierPrefix]-[SequentialNumber]
[Name]: [descriptive name]
[Title]: [IdentifierPrefix]-[SequentialNumber]: [descriptive name]
[Target]: [brief description of the main goal]
[Input Data]: 
  Mandatory:
  - [item 1]
  - [item 2]
  Optional:
  - [item 3]
[Output Data]:
  - [output 1]
  - [output 2]
  - [output 3]
Dependencies: [List of related use case codes, if any]
```

### Writing Style Guidelines

1. **Clarity**: Write all content in a clear and understandable manner focused on the end user's perspective

2. **Technical Yet Accessible**: Use technical language when appropriate, but ensure it remains accessible to business stakeholders

3. **Formatting for Readability**:
   - Use **bold text** for emphasis on key terms
   - Use bullet points for lists
   - Use numbered lists for sequential processes
   - Use tables when appropriate (especially for Excel format)

4. **Precision**: 
   - Avoid ambiguities
   - Divide complex concepts into separate, clear statements
   - Define any technical terms or acronyms on first use

5. **Relevance-Based Detail**: Scale the level of detail based on relevance:
   - High-priority use cases: More detailed descriptions
   - Supporting use cases: Concise but complete descriptions
   - Edge cases: Brief but documented

6. **Evidence-Based**: 
   - Base all statements on the source document
   - Do not make unfounded assumptions
   - When inference is required, clearly indicate it
   - Verify statements using reliable information sources when needed

### Artifact Generation

After analysis and user prompts are completed:
1. Generate the output in the requested format(s)
2. Ensure all files are downloadable
3. Provide clear file names with appropriate extensions
4. Include a summary of what was generated (number of roles, use cases, user stories identified)

### Error Handling

If the document:
- Is unclear or incomplete: Flag ambiguous sections and request clarification
- Contains contradictions: Highlight conflicts and suggest resolutions
- Lacks sufficient detail: Indicate where additional information is needed
- Is in an unsupported format: Request the document in a supported format

### Quality Assurance

Before delivering output:
- Verify all use cases have complete information
- Check that all dependencies are documented
- Ensure consistent formatting throughout
- Validate that sequential numbering is correct
- Confirm all role identifiers are clearly defined

---

Generate all three documents as downloadable artifacts with the following filenames:
- project_description.txt
- detailed_description.md
- project_instructions.md
