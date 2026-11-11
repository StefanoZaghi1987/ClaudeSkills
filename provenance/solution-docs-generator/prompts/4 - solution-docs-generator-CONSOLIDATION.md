# solution-docs-generator – note di progetto del consolidamento

Sintesi dell'analisi del round di consolidamento. Come nella prima release, le convenzioni
dell'organizzazione di origine restano nel profilo documentale, fuori dal repository.

## Cosa è stato verificato

- La prima release era solida nell'impostazione: script per le parti meccaniche, agente per
  analisi e scrittura, profilo esterno, tracciabilità con ID di fonte, gate di consegna.
- Dodici lacune verificate (prove eseguite, non ipotesi), raggruppate qui per soluzione:

| Lacuna | Soluzione |
|---|---|
| Trascrizioni Whisper `.json`/`.tsv` non lette; un `.txt` senza speaker né tempi collassava in una riga | `transcript.py`: formato riconosciuto dal contenuto; lettori per sottotitoli (VTT, SRT, SBV), JSON dei motori (Whisper/WhisperX, OpenAI, AssemblyAI, Deepgram, Rev, Azure, AWS, Google, generico), TSV/CSV, layout testuali, prosa con ancore `[¶n]`; contenitori `.md`, `.docx`, `.pdf`, `.html`, `.rtf/.odt`; UTF-16; `--speakers`, `--format` |
| Parole fisse copiate in tre punti e già divergenti (lo spagnolo mancava nel gate) | Language pack `assets/i18n/<lang>.json` (it, en, de, fr, es) letti da script e agente: capitoli, etichette di copertina e scheda, didascalie, callout, marcatore "da confermare", formato data, nomi file; lingua senza pack con `--lang-pack` |
| Il "set di documenti" esisteva solo come frase | Un'analisi, un master per tipo, matrice di ripartizione al checkpoint, prefisso ID per documento, `check_doc.py --set` che verifica i rimandi tra documenti |
| Nessun flusso di revisione; consegna che poteva sovrascrivere | Revisione = stessa pipeline con il master precedente; ID stabili; `check_doc.py --previous`; mai sovrascrivere |
| Callout e stile dei manuali reali non riproducibili | Callout `verify` e `technical`; chiavi di stile nel profilo: logo, testi di intestazione e piè di pagina con segnaposto, "Pag. N di M", copertina a modulo, override delle etichette |
| Tipi di documento chiusi in un file monolitico | Registro `references/types/`: un file per tipo con capitoli in ordine (chiavi) e varianti; nuovi tipi procedura di manutenzione e scheda della soluzione; `check_doc.py` verifica ordine e nomi dei capitoli |
| Nessun uso del lavoro in parallelo | Regola fissa: worker solo se l'ambiente ha i subagenti e ci sono almeno due unità indipendenti (componenti, documenti, lingue, verifiche); passaggio di consegne su file; sequenziale altrimenti |
| Evals deboli (5 casi, nessun master di riferimento) | 17 casi, `eval_notes`, master di riferimento in `evals/samples/golden/` renderizzato e verificato dal self-test |

## Modello adottato

Sei assi indipendenti — soggetto, tipi, variante, profondità, lingue, formati — e una sola
pipeline: fonti → corpus → analisi (una volta) → un master per tipo → traduzioni → render →
controlli. Tre livelli separati: la skill (metodo), il profilo (organizzazione), la cartella di
lavoro (stato del soggetto).

## Scelte

- I nomi dei capitoli stanno nel language pack per chiave, la struttura nel file del tipo: una
  lingua nuova è un file, un tipo nuovo è un file più una riga per pack.
- Più lingue: il master si scrive e si chiude nella prima lingua, le altre sono sue traduzioni
  (stessi ID e numeri, verificati con `--parity`), mai scritture indipendenti.
- Parallelo solo dove le unità sono davvero indipendenti; mai un agente per capitolo.
- L'interazione resta quella delle skill sorelle: intake in un solo messaggio per ciò che manca,
  un checkpoint, modalità guidata, automatica, interattiva.
