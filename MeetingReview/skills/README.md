# Meeting Review Generator Skill - Guida Completa

## Panoramica

Lo **Meeting Review Generator** è uno skill professionale per Claude che trasforma tracce di registrazioni di riunioni in verbali strutturati, actionable e pronti per la distribuzione esecutiva. Basato sulle logiche implementate nel progetto AI4Gamma, questo skill fornisce a Claude le capacità di un analista aziendale senior con 20+ anni di esperienza.

## Caratteristiche Principali

### 1. Analisi Completa delle Riunioni
- **Identificazione partecipanti**: Estrazione automatica di nomi, ruoli e contributi
- **Estrazione temi**: Identificazione di topic distinti con contesto tecnico
- **Inferenza rilevanza**: Valutazione automatica dell'importanza (Alta/Media/Bassa)
- **Tracciamento decisioni**: Cattura di tutte le conclusioni e scelte
- **Gestione action items**: Identificazione di task con assegnatari e deadline
- **Mapping dipendenze**: Relazioni logiche, temporali e organizzative

### 2. Struttura Report Professionale
Ogni report generato contiene esattamente **4 sezioni**:

#### Sezione 1: INTRODUZIONE
- Data della riunione e partecipanti
- Obiettivo principale
- Contesto e scope della discussione

#### Sezione 2: TEMI DISCUSSI
- Un sottosezione dedicata per ogni tema
- Dettaglio **proporzionale alla rilevanza**:
  - **Alta rilevanza**: 3-6+ paragrafi con contesto completo, specifiche tecniche, tutte le decisioni/azioni
  - **Media rilevanza**: 1-2 paragrafi con punti chiave
  - **Bassa rilevanza**: 1 paragrafo o meno con informazioni essenziali

#### Sezione 3: RIEPILOGO
- Recap di tutte le decisioni
- Lista dei punti aperti
- Overview delle azioni
- Aspetti critici (rischi, priorità, vincoli)
- Progresso complessivo (se report storici forniti)

#### Sezione 4: FOLLOW-UP
- Azioni specifiche e actionable
- Assegnatari con nomi in grassetto
- Deadline e dipendenze
- Priorità e criteri di successo

### 3. Formattazione Strategica
- **Testo in grassetto** per decisioni, punti aperti, azioni, aspetti critici
- **Bullet points** per liste di item correlati
- **Liste numerate** per step sequenziali o azioni prioritizzate
- **Cross-reference** tra temi correlati

### 4. Supporto Multilingue e Multi-formato
- **Lingue**: Italiano (default), Inglese, altre su richiesta
- **Formati**: DOCX (Word), PDF, MD (Markdown)
- Workflow interattivo che richiede preferenze utente prima della generazione

### 5. Integrazione Contesto Storico
- Analisi di report di riunioni precedenti
- Tracciamento evoluzione dei temi
- Monitoraggio progresso su azioni precedenti
- Mantenimento continuità narrativa

## Struttura dello Skill

```
meeting-review-generator/
├── SKILL.md (6.5KB)
│   └── Workflow principale con istruzioni concise
└── references/ (57KB totali)
    ├── output_structure.md (9.5KB)
    │   └── Specifiche dettagliate struttura 4 sezioni
    ├── writing_guidelines.md (11KB)
    │   └── Linee guida lingua, tono, chiarezza, formattazione
    ├── quality_standards.md (15KB)
    │   └── Criteri qualità per contenuto, struttura, formato
    └── examples.md (18KB)
        └── Esempi concreti di componenti report ben formattati
```

## Quando Claude Usa Questo Skill

Lo skill si attiva automaticamente quando l'utente:
- Carica tracce di riunioni, trascrizioni o note
- Richiede documentazione formale o verbali
- Menziona "SAL" (Stato Avanzamento Lavori)
- Chiede report o summary di meeting
- Vuole generare verbali di riunione professionali

## Workflow di Utilizzo

### Fase 1: Caricamento Documenti
L'utente carica:
- **Traccia riunione** (obbligatorio): Transcript, note, contenuto conversazionale
- **Report storici** (opzionale): Verbali di riunioni precedenti per contesto

### Fase 2: Analisi Automatica
Claude:
1. Legge tutti i documenti
2. Identifica partecipanti e ruoli
3. Estrae temi con livelli di rilevanza
4. Traccia decisioni, azioni, punti aperti
5. Mappa dipendenze tra temi

### Fase 3: Interazione Utente
Claude chiede:
1. **Lingua preferita**: Italiano (default), Inglese, altra
2. **Formato output**: DOCX, PDF, o MD

### Fase 4: Generazione Report
Claude:
1. Legge skill documentation appropriata (DOCX/PDF)
2. Legge tutti i file references/ per linee guida complete
3. Genera report seguendo tutte le specifiche
4. Crea file in `/mnt/user-data/outputs/`
5. Fornisce link di download

## Principi di Design

### Progressive Disclosure
Lo skill utilizza il pattern a tre livelli:
1. **Metadata** (name + description): Sempre nel contesto (~200 parole)
2. **SKILL.md body**: Caricato quando skill si attiva (~6.5KB)
3. **References files**: Caricati da Claude quando necessari (~57KB)

### Conciseness
- SKILL.md mantiene solo workflow essenziale
- Dettagli estesi spostati nei references/
- Riduce token usage ottimizzando contesto

### Appropriate Degrees of Freedom
- **Workflow strutturato** per garantire consistenza
- **Linee guida dettagliate** per qualità professionale
- **Esempi concreti** per chiarezza esecutiva

## Qualità del Report Generato

### Completezza
✓ Tutti i temi, decisioni, azioni, punti aperti catturati
✓ Tutti i partecipanti identificati
✓ Nessun gap nella copertura

### Accuratezza
✓ Fedele al contenuto della traccia riunione
✓ Dettagli tecnici verificati
✓ Nessun dettaglio fabbricato

### Professionalità
✓ Tono business appropriato
✓ Linguaggio tecnico ma accessibile
✓ Formattazione executive-ready

### Actionability
✓ Ogni azione specifica e chiara
✓ Tutti gli assegnatari identificati
✓ Dipendenze mappate
✓ Timeline awareness presente

## Casi d'Uso Tipici

### 1. Riunioni di Progetto (SAL)
- Tracciamento avanzamento lavori
- Documentazione decisioni tecniche
- Assegnazione task e responsabilità
- Monitoraggio blockers e rischi

### 2. Riunioni Esecutive
- Report per stakeholder
- Sintesi decisioni strategiche
- Tracking commitment e azioni
- Documentazione per audit

### 3. Riunioni Tecniche
- Specifiche architetturali
- Decisioni di design
- Review tecnici
- Planning implementazione

### 4. Riunioni Cross-Funzionali
- Coordinamento tra team
- Handoff e dipendenze
- Allineamento priorità
- Resource allocation

## Best Practices per l'Utente

### Per Input di Qualità
1. **Tracce complete**: Includere tutto il contenuto conversazionale
2. **Nomi chiari**: Specificare partecipanti e ruoli quando possibile
3. **Dettagli tecnici**: Catturare specifiche, versioni, configurazioni
4. **Decisioni esplicite**: Notare quando decisioni vengono prese
5. **Azioni assegnate**: Registrare chi fa cosa e quando

### Per Report Storici
1. **Report immediatamente precedente** per continuità
2. **Naming consistente** dei partecipanti
3. **Archiviazione sistematica** per riferimento futuro

### Per Risultati Ottimali
1. **Revisione post-generazione**: Verificare accuratezza
2. **Feedback**: Notare cosa funziona bene
3. **Iterazione**: Raffinare processo di cattura tracce
4. **Distribuzione tempestiva**: Condividere report prontamente

## Vantaggi dello Skill

### Per gli Utenti
- ⏱️ **Risparmio tempo**: Da ore a minuti per verbale completo
- 📊 **Qualità consistente**: Standard professionali garantiti
- 🎯 **Accountability chiara**: Assegnazioni esplicite
- 📈 **Tracciabilità**: Storico decisioni e progressi
- 🌍 **Multilingue**: Supporto internazionale

### Per le Organizzazioni
- 📋 **Documentazione permanente**: Record affidabili
- 🔄 **Continuità**: Tracking attraverso riunioni multiple
- ⚖️ **Compliance**: Audit trail completo
- 🤝 **Collaborazione**: Allineamento team
- 💼 **Professionalità**: Comunicazione executive-level

### Per Claude
- 🧠 **Expertise focalizzata**: Specializzazione analista senior
- 📚 **Knowledge procedural**: Workflow step-by-step
- ✅ **Quality assurance**: Standard integrati
- 🔧 **Tool integration**: Uso skills DOCX/PDF

## Installazione

1. **Scarica** il file `meeting-review-generator.skill`
2. **Importa in Claude.ai**:
   - Vai a Progetti
   - Crea nuovo progetto o apri esistente
   - Aggiungi lo skill dalla library
3. **Configura** (opzionale):
   - Aggiungi custom knowledge se necessario
   - Imposta preferenze di progetto

## Manutenzione e Aggiornamenti

### Quando Aggiornare
- Feedback utente indica gap o problemi
- Nuovi requisiti emergono (es. nuovo formato output)
- Best practices evolvono
- Necessità di supporto per nuovi scenari

### Come Aggiornare
1. Modifica `SKILL.md` o files in `references/`
2. Testa con casi reali
3. Ri-pacchettizza con `package_skill.py`
4. Ridistribuisci agli utenti

## Supporto e Feedback

Per miglioramenti continui:
- Raccogli feedback utente
- Analizza pattern di uso
- Identifica punti deboli
- Itera sulle linee guida
- Aggiorna examples con casi reali

## Conclusione

Il **Meeting Review Generator** skill trasforma Claude in un analista aziendale specializzato, capace di produrre verbali di riunione di qualità professionale in modo consistente, efficiente e scalabile. Basato su workflow comprovati e best practices consolidate, questo skill abilita organizzazioni a mantenere documentazione eccellente senza overhead manuale.

---

**Versione**: 1.0  
**Data Creazione**: Dicembre 2024  
**Basato su**: AI4Gamma Project - Gamma SPA  
**License**: Conforme ai termini del progetto originale
