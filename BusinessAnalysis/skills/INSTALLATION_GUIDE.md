# Use Case Extractor Skill - Installation & Usage Guide

## Overview

The **Use Case Extractor** skill transforms requirements documents and functional specifications into structured, professional use case documentation. Built on 20+ years of business analysis best practices, this skill automates the extraction and organization of use cases by user role.

## What This Skill Does

✅ **Identifies all actors and user roles** from requirements documents  
✅ **Extracts explicit use cases** already defined in your documents  
✅ **Infers use cases** from functional requirements and business processes  
✅ **Structures each use case** with code, name, target, inputs, outputs, and dependencies  
✅ **Organizes by user role** for clear ownership and responsibility  
✅ **Exports in multiple formats**: Word (.docx), Excel (.xlsx), or Markdown (.md)  
✅ **Supports multiple languages** for international teams  

## Installation

### Method 1: Upload to Claude.ai

1. Go to your Claude Project in Claude.ai
2. Navigate to **Project Settings** → **Skills**
3. Click **Upload Skill**
4. Select the `usecase-extractor.skill` file
5. Click **Add Skill**

The skill is now available in your project!

### Method 2: Add to MCP-Compatible Applications

If you're using Claude through an MCP-compatible application:

1. Place `usecase-extractor.skill` in your skills directory
2. The skill will be automatically loaded
3. Verify by asking Claude: "What skills do you have access to?"

## Usage

### Basic Workflow

1. **Upload your requirements document**  
   Supported formats: PDF, DOCX, TXT, MD, RTF

2. **Claude will automatically trigger the skill** when it detects requirements analysis is needed

3. **Select your preferred language**  
   Claude will prompt: "Which language should be used for the output document?"
   - Default: English
   - You can specify any language

4. **Select your output format**  
   Claude will prompt with options:
   - Word Document (.docx) - Professional formatted document
   - Excel Spreadsheet (.xlsx) - Structured table format
   - Markdown File (.md) - Developer-friendly format
   - Multiple formats - Get several formats at once

5. **Receive your structured documentation**  
   Claude will generate downloadable file(s) organized by user role

### Example Interactions

**Example 1: Basic Requirements Analysis**
```
You: [Upload requirements.pdf]
     "Please analyze this requirements document and extract use cases"

Claude: [Analyzes document]
        "Which language should be used for the output document?
        Default: English"

You: "English"

Claude: "Please choose the output format(s)..."

You: "Word document"

Claude: [Generates professional Word document with role-based use cases]
```

**Example 2: Multi-Format Output**
```
You: [Upload functional-spec.docx]
     "Extract use cases in both Excel and Markdown format"

Claude: [Analyzes document, prompts for language]

You: "Italian"

Claude: [Generates both Excel and Markdown files in Italian]
```

**Example 3: Multiple Documents**
```
You: [Upload requirements-part1.pdf, requirements-part2.pdf]
     "Analyze both documents and create a comprehensive use case document"

Claude: [Analyzes all documents together, generates unified output]
```

## What the Skill Extracts

For each use case, the skill structures:

### Use Case Structure
- **Code**: Unique identifier (e.g., ADM-001, USR-003)
- **Name**: Action-oriented name (e.g., "Register New User")
- **Title**: Full formatted title (e.g., "ADM-001: Configure System Settings")
- **Target**: Clear description of the goal and business value
- **Input Data**: 
  - Mandatory: Required inputs for execution
  - Optional: Inputs that enhance functionality
- **Output Data**: Complete list of results, artifacts, notifications, and side effects
- **Dependencies**: Related use cases with relationship types

### Role Prefixes
The skill uses standard prefixes:
- **ADM** = Administrator
- **USR** = End User / General User
- **DEV** = Developer
- **OPR** = Operator
- **MGR** = Manager
- **SYS** = System (automated processes)
- **API** = API Consumer / External System
- **AUD** = Auditor
- **SUP** = Support Staff
- **CST** = Customer

Custom prefixes are created automatically for domain-specific roles (e.g., DOC for Doctor, TCH for Teacher).

## Output Examples

### Word Document Output
- Professional formatting with section headers
- Table of contents (for longer documents)
- Structured tables for use cases
- Color-coded by role
- Page breaks between sections
- Print-ready formatting

### Excel Spreadsheet Output
- One row per use case
- Filterable columns
- Summary statistics sheet
- Dependencies matrix
- Flagged items sheet
- Color-coded by priority

### Markdown Output
- Clear heading hierarchy
- Version control friendly
- Easy to integrate with Git/GitHub
- Developer-friendly format
- Can be converted to other formats

## Advanced Features

### Handling Large Documents
For documents over 100 pages, Claude will:
- Offer to process in sections
- Create summary structure first
- Generate detailed use cases per section
- Combine into final comprehensive output

### Ambiguity Detection
The skill identifies and flags:
- Unclear or contradictory requirements
- Missing critical information
- Areas needing clarification

These are documented in a "Flagged Items" section with recommendations.

### Dependency Mapping
The skill automatically identifies and categorizes:
- **Prerequisites**: Must complete first
- **Data dependencies**: Creates needed data
- **Workflow sequences**: Typical execution order
- **Shared resources**: Access same data/systems
- **Triggering relationships**: Automatic initiation

## Tips for Best Results

### Document Preparation
✅ **Include context**: Provide background about the project domain  
✅ **Define terms**: Include a glossary for specialized terminology  
✅ **Add structure**: Even basic headings improve extraction accuracy  
✅ **Mention user types**: Explicitly reference actors and roles  
✅ **Use action verbs**: Clear verbs for system behaviors (create, update, delete, notify)  
✅ **Specify inputs/outputs**: Be clear about what data goes in and comes out  
✅ **Provide examples**: Real examples help Claude understand context  

### Document Types That Work Well
- Functional requirements documents
- Business requirements documents
- System specification documents
- User need statements
- Business process descriptions
- Product requirement documents (PRDs)
- Software requirement specifications (SRS)

### Iteration and Refinement
If the initial output needs adjustment:
- Provide feedback on specific use cases
- Request additional detail for certain roles
- Ask for clarification on dependencies
- Request different priority classifications
- The skill learns from your feedback within the conversation

## Use Cases for This Skill

### 1. Agile Sprint Planning
Transform high-level product vision into sprint-ready user stories organized by persona with clear acceptance criteria.

### 2. Stakeholder Communication
Convert technical specifications into business-friendly documentation for stakeholder approval.

### 3. QA Test Planning
Generate structured use cases with inputs and outputs that map directly to test cases for comprehensive coverage.

### 4. Multi-Language Projects
Create requirements documentation in multiple languages for distributed international teams.

### 5. Requirements Traceability
Establish clear links between requirements and implementation with uniquely identified use cases.

### 6. Team Onboarding
Provide new team members with clear, structured documentation of system functionality organized by user role.

## Troubleshooting

**Q: The skill didn't trigger automatically**  
A: Explicitly mention "analyze requirements", "extract use cases", or "create user stories" in your message.

**Q: Some use cases seem missing**  
A: Check if they might be implied in the document. Ask Claude to "review the document for any missed use cases" or "infer additional use cases from business processes described".

**Q: The priorities don't seem right**  
A: Provide feedback like "Use case ADM-005 should be high priority because..." and ask Claude to adjust.

**Q: Can I get different formats later?**  
A: Yes! Just ask "Can you also provide this in Excel format?" and Claude will generate the additional format.

**Q: The language isn't quite right**  
A: Ask Claude to regenerate in a different language: "Please generate this in [language] instead".

## Technical Details

### Supported Input Formats
- PDF (text-extractable)
- Word Documents (.docx, .doc)
- Text Files (.txt)
- Markdown (.md)
- Rich Text Format (.rtf)

### Supported Output Formats
- Word Documents (.docx) - Microsoft Word 2010+
- Excel Spreadsheets (.xlsx) - Microsoft Excel 2010+
- Markdown (.md) - CommonMark standard

### Skill Components
- **SKILL.md**: Core extraction logic and workflow
- **references/examples.md**: Detailed extraction examples across domains
- **references/format-templates.md**: Output format templates and guidelines

## Version Information

**Skill Version**: 1.0  
**Created**: December 2025  
**Compatible With**: Claude Projects (Sonnet 4.5+)  
**License**: See project license terms  

## Support and Feedback

For best results:
- Ensure requirements documents are reasonably clear and complete
- Mention user roles explicitly or provide context for inference
- Describe business processes with sufficient detail
- Provide feedback during the conversation to refine output

The skill continuously improves through iterative use within the same project context.

## Getting Started Checklist

- [ ] Install the skill in your Claude Project
- [ ] Prepare your requirements document(s)
- [ ] Upload document and request use case extraction
- [ ] Select your preferred language
- [ ] Choose your output format(s)
- [ ] Review the generated documentation
- [ ] Provide feedback for any adjustments needed
- [ ] Download and use in your project!

---

**Ready to transform your requirements into structured use cases?**  
Upload your requirements document and let Claude's Use Case Extractor skill do the work!
