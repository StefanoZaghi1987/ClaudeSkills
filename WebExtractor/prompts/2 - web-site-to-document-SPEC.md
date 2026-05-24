# SKILL SPECIFICATION — `web-site-to-document`

**Versione:** 1.0-draft  
**Data:** 2026-04-09  
**Autore:** Stefano Zaghi (gamma-spa.com)  
**Stato:** In revisione — Non avviare lo sviluppo prima della conferma esplicita

---

## 1. Panoramica

La skill `web-site-to-document` consente di estrarre il contenuto informativo completo di qualsiasi sito web pubblico e di convertirlo in un documento strutturato (Word, PDF o Markdown). La skill effettua una traversata ricorsiva dell'albero di navigazione del sito, estrae il contenuto semantico di ogni pagina, e aggrega il risultato in un singolo documento organizzato, con indice automatico.

**Obiettivo principale:** "Trasformare un sito web in un documento leggibile, ricercabile e autocontenuto."

---

## 2. Lingua e Interfaccia

- La skill rileva la lingua preferita dell'utente in base alla lingua del messaggio che l'ha attivata
- Se il messaggio è in italiano → la skill comunica in italiano
- Se il messaggio è in inglese → la skill comunica in inglese
- In assenza di indicazione chiara → default: italiano
- I messaggi di log, avanzamento, avvisi ed errori rispettano la stessa lingua dell'interfaccia
- Il contenuto estratto dal sito viene sempre riprodotto nella **lingua originale del sito**, indipendentemente dalla lingua dell'interfaccia

---

## 3. Workflow della Skill

La skill si articola in cinque fasi sequenziali. L'utente può intervenire nelle fasi 1 e 2.

### Fase 1 — Raccolta Input (interattiva)

La skill raccoglie i parametri necessari. Se già presenti nella richiesta dell'utente, non li chiede nuovamente.

| Parametro | Modalità | Default |
|---|---|---|
| URL di partenza | Estrapolato dalla richiesta o chiesto interattivamente | — (obbligatorio) |
| Formato output | Chiesto interattivamente con opzioni | `.docx` |
| Profondità di scraping | Chiesto interattivamente | Intero albero di navigazione |
| Scope dei domini | Chiesto interattivamente | Solo dominio di partenza (configurabile) |
| Limite massimo pagine | Chiesto solo se la stima lo suggerisce (v. Fase 2) | Nessun limite |

**Opzioni formato output:**
- Microsoft Word (`.docx`) — default raccomandato
- PDF (`.pdf`)
- Markdown (`.md`)

**Opzioni profondità:**
- Intero albero di navigazione (default)
- Numero di livelli specificato dall'utente (es. 2 livelli)

**Opzioni scope domini:**
- Solo il dominio esatto di partenza (es. `help.sap.com`)
- Dominio + sottodomini (es. `*.sap.com`)
- Lista personalizzata di domini da includere/escludere specificata dall'utente

### Fase 2 — Analisi Preventiva del Sito

Prima di avviare lo scraping completo, la skill effettua un'analisi rapida del sito.

**Operazioni:**
1. Verifica la raggiungibilità dell'URL di partenza
2. Identifica il tipo di sito (statico HTML vs JavaScript-rendered)
3. Stima il numero totale di pagine raggiungibili alla profondità configurata
4. Stima la dimensione approssimativa del documento finale
5. Verifica la raggiungibilità dei domini nello scope

**Comportamento in base alla stima:**
- Se le pagine stimate sono ≤ 50 → procede senza chiedere conferma
- Se le pagine stimate sono tra 51 e 200 → informa l'utente e chiede conferma prima di procedere
- Se le pagine stimate sono > 200 → informa l'utente, comunica la stima della dimensione del documento, e chiede se impostare un limite massimo di pagine

### Fase 3 — Scraping e Estrazione Contenuto

La skill seleziona automaticamente la strategia tecnica più adatta in base al tipo di sito rilevato in Fase 2.

**Strategie disponibili:**

| Strategia | Quando si usa | Caratteristiche |
|---|---|---|
| Python statico (requests + BeautifulSoup) | Siti HTML statici con rendering server-side | Veloce, efficiente, scalabile |
| Playwright headless browser | Siti JS-heavy (SPA, React, Angular, Vue) | Più lento, gestisce JavaScript completo |
| Claude in Chrome MCP | Fallback se Playwright non disponibile o fallisce | Browser reale, massima compatibilità |

**Algoritmo di traversata:**
- Breadth-First Search (BFS) per rispettare i livelli di profondità
- Set delle URL visitate per evitare cicli e duplicati
- Normalizzazione degli URL (rimozione di ancore `#`, parametri di sessione, URL canonicalizzazione)
- Rate limiting: pausa di 1 secondo tra le richieste per evitare blocchi anti-scraping

**Per ogni pagina estratta la skill raccoglie:**
- Titolo della pagina (tag `<title>` o primo `<h1>`)
- Struttura gerarchica dei titoli (H1–H6)
- Testo dei paragrafi
- Tabelle (struttura completa)
- Elenchi puntati e numerati
- Blocchi di codice (con indicazione del linguaggio se presente)
- Immagini (scaricate e incorporate, v. §4)
- Note, avvisi, callout (formattati in modo distinto)
- Link interni (per la traversata) e link esterni (preservati come hyperlink)
- Percorso di navigazione (breadcrumb) come contesto gerarchico

**Gestione contenuto non-HTML:**
- File PDF, ZIP, video, audio, Office trovati come link durante la traversata: vengono elencati in una sezione "Riferimenti e Allegati" del documento, con nome file, tipo e URL originale, ma non vengono scaricati né incorporati
- Eccezione: le immagini (PNG, JPG, SVG, WebP, GIF) vengono sempre scaricate e incorporate

**Log di avanzamento (mostrato in tempo reale):**
```
[1/47] Scraping: https://help.example.com/intro ...  ✓
[2/47] Scraping: https://help.example.com/guide/step1 ...  ✓
[3/47] Scraping: https://help.example.com/guide/step2 ...  ⚠ Timeout (skipped)
...
```

### Fase 4 — Assemblaggio del Documento

Una volta completato lo scraping, la skill assembla il documento finale.

**Struttura del documento generato:**

1. **Copertina** — URL sorgente, data di estrazione, profondità, numero di pagine estratte, formato e versione della skill
2. **Indice / Sommario** — generato automaticamente, collegato alle sezioni (per formati che lo supportano)
3. **Sezioni di contenuto** — una per ogni pagina estratta, organizzate secondo la gerarchia di navigazione del sito
4. **Sezione Riferimenti e Allegati** — lista dei file non-HTML incontrati durante la traversata

**Denominazione automatica del file:**
```
{nome_dominio}_{data}_{profondità}.{estensione}
```
Esempi:
- `help_sap_com_20260409_full.docx`
- `help_boyum-it_com_20260409_3livelli.pdf`
- `learn_microsoft_com_20260409_full.md`

**Deduplicazione contenuto:**
- Le pagine con contenuto identico o quasi identico vengono consolidate (una sola occorrenza nel documento con nota "contenuto anche raggiungibile da: [lista URL]")

### Fase 5 — Generazione del File

**Selezione del motore di generazione:**

1. La skill verifica se le skill esistenti `docx` e/o `pdf` sono disponibili e integrabili
2. Se disponibili e applicabili → le usa, presentando all'utente l'opzione di integrazione
3. Se non disponibili o non applicabili → usa direttamente librerie Python:
   - `.docx`: `python-docx`
   - `.pdf`: `weasyprint` (con HTML intermedio) o `reportlab`
   - `.md`: generazione diretta come testo strutturato

Il file finale viene salvato nella cartella workspace dell'utente e viene fornito un link diretto per aprirlo.

---

## 4. Gestione delle Immagini

- Le immagini trovate nelle pagine HTML vengono scaricate durante lo scraping
- Vengono incorporate (embedded) nel documento finale
- Formato supportati: PNG, JPG, JPEG, WebP, GIF, SVG
- Dimensione massima per immagine incorporata: 5 MB (oltre vengono elencate come riferimento URL)
- Le immagini SVG vengono convertite in PNG prima dell'incorporamento se il formato target non supporta SVG nativo
- In caso di errore nel download di una singola immagine: la skill registra un avviso e continua (inserendo nel documento un segnaposto con l'URL originale)

---

## 5. Gestione della Rete e dei Domini

**Verifica preventiva:**
Prima di avviare lo scraping, la skill verifica la raggiungibilità di tutti i domini nello scope usando WebFetch. Un dominio è considerato "bloccato" se WebFetch restituisce un errore di rete (non un errore HTTP come 404).

**Comportamento in caso di dominio bloccato:**
- Registra un avviso nel log di avanzamento: `⛔ Dominio bloccato: {dominio} — escluso dallo scope`
- Esclude automaticamente il dominio dalla traversata
- Continua lo scraping sui domini raggiungibili
- Include nella sezione iniziale del documento una nota sui domini esclusi

**Rate limiting e comportamento cortese:**
- Pausa di 1 secondo tra richieste successive allo stesso dominio
- Rispetto dell'header `Retry-After` se restituito dal server
- Aggiunta dell'header `User-Agent` identificativo della skill

---

## 6. Gestione degli Errori

**Classificazione errori:**

| Tipo | Comportamento |
|---|---|
| Timeout di rete | Avviso nel log, pagina saltata, contatore errori +1 |
| HTTP 4xx (client error) | Avviso nel log, pagina saltata, contatore errori +1 |
| HTTP 5xx (server error) | Avviso nel log, pagina saltata, contatore errori +1 |
| Errore di parsing HTML | Avviso nel log, estrazione parziale se possibile, contatore +1 |
| Errore download immagine | Avviso nel log, segnaposto nel documento, contatore NON incrementato |
| Dominio bloccato | Registrato separatamente, NON incrementa contatore errori pagina |

**Soglia di stop:**
- Dopo **10 errori consecutivi** (senza nessuna pagina estratta con successo nel mezzo), la skill si ferma
- Comunica all'utente le pagine estratte fino a quel momento
- Chiede se procedere con il documento parziale o interrompere

**Errori non consecutivi:**
- Il contatore si azzera ogni volta che una pagina viene estratta con successo
- Non esiste un limite assoluto sul numero totale di errori (solo sul numero consecutivo)

---

## 7. Fedeltà del Contenuto

La skill adotta un approccio **strutturato semantico**: l'obiettivo non è riprodurre il layout visivo pixel-perfect del sito (colori, font, sfondi), ma preservare fedelmente il **contenuto informativo** e la **struttura gerarchica**.

**Elementi preservati:**
- ✅ Gerarchia dei titoli (H1–H6 → stili heading del documento)
- ✅ Testo dei paragrafi (formattazione grassetto, corsivo, sottolineato)
- ✅ Tabelle (struttura completa con intestazioni)
- ✅ Elenchi puntati e numerati (inclusi annidati)
- ✅ Blocchi di codice (font monospace, con indicazione del linguaggio)
- ✅ Immagini (incorporate)
- ✅ Link (preservati come hyperlink cliccabili)
- ✅ Note, avvisi, callout (formattati in riquadri distinti)
- ✅ Lingua originale del sito (non tradotta)
- ✅ Contenuto ricercabile e selezionabile

**Elementi NON replicati:**
- ❌ Colori del tema (sfondo, testo colorato)
- ❌ Font personalizzati del sito
- ❌ Animazioni e transizioni
- ❌ Menu di navigazione laterale (la navigazione diventa struttura del documento)
- ❌ Widget interattivi (form, slider, tab) — il contenuto visibile viene estratto, l'interattività no

---

## 8. Struttura dei File della Skill

```
skills/web-site-to-document/
├── SKILL.md                    # Istruzioni principali della skill (prompt)
├── README.md                   # Documentazione per sviluppatori
└── src/
    ├── scraper.py              # Engine di scraping (statico + Playwright)
    ├── content_extractor.py    # Estrazione semantica da HTML (BeautifulSoup)
    ├── link_traverser.py       # Gestione BFS, deduplicazione URL, scope domini
    ├── image_handler.py        # Download e preprocessing immagini
    ├── document_builder.py     # Assemblaggio struttura documento (intermediario)
    ├── output_docx.py          # Generazione .docx (python-docx)
    ├── output_pdf.py           # Generazione .pdf (weasyprint/reportlab)
    ├── output_md.py            # Generazione .md
    └── utils.py                # Network check, URL normalization, logging
```

---

## 9. Casi d'Uso Principali (Siti di Riferimento)

I seguenti siti sono stati indicati dall'utente come casi d'uso primari. La skill deve funzionare correttamente su tutti.

| Sito | Tipo | Note tecniche |
|---|---|---|
| `help.sap.com/docs/SAP_BUSINESS_ONE/...` | Documentazione SAP | JS-rendered, struttura profonda |
| `help.sap.com/doc/...` (Service Layer API) | API Reference | Potenzialmente molto grande |
| `help.boyum-it.com/B1UP/` | Documentazione prodotto | Struttura da analizzare |
| `help.beascloud.com/beas202404/` | Documentazione prodotto | Struttura da analizzare |
| `help.beascloud.com/script202404/` | Documentazione scripting | Potrebbe contenere molti blocchi di codice |
| `learn.microsoft.com/en-us/entra/...` | Documentazione Microsoft | JS-rendered, struttura molto profonda |

---

## 10. Vincoli e Limitazioni Note

1. **Network egress**: alcuni domini potrebbero essere bloccati dalle impostazioni di rete di Cowork. La skill non può aggirare queste restrizioni; può solo rilevare il blocco e informare l'utente.
2. **Siti autenticati**: la skill opera solo su contenuto pubblicamente accessibile senza credenziali.
3. **Anti-scraping**: alcuni siti usano tecniche anti-bot (Cloudflare, reCAPTCHA). La skill non implementa bypass di questi sistemi; in tal caso segnala il problema all'utente.
4. **Dimensione documenti**: documenti con migliaia di pagine e molte immagini incorporate possono superare i 100–200 MB. La stima preventiva serve a informare l'utente prima di procedere.
5. **Contenuto dinamico personalizzato**: contenuto reso lato client in base a sessione utente, geolocalizzazione o A/B testing non è riproducibile in modo deterministico.

---

## 11. Decisioni Tecniche di Dettaglio

| # | Aspetto | Decisione |
|---|---|---|
| A | Tab e accordion nascosti | La skill espande tutti i pannelli JS (tab, accordion) usando il browser per estrarne il contenuto completo |
| B | Deduplicazione URL | Usa il tag `<link rel="canonical">` indicato dal sito; in sua assenza, normalizzazione URL standard (lowercase, rimozione trailing slash, rimozione parametri di sessione) |
| C | Sitemap XML | Se disponibile (`/sitemap.xml` o dichiarata in `robots.txt`), usata come lista primaria delle pagine. I link interni nelle pagine integrano le eventuali pagine mancanti dalla sitemap |
| D | Robots.txt | Rispettato. Le direttive `Disallow` per lo user-agent della skill vengono seguite; le sezioni escluse vengono elencate nel documento con una nota |

---

*Fine documento di specifica v1.0 — APPROVATA*
