# Quick Start Guide - Training Manual Generator

Get started with the training-manual-generator skill in 5 minutes.

## Installation

### Option 1: Download and Install (Recommended)

1. **Download the skill package**
   ```bash
   # Download as ZIP or clone the repository
   # Extract to your skills directory
   ```

2. **Copy to skills directory**
   ```bash
   # For user skills (personal)
   cp -r training-manual-generator /mnt/skills/user/
   
   # For example skills (shared)
   cp -r training-manual-generator /mnt/skills/examples/
   ```

3. **Verify installation**
   ```bash
   # Check skill is accessible
   ls /mnt/skills/user/training-manual-generator/SKILL.md
   ```

4. **Test the skill**
   - Open Claude
   - Upload a training transcript
   - Say: "Generate training manual"
   - Skill should activate automatically

### Option 2: Manual File Creation

If you prefer to create files manually:

1. Create directory structure:
   ```bash
   mkdir -p /mnt/skills/user/training-manual-generator/evals/files
   ```

2. Copy each file from the package to the appropriate location

3. Verify all required files are present:
   - `SKILL.md` (main skill file)
   - `README.md` (documentation)
   - `EXAMPLES.md` (usage examples)
   - `CHANGELOG.md` (version history)
   - `evals/evals.json` (test cases)
   - `evals/files/*.txt` (sample training files)

## First Use

### Test with Sample Data

The skill includes sample training files for testing:

```
User: I want to test the training manual generator

Claude: Great! Let me use one of the sample training files...

[Skill processes python_basics_training.txt]

📋 ANALYSIS COMPLETE

Main Focus: Python programming fundamentals
[... continues with normal workflow]
```

### Basic Usage Pattern

**Step 1: Upload Training Content**
```
Just drag and drop your training transcript file into Claude
```

**Step 2: Activate Skill**
```
You: "Generate a training manual from this"
```

**Step 3: Configure**
```
Claude: "In which language?" 
You: "English"

Claude: "Select output format..."
You: "Word"
```

**Step 4: Receive Manual**
```
Claude: "✅ MANUAL READY"
[Download link provided]
```

## Configuration

### Default Settings

The skill comes with sensible defaults:
- **Language**: Italian
- **Format**: Word (.docx)
- **Mode**: Semi-Automatic
- **Quality Reports**: Warnings only

### Customizing Defaults

You can request different defaults by saying:

**Change operating mode:**
```
"Use automatic mode by default"
"Always use interactive mode"
```

**Change format preference:**
```
"Always generate PDF"
"Prefer Markdown format"
```

**Change language:**
```
"Default to English instead of Italian"
```

Note: These customizations apply to the current session. For permanent changes, the skill maintains session preferences.

## Common Use Cases

### Quick Documentation (2 minutes)
```
1. Upload training_session.txt
2. Say: "automatic mode"
3. Receive: Training_Manual_[Topic]_[Date].docx
```

### Professional Manual (4 minutes)
```
1. Upload training_trace.txt
2. Review analysis summary
3. Select language: "English"
4. Select format: "PDF"
5. Receive: Professional PDF manual
```

### Multi-Session Course (6 minutes)
```
1. Upload: session1.txt, session2.txt, session3.txt
2. Say: "Create comprehensive manual from all sessions"
3. Review integrated analysis
4. Configure and generate
5. Receive: Complete course manual
```

## Troubleshooting

### Skill Doesn't Activate

**Problem**: Upload file but skill doesn't trigger

**Solutions**:
1. Explicitly request: "Generate training manual"
2. Check file format (should be text-based)
3. Verify skill is in correct directory
4. Restart Claude session if needed

### Wrong Language/Format

**Problem**: Manual generated in unexpected format

**Solution**:
```
"Regenerate in [desired language]"
"Change format to [PDF/Word/Markdown]"
```

### Content Issues

**Problem**: Topics missing or incorrectly identified

**Solution**:
```
Review analysis summary and request adjustments:
"Add section on [topic]"
"Increase detail for [topic]"
"Reorganize by [criteria]"
```

### Quality Warnings

**Problem**: Warnings shown about content

**Solution**:
1. Review the specific issues
2. Provide clarification if possible
3. Confirm proceeding if acceptable
4. Request regeneration after fixes

## Testing the Skill

### Run Sample Evaluations

The skill includes test cases:

```bash
# Basic test
Use eval file: evals/files/python_basics_training.txt

# Complex test  
Use eval file: evals/files/api_training_trace.txt

# Expected outcomes defined in: evals/evals.json
```

### Manual Testing Checklist

- [ ] Upload file activates skill intelligently
- [ ] Analysis correctly identifies topics
- [ ] Relevance levels seem appropriate
- [ ] Language selection works
- [ ] Format selection works
- [ ] Generated manual has correct structure
- [ ] Quality checks run automatically
- [ ] File saved with proper naming
- [ ] Manual meets quality standards

## Getting Help

### Built-in Examples

Review comprehensive examples:
```
Read: EXAMPLES.md for 7 detailed scenarios
```

### Documentation

Full documentation available:
```
SKILL.md - Complete skill specifications
README.md - User guide and features
CHANGELOG.md - Version history
```

### Interactive Mode

If unsure, use interactive mode:
```
"Generate manual in interactive mode"
```
This provides more guidance through the process.

## Next Steps

### Start Using

1. **Prepare Training Content**
   - Collect training transcripts
   - Ensure text format
   - Add timestamps/labels if available

2. **Generate First Manual**
   - Upload content
   - Follow skill prompts
   - Review generated manual

3. **Refine Process**
   - Experiment with modes
   - Try different formats
   - Adjust detail levels

### Advanced Usage

Once comfortable with basics:

- Process multiple session files
- Customize structure and organization
- Request specific formatting
- Generate in multiple languages
- Create course documentation

### Provide Feedback

Help improve the skill:
- Report issues encountered
- Suggest new features
- Share successful use cases
- Contribute test scenarios

## Quick Reference Card

```
┌─────────────────────────────────────────────┐
│   TRAINING MANUAL GENERATOR - QUICK REF     │
├─────────────────────────────────────────────┤
│                                             │
│  ACTIVATE                                   │
│  • Upload file + "generate manual"          │
│  • Or say: "automatic mode"                 │
│                                             │
│  MODES                                      │
│  • Semi-automatic (default)                 │
│  • Automatic (fast)                         │
│  • Interactive (control)                    │
│                                             │
│  FORMATS                                    │
│  • Word (.docx) - editable                  │
│  • PDF (.pdf) - fixed                       │
│  • Markdown (.md) - version control         │
│                                             │
│  LANGUAGES                                  │
│  • Italian (default)                        │
│  • English, Spanish, German, French...      │
│  • Any language Claude supports             │
│                                             │
│  STRUCTURE                                  │
│  1. Introduction                            │
│  2. Discussed Topics (adaptive depth)       │
│  3. Summary                                 │
│                                             │
│  QUALITY                                    │
│  • Automatic validation                     │
│  • Warnings only when issues found          │
│  • Professional standards                   │
│                                             │
│  COMMANDS                                   │
│  • "automatic" - fast generation            │
│  • "interactive" - step by step             │
│  • "expand [topic]" - more detail           │
│  • "regenerate in [language]" - convert     │
│                                             │
└─────────────────────────────────────────────┘
```

## Support

For issues or questions:
1. Check EXAMPLES.md for similar scenarios
2. Review README.md documentation
3. Try interactive mode for guidance
4. Consult CHANGELOG.md for known issues

---

**You're ready to start generating professional training manuals!**

Upload your first training transcript and say "generate training manual" to begin.
