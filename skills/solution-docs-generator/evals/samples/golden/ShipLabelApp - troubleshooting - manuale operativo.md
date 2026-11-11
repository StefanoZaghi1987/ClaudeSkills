---
title: ShipLabelApp – Manuale di troubleshooting
subtitle: Manuale operativo · Diagnosi e risoluzione dei problemi
lang: it
type: troubleshooting
version: "1.0"
date: 11/11/2026
ref: Esempio di riferimento
author: Elena Martinelli
fields:
  - Rif.: Richiesta DOC-2026-118 – inventario applicazioni, voce ShipLabelApp
  - Redatto da: Elena Martinelli (ICT – Applicazioni)
  - Versione: 1.0 del 11/11/2026
  - Classificazione: guida completa – manutenzione e troubleshooting
  - Destinatari: Magazzino spedizioni (Parte A) · ICT (Parte B)
  - Fonti: sessione registrata (trascrizione) e messaggi della chat della sessione, codice sorgente di ShipLabelApp, mail del ticket 4711, appunti di installazione del 2023
  - Documenti collegati: ShipLabelApp – Manuale utente · ShipLabelApp – Manuale di configurazione
notice: Documento interno. Non riportare mai in questo documento password, client secret o altre credenziali.
revisions:
  - 1.0 | 11/11/2026 | Elena Martinelli | Prima stesura
ids: [S, A, Q]
toc: true
toc_levels: 2
---

# 1. Sintesi

ShipLabelApp è l'applicazione con cui il magazzino spedizioni stampa le etichette dei colli
partendo dai documenti di trasporto (DDT) registrati nel gestionale OrbitERP. Gli operatori la
usano tutti i giorni, dai PC del banco imballi e dai palmari, accedendo con l'account aziendale
(login Microsoft, Microsoft Entra ID).

L'applicazione è composta da un front-end React e da un back-end ASP.NET Core 8 pubblicato su IIS.
Il back-end non legge mai direttamente il database: ogni dato passa dalla Orbit Data API, le API
del gestionale. La stampa è affidata al servizio Windows `LabelPrintService` sul server `PRN01`,
che riceve dal back-end il PDF dell'etichetta e il nome della stampante dell'utente.

Questo manuale serve a chi deve reagire quando le etichette non escono (Parte A, operatori del
magazzino) e a chi deve diagnosticare e risolvere il problema (Parte B, ICT).

## 1.1 Scheda della soluzione

La tabella riassume l'identità della soluzione.

| Voce | Descrizione |
|---|---|
| Soluzione | ShipLabelApp |
| Scopo | Stampa delle etichette di spedizione dei colli a partire dai documenti di trasporto di OrbitERP |
| Utenti | Operatori del magazzino spedizioni, dai PC del banco imballi e dai palmari |
| Accesso | Account aziendale, login Microsoft (Microsoft Entra ID) |
| Criticità | Uso quotidiano: un fermo blocca la stampa delle etichette dei colli in partenza |
| Componenti | Front-end React · back-end ASP.NET Core 8 su IIS · Orbit Data API · `LabelPrintService` su `PRN01` |
| Ambienti | Produzione `APP01` · test `APPTEST01` · print server `PRN01` |
| Referenti | Marco Neri (ICT, referente tecnico dell'applicazione) · Helpdesk ICT |
| Classificazione | Guida completa – manutenzione e troubleshooting |
| Destinatari | Magazzino spedizioni (Parte A) · ICT (Parte B) |
| Fonti | Sessione registrata e chat, codice sorgente, ticket 4711, appunti di installazione del 2023 |

Table: Scheda della soluzione ShipLabelApp {widths=25,75}

## 1.2 Come usare questo manuale

Il manuale è diviso in due parti, una per ciascun pubblico.

| Lettore | Cosa leggere | Per fare cosa |
|---|---|---|
| Operatore del magazzino spedizioni | Capitoli 2, 3 e 4 | Evitare i problemi noti, reagire a un messaggio, segnalare un problema in modo utile |
| Responsabile del magazzino (key user) | Parte A e indice rapido dei sintomi | Riconoscere il problema e decidere quando chiamare l'assistenza |
| ICT | Parte B e appendici | Diagnosticare con il metodo del capitolo 7, applicare le schede del capitolo 8 e le procedure del capitolo 9 |

Table: Chi legge cosa {widths=28,32,40}

Le schede di troubleshooting hanno un identificativo `S` (S01, S02…), le anomalie note un
identificativo `A` (A01…), le query diagnostiche un identificativo `Q` (Q01…). Gli identificativi
non cambiano tra una versione e l'altra del manuale.

## 1.3 Indice rapido dei sintomi

Partire dal sintomo osservato, eseguire la prima azione e, se il problema resta, aprire la scheda.

| Sintomo | Prima azione | Schede |
|---|---|---|
| Nessun utente riesce ad accedere con l'account aziendale | Verificare con un secondo utente; avvisare subito l'ICT | S01 |
| Errori su ogni operazione dopo una pausa | Uscire dall'applicazione e accedere di nuovo | S02 |
| L'elenco dei documenti di trasporto è vuoto | Verificare con un collega; se è vuoto per tutti, avvisare l'ICT | S03 |
| Un documento di trasporto non compare nell'elenco | Verificare in OrbitERP che il DDT sia aperto e abbia i colli | S04 |
| "Etichetta inviata alla stampante" ma non esce nulla, per un solo utente | Non ripetere la stampa; segnalare utente e ora all'ICT | S05 |
| Non esce nessuna etichetta, per nessun utente | Avvisare subito l'ICT; annotare i DDT da ristampare | S06 |
| Messaggio "Troppe etichette (massimo 50 per stampa)" | Dividere la stampa in gruppi di 50 etichette al massimo | S07 |
| Escono solo alcune delle etichette richieste | Annotare quali etichette sono uscite prima di ristampare | S08 |
| Le etichette escono su una stampante sbagliata | Verificare quale utente è collegato alla postazione | S09 |

Table: Indice rapido dei sintomi {widths=40,42,18}

::: important
Il messaggio "Etichetta inviata alla stampante" **non** garantisce che l'etichetta sia stata
stampata: l'applicazione lo mostra anche quando l'utente non ha una stampante configurata (A01).
Dopo ogni stampa controllare che le etichette siano uscite.
:::

::: part Parte A – Guida per gli operatori e i key user

Questa parte è per gli operatori del magazzino spedizioni e per i loro responsabili: le regole
che evitano i problemi più frequenti, cosa fare quando qualcosa non funziona e come segnalare un
problema all'assistenza.

Non servono conoscenze tecniche. Le ragioni di ogni regola sono spiegate nella Parte B.
:::

# 2. Regole di buon utilizzo

Ogni regola di questo capitolo evita un problema già capitato o previsto dal funzionamento
dell'applicazione.

## 2.1 Accesso e sessione

- Accedere sempre con il proprio account aziendale. La stampante usata dipende dall'utente
  collegato, non dalla postazione (A05).
- Dopo una pausa lunga (oltre 30 minuti senza usare l'applicazione) uscire e accedere di nuovo
  prima di stampare: la sessione verso il gestionale scade dopo 30 minuti di inattività.
- Su un PC o un palmare condiviso uscire dall'applicazione a fine turno, così il collega del turno
  successivo stampa sulla propria stampante.

## 2.2 Stampa delle etichette

- Stampare al massimo 50 etichette per volta. Oltre questo numero l'applicazione rifiuta la
  richiesta con il messaggio "Troppe etichette (massimo 50 per stampa)" e non stampa nulla.
- Dopo il messaggio "Etichetta inviata alla stampante" controllare che le etichette siano uscite
  davvero. Il messaggio conferma solo che la richiesta è stata accettata.
- Se non esce nulla, non ripetere la stampa più volte: annotare i documenti di trasporto e
  segnalare il problema. Quando il problema è risolto si ristampa una volta sola, senza
  etichette doppie.
- Se escono solo alcune etichette, annotare quali sono uscite prima di ristamparle (A03).

## 2.3 Nuovi colleghi e cambi di postazione

- Quando un nuovo operatore inizia a usare ShipLabelApp, chiedere all'ICT di configurare la sua
  stampante **prima** del primo turno. Senza questa configurazione l'applicazione mostra
  "Etichetta inviata alla stampante" ma non stampa nulla.
- Quando un operatore cambia stabilmente banco o stampante, chiedere all'ICT di aggiornare la
  sua stampante.

# 3. Cosa fare quando…

La tabella elenca le situazioni più comuni, l'azione immediata e il momento in cui chiamare
l'assistenza.

| Situazione o messaggio | Cosa fare subito | Quando chiamare l'assistenza |
|---|---|---|
| Non riesco ad accedere con l'account aziendale | Chiudere il browser e riprovare; chiedere a un collega se riesce ad accedere | Subito se nessuno riesce ad accedere |
| Errori su ogni operazione dopo una pausa | Uscire dall'applicazione e accedere di nuovo | Se l'errore resta dopo il nuovo accesso |
| L'elenco dei documenti di trasporto è vuoto | Uscire e accedere di nuovo; chiedere a un collega se vede i documenti | Se l'elenco è vuoto anche per i colleghi |
| Un documento di trasporto non compare | Chiedere all'ufficio spedizioni se il DDT è aperto e ha i colli registrati | Se il DDT è aperto, ha i colli e non compare |
| "Etichetta inviata alla stampante" ma non esce nulla | Controllare che la stampante sia accesa e abbia le etichette; non ripetere la stampa | Subito, indicando utente, ora e DDT |
| Non esce nessuna etichetta per nessuno | Annotare i DDT da stampare | Subito: è un fermo del servizio di stampa |
| "Troppe etichette (massimo 50 per stampa)" | Dividere la stampa in gruppi di 50 etichette al massimo | Non serve |
| Escono solo alcune etichette | Annotare quali etichette sono uscite; ristampare solo le mancanti | Se si ripete |
| Le etichette escono su un'altra stampante | Verificare con quale utente si è collegati; uscire e accedere con il proprio account | Se la stampante è sbagliata anche con il proprio account |

Table: Cosa fare quando… {widths=30,40,30}

::: tip
Quando le etichette non escono, tenere un elenco dei DDT rimasti senza etichetta: dopo la
soluzione la ristampa sarà più rapida e senza doppioni.
:::

# 4. Come segnalare un problema all'assistenza

Scrivere all'Helpdesk ICT (`helpdesk@acme-components.example`). Una segnalazione completa
permette di trovare subito l'errore nei log.

| Informazione | Perché serve |
|---|---|
| Ora del problema (hh:mm) | I log dell'applicazione sono un file al giorno: senza l'ora è difficile trovare l'errore |
| Utente con cui si è collegati | La stampante è configurata per utente: l'ICT verifica la configurazione di quell'utente |
| Numero del documento di trasporto | Permette di verificare se il DDT è visibile all'applicazione e quali colli ha |
| Messaggio mostrato, parola per parola | Distingue i casi: limite di 50 etichette, sessione scaduta, stampa non uscita |
| Numero di etichette richieste | Oltre 50 etichette la richiesta viene rifiutata |
| Postazione (PC del banco imballi o palmare) e stampante attesa | Aiuta a riconoscere una stampante configurata in modo errato |
| Se il problema riguarda solo lei o anche i colleghi | Distingue un problema di configurazione dell'utente da un fermo del servizio |

Table: Informazioni da indicare nella segnalazione {widths=35,65}

::: part Parte B – Guida tecnica

Questa parte è per l'ICT: architettura, concetti necessari alla diagnosi, metodo di diagnosi,
schede di troubleshooting, procedure di ripristino, anomalie note e casi storici.

Le credenziali dell'utenza di servizio e il client secret dell'applicazione sono conservati nel
password manager aziendale e non sono riportati in questo manuale.
:::

# 5. Architettura e dipendenze

Il capitolo descrive i componenti di ShipLabelApp, gli ambienti, il flusso delle chiamate e i dati
che l'applicazione legge.

## 5.1 Componenti

| Componente | Tecnologia | Dove gira | Ruolo |
|---|---|---|---|
| Front-end | React (cartella `client/`) | Browser dei PC del banco imballi e dei palmari | Interfaccia: elenco dei DDT, richiesta di stampa |
| Back-end | ASP.NET Core 8 (`src/ShipLabelApp.Api`) su IIS | `APP01` (produzione), `APPTEST01` (test) | API `api/label`, controllo del limite di stampa, ricerca della stampante, invio dei PDF |
| Orbit Data API | API del gestionale OrbitERP | `erp01.acme.local`, porta 50000 | Unico accesso ai dati: vista dei DDT, stampante dell'utente, PDF dell'etichetta |
| `LabelPrintService` | Servizio Windows | `PRN01` (print server) | Riceve PDF e nome stampante e stampa l'etichetta |
| Microsoft Entra ID | Registrazione dell'app nel tenant aziendale | Cloud Microsoft | Autenticazione degli utenti con l'account aziendale |

Table: Componenti di ShipLabelApp {widths=17,25,23,35}

## 5.2 Ambienti e server

| Ambiente | Server applicativo | Indirizzi e servizi |
|---|---|---|
| Produzione | `APP01` (IIS) | Orbit Data API `https://erp01.acme.local:50000/api/v2` · stampa `http://prn01.acme.local:8085/print` |
| Test | `APPTEST01` (IIS) | [da confermare: indirizzi della Orbit Data API e del servizio di stampa usati in test; la configurazione per ambiente non è tra le fonti] |
| Print server | `PRN01` | `LabelPrintService`, log in `C:\Logs\LabelPrintService` |

Table: Ambienti e server {widths=18,22,60}

::: verify
Il file `appsettings.json` analizzato contiene un solo insieme di indirizzi, senza varianti per
ambiente. Verificare su `APPTEST01` quali indirizzi sono configurati e se il test stampa sullo
stesso `PRN01` della produzione.
:::

## 5.3 Flusso delle chiamate

1. L'operatore accede con l'account aziendale: l'autenticazione è gestita da Microsoft Entra ID.
2. Il front-end chiede l'elenco dei documenti (`GET api/label/documents`); il back-end lo legge
   dalla vista `ACM_VIEW_LABELS` attraverso la Orbit Data API, con l'utenza di servizio
   `svc_labels`.
3. L'operatore seleziona i colli e chiede la stampa (`POST api/label/print`).
4. Il back-end rifiuta la richiesta se i colli sono più di 50.
5. Il back-end cerca la stampante dell'utente nella tabella `ACM_USER_PRINTERS`, sempre
   attraverso la Orbit Data API.
6. Per ogni collo il back-end chiede alla Orbit Data API il PDF dell'etichetta e lo invia a
   `LabelPrintService` su `PRN01` insieme al nome della stampante.
7. Il back-end risponde "Etichetta inviata alla stampante".

Il dettaglio delle chiamate, con classi e metodi, è nell'appendice B.

## 5.4 Dati

| Oggetto | Tipo | Contenuto | Usato per |
|---|---|---|---|
| `ACM_VIEW_LABELS` | Vista | DDT aperti con i loro colli: `DocNum`, `DocDate`, `CardName`, `ParcelId`, `Weight` | Elenco dei documenti da etichettare |
| `DELIVERY_NOTES` | Tabella di OrbitERP | Testate dei documenti di trasporto, con lo stato (`Status`) | Base della vista |
| `PARCELS` | Tabella di OrbitERP | Colli dei documenti di trasporto (`DocEntry`, `ParcelId`, `Weight`) | Base della vista |
| `ACM_USER_PRINTERS` | Tabella utente | Una riga per utente: `UserName`, `PrinterName` | Stampante su cui stampare |

Table: Tabelle e viste usate da ShipLabelApp {widths=22,18,38,22}

## 5.5 Codice sorgente, configurazione e log

- Codice sorgente: front-end in `client/`, back-end in `src/ShipLabelApp.Api`, definizione della
  vista in `database/ACM_VIEW_LABELS.sql`.
  [da confermare: posizione del repository e versione installata in produzione]
- Configurazione del back-end: `appsettings.json` del sito su IIS. Le chiavi principali sono
  elencate nella tabella seguente; i valori delle credenziali non sono riportati.
- Log dell'applicazione: `C:\Logs\ShipLabelApp` sul server applicativo, un file al giorno.
- Log del servizio di stampa: `C:\Logs\LabelPrintService` su `PRN01`.

| Chiave | Valore o significato |
|---|---|
| `OrbitApi:BaseUrl` | Indirizzo della Orbit Data API (`https://erp01.acme.local:50000/api/v2`) |
| `OrbitApi:User` | Utenza di servizio `svc_labels` |
| `OrbitApi:Password` | Credenziale dell'utenza di servizio: nel password manager aziendale |
| `AzureAd:TenantId`, `AzureAd:ClientId` | Tenant e applicazione registrata su Microsoft Entra ID |
| `AzureAd:ClientSecret` | Client secret dell'app registrata: nel password manager aziendale, scade il 15/09/2027 |
| `Session:TimeoutMinutes` | Durata della sessione senza attività: 30 minuti |
| `Printing:ServiceUrl` | Indirizzo di `LabelPrintService` (`http://prn01.acme.local:8085/print`) |
| `Printing:MaxLabelsPerRequest` | Numero massimo di etichette per richiesta: 50 |
| `Serilog:LogPath`, `Serilog:RollingInterval` | File di log `C:\Logs\ShipLabelApp\log-.txt`, un file al giorno |

Table: Chiavi di configurazione del back-end {widths=35,65}

# 6. Concetti chiave per la diagnosi

Il capitolo spiega i meccanismi che stanno dietro alla maggior parte dei problemi. Leggerlo prima
di usare le schede del capitolo 8.

## 6.1 Tutto passa dalla Orbit Data API

Il back-end non apre mai una connessione al database. L'elenco dei DDT, la stampante dell'utente
e il PDF di ogni etichetta arrivano dalla Orbit Data API, con l'utenza di servizio `svc_labels`.
Le sue credenziali sono nel password manager aziendale.

Conseguenza per la diagnosi: se la Orbit Data API non risponde o rifiuta l'utenza di servizio,
falliscono insieme l'elenco dei documenti e la stampa. Un problema che riguarda solo la stampa o
solo un utente ha invece una causa più a valle (stampante dell'utente, `LabelPrintService`).

## 6.2 Accesso con Microsoft Entra ID

Gli utenti accedono con l'account aziendale. Il back-end è registrato come applicazione su
Microsoft Entra ID e usa un client secret, conservato nel password manager aziendale. Il client
secret scade il 15/09/2027: se scade, nessun utente riesce più ad accedere. Va rinnovato prima
della scadenza e aggiornato nella configurazione del back-end (procedura 9.4).

## 6.3 Sessione di 30 minuti

La sessione verso le API scade dopo 30 minuti di inattività (chiave `Session:TimeoutMinutes` = 30
nella configurazione, confermato nella sessione registrata). Dopo una pausa lunga conviene uscire
e accedere di nuovo.

::: note
Gli appunti di installazione del 2023 indicano una sessione di 60 minuti. Il dato è superato: vale
la configurazione attuale, 30 minuti.
:::

## 6.4 La catena di stampa

Una richiesta di stampa attraversa quattro passaggi, ognuno dei quali può interrompere la catena:

1. **Controllo del limite**: oltre 50 colli la richiesta è rifiutata con "Troppe etichette
   (massimo 50 per stampa)" e non si stampa nulla.
2. **Ricerca della stampante**: il back-end legge la riga dell'utente in `ACM_USER_PRINTERS`. La
   stampante è legata all'utente, non alla postazione. La tabella è letta a ogni stampa: una riga
   aggiunta o corretta vale dalla stampa successiva, senza riavvii.
3. **PDF dell'etichetta**: per ogni collo il back-end chiede il PDF alla Orbit Data API.
4. **Invio a `LabelPrintService`**: il PDF e il nome della stampante vanno al servizio su `PRN01`,
   che stampa.

Il messaggio "Etichetta inviata alla stampante" è mostrato alla fine, in ogni caso in cui non si
verifica un errore. Non dice che la stampante ha stampato.

::: technical
- `LabelController.Print()` restituisce sempre il messaggio "Etichetta inviata alla stampante" con
  il campo `queued` preso dal risultato del servizio.
- `LabelService.PrintAsync()` restituisce `Queued: true` in entrambi i rami: anche quando
  `GetUserPrinterAsync()` non trova la stampante dell'utente. In quel caso non invia nulla e
  scrive nel log solo a livello Debug il messaggio "No printer configured for {User}".
- Il limite di 50 è la proprietà `LabelService.MaxLabelsPerRequest`, inizializzata a 50 nel
  codice. La chiave `Printing:MaxLabelsPerRequest` di `appsettings.json` ha lo stesso valore, ma
  nel codice analizzato non viene letta: modificarla potrebbe non avere effetto.
  [da confermare: se la chiave è letta in un'altra parte del back-end]
- I colli sono inviati uno alla volta: se un invio fallisce, quelli precedenti sono già stati
  stampati (A03).
:::

## 6.5 La vista dei documenti da etichettare

L'elenco dei documenti mostrato all'operatore è il contenuto della vista `ACM_VIEW_LABELS`. La
vista unisce i DDT (`DELIVERY_NOTES`) con i loro colli (`PARCELS`) e tiene solo i DDT aperti
(`Status = 'O'`). Ne derivano due regole utili per la diagnosi:

- un DDT chiuso, o un DDT senza colli registrati, non compare nell'elenco (A04);
- se dopo un rilascio la vista non è aggiornata, l'elenco dei documenti resta vuoto (S03).

## 6.6 Log e livelli di dettaglio

Il back-end scrive i log in `C:\Logs\ShipLabelApp`, un file al giorno (`log-<data>.txt`). Il caso
dell'utente senza stampante è registrato solo a livello Debug: se il livello minimo dei log in
produzione è superiore, nel file non compare nulla.
[da confermare: livello minimo di log configurato su `APP01`]

`LabelPrintService` scrive i propri log in `C:\Logs\LabelPrintService` su `PRN01`.

# 7. Metodo di diagnosi

Procedere per livelli, dal più rapido al più invasivo. Passare al livello successivo solo quando
il precedente non ha chiarito la causa.

| Livello | Strumento | Dove | Cosa si scopre |
|---|---|---|---|
| 1 | Raccolta informazioni e riproduzione | Segnalazione dell'operatore (capitolo 4) | Chi, quando, quale DDT, quale messaggio; se il problema è di un utente o di tutti |
| 2 | Console del browser (F12 › Rete) | PC del banco imballi | Quale chiamata fallisce (`api/label/documents`, `api/label/print`) e con quale stato HTTP |
| 3 | Log dell'applicazione | `C:\Logs\ShipLabelApp` su `APP01` | Errori del back-end e delle chiamate alla Orbit Data API, all'ora indicata |
| 4 | Console dei servizi e log di stampa | `PRN01`: stato di `LabelPrintService`, `C:\Logs\LabelPrintService` | Se il servizio è in esecuzione e se ha ricevuto e stampato i PDF |
| 5 | Piattaforme | IIS su `APP01`; Microsoft Entra ID (registrazione dell'app) | Sito e Application Pool avviati; stato e scadenza del client secret |
| 6 | Database, in sola lettura | Database di OrbitERP, query dell'appendice A | Stampante dell'utente, contenuto della vista, stato del DDT |

Table: Livelli di diagnosi {widths=9,24,30,37}

Indicazioni per i livelli:

- **Livello 1.** Chiedere sempre se il problema riguarda un solo utente o tutti: un solo utente
  indica la configurazione della stampante (S05), tutti indicano un componente comune (S06, S01).
- **Livello 2.** Sui palmari la console del browser non è comoda da usare: riprodurre il problema
  da un PC del banco imballi con lo stesso utente.
- **Livello 3.** Cercare nel file del giorno le righe intorno all'ora segnalata.
- **Livello 6.** Usare solo query `SELECT`. Le modifiche ai dati passano dalle procedure del
  capitolo 9.

# 8. Schede di troubleshooting

Ogni scheda riporta sintomo, chi interviene, cause probabili in ordine di probabilità, come
verificare e come risolvere. Le query citate sono nell'appendice A, le procedure nel capitolo 9.

## 8.1 Accesso e sessione

### S01 · Nessun utente riesce ad accedere

::: card
Sintomo: nessun operatore riesce ad accedere con l'account aziendale; il problema riguarda tutti gli utenti e tutte le postazioni [da confermare: messaggio mostrato al login].
Chi interviene: Operatore (avvisa l'Helpdesk), poi ICT.
Cause probabili:
- Client secret dell'app registrata su Microsoft Entra ID scaduto (scadenza 15/09/2027) o non aggiornato nella configurazione dopo un rinnovo.
- Sito o Application Pool di ShipLabelApp fermo su IIS di `APP01`.
- `APP01` non raggiungibile dalla rete del magazzino.
Come verificare:
- Livello 2: stato HTTP della chiamata di login nella console del browser.
- Log del giorno in `C:\Logs\ShipLabelApp` su `APP01`: errori di autenticazione verso Microsoft Entra ID.
- Microsoft Entra ID: data di scadenza del client secret dell'app registrata.
- IIS su `APP01`: sito e Application Pool avviati.
Come risolvere:
- Client secret scaduto o errato: procedura 9.4.
- Sito o Application Pool fermo: avviarlo da IIS e verificare l'accesso con un utente di prova.
:::

### S02 · Errori su ogni operazione dopo una pausa

::: card
Sintomo: dopo una pausa lunga ogni operazione dell'applicazione restituisce un errore [da confermare: testo del messaggio di sessione scaduta].
Chi interviene: Operatore.
Cause probabili:
- Sessione verso le API scaduta dopo 30 minuti di inattività (paragrafo 6.3).
Come verificare:
- L'errore compare alla prima operazione dopo la pausa e scompare dopo un nuovo accesso.
Come risolvere:
- Uscire dall'applicazione e accedere di nuovo. I DDT e le etichette già stampate non sono toccati.
- Se l'errore resta dopo il nuovo accesso, trattare il caso come S01.
:::

## 8.2 Elenco dei documenti di trasporto

### S03 · L'elenco dei documenti di trasporto è vuoto

::: card
Sintomo: l'elenco dei documenti da etichettare è vuoto, per tutti gli utenti, anche se in OrbitERP esistono DDT aperti con colli.
Chi interviene: ICT.
Cause probabili:
- Vista `ACM_VIEW_LABELS` non aggiornata dopo un rilascio.
- Orbit Data API non raggiungibile, oppure utenza di servizio `svc_labels` rifiutata (credenziali cambiate o bloccate).
- Nessun DDT aperto con colli in quel momento (A04).
Come verificare:
- Log del giorno in `C:\Logs\ShipLabelApp`: errori sulla lettura di `ACM_VIEW_LABELS` o sull'autenticazione di `svc_labels`.
- Query Q05: righe presenti nella vista.
- Query Q04 su un DDT che dovrebbe comparire.
Come risolvere:
- Vista non aggiornata: procedura 9.3.
- Utenza di servizio rifiutata: verificare le credenziali nel password manager aziendale e lo stato dell'utenza `svc_labels` in OrbitERP.
- Orbit Data API ferma: coinvolgere i referenti di OrbitERP.
:::

### S04 · Un documento di trasporto non compare nell'elenco

::: card
Sintomo: l'elenco mostra i documenti, ma un DDT specifico non c'è.
Chi interviene: Operatore (verifica con l'ufficio spedizioni), poi ICT.
Cause probabili:
- Il DDT non è aperto (`Status` diverso da `'O'`) (A04).
- Il DDT non ha colli registrati (A04).
Come verificare:
- Query Q04: stato del DDT e numero di colli.
- Query Q03: righe del DDT nella vista.
Come risolvere:
- DDT chiuso o senza colli: correggere il documento in OrbitERP secondo le regole dell'ufficio spedizioni; il DDT compare al successivo aggiornamento dell'elenco.
- DDT aperto, con colli, ma assente dalla vista: verificare la definizione della vista (procedura 9.3).
:::

## 8.3 Stampa

### S05 · "Etichetta inviata alla stampante" ma non esce nulla

::: card
Sintomo: l'applicazione mostra "Etichetta inviata alla stampante", ma dalla stampante non esce nessuna etichetta. Di solito riguarda un solo utente, spesso un utente nuovo.
Chi interviene: Operatore (controlla stampante e carta), poi ICT.
Cause probabili:
- Nessuna riga per l'utente in `ACM_USER_PRINTERS`: l'applicazione non invia nulla ma conferma comunque la stampa (A01).
- Nome della stampante errato nella riga dell'utente.
- `LabelPrintService` fermo su `PRN01` (ticket 4711): in questo caso il problema riguarda tutti gli utenti (S06).
- Stampante spenta, senza etichette o in errore.
Come verificare:
- Query Q01 con il nome dell'utente: la riga esiste e `PrinterName` è corretto?
- Log del giorno in `C:\Logs\ShipLabelApp`: "No printer configured for …" (presente solo se il livello Debug è attivo).
- `PRN01`: stato di `LabelPrintService` e log in `C:\Logs\LabelPrintService` all'ora della stampa.
Come risolvere:
- Riga mancante o errata: procedura 9.1, poi ristampare.
- Servizio fermo: procedura 9.2.
- Stampante in errore: ripristinare la stampante e ristampare.
:::

### S06 · Non esce nessuna etichetta, per nessun utente

::: card
Sintomo: nessuna etichetta esce su nessuna stampante, mentre l'applicazione continua a confermare le stampe (A02).
Chi interviene: ICT.
Cause probabili:
- `LabelPrintService` fermo su `PRN01`, tipicamente dopo un riavvio per gli aggiornamenti di Windows con tipo di avvio "Manuale" (caso storico 11.1).
- `PRN01` non raggiungibile da `APP01` sulla porta 8085.
- Orbit Data API non disponibile: in questo caso è vuoto anche l'elenco dei documenti (S03).
Come verificare:
- `PRN01`: stato e tipo di avvio di `LabelPrintService` nella console dei servizi.
- Log in `C:\Logs\LabelPrintService`: ultima stampa registrata.
- Log del giorno in `C:\Logs\ShipLabelApp`: errori di invio verso `http://prn01.acme.local:8085/print`.
Come risolvere:
- Servizio fermo: procedura 9.2, poi far ristampare le etichette non uscite.
- `PRN01` non raggiungibile: ripristinare il server o la rete, poi ripetere le verifiche della procedura 9.2.
:::

### S07 · Messaggio "Troppe etichette (massimo 50 per stampa)"

::: card
Sintomo: la stampa è rifiutata con il messaggio "Troppe etichette (massimo 50 per stampa)"; non esce nessuna etichetta.
Chi interviene: Operatore.
Cause probabili:
- Sono stati selezionati più di 50 colli in una sola richiesta: il back-end rifiuta la richiesta intera (risposta HTTP 400).
Come verificare:
- Contare i colli selezionati: il limite è 50 per richiesta, 50 compresi.
Come risolvere:
- Dividere la stampa in più richieste di 50 etichette al massimo.
- Il limite è fissato nel codice del back-end: un aumento può richiedere una modifica dell'applicazione e non solo della configurazione (paragrafo 6.4).
:::

### S08 · Escono solo alcune delle etichette richieste

::: card
Sintomo: di una richiesta con più colli escono solo le prime etichette [da confermare: messaggio mostrato all'operatore quando l'invio si interrompe].
Chi interviene: Operatore (annota le etichette uscite), poi ICT.
Cause probabili:
- Errore nell'invio di un collo a `LabelPrintService` o nella lettura del suo PDF dalla Orbit Data API: le etichette precedenti sono già state stampate (A03).
- `LabelPrintService` fermato durante la richiesta (S06).
Come verificare:
- Log del giorno in `C:\Logs\ShipLabelApp` all'ora della stampa: errore e collo su cui si è interrotto l'invio.
- Log in `C:\Logs\LabelPrintService`: etichette ricevute.
Come risolvere:
- Ristampare solo le etichette mancanti, per evitare doppioni.
- Se l'errore si ripete sullo stesso collo, verificare il collo con la query Q03 e coinvolgere i referenti di OrbitERP.
:::

### S09 · Le etichette escono su una stampante sbagliata

::: card
Sintomo: le etichette escono, ma su una stampante diversa da quella del banco in cui si lavora.
Chi interviene: Operatore, poi ICT.
Cause probabili:
- La postazione è collegata con l'account di un altro operatore: la stampante dipende dall'utente, non dalla postazione (A05).
- L'operatore ha cambiato banco e la sua riga in `ACM_USER_PRINTERS` indica ancora la stampante precedente.
- Nome della stampante errato nella riga dell'utente.
Come verificare:
- Utente collegato sulla postazione.
- Query Q01 con il nome dell'utente: valore di `PrinterName`.
Come risolvere:
- Uscire e accedere con il proprio account.
- Riga da aggiornare: procedura 9.1.
:::

# 9. Procedure di ripristino

Le procedure sono citate dalle schede del capitolo 8. Sono riservate all'ICT; quando la procedura
lo consente, provarla prima nell'ambiente di test (`APPTEST01`).

## 9.1 Configurare la stampante di un utente

Prerequisiti: nome dell'utente e nome della stampante da usare; diritti di modifica sulla tabella
utente `ACM_USER_PRINTERS` in OrbitERP.
[da confermare: strumento con cui si inserisce o modifica la riga, maschera di OrbitERP o script]

1. Eseguire la query Q01 con il nome dell'utente per verificare se la riga esiste già.
2. Eseguire la query Q02 e confrontare il formato di `UserName` e di `PrinterName` con quello
   degli utenti già configurati.
   [da confermare: formato atteso di `UserName` (account completo o nome breve) e di `PrinterName`]
3. Verificare su `PRN01` il nome esatto della stampante da usare.
4. Inserire la riga (`UserName`, `PrinterName`), oppure correggere `PrinterName` se la riga
   esiste, con lo strumento previsto.
5. Eseguire di nuovo la query Q01: la riga deve comparire con i valori corretti.
6. Chiedere all'operatore di stampare un'etichetta di prova.

Risultato atteso: l'etichetta esce sulla stampante indicata. Non serve riavviare nulla: la
tabella è letta a ogni stampa.

Se l'etichetta non esce: verificare il log di `LabelPrintService` su `PRN01` all'ora della prova e
proseguire con la scheda S06.

## 9.2 Riavviare LabelPrintService su PRN01

Prerequisiti: accesso amministrativo a `PRN01`.

::: warning
Durante il riavvio nessuna etichetta viene stampata. Avvisare il banco imballi prima di
procedere e chiedere di sospendere le stampe.
:::

1. Accedere a `PRN01` e aprire la console dei servizi di Windows.
2. Individuare `LabelPrintService` e annotarne stato e tipo di avvio.
3. Se il servizio è fermo, avviarlo; se è in esecuzione ma non stampa, riavviarlo.
4. Verificare che lo stato sia "In esecuzione".
5. Verificare che il tipo di avvio sia "Automatico (avvio ritardato)"; se è "Manuale", impostarlo
   a "Automatico (avvio ritardato)".
6. Aprire il log del giorno in `C:\Logs\LabelPrintService` e verificare che non ci siano errori
   all'avvio.
7. Chiedere al banco imballi una stampa di prova.
8. Chiedere al banco imballi di ristampare le etichette richieste durante il fermo.

Risultato atteso: l'etichetta di prova esce; il servizio ripartirà da solo al prossimo riavvio di
`PRN01`.

::: important
Le etichette richieste mentre il servizio era fermo non escono da sole dopo il riavvio: vanno
ristampate (caso storico 11.1).
:::

## 9.3 Ripristinare la vista ACM_VIEW_LABELS dopo un rilascio

Prerequisiti: script `database/ACM_VIEW_LABELS.sql` della versione installata; diritti di
modifica delle viste sul database di OrbitERP; finestra concordata con il magazzino.

1. Eseguire la query Q05 per confermare che la vista non restituisce righe.
2. Eseguire la query Q04 su un DDT aperto con colli: se le tabelle hanno dati, il problema è la
   vista.
3. Confrontare la definizione della vista in produzione con lo script della versione installata.
4. Applicare lo script in test e verificare con la query Q05 che la vista restituisca righe.

::: warning
Il passo successivo modifica un oggetto del database di produzione. Salvare prima la definizione
attuale della vista ed eseguire lo script solo dopo la prova in test.
:::

5. Applicare lo script in produzione.
6. Eseguire la query Q05 e verificare che la vista restituisca righe.
7. Chiedere a un operatore di aggiornare l'elenco dei documenti in ShipLabelApp.

Risultato atteso: l'elenco dei documenti mostra i DDT aperti con colli.

## 9.4 Rinnovare il client secret dell'app su Microsoft Entra ID

Il client secret dell'app registrata su Microsoft Entra ID scade il 15/09/2027. Se scade, nessun
utente riesce più ad accedere. Rinnovarlo con anticipo.

Prerequisiti: diritti di gestione della registrazione dell'app su Microsoft Entra ID; accesso
amministrativo ad `APP01` e `APPTEST01`; accesso in scrittura alla voce di ShipLabelApp nel
password manager aziendale.

1. Su Microsoft Entra ID aprire la registrazione dell'app di ShipLabelApp e creare un nuovo client
   secret, annotandone la scadenza.
2. Salvare subito il nuovo valore nel password manager aziendale. Non scriverlo in mail, ticket o
   documenti.
3. Aggiornare la chiave `AzureAd:ClientSecret` nella configurazione del back-end su `APPTEST01`
   e riavviare l'Application Pool del sito [da confermare: nome dell'Application Pool].
4. Verificare in test l'accesso con un utente di prova.
5. Ripetere i passi 3 e 4 su `APP01`.

::: warning
Eliminare il client secret precedente solo dopo aver verificato l'accesso in produzione: finché
la configurazione non è aggiornata, il back-end usa ancora il secret precedente.
:::

6. Eliminare il client secret precedente su Microsoft Entra ID.
7. Aggiornare la nuova scadenza nella tabella delle scadenze (paragrafo 12.1).

Risultato atteso: gli operatori accedono con l'account aziendale senza errori.

# 10. Anomalie note

Le anomalie note sono comportamenti del software che possono sorprendere un operatore o l'ICT e
che hanno una soluzione alternativa. I riferimenti al codice sono nell'appendice D.

| ID | Comportamento | Effetto | Soluzione alternativa | Schede |
|---|---|---|---|---|
| A01 | Se l'utente non ha una riga in `ACM_USER_PRINTERS`, la richiesta di stampa è segnalata come accodata (`queued`) e l'operatore vede "Etichetta inviata alla stampante"; il caso è registrato nel log solo a livello Debug | Non esce nulla e l'operatore crede che la stampa sia partita; nel log di produzione può non esserci traccia | Configurare la stampante prima del primo turno di ogni nuovo operatore (procedura 9.1); quando non esce nulla per un solo utente, controllare per prima la query Q01 | S05 |
| A02 | Con `LabelPrintService` fermo l'applicazione ha mostrato comunque "Etichetta inviata alla stampante" (ticket 4711) | Il fermo del servizio non è visibile dall'applicazione | Dopo ogni riavvio di `PRN01` verificare che il servizio sia in esecuzione (paragrafo 12.2) | S06 |
| A03 | I colli di una richiesta sono inviati uno alla volta; un errore a metà non annulla gli invii già fatti | Escono solo le prime etichette; ristampando tutto si ottengono doppioni | Annotare le etichette uscite e ristampare solo le mancanti | S08 |
| A04 | La vista `ACM_VIEW_LABELS` contiene solo DDT aperti (`Status = 'O'`) con almeno un collo | Un DDT chiuso o senza colli non compare nell'elenco | Verificare stato e colli con la query Q04 e correggere il DDT in OrbitERP | S03, S04 |
| A05 | La stampante è associata all'utente (una riga per utente), non alla postazione | Chi lavora su una postazione con l'account di un collega stampa sulla stampante del collega | Accedere sempre con il proprio account; aggiornare la riga quando un operatore cambia banco | S09 |

Table: Anomalie note {widths=6,30,22,32,10}

::: verify
A02 deriva dal ticket 4711. Nel codice analizzato l'invio a `LabelPrintService` avviene tramite
l'interfaccia `IPrintClient`, la cui implementazione non è tra le fonti: non è quindi possibile
dire se un errore di invio venga intercettato e nascosto o restituito come errore
[da confermare: comportamento di `IPrintClient` quando `PRN01` non risponde].
:::

# 11. Casi storici

Il capitolo raccoglie i problemi già accaduti, con la diagnosi e la lezione che ne è derivata.

## 11.1 Marzo 2025 – Etichette non stampate dopo gli aggiornamenti di Windows (ticket 4711)

| Voce | Descrizione |
|---|---|
| Data | Martedì 11/03/2025 (aggiornamenti di Windows) – risolto mercoledì 12/03/2025 |
| Ticket | 4711 – "Etichette di spedizione non stampate" |
| Sintomo | Dopo gli aggiornamenti di Windows non usciva più nessuna etichetta; l'applicazione mostrava comunque "Etichetta inviata alla stampante" |
| Diagnosi | `LabelPrintService` su `PRN01` non era ripartito dopo il riavvio del server: il tipo di avvio era "Manuale" |
| Soluzione | Avvio del servizio e impostazione del tipo di avvio "Automatico (avvio ritardato)"; le 37 etichette in coda sono state ristampate dal banco imballi alle 11:30 |
| Lezione | Dopo ogni riavvio di `PRN01` verificare che il servizio sia in esecuzione (paragrafo 12.2) |
| Schede e anomalie | S06, A02 |

Table: Caso storico – ticket 4711 {widths=20,80}

# 12. Controlli periodici e dopo i cambiamenti

Il capitolo elenca le scadenze da sorvegliare e i controlli da eseguire periodicamente e dopo
ogni cambiamento dell'infrastruttura o dell'applicazione.

## 12.1 Scadenze da tenere sotto controllo

| Elemento | Scadenza | Cosa succede se scade | Azione |
|---|---|---|---|
| Client secret dell'app ShipLabelApp su Microsoft Entra ID | 15/09/2027 | Nessun utente riesce più ad accedere (S01) | Rinnovarlo prima della scadenza e aggiornarlo nella configurazione del back-end (procedura 9.4) |

Table: Scadenze da tenere sotto controllo {widths=26,16,26,32}

Dopo ogni rinnovo aggiornare la data di questa tabella con la nuova scadenza.

## 12.2 Dopo gli aggiornamenti di Windows o un riavvio di PRN01

1. Verificare che `LabelPrintService` sia "In esecuzione" e con tipo di avvio "Automatico (avvio
   ritardato)".
2. Chiedere al banco imballi una stampa di prova.
3. Se il servizio è fermo, applicare la procedura 9.2.

## 12.3 Dopo un rilascio di ShipLabelApp

1. Verificare che l'elenco dei documenti non sia vuoto; se lo è, eseguire la query Q05 e, se
   serve, la procedura 9.3.
2. Stampare un'etichetta di prova con un utente configurato.
3. Verificare che non ci siano errori nuovi nel log del giorno in `C:\Logs\ShipLabelApp`.

## 12.4 Dopo gli aggiornamenti di APP01 o della Orbit Data API

1. Verificare che il sito di ShipLabelApp su IIS e il relativo Application Pool siano avviati.
2. Verificare l'accesso con l'account aziendale e la presenza dei documenti nell'elenco.
3. Stampare un'etichetta di prova.

## 12.5 Nuovo operatore o cambio di postazione

1. Configurare la stampante dell'operatore con la procedura 9.1 prima del suo primo turno.
2. Far stampare un'etichetta di prova all'operatore.

## 12.6 Controlli periodici

| Controllo | Quando | Come |
|---|---|---|
| Stato di `LabelPrintService` e tipo di avvio | Dopo ogni riavvio di `PRN01` | Console dei servizi su `PRN01` (paragrafo 12.2) |
| Scadenza del client secret | Con anticipo rispetto al 15/09/2027 | Microsoft Entra ID, registrazione dell'app (paragrafo 12.1) |
| Operatori senza stampante | All'ingresso di ogni nuovo operatore | Query Q02 confrontata con l'elenco degli operatori del magazzino |
| Errori ricorrenti nei log | A ogni segnalazione e dopo ogni rilascio | `C:\Logs\ShipLabelApp` su `APP01` e `C:\Logs\LabelPrintService` su `PRN01` |

Table: Controlli periodici {widths=30,25,45}

# 13. Appendici

Le appendici raccolgono i riferimenti tecnici citati nella Parte B.

## A. Query diagnostiche

Le query sono in sola lettura (`SELECT`) e servono solo alla diagnosi. Sono scritte in SQL
standard sulle tabelle e sulla vista lette dal codice; i valori tra parentesi angolari sono
esempi da sostituire. Le query non sono state provate sul database di produzione.
[da confermare: dialetto e schema del database di OrbitERP, accesso in sola lettura per l'ICT]

**Q01 – Stampante configurata per un utente**

```sql
SELECT UserName, PrinterName
FROM ACM_USER_PRINTERS
WHERE UserName = '<nome utente>';
```

Nessuna riga: l'utente non ha una stampante (A01). Usata dalle schede S05 e S09.

**Q02 – Tutti gli utenti con una stampante**

```sql
SELECT UserName, PrinterName
FROM ACM_USER_PRINTERS
ORDER BY UserName;
```

Serve a confrontare il formato di `UserName` e `PrinterName` prima di inserire una nuova riga
(procedura 9.1).

**Q03 – Righe di un DDT nella vista dei documenti**

```sql
SELECT DocNum, DocDate, CardName, ParcelId, Weight
FROM ACM_VIEW_LABELS
WHERE DocNum = <numero DDT>;
```

Una riga per collo. Nessuna riga: il DDT non è visibile all'applicazione (S04).

**Q04 – Stato e colli di un DDT nelle tabelle di origine**

```sql
SELECT d.DocNum, d.Status, COUNT(p.ParcelId) AS Colli
FROM DELIVERY_NOTES d
LEFT JOIN PARCELS p ON p.DocEntry = d.DocEntry
WHERE d.DocNum = <numero DDT>
GROUP BY d.DocNum, d.Status;
```

`Status` diverso da `'O'` o `Colli` = 0: il DDT non può comparire nell'elenco (A04).

**Q05 – Righe presenti nella vista dei documenti**

```sql
SELECT COUNT(*) AS Righe
FROM ACM_VIEW_LABELS;
```

Zero righe con DDT aperti e colli presenti nelle tabelle (Q04): la vista va verificata
(procedura 9.3).

## B. Mappa delle chiamate

| Operazione | Front-end › back-end | Back-end | Servizio o dato |
|---|---|---|---|
| Accesso | Login Microsoft | Autenticazione con l'app registrata (`AzureAd`) | Microsoft Entra ID |
| Elenco documenti | `GET api/label/documents` | `LabelController.Documents()` › `LabelService.GetDocumentsAsync()` › `QueryViewAsync("ACM_VIEW_LABELS")` | Orbit Data API › vista `ACM_VIEW_LABELS` |
| Stampa: controllo limite | `POST api/label/print` | `LabelController.Print()`: più di 50 colli › HTTP 400 "Troppe etichette" | — |
| Stampa: stampante | — | `LabelService.PrintAsync()` › `GetUserPrinterAsync(userName)` | Orbit Data API › `ACM_USER_PRINTERS` |
| Stampa: PDF | — | `GetLabelPdfAsync(id)`, per ogni collo | Orbit Data API |
| Stampa: invio | — | `IPrintClient.SendAsync(printer, pdf)`, per ogni collo | `LabelPrintService` su `PRN01` (`http://prn01.acme.local:8085/print`) |

Table: Mappa delle chiamate {widths=16,20,40,24}

## C. Messaggi e codici di errore

| Messaggio | Dove compare | Significato | Schede |
|---|---|---|---|
| "Etichetta inviata alla stampante" | Applicazione (HTTP 200) | La richiesta è stata accettata; non garantisce la stampa (A01, A02) | S05, S06 |
| "Troppe etichette (massimo 50 per stampa)" | Applicazione (HTTP 400) | Più di 50 colli in una richiesta; non si stampa nulla | S07 |
| "No printer configured for {User}" | Log dell'applicazione, solo livello Debug | L'utente non ha una riga in `ACM_USER_PRINTERS` | S05 |

Table: Messaggi e codici di errore {widths=30,22,33,15}

I messaggi mostrati alla scadenza della sessione e quando l'accesso non riesce non sono tra le
fonti: sono indicati come da confermare nelle schede S01 e S02.

[da confermare: screenshot dei messaggi "Etichetta inviata alla stampante" e "Troppe etichette" su PC e palmare]

## D. Riferimenti al codice delle anomalie note

| ID | File | Metodo o elemento | Nota |
|---|---|---|---|
| A01 | `src/ShipLabelApp.Api/Services/LabelService.cs` | `PrintAsync()`, ramo `printer is null` | `LogDebug` e `Queued: true` senza invio |
| A01 | `src/ShipLabelApp.Api/Controllers/LabelController.cs` | `Print()` | Messaggio fisso "Etichetta inviata alla stampante" |
| A02 | Implementazione di `IPrintClient` | `SendAsync()` | Non disponibile tra le fonti (capitolo 10) |
| A03 | `src/ShipLabelApp.Api/Services/LabelService.cs` | `PrintAsync()`, ciclo sui colli | Un invio per collo, senza annullamento dei precedenti |
| A04 | `database/ACM_VIEW_LABELS.sql` | Vista `ACM_VIEW_LABELS` | `JOIN` tra `DELIVERY_NOTES` e `PARCELS`, filtro `Status = 'O'` |
| A05 | `src/ShipLabelApp.Api/Services/LabelService.cs` | `PrintAsync()`, `GetUserPrinterAsync(userName)` | Stampante cercata per nome utente |

Table: Riferimenti al codice delle anomalie note {widths=8,40,30,22}

## E. Glossario

| Termine | Significato |
|---|---|
| ShipLabelApp | Applicazione per la stampa delle etichette di spedizione del magazzino |
| DDT | Documento di trasporto registrato in OrbitERP; le sue righe di collo generano le etichette |
| Collo | Singola unità spedita di un DDT (`PARCELS`); ogni collo ha un'etichetta |
| OrbitERP | Gestionale aziendale da cui provengono DDT, colli e stampanti degli utenti |
| Orbit Data API | API di OrbitERP: unico canale con cui il back-end legge i dati |
| `svc_labels` | Utenza di servizio con cui il back-end chiama la Orbit Data API |
| `LabelPrintService` | Servizio Windows su `PRN01` che riceve i PDF e li stampa |
| `ACM_USER_PRINTERS` | Tabella utente che associa a ogni utente la sua stampante |
| `ACM_VIEW_LABELS` | Vista dei DDT aperti con i loro colli, letta per l'elenco dei documenti |
| Microsoft Entra ID | Servizio Microsoft di identità con cui gli utenti accedono con l'account aziendale |
| Client secret | Chiave dell'app registrata su Microsoft Entra ID, con una data di scadenza |
| Application Pool | Processo di IIS in cui gira il back-end |
| Avvio ritardato | Tipo di avvio di un servizio Windows che parte automaticamente poco dopo l'avvio del server |

Table: Glossario {widths=28,72}

## F. Documentazione e riferimenti

| Riferimento | Contenuto | Note |
|---|---|---|
| Sessione registrata (trascrizione) | Architettura, sessione, stampa, caso storico, limite di 50 etichette, scadenze, segnalazioni | Relatore Marco Neri [da confermare: data della sessione] |
| Chat della sessione | Grafia corretta di nomi, server, tabelle e percorsi | — |
| Codice sorgente di ShipLabelApp | `README.md`, `appsettings.json`, `LabelController.cs`, `LabelService.cs`, `ACM_VIEW_LABELS.sql` | Prevale sugli altri documenti per il comportamento dell'applicazione |
| Mail del ticket 4711 (12/03/2025) | Diagnosi e soluzione del fermo di `LabelPrintService` | Caso storico 11.1 |
| Appunti di installazione (2023) | Server, servizio di stampa, tabella delle stampanti | Superati per la durata della sessione: 60 minuti negli appunti, 30 minuti nella configurazione attuale |
| Password manager aziendale | Credenziali di `svc_labels` e client secret dell'app | Unico luogo in cui sono conservate |
| ShipLabelApp – Manuale utente | Uso dell'applicazione da parte degli operatori | Documento collegato |
| ShipLabelApp – Manuale di configurazione | Configurazione e manutenzione | Documento collegato |

Table: Documentazione e riferimenti {widths=28,42,30}
