# Tilt — Piano di ricerca e pre-registrazione (v1)

Scritto il 15 novembre 2026, prima di qualsiasi analisi sugli esiti: finora sono stati guardati solo conteggi descrittivi (`riassunto_dati.txt`, `statistiche_campione.txt`). Committato su GitHub prima della fase 3: la data del commit prova che le ipotesi precedono i risultati.

## 1. Ipotesi

| ID  | Ipotesi e direzione prevista                                                                                                                                     | Ruolo                       |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------- |
| H1a | Nella stessa sessione, contro un avversario diverso, il punteggio rispetto all'atteso è più basso subito dopo una sconfitta che subito dopo una vittoria (τ < 0) | Confermativa, primaria      |
| H1b | L'effetto cala con la pausa tra le due partite e con la distanza (partita +1, +2, +3); dopo una pausa oltre 30 minuti è circa zero                               | Confermativa                |
| H1c | L'effetto è più forte nelle cadenze veloci (bullet > blitz > rapid)                                                                                              | Confermativa                |
| H1d | L'effetto è più debole al crescere del rating                                                                                                                    | Confermativa                |
| H1e | Dopo una sconfitta si ricomincia prima, si muove più in fretta nelle prime 10 mosse e si perde più spesso per tempo                                              | Secondaria (meccanismo)     |
| H2a | La probabilità di errore grave per mossa cresce al calare del tempo residuo, con un'impennata sotto i 10 secondi                                                 | Confermativa                |
| H2b | I forti sbagliano meno a ogni livello di tempo, e anche il loro aumento relativo sotto i 10 secondi è minore                                                     | Confermativa                |
| H3  | Sotto tilt e pressione i forti commettono in proporzione più imprecisioni e meno errori gravi                                                                    | Rimandata (solo specifica)  |
| H4  | Momentum: dopo una vittoria non c'è guadagno oltre l'atteso                                                                                                      | Esplorativa, se resta tempo |

**Soglia di rilevanza pratica: 1 punto percentuale (pp) di punteggio**, circa 7 punti Elo a parità di forza, cioè più o meno quanto sposta una singola partita. Con milioni di partite quasi tutto risulta "significativo", quindi decide l'ampiezza:

- tilt rilevante: stima a −1 pp o oltre e intervallo di confidenza al 95% tutto sotto zero;
- tilt trascurabile: intervallo tutto compreso tra −1 e +1 pp;
- inconcludente: negli altri casi.

## 2. Definizioni operative

| Termine               | Definizione                                                                                                                                                                                           | Motivo                                                                                                                        |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| Partita valida        | Risultato 1-0, 0-1 o ½-½, rating e variazioni di rating presenti, non Correspondence                                                                                                                  | Servono un esito e un atteso                                                                                                  |
| Classe di cadenza     | Soglie attuali di Lichess sulla durata stimata (tempo iniziale + 40 × incremento): ultrabullet < 30 s, bullet < 180, blitz < 480, rapid < 1500, classical oltre                                       | Nel 2017 "Rapid" non esisteva: 600+0 era etichettata Classical                                                                |
| Fine stimata          | `start_utc` + tempo consumato dai due orologi (primo orologio − ultimo + incrementi; per chi perde per tempo anche il residuo)                                                                        | L'orario di fine manca. È una stima per difetto: esclude ritardi di rete e attesa iniziale                                    |
| Pausa                 | Inizio della partita seguente − fine stimata della precedente                                                                                                                                         | Sotto −10 s le partite si sovrappongono: coppia esclusa                                                                       |
| Sessione              | Partite dello stesso giocatore (tutte le cadenze in tempo reale, tornei inclusi) ordinate per `start_utc, game_id`, con pause fino a 30 minuti                                                        | Soglia fissata ora; robustezza a 10 e 60                                                                                      |
| Partita successiva    | La seguente nella stessa sessione. Coppia primaria: entrambe fuori torneo, stessa classe, avversario diverso                                                                                          | Nella rivincita chi ti ha appena battuto è in media più forte del suo rating: perderesti di più anche senza tilt              |
| Rating di riferimento | Rating del giocatore prima della sua prima partita in quella categoria di rating (quelle del 2017) nella sessione; per le coppie a cavallo di due sessioni, quello a inizio della sessione precedente | Non è toccato dall'esito che studio. Il rating corrente scende dopo la sconfitta e sposterebbe l'atteso                       |
| Punteggio atteso E    | Tabella empirica: punteggio medio per classe, colore e fascia di 25 punti di differenza (riferimento − avversario), stimata sulle prime partite di sessione                                           | Lichess usa Glicko-2: la formula Elo teorica non è calibrata su questi dati                                                   |
| Residuo               | Punteggio (1, ½, 0) − E                                                                                                                                                                               | Esito primario: esiste per tutte le partite, non solo per l'8% con valutazioni                                                |
| Perdita di una mossa  | Calo della probabilità di vittoria di chi muove tra la valutazione prima e dopo: Win% = 50 + 50 × (2 / (1 + e^(−0,00368 × cp)) − 1), con cp limitati a ±1000 e matto = ±1000                          | Scala di Lichess; pesa poco gli errori in posizioni già decise                                                                |
| Errore                | Imprecisione da 5 pp di perdita, errore da 10, errore grave da 15                                                                                                                                     | Soglie attuali di Lichess (da ricontrollare nel sorgente). I simboli ?!, ?, ?? del PGN 2017 seguono regole diverse: li ignoro |
| Tempo residuo         | Orologio di chi muove dopo la sua mossa precedente                                                                                                                                                    | È il tempo disponibile quando inizia a pensare                                                                                |
| Rating stabile        | Almeno 50 partite valide nella classe nel mese e mediana della variazione assoluta di rating fino a 15 punti                                                                                          | I rating nuovi si muovono di 25 punti e più a partita: l'atteso non è affidabile                                              |
| Fasce di livello      | < 1400, 1400–1599, 1600–1799, 1800–1999, ≥ 2000 (rating di riferimento)                                                                                                                               | 10°, 50° e 90° percentile a circa 1283, 1646, 2003                                                                            |

## 3. Dati e campione

- Maggio 2017: 11.693.919 partite, 228.525 giocatori. Le partite con valutazioni sono l'8,2% (957.369), non il 6%.
- **Nuova passata in streaming** sul `.pgn.zst` (stima: 15–30 minuti): per ogni partita e colore, primo orologio, orologio dopo la decima mossa, ultimo orologio, numero di mosse. `partite.parquet` non ha gli orologi delle partite senza valutazioni, e servono per la fine stimata, il ritmo di gioco e i finali al fotofinish. Il primo orologio rivela anche il berserk (tempo dimezzato nei tornei).
- Le sessioni si costruiscono con tutte le partite; gli esiti primari sono partite fuori torneo, bullet, blitz o rapid, di giocatori con rating stabile.
- Ogni partita conta come esito per un solo giocatore, scelto con un hash del `game_id`: le due righe della stessa partita hanno residui opposti e tenerle entrambe falserebbe gli errori standard.
- **Esplorazione e conferma**: il 20% dei giocatori (hash del nome) serve a sviluppare e correggere il codice; l'80% restante si analizza una volta sola, a codice bloccato.
- DuckDB con `memory_limit` a 5 GB e cartella temporanea su disco; sempre `ORDER BY start_utc, game_id`.

## 4. Metodo, domanda 1 (tilt)

τ = media del residuo dopo una sconfitta − media dopo una vittoria (le patte a parte).

1. **Stimatore A, tra sessioni.** Al residuo sottraggo la media dei residui dello stesso giocatore in tutte le _altre_ sessioni: è il confronto del giocatore con se stesso. Contiene ancora la "giornata storta" (forma bassa che causa sia la sconfitta sia la partita dopo), quindi è un limite superiore del tilt.
2. **Stimatore B, dentro la sessione (primario).** τ calcolato dentro ogni sessione e poi mediato: elimina la giornata storta. In sequenze corte però questa differenza è distorta di circa +1/(n−1) anche con partite indipendenti (Miller e Sanjurjo, 2018): 11 pp con 10 partite, 1 pp con 100. Correzione: rimescolo 200 volte l'ordine delle partite dentro ogni sessione, ricalcolo τ e sottraggo la media; la distribuzione rimescolata dà anche il p-value.
3. **Stanchezza.** Prima del confronto sottraggo il residuo medio per posizione nella sessione (1, 2, 3, 4–5, 6–10, 11–20, 21+) e classe. La curva è anche un risultato a sé.
4. **Decadimento (H1b).** τ_A per fascia di pausa (fino a 15 s, 15–60 s, 1–5 min, 5–30 min, oltre 30 min, oltre 6 h) e per distanza +1, +2, +3. La fascia oltre 30 minuti è il controllo negativo: un effetto uguale anche lì indicherebbe forma o rating, non tilt. La pausa la sceglie il giocatore: questa curva è descrittiva.
5. **Verifica causale 1, finali al fotofinish.** Partite senza incremento perse per tempo con il vincitore a 3 secondi o meno: l'esito è quasi un lancio di moneta. Confronto la partita successiva di perdente e vincitore della stessa partita (stessa durata, ora e fatica), dopo aver verificato che i due gruppi fossero simili prima.
6. **Verifica causale 2, il colore come strumento.** Il colore è assegnato quasi a caso e il Bianco vince più spesso (49,6% contro 46,5%): aver avuto il Nero nella partita precedente rende più probabile averla persa, senza dipendere dalla forma. τ_IV = differenza di residuo tra chi aveva il Nero e chi il Bianco, divisa per la differenza nella quota di sconfitte, a parità di colore attuale; solo giocatori con quota di Bianco tra 45% e 55%. Con un solo mese la precisione attesa è circa ±3 pp: può escludere solo effetti grandi, diventa utile aggiungendo mesi.
7. **Selezione.** (a) Probabilità di chiudere la sessione dopo sconfitta e dopo vittoria. (b) τ nei tornei arena, dove l'abbinamento seguente è automatico e la scelta di continuare pesa meno. (c) Partite dopo sconfitta ripesate con l'inverso della probabilità stimata di continuare. In ogni caso τ misura l'effetto sulle partite davvero giocate dopo una sconfitta, cioè la risposta a "conviene continuare?"; non dice come avrebbe giocato chi ha smesso.
8. **Inferenza.** Bootstrap a grappolo sui giocatori (1000 ricampionamenti delle somme per giocatore), intervalli al 95%. Stima pesata per partita e, in parallelo, per giocatore, per escludere che pochi giocatori molto attivi decidano il risultato.
9. **Moderatori.** τ per classe (H1c) e interazione lineare con il rating per 200 punti (H1d).

Esiti secondari (H1e), stessi stimatori: pausa prima della partita seguente, secondi per mossa nelle mosse 2–10 rispetto all'abitudine del giocatore in quel controllo di tempo, sconfitta per tempo.

## 5. Metodo, domanda 2 (pressione del tempo)

- Unità: la mossa, nelle partite con valutazioni e senza incremento. Esito: errore grave; in parallelo la perdita media.
- Esposizione: tempo residuo a fasce (< 3, 3–5, 5–10, 10–20, 20–40, 40–80, 80–160, > 160 s).
- Confronto dentro la stessa partita e lo stesso giocatore (sottraggo la media della coppia partita-giocatore), a parità di fase (numero di mossa a fasce, catture già avvenute come misura del materiale) e di equilibrio (Win% prima della mossa a fasce): chi è già perso non può più sbagliare molto.
- Curve separate per classe e fascia di livello; test confermativi sul blitz (nel bullet 60+0 "più di 60 secondi" non esiste).
- Robustezza: confronto tra i due giocatori nella stessa finestra di 10 semimosse (stessa complessità, orologi diversi).
- Limite noto: una posizione difficile fa consumare tempo e resta difficile; fase ed equilibrio la controllano solo in parte.

## 6. Domanda 3 e momentum (solo specifica)

- H3: quote di imprecisioni, errori ed errori gravi per fascia di livello, in tre condizioni: normale, dopo sconfitta, sotto i 10 secondi.
- H4: stimatori A e B con lo stato "serie in corso" (1, 2, 3+ vittorie o sconfitte consecutive nella sessione).

## 7. Il campione con valutazioni è distorto?

Tre controlli prima di usarlo:

1. Differenze standardizzate tra partite con e senza valutazioni (rating, lunghezza, classe, terminazione, risultato, torneo).
2. Per giocatore: la probabilità che una partita sia stata analizzata dipende dall'esito della precedente o dal proprio risultato? È il controllo che conta per il tilt.
3. Quota di partite di "analizzatori sistematici" (almeno 30 partite, almeno 80% analizzate).

Regola: se nel controllo 2 le probabilità differiscono di oltre il 10% relativo, gli errori dopo sconfitta si misurano solo su (i) analizzatori sistematici e (ii) piano B: circa 6.000 partite estratte a caso a coppie (dopo sconfitta e dopo vittoria, stesso giocatore), analizzate in locale con Stockfish a nodi fissi (100.000 per posizione, stima 3–4 ore su 4 thread). La domanda 2 confronta mosse della stessa partita: lì la selezione limita solo la generalizzabilità.

## 8. Test multipli e robustezza

- Sei test confermativi (H1a, H1b, H1c, H1d, H2a, H2b) con correzione di Holm al 5%. Tutto il resto è esplorativo, riportato con intervalli e correzione FDR di Benjamini-Hochberg.
- Robustezza già decisa: soglia di sessione a 10 e 60 minuti; rivincite incluse; rating corrente al posto di quello di riferimento; entrambi i lati della partita; partite sotto 10 semimosse e Abandoned escluse; soglie di rating stabile più larghe e più strette; fotofinish a 5 secondi.
- Esplorativo: tipo di sconfitta (per tempo o sulla scacchiera, attesa o a sorpresa, vittoria buttata nel campione con valutazioni).

## 9. Rischi

| Rischio                                | Contromisura                                                                                                                  |
| -------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| Fine stimata sbagliata                 | Pause negative attese sotto l'1%; l'istogramma del logaritmo della pausa deve avere due gobbe con la valle vicino a 30 minuti |
| Il file `.pgn.zst` non è più sul disco | Riscaricarlo (pochi GB) prima della fase 2                                                                                    |
| 8 GB di RAM                            | Solo aggregati SQL e numpy sulle somme per giocatore; nessuna libreria di regressione pesante                                 |
| Maggio 2017 non rappresenta oggi       | Codice parametrico sul mese; replica su un mese recente dopo la scadenza                                                      |
| Rating instabili, account doppi, bari  | Filtro di stabilità; il resto è rumore non legato all'esito precedente                                                        |
| Tempo e quota                          | Ordine di taglio: H4, H3, verifica causale 2, domanda 2                                                                       |

## 10. Calendario (scadenza: martedì 17 alle 08:59)

- Domenica: OK al piano, commit, codice della fase 2, nuova passata sul file, sessioni sul 20% di esplorazione.
- Lunedì mattina: domanda 1 sull'80% di conferma, con robustezza.
- Lunedì pomeriggio e sera: revisione critica, kit colloquio, domanda 2 se resta quota.
