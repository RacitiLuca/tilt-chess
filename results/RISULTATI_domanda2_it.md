# Tilt — Risultati della domanda 2 (pressione del tempo) e approfondimenti post hoc della domanda 1

Scritto domenica 22 novembre 2026 da `11_pressione_conferma.txt`, `11_pressione_conferma_senzatornei.txt`, `11_pressione_conferma_stabile.txt`, `10_posthoc_esplorazione.txt` e `10_posthoc_conferma.txt`. Codice della domanda 2 bloccato prima della conferma (etichetta `codice-bloccato-2`, dopo P14); nessuna modifica dopo. Regole di lettura: P13.5 e P14 (domanda 2), specifica post hoc in `HANDOFF.md` (domanda 1), tutte fissate prima delle esecuzioni.

- **Unità della domanda 2**: rapporto di rischio (RR) di errore grave (perdita di almeno 15 punti di Win%), nella stessa partita, per lo stesso giocatore, nello stesso tipo di posizione (fase, materiale, equilibrio). Accanto, sempre, l'equivalente in errori gravi ogni 100 mosse.
- **Confermativo**: solo le sezioni 1–3 (H2a, H2b, Holm sui sei test). Tutto il resto è descrittivo o esplorativo. Le sezioni 7–8 (post hoc) non possono cambiare nessun verdetto.
- **Controlli**: controllo numerico del modello tra 7e-12 e 7e-11 in tutte le classi e varianti; post hoc con «IDENTITA' VERIFICATA» su entrambi i gruppi (stessi numeri di `08`, scarto 0).

## 0. In sei righe

1. **H2a confermata.** Nel blitz, con meno di 10 secondi sull'orologio si commettono il 25% di errori gravi in più: RR 1,255 (IC95 1,231; 1,280), p = 4e-113. Tra le mosse giocate sotto i 10 secondi: circa 8,2 errori gravi ogni 100 mosse invece di 6,5 (+1,66; IC95 1,52; 1,81).
2. **Nessuna «impennata» sotto i 10 secondi nel blitz**: il rischio cresce in modo regolare man mano che il tempo cala, dal tempo pieno all'ultimo secondo (indice −0,014; IC95 −0,051; 0,020).
3. **H2b confermata solo in parte.** I forti sbagliano meno della media a ogni livello di tempo (8 fasce su 8), ma il loro aumento relativo sotto i 10 secondi non è dimostrabilmente minore: pendenza −0,017 (IC95 −0,032; −0,003), p = 0,025, sopra la soglia di Holm 0,0125.
4. **Il risultato regge** senza tornei (RR 1,246) e con i soli rating stabili (RR 1,216), con il modello additivo del piano (+2,4 pp) e nel bullet e nel rapid (RR 1,27 e 1,38). Nessuna stima accanto ha segno opposto.
5. **Post hoc della domanda 1**: lo scarto tra B e la stima congiunta viene dal termine di paragone, non dal campione (PH1: −0,03). Il fotofinish nel blitz si spiega in gran parte con la forma di prima (placebo −1,09; differenza dopo − prima −0,47, IC95 −1,85; 0,88): **l'«eccezione» della domanda 1 va ridimensionata**.
6. **Nulla è causale**: una posizione difficile fa consumare tempo e resta difficile. Vale per le partite analizzate dal motore, senza incremento, maggio 2017.

## 1. Domanda 2: campione (gruppo conferma)

| Classe | Coppie partita-giocatore | Giocatori | Partite | Mosse | Mosse sotto i 10 s | Coppie con mosse sopra e sotto i 10 s |
|---|---|---|---|---|---|---|
| Bullet | 299.459 | 24.864 | 180.065 | 8.908.487 | 725.414 (8,1%) | 132.345 |
| **Blitz** | **387.057** | **57.889** | **232.875** | **12.302.516** | **233.961 (1,9%)** | **47.024** |
| Rapid | 303.277 | 50.420 | 182.270 | 9.738.775 | 48.641 (0,5%) | 12.064 |

## 2. H2a e H2b: verdetti (blitz)

| Ipotesi | Statistica | Stima | IC95 | p | Soglia di Holm | Verdetto (P13.5) |
|---|---|---|---|---|---|---|
| **H2a** | RR sotto 10 s contro 10 s o più, tutti i livelli | **1,255** (log 0,227) | 1,231; 1,280 | 4,3e-113 | 0,0083 | **Confermata**: Holm rifiuta e IC95 tutto sopra 1,10 |
| H2a, seconda parte | Indice di impennata | −0,014 | −0,051; 0,020 | — | — | **Niente «impennata»**: «cresce al calare del tempo» |
| **H2b**, seconda parte | Pendenza di log RR per fascia di livello | **−0,017** | −0,032; −0,003 | 0,025 | 0,0125 | **Non confermata**: nella direzione prevista, ma non supera Holm |
| H2b, prima parte | Forti (≥ 2000) − deboli (< 1400) sul rapporto osservati/attesi | sotto zero in 8 fasce su 8 | — | — | — | **Regge**: «i forti sbagliano meno a ogni livello di tempo» |

- **H2b nel suo insieme: confermata solo nella prima parte.** In simulazione la pendenza è attenuata (stimata −0,015 contro −0,050 vera, P13.6): un «non confermata» può essere un falso negativo. La pendenza non è nemmeno regolare: RR per fascia di livello 1,309 (< 1400), 1,308 (1400–1599), 1,243 (1600–1799), 1,174 (1800–1999), 1,269 (≥ 2000); forti − deboli in log RR −0,031 (IC95 −0,097; 0,033).
- **Tassi grezzi** (blitz): 8,19% sotto i 10 secondi, 6,12% con 10 secondi o più. Il RR confronta le mosse della stessa partita e dello stesso giocatore, a parità di posizione: per questo è più piccolo del rapporto grezzo (1,34).

## 3. Holm sui sei test confermativi

| Test | p | Soglia | Uguaglianza rifiutata | Verdetto |
|---|---|---|---|---|
| H2a | 4,3e-113 | 0,0083 | Sì | Confermata |
| H1c | 0,0009 | 0,0100 | Sì | Smentita (verso opposto al previsto) |
| H2b | 0,025 | 0,0125 | No | Non confermata (seconda parte) |
| H1a | 0,42 | 0,0167 | No | Trascurabile (regola di 1 pp) |
| H1d | 0,49 | 0,0250 | No | Non confermata |
| H1b | 0,94 | 0,0500 | No | Non confermata |

I verdetti della domanda 1 non cambiano (P13.4, P14). La soglia di H2a è 0,0083 e non 0,0100 perché il suo p è più piccolo di quello di H1c: è Holm nella forma standard, dichiarato in P14.

## 4. Accanto alla stima primaria (P13.7, punto 6)

| Stima (blitz, conferma) | Valore | IC95 | Stesso segno? |
|---|---|---|---|
| RR principale | 1,255 | 1,231; 1,280 | — |
| Variante senza tornei | 1,246 | 1,220; 1,275 | Sì (H2b −0,019, p 0,022: non confermata) |
| Variante solo rating stabili | 1,216 | 1,189; 1,241 | Sì (H2b −0,011, p 0,18: non confermata) |
| Modello additivo del piano | +2,36 pp | 2,20; 2,49 | Sì |
| Robustezza a finestre (si legge solo nel segno) | log RR 0,156 | 0,047; 0,262 | Sì |
| Perdita media di Win% | ×1,32 (log 0,281); +1,21 pp (4,30 contro 3,77) | 0,266; 0,297 | Sì |

In tutte e tre le esecuzioni H2a è «confermata», H2b «non confermata» nella seconda parte e confermata nella prima (8 fasce su 8), e l'impennata è assente.

## 5. Descrittivo: le curve (gruppo conferma)

**RR di errore grave rispetto a 20–40 secondi**, tutti i livelli. Le celle con meno di 30 errori gravi non si riportano (P14): nel bullet la fascia «160 s e oltre».

| Tempo residuo | Bullet | Blitz | Rapid |
|---|---|---|---|
| < 3 s | 1,68 | 1,53 | 1,56 |
| 3–5 s | 1,58 | 1,35 | 1,36 |
| 5–10 s | 1,43 | 1,20 | 1,19 |
| 10–20 s | 1,15 | 1,11 | 1,06 |
| 20–40 s | 1 | 1 | 1 |
| 40–80 s | 0,79 | 0,89 | 0,96 |
| 80–160 s | 0,54 | 0,79 | 0,88 |
| ≥ 160 s | — | 0,63 | 0,81 |

- Nel blitz il rischio sale in modo regolare, tra il 9% e il 13% ogni volta che il tempo residuo si dimezza (da 80–160 a 40–80 s, da 40–80 a 20–40 s, da 20–40 a 10–20 s, da 10–20 a 5–10 s). Descrittivo: le fasce estreme vanno lette come ordine di grandezza (P13.6).
- **Sotto i 10 secondi contro 10 o più**: bullet RR 1,265 (1,249; 1,282), +2,25 errori gravi ogni 100 mosse; rapid RR 1,377 (1,320; 1,444), +2,03. Impennata: presente nel bullet (0,075; IC95 0,059; 0,093), assente nel rapid (0,056; IC95 −0,033; 0,140).
- **Osservati/attesi per livello (blitz)**: i forti sbagliano meno della media della classe in ogni fascia, ma il vantaggio si riduce quando il tempo finisce. Forti − deboli: −1,01 con 160 secondi o più, −0,48 a 20–40 s, −0,15 sotto i 3 s (IC95 −0,27; −0,02). Sotto i 3 secondi un giocatore oltre 2000 sbaglia quanto la media della classe nelle stesse posizioni (O/A 1,02). Descrittivo, non è un test.
- Nel bullet (sotto i 3 s) e nel rapid (3–5 s) la frase «a ogni livello di tempo» non regge per intero: una fascia ha l'intervallo che contiene lo zero.

## 6. Esplorazione (20%) contro conferma (80%), domanda 2

| Quantità | Esplorazione | Conferma | Replicato? |
|---|---|---|---|
| H2a, RR blitz | 1,306 (1,259; 1,362) | 1,255 (1,231; 1,280) | Sì |
| Impennata blitz | 0,002 (−0,060; 0,072) | −0,014 (−0,051; 0,020) | Sì (assente) |
| H2b, pendenza | −0,003 (−0,033; 0,027) | −0,017 (−0,032; −0,003) | Compatibile; non confermata in nessuno dei due |
| H2b, prima parte | 7 fasce su 8 | 8 fasce su 8 | Sì |
| RR bullet / rapid | 1,279 / 1,411 | 1,265 / 1,377 | Sì |

## 7. Domanda 2: che cosa si può concludere e che cosa no

**Sì**

- Nella stessa partita, per lo stesso giocatore e nello stesso tipo di posizione, con meno di 10 secondi si commettono più errori gravi: +25% nel blitz (RR 1,26), +27% nel bullet, +38% nel rapid.
- Nel blitz il rischio cresce in modo regolare al calare del tempo, senza una soglia a 10 secondi.
- I forti sbagliano meno a ogni livello di tempo, ma il vantaggio si assottiglia negli ultimi secondi.

**No**

- Che il poco tempo *causi* gli errori: una posizione difficile fa pensare di più e resta difficile; gli strati la controllano solo in parte.
- Che i forti reggano meglio la pressione in termini relativi: la pendenza va nella direzione prevista, ma non supera Holm.
- Nulla sulle partite con incremento, su quelle non analizzate dal motore (P12: il campione con valutazioni è selezionato) e su mesi diversi da maggio 2017.

**Deviazioni dalla pre-registrazione** (P13, P14): modello moltiplicativo al posto dell'additivo (l'additivo resta accanto e dà lo stesso segno); soglia di rilevanza di 1,10 fissata dopo il piano, prima dei dati; Holm calcolato con i p della domanda 1 già noti; regola sulle celle con meno di 30 errori fissata dopo l'esplorazione, prima della conferma.

## 8. Approfondimenti post hoc della domanda 1 (esplorativi)

Scritti dopo aver visto la conferma della domanda 1, con regole di lettura fissate prima di eseguirli. Correzione FDR sulle celle. **Nessuno cambia un verdetto confermativo.**

### 8.1 PH1 — Perché B e la stima congiunta non coincidono?

| Esiti | Esplorazione | Conferma |
|---|---|---|
| Tutti (= `08`) | −0,22 (−0,57; 0,11) | −0,07 (−0,24; 0,09) |
| **Con almeno 4 partite prima (stesso campione della congiunta)** | −0,29 (−0,72; 0,21) | **−0,03 (−0,25; 0,19)** |
| Con 1–3 partite prima | +0,38 (−0,34; 1,12) | −0,08 (−0,45; 0,29) |

- **Lettura (regola fissata prima): −0,03 è sopra −0,35, quindi lo scarto viene dal termine di paragone, non dal campione.** Anche nei blocchi lunghi, dove la congiunta trova −0,68, la partita precedente non pesa più delle altre partite dello stesso blocco. Le partite vicine si somigliano più di quelle lontane: la dipendenza è diffusa, non concentrata sull'ultima partita.
- **La previsione scritta prima (circa −0,5, «campione») era sbagliata**: va detto.
- Esplorativo: nel bullet B con almeno 4 partite prima è positivo, +0,45 (0,11; 0,82), come B nel bullet della domanda 1 (+0,30).

### 8.2 PH3 — L'effetto finisce dopo 3 partite?

| Distanza | +1 | +2 | +3 | +4 | +5 | +6 |
|---|---|---|---|---|---|---|
| Sei distanze, conferma | −0,67 (−0,97; −0,37) | −0,84 (−1,12; −0,54) | −0,42 (−0,73; −0,14) | −0,29 (−0,58; 0,01) | −0,20 (−0,49; 0,14) | −0,28 (−0,57; 0,02) |
| Sei distanze, esplorazione | −0,97 | −0,56 | −0,73 | −0,17 | −0,12 | −0,16 |

- **Lettura: gli IC95 di +4, +5 e +6 contengono lo zero, quindi l'ipotesi «dopo 3 partite l'effetto è finito» è accettabile**, ma di poco: le stime puntuali restano tra −0,2 e −0,3.
- La stima a +1 non cambia con l'orizzonte: −0,67 con tre distanze sugli stessi esiti, −0,67 con sei. A sei distanze l'IC95 di +1 resta dentro ±1 pp (estremo −0,97): il margine del verdetto di H1a regge, ma è sottile.
- Un effetto che non cala resta invisibile anche qui (seconda serie del collaudo).

### 8.3 PH4 — Il fotofinish nel blitz, con il placebo

| Fotofinish entro 3 s, blitz | Esplorazione | Conferma |
|---|---|---|
| Partita dopo, non stratificato (= `08`) | −1,47 (−3,11; 0,30) | −1,38 (−2,26; −0,48) |
| Partita dopo, stratificato per atteso | −1,75 (−3,38; 0,03) | −1,62 (−2,48; −0,72) |
| Partita dopo, solo chi ha la partita prima | −2,05 (−3,92; 0,08) | −1,56 (−2,58; −0,59) |
| **Placebo: la partita PRIMA del fotofinish** | −0,50 (−2,33; 1,43) | **−1,09 (−2,03; −0,09)** |
| **Differenza dopo − prima** | −1,56 (−4,18; 1,16) | **−0,47 (−1,85; 0,88)** |

- **Lettura (regola fissata prima): il placebo non contiene lo zero ed è oltre 0,3 pp, quindi il confronto resta confuso.** Si riporta solo la differenza dopo − prima, come descrittiva: −0,47, non distinguibile da zero.
- In parole: chi perde la volata nel blitz va 1,6 pp peggio nella partita dopo, ma andava già 1,1 pp peggio nella partita prima. Gran parte dello scarto c'era prima del fotofinish: la volata la perde più spesso chi è già in cattiva forma. Gli strati per atteso bilanciano il rating (differenze standardizzate sotto 0,07), non la forma del momento.
- Con tutte le classi insieme, e nel bullet, il placebo è ancora più negativo (−2,70 e −3,24) della partita dopo (−1,09 e −1,00): la differenza dopo − prima è positiva (+1,61 e +2,24). Dopo il fotofinish lo scarto tra perdenti e vincitori si riduce, invece di crescere. Descrittivo; per il collaudo, «dopo − prima» non è una stima del tilt.
- Selezione: tra chi perde e chi vince una volata nel blitz, ha una partita successiva utilizzabile il 48,5% e il 49,8%.

### 8.4 PH2 — La stima congiunta per cadenza e per livello

| Cella, conferma | +1 | +2 | +3 |
|---|---|---|---|
| Bullet | −0,09 (−0,47; 0,33) | −0,62 (−1,04; −0,22) | −0,27 (−0,63; 0,09) |
| Blitz | −0,78 (−1,11; −0,47) | −0,81 (−1,15; −0,50) | −0,32 (−0,67; −0,01) |
| Rapid | **−1,80 (−2,47; −1,18)** | −0,40 (−1,04; 0,26) | −0,57 (−1,21; 0,11) |
| Rating < 1400 | −1,29 (−1,88; −0,72) | −0,58 | −0,52 |
| 1400–1599 | −0,89 (−1,37; −0,39) | −1,11 | −0,34 |
| 1600–1799 | −0,43 (−0,87; −0,01) | −0,43 | −0,20 |
| 1800–1999 | −0,23 (−0,74; 0,25) | −0,47 | −0,14 |
| ≥ 2000 | −0,58 (−1,31; 0,15) | −1,02 | −0,82 |

- **Lettura (regola fissata prima): bullet − rapid a +1 = +1,71 (IC95 1,00; 2,47), stesso segno di B (+0,85). L'ordine rapid > blitz > bullet non dipende dallo stimatore.** Il confronto tra cadenze resta «per partita», non alla pari.
- **Segnale esplorativo da riprendere, non da annunciare:** nel rapid la congiunta a +1 vale −1,80, oltre 1 pp, e in esplorazione −1,34 (−2,62; −0,04). Tre motivi di cautela:
  1. è post hoc e per cella;
  2. usa solo i blocchi di almeno 5 partite di rapid di fila, una minoranza selezionata (la mediana è 2);
  3. B nel rapid vale −0,55, e in esplorazione il calo a +2 non c'era (−1,60).

  È un'ipotesi da pre-registrare su un altro mese.
- Per livello, la persistenza a +1 è più marcata sotto 1600 (−1,29 e −0,89; in esplorazione −1,97 e −1,28) e si riduce salendo. Con B la pendenza per livello era piatta (H1d non confermata): anche qui due stimatori rispondono a domande diverse.

### 8.5 PH6 — Pausa prima della partita (descrittivo)

Congiunta a +1: −0,79 con pausa fino a 60 secondi, −0,52 oltre; differenza −0,28 (IC95 −0,68; 0,19). Nessuna differenza dimostrabile; la pausa la sceglie il giocatore.

## 9. Che cosa cambia nelle formulazioni della domanda 1

| Dove | Prima | Dopo |
|---|---|---|
| Eccezione del fotofinish | «Nel blitz, dopo una sconfitta per tempo al fotofinish, la partita successiva va 1,4 pp peggio, in entrambi i campioni» | «Nel blitz chi perde la volata va 1,4–1,6 pp peggio nella partita dopo, ma andava già 1,1 pp peggio in quella prima. La differenza (−0,5; IC95 −1,9; +0,9) non si distingue da zero: la volata la perde più spesso chi è già in cattiva forma» |
| Scarto tra B e congiunta | «Lo spiegherà PH1» | «Anche nei blocchi lunghi la partita precedente non pesa più delle altre (B −0,03); le partite vicine si somigliano più delle lontane. La mia previsione (−0,5) era sbagliata» |
| Margine della congiunta | «Assume che l'effetto finisca dopo 3 partite» | «Con sei distanze +1 resta −0,67 (IC95 −0,97; −0,37); +4, +5, +6 sono compatibili con zero» |
| H1c | «Smentita» | Invariato, e confermato con un secondo stimatore (congiunta bullet − rapid +1,71) |
| Nuovo | — | «Post hoc: nel rapid la congiunta a +1 è −1,8 pp; da pre-registrare su un altro mese» |

**Frasi pronte in inglese** (README e articolo):

- "Time pressure, unlike tilt, is large and clear. In blitz, with under 10 seconds on the clock, players make 25% more blunders than in the same game and the same kind of position with more time (risk ratio 1.26, 95% CI 1.23 to 1.28): about 8.2 blunders per 100 moves instead of 6.5."
- "There is no cliff at 10 seconds: the risk rises steadily as the clock runs down."
- "Stronger players blunder less at every level of remaining time, but their edge shrinks in the last seconds. I could not show that their relative increase is smaller."
- "The photo-finish 'exception' did not survive its placebo test: blitz players who lose a time scramble do 1.6 points worse in the next game, but they were already doing 1.1 points worse in the game before."

## 10. Specifiche dei grafici della domanda 2 (numeri in `11_stime_conferma*.csv`)

1. **Il grafico della domanda 2** (P13.7, punto 5): RR in scala logaritmica contro tempo residuo (8 fasce, riferimento 20–40 s), una linea per fascia di livello, un riquadro per classe. Celle con meno di 30 errori gravi escluse (P14). Messaggio: il rischio sale in modo regolare al calare del tempo, in tutte le classi.
2. **Errori gravi ogni 100 mosse sotto e sopra i 10 secondi** (blitz), con l'equivalente senza il RR: 6,5 → 8,2. Messaggio: quanto costa, in pratica, finire il tempo.
3. **Osservati/attesi per fascia di tempo**, linea dei forti (≥ 2000) e dei deboli (< 1400), blitz. Messaggio: il vantaggio dei forti si assottiglia negli ultimi secondi.
4. **Robustezza H2a**: RR principale, senza tornei, rating stabili, bullet, rapid, con la fascia 1,10. Messaggio: sempre sopra la soglia.
5. **Post hoc, fotofinish con placebo** (blitz): partita prima, partita dopo, differenza. Messaggio: lo scarto c'era già prima.
