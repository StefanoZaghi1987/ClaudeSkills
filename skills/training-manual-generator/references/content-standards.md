# Content standards — training-manual-generator

Structure, depth, formatting, and quality standards for the generated manual.
Applied during PHASE 3 (Content Generation).

## Structure overview

Generate the manual with three main sections:

```
MANUAL STRUCTURE
├── 1. Introduction
│   ├── Training Overview
│   ├── Context and Relevance
│   └── Learning Objectives
│
├── 2. Discussed Topics (Core)
│   ├── Topic 1 (HIGH) - Comprehensive
│   ├── Topic 2 (HIGH) - Comprehensive
│   ├── Topic 3 (MEDIUM) - Solid
│   ├── Topic 4 (MEDIUM) - Solid
│   └── Topic 5 (LOW) - Concise
│
└── 3. Summary
    ├── Key Concepts Recap
    ├── Critical Takeaways
    ├── Important Details
    └── Closing Perspective
```

Render only *Introduction* and *Summary* as major section headings, each topic as
its own chapter heading between them — the *Discussed Topics* grouping above
is structural, never printed. All headings plain and unnumbered: no all-caps,
no brackets, no outline numbers. Write them in the manual's language —
*Introduction / Summary* in English, *Introduzione / Riepilogo* in Italian;
other languages follow the same pattern.

## Section 1: Introduction

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

## Section 2: Discussed Topics

**Organization Principles:**

1. **Topic Sequencing:**
   - Logical prerequisites first
   - Simple to complex progression
   - Thematic grouping
   - Follow original sequence when appropriate

2. **Chapter Structure:**
   - Clear, descriptive headings (## Level 2)
   - Logical sub-sections (### and ####)

**Content Development by Relevance:**

For multi-session or very long sources, scale these budgets proportionally
(see quality-checks.md: Very Short or Long Sessions).

**HIGH-RELEVANCE TOPICS** (800-1500 words)

Requirements:
- ✓ Comprehensive explanation (3-6 paragraphs minimum)
- ✓ Deep technical detail (HOW and WHY, not just WHAT)
- ✓ Multiple examples (2-3 practical use cases)
- ✓ Step-by-step procedures for complex processes
- ✓ Diagrams and workflows the instructor showed, explained in words
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

## Formatting standards

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

Bulleted lists for:
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

## Content quality standards

1. **Clarity**: Technical but understandable
   - Define terms on first use
   - Use analogies when helpful
   - Break down complexity
   - Explain WHY, not just WHAT

2. **Accuracy**: Grounded in source
   - Every statement traceable to the source
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

6. **Numbers inside right-to-left text**: in a right-to-left manual language, keep numeric
   runs reading left-to-right with direction marks, so a sign or a unit never detaches
   from its value
   - Step numbers, versions, and dates
   - Signed or unit-bearing values
   - Page estimates in previews and in the delivery message

**Critical Information Highlighting:**

Strategies:
- Explicit call-outs: **Critical Point:**, **Important:**, **Note:**, **Warning:**
- Visual separation: horizontal rules (---) between sections
- Repetition: Mention critical points in multiple contexts
- Strategic placement: Critical info at section start

## Section 3: Summary

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

3. **Important Details** (bullet list)
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
