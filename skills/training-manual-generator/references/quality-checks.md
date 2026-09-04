# Quality checks — training-manual-generator

Internal validation checklists (PHASE 4) plus edge cases and troubleshooting.

## Internal validation checklist

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

If no issues: Silent validation, proceed to file generation.

## Edge cases and troubleshooting

### Transcript issues

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
- Scale the word budgets in content-standards with source length: they assume a
  60–90 minute single session; use the bottom of each range for ~30 minutes,
  about half of that for shorter sessions, about double for a three-session
  course, and interpolate between the anchors

### Relevance assessment challenges

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

### Language and translation

**Unfamiliar Language:**
1. Confirm ability to work in language
2. Ensure technical terminology appropriate
3. Consider cultural context
4. Verify terminology with user if uncertain

**Technical Terms:**
1. Use original with explanation if no translation
2. Provide both original and translated when helpful
3. Be consistent throughout

### Format issues

**Word Validation Errors:**
1. Review validation output
2. Fix the reported errors
3. Ensure the branch you used (platform document skill, docx-js, or python-docx) met its requirements
4. On Claude Code, re-open the saved file with the library that built it (for example python-docx) to confirm it parses

**PDF Rendering Problems:**
1. Check markdown syntax
2. Verify page breaks
3. Confirm the PDF text is selectable (not rasterized)
4. Ensure formatting renders correctly

**Markdown Display Issues:**
1. Validate syntax
2. Re-read the saved file and confirm the heading hierarchy and lists match the generated structure

### Revision requests

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
