# Training Manual Generator - Source Examples

Worked examples for difficult sources: a long, complex single session
(Example 2), ambiguous content (Example 3), and training split across
multiple files (Example 4). The interaction walkthroughs — the canonical
run, automatic mode, revisions, interactive mode — live in `examples.md`.

---

## Example 2: Complex API Training

### Input
**File:** `evals/api_training_trace.txt` (90-minute session)
**User Request:** "Create a professional manual from our API training. English, PDF format."

### Expected Behavior

**PHASE 1 — Analysis**
```
✓ Content received: api_training_trace.txt
⚙ Analyzing training content...

📋 ANALYSIS COMPLETE

Main Focus: REST API Integration for microservices architecture

Primary Topics Identified:
1. Authentication Methods - HIGH relevance
2. Endpoint Design Best Practices - HIGH relevance
3. Error Handling Strategies - HIGH relevance
4. API Fundamentals - MEDIUM relevance
5. Request and Response Handling - MEDIUM relevance
6. Security Best Practices - MEDIUM relevance
7. Rate Limiting Implementation - LOW relevance
8. Testing Strategies - LOW relevance

Target Audience: Backend developers with basic API knowledge
Estimated Manual Length: ~23 pages

⚠ Note: Instructor emphasized authentication and error handling as critical topics

Ready to proceed with manual generation?
```

**PHASE 2 — Configuration (Step 2.1)** (already stated — acknowledged, not asked)
```
✓ Language: English (as requested)
✓ Format: PDF Document (as requested)
```

**PHASE 3 — Structure preview (Step 3.0, final checkpoint)**
```
📋 STRUCTURE PREVIEW

- Introduction (~2 pages)
- Authentication Methods — HIGH (~3.5 pages)
- Endpoint Design Best Practices — HIGH (~3.5 pages)
- Error Handling Strategies — HIGH (~3.5 pages)
- API Fundamentals — MEDIUM (~2 pages)
- Request and Response Handling — MEDIUM (~2 pages)
- Security Best Practices — MEDIUM (~2 pages)
- Rate Limiting Implementation — LOW (~1 page)
- Testing Strategies — LOW (~1 page)
- Summary (~2 pages)

Proceed with this structure?

[User responds: Yes]

⚙ Generating comprehensive PDF manual...
```

**PHASE 5 — Delivery**
```
✅ MANUAL READY

Format: PDF Document (.pdf)
Language: English
Length: ~23 pages across 10 sections

📥 Training_Manual_REST_API_Integration_EN_2026-08-27.pdf
```

### Key Differences from the Basic Session (Example 1)

**Higher Complexity:**
- More topics (8 vs 7)
- Longer content (23 vs 12 pages)
- Greater technical depth required

**Manual Contains:**
1. **Authentication Methods** (3.5 pages)
   - OAuth 2.0 detailed flow
   - JWT implementation details
   - API key management
   - Multiple code examples
   - Security considerations

2. **Endpoint Design** (3.5 pages)
   - RESTful conventions
   - Versioning strategies  
   - Nested resources
   - Filtering and pagination
   - BAD vs GOOD examples

3. **Error Handling** (3.5 pages)
   - Structured error responses
   - Status code usage
   - Common scenarios
   - Partial failure handling

[Medium and Low relevance topics with appropriate coverage]

---

## Example 3: Ambiguous Content

### Input
**File:** `evals/mixed_training_notes.txt` (unclear structure)
**User Request:** "Turn this into a manual. Markdown format."

### Expected Behavior

**PHASE 1 — Analysis**
```
✓ Content received: mixed_training_notes.txt
⚙ Analyzing training content...

📋 ANALYSIS COMPLETE

Main Focus: Database optimization techniques (inferred from content)

Primary Topics Identified:
1. Query Optimization - HIGH relevance (inferred from duration)
2. Indexing Strategies - HIGH relevance (multiple examples)
3. Connection Pooling - MEDIUM relevance
4. Caching Mechanisms - MEDIUM relevance
5. Performance Monitoring - LOW relevance

Target Audience: Database administrators (inferred)
Estimated Manual Length: ~14 pages

⚠ Issues Detected:
• Some technical terms used without definition (e.g., "B-tree index")
• Section transitions unclear in source material
• Topic sequence reorganized for logical flow

Ready to proceed with manual generation?
```

**PHASE 2 — Configuration (Step 2.1)** (format already stated — only the missing preference is asked)
```
⚙ Configuration

1. Language
   Italian (default — confirm or specify another)

[User responds: "English"]
```

**PHASE 3 — Structure preview (Step 3.0, final checkpoint)**
```
📋 STRUCTURE PREVIEW

- Introduction (~1 page)
- Query Optimization — HIGH (~3.5 pages)
- Indexing Strategies — HIGH (~3.5 pages)
- Connection Pooling — MEDIUM (~2 pages)
- Caching Mechanisms — MEDIUM (~2 pages)
- Performance Monitoring — LOW (~1 page)
- Summary (~1 page)

Proceed with this structure?

[User responds: Yes]
```

**PHASE 4 — Quality warning**
```
⚠ QUALITY CHECKS

Issues found:
• Technical term "B-tree index" not defined in source material
• Connection pooling section has limited detail

Recommendations:
• Manual includes inferred definition for B-tree based on context
• Connection pooling section marked as "brief overview"
• Suggest user review technical accuracy

Proceed anyway? [Y/n]

[User responds: Y]
```

**PHASE 5 — Delivery**
```
✅ MANUAL READY

Format: Markdown (.md)
Language: English
Length: ~14 pages across 7 sections

Note: Some content inferred due to source limitations. 
Technical definitions added based on standard usage.

📥 Training_Manual_Database_Optimization_EN_2026-08-27.md
```

---

## Example 4: Multi-File Training

### Input
**Files:** `evals/session1_intro.txt`, `evals/session2_advanced.txt`, `evals/session3_practice.txt`
**User Request:** "Create comprehensive manual from all three sessions. Italian, Word."

### Expected Behavior

**PHASE 1 — Analysis**
```
✓ Content received:
  - session1_intro.txt
  - session2_advanced.txt
  - session3_practice.txt
⚙ Analyzing training content from 3 files...

📋 ANALYSIS COMPLETE

Main Focus: Complete React.js development course (3 sessions)

Content Integration:
Session 1: React Basics (Components, Props, State)
Session 2: Advanced Patterns (Hooks, Context, Performance)
Session 3: Practical Project (Building complete application)

Primary Topics Identified (integrated):
1. Component Architecture - HIGH relevance (sessions 1, 2)
2. React Hooks - HIGH relevance (sessions 2, 3)
3. State Management - HIGH relevance (sessions 1, 2, 3)
4. Performance Optimization - MEDIUM relevance (sessions 2, 3)
5. Props and Data Flow - MEDIUM relevance (sessions 1, 2)
6. Project Structure - MEDIUM relevance (session 3)
7. Routing - LOW relevance (session 3)
8. Testing - LOW relevance (session 3)

Target Audience: Frontend developers learning React
Estimated Manual Length: ~35 pages

✓ All sessions successfully integrated
✓ No contradictions found between sessions
✓ Logical progression maintained

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

- Introduzione (~2 pages)
- Architettura dei Componenti — HIGH (~5 pages) [sessioni 1, 2]
- React Hooks — HIGH (~5 pages) [sessioni 2, 3]
- Gestione dello Stato — HIGH (~5 pages) [sessioni 1, 2, 3]
- Ottimizzazione delle Prestazioni — MEDIUM (~4 pages) [sessioni 2, 3]
- Props e Flusso dei Dati — MEDIUM (~4 pages) [sessioni 1, 2]
- Struttura del Progetto — MEDIUM (~3 pages) [sessione 3]
- Routing — LOW (~2 pages) [sessione 3]
- Testing — LOW (~2 pages) [sessione 3]
- Riepilogo (~3 pages)

Proceed with this structure?

[User responds: Yes]

⚙ Integrating content from 3 training sessions...
```

### Multi-File Integration Features

**Content Synthesis:**
- Topics from different sessions merged logically
- Progressive complexity maintained
- No duplicate explanations
- Cross-session examples integrated

**Session References:**
```markdown
## React Hooks

**I React Hooks** sono stati introdotti nella sessione 2 e applicati 
praticamente nella sessione 3...

### useState Hook
[Combines theory from Session 2 with practical examples from Session 3]

### useEffect Hook  
**Esempio Pratico** (dalla sessione 3): Nel progetto completo, 
abbiamo utilizzato useEffect per...
```
