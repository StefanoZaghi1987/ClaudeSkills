**Generate Technical Translation Project Configuration Files:**

I need you to create a complete Claude Project configuration for an automated technical document translation system from Italian to other languages (primarily English). Generate the following three artifacts as downloadable files:

## **ARTIFACT 1: Project Description (project_description.txt)**

Create a concise project description (150-200 words) for the Claude Project setup interface that summarizes:
- Primary purpose: automated translation of Italian technical documentation
- Core capability: Word/PDF input → translated Word output with formatting preservation
- Key features: multi-phase workflow, terminology consistency, technical accuracy
- Automation level: minimal user intervention (only language selection required)
- Target domains: industrial machinery, automation systems, manufacturing equipment

## **ARTIFACT 2: Detailed Project Documentation (project_documentation.md)**

Create a comprehensive Markdown document (1500-2500 words) with the following sections:

### 1. Project Overview
- Mission and scope
- Primary use cases and applications
- Key benefits and value proposition
- Technical capabilities summary

### 2. System Architecture
- Input specifications (formats, languages, size limits)
- Processing workflow (7 phases detailed)
- Output specifications
- Automation framework

### 3. Phase-by-Phase Workflow

**Phase 1: Document Size Evaluation**
- Token estimation methodology
- Context window capacity assessment
- Multi-chunk processing strategy for large documents
- Automatic tool activation logic
- User communication protocol

**Phase 2: Document Analysis**
- Document type identification (manual, spec sheet, safety guide, etc.)
- Structure mapping (sections, subsections, appendices)
- Technical domain extraction
- Critical element identification (warnings, specs, regulatory refs)
- Formatting pattern recognition

**Phase 3: Pre-Translation Preparation**
- Terminology database construction
- Numerical data and units preservation
- Ambiguity flagging mechanisms
- Industry-standard terminology detection (ISO, IEC, CE)
- Non-translatable element identification (codes, URLs, brands)

**Phase 4: User Interaction**
- Target language selection interface
- Special requirements confirmation
- Technical term handling preferences
- Default settings and options

**Phase 5: Translation Execution**
- Technical precision maintenance
- Industry-standard terminology adherence
- Consistency enforcement
- Safety warning translation protocols
- Data integrity preservation
- Multi-element translation (captions, tables, charts, diagrams)
- Tone adaptation strategies

**Phase 6: Quality Assurance**
- Terminology consistency verification
- Structure preservation validation
- Formatting fidelity checks
- Technical accuracy confirmation
- Acronym and abbreviation handling

**Phase 7: Output Generation**
- Formatting preservation techniques
- Visual element handling
- File naming conventions
- Artifact delivery

### 4. Fidelity Requirements
Detail the preservation requirements:
- Meaning, intent, and tone
- Document structure (sections, headings, organization)
- Formatting (fonts, styles, emphasis, spacing, layout)
- Data integrity (tables, numerical values, units, specifications)
- Visual elements (images, charts, diagrams with translated captions)
- Safety and regulatory content
- Technical terminology accuracy
- Natural language flow and readability

### 5. Technical Specifications
- Supported input formats: .docx, .pdf
- Source language: Italian (default/primary)
- Target languages: English (default), others selectable
- Output format: .docx (Word document)
- Context window management strategies
- Tool integration requirements

### 6. Automation Capabilities
- Automatic document size evaluation
- Programmatic workflow execution
- Minimal intervention design
- Error handling and ambiguity resolution
- End-to-end processing in single execution

### 7. Quality Standards
- Technical accuracy benchmarks
- Terminology consistency requirements
- Formatting fidelity metrics
- Completeness verification
- Regulatory compliance preservation

### 8. Best Practices
- Document preparation recommendations
- Terminology glossary usage
- Quality review protocols
- Common challenges and solutions

## **ARTIFACT 3: Project Instructions (project_instructions.md)**

Create detailed Claude Project custom instructions (800-1200 words) in Markdown format that will be pasted into the "Custom instructions" field. Structure as:

### Role Definition
Define Claude's role as an expert technical translator with 20+ years of experience in automation engineering and industrial machinery documentation.

### Core Mission
Automated translation of Italian technical documents to target languages with maximum fidelity, minimal user intervention, and complete formatting preservation.

### Operational Protocol

**STEP 1: Initial Document Assessment**
```
When a document is uploaded:
1. Automatically evaluate document size and token count
2. If size exceeds context window capacity, activate multi-chunk processing
3. Inform user of processing strategy
4. Proceed with analysis
```

**STEP 2: Automatic Document Analysis**
```
Analyze without prompting:
- Document type and purpose
- Structure hierarchy
- Technical domains and terminology
- Critical elements (safety, specs, regulatory)
- Formatting patterns
```

**STEP 3: Pre-Translation Preparation**
```
Build automatically:
- Terminology database
- Units and numerical data inventory
- Ambiguity flags
- Industry-standard term registry
- Non-translatable element list
```

**STEP 4: User Interaction (ONLY REQUIRED INPUT)**
```
Prompt user for:
- Target language selection (default: English)
- Any special translation preferences
- Technical term handling approach
Then proceed automatically with no further interruptions.
```

**STEP 5-7: Automated Translation and Output**
```
Execute automatically:
- Translation with technical precision
- Quality assurance checks
- Word document generation
- Artifact delivery with clear filename
```

### Processing Rules
- **Default behavior**: Fully automated execution after language selection
- **Document size handling**: Automatic evaluation and strategy selection
- **Tool usage**: Activate all necessary tools automatically (docx skill, file creation, etc.)
- **User interruption**: Only for language selection and critical ambiguities
- **Output requirement**: Always generate downloadable .docx artifact

### Fidelity Mandates
List absolute requirements for:
- Meaning and intent preservation
- Complete structure maintenance
- Formatting fidelity
- Data integrity
- Visual element handling
- Safety content accuracy
- Technical terminology consistency

### Technical Term Handling
Default approach: Translate technical terms using industry-standard equivalents, with option to preserve original term in parentheses on first use if requested by user.

### Quality Control Checks
Enumerate mandatory verification steps before output generation.

### Output Specifications
- Format: Microsoft Word (.docx)
- Filename: `[original_filename]_[target_language_code].docx`
- Delivery: Downloadable artifact via present_files tool
- Content: Complete translated document with preserved formatting

### Error Handling
Protocol for managing ambiguities, missing context, or technical uncertainties.

---

**Generate all three artifacts now as downloadable files, ensuring they are comprehensive, professionally written, and ready for immediate use in Claude Project setup.**
