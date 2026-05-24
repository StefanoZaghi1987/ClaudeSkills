# Use Case Extractor - Quick Reference Card

## 🎯 What It Does
Transforms requirements documents into structured use cases organized by user role with professional formatting.

## 📋 Quick Start
1. Upload requirements document
2. Skill triggers automatically (or say "extract use cases")
3. Choose language (default: English)
4. Choose format (Word/Excel/Markdown)
5. Download your structured documentation

## 🔤 Role Prefixes
- **ADM** = Administrator
- **USR** = End User
- **DEV** = Developer
- **OPR** = Operator
- **MGR** = Manager
- **SYS** = System
- **API** = API Consumer
- **AUD** = Auditor
- **SUP** = Support Staff
- **CST** = Customer
- *Custom prefixes auto-generated as needed*

## 📊 Use Case Structure
Each use case includes:
- **Code**: Unique identifier (e.g., ADM-001)
- **Name**: Action-oriented (e.g., "Register New User")
- **Title**: Full formatted title
- **Target**: Goal and business value
- **Input Data**: Mandatory and optional inputs
- **Output Data**: Results, artifacts, notifications
- **Dependencies**: Related use cases with relationship types

## 📄 Output Formats

### Word (.docx)
✅ Professional formatting  
✅ Table of contents  
✅ Section headers  
✅ Print-ready  
**Best for**: Stakeholder presentations, formal documentation

### Excel (.xlsx)
✅ Filterable rows  
✅ Summary statistics  
✅ Dependencies matrix  
✅ Color-coded priorities  
**Best for**: Project tracking, team collaboration, analysis

### Markdown (.md)
✅ Version control friendly  
✅ Clean hierarchy  
✅ GitHub/GitLab compatible  
✅ Developer-friendly  
**Best for**: Technical teams, repository documentation

## 🎨 Priority Levels

| Priority | Description | Detail Level |
|----------|-------------|--------------|
| **High** | Core functionality, critical | 5-15 inputs/outputs |
| **Medium** | Supporting features | 3-8 inputs/outputs |
| **Low** | Edge cases, admin tasks | 2-5 inputs/outputs |

## 🔗 Dependency Types
- **Prerequisite**: Must complete first
- **Data Dependency**: Creates needed data
- **Workflow Sequence**: Typical execution order
- **Shared Resource**: Access same data/systems
- **Triggering**: Automatic initiation

## 💡 Tips for Best Results

### ✅ Do This
- Provide document context
- Define specialized terms
- Use clear action verbs
- Specify inputs and outputs
- Mention user roles explicitly
- Include examples in requirements

### ❌ Avoid This
- Extremely vague requirements
- Missing user context
- Contradictory statements (will be flagged)
- Technical code instead of requirements
- Diagrams without text descriptions

## 🔧 Common Commands

**Basic extraction**:
- "Extract use cases from this document"
- "Analyze requirements and create use cases"
- "Generate user stories from these specs"

**Format selection**:
- "Create a Word document"
- "Generate in Excel format"
- "I need both Word and Markdown"

**Language selection**:
- "Generate in Italian"
- "Create Spanish version"
- "Output in English" (default)

**Refinement**:
- "Add more detail to use case ADM-003"
- "Explain the dependencies better"
- "Flag ambiguous requirements"
- "Infer additional use cases"

## 📂 Supported Input Formats
PDF • DOCX • TXT • MD • RTF

## 🌍 Multi-Language Support
Any language supported by Claude - just specify your preference when prompted!

## ⚡ Processing Speed
- Small docs (1-20 pages): 1-2 minutes
- Medium docs (20-100 pages): 3-5 minutes
- Large docs (100+ pages): May suggest section-by-section processing

## 🎓 Use Cases
✅ Agile sprint planning  
✅ Stakeholder communication  
✅ QA test planning  
✅ Requirements traceability  
✅ Team onboarding  
✅ Multi-language projects  

## 🐛 Troubleshooting

**Skill didn't trigger?**  
→ Say "extract use cases" explicitly

**Missing use cases?**  
→ Ask "infer additional use cases from business processes"

**Wrong priorities?**  
→ Provide feedback: "ADM-005 should be high priority"

**Need different format?**  
→ Ask "also provide this in Excel format"

**Different language?**  
→ Ask "regenerate this in [language]"

## 📞 Getting Help

**Within conversation**:
- Ask Claude to explain any use case
- Request clarification on dependencies
- Ask for examples of similar use cases
- Request additional detail on any section

**Iteration**:
- The skill improves with feedback
- Refine output within same conversation
- Adjust priorities, add details, fix errors

---

## 🚀 Ready to Start?

1. Upload your requirements document
2. Let Claude analyze it
3. Choose your preferences
4. Get professional use case documentation!

**Pro Tip**: For large projects, start with a sample section to verify the output format meets your needs before processing the entire document.
