# Tilt — Risultati della conferma, domanda 1

Scritto lunedì 16 novembre 2026 da `08_tilt_conferma.txt` (intero) e `08_varianti_conferma.txt` (prime tre tabelle di ogni variante). Codice bloccato prima della conferma (etichetta `codice-bloccato`); nessuna modifica dopo.

- **Dati**: Lichess, partite rated di maggio 2017; gruppo conferma = 80% dei giocatori. 63.695 giocatori con rating stabile, 11.829.759 righe giocatore-partita in 2.168.488 blocchi; 3.109.451 coppie «partita precedente → partita» utilizzabili in 662.938 blocchi. 200 rimescolamenti, 1000 ricampionamenti sui giocatori, seme 20170501.
- **Unità**: punti percentuali di punteggio (pp). τ = residuo dopo una sconfitta − dopo una vittoria; τ < 0 = dopo una sconfitta si gioca peggio. 1 pp ≈ 7 punti Elo.
- **Regola di rilevanza (pre-registrata)**: rilevante = stima ≤ −1 pp e IC95 tutto sotto zero; trascurabile = IC95 tutto tra −1 e +1; altrimenti inconcludente.
- **Confermativo**: solo le sezioni 1 e 2. Tutto il resto è descrittivo o esplorativo.

## 0. In cinque righe

1. **Un tilt sulla partita successiva di almeno 1 pp è escluso.** τ_B = −0,07 pp (IC95 −0,24; 0,09); stima congiunta a +1 = −0,68 (−0,90; −0,45). Entrambi gli intervalli stanno dentro ±1 pp, in tutte le nove varianti: verdetto «trascurabile».
2. **Il confronto ingenuo (−2,77 pp) è quasi tutto altro**: forma della giornata, differenze tra giocatori, abbinamento. Tra il 75% (congiunta) e il 97% (B) del confronto ingenuo non è effetto della partita precedente.
3. **Resta una persistenza locale piccola e non attribuibile**: −0,68, −0,69, −0,34 pp a distanza +1, +2, +3. È piatta tra +1 e +2 (H1b = 0,01): non ha la forma di un tilt di una partita. Tilt che dura più partite, deriva della forma o tendenza individuale: questo disegno non li separa.
4. **H1c è smentita**: la dipendenza è più forte nel rapid che nel bullet (+0,85 pp, p = 0,0009), al contrario del previsto. H1b e H1d non sono confermate.
5. **Non si può concludere** nulla su chi smette dopo una sconfitta (25,4% contro 20,6%), sulla qualità delle mosse, sulle rivincite, sui singoli giocatori, su mesi diversi da maggio 2017; e nessuna stima è causale (il fotofinish non supera il controllo di bilanciamento).

## 1. H1a: verdetto

| Stimatore | Stima (pp) | IC95 | Errore std | p | Regola di 1 pp |
|---|---|---|---|---|---|
| τ_B, tutte le classi, partita +1 (primario) | −0,07 | −0,24; 0,09 | 0,08 | 0,423 (permutazione) | **Trascurabile** |
| Stima congiunta a +1 (controllo, P10–P11) | −0,68 | −0,90; −0,45 | 0,12 | < 0,0001 (normale) | **Trascurabile** |

- I due verdetti coincidono: **H1a = tilt trascurabile**, non «inconcludente».
- Le due stime però non coincidono: lo scarto (0,61 pp) è già nell'esplorazione (0,72) ed è molto oltre l'errore. B confronta la partita precedente con la media del blocco; la congiunta confronta le tre precedenti con le partite lontane (almeno 4 prima) e usa solo blocchi da 5 partite in su. B vicino a zero con una congiunta piatta a +1 e +2 dice che la partita precedente non pesa più delle altre partite vicine.
- Margine della congiunta: l'estremo inferiore (−0,90; −0,96 con il rating stabile «largo») è vicino a −1, e la stima è schiacciata verso zero se l'effetto dura oltre 3 partite (a +3 vale ancora −0,34). Il verdetto regge sulla regola, con poco margine.
- In Elo: τ_B ≈ 0,5 punti; congiunta ≈ 5 punti (al più 6).

## 2. I quattro test confermativi di H1 (Holm prudente)

Famiglia di sei test (H2a e H2b non ancora stimate): soglie 0,05/6, /5, /4, /3 in ordine di p-value. Tutti i p-value sono a due code.

| Ordine | Ipotesi | Statistica | Stima (pp) | IC95 | p | Soglia | Decisione |
|---|---|---|---|---|---|---|---|
| 1 | H1c | τ_B bullet − τ_B rapid | +0,85 | 0,37; 1,35 | 0,0009 | 0,0083 | Uguaglianza rifiutata, **segno opposto al previsto: H1c smentita** |
| 2 | H1a | τ_B, tutte, +1 | −0,07 | −0,24; 0,09 | 0,423 | 0,0100 | Non rifiutata; regola di 1 pp: trascurabile |
| 3 | H1d | pendenza di τ_B per +200 punti di rating | +0,05 | −0,07; 0,17 | 0,488 | 0,0125 | Non rifiutata |
| 4 | H1b | congiunta (+1) − (+2) | +0,01 | −0,28; 0,31 | 0,937 | 0,0167 | Non rifiutata |

- H1c prevedeva bullet più negativo del rapid (differenza < 0). Osservato: bullet +0,30, blitz −0,16, rapid −0,55. Lo stimatore A dà lo stesso ordine (−1,96; −2,45; −3,21; bullet − rapid +1,25).
- H1b: nessun calo tra +1 e +2; a +3 l'effetto è la metà. La parte «dopo una pausa oltre 30 minuti è circa zero» è descrittiva (sezione 5.4).
- Il p-value di permutazione ha risoluzione 1/201 ≈ 0,005 (200 rimescolamenti).

## 3. Esplorazione (20%) contro conferma (80%)

| Quantità | Esplorazione | Conferma | Replicato? |
|---|---|---|---|
| τ_B | −0,22 (−0,57; 0,11) | −0,07 (−0,24; 0,09) | Sì |
| τ_B, rimescolamento libero | −0,30 | −0,17 | Sì |
| Distorsione b | 13,38 | 13,25 | Sì |
| τ_B, peso uguale per giocatore | −0,60 (−1,06; −0,14) | −0,12 (−0,37; 0,10) | No: segnale sparito |
| Congiunta +1 | −0,94 (−1,38; −0,45) | −0,68 (−0,90; −0,45) | Sì |
| Congiunta +2 | −0,75 (−1,22; −0,28) | −0,69 (−0,91; −0,45) | Sì |
| Congiunta +3 | −0,43 (−0,90; 0,04) | −0,34 (−0,58; −0,12) | Sì |
| H1b, congiunta (+1) − (+2) | −0,20 (−0,75; 0,39) | +0,01 (−0,28; 0,31) | Sì (zero) |
| H1c, bullet − rapid | +0,10 (−0,92; 1,05) | +0,85 (0,37; 1,35) | Compatibile; emerge solo in conferma |
| H1d, pendenza per 200 punti | +0,24 (−0,02; 0,53), p = 0,050 | +0,05 (−0,07; 0,17), p = 0,49 | No: segnale sparito |
| Separata +2 (distorta, P10) | −0,45 | −0,26 (−0,44; −0,09) | Sì: negativa, nessun falso rimbalzo |
| B pre-registrato (distorto, P1) | −0,81 (−1,12; −0,50) | −0,66 (−0,83; −0,50) | Sì |
| A, stessa sessione +1 | −2,51 (−2,74; −2,28) | −2,50 (−2,61; −2,38) | Sì |
| A, controllo negativo (> 30 min) | −1,49 | −1,51 (−1,68; −1,36) | Sì |
| A, pausa ≤ 5 min − controllo negativo | −1,08 | −1,01 (−1,21; −0,82) | Sì |
| A, confronto quasi ingenuo | −2,78 | −2,77 (−2,89; −2,66) | Sì |
| Fotofinish ≤ 3 s | −0,87 (−1,67; −0,06) | −0,54 (−0,98; −0,14) | Sì |
| Fotofinish ≤ 5 s | −1,49 (−2,16; −0,82) | −0,63 (−0,96; −0,32) | In parte: dimezzato |
| Fotofinish ≤ 3 s, blitz | −1,47 (−3,13; 0,22) | −1,38 (−2,22; −0,52) | Sì |
| Bilanciamento fotofinish: vantaggio di rating; atteso | −0,28; −0,26 | −0,27; −0,25 | Sì: criterio P8 non superato |
| Chiude la sessione dopo sconfitta − dopo vittoria | 25,4% − 20,9% = 4,55 | 25,4% − 20,6% = 4,75 (4,60; 4,91) | Sì |
| Rivincita dopo sconfitta − dopo vittoria | 36,0% − 33,8% = 2,13 | 36,6% − 34,3% = 2,29 (2,08; 2,51) | Sì |

Errori standard previsti in HANDOFF per la conferma: 0,09 (B) e 0,12 (congiunta); osservati 0,08 e 0,12. La lettura provvisoria dell'esplorazione («nessun tilt concentrato sulla partita successiva, persistenza locale sotto 1 pp non attribuibile») è confermata. I due segnali marginali dell'esplorazione (H1d, peso uguale per giocatore) non si replicano.

## 4. Robustezza (gruppo conferma)

Tutte le stime in pp; tra parentesi l'IC95. H1c = τ_B bullet − rapid; H1d = pendenza per +200 punti.

| Variante | τ_B | Congiunta +1 | Congiunta +2 | Congiunta +3 | H1b | H1c (p) | H1d (p) |
|---|---|---|---|---|---|---|---|
| **Principale** | −0,07 (−0,24; 0,09) | −0,68 (−0,90; −0,45) | −0,69 (−0,91; −0,45) | −0,34 (−0,58; −0,12) | +0,01 (−0,28; 0,31) | +0,85 (0,0009) | +0,05 (0,49) |
| Rivincite incluse | −0,39 (−0,52; −0,26) | −0,73 (−0,89; −0,58) | −0,72 (−0,88; −0,57) | −0,22 (−0,38; −0,08) | −0,00 (−0,19; 0,18) | +1,45 (< 0,001) | **+0,30 (≤ 0,005)** |
| Rating corrente | +0,04 (−0,12; 0,20) | −0,33 (−0,56; −0,11) | −0,36 (−0,58; −0,12) | −0,08 (−0,31; 0,14) | +0,03 (−0,25; 0,32) | +0,99 (0,0001) | +0,07 (0,30) |
| Due lati | −0,05 (−0,15; 0,05) | −0,56 (−0,74; −0,39) | −0,57 (−0,74; −0,41) | −0,30 (−0,47; −0,14) | +0,00 (−0,21; 0,19) | +1,03 (< 0,001) | **+0,12 (≤ 0,005)** |
| Senza partite corte | −0,01 (−0,17; 0,15) | −0,56 (−0,79; −0,33) | −0,64 (−0,87; −0,40) | −0,29 (−0,54; −0,07) | +0,08 (−0,22; 0,38) | +0,86 (0,0009) | +0,02 (0,75) |
| Rating stabile largo | −0,11 (−0,27; 0,05) | −0,73 (−0,96; −0,51) | −0,72 (−0,96; −0,50) | −0,38 (−0,61; −0,16) | −0,01 (−0,31; 0,28) | +0,83 (0,0008) | +0,07 (0,25) |
| Rating stabile stretto | −0,03 (−0,21; 0,14) | −0,66 (−0,89; −0,43) | −0,65 (−0,88; −0,42) | −0,31 (−0,54; −0,07) | −0,00 (−0,29; 0,28) | +0,75 (0,0045) | +0,06 (0,39) |
| Sessione a 10 minuti | +0,07 (−0,11; 0,25) | −0,56 (−0,82; −0,30) | −0,66 (−0,94; −0,41) | −0,46 (−0,71; −0,21) | +0,10 (−0,21; 0,44) | +1,01 (0,0008) | +0,04 (0,55) |
| Sessione a 60 minuti | −0,16 (−0,32; −0,00) | −0,66 (−0,85; −0,46) | −0,64 (−0,84; −0,43) | −0,36 (−0,56; −0,15) | −0,02 (−0,29; 0,23) | **+0,61 (0,0092)** | +0,05 (0,40) |

Verdetti:

- **H1a: «trascurabile» in tutte le nove varianti**, per τ_B (da −0,39 a +0,07) e per la congiunta a +1 (da −0,73 a −0,33). **H1b: mai diversa da zero.**
- **H1c**: segno e ordine di grandezza stabili (da +0,61 a +1,45). Con la sessione a 60 minuti p = 0,0092 è appena sopra la soglia prudente 0,0083: unica variante in cui la decisione di Holm cambia.
- **H1d**: diventa significativa in due varianti. *Rivincite incluse* (+0,30): è l'artefatto per cui le rivincite sono escluse (chi ti ha appena battuto è più forte del suo rating, e il rating informa meno ai livelli bassi); con le rivincite τ_B scende a −1,27 (−1,61; −0,94) nel rapid e a −1,00 (−1,32; −0,68) sotto 1400, uniche celle che toccano −1 pp. *Due lati* (+0,12): stessa direzione della principale (+0,05, il cui intervallo contiene 0,12), con il doppio dei dati. Lettura: pendenza nella direzione prevista ma minuscola, non confermata.
- **Rating corrente**: dimezza la congiunta (−0,33; +3 non più distinguibile da zero). Il rating corrente insegue i risultati recenti: assorbe parte della persistenza, qualunque ne sia la causa. Verdetto invariato; la persistenza sta tra −0,3 e −0,7 pp secondo la definizione dell'atteso.
- **Soglia di sessione**: τ_B va da +0,07 (10 min) a −0,07 (30) a −0,16 (60): blocchi più lunghi nel tempo contengono più deriva. Sempre dentro ±0,35.

## 5. Risultati descrittivi ed esplorativi (conferma, variante principale)

### 5.1 Dal confronto ingenuo allo stimatore primario

| Confronto | τ (pp) | IC95 | Che cosa contiene ancora |
|---|---|---|---|
| Quasi ingenuo (senza base del giocatore) | −2,77 | −2,89; −2,66 | Differenze tra giocatori, forma, abbinamento |
| A: stessa sessione, partita +1 | −2,50 | −2,61; −2,38 | Forma della giornata, errore del rating di sessione |
| A, peso uguale per giocatore | −2,89 | errore std 0,08 | Come sopra |
| A: controllo negativo, pausa oltre 30 min | −1,51 | −1,68; −1,36 | Forma di più giorni: non può essere tilt immediato |
| A: pausa ≤ 5 min − controllo negativo | −1,01 | −1,21; −0,82 | In simulazione senza tilt vale −1,1: non prova un tilt |
| B come pre-registrato (distorto, P1) | −0,66 | −0,83; −0,50 | Abbinamento; in simulazione senza tilt −1,06 |
| **B (primario)** | **−0,07** | −0,24; 0,09 | — |
| B, peso uguale per giocatore | −0,12 | −0,37; 0,10 | — |
| B, rimescolamento libero | −0,17 | — | Regole di selezione: pesano 0,10 pp |

### 5.2 Stimatore B per cella

| Cella | Blocchi | b (pp) | τ_B (pp) | IC95 | p permutazione |
|---|---|---|---|---|---|
| Tutte | 662.938 | 13,25 | −0,07 | −0,24; 0,09 | 0,423 |
| Bullet | 147.230 | 8,76 | +0,30 | −0,02; 0,58 | 0,030 |
| Blitz | 364.962 | 13,94 | −0,16 | −0,39; 0,07 | 0,149 |
| Rapid | 150.746 | 19,17 | −0,55 | −0,93; −0,16 | 0,005 |
| Rating < 1400 | 142.080 | 15,54 | −0,19 | −0,58; 0,19 | 0,358 |
| 1400–1599 | 172.897 | 13,95 | −0,25 | −0,58; 0,06 | 0,139 |
| 1600–1799 | 181.427 | 12,69 | +0,01 | −0,27; 0,30 | 0,965 |
| 1800–1999 | 112.847 | 11,82 | +0,22 | −0,13; 0,59 | 0,189 |
| ≥ 2000 | 53.687 | 10,76 | −0,15 | −0,69; 0,40 | 0,567 |

Nessuna cella raggiunge −1 pp. Con la correzione FDR sulle otto celle resta solo il rapid, che è comunque «trascurabile» sulla regola di 1 pp. Nel bullet il segno è positivo (+0,47 con il rating corrente, +0,45 con due lati): se mai, dopo un risultato inatteso negativo si fa leggermente meglio.

### 5.3 Distanza

| Distanza | Congiunta (pp) | IC95 | Coppie | Senza tipi | Separata con rimescolamenti (distorta, P10) | A |
|---|---|---|---|---|---|---|
| +1 | −0,68 | −0,90; −0,45 | 1.168.821 | −0,68 | −0,07 (−0,24; 0,08) | −2,50 |
| +2 | −0,69 | −0,91; −0,45 | 1.119.170 | −0,71 | −0,26 (−0,44; −0,09) | −2,29 |
| +3 | −0,34 | −0,58; −0,12 | 1.131.457 | −0,47 | −0,33 (−0,53; −0,16) | −2,12 |

Con e senza tipi di selezione le stime coincidono a +1 e +2. Le regressioni separate a +2 e +3 sono negative: con un tilt concentrato a +1 sarebbero positive (falso rimbalzo, P10). A è quasi piatto con la distanza: misura soprattutto la forma della giornata.

### 5.4 Stimatore A per pausa, classe e livello

| Cella | τ_A (pp) | IC95 |
|---|---|---|
| Pausa fino a 15 s | −3,44 | −4,53; −2,24 |
| Pausa 15–60 s | −2,73 | −2,89; −2,59 |
| Pausa 1–5 min | −2,26 | −2,45; −2,06 |
| Pausa 5–30 min | −2,29 | −2,54; −2,01 |
| Oltre 30 min (controllo negativo) | −1,51 | −1,68; −1,36 |
| di cui 30 min – 6 h | −1,69 | −1,91; −1,47 |
| di cui oltre 6 h | −1,29 | −1,53; −1,03 |
| Bullet | −1,96 | −2,20; −1,73 |
| Blitz | −2,45 | −2,61; −2,29 |
| Rapid | −3,21 | −3,46; −2,97 |
| Rating < 1400 | −3,01 | −3,27; −2,78 |
| 1400–1599 | −3,05 | −3,28; −2,83 |
| 1600–1799 | −2,42 | −2,62; −2,21 |
| 1800–1999 | −2,05 | −2,31; −1,77 |
| ≥ 2000 | −1,70 | −2,09; −1,29 |

La pausa la sceglie il giocatore: la curva è descrittiva. A è un limite superiore: contiene la forma della giornata.

### 5.5 Fotofinish (verifica causale 1)

| Cella | n perdenti / vincitori | τ (pp) | IC95 | p |
|---|---|---|---|---|
| Vincitore entro 3 s | 98.647 / 101.115 | −0,54 | −0,98; −0,14 | 0,013 |
| Vincitore entro 5 s | 151.881 / 155.638 | −0,63 | −0,96; −0,32 | 0,0002 |
| Entro 3 s e perdente entro 10 s | 98.210 / 100.509 | −0,55 | −1,01; −0,15 | 0,011 |
| Entro 3 s, bullet | 74.029 / 76.053 | −0,31 | −0,75; 0,16 | 0,200 |
| Entro 3 s, blitz | 23.641 / 24.139 | −1,38 | −2,22; −0,52 | 0,0015 |
| Entro 3 s, rapid | 977 / 923 | +2,76 | −1,54; 6,80 | 0,211 |

| Bilanciamento prima del fotofinish | Perdenti | Vincitori | Differenza standardizzata |
|---|---|---|---|
| Vantaggio di rating nella partita | −14,5 | +15,9 | **−0,27** |
| Atteso nella partita | 0,472 | 0,504 | **−0,25** |
| Rating | 1662,9 | 1678,8 | −0,06 |
| Posizione nella sessione | 13,6 | 13,1 | 0,03 |
| Base del giocatore (pp) | −0,09 | −0,14 | 0,01 |
| Punteggio nella partita prima | 0,500 | 0,524 | −0,05 |

Criterio di P8 non superato (vantaggio di rating e atteso oltre 0,1): la volata la vince più spesso chi ha più rating. Va letta come variante di A, non come verifica causale; le variabili di forma sono bilanciate. La stima complessiva resta sotto 1 pp. Il blitz (−1,38, uguale all'esplorazione: −1,47) è l'unica cella dello studio che soddisfa la regola «rilevante»: esplorativa, da riprendere con la stratificazione per atteso.

### 5.6 Residuo medio per posizione nella sessione (pp)

| Posizione | Bullet | Blitz | Rapid |
|---|---|---|---|
| 1 | 0,07 | −0,04 | 0,13 |
| 2 | 1,72 | 0,62 | 0,42 |
| 3 | 1,76 | 0,66 | 0,65 |
| 4–5 | 1,93 | 0,94 | 0,71 |
| 6–10 | 1,97 | 1,16 | 0,49 |
| 11–20 | 2,62 | 1,15 | 0,32 |
| 21+ | 2,24 | 1,11 | −0,10 |

Errori standard tra 0,05 e 0,18 (rapid 21+: 0,40). Non c'è stanchezza: il residuo sale dalla seconda partita. Riscaldamento o selezione (chi vince continua): descrittivo. Gli stimatori lavorano sul residuo già corretto per posizione.

### 5.7 Selezione

| Cella | Chiude la sessione: dopo sconfitta − dopo vittoria (pp) | Rivincita: dopo sconfitta − dopo vittoria (pp) |
|---|---|---|
| Tutte | +4,75 (4,60; 4,91): 25,4% contro 20,6% | +2,29 (2,08; 2,51): 36,6% contro 34,3% |
| Bullet | +2,64 (2,38; 2,87) | +2,63 (2,20; 3,06) |
| Blitz | +5,08 (4,86; 5,29) | +2,08 (1,87; 2,31) |
| Rapid | +6,56 (6,25; 6,85) | +1,88 (1,56; 2,19) |

## 6. Che cosa si può concludere e che cosa no

**Sì**

- Tra chi continua a giocare, contro un avversario diverso, il risultato della partita precedente sposta quello della successiva di meno di 1 pp (al più 6 punti Elo). Vale per classe, livello e in nove varianti.
- Il confronto ingenuo «dopo sconfitta − dopo vittoria» sovrastima di un ordine di grandezza. La differenza che resta dopo oltre 30 minuti (−1,5 pp) mostra che gran parte è forma, non reazione alla sconfitta.
- I risultati vicini si somigliano un po' più di quelli lontani nella stessa sessione (0,3–0,7 pp per punto di risultato inatteso), senza un ruolo speciale della partita immediatamente precedente.
- Dopo una sconfitta si smette più spesso (+4,75 pp) e si chiede un po' più spesso la rivincita (+2,3 pp).
- L'ipotesi «più veloce = più tilt» è contraddetta dai dati: l'ordine è rapid > blitz > bullet.

**No**

- Che il tilt non esista: τ riguarda le partite davvero giocate. Chi va in tilt e smette non è misurato, e l'effetto medio non esclude giocatori singoli con un tilt forte.
- Che la persistenza locale sia tilt (o che non lo sia): un tilt di più partite e una deriva della forma danno la stessa curva.
- Nulla sulla qualità delle mosse: il campione con valutazioni dipende dal risultato (P12).
- Nulla di causale: il fotofinish non è bilanciato su rating e atteso. Il segnale nel blitz (−1,4 pp dopo una sconfitta per tempo al fotofinish) è esplorativo.
- Nulla sulle rivincite contro lo stesso avversario (τ_B −0,39; rapid −1,27): lì tilt e forza vera dell'avversario sono confusi.
- Nulla fuori da maggio 2017, dai giocatori con rating stabile e dalle cadenze bullet, blitz, rapid fuori torneo.
- Perché il rapid mostri più dipendenza del bullet: spiegazioni solo post hoc.

## 7. Specifiche dei grafici (i numeri sono nelle tabelle sopra e in `08_stime_conferma*.csv`)

1. **«La scala»** (grafico principale): τ dal confronto ingenuo a B, punti con IC95 su un asse orizzontale: ingenuo −2,77 → A −2,50 → controllo negativo −1,51 → B pre-registrato −0,66 → congiunta +1 −0,68 → B −0,07. Fascia grigia tra −1 e +1 pp («trascurabile»). Messaggio: ogni correzione toglie un pezzo che non è tilt.
2. **Curva per distanza**: congiunta a +1, +2, +3 con IC95 (conferma piena, esplorazione sbiadita). Linea a zero e a −1. Messaggio: piatta tra +1 e +2, non è un tilt di una partita.
3. **Robustezza** (forest plot): τ_B e congiunta +1 per le nove varianti, con la fascia ±1 pp. Messaggio: il verdetto non dipende dalle scelte.
4. **A per pausa**: cinque fasce più il controllo negativo, con IC95. Nota nel titolo: descrittivo, la pausa la sceglie il giocatore.
5. **Per classe e livello**: τ_B per bullet, blitz, rapid e per le cinque fasce di rating. Messaggio: H1c al contrario, H1d piatta.
6. **Posizione nella sessione**: residuo medio per posizione, una linea per classe. Messaggio: nessuna stanchezza, riscaldamento o selezione.

## 8. Approfondimenti post hoc

Specifica in `claude/HANDOFF.md`, sezione «Specifica degli approfondimenti post hoc». Sono esplorativi, non cambiano nessun verdetto di questa pagina e vanno riportati in una sezione separata e dichiarata.
