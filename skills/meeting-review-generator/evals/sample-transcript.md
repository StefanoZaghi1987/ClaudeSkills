# Trascrizione riunione — Progetto Portale Ordini

Data: 26 agosto 2026, ore 9:30–10:45
Presenti: Luca Bianchi (responsabile progetto), Giulia Romano (IT), Marco Ferrari (qualità), Elena Ricci (acquisti)

---

**Luca Bianchi**: Buongiorno a tutti. Oggi dobbiamo chiudere tre punti: lo stato del nuovo portale ordini, l'aggiornamento dei manuali di procedura e un paio di comunicazioni organizzative. Partiamo dal portale.

**Giulia Romano**: Abbiamo completato l'ambiente di test. Il portale gira sulla versione 2.4 della piattaforma e abbiamo importato i dati degli ultimi due anni. Sui carichi pesanti — oltre 5.000 righe d'ordine — le pagine di conferma impiegano 8 secondi, troppo per il go-live. Ho misurato tre scenari: la query di riepilogo è la causa, non il frontend.

**Marco Ferrari**: Otto secondi viola il requisito di prestazione che abbiamo firmato con la direzione: massimo 3 secondi per ogni schermata. Non possiamo accettare deroghe su questo punto.

**Luca Bianchi**: Concordo. Giulia, che opzioni abbiamo?

**Giulia Romano**: Due: riscrivere la query con gli indici sugli ordini aperti, oppure introdurre una cache lato server. La riscrittura richiede circa due settimane di lavoro; la cache una settimana, ma va svuotata a ogni import notturno.

**Luca Bianchi**: Direi di procedere con la riscrittura: è la soluzione stabile e non ci espone a incongruenze tra i dati. Giulia, puoi consegnare la versione ottimizzata entro il 12 settembre?

**Giulia Romano**: Sì, entro il 12 settembre la query è riscritta e rilanciata in test.

**Marco Ferrari**: Io nel frattempo preparo il piano di collaudo prestazioni con i casi oltre 5.000 righe, così il giorno dopo il rilascio in test eseguiamo subito le verifiche. Consegno il piano entro il 5 settembre.

**Luca Bianchi**: Approvato. Restano però da definire le utenze per i clienti esterni: accesso con credenziali aziendali o tramite area riservata del sito? Non ne abbiamo ancora parlato con il reparto commerciale.

**Elena Ricci**: Per gli acquisti non ho vincoli, ma chiedo che il portale vada in produzione dopo l'1 novembre, quando chiudiamo il rinnovo dei contratti fornitura. Prima di quella data rischiamo di sovrapporre i due ordini di lavoro.

**Luca Bianchi**: Va bene, annoto la dipendenza: il go-live dipende dalla chiusura dei collaudi e dal rinnovo contratti di novembre. Le utenze esterne le portiamo all'ordine del giorno della prossima riunione.

**Luca Bianchi**: Secondo punto: i manuali di procedura. Marco, a che punto siamo?

**Marco Ferrari**: I manuali di magazzino e fatturazione sono stati aggiornati a luglio, ma non riflettono ancora le tre nuove procedure introdotte a giugno. Serve una revisione completa entro l'anno, altrimenti saltiamo il controllo di conformità interno.

**Luca Bianchi**: Allora confermiamo la revisione entro dicembre. Marco, ti occupi tu del coordinamento con i responsabili di area?

**Marco Ferrari**: Sì, ricevuto.

**Luca Bianchi**: Ultimo punto, solo informativo: l'ufficio resterà chiuso venerdì 18 settembre per la manutenzione degli impianti di climatizzazione. Vi arriverà la circolare; nessuna azione richiesta.

**Luca Bianchi**: Chiudiamo qui. Prossima riunione: 9 settembre, stessa ora.
