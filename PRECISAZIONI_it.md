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
