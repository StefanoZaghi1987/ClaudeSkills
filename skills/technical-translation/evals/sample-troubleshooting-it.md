# Specifiche tecniche e risoluzione guasti — Linea di riempimento RF-10

## 1. Descrizione generale

La linea di riempimento RF-10 è controllata da un controllore logico programmabile (PLC) che gestisce le fasi di trasporto, riempimento e tappatura. Il PLC comunica con il pannello operatore tramite bus di campo.

## 2. Specifiche funzionali

- Precisione di riempimento: ± 0,5 ml
- Cadenza nominale: 6.000 bottiglie/ora
- Tensione di alimentazione: 380-420 V
- Livello di rumorosità: ≤ 75 dB(A)

## 3. Risoluzione guasti

### Guasto 1: La linea si arresta con allarme E-04

**Causa probabile:** sovrappressione nell'impianto pneumatico (rif. paragrafo 4.2).

**Rimedio:**
1. Verificare la lettura del manometro a monte del riduttore di pressione
2. Regolare la pressione a 6,5 bar
3. Ripristinare l'allarme dal pannello operatore
4. Se il guasto persiste, sostituire l'elettrovalvola di scarico EV-12

### Guasto 2: Riempimento incompleto delle bottiglie

**Causa probabile:** otturazione parziale dell'ugello di riempimento.

**Rimedio:**
1. Arrestare la linea e chiudere la valvola di alimentazione del prodotto
2. Rimuovere l'ugello e lavarlo con soluzione sgrassante
3. Rimontare l'ugello serrando a mano
4. Eseguire un ciclo di prova e controllare la precisione di riempimento

**AVVERTENZA: Superfici calde. Il gruppo di tappatura raggiunge temperature fino a 120 °C durante il funzionamento. Attendere il raffreddamento prima di intervenire.**

### Guasto 3: Il PLC non comunica con il pannello operatore

**Causa probabile:** interruzione del bus di campo o indirizzo slave duplicato.

**Rimedio:**
1. Controllare i connettori del bus di campo
2. Verificare che ogni stazione abbia un indirizzo univoco
3. Riavviare il PLC dall'interruttore di servizio

## 4. Manutenzione programmata

### 4.1 Settimanale

- Controllo del livello dell'olio del riduttore di pressione
- Pulizia dei sensori fotoelettrici

### 4.2 Trimestrale

- Verifica della taratura del riduttore di pressione (valore nominale 6,5 bar)
- Sostituzione dei filtri dell'aria compressa

Le operazioni di manutenzione devono essere eseguite solo da personale qualificato, con la linea arrestata e l'alimentazione elettrica sconnessa.
