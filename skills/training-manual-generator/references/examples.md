# Training Manual Generator - Practical Examples

This document provides the interaction walkthroughs: the canonical
semi-automatic run (Example 1), fully automatic mode (Example 5), a
revision request (Example 6), and interactive mode (Example 7). Worked
examples for difficult sources — long or complex sessions, ambiguous
content, multiple input files — live in `source-examples.md`.

## Example 1: Basic Technical Training

### Input
**File:** `evals/python_basics_training.txt` (30-minute session)
**User Request:** "Generate a training manual from this Python session. Use Italian and Word format."

### Expected Behavior

**PHASE 1 — Analysis**
```
✓ Content received: python_basics_training.txt
⚙ Analyzing training content...

📋 ANALYSIS COMPLETE

Main Focus: Python programming fundamentals for junior developers

Primary Topics Identified:
1. Variables and Data Types - HIGH relevance
2. Indentation and Code Structure - HIGH relevance
3. Control Structures (if/else, loops) - HIGH relevance
4. Data Structures (lists, dictionaries) - MEDIUM relevance
5. Functions - MEDIUM relevance
6. Modules and Imports - LOW relevance
7. Error Handling - LOW relevance

Target Audience: Junior developers new to Python
Estimated Manual Length: ~12 pages

Ready to proceed with manual generation?
```

**PHASE 2 — Configuration (Step 2.1)** (already stated — acknowledged, not asked)
```
✓ Language: Italian (as requested)
✓ Format: Word Document (as requested)
```

**PHASE 3 — Structure preview (Step 3.0, final checkpoint)**
```
📋 STRUCTURE PREVIEW

- Introduzione (~1 page)
- Variabili e Tipi di Dati — HIGH (~2 pages)
- Indentazione e Struttura del Codice — HIGH (~2 pages)
- Strutture di Controllo — HIGH (~2 pages)
- Strutture Dati — MEDIUM (~1.5 pages)
- Funzioni — MEDIUM (~1 page)
- Moduli e Import — LOW (~0.5 pages)
- Gestione degli Errori — LOW (~0.5 pages)
- Riepilogo (~1 page)

Proceed with this structure?

[User responds: Yes]

⚙ Generating Word document...
```

**PHASE 5 — Delivery**
```
✅ MANUAL READY

Format: Word Document (.docx)
Language: Italian
Length: ~12 pages across 9 main sections

Content:
• Comprehensive introduction with learning objectives
• 7 chapters with adaptive detail levels
• Professional formatting with clear structure
• Detailed summary with key takeaways

📥 Training_Manual_Python_Fundamentals_IT_2026-08-27.docx

Review and let me know if you'd like adjustments!
```

### Generated Manual Structure

```markdown
# Manuale Utente: Fondamenti di Python

## Introduzione

### Panoramica del Corso
Questo manuale documenta la sessione formativa sui fondamenti di Python...
[2-3 paragraphs explaining the training focus]

### Contesto e Rilevanza  
Python è uno dei linguaggi di programmazione più richiesti...
[Explains why Python matters]

### Obiettivi di Apprendimento
Dopo aver studiato questo manuale, sarai in grado di:
- Comprendere e utilizzare variabili e tipi di dati in Python
- Applicare correttamente l'indentazione per strutturare il codice
- Implementare strutture di controllo (if/else, cicli for/while)
...

## Variabili e Tipi di Dati

**Le variabili in Python sono fondamentali** per memorizzare e manipolare dati...
[Comprehensive 2-page explanation with examples]

### Tipi di Dati Principali

**Stringhe (str)**: Sequenze di caratteri...
**Interi (int)**: Numeri senza decimali...
**Float**: Numeri con decimali...
**Boolean**: Valori True/False...

[Detailed examples and explanations]

## Indentazione e Struttura del Codice

**CRITICO**: L'indentazione in Python non è solo per la leggibilità...
[2-page comprehensive coverage]

## Riepilogo

### Concetti Chiave
- **Variabili e Tipi di Dati**: Python è dinamicamente tipizzato...
- **Indentazione**: Definisce i blocchi di codice, sempre 4 spazi...
[8-12 key concepts]

### Punti Critici da Ricordare
1. L'indentazione è OBBLIGATORIA e definisce la struttura
2. Le variabili non richiedono dichiarazione di tipo
...

**Fine del Manuale**
```

---

## Example 5: Fully Automatic Mode (also "quick mode")

### Input
**File:** `evals/standard_training.txt`
**User Request:** "Generate automatically, use defaults"

### Expected Behavior

**Automatic Processing:**
```
✓ Content received: standard_training.txt
⚙ Auto mode activated: using default settings
⚙ Analyzing training content...
⚙ Language: Italian (default)
⚙ Format: Word Document (default)
⚙ Generating manual...

✅ MANUAL READY

Format: Word Document (.docx)
Language: Italian  
Length: ~18 pages across 8 sections

📥 Training_Manual_Git_Fundamentals_IT_2026-08-27.docx

Manual generated automatically with default settings.
Review and request changes if needed!
```

**Key Differences:**
- No analysis summary shown (silent processing)
- No language confirmation prompt
- No format selection prompt
- Immediate generation with defaults
- Brief delivery message
- Quality checks run silently (only warn if issues)

---

## Example 6: Revision Request

### Scenario
User receives manual but wants changes.

**Initial Generation:**
```
✅ MANUAL READY
📥 Training_Manual_Docker_Basics_IT_2026-08-27.docx
```

**User Request:** "The networking section needs more detail, and I want it in PDF instead."

**Response:**
```
✓ Understood: 
  - Expand Docker networking section
  - Convert format to PDF

⚙ Reviewing source material for networking details...
⚙ Expanding section with:
  - Bridge network detailed explanation
  - Host network use cases
  - Overlay network for Swarm
  - Additional practical examples
  - Troubleshooting common issues

⚙ Converting to PDF format...

✅ UPDATED MANUAL READY

Changes applied:
• Docker Networking section expanded from 1.5 to 3.5 pages
• Added 4 practical examples
• Added troubleshooting subsection
• Converted to PDF format

Format: PDF Document (.pdf)
Language: Italian (unchanged)
Length: ~20 pages (was ~18 pages)

📥 Training_Manual_Docker_Basics_IT_2026-08-27_v2.pdf
```

---

## Example 7: Interactive Mode

### Input
**File:** `evals/javascript_advanced.txt`
**User Request:** "Generate manual in interactive mode"

### Expected Behavior

**Enhanced Interaction:**
```
✓ Content received: javascript_advanced.txt
⚙ Interactive mode activated
⚙ Analyzing training content...

📋 ANALYSIS COMPLETE

Main Focus: Advanced JavaScript patterns and techniques

Primary Topics Identified:
1. Closures and Scope - HIGH relevance
2. Async/Await Patterns - HIGH relevance
3. Prototype Chain - MEDIUM relevance
4. Memory Management - MEDIUM relevance
5. Design Patterns - LOW relevance

Would you like to:
1. Adjust topic relevance levels
2. Change topic organization  
3. Proceed as is

[User: "3 - proceed"]

⚙ Configuration
[Standard configuration prompt — Step 2.1]

[User: "English, Word"]

📋 STRUCTURE PREVIEW

- Introduction (~2 pages)
- Closures and Scope — HIGH (~3.5 pages)
- Async/Await Patterns — HIGH (~3.5 pages)
- Prototype Chain — MEDIUM (~2 pages)
- Memory Management — MEDIUM (~2 pages)
- Design Patterns — LOW (~1 page)
- Summary (~2 pages)

Approve this structure? [Y/n to adjust]

[User: "Y"]

⚙ Generating manual with approved structure...

✅ MANUAL READY
[Standard delivery]
```

**Key Features of Interactive Mode:**
- Option to adjust relevance levels
- Structure confirmation step
- More granular control
- Ability to reorganize before generation
- Suitable for users wanting customization
