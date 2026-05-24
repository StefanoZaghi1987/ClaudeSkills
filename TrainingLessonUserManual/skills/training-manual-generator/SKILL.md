---
name: training-manual-generator
description: Transform meeting recording traces from training sessions into comprehensive, professional user manuals. Automatically analyzes content, identifies topics with relevance levels, and generates structured documentation in Word, PDF, or Markdown formats. Use when users upload training transcripts, meeting traces, or request documentation from training sessions.
---

# Training Lesson User Manual Generator

A specialized skill for transforming training session recording traces into comprehensive, professional user manuals with intelligent content analysis, adaptive detail levels, and multi-format output.

## Overview

This skill bridges the gap between ephemeral training content and permanent, accessible knowledge documentation. It performs deep analysis of meeting traces, identifies topics with relevance assessment, maps dependencies, and generates enterprise-grade manuals that serve as effective reference materials.

**Key Capabilities:**
- **Intelligent Content Analysis**: Automatic topic identification with relevance levels
- **Adaptive Writing**: Content depth proportional to topic importance
- **Multi-format Support**: Word (.docx), PDF (.pdf), or Markdown (.md)
- **Multi-language**: Any language, Italian default
- **Quality Assurance**: Automated checks with minimal reporting

## Operating Modes

### Default: Semi-Automatic Mode

Confirmations at key decision points:
1. After analysis: Summary of identified topics
2. Language selection
3. Format selection
4. Final checkpoint before generation

### Configuration Options

Users can request different interaction levels:
- **"Fully automatic"**: Minimal interaction, use defaults (Italian, Word)
- **"Interactive mode"**: Additional confirmations for structure decisions
- **"Quick mode"**: Skip analysis summary, use first available defaults

## Activation Triggers

The skill activates intelligently when:

**Explicit Triggers:**
- "Generate training manual"
- "Create user manual from this training"
- "Document this training session"
- "Turn this into a manual"

**Intelligent Detection:**
- User uploads file with training-like content (transcripts, meeting traces)
- File contains timestamps, speaker labels, or training terminology
- Content structure suggests instructional/educational context

**Optional Confirmation:**
If content is ambiguous, ask:
> "It looks like you've uploaded training content. Would you like me to generate a comprehensive user manual from it?"

## Workflow

### PHASE 1: Analysis and Understanding

#### Step 1.1: Content Reception

When training content is detected or requested:

```
✓ File received: [filename]
⚙ Analyzing training content...
```

#### Step 1.2: Deep Analysis

Perform comprehensive content analysis:

**A. Topic Identification**
- Read entire recording trace systematically
- Extract all discussed topics, themes, and concepts
- Note technical terminology and methodologies
- Identify learning objectives and target audience

**B. Relevance Assessment**

Use multi-factor analysis to determine topic importance:

**Explicit Indicators** (when present):
- Direct emphasis: "This is critical", "Key point", "Most important"
- Repetition frequency
- Time allocation
- Instructor emphasis

**Inference Criteria** (when explicit indicators absent):
- **Duration**: Time spent on topic
- **Depth**: Level of detail provided
- **Examples**: Number of practical examples
- **Questions**: Discussion volume generated
- **Position**: Introduction order (foundations vs supplementary)
- **Cross-references**: How often other topics reference it

**Classification:**
- **HIGH**: Core concepts, critical procedures (800-1500 words per topic)
- **MEDIUM**: Supporting concepts, useful procedures (400-800 words)
- **LOW**: Supplementary topics, tangential discussions (150-400 words)

**C. Dependency Mapping**

Identify three types of relationships:

1. **Logical**: Prerequisites (Topic A → Topic B)
2. **Temporal**: Sequential learning flow
3. **Organizational**: Thematic groupings

#### Step 1.3: Analysis Summary

Present executive summary to user:

```markdown
📋 ANALYSIS COMPLETE

Main Focus: [2-3 sentence description]

Primary Topics Identified:
1. [Topic name] - HIGH relevance
2. [Topic name] - HIGH relevance
3. [Topic name] - MEDIUM relevance
4. [Topic name] - MEDIUM relevance
5. [Topic name] - LOW relevance
...

Target Audience: [Identified audience]
Estimated Manual Length: ~[X] pages

⚠ Issues Detected: [If any: gaps, unclear sections, undefined terms]

Ready to proceed with manual generation?
```

**Quality Checks (Internal):**
- [ ] All topics identified
- [ ] Relevance levels assigned
- [ ] Dependencies mapped
- [ ] No critical gaps in understanding

**Report Only If Issues Found:**
- Missing context for technical terms
- Incomplete sections that need clarification
- Ambiguous content requiring user input

---

### PHASE 2: User Configuration

#### Step 2.1: Language Selection

**Prompt:**
```
🌐 Language Selection

In which language should the manual be written?

Default: Italian (Italiano)
Other options: English, Spanish, German, French, or any language

[Skip to use Italian]
```

**Handling:**
- No response or "skip" → Italian
- "Italian"/"Italiano"/"default" → Italian
- Any other language → Use specified language
- Apply language to ALL content: headings, text, labels

#### Step 2.2: Format Selection

**Prompt:**
```
📄 Output Format

Select format for your training user manual:

1. Word Document (.docx) - Editable, professional formatting [RECOMMENDED]
2. PDF Document (.pdf) - Fixed layout, print-ready
3. Markdown File (.md) - Plain text, version control friendly

Choose: [1/2/3 or docx/pdf/md]
```

**Handling:**
- 1, "Word", "docx", ".docx" → Word document
- 2, "PDF", "pdf", ".pdf" → PDF document  
- 3, "Markdown", "md", ".md" → Markdown file
- No response → Ask again with default suggestion

---

### PHASE 3: Content Generation

#### Structure Overview

Generate manual with three main sections:

```
MANUAL STRUCTURE
├── 1. INTRODUCTION
│   ├── Training Overview
│   ├── Context and Relevance
│   └── Learning Objectives
│
├── 2. DISCUSSED TOPICS (Core)
│   ├── Topic 1 (HIGH) - Comprehensive
│   ├── Topic 2 (HIGH) - Comprehensive
│   ├── Topic 3 (MEDIUM) - Solid
│   ├── Topic 4 (MEDIUM) - Solid
│   └── Topic 5 (LOW) - Concise
│
└── 3. SUMMARY
    ├── Key Concepts Recap
    ├── Critical Takeaways
    ├── Important Details
    └── Closing Perspective
```

#### Section 1: INTRODUCTION

**Required Components:**

1. **Training Overview** (2-3 paragraphs)
   - Main focus and primary objective
   - Topics covered and their importance
   - Target audience and expected background

2. **Context and Relevance** (1-2 paragraphs)
   - Why this training matters
   - Real-world applications
   - Business value and broader goals

3. **Learning Objectives** (bullet list)
   - What learners will be able to do
   - Specific knowledge/skills gained
   - Tools/methodologies understood

**Quality Standards:**
- Welcoming, professional tone
- Accessible yet technically credible
- Concise but comprehensive (1-2 pages)
- Sets voice for entire manual

---

#### Section 2: DISCUSSED TOPICS

**Organization Principles:**

1. **Topic Sequencing:**
   - Logical prerequisites first
   - Simple to complex progression
   - Thematic grouping
   - Follow original sequence when appropriate

2. **Chapter Structure:**
   - Clear, descriptive headings (## Level 2)
   - Proper numbering for reference
   - Logical sub-sections (### and ####)

**Content Development by Relevance:**

**HIGH-RELEVANCE TOPICS** (800-1500 words)

Requirements:
- ✓ Comprehensive explanation (3-6 paragraphs minimum)
- ✓ Deep technical detail (HOW and WHY, not just WHAT)
- ✓ Multiple examples (2-3 practical use cases)
- ✓ Step-by-step procedures for complex processes
- ✓ Visual descriptions (diagrams, workflows mentioned)
- ✓ Best practices and common pitfalls
- ✓ Related concepts with explicit connections
- ✓ Troubleshooting guidance

**MEDIUM-RELEVANCE TOPICS** (400-800 words)

Requirements:
- ✓ Solid explanation (2-3 paragraphs)
- ✓ Key technical points
- ✓ At least one practical example
- ✓ Clear context and bigger picture
- ✓ Essential procedures without exhaustive detail
- ✓ Brief connections to other topics

**LOW-RELEVANCE TOPICS** (150-400 words)

Requirements:
- ✓ Concise but complete (1-2 paragraphs)
- ✓ Essential information only
- ✓ Basic context for inclusion
- ✓ Minimal examples (one if helpful)
- ✓ Summary of key points

**Formatting Standards:**

**Typography:**

Use **bold** for:
- **Key concepts** on first introduction
- **Important warnings** or cautionary information
- **Critical steps** in procedures
- **Essential takeaways**
- **Central technical terms**

Use *italic* (sparingly) for:
- Terms being defined
- Emphasis for contrast
- Citations or references

**Lists:**

Bullet points (•) for:
- Related items without sequence
- Features, characteristics, attributes
- Benefits or advantages
- Examples or use cases

Numbered lists (1, 2, 3) for:
- Step-by-step procedures
- Sequential processes
- Prioritized items
- Requirements in order
- Temporal sequences

**Hierarchy:**

```markdown
# Manual Title (Level 1 - Document Title)

## Introduction (Level 2 - Major Section)

## Topic Name (Level 2 - Main Topic)

### Key Concept (Level 3 - Sub-topic)

#### Detailed Aspect (Level 4 - Specific Detail)
```

**Content Quality Standards:**

1. **Clarity**: Technical but understandable
   - Define terms on first use
   - Use analogies when helpful
   - Break down complexity
   - Explain WHY, not just WHAT

2. **Accuracy**: Grounded in source
   - Every statement traceable to recording
   - No assumptions without basis
   - Verify technical details
   - Cite uncertainties explicitly

3. **Completeness**: Comprehensive coverage
   - All aspects of each topic
   - Include all examples mentioned
   - Sufficient background
   - Note prerequisites
   - Link related concepts

4. **Precision**: Unambiguous language
   - Clear, focused statements
   - One idea per sentence
   - Logical flow
   - Consistent terminology
   - Clear transitions

5. **Practical Focus**: User perspective
   - Actionable information
   - Real-world context
   - Concrete examples
   - Implementation guidance

**Critical Information Highlighting:**

Strategies:
- Explicit call-outs: **Critical Point:**, **Important:**, **Note:**, **Warning:**
- Visual separation: horizontal rules (---) between sections
- Repetition: Mention critical points in multiple contexts
- Strategic placement: Critical info at section start

---

#### Section 3: SUMMARY

**Required Components:**

1. **Key Concepts Recap** (bullet list)
   - 8-12 most important concepts
   - 1-2 sentence significance per concept
   - Organized by importance or theme

   Format:
   ```markdown
   - **Concept Name**: Brief explanation of what it is and why it matters
   - **Concept Name**: Brief explanation of what it is and why it matters
   ```

2. **Critical Takeaways** (bullet list or paragraphs)
   - 5-8 essential points to remember
   - Focus on practical application
   - Frequently used concepts
   - Crucial warnings or pitfalls

3. **Important Details Highlighted** (bullet list)
   - Specific technical details, parameters, specifications
   - Numbers, thresholds, requirements
   - Best practices
   - Tools, commands, resources

4. **Closing Perspective** (1-2 paragraphs)
   - Synthesis tying everything together
   - Connection to overall learning objective
   - Encourage practical application
   - Next steps or further learning
   - Positive, empowering note

**Quality Standards:**
- Comprehensive but concise
- Active, direct language
- Actionable information prioritized
- Consistent language with main content
- High quick-reference value

---

### PHASE 4: Quality Assurance (Automated)

**Internal Validation Checklist:**

Before delivery, verify:

Content:
- [ ] All major topics included
- [ ] Depth matches relevance levels
- [ ] Introduction provides clear context
- [ ] Each section is complete
- [ ] Summary synthesizes effectively
- [ ] All examples from source included
- [ ] Dependencies respected in order

Accuracy:
- [ ] Statements traceable to source
- [ ] No unsupported assumptions
- [ ] Technical terms used correctly
- [ ] Definitions provided
- [ ] User perspective maintained
- [ ] Clear, accessible language

Structure:
- [ ] Follows prescribed structure
- [ ] Logical heading hierarchy
- [ ] Appropriate topic ordering
- [ ] Smooth logical flow
- [ ] Easy navigation
- [ ] TOC accurate (if applicable)

Formatting:
- [ ] Consistent throughout
- [ ] Bold used appropriately
- [ ] Lists properly formatted
- [ ] Correct heading levels
- [ ] Good readability spacing
- [ ] Purposeful formatting

Format-Specific:
- [ ] Correctly implemented
- [ ] Best practices followed
- [ ] Renders correctly
- [ ] Saved to correct location
- [ ] Proper filename
- [ ] Complete and uncorrupted

Language:
- [ ] Entire document in selected language
- [ ] Natural, correct usage
- [ ] Technical terms appropriate
- [ ] Section labels correct
- [ ] Culturally appropriate

**Report Only Issues/Warnings:**

Display ONLY if problems detected:
```
⚠ QUALITY CHECKS

Issues found:
• [Specific issue description]
• [Specific issue description]

Recommendations:
• [Suggestion for resolution]

Proceed anyway? [Y/n]
```

If no issues: Silent validation, proceed to generation.

---

### PHASE 5: Generation and Delivery

#### Format-Specific Generation

**For Word Documents (.docx):**

CRITICAL: Read `/mnt/skills/public/docx/SKILL.md` BEFORE generation.

Implementation requirements:
```javascript
const { Document, Packer, Paragraph, TextRun, 
        HeadingLevel, AlignmentType, LevelFormat } = require('docx');

// Page setup: US Letter, 1" margins
sections: [{
  properties: {
    page: {
      size: { width: 12240, height: 15840 },
      margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
    }
  }
}]

// Typography: Arial, proper sizing
styles: {
  default: { 
    document: { 
      run: { font: "Arial", size: 24 } // 12pt
    } 
  },
  paragraphStyles: [
    { 
      id: "Heading1",
      run: { size: 32, bold: true, font: "Arial" }, // 16pt
      paragraph: { spacing: { before: 240, after: 240 }, outlineLevel: 0 }
    },
    { 
      id: "Heading2",
      run: { size: 28, bold: true, font: "Arial" }, // 14pt
      paragraph: { spacing: { before: 180, after: 180 }, outlineLevel: 1 }
    },
    { 
      id: "Heading3",
      run: { size: 26, bold: true, font: "Arial" }, // 13pt
      paragraph: { spacing: { before: 120, after: 120 }, outlineLevel: 2 }
    }
  ]
}

// Lists: NEVER use unicode bullets
numbering: {
  config: [
    { 
      reference: "bullets",
      levels: [{ 
        level: 0, 
        format: LevelFormat.BULLET,
        text: "•",
        style: { paragraph: { indent: { left: 720, hanging: 360 } } }
      }]
    },
    { 
      reference: "numbers",
      levels: [{ 
        level: 0,
        format: LevelFormat.DECIMAL,
        text: "%1.",
        style: { paragraph: { indent: { left: 720, hanging: 360 } } }
      }]
    }
  ]
}
```

Critical rules:
- ✗ NEVER use `\n` for line breaks → use separate Paragraph elements
- ✗ NEVER use unicode bullets → use LevelFormat.BULLET
- ✓ ALWAYS set page size explicitly
- ✓ ALWAYS use Arial font
- ✓ ALWAYS validate after creation

Optional: Table of contents for manuals >10 pages

---

**For PDF Documents (.pdf):**

CRITICAL: Read `/mnt/skills/public/pdf/SKILL.md` BEFORE generation.

Use `write_pdf` tool with markdown content:

```python
content = """
# Training User Manual: [Topic]

## Introduction
[Content with **bold** and *italic*]

## Topic Name

### Subtopic

Content with formatting:
- Bullet point
- Bullet point

**Key Concept**: Important info in bold.

### Another Subtopic

1. First step
2. Second step
3. Third step

## Summary
[Summary content]
"""

write_pdf(
    path="Training_Manual_[Topic].pdf",
    content=content,
    options={
        "margin": {
            "top": "1in",
            "right": "1in", 
            "bottom": "1in",
            "left": "1in"
        }
    }
)
```

Page breaks:
```html
<div style="page-break-before: always;"></div>
```

Advanced styling: HTML/CSS for colors, boxes, highlights

---

**For Markdown Files (.md):**

Structure:
```markdown
# Training User Manual: [Topic Name]

**Created**: [Date]  
**Language**: [Language]

---

## Introduction

[Content with **bold** for emphasis, *italic* for definitions]

Key objectives:
- First objective
- Second objective

---

## Topic 1: [Name]

### Key Concept A

Detailed explanation with **bold** and *italic*.

**Important**: Critical information.

#### Specific Detail

1. First step
2. Second step

---

## Summary

### Key Concepts Recap

- **Concept 1**: Explanation
- **Concept 2**: Explanation

### Critical Takeaways

1. First takeaway
2. Second takeaway

---

**End of Manual**
```

Best practices:
- One # for title (only one per document)
- ## for major sections
- ### for subsections
- #### for details
- Never skip levels
- Use --- for visual breaks
- Consistent list format (- or *)
- Blank lines before/after lists

---

#### File Saving

**Location:** `/mnt/user-data/outputs/`

**Filename Convention:**
```
Training_Manual_[Primary_Topic]_[YYYY-MM-DD].[ext]

Examples:
Training_Manual_REST_API_Integration_2024-02-12.docx
Training_Manual_Python_Basics_2024-02-12.pdf
Training_Manual_Project_Management_2024-02-12.md
```

Guidelines:
- Use underscores (not spaces)
- Include primary topic
- ISO date format (YYYY-MM-DD)
- Appropriate extension
- Under 100 characters
- Alphanumeric and underscores only

---

#### Delivery to User

Use `present_files` tool with confirmation:

```
✅ MANUAL READY

Format: [Word/PDF/Markdown]
Language: [Selected Language]
Length: ~[X] pages across [N] main sections

Content:
• Comprehensive introduction with learning objectives
• [N] topic chapters with adaptive detail levels
• Professional formatting with clear structure
• Detailed summary with key takeaways

[Download link via present_files]

Review and let me know if you'd like adjustments!
```

Offer revisions:
- "I can modify specific sections if needed"
- "Let me know if you'd like to expand particular topics"
- "Happy to adjust structure or formatting"

---

## Edge Cases and Troubleshooting

### Recording Trace Issues

**Incomplete/Unclear Content:**
1. Identify specific gaps
2. Notify user of limitations
3. Ask clarifying questions
4. Proceed with available information
5. Note limitations in manual
6. Offer to update when more info available

**Multiple Files:**
1. Read and analyze ALL files
2. Integrate from all sources
3. Resolve contradictions
4. Create unified manual
5. Note different aspects covered

**Very Short (<30 min) or Long (>3 hrs) Sessions:**
- Short: Concise manual with essentials
- Long: Consider multiple chapters or breaking into volumes
- Adjust target lengths proportionally

### Relevance Assessment Challenges

**No Clear Indicators:**
1. Apply inference systematically
2. Distribute fairly
3. Emphasize first or frequent topics
4. Explain approach to user
5. Offer to adjust based on feedback

**Conflicting Signals:**
1. Consider multiple factors
2. Make best judgment from overall pattern
3. Document reasoning if questioned
4. Be prepared to adjust

### Language and Translation

**Unfamiliar Language:**
1. Confirm ability to work in language
2. Ensure technical terminology appropriate
3. Consider cultural context
4. Verify terminology with user if uncertain

**Technical Terms:**
1. Use original with explanation if no translation
2. Provide both original and translated when helpful
3. Be consistent throughout

### Format Issues

**Word Validation Errors:**
1. Review validation output
2. Fix XML errors if needed
3. Ensure docx-js requirements met
4. Test opens in Microsoft Word

**PDF Rendering Problems:**
1. Check markdown syntax
2. Verify page breaks
3. Test searchability
4. Ensure formatting renders correctly

**Markdown Display Issues:**
1. Validate syntax
2. Test in multiple viewers
3. Check heading hierarchy
4. Verify list rendering

### Revision Requests

**Section Expansion:**
1. Confirm what needs expansion
2. Review source for additional info
3. Expand while maintaining consistency
4. Update summary if critical info added

**Different Organization:**
1. Understand preferred approach
2. Reorganize as requested
3. Ensure dependencies still make sense
4. Update cross-references

**Different Detail Level:**
1. Clarify which topics need adjustment
2. Adjust content depth
3. Maintain balance and coherence
4. Ensure minimum quality maintained

**Format Change:**
1. Convert to new format
2. Ensure content transfers correctly
3. Apply format-specific best practices
4. Deliver professionally

---

## Communication Guidelines

### Professional and Approachable

- Clear, friendly language
- Avoid overly formal phrasing
- Helpful and solution-oriented
- Show expertise without arrogance

### Concise and Clear

- Brief status updates
- Get to the point quickly
- Avoid unnecessary explanations
- Simple language for procedures

### Proactive and Anticipatory

- Ask clarifying questions when unclear
- Anticipate user needs
- Offer helpful suggestions
- Flag potential issues early

### User-Focused

- Frame in terms of user benefit
- Emphasize value and utility
- Show how manual serves needs
- Responsive to preferences and feedback

---

## Success Criteria

The manual is successful when:

1. **Content Quality:**
   - Complete, accurate manual delivered
   - All relevant topics appropriately covered
   - Technical information correct and accessible
   - Clear examples and explanations

2. **Structure and Organization:**
   - Well-structured, logical document
   - Sensible topic sequence
   - Intuitive navigation
   - Dependencies respected

3. **Professional Standards:**
   - Enterprise-grade quality
   - Consistent, appropriate formatting
   - Clear, professional, effective writing
   - Reflects well on organization

4. **User Satisfaction:**
   - Format and language match preferences
   - Effective reference material
   - Immediately usable
   - Valuable and helpful

5. **Practical Utility:**
   - Supports learning and retention
   - Accessible information
   - Easy to find critical details
   - Fulfills purpose as training reference

---

## Example Workflow

**Scenario:** 90-minute REST API Integration training for backend developers

**Step 1: Analysis**
- Topics: API fundamentals, authentication, endpoints, request/response, error handling, security, rate limiting, testing
- Relevance: HIGH (auth, endpoints, errors), MEDIUM (fundamentals, request/response, security), LOW (rate limiting, testing)
- Dependencies: Fundamentals → Endpoints → Request/Response

**Step 2: Configuration**
- Language: English
- Format: Word (.docx)

**Step 3: Generation**
- Introduction (1.5 pages)
- Ch 1: API Fundamentals (2 pages - MEDIUM)
- Ch 2: Authentication Methods (4 pages - HIGH)
- Ch 3: Endpoint Design (4 pages - HIGH)
- Ch 4: Request/Response Handling (2.5 pages - MEDIUM)
- Ch 5: Error Handling (3.5 pages - HIGH)
- Ch 6: Security Best Practices (2.5 pages - MEDIUM)
- Ch 7: Rate Limiting (1.5 pages - LOW)
- Ch 8: Testing Strategies (1.5 pages - LOW)
- Summary (2 pages)

**Step 4: Delivery**
- File: `Training_Manual_REST_API_Integration_2024-02-12.docx`
- 25-page professional manual
- Ready for developer reference

---

## Notes for Claude

**Goal:** Transform recording traces into organized, professional, highly useful reference documentation that:
- Enhances learning and retention
- Serves as go-to resource
- Meets professional standards
- Provides long-term value
- Makes complex content accessible

**Expertise should shine through:**
- Thoughtful content organization
- Clear, accessible technical explanations
- Appropriate emphasis on critical information
- Professional formatting and presentation
- Consistent user-focused approach

**Quality over speed:** Take time to produce excellent documentation. A well-crafted manual provides years of value.

---

## Version Information

**Version:** 1.0  
**Created:** 2024-02-12  
**Mode:** Semi-Automatic with Checkpoints  
**Quality:** Automated validation with minimal reporting  
**Trigger:** Intelligent with optional confirmation  
**Languages:** All supported, Italian default  
**Formats:** Word (.docx), PDF (.pdf), Markdown (.md)
