# solution-docs-generator – note di progetto

Sintesi dell'analisi che ha portato alla prima release. I nomi di sistemi, server e persone
dell'organizzazione di origine sono omessi: le convenzioni specifiche vivono nel profilo
documentale, fuori dal repository.

## Materiale analizzato

- Otto manuali prodotti con il metodo descritto nel prompt iniziale: cinque manuali di
  troubleshooting (due applicazioni web di logistica integrate con un ERP, un'applicazione di
  pianificazione delle attività, tre processi schedulati dell'ERP raccolti in tre documenti
  collegati), un manuale utente, un manuale di configurazione e due note riservate sui rilievi di
  sicurezza emersi dall'analisi del codice.
- Due manuali utente scritti a mano negli anni precedenti, con il modello documentale aziendale
  (stato del documento, riservatezza, tabella delle revisioni).
- Il repository ClaudeSkills: convenzioni dei generatori, `local-python.md` condiviso, vincoli di
  `build_skills.py`, evals, provenance, CI.

## Cosa funzionava (e la skill fissa)

- Incrocio delle fonti: trascrizione per pratica e storia, codice per il comportamento reale,
  documenti e mail per date, ticket e decisioni.
- Correzione della trascrizione con i messaggi scritti in chat durante la sessione.
- Struttura costante per tipo di documento: intestazione completa; Sintesi con scheda della
  soluzione e indice rapido sintomo → scheda; Parte A per gli utenti e Parte B tecnica; metodo di
  diagnosi a livelli; schede con ID e campi fissi (Sintomo · Chi interviene · Cause · Verifica ·
  Soluzione); procedure di ripristino; anomalie note ricavate dal codice; casi storici; controlli
  periodici e dopo i cambiamenti; appendici (query di sola lettura, mappa delle chiamate,
  messaggi, glossario, riferimenti).
- Manuale utente orientato ai compiti, con badge per le funzioni presenti in un solo ambiente;
  manuale di configurazione con modello concettuale, aree di configurazione e procedure operative.
- Classificazione esplicita del livello di dettaglio (completo / essenziale).
- Nessuna credenziale nei documenti; rilievi di sicurezza tenuti fuori dal manuale.

## Punti deboli rilevati (e la soluzione adottata)

| Punto debole | Soluzione |
|---|---|
| Lo stile viveva nella memoria della sessione: prefissi delle schede, appendici e sommari variavano tra documenti | `references/document-types.md` fissa struttura e nomi; `render.py` applica un solo stile della casa su ogni piattaforma |
| Sommario con numeri di pagina scritti a mano, che si sfasano | Campo TOC reale; numeri misurati su una copia renderizzata con LibreOffice e aggiornamento del campo all'apertura in Word |
| Query in celle di tabella, non copiabili come codice | Blocchi di codice monospaziati |
| Nessuna traccia esplicita "affermazione → fonte" né registro dei conflitti | ID di fonte `SRC-nn`, registro delle affermazioni e dei conflitti in `analysis.md`, regole di prevalenza in `writing-standards.md` |
| Oscuramento delle credenziali e controllo dei rimandi fatti a mano | `extract_sources.py` oscura i segreti prima della lettura; `check_doc.py` verifica ID, rimandi a sezioni, numerazione, segreti, immagini |
| Correzione della trascrizione ricostruita ogni volta | `transcript.py`: termini canonici da chat e codice, suggerimenti per somiglianza ortografica e fonetica, glossario applicato in un solo passaggio |
| Convenzioni aziendali mescolate al metodo | Profilo documentale separato (`references/profile.md`, modello in `assets/`) |
| Schede mai raggiungibili dall'indice rapido né da altre schede (sei casi in un manuale esistente), rimandi a sezioni non verificati | Controllo automatico di ID e rimandi a sezioni, che distingue i rimandi ad altri documenti |
| Trasferimento lento di molti file tra macchina dell'utente e ambiente di analisi | Un'unica estrazione o un unico pacchetto dei sorgenti senza output di build |

## Scelte

- Una sola skill per tre tipi di documento, perché fonti, metodo e controlli sono gli stessi; la
  struttura cambia per tipo.
- Sorgente Markdown con poche estensioni come formato master: leggibile, versionabile, revisionabile
  in una sessione successiva; Word, PDF e Markdown generati dallo stesso sorgente.
- Un solo punto di confronto con l'utente dopo l'analisi (più l'intake, solo per ciò che manca),
  con al massimo 3–4 domande che cambiano il contenuto.
- La skill non sostituisce `training-manual-generator`: quella resta per i corsi la cui unica fonte
  è la lezione.
