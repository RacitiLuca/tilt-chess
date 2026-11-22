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

---

# Terza serie di precisazioni (P13): domanda 2, pressione del tempo

Scritta martedì 17 novembre 2026, di notte. A questa data **`11_pressione.py` non è mai stato eseguito sui dati veri**, su nessuno dei due gruppi: delle mosse sono stati visti solo il riassunto generale stampato da `07_mosse.py` e i controlli di `09`. Nessun confronto tra mosse con poco e con molto tempo è stato visto. La domanda 1 invece è chiusa: i suoi quattro p-value sono noti, e lo dichiaro perché servono a Holm (P13.4). Tutto nasce da prove su mosse simulate (`tests/simula_mosse.py`), in cui l'effetto vero è noto. Va committata (tradotta in una sezione 14 di `PREREGISTRATION.md`) insieme a `11_pressione.py` **prima** di lanciarlo.

## P13.1 Campione e variabili (scelte che il piano non fissava)

- **Mosse**: `data/mosse.parquet` unite a `data/analisi` per partita e colore. Entra una mossa se ha perdita, Win% prima della mossa e tempo residuo (la prima semimossa della partita non ha un «prima») e se la partita è valida, con valutazioni, **senza incremento**, di classe bullet, blitz o rapid (soglie attuali).
- **Gruppo**: quello di chi muove. I due giocatori di una partita possono stare in gruppi diversi: ognuno porta solo le proprie mosse.
- **Tornei inclusi** (il piano non li esclude; nel berserk conta comunque l'orologio di chi muove). **Rating stabile non richiesto**: qui il rating serve solo a mettere il giocatore in una fascia. Varianti di robustezza: `--senza-tornei`, `--stabile`.
- **Errore grave** = giudizio 3 di `07_mosse.py` (perdita di almeno 15 punti di Win%). **Perdita media**: le perdite negative (rumore del motore) contano zero.
- **Tempo residuo** = `clk_prima`, in secondi interi. Fasce chiuse a sinistra: 0–2, 3–4, 5–9, 10–19, 20–39, 40–79, 80–159, 160 e oltre. Riferimento delle curve: 20–40 s, l'unica fascia centrale che esiste in tutte le classi.
- **Strati** («a parità di fase e di equilibrio»), incrociati tra loro, 6 × 7 × 7 = 294:
  - numero di mossa del giocatore: 1–10, 11–20, 21–30, 31–40, 41–50, 51 e oltre;
  - catture già avvenute nella partita: 0–3, 4–7, 8–11, 12–15, 16–19, 20–23, 24 e oltre;
  - Win% prima della mossa: sotto 15 (un errore grave è impossibile), 15–30, 30–45, 45–55, 55–70, 70–85, 85 e oltre.
- **Livello**: rating di riferimento della riga, nelle cinque fasce del piano.
- **Coppia** = partita × giocatore: è l'unità di cui si toglie il livello.

## P13.2 Modello moltiplicativo al posto di quello additivo (deviazione dal piano)

- **Piano**: «confronto dentro la stessa partita e lo stesso giocatore (sottraggo la media della coppia partita-giocatore)», cioè un modello additivo: errore grave = a[coppia] + β[fascia di tempo] + γ[strato].
- **Problema**: se le coppie hanno livelli di errore diversi e il livello *moltiplica* il rischio (chi sbaglia il doppio lo fa in ogni fase), nelle coppie che sbagliano di più il rischio sale di più, in valore assoluto, col passare delle mosse. Il modello additivo non può rappresentarlo e lo attribuisce al tempo, che in ogni partita cala col passare delle mosse. Prova, **senza alcun effetto del tempo**: +0,68 ± 0,06 pp (6 semi, differenza grezza 3 pp) nello scenario di base; con 240.000 partite, +0,34 ± 0,04 senza abbandoni e 0,00 ± 0,04 se tutte le coppie di uno stesso livello hanno lo stesso rischio. Con una struttura diversa il segno si inverte (−0,46 pp in `tests/verifica_11.py`): la direzione dell'errore non è prevedibile.
- **Ora** (primario): modello moltiplicativo, cioè una regressione di Poisson a effetti fissi:
  probabilità di errore grave = a[coppia] × B[fascia di tempo] × C[strato].
  B[k] / B[j] è il **rapporto di rischio** (RR) tra due fasce di tempo, nella stessa partita, per lo stesso giocatore e nello stesso strato. Il livello della coppia si toglie dividendo, non sottraendo. Non richiede che gli errori seguano una Poisson: basta che la media abbia questa forma. Le coppie senza errori gravi e gli strati dove l'errore è impossibile non danno informazione e pesano zero da soli.
- **Effetto in punti percentuali**, da riportare accanto al RR: tra le mosse giocate con meno di 10 secondi, tasso osservato × (1 − 1/RR), cioè quanti errori gravi in più ogni 100 mosse rispetto alle stesse mosse senza il rapporto di rischio.
- Il modello additivo resta nell'output, in pp, etichettato «modello del piano»: non entra nei verdetti.
- **Stima**: aggiustamento proporzionale iterato (30 giri), poi passi di Newton. Gli strati sono stimati sul gruppo analizzato, insieme al resto: nessuna quantità di servizio viene dall'altro gruppo.
- **Inferenza**: bootstrap a grappolo sui giocatori, 1000 ricampionamenti, seme 20170501. Si ricampionano i contributi di ogni giocatore alla stima (la somma, sulle sue mosse, di «osservato − previsto», passata per l'inversa della matrice d'informazione del modello completo): l'incertezza sugli strati è compresa, la matrice resta quella del campione intero. Tutte le celle di una classe usano gli stessi ricampionamenti. Intervalli: percentili 2,5 e 97,5. p-value: normale a due code, stima / errore standard del bootstrap (come H1b e H1c in P7).
- **Controlli d'identità** (`tests/verifica_11.py`, superati): stessi coefficienti di una regressione a forza bruta con una dummy per coppia (scarto 1e-13 per l'additivo, 1e-16 per il moltiplicativo); stesso errore standard robusto; su dati davvero moltiplicativi il RR inserito è ritrovato (log RR vero 0 → −0,004 ± 0,003; vero 0,693 → 0,701 ± 0,003) e la dispersione delle stime su 150 repliche è 0,94–1,10 volte l'errore standard calcolato.

## P13.3 Statistiche dei due test confermativi (sul blitz, come nel piano)

| Ipotesi | Statistica | Test | Previsione |
|---|---|---|---|
| H2a | log RR di «meno di 10 secondi» contro «10 secondi o più», blitz, tutti i livelli | bootstrap sui giocatori, p normale a due code | > 0 |
| H2b | pendenza del log RR sulle cinque fasce di livello: Σ c_f · log RR_f con c = (−2, −1, 0, 1, 2) / 10. È la retta ai minimi quadrati su cinque punti equidistanti e si legge «per fascia di livello» (circa 200 punti). Un modello separato per fascia, stessi ricampionamenti | bootstrap sui giocatori, p normale a due code | < 0 |

- Ogni ipotesi ha due parti; il test confermativo ne copre una, l'altra è descrittiva:
  - H2a, «con un'impennata sotto i 10 secondi»: curva a 8 fasce e indice di impennata = [log RR(5–10) − log RR(10–20)] − [log RR(10–20) − log RR(20–40)]. Le tre fasce raddoppiano: l'indice è positivo se il rischio accelera sotto i 10 secondi.
  - H2b, «i forti sbagliano meno a ogni livello di tempo»: per fascia di livello e di tempo, errori gravi osservati / attesi (atteso = tasso medio della classe nello stesso strato e nella stessa fascia di tempo); differenza tra ≥ 2000 e < 1400 con IC95.
- In parallelo, descrittiva: perdita media di Win% (rapporto moltiplicativo e differenza additiva).
- Una cella entra solo con almeno 200 errori gravi sotto i 10 secondi. Se una fascia di livello non ci arriva nel blitz, H2b non è calcolabile e conta come non rifiutata.
- Bullet e rapid, le curve per livello e tutte le altre stime: descrittive, da riportare con intervalli (e correzione FDR se si riportano p-value).

## P13.4 Holm: le soglie che spettano a H2a e H2b

- La famiglia resta di sei test al 5%. I quattro p-value della domanda 1 sono noti: H1c 0,0009; H1a 0,42; H1d 0,49; H1b 0,94.
- Holm ordina i sei p-value e li confronta con 0,05/6, 0,05/5, 0,05/4… fermandosi al primo non rifiutato. Dato che 0,0009 supera qualunque soglia e gli altri tre sono sopra 0,05, la regola per la domanda 2 diventa:
  - il **più piccolo** tra p(H2a) e p(H2b) è rifiutato se è **≤ 0,0100** (0,05/5);
  - il **più grande** è rifiutato solo se lo è il primo e se è **≤ 0,0125** (0,05/4).
- I verdetti della domanda 1 non possono cambiare: H1c resta rifiutata qualunque cosa esca, le altre tre restano non rifiutate. Lo script stampa la tabella completa.
- Come per H1c: un'uguaglianza rifiutata **nel verso opposto** alla previsione smentisce l'ipotesi.

## P13.5 Regole di lettura (fissate prima di eseguire)

Il piano non fissava una soglia di rilevanza per la domanda 2. La fisso ora, sopra l'errore del metodo misurato in simulazione (P13.6).

- **H2a** (RR nel blitz, tutti i livelli):
  - **confermata**: uguaglianza rifiutata con Holm e IC95 del RR tutto sopra **1,10**;
  - **smentita**: uguaglianza rifiutata e IC95 tutto sotto 0,90;
  - **trascurabile**: IC95 tutto tra 0,91 e 1,10;
  - **inconcludente**: negli altri casi.
  - «Impennata» si scrive solo se l'IC95 dell'indice di impennata è tutto sopra zero; altrimenti «cresce al calare del tempo», senza «impennata».
- **H2b** (pendenza nel blitz):
  - seconda parte **confermata**: uguaglianza rifiutata e pendenza negativa;
  - seconda parte **smentita**: uguaglianza rifiutata e IC95 tutto sopra **+0,04** (in simulazione la pendenza ha un errore positivo fino a +0,035);
  - **non confermata**: negli altri casi.
  - prima parte: «a ogni livello di tempo» regge se, in tutte le fasce di tempo con dati, l'IC95 di (≥ 2000) − (< 1400) sul rapporto osservati/attesi è tutto sotto zero.
  - H2b è confermata per intero solo se reggono entrambe le parti; altrimenti si dice quale.
- I verdetti valgono per il gruppo conferma. L'esplorazione serve a provare il codice; dopo l'esplorazione il codice si cambia solo per errori di esecuzione o di identità, dichiarati in una P14 prima della conferma.
- **Frasi**: «si commettono più errori gravi», non «si gioca peggio»; il RR sempre con l'equivalente in pp e con il tasso di base; mai «causa»: una posizione difficile fa consumare tempo e resta difficile (limite del piano). Il risultato vale per le partite analizzate dal motore, senza incremento, e si legge per classe (P12).

## P13.6 Collaudo su mosse simulate

`tests/collaudo_11.py`: 120.000 partite e 10.000 giocatori per simulazione, gruppo conferma dei dati simulati, blitz; media ± errore standard tra semi. Il simulatore ha livelli di errore diversi per coppia (legati al ritmo di gioco), abbandono di chi è perso, matto, caduta della bandierina. «Vero» per H2a = rapporto tra il rischio relativo inserito sotto i 10 secondi e quello inserito sopra.

| Scenario simulato | Semi | H2a vero | H2a stimato | H2b vero | H2b stimato | Additivo (pp) | Finestre (log RR) |
|---|---|---|---|---|---|---|---|
| Nessun effetto del tempo | 6 | 0 | **0,031 ± 0,006** | 0 | 0,002 ± 0,006 | **0,68 ± 0,06** | **0,118 ± 0,006** |
| Nessun effetto, difficoltà nascosta della posizione | 2 | 0 | **−0,057 ± 0,006** | 0 | 0,028 ± 0,012 | 0,29 ± 0,09 | 0,094 ± 0,013 |
| Nessun effetto, a corto di tempo non si abbandona | 2 | 0 | −0,007 ± 0,010 | 0 | 0,019 ± 0,004 | 0,44 ± 0,03 | 0,094 ± 0,021 |
| Effetto moltiplicativo, minore per i forti | 6 | 0,732 | 0,631 ± 0,004 | −0,050 | −0,015 ± 0,006 | 10,27 | 0,607 |
| Effetto moltiplicativo, uguale per tutti | 4 | 0,727 | 0,635 ± 0,006 | 0,017 | 0,035 ± 0,005 | 10,34 | 0,621 |
| Effetto moltiplicativo, difficoltà nascosta | 2 | 0,684 | 0,519 ± 0,006 | −0,019 | −0,008 ± 0,005 | 10,56 | 0,554 |
| Effetto additivo (stessi pp per tutti) | 2 | 0,330 | 0,315 ± 0,001 | 0,095 | 0,097 ± 0,000 | 4,29 | 0,365 |

- **Senza effetto** il log RR primario sta tra −0,06 e +0,03, cioè RR tra 0,94 e 1,03: da qui la soglia di 1,10.
- **Con un effetto vero** la stima è schiacciata verso zero dal 5% al 24%: prudente. La curva a 8 fasce è invece un po' più ripida del vero ai due estremi (in una simulazione da 240.000 partite, sotto 3 s: 3,07 stimato contro 2,73; oltre 160 s: 0,78 contro 0,91): i RR delle fasce estreme vanno letti come ordine di grandezza.
- **H2b**: errore tra 0,00 e +0,035, sempre nel verso contrario all'ipotesi. Se la pendenza vera è negativa la stima è attenuata (−0,015 contro −0,050): un «non confermata» può essere un falso negativo, e va detto.
- **Indice di impennata**: senza effetto −0,002 ± 0,015; con l'effetto inserito 0,187 ± 0,010 (vero 0,18).
- **Errori standard**: dispersione tra semi / errore standard del bootstrap tra 0,85 e 1,02 per H2a, tra 0,79 e 1,29 per H2b (4–6 semi).
- **Robustezza a finestre** del piano (i due giocatori nella stessa finestra di 10 semimosse; strati: equilibrio × scarto di rating): senza effetto dà +0,09 / +0,12 quando chi pensa di più sbaglia di più. Non toglie le differenze tra i due giocatori: si legge solo nel segno e non entra nei verdetti.
- **Limiti non risolti**: la difficoltà nascosta sposta la stima nei due versi (−0,06 senza effetto; −24% con effetto); il simulatore non è Lichess; gli strati sono a fasce, e dentro una fascia resta confusione residua.

## P13.7 Che cosa riportare

1. Campione: coppie, partite, mosse per classe; quota di mosse sotto i 10 secondi; coppie con mosse sia sopra sia sotto i 10 secondi.
2. H2a: RR con IC95, p, verdetto; tasso grezzo sotto e sopra i 10 secondi; equivalente in pp; indice di impennata con IC95.
3. H2b: pendenza con IC95, p, verdetto; i cinque RR per fascia di livello; tabella osservati/attesi.
4. Tabella di Holm sui sei test.
5. Curve a 8 fasce per classe e per livello (grafico: RR in scala logaritmica contro tempo residuo, una linea per fascia di livello, un riquadro per classe).
6. Accanto, sempre: stima additiva (modello del piano), robustezza a finestre, varianti `--senza-tornei` e `--stabile`, perdita media. Se una di queste ha segno opposto alla stima primaria, va scritto nella stessa frase del risultato.
7. Deviazioni dalla pre-registrazione: modello moltiplicativo al posto dell'additivo; soglia di rilevanza fissata dopo il piano; Holm calcolato con i p-value della domanda 1 già noti.

---

# P14. Dopo l'esplorazione della domanda 2: nessuna modifica al codice, una regola di presentazione

Scritta domenica 22 novembre 2026, dopo aver letto `11_pressione_esplorazione.txt` (gruppo esplorazione) e **prima di qualsiasi esecuzione sul gruppo conferma**.

- **Codice: nessuna modifica.** L'esplorazione non mostra errori di esecuzione: controllo numerico (attesi − osservati) 7e-12 nel bullet, 6e-12 nel blitz, 3e-12 nel rapid; campione plausibile (blitz la classe più grande, 99.175 coppie).
- **Problema di presentazione.** Nelle curve a 8 fasce alcune celle hanno pochissime mosse o nessuna: soprattutto la fascia «160 secondi e oltre» del bullet, perché le partite bullet senza incremento con almeno 160 secondi iniziali sono rare. Lì il modello non è identificato e la tabella stampa numeri senza significato: RR 9399 con 26 mosse e 1 errore grave (bullet, 1800–1999); RR 0,000 e un effetto additivo diverso da zero con 0 mosse; intervalli troppo stretti con 3 errori. Non riguarda i test confermativi (modello a due fasce, blitz: controllo numerico 6e-12) né le curve del blitz, dove ogni cella ha almeno 188 errori gravi nell'esplorazione.
- **Regola (fissata ora, prima della conferma).** Nelle curve a 8 fasce (RR e additivo) una cella si riporta e si disegna solo se nella sua fascia di tempo ha **almeno 30 errori gravi**, la stessa soglia della tabella osservati/attesi. Le altre restano nel CSV ma non si commentano. Una cella esclusa non cambia nessun verdetto.
- **Precisazione su Holm (P13.4).** P13.4 descriveva le soglie per il caso in cui p(H2a) e p(H2b) sono più grandi di p(H1c) = 0,0009. Il codice applica Holm nella forma standard: se un p della domanda 2 è più piccolo di 0,0009, riceve 0,0083 e H1c riceve 0,0100. Le decisioni coincidono in tutti i casi: H1c resta rifiutata, e un p della domanda 2 più piccolo di 0,0009 supera qualunque soglia.
