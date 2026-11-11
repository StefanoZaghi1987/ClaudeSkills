# Report Output Structure

Complete specification for the four-section meeting review report structure.

Write the four section titles in the report's language — Italian: Introduzione, Temi trattati, Sintesi, Prossimi passi. The structure below uses the English titles for reference.

## Section 1: INTRODUCTION

### Purpose
Provide a concise overview of the meeting's primary focus and context.

### Required Content
- **Meeting date** (if available in transcript)
- **List of participants** with roles/affiliations when known
- **Main objective or purpose** of the meeting
- **High-level context** (why this meeting occurred)
- **Scope of discussion** covered

### Length
Concise - 1 to 3 paragraphs maximum

### Tone
Professional but accessible, setting the stage for detailed analysis

### Example Structure
```
On [date], [participants] met to discuss [main topic/purpose].
The meeting focused on [scope], addressing [high-level themes].
This report provides a detailed analysis of the discussions and outcomes.
```

---

## Section 2: DISCUSSED THEMES

### Purpose
Present detailed analysis of each theme discussed during the meeting.

### Structure
- **One dedicated subsection per theme**
- **Clear, descriptive subsection titles** (e.g., "Database Migration Strategy" not "Database Issues")
- **Proportional detail levels** based on theme relevance

### Detail Levels by Relevance

Relevance is assigned in SKILL.md STEP 2.2; this section sets the detail each level receives.

#### High Relevance Themes (Comprehensive Coverage)

**Content to include**:
- **Full technical context and specifications**: Complete background, requirements, constraints
- **All discussion points**: Key arguments, perspectives, considerations raised during discussion
- **Technical details**: Specific technologies, versions, configurations, requirements
- **Complete decision documentation**: All decisions with context and rationale
- **Detailed action items**: Specific tasks with assignees, deadlines, success criteria
- **Thorough dependency mapping**: All relationships to other themes
- **Risk and constraint analysis**: All identified risks, priorities, constraints
- **Multiple paragraphs** with rich, comprehensive detail

**Length**: 3-6 paragraphs or more

#### Medium Relevance Themes (Moderate Coverage)

**Content to include**:
- **Key technical points**: Essential technical information
- **Main discussion highlights**: Primary arguments and considerations
- **Important decisions and actions**: Significant outcomes only
- **Primary dependencies**: Most important relationships
- **Standard detail level**

**Length**: 1-2 paragraphs

#### Low Relevance Themes (Brief Coverage)

**Content to include**:
- **Essential information only**: Bare minimum needed for reference
- **Key takeaway or decision** if any
- **Minimal context**

**Length**: 1 paragraph or less

### Content Components for Each Theme

Include these elements when applicable (adjust detail based on relevance):

1. **Context and Background**
   - Why this theme was discussed
   - Historical context if relevant
   - Connection to organizational goals

2. **Technical Details**
   - Specifications, requirements, constraints
   - Technologies, tools, or methodologies involved
   - Technical architecture or design considerations

3. **Discussion Points**
   - Key arguments presented
   - Different perspectives or approaches considered
   - Stakeholder concerns raised
   - Questions explored

4. **Decisions** (**BOLD**)
   - All decisions made related to this theme
   - Decision rationale when provided
   - Who made the decision (if specified)
   - Impact on other themes or projects

5. **Open Points** (**BOLD**)
   - Items requiring further discussion
   - Questions needing answers
   - Topics awaiting information or resources
   - Unresolved issues

6. **Action Items** (**BOLD**)
   - Specific tasks assigned
   - Assignee names (when identified)
   - Deadlines or timeframes (when specified)
   - Success criteria (when defined)

7. **Dependencies**
   - **Logical dependencies**: One theme requires another
   - **Temporal dependencies**: Order of execution matters
   - **Organizational dependencies**: Different teams/departments involved
   - **Resource dependencies**: Shared budgets, tools, or personnel
   - Cross-reference related themes by name

8. **Critical Aspects** (**BOLD**)
   - Risks identified
   - Priorities established
   - Constraints acknowledged
   - Urgent items requiring immediate attention

---

## Section 3: SUMMARY

### Purpose
Consolidate all key outcomes across all themes for quick executive reference.

### Required Subsections

#### 3.1 Decisions Recap
- **List ALL decisions** made during the meeting
- Group by theme if many decisions exist
- Include brief context for each decision
- **Use bold text** for each decision statement
- Format: "**Decision**: [Statement]"

#### 3.2 Open Points List
- **Consolidate ALL items** requiring follow-up
- Group by theme or by type (technical, strategic, resource-related)
- Note which themes each relates to
- **Use bold text** for each open point
- Format: "**Open Point**: [Statement] (Related to: [Theme])"

#### 3.3 Actions Overview
- **List ALL action items** assigned during the meeting
- Include assignee for each action
- Note deadlines when specified
- Reference related themes
- **Use bold text** for each action and assignee
- Format: "**Action**: [Task] | **Assignee**: [Name] | Deadline: [Date] | Related to: [Theme]"

#### 3.4 Critical Aspects
- **Highlight ALL risks** identified
- **Note ALL priorities** established
- **List ALL constraints** acknowledged
- **Include ALL urgent items**
- **Use bold text** for emphasis
- Group by category (risks, priorities, constraints)

#### 3.5 Overall Progress (when historical context available)
- Assessment of advancement since previous meeting(s)
- Completion status of previous action items
- Theme evolution summary
- Long-term trend observations
- Changes in direction or priorities

### Formatting
- Use nested bullet points or numbered lists for clarity
- Organize logically by category
- Make it easy to scan and find specific information
- No new information here - only consolidation from previous sections

### Purpose Note
This section enables executives and stakeholders to quickly grasp all key outcomes without reading full theme details. It should serve as a standalone reference document.

---

## Section 4: FOLLOW-UP

### Purpose
Provide clear, actionable next steps with accountability mechanisms.

### Content Structure

List ALL action items in actionable, task-tracking format.

### For Each Action Item Include

1. **Task Description**
   - Clear, specific, actionable statement
   - Unambiguous about what needs to be done
   - Measurable when possible

2. **Assignee** (**BOLD**)
   - Person or team responsible
   - Contact information if available
   - Role/department if helpful

3. **Deadline**
   - Specific date when provided
   - Timeframe when date not specified (e.g., "within 2 weeks")
   - Relative timeframe if appropriate (e.g., "before next meeting")

4. **Related Theme**
   - Which theme this action supports
   - Context for why action is needed
   - Cross-reference to theme section

5. **Dependencies**
   - Prerequisites that must be completed first
   - Blocking items
   - Resources needed
   - Other team dependencies

6. **Priority** (when evident)
   - High: Urgent, critical path items
   - Medium: Important but not urgent
   - Low: Nice to have, can be deferred

7. **Success Criteria** (when specified)
   - How completion will be measured
   - Deliverables expected
   - Quality standards to meet

### Formatting Options

**Option 1: Numbered List with Sub-bullets**
```
1. **[Assignee Name]**: [Clear action description]
   - Deadline: [Date or timeframe]
   - Related to: [Theme name]
   - Dependencies: [Prerequisites if any]
   - Priority: [High/Medium/Low]
   - Success criteria: [How completion measured]
```

**Option 2: Table Format** (for many actions with consistent attributes)
| Action | Assignee | Deadline | Theme | Priority |
|--------|----------|----------|-------|----------|
| [Task] | **[Name]** | [Date] | [Theme] | [Level] |

**Option 3: Grouped by Priority**
```
### High Priority Actions
1. **[Assignee]**: [Action]...
2. **[Assignee]**: [Action]...

### Medium Priority Actions
1. **[Assignee]**: [Action]...
```

Choose the format that best fits the number of actions and their complexity.

### Emphasis
This section should enable immediate:
- Action tracking in project management tools
- Assignment to team members
- Progress monitoring
- Dependency management
- Risk mitigation through priority awareness

---

## Multi-Meeting Consolidated Report

When the user chooses one consolidated report for several meetings, keep the four-section structure and apply these rules:

- **Introduction**: one section covering all meetings — each date, and the union of the participants.
- **Discussed Themes**: a theme that recurs across meetings becomes ONE subsection telling its story in order (e.g., open on the first date, resolved on the second). Each theme carries its meeting date or dates. A theme discussed in one meeting only keeps its single date. The rule "keep each point in one theme only" still holds.
- **Summary**: every decision, action, open point, and critical aspect appears once, each tagged with its meeting date.
- **Follow-up**: one merged list. An action completed in a later meeting is reported as completed — never re-listed as open.
- **Overall Progress (3.5)**: required, not optional — comparing the meetings is the purpose of consolidation.
