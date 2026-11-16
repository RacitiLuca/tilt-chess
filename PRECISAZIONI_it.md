# Precisazioni alla pre-registrazione — progetto Tilt

Scritte domenica 15 novembre 2026, a fine fase 2, **prima di eseguire qualsiasi script sui dati veri**. Tutte nascono da prove su dati simulati (`tests/simula_dati.py`), in cui l'effetto vero è noto. Committate su GitHub (tradotte nella sezione 12 di `PREREGISTRATION.md`) prima di lanciare `08_tilt.py` sui dati veri: la data del commit prova che precedono i risultati.

## P1. Stimatore B: risultato inatteso al posto di sconfitta/vittoria

- **Piano**: dentro la sessione, media del residuo dopo sconfitta − dopo vittoria.
- **Ora**: regressione con effetto fisso di blocco del residuo y(t) sul residuo y(t−1), cioè sul risultato _inatteso_ della partita precedente (punteggio − atteso). Riporto τ = −pendenza: tra sconfitta e vittoria il residuo cambia di un punto, quindi τ si legge ancora «dopo sconfitta − dopo vittoria».
- **Perché**: il confronto sconfitta/vittoria dentro la sessione è distorto dal sistema di abbinamento. Se vinco, il rating sale, incontro avversari più forti e perdo più spesso _dopo_: vittorie e sconfitte non sono scambiabili nemmeno senza tilt, e i rimescolamenti non lo correggono. Il residuo tiene già conto della forza dell'avversario.
- **Prova**: su dati simulati senza tilt la versione del piano dà −1,06 pp (IC95 da −1,74 a −0,43), la nuova −0,01 pp (da −0,66 a 0,68). Altri due semi, a due lati: +0,07 e −0,05 pp (errore standard 0,21).
- La versione del piano resta nell'output, etichettata come distorta, per trasparenza.

## P2. Correzione della distorsione: divisione per (1 − b)

- **Piano**: τ corretto = τ osservato − media dei rimescolamenti (b).
- **Ora**: τ_B = (τ osservato − b) / (1 − b).
- **Perché**: la distorsione delle sequenze corte schiaccia anche un effetto vero verso zero, del fattore (1 − b). Con b tra 0,11 e 0,16 la sola sottrazione sottostima del 11–16%.
- **Prova**: catena di Markov simulata con τ vero −2,00 e −5,00 pp: sottrazione −1,67 e −4,15; con la divisione −2,00 e −4,94. Con tutta la catena di script e un tilt di 30 Elo (circa −4,0 pp): τ_B = −3,86 pp (IC95 da −4,55 a −3,17).

## P3. Rimescolamenti: dentro il blocco, ultima partita fissa

- **Piano**: rimescolo l'ordine delle partite dentro ogni sessione.
- **Ora**: rimescolo dentro ogni _blocco_, lasciando l'ultima partita del blocco all'ultimo posto.
- **Perché**: la decisione di smettere dipende dall'ultimo esito, quindi l'ultima partita non è scambiabile con le altre; le prime n−1 lo sono, se l'ordine non conta. Lo schema con tutte le partite rimescolate è riportato accanto: se le due stime differiscono, la regola di interruzione pesa.

## P4. Unità dello stimatore B: il blocco

- Blocco = sequenza ininterrotta, dentro una sessione, di partite valide, fuori torneo, della stessa classe, non sovrapposte (pausa non sotto −10 s). Un torneo, un cambio di classe o una partita non valida chiudono il blocco.
- Pesi: quelli della regressione a effetti fissi (somma dei quadrati degli scarti di x nel blocco). «Mediato» nel piano era ambiguo; in parallelo riporto la stima con peso uguale per giocatore.

## P5. Dettagli di campionamento

- Gruppo esplorazione/conferma: MD5 del nome in minuscolo, modulo 100, sotto 20 = esplorazione.
- Lato scelto per partita: parità dell'ultimo carattere del `game_id` (al posto di un hash: stesso scopo, riproducibile ovunque).
- Rivincita: attributo della partita (stesso avversario della precedente nell'ordine vero); una rivincita non fa da esito ma fa da «precedente».

## P6. Punteggio atteso e quantità di servizio

- Curva empirica per classe e colore: medie in fasce di 25 punti sulle prime partite di sessione di giocatori stabili, interpolazione lineare tra le fasce (almeno 200 partite); nelle code, logistica stimata sulle stesse fasce e raccordata senza salti; differenze limitate a ±600.
- Curva, correzione per posizione e basi dei giocatori si calcolano su tutti i giocatori (non contengono il confronto dopo sconfitta/dopo vittoria). Gli script non stampano alcun esito del gruppo di conferma prima di `08_tilt.py --gruppo conferma --codice-bloccato`.
- Base per le coppie tra due sessioni (controllo negativo): esclude _entrambe_ le sessioni, perché la precedente contiene la partita che definisce la condizione (altrimenti +1 pp circa di distorsione meccanica con 100 partite).

## P7. Definizione operativa dei test confermativi

| Ipotesi | Statistica                                                                    | Test                                                    |
| ------- | ----------------------------------------------------------------------------- | ------------------------------------------------------- |
| H1a     | τ_B, tutte le classi, partita +1                                              | permutazione; decisione con la regola di 1 pp sull'IC95 |
| H1b     | τ_B(+1) − τ_B(+2), cioè effetto della partita prima meno effetto di due prima | bootstrap sui giocatori, p normale                      |
| H1c     | τ_B bullet − τ_B rapid                                                        | bootstrap sui giocatori, p normale                      |
| H1d     | pendenza di τ_B per +200 punti di rating di riferimento                       | permutazione                                            |

- La curva di τ_A per pausa e il controllo negativo restano **descrittivi**: sui dati simulati senza tilt la differenza «pausa breve − controllo negativo» di A vale −1,1 pp, perché la forma di giornata pesa di più dentro la sessione che tra sessioni.
- Limite noto, misurato in simulazione: τ_B a distanza +2 e +3 è spinto verso zero di circa b × τ(+1) (0,3–0,4 pp con τ(+1) = −4 pp). H1b è quindi leggermente favorita; va detto nei limiti.

## P8. Fotofinish

- Stima primaria come nel piano (vincitore a 3 secondi o meno), con ogni giocatore rispetto alla propria base. Robustezza: 5 secondi; perdente a 10 secondi o meno.
- Nuovo criterio di lettura: la tabella di bilanciamento decide se il fotofinish è davvero quasi casuale (differenze standardizzate sotto 0,1 su vantaggio di rating, atteso nella partita, base, punteggio prima). Se non lo è, la stima va letta come una variante dello stimatore A, non come verifica causale.

## P9. Altro

- Soglie di errore verificate nel sorgente di Lichess (`Advice.scala`): 0,1 / 0,2 / 0,3 sulla scala da −1 a +1, cioè 5 / 10 / 15 pp di Win%. Coincidono con il piano.
- Limite di memoria di DuckDB: 4 GB di default (non 5), per lasciare margine a Windows su 8 GB.
- Numeri di rimescolamenti (200) e ricampionamenti (1000) confermati: tempi misurati sotto (vedi `HANDOFF.md`).

---

# Seconda serie di precisazioni (P10–P12)

Scritte lunedì 16 novembre 2026. A questa data sui dati veri sono stati eseguiti `05`, `06`, `09` e `07` (diagnostiche di struttura; per il solo gruppo esplorazione, residuo medio per posizione e controlli sul campione con valutazioni). **`08_tilt.py` non è mai stato eseguito sui dati veri**: nessun confronto «dopo sconfitta / dopo vittoria» è stato visto. P10 e P11 nascono da prove su dati simulati; P12 dalla lettura dell'output di `09` sul gruppo esplorazione, e lo dichiaro. Vanno committate (tradotte nella sezione 13 di `PREREGISTRATION.md`) prima di lanciare `08`.

Nelle tabelle: medie su più simulazioni indipendenti (semi diversi) ± errore standard della media, in pp; gruppo conferma dei dati simulati, 4.000 giocatori per simulazione. Un tilt di 30 Elo vale circa −3,9 pp; 15 Elo circa −1,95 pp.

## P10. Curva per distanza e test H1b: stima congiunta

- **P7**: H1b = τ_B(+1) − τ_B(+2), con una regressione separata per ogni distanza, ciascuna corretta con i rimescolamenti. Limite dichiarato: a +2 e +3 la stima è «spinta verso zero di 0,3–0,4 pp».
- **Problema**: quel limite era sbagliato in segno e in misura. Con un tilt vero solo a +1 (circa −3,9 pp) la regressione separata a +2 dà **+0,88 ± 0,13** (7 semi; seme 1: +1,09, IC95 da 0,42 a 1,78), a +3 +0,71 ± 0,19, e H1b −4,58 invece di −3,9. Senza tilt la distorsione non c'è (−0,24 ± 0,19). Sui dati veri un tilt a +1 sarebbe apparso come un falso «rimbalzo» due partite dopo, e H1b, che è confermativa, ne sarebbe uscita gonfiata.
- **Perché**: tolta la media del blocco, i prodotti tra tutte le coppie di partite di un blocco hanno somma fissa. Se le coppie a distanza 1 si somigliano più della media (tilt a +1), le altre devono somigliarsi meno della media. I rimescolamenti non lo correggono: il loro termine di paragone sono tutte le coppie del blocco, comprese quelle a distanza 1.
- **Ora**: le tre distanze si stimano insieme, e il termine di paragone non contiene nessuna di loro. Per ogni partita t che fa da esito si guarda solo il suo passato nel blocco:
  - x_d = risultato inatteso della partita di d posti prima (d = 1, 2, 3);
  - z_d = x_d − media dei risultati delle partite *lontane* (almeno 4 posti prima di t) dello stesso blocco e dello stesso tipo di selezione della partita di d posti prima (i tipi sono definiti in P11);
  - i coefficienti b_1, b_2, b_3 risolvono insieme Σ_t y_t z_d = Σ_k b_k Σ_t x_k z_d (d = 1, 2, 3); τ(+d) = −b_d.
  È la regressione di y_t sui tre risultati precedenti, in cui lo scarto dalle partite lontane fa da strumento: b_d è l'effetto del risultato di d partite prima a parità delle altre due. Non servono rimescolamenti né la correzione (1 − b), perché z usa solo partite precedenti a t (nessuna media che contenga y_t) e non pone condizioni su ciò che accade dopo t.
- **Test H1b** (sostituisce la riga di P7): τ(+1) − τ(+2) della stima congiunta; bootstrap sui giocatori, p normale, come in P7.
- **Ipotesi e costo**: dopo 3 partite l'effetto è finito; contano solo gli esiti con almeno 4 partite precedenti nel blocco (blocchi da 5 in su). Nelle simulazioni l'errore standard a +1 è 0,42 contro 0,32 dello stimatore B; con molte rivincite 0,65 contro 0,45.
- Le regressioni separate restano nell'output, etichettate come distorte.

| Scenario simulato | Semi | Congiunta +1 | +2 | +3 | H1b | Separata +2 (P7) |
|---|---|---|---|---|---|---|
| Nessun tilt | 7 | −0,06 ± 0,22 | 0,07 ± 0,16 | 0,18 ± 0,15 | −0,13 ± 0,22 | −0,24 ± 0,19 |
| Tilt 30 (−3,9 a +1) | 7 | −3,73 ± 0,15 | 0,18 ± 0,19 | 0,29 ± 0,15 | −3,92 ± 0,24 | **+0,88 ± 0,13** |
| Tilt 30 e tilt2 15 (−3,9 e −1,95) | 7 | −4,01 ± 0,28 | −1,73 ± 0,11 | 0,02 ± 0,18 | −2,28 ± 0,32 | −1,10 ± 0,09 |
| Nessun tilt, rivincite «realistiche» (vedi P11) | 4 | −0,20 ± 0,19 | 0,05 ± 0,34 | −0,12 ± 0,09 | −0,25 ± 0,20 | −0,13 ± 0,24 |
| Tilt 30, rivincite «realistiche» | 4 | −3,87 ± 0,26 | 0,10 ± 0,25 | −0,42 ± 0,25 | −3,98 ± 0,40 | **+1,08 ± 0,28** |

Seme 1, come nel controllo che ha scoperto il problema: `--tilt 30` → +1 −3,89 (IC95 da −4,66 a −3,13), +2 **+0,60 (da −0,29 a 1,41)**, +3 −0,15, H1b −4,49; `--tilt 30 --tilt2 15` → +1 −4,87 (da −5,69 a −4,00), +2 −1,69 (da −2,55 a −0,80), +3 −0,28, H1b −3,17. Su 11 scenari e 55 simulazioni la dispersione delle stime tra semi è in linea con l'errore standard del bootstrap (rapporti tra 0,88 e 1,18).

## P11. Rimescolamenti: struttura ferma, scambi dentro il tipo di selezione (sostituisce P3)

- **P3**: rimescolo l'ordine delle partite dentro il blocco, ultima partita fissa. Nel codice ogni partita si spostava insieme ai suoi attributi (è una rivincita, è il lato scelto).
- **Problema**: le rivincite non fanno da esito e arrivano a serie. Quali partite entrano nella regressione è una *struttura* del blocco, e la distorsione delle sequenze corte dipende da quella struttura (da quante partite fanno sia da precedente sia da esito). Spostando le partite con i loro attributi le rivincite si sparpagliano, la struttura dei rimescolamenti non è più quella vera e b è sottostimato. Prova, **senza alcun tilt**, con serie di rivincite (probabilità 0,75 di un'altra rivincita dopo una rivincita), codice del commit precedente: τ_B = +1,47, +1,26, +1,42, +0,89 su quattro semi (media **+1,26**; tutti e quattro gli IC95 escludono lo zero, p di permutazione 0,005). Se in più la rivincita è più probabile dopo una sconfitta (0,40 contro 0,12): media **+2,0**. Nei dati veri le rivincite sono dal 26% (rapid) al 50% (bullet) delle coppie dentro il blocco (`06_diagnostiche.txt`): lo stimatore primario avrebbe avuto una distorsione positiva, capace di nascondere un tilt o di simulare un rimbalzo.
- **Ora**:
  1. la struttura resta ferma: quali partite sono rivincite, quali fanno da esito, qual è l'ultima. Si scambiano solo i risultati (y e punteggio);
  2. un risultato può finire solo al posto di una partita dello stesso **tipo di selezione**: che cosa segue la partita (un altro avversario, una rivincita, la fine del blocco) × se la partita è essa stessa una rivincita. Smettere e chiedere la rivincita dipendono dal risultato appena ottenuto: è la stessa ragione dell'«ultima partita fissa» di P3, estesa alle rivincite. Con `--rivincite` conta solo «ultima».
  - La colonna `rim_libero` scambia i risultati tra tutte le partite del blocco, a struttura ferma: se differisce, le regole di selezione contano. Lo script stampa anche la probabilità di rivincita dopo sconfitta e dopo vittoria.
- La statistica osservata non cambia; cambiano b e il p-value di permutazione di H1a e H1d.
- **Regola per H1a**: resta su τ_B. Se la stima congiunta a +1 (P10) porta a un verdetto diverso sulla regola di 1 pp, riporto entrambe e il verdetto è «inconcludente».

| Scenario simulato | Semi | τ_B, commit precedente | τ_B, ora | `rim_libero` |
|---|---|---|---|---|
| Nessun tilt | 7 | — | 0,14 ± 0,17 | 0,11 ± 0,15 |
| Nessun tilt, serie di rivincite (0,75) | 4 | **+1,26** | 0,04 ± 0,13 | 0,01 ± 0,08 |
| Nessun tilt, serie e rivincita dopo sconfitta (0,40) | 4 | **+2,01** | −0,34 ± 0,27 | −0,11 ± 0,26 |
| Nessun tilt, rivincita dopo sconfitta (0,60), senza serie | 9 | — | 0,04 ± 0,14 | 0,00 ± 0,16 |
| Nessun tilt, «realistico»: serie, dopo sconfitta 0,40, avversario che conserva la sua forza vera | 4 | — | 0,10 ± 0,16 | 0,24 ± 0,14 |
| Tilt 30 (−3,9) | 7 | — | −3,71 ± 0,09 | −3,76 ± 0,09 |
| Tilt 30, «realistico» | 4 | — | −3,39 ± 0,13 | −3,57 ± 0,18 |
| Tilt 30 e tilt2 15 | 7 | — | −3,35 ± 0,15 | −3,43 ± 0,14 |

- **Limiti misurati** (tutti prudenti, cioè verso zero): τ_B è schiacciato del 5% nel simulatore di base e del 13% nello scenario realistico (la correzione (1 − b) è approssimata, e scambiare dentro il tipo condiziona su ciò che segue la partita-esito); del 14% se l'effetto dura due partite, perché B assume che ne duri una. La stima congiunta a +1 non ha questi limiti (−3,87 e −4,01 negli stessi scenari) ma è meno precisa.
- Limite non misurato: se smettere o chiedere la rivincita dipendono da più dell'ultimo risultato (per esempio da due sconfitte di fila), i tipi non bastano.
- Nuove opzioni di `tests/simula_dati.py` per questi collaudi: `--rivincita-sconfitta`, `--rivincita-catena`, `--avversario-stabile`, `--verita`.

## P12. Campione con valutazioni: il verdetto del controllo 2 si legge dentro il giocatore

Scritta dopo aver letto `09_controlli_eval_esplorazione.txt`; non riguarda alcun test confermativo.

- **Piano (sezione 7)**: «per giocatore: la probabilità che una partita sia stata analizzata dipende dall'esito della precedente o dal proprio risultato?», soglia 10% relativo.
- **Problema**: lo script stampava il verdetto sulle quote di tutti i giocatori insieme (tabella 2a). Per il «risultato della partita stessa» quel confronto non può dire nulla: ogni partita decisa ha un vincitore e uno sconfitto, quindi le due quote sono uguali per costruzione (8,36% e 8,38%).
- **Ora**: il verdetto usa il confronto dentro il giocatore (tabella 2b). Sul gruppo esplorazione: esito della partita precedente 13,19% contro 14,24%, cioè −7,4% (entro la soglia); risultato della partita stessa 12,59% contro 16,24%, cioè **−22,5% (oltre la soglia)**: tra i giocatori le cui partite sono analizzate solo a volte, quelle vinte lo sono più spesso di quelle perse.
- **Conseguenza**, secondo la regola del piano: gli errori «dopo una sconfitta» non si misurano sulle valutazioni di Lichess, se non sugli analizzatori sistematici (89 giocatori, 2,2% delle partite analizzate) e con il piano B (Stockfish in locale). Riguarda H3 e l'analisi esplorativa sul tipo di sconfitta, entrambe fuori da questo sprint. La domanda 1 usa il punteggio di tutte le partite e non è toccata. La domanda 2 confronta mosse della stessa partita: resta valida, ma vale per un campione in cui il «Classical» del 2017 pesa il 35,6% (contro il 23,0% tra le partite non analizzate) e le patte sono analizzate meno spesso (5,3% contro 8,4% delle partite decise): le curve vanno lette per classe.
