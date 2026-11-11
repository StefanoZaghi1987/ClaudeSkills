I need you to create three configuration artifacts for a new Claude project focused on generating training lesson user manuals from meeting recording traces.

Generate the following three downloadable artifacts:

1. **Project Description (project_description.txt)** - A concise, synthetic description suitable for Claude's project setup field

2. **Detailed Project Description (detailed_description.md)** - A comprehensive Markdown document explaining the project's purpose, capabilities, and workflow

3. **Project Instructions (project_instructions.md)** - Detailed instructions in Markdown format that will guide Claude's behavior when processing training materials


## PROJECT SPECIFICATIONS

### Purpose
Transform training lesson meeting recording traces into comprehensive, well-structured user manuals that serve as detailed documentation for all covered topics.

### Input Requirements
- Accept meeting recording traces as attached files
- Analyze and extract all relevant discussed topics and themes
- Identify technical context and topic relevance levels
- Track logical, temporal, and organizational dependencies between topics

### Output Structure
The generated user manual must include:

**[INTRODUCTION]**
- Brief overview of the training lesson's main focus
- Context and objectives

**[DISCUSSED TOPICS]**
- Dedicated chapter/section for each relevant topic
- Detail level weighted by topic relevance
- More relevant themes receive deeper analysis
- Clear technical explanations with practical examples

**[SUMMARY]**
- Synthesis of most important concepts
- Key takeaways and critical information details
- Consolidated view of all covered material

### Processing Instructions
The project must guide Claude to:

1. **Analysis Phase**
   - Read and thoroughly analyze the uploaded recording trace
   - Identify all relevant topics and themes
   - Determine technical context for each topic
   - Infer relevance levels if not explicitly stated
   - Map dependencies between topics (logical, temporal, organizational)

2. **Content Development**
   - Write clear, understandable content focused on end-user perspective
   - Use technical but accessible language
   - Apply formatting best practices:
     * Bold text for emphasis on key concepts
     * Bullet points for lists and enumerations
     * Clear section hierarchies
   - Avoid ambiguities by dividing complex concepts into distinct statements
   - Never make assumptions - verify statements with reliable sources
   - Highlight all relevant concepts, information details, and critical aspects

3. **User Interaction**
   - Prompt user to select output language (default: Italian)
   - Prompt user to choose output format:
     * Word Document (.docx)
     * PDF document (.pdf)
     * Markdown file (.md)

4. **Output Generation**
   - Create the document as a downloadable artifact
   - Ensure proper formatting for chosen file type
   - Maintain consistent structure throughout

### Quality Standards
- Accuracy: All information must be verifiable
- Clarity: Technical content must be understandable
- Structure: Logical organization with clear hierarchies
- Completeness: All relevant topics adequately covered
- Professionalism: Enterprise-grade documentation quality


## GENERATION REQUIREMENTS

For each of the three artifacts you create:

**project_description.txt**
- Maximum 500 characters
- Concise summary suitable for Claude's project description field
- Clear indication of project purpose

**detailed_description.md**
- Comprehensive explanation (1000-1500 words)
- Include: purpose, use cases, workflow, expected inputs/outputs
- Professional tone with clear section organization

**project_instructions.md**
- Step-by-step operational instructions for Claude
- Include specific behavioral guidelines
- Cover all interaction points and decision criteria
- Format as clear, actionable directives
- Include example scenarios if helpful

Generate all three artifacts now as downloadable files.