"""
08_tilt.py - Domanda 1: dopo una sconfitta si gioca peggio? Stimatori A e B

Tutto e' in punti percentuali di punteggio ("pp"). tau = punteggio (meno l'atteso)
dopo una SCONFITTA - dopo una VITTORIA. tau negativo = dopo una sconfitta si gioca peggio.

Stimatore A (tra sessioni)
  Ogni giocatore e' confrontato con se stesso nelle ALTRE sessioni (la sua "base").
  Contiene ancora la "giornata storta" e l'errore del rating a inizio sessione:
  chi e' in cattiva forma perde la partita prima E gioca male quella dopo, senza
  alcun tilt. Per questo A e' un limite superiore (in valore assoluto) del tilt.
  Il controllo negativo (partita dopo una pausa oltre la soglia) misura quanta
  parte di A NON e' tilt.

Stimatore B (dentro il blocco, primario)
  Confronta tra loro le partite dello stesso blocco (stessa sessione, stessa
  classe): giornata storta ed errore del rating sono uguali per tutte e spariscono.
  E' una regressione con un effetto fisso per blocco del residuo y di una partita
  sul residuo della partita precedente (il suo risultato INATTESO). Quattro trappole:

  1. Sequenze corte (Miller e Sanjurjo 2018; "distorsione di Nickell"). Dentro un
     blocco corto il confronto e' distorto anche se l'ordine delle partite non
     conta nulla: se la partita prima e' andata male, le ALTRE del blocco sono
     per forza andate meglio della media del blocco. Stimo la distorsione b
     rimescolando l'ordine delle partite dentro ogni blocco, e correggo:
         tau_B = (tau_osservato - b) / (1 - b)
     La divisione serve perche' la stessa distorsione schiaccia verso zero un
     effetto vero, del fattore (1 - b). I rimescolamenti danno anche il p-value.

  2. Abbinamento (scoperta sui dati simulati, prima di guardare quelli veri). Il
     confronto "dopo sconfitta / dopo vittoria" dentro la sessione e' distorto dal
     sistema di abbinamento: se vinco, il mio rating sale, incontro avversari piu'
     forti e perdo piu' spesso DOPO. Vittorie e sconfitte non sono scambiabili
     nemmeno senza tilt, e il rimescolamento non lo corregge (-1 pp su dati
     simulati senza alcun tilt). Il risultato inatteso (punteggio - atteso)
     invece tiene gia' conto della forza dell'avversario: senza tilt e'
     scambiabile. Per questo B usa il residuo della partita precedente e non il
     suo esito. La versione pre-registrata resta in tabella, solo per confronto.

  3. Chi smette e chi chiede la rivincita (precisazione P11). Smettere e chiedere
     la rivincita dipendono dal risultato appena ottenuto: l'ultima partita del
     blocco, o una partita seguita da una rivincita, non e' una partita qualsiasi.
     Inoltre le rivincite non fanno da esito e arrivano a serie: quali partite
     entrano nel confronto e' una STRUTTURA del blocco, che non va rimescolata.
     Nei rimescolamenti la struttura resta ferma (chi e' una rivincita, chi fa da
     esito, qual e' l'ultima partita) e si scambiano solo i risultati, e solo tra
     partite dello stesso tipo di selezione (vedi DatiBlocchi.tipo). La colonna
     "rim_libero" scambia i risultati tra tutte le partite del blocco: se
     differisce, le regole di selezione contano.
     Collaudo: con serie di rivincite e nessun tilt, rimescolando le partite
     insieme ai loro attributi (versione precedente) lo stimatore dava in media
     +1,3 pp, con p = 0,005; con la struttura ferma torna a zero.

  4. Distanza +2 e +3 (scoperta sui dati simulati, precisazione P10). Tolta la
     media del blocco, i prodotti tra tutte le coppie di partite di un blocco hanno
     somma fissa. Se le coppie a distanza 1 si somigliano piu' della media (tilt
     vero a +1), le altre coppie devono per forza somigliarsi MENO della media. La
     regressione separata a distanza +2 trova allora un falso "rimbalzo": +0,9 pp
     in media simulando un tilt di -3,9 pp solo a +1. Il rimescolamento non lo
     corregge, perche' il suo termine di paragone sono tutte le coppie del blocco,
     comprese quelle a distanza 1.
     Per questo la curva per distanza (e il test H1b) usa una STIMA CONGIUNTA
     (vedi DatiBlocchi.somme_congiunte): le tre distanze sono stimate insieme, e il
     termine di paragone sono le partite LONTANE (almeno 4 posti prima dell'esito)
     dello stesso blocco, che non contengono nessuna delle distanze stimate.
     La regressione a distanza +1 con rimescolamenti resta lo stimatore primario
     di H1a: e' corretta se l'effetto dura una sola partita; se dura di piu' e'
     schiacciata verso zero (prudente). Le regressioni separate a +2 e +3 restano
     in una tabella a parte, solo per confronto.

  Collaudo su dati simulati (tests/simula_dati.py), medie su 7 semi: tilt 0 ->
  tau_B = 0,14 pp (errore standard della media 0,17); tilt di 30 Elo (circa
  -3,9 pp) -> tau_B = -3,71 pp (0,09). Stima congiunta e scenari con rivincite:
  PRECISAZIONI.md, P10 e P11.

Intervalli al 95%: bootstrap a grappolo sui giocatori (si ricampionano i giocatori
interi, non le partite: le partite di uno stesso giocatore non sono indipendenti).

Inoltre: effetto per pausa e distanza, finali al fotofinish (verifica causale 1),
curva della stanchezza, probabilita' di chiudere la sessione.

Uso (PowerShell, nella cartella C:\\tilt):
    .\\.venv\\Scripts\\python 08_tilt.py                       (gruppo esplorazione)
    .\\.venv\\Scripts\\python 08_tilt.py --gruppo conferma --codice-bloccato
Robustezza (una variante alla volta):
    --rivincite | --rating corrente | --due-lati | --senza-corte
    --stabile largo | --stabile stretto | --soglia 10 | --soglia 60
"""

import argparse
import math
import sys
import time

import numpy as np
import pandas as pd

from tilt_utils import CARTELLA_DATI, CARTELLA_OUTPUT, CLASSI, Registro, apri_duckdb

FASCE_RATING = ["<1400", "1400-1599", "1600-1799", "1800-1999", ">=2000"]
SQL_FASCIA_RATING = """CASE WHEN rating_rif < 1400 THEN 0 WHEN rating_rif < 1600 THEN 1
                            WHEN rating_rif < 1800 THEN 2 WHEN rating_rif < 2000 THEN 3 ELSE 4 END"""
SQL_CLASSE_ID = "CASE classe " + " ".join(f"WHEN '{c}' THEN {i}" for i, c in enumerate(CLASSI)) + " END"
FASCE_PAUSA = ["fino a 15 s", "15-60 s", "1-5 min", "5 min - soglia", "soglia - 6 h", "oltre 6 h"]
N_CELLE_B = 1 + len(CLASSI) + len(FASCE_RATING)      # tutte, 3 classi, 5 fasce di rating
N_DISTANZE = 3                                       # stima congiunta: distanze +1, +2, +3
NOMI_CELLE_B = ["tutte"] + [f"classe {c}" for c in CLASSI] + [f"rating {f}" for f in FASCE_RATING]


# --------------------------------------------------------------------------
# Bootstrap a grappolo sui giocatori
# --------------------------------------------------------------------------
def bootstrap_somme(matrice, n_boot, rng, blocco=50):
    """Ricampiona i giocatori con reinserimento e restituisce le somme per colonna.

    matrice: una riga per giocatore, una colonna per ogni somma che serve alle stime
             (per esempio: somma dei residui dopo sconfitta, numero di partite...).
    Ogni stima e' una funzione di queste somme: basta ricalcolarla sulle somme
    ricampionate, senza mai tornare alle singole partite. Per questo costa poco.
    """
    n = matrice.shape[0]
    risultati = np.empty((n_boot, matrice.shape[1]))
    probabilita = np.full(n, 1.0 / n)
    for inizio in range(0, n_boot, blocco):
        quanti = min(blocco, n_boot - inizio)
        # conteggi[r, i] = quante volte il giocatore i e' estratto nel ricampionamento r
        conteggi = rng.multinomial(n, probabilita, size=quanti).astype(np.float64)
        risultati[inizio:inizio + quanti] = conteggi @ matrice
    return risultati


def p_normale(stima, err_std):
    """p-value a due code da stima / errore standard (approssimazione normale)."""
    if not np.isfinite(stima) or not np.isfinite(err_std) or err_std <= 0:
        return np.nan
    return math.erfc(abs(stima / err_std) / math.sqrt(2))


N_MIN_CELLA = 30   # sotto questo numero di coppie per tipo la stima non viene riportata


def intervallo(valori):
    """Intervallo al 95% (percentili 2,5 e 97,5 dei ricampionamenti) ed errore standard."""
    return np.nanpercentile(valori, 2.5, axis=0), np.nanpercentile(valori, 97.5, axis=0), np.nanstd(valori, axis=0)


# --------------------------------------------------------------------------
# Stimatore B: dentro il blocco, con rimescolamenti
# --------------------------------------------------------------------------
class DatiBlocchi:
    """Partite dei blocchi con almeno 2 partite, ordinate per (giocatore, blocco, posizione).

    Due tipi di vettori:
      - di STRUTTURA (blk, pos, ultimo, tipo, esito_ok, prec_ok): dicono quali partite
        sono rivincite, quali fanno da esito, qual e' l'ultima. NON si rimescolano;
      - di RISULTATO (punt, y): sono cio' che si scambia nei rimescolamenti.
    """

    def __init__(self, con, analisi, gruppo, opz):
        col_y = "y_cor" if opz.rating == "corrente" else "y"
        d = con.execute(f"""
            SELECT gid, blocco, (punteggio * 2)::TINYINT AS punt, {col_y} AS y, lato_scelto, corta,
                   COALESCE(pos_blocco > 1 AND avv = prec_avv, FALSE) AS rivincita,
                   {SQL_CLASSE_ID} AS classe_id, {SQL_FASCIA_RATING} AS fascia_id, rating_rif
            FROM {analisi}
            WHERE gruppo = '{gruppo}' AND blocco IS NOT NULL AND n_blocco >= 2 AND {opz.col_stabile}
            ORDER BY gid, blocco, pos_blocco
        """).fetchnumpy()
        gid = np.asarray(d["gid"])
        blocco = np.asarray(d["blocco"])
        self.n = len(gid)
        self.primo = np.r_[True, (gid[1:] != gid[:-1]) | (blocco[1:] != blocco[:-1])]
        self.blk = np.cumsum(self.primo) - 1                     # indice del blocco, 0..nb-1
        self.nb = int(self.blk[-1]) + 1
        inizio_blocco = np.maximum.accumulate(np.where(self.primo, np.arange(self.n), 0))
        self.pos = np.arange(self.n) - inizio_blocco             # 0 = prima partita del blocco
        self.punt = np.asarray(d["punt"]).astype(np.int8)        # 0 sconfitta, 1 patta, 2 vittoria
        y = np.asarray(d["y"], dtype=np.float64)
        manca = np.isnan(y)
        self.y = np.where(manca, 0.0, y)
        rivincita = np.asarray(d["rivincita"]).astype(bool)
        self.ultimo = np.r_[self.primo[1:], True]                # ultima partita di ogni blocco
        corta = np.asarray(d["corta"]).astype(bool)
        scelto = np.asarray(d["lato_scelto"]).astype(bool)
        # Una partita puo' fare da ESITO se e' il lato scelto (una riga per partita)...
        self.esito_ok = (scelto | opz.due_lati) & ~manca
        # ...e da PRECEDENTE sempre (salvo l'opzione che esclude le partite corte).
        self.prec_ok = ~manca
        if opz.senza_corte:
            self.esito_ok &= ~corta
            self.prec_ok &= ~corta
        # Le rivincite non fanno da esito: chi ti ha appena battuto e' in media piu'
        # forte del suo rating. E' un attributo della partita, fissato sull'ordine vero.
        if not opz.rivincite:
            self.esito_ok &= ~rivincita
        # TIPO DI SELEZIONE di ogni partita (P11): che cosa le e' successo intorno.
        #   seguito: 0 = dopo, una partita contro un altro avversario;
        #            1 = dopo, una rivincita (che non fa da esito);
        #            2 = e' l'ultima del blocco (dopo si e' smesso, o il blocco si e' interrotto);
        #   + 3 se la partita stessa e' una rivincita.
        # Smettere e chiedere la rivincita dipendono dal risultato appena ottenuto, e in
        # una rivincita si ritrova lo stesso avversario: i tipi hanno medie diverse
        # anche senza tilt, e si confrontano solo tra loro.
        # Con --rivincite le rivincite sono partite come le altre: conta solo "ultima".
        self.tipo = np.where(self.ultimo, 2, 0)
        if not opz.rivincite:
            seguita_da_rivincita = np.zeros(self.n, dtype=bool)
            seguita_da_rivincita[:-1] = rivincita[1:]        # la prima di un blocco non e' mai rivincita
            self.tipo = np.where(self.ultimo, 2, seguita_da_rivincita.astype(np.int64)) + 3 * rivincita
        # Chiavi per rimescolare: dentro il blocco e il tipo (schema principale) o solo
        # dentro il blocco (schema "libero"). Le partite senza y, o escluse da ogni ruolo,
        # si scambiano solo tra loro: cosi' chi fa da esito e chi da precedente non cambia.
        fuori = manca | (corta if opz.senza_corte else False)
        self.chiave_tipo = (self.blk * 12 + self.tipo + 6 * fuori).astype(np.float64)
        self.posti_tipo = np.argsort(self.chiave_tipo, kind="stable")
        # Attributi del blocco (dalla sua prima riga)
        giocatori, self.gioc_blk = np.unique(gid[self.primo], return_inverse=True)
        self.n_gioc = len(giocatori)
        self.classe_blk = np.asarray(d["classe_id"])[self.primo].astype(np.int64)
        self.fascia_blk = np.asarray(d["fascia_id"])[self.primo].astype(np.int64)
        self.x_blk = (np.asarray(d["rating_rif"])[self.primo].astype(np.float64) - 1700.0) / 200.0
        self.chiave = self.blk.astype(np.float64)                # per rimescolare restando nel blocco

    def ordine_casuale(self, rng, entro_tipo):
        """Rimescola i RISULTATI delle partite dentro ogni blocco; la struttura resta ferma.

        Restituisce `ordine`: al posto i va il risultato della partita ordine[i].
        Restano fermi al loro posto tutti gli attributi di struttura: quali partite
        sono rivincite, quali fanno da esito, qual e' l'ultima. Si scambiano solo i
        risultati (y e punteggio).

        entro_tipo=True (schema principale): un risultato puo' finire solo al posto
        di una partita dello stesso TIPO di selezione (vedi self.tipo). Motivo: la
        decisione di smettere o di chiedere la rivincita dipende dal risultato appena
        ottenuto, quindi il risultato dell'ultima partita, o di una partita seguita da
        una rivincita, non e' "un risultato qualsiasi". Tra partite dello stesso tipo,
        invece, se l'ordine non conta i risultati sono scambiabili.
        entro_tipo=False (schema "libero"): scambi tra tutte le partite del blocco;
        solo per confronto.

        Tecnica: chiave = numero della classe + numero casuale in [0, 1). Ordinando per
        chiave ottengo, classe per classe, le partite in ordine casuale; le assegno
        ai posti della stessa classe, presi nel loro ordine naturale.
        """
        casuale = rng.random(self.n)
        if not entro_tipo:
            return np.argsort(self.chiave + casuale)             # la classe e' il blocco: i posti sono gia' in ordine
        ordine = np.empty(self.n, dtype=np.int64)
        ordine[self.posti_tipo] = np.argsort(self.chiave_tipo + casuale)
        return ordine

    def regressione(self, ordine, distanza):
        """Regressione dentro il blocco del residuo y sul residuo x di `distanza` partite prima.

        E' una regressione con un effetto fisso per blocco:
            pendenza = somma (x - media_x)(y - media_y) / somma (x - media_x)^2
        Per ogni blocco restituisco il denominatore (peso w) e il numeratore cambiato
        di segno: tau = somma numeratori / somma pesi = -pendenza. Tra una sconfitta
        e una vittoria x cambia di un punto intero: tau si legge "dopo sconfitta - dopo vittoria".
        """
        prec = np.empty_like(ordine)
        prec[distanza:] = ordine[:-distanza]
        prec[:distanza] = ordine[:distanza]
        # Chi fa da esito e chi da precedente dipende dal POSTO, non dal risultato che ci finisce
        prec_ok_posto = np.zeros(self.n, dtype=bool)
        prec_ok_posto[distanza:] = self.prec_ok[:-distanza]
        ok = (self.pos >= distanza) & self.esito_ok & prec_ok_posto
        conta = lambda pesi: np.bincount(self.blk, weights=pesi, minlength=self.nb)
        x = self.y[prec] * ok
        yc = self.y[ordine] * ok
        n = conta(ok)
        sx, sy = conta(x), conta(yc)
        nn = np.maximum(n, 1)
        w = np.where(n >= 2, conta(x * x) - sx * sx / nn, 0.0)
        num = -np.where(n >= 2, conta(x * yc) - sx * sy / nn, 0.0)
        return w, num, prec, ok

    def statistica(self, ordine):
        """Per ogni blocco: peso e numeratore, dato un ordine delle partite. Quattro versioni.

        "residuo" (principale), "residuo_d2", "residuo_d3": regressione sul risultato
          inatteso di 1, 2, 3 partite prima (vedi regressione).
        "esito" (come pre-registrato): media di y dopo sconfitta - dopo vittoria nel
          blocco, con peso nL * nW / (nL + nW). E' DISTORTA dal sistema di
          abbinamento (vedi intestazione): resta solo per confronto.
        """
        w1, num1, prec, ok = self.regressione(ordine, 1)
        w2, num2, _, _ = self.regressione(ordine, 2)
        w3, num3, _, _ = self.regressione(ordine, 3)

        conta = lambda pesi: np.bincount(self.blk, weights=pesi, minlength=self.nb)
        yc = self.y[ordine]
        esito_prec = self.punt[prec]
        dopo_sconfitta = ok & (esito_prec == 0)
        dopo_vittoria = ok & (esito_prec == 2)
        nL, nW = conta(dopo_sconfitta), conta(dopo_vittoria)
        sL, sW = conta(yc * dopo_sconfitta), conta(yc * dopo_vittoria)
        valido = (nL > 0) & (nW > 0)
        tot = np.maximum(nL + nW, 1)
        w_esi = np.where(valido, nL * nW / tot, 0.0)
        num_esi = np.where(valido, (sL * nW - sW * nL) / tot, 0.0)
        return {"residuo": (w1, num1), "residuo_d2": (w2, num2), "residuo_d3": (w3, num3),
                "esito": (w_esi, num_esi)}, int(ok.sum())

    def somme_giocatore(self, w, num):
        """Matrice (giocatori x 21): somme di w e di num per cella, piu' quelle per la pendenza.

        Colonne 0-8: somma di w per cella; 9-17: somma di num per cella;
        18-20: somme di w*x, w*x^2, num*x (x = rating di riferimento, per la pendenza H1d).
        """
        M = np.zeros((self.n_gioc, 2 * N_CELLE_B + 3))
        for cella in (np.zeros(self.nb, dtype=np.int64), 1 + self.classe_blk, 1 + len(CLASSI) + self.fascia_blk):
            indice = self.gioc_blk * N_CELLE_B + cella
            dimensione = self.n_gioc * N_CELLE_B
            M[:, :N_CELLE_B] += np.bincount(indice, weights=w, minlength=dimensione).reshape(self.n_gioc, N_CELLE_B)
            M[:, N_CELLE_B:2 * N_CELLE_B] += np.bincount(indice, weights=num, minlength=dimensione).reshape(self.n_gioc, N_CELLE_B)
        M[:, -3] = np.bincount(self.gioc_blk, weights=w * self.x_blk, minlength=self.n_gioc)
        M[:, -2] = np.bincount(self.gioc_blk, weights=w * self.x_blk ** 2, minlength=self.n_gioc)
        M[:, -1] = np.bincount(self.gioc_blk, weights=num * self.x_blk, minlength=self.n_gioc)
        return M

    def somme_congiunte(self, per_tipo=True):
        """Stima congiunta per distanza (P10): somme per giocatore e numero di coppie.

        Per ogni partita t che fa da esito guardo SOLO il suo passato nel blocco:
          x_d = risultato inatteso della partita di d posti prima (d = 1, 2, 3);
          z_d = x_d - media dei risultati delle partite LONTANE (distanza 4 o piu')
                che hanno lo stesso tipo di selezione della partita di d posti prima.
        z_d dice se la partita di d posti prima e' andata meglio o peggio delle partite
        lontane e confrontabili della stessa serata. Se l'ordine non conta, y_t non ha
        motivo di seguire z_d; con un tilt a distanza d, a z_d basso segue y_t basso.

        Stima: i tre coefficienti b_1, b_2, b_3 risolvono insieme le tre equazioni
            somma_t y_t * z_d  =  somma_k b_k * (somma_t x_k * z_d)        d = 1, 2, 3
        E' la regressione di y_t su x_1, x_2, x_3 in cui z fa da "strumento": b_d e'
        l'effetto del risultato di d partite prima A PARITA' delle altre due.
        tau_d = -b_d, che come per B si legge "dopo sconfitta - dopo vittoria".

        Perche' cosi':
          - il termine di paragone (le partite lontane) non contiene le distanze che
            sto stimando: niente falso rimbalzo a +2;
          - z usa solo partite PRECEDENTI a t: nessuna media di blocco che contenga
            y_t, quindi nessuna distorsione delle sequenze corte e nessun rimescolamento;
          - il confronto e' tra partite dello stesso tipo di selezione (seguite o no da
            una rivincita, rivincite o no): chi smette e chi chiede la rivincita non
            falsano il confronto. Nessuna condizione su cio' che succede DOPO t.
        Ipotesi: dopo 3 partite l'effetto e' finito. Costo: servono almeno 4 partite
        prima di t, quindi contano solo i blocchi con almeno 5 partite.

        per_tipo=False confronta con tutte le partite lontane, senza guardare il tipo
        (solo per confronto: se differisce, le regole di selezione contano).
        Restituisce una riga per giocatore: 9 colonne (somma_t x_k * z_d) e 3 (somma_t y_t * z_d).
        """
        D = N_DISTANZE
        e = self.esito_ok.astype(np.float64)                 # la partita puo' fare da esito
        p = self.prec_ok.astype(np.float64)                  # la partita puo' fare da precedente
        py = p * self.y
        inizio = np.arange(self.n) - self.pos                # indice della prima partita del blocco

        def spostato(v, d):
            """Il valore di v nella partita di d posti prima nello stesso blocco (0 se non c'e')."""
            w = np.zeros(self.n)
            w[d:] = v[:-d]
            return w * (self.pos >= d)

        x = [spostato(py, d) for d in range(1, D + 1)]       # x_1, x_2, x_3
        A, m, coppie = np.zeros((self.n_gioc, D * D)), np.zeros((self.n_gioc, D)), np.zeros(D)
        gioc_riga = self.gioc_blk[self.blk]                  # il giocatore di ogni riga
        per_giocatore = lambda v: np.bincount(gioc_riga, weights=v, minlength=self.n_gioc)
        # Una partita precedente non e' mai l'ultima del blocco: i tipi con "seguito" = 2 non servono
        tipi = [self.tipo == k for k in np.unique(self.tipo) if k % 3 != 2] if per_tipo else [np.ones(self.n, dtype=bool)]
        for del_tipo in tipi:
            q = p * del_tipo                                 # partite precedenti di questo tipo
            qy = q * self.y
            # Somma e numero delle partite di questo tipo PRIMA di t nel blocco: somma
            # cumulata fino a t, meno la partita t, meno cio' che precede il blocco...
            cum_y, cum_n = np.cumsum(qy), np.cumsum(q)
            lont_y = cum_y - qy - (cum_y[inizio] - qy[inizio])
            lont_n = cum_n - q - (cum_n[inizio] - q[inizio])
            q_d = [spostato(q, d) for d in range(1, D + 1)]  # la partita di d posti prima e' di questo tipo?
            # ...meno le tre piu' vicine: restano le LONTANE (distanza 4 o piu').
            for d in range(D):
                lont_y -= spostato(qy, d + 1)
                lont_n -= q_d[d]
            lont_n = np.round(lont_n)                        # e' un conteggio: tolgo gli errori di arrotondamento
            media_lontane = lont_y / np.maximum(lont_n, 1.0)
            for d in range(D):
                usabile = e * q_d[d] * (lont_n > 0)          # t fa da esito, la partita a distanza d+1 e' del tipo, c'e' il paragone
                z = usabile * (x[d] - media_lontane)
                m[:, d] += per_giocatore(self.y * z)
                for k in range(D):
                    A[:, d * D + k] += per_giocatore(x[k] * z)
                coppie[d] += usabile.sum()
        return np.column_stack([A, m]), [int(c) for c in coppie]


def stime_congiunte(S):
    """Dalle somme di somme_congiunte: tau a distanza +1, +2, +3 (in frazione, non in pp).

    Risolve il sistema A b = m (3 equazioni, 3 incognite) e restituisce tau = -b.
    """
    D = N_DISTANZE
    S = np.atleast_2d(S)
    A = S[:, :D * D].reshape(-1, D, D)
    m = S[:, D * D:]
    tau = np.full((len(S), D), np.nan)
    risolvibile = np.abs(np.linalg.det(A)) > 1e-9
    if risolvibile.any():
        tau[risolvibile] = -np.linalg.solve(A[risolvibile], m[risolvibile][..., None])[..., 0]
    return tau


def tau_e_pendenza(S):
    """Dalle somme per colonna: tau per cella e pendenza di tau sul rating (per 200 punti)."""
    with np.errstate(divide="ignore", invalid="ignore"):
        W, NUM = S[..., :N_CELLE_B], S[..., N_CELLE_B:2 * N_CELLE_B]
        tau = NUM / W
        x_medio = S[..., -3] / W[..., 0]
        # minimi quadrati pesati di tau_blocco su x: equivale all'interazione
        # (dopo sconfitta) x (rating) in una regressione con effetti fissi di blocco
        pendenza = (S[..., -1] - x_medio * NUM[..., 0]) / (S[..., -2] - x_medio * S[..., -3])
    return tau, pendenza


def stime_B(S_oss, S_rim):
    """Stime corrette. S_oss: somme osservate; S_rim: somme medie sui rimescolamenti."""
    tau_oss, pend_oss = tau_e_pendenza(S_oss)
    b, pend_rim = tau_e_pendenza(S_rim)
    tau_B = (tau_oss - b) / (1 - b)
    pendenza_B = (pend_oss - pend_rim) / (1 - b[..., 0])
    i_bullet, i_rapid = 1 + CLASSI.index("bullet"), 1 + CLASSI.index("rapid")
    return tau_oss, b, tau_B, pendenza_B, tau_B[..., i_bullet] - tau_B[..., i_rapid]


def stimatore_B(con, analisi, gruppo, opz, rng, reg, righe_csv):
    t0 = time.time()
    dati = DatiBlocchi(con, analisi, gruppo, opz)
    oss, n_coppie = dati.statistica(np.arange(dati.n))
    M_oss = {v: dati.somme_giocatore(*oss[v]) for v in oss}
    reg.scrivi(f"\nStimatore B: {dati.n:,} partite in {dati.nb:,} blocchi di {dati.n_gioc:,} giocatori; "
               f"coppie utilizzabili {n_coppie:,}; blocchi con almeno 2 coppie {int((oss['residuo'][0] > 0).sum()):,}")

    # Rimescolamenti: stessa statistica, risultati scambiati a caso dentro ogni blocco.
    # Schema principale: scambi solo tra partite dello stesso tipo di selezione (P11).
    # Schema "libero" (scambi tra tutte le partite del blocco): solo per confronto; se
    # le due stime differiscono, smettere e chiedere la rivincita dipendono dall'esito.
    K = opz.rimescolamenti
    M_rim = {v: np.zeros_like(M_oss[v]) for v in oss}
    M_lib = np.zeros_like(M_oss["residuo"])
    tau_rim = {v: np.empty((K, N_CELLE_B)) for v in oss}
    pend_rim = np.empty(K)
    for k in range(K):
        rim, _ = dati.statistica(dati.ordine_casuale(rng, entro_tipo=True))
        for v in oss:
            Mk = dati.somme_giocatore(*rim[v])
            M_rim[v] += Mk / K
            tau_k, pend_k = tau_e_pendenza(Mk.sum(axis=0))
            tau_rim[v][k] = tau_k
            if v == "residuo":
                pend_rim[k] = pend_k
        w_lib, num_lib, _, _ = dati.regressione(dati.ordine_casuale(rng, entro_tipo=False), 1)
        M_lib += dati.somme_giocatore(w_lib, num_lib) / K
        if (k + 1) % 50 == 0:
            print(f"  rimescolamento {k + 1}/{K} - {time.time() - t0:.0f} s")

    # Decadimento con la distanza (H1b), STIMA CONGIUNTA (P10): vedi somme_congiunte.
    # Non usa i rimescolamenti; intervalli dal bootstrap sui giocatori, p-value normale.
    # Generatore casuale a parte: aggiungere o togliere la stima congiunta non cambia
    # i numeri casuali usati dal resto dello script.
    M_c, coppie_c = dati.somme_congiunte(per_tipo=True)
    M_c1, _ = dati.somme_congiunte(per_tipo=False)
    tau_c = stime_congiunte(M_c.sum(axis=0))[0]
    tau_c1 = stime_congiunte(M_c1.sum(axis=0))[0]
    boot_c = stime_congiunte(bootstrap_somme(M_c, opz.bootstrap, np.random.default_rng([opz.seme, 10])))
    righe_c = []
    for j in range(N_DISTANZE):
        lo, hi, es = intervallo(boot_c[:, j])
        righe_c.append((f"partita +{j + 1}", coppie_c[j], 100 * tau_c[j], 100 * lo, 100 * hi, 100 * es,
                        p_normale(tau_c[j], es), 100 * tau_c1[j]))
    lo, hi, es = intervallo(boot_c[:, 0] - boot_c[:, 1])
    diff = tau_c[0] - tau_c[1]
    righe_c.append(("H1b: (+1) - (+2)", 0, 100 * diff, 100 * lo, 100 * hi, 100 * es, p_normale(diff, es),
                    100 * (tau_c1[0] - tau_c1[1])))
    tab_c = pd.DataFrame(righe_c, columns=["distanza", "coppie", "tau_pp", "ic95_da", "ic95_a", "err_std", "p",
                                           "tau_senza_tipi_pp"])

    # Regressioni SEPARATE per distanza, con rimescolamenti (come in P7): a +2 e +3 sono
    # distorte se c'e' un effetto vero a +1 (P10). Restano solo per confronto.
    versioni_d = ["residuo", "residuo_d2", "residuo_d3"]
    nc = M_oss["residuo"].shape[1]
    S = bootstrap_somme(np.hstack([np.hstack([M_oss[v], M_rim[v]]) for v in versioni_d]), opz.bootstrap, rng)
    righe_d, boot_d = [], []
    for j, v in enumerate(versioni_d):
        tau_oss, b, tau_B, _, _ = stime_B(M_oss[v].sum(axis=0), M_rim[v].sum(axis=0))
        tb = stime_B(S[:, 2 * nc * j:2 * nc * j + nc], S[:, 2 * nc * j + nc:2 * nc * (j + 1)])[2][:, 0]
        boot_d.append(tb)
        lo, hi, es = intervallo(tb)
        centro = tau_rim[v][:, 0].mean()
        p = (1 + (np.abs(tau_rim[v][:, 0] - centro) >= abs(tau_oss[0] - centro)).sum()) / (K + 1)
        righe_d.append((f"partita +{j + 1}", int((oss[v][0] > 0).sum()), 100 * b[0], 100 * tau_B[0], 100 * lo, 100 * hi, 100 * es, p))
    lo, hi, es = intervallo(boot_d[0] - boot_d[1])
    diff = righe_d[0][3] - righe_d[1][3]
    righe_d.append(("H1b: (+1) - (+2)", 0, np.nan, diff, 100 * lo, 100 * hi, 100 * es, p_normale(diff, 100 * es)))
    tab_d = pd.DataFrame(righe_d, columns=["distanza", "blocchi", "distorsione_b_pp", "tau_B_pp", "ic95_da", "ic95_a", "err_std", "p"])

    for v, titolo in (("residuo", "STIMATORE B (primario): regressione sul risultato inatteso della partita precedente"),
                      ("esito", "Stimatore B come pre-registrato (dopo sconfitta - dopo vittoria): DISTORTO dall'abbinamento, solo per confronto")):
        tau_oss, b, tau_B, pendenza_B, diff_cl = stime_B(M_oss[v].sum(axis=0), M_rim[v].sum(axis=0))
        # p-value di permutazione a due code: quanto spesso un ordine casuale da' una
        # statistica lontana dalla media dei rimescolamenti almeno quanto quella osservata.
        centro = tau_rim[v].mean(axis=0)
        p_perm = (1 + (np.abs(tau_rim[v] - centro) >= np.abs(tau_oss - centro)).sum(axis=0)) / (K + 1)
        # Bootstrap sui giocatori di tutta la procedura (osservato e correzione insieme)
        S = bootstrap_somme(np.hstack([M_oss[v], M_rim[v]]), opz.bootstrap, rng)
        nc = M_oss[v].shape[1]
        _, _, tau_boot, pend_boot, diff_boot = stime_B(S[:, :nc], S[:, nc:])
        lo, hi, es = intervallo(tau_boot)
        w = oss[v][0]
        blocchi_validi = [int((w > 0).sum())] + \
            [int(((w > 0) & (dati.classe_blk == i)).sum()) for i in range(len(CLASSI))] + \
            [int(((w > 0) & (dati.fascia_blk == i)).sum()) for i in range(len(FASCE_RATING))]
        tab = pd.DataFrame({
            "cella": NOMI_CELLE_B, "blocchi": blocchi_validi,
            "tau_dentro_blocco_pp": 100 * tau_oss, "distorsione_b_pp": 100 * b,
            "tau_B_pp": 100 * tau_B, "ic95_da": 100 * lo, "ic95_a": 100 * hi, "err_std": 100 * es, "p_permutazione": p_perm,
        })
        if v == "residuo":
            tab["tau_B_rim_libero_pp"] = 100 * stime_B(M_oss[v].sum(axis=0), M_lib.sum(axis=0))[2]
        reg.tabella(f"{titolo} - {K} rimescolamenti, {opz.bootstrap} ricampionamenti", tab.round(
            {"tau_dentro_blocco_pp": 2, "distorsione_b_pp": 2, "tau_B_pp": 2, "ic95_da": 2, "ic95_a": 2,
             "err_std": 2, "p_permutazione": 4, "tau_B_rim_libero_pp": 2}))
        etichetta = "B" if v == "residuo" else "B_preregistrato"
        for r in tab.itertuples():
            righe_csv.append((etichetta, r.cella, r.tau_B_pp, r.ic95_da, r.ic95_a, r.err_std, r.p_permutazione, r.blocchi))
        if v != "residuo":
            continue

        pend_oss = tau_e_pendenza(M_oss[v].sum(axis=0))[1]
        p_pend = (1 + (np.abs(pend_rim - pend_rim.mean()) >= abs(pend_oss - pend_rim.mean())).sum()) / (K + 1)
        lo_p, hi_p, es_p = intervallo(pend_boot)
        lo_d, hi_d, es_d = intervallo(diff_boot)
        extra = pd.DataFrame({
            "stima": ["H1d: pendenza di tau_B per +200 punti di rating", "H1c: tau_B bullet - tau_B rapid"],
            "valore_pp": [100 * pendenza_B, 100 * diff_cl], "ic95_da": [100 * lo_p, 100 * lo_d],
            "ic95_a": [100 * hi_p, 100 * hi_d], "err_std": [100 * es_p, 100 * es_d],
            "p": [p_pend, p_normale(diff_cl, es_d)], "tipo_p": ["permutazione", "normale"],
        })
        reg.tabella("Moderatori (stimatore B primario)", extra.round(4))
        reg.tabella("DECADIMENTO CON LA DISTANZA - stima congiunta (P10): effetto del risultato inatteso di 1, 2, 3 "
                    "partite prima, a parita' delle altre due; p-value normale",
                    tab_c.round({"tau_pp": 2, "ic95_da": 2, "ic95_a": 2, "err_std": 2, "p": 4, "tau_senza_tipi_pp": 2}))
        reg.scrivi("Termine di paragone: partite dello stesso blocco e dello stesso tipo, almeno 4 posti prima dell'esito. "
                   "tau_senza_tipi: paragone con tutte le partite lontane; se differisce, le regole di selezione "
                   "(smettere, chiedere la rivincita) contano.")
        for r in tab_c.itertuples():
            righe_csv.append(("B_distanza", r.distanza, r.tau_pp, r.ic95_da, r.ic95_a, r.err_std, r.p, r.coppie))
        reg.tabella("Regressioni separate per distanza, con rimescolamenti (versione di P7): a +2 e +3 DISTORTE "
                    "se c'e' un effetto vero a +1, solo per confronto",
                    tab_d.round({"distorsione_b_pp": 2, "tau_B_pp": 2, "ic95_da": 2, "ic95_a": 2, "err_std": 2, "p": 4}))
        for r in tab_d.itertuples():
            righe_csv.append(("B_distanza_separata", r.distanza, r.tau_B_pp, r.ic95_da, r.ic95_a, r.err_std, r.p, r.blocchi))
        for r in extra.itertuples():
            righe_csv.append(("B", r.stima, r.valore_pp, r.ic95_da, r.ic95_a, r.err_std, r.p, np.nan))

        # Controllo: stessa stima dando lo stesso peso a ogni GIOCATORE (non a ogni partita),
        # per escludere che pochi giocatori molto attivi decidano il risultato.
        W0, N0 = M_oss[v][:, 0], M_oss[v][:, N_CELLE_B]
        Wr, Nr = M_rim[v][:, 0], M_rim[v][:, N_CELLE_B]
        tieni = (W0 >= opz.peso_min_giocatore) & (Wr > 0)
        a = N0[tieni] / W0[tieni] - Nr[tieni] / Wr[tieni]        # tau osservato - distorsione, per giocatore
        c = 1 - Nr[tieni] / Wr[tieni]                            # fattore (1 - b), per giocatore
        Sg = bootstrap_somme(np.column_stack([a, c]), opz.bootstrap, rng)
        lo_g, hi_g, es_g = intervallo(Sg[:, 0] / Sg[:, 1])
        stima_g = a.mean() / c.mean()
        reg.scrivi(f"\nStimatore B con peso uguale per giocatore ({int(tieni.sum()):,} giocatori con peso >= {opz.peso_min_giocatore}): "
                   f"{100 * stima_g:.2f} pp  [IC95 {100 * lo_g:.2f}, {100 * hi_g:.2f}]")
        righe_csv.append(("B", "tutte, peso uguale per giocatore", 100 * stima_g, 100 * lo_g, 100 * hi_g, 100 * es_g, np.nan, int(tieni.sum())))
    reg.scrivi(f"(stimatore B: {time.time() - t0:.0f} s)")


# --------------------------------------------------------------------------
# Stime "differenza di due medie" da somme per giocatore (stimatore A e affini)
# --------------------------------------------------------------------------
def differenze_con_bootstrap(df, celle, opz, rng, contrasti=()):
    """df: una riga per (giocatore, gruppo di righe) con le somme sL, nL, sW, nW.
    celle: lista di (nome, maschera sulle righe di df).
    Stima per cella: sL/nL - sW/nW, cioe' media dopo sconfitta - media dopo vittoria.
    contrasti: lista di (nome, cella_1, cella_2) -> differenza tra due celle, con lo
    stesso ricampionamento (cosi' l'intervallo tiene conto che condividono i giocatori).
    """
    giocatori, indice = np.unique(df["gid"].to_numpy(), return_inverse=True)
    n, nc = len(giocatori), len(celle)
    M = np.zeros((n, 4 * nc))
    for j, (_, maschera) in enumerate(celle):
        m = np.asarray(maschera)
        for k, col in enumerate(("sL", "nL", "sW", "nW")):
            M[:, 4 * j + k] = np.bincount(indice[m], weights=df[col].to_numpy()[m].astype(np.float64), minlength=n)

    def stima(S):
        with np.errstate(divide="ignore", invalid="ignore"):
            return S[..., 0::4] / S[..., 1::4] - S[..., 2::4] / S[..., 3::4]

    tot = M.sum(axis=0)
    valore = stima(tot)
    boot = stima(bootstrap_somme(M, opz.bootstrap, rng))
    pochi = (tot[1::4] < N_MIN_CELLA) | (tot[3::4] < N_MIN_CELLA)
    valore[pochi] = np.nan
    boot[:, pochi] = np.nan
    with np.errstate(all="ignore"), __import__("warnings").catch_warnings():
        __import__("warnings").simplefilter("ignore")
        lo, hi, es = intervallo(boot)
    tab = pd.DataFrame({"cella": [c[0] for c in celle], "n_dopo_sconfitta": tot[1::4].astype(np.int64),
                        "n_dopo_vittoria": tot[3::4].astype(np.int64), "valore": valore,
                        "ic95_da": lo, "ic95_a": hi, "err_std": es})
    nomi = [c[0] for c in celle]
    for nome, c1, c2 in contrasti:
        j1, j2 = nomi.index(c1), nomi.index(c2)
        lo_c, hi_c, es_c = intervallo(boot[:, j1] - boot[:, j2])
        tab.loc[len(tab)] = [nome, 0, 0, valore[j1] - valore[j2], lo_c, hi_c, es_c]
    tab["p"] = [p_normale(v, e) for v, e in zip(tab["valore"], tab["err_std"])]
    # Peso uguale per giocatore (prima cella): media delle differenze individuali
    ok = (M[:, 1] >= 5) & (M[:, 3] >= 5)
    if ok.sum() < 2:
        return tab, (np.nan, np.nan, int(ok.sum()))
    per_giocatore = M[ok, 0] / M[ok, 1] - M[ok, 2] / M[ok, 3]
    return tab, (per_giocatore.mean(), per_giocatore.std(ddof=1) / np.sqrt(ok.sum()), int(ok.sum()))


def filtri_comuni(gruppo, opz, con_lato=True):
    f = f"gruppo = '{gruppo}' AND elig AND {opz.col_stabile}"
    if con_lato and not opz.due_lati:
        f += " AND lato_scelto"
    if opz.senza_corte:
        f += " AND NOT corta AND NOT COALESCE(prec_corta, FALSE)"
    return f


def stimatore_A(con, analisi, gruppo, opz, rng, reg, righe_csv):
    col_y, col_base = ("y_cor", "base_altre_cor") if opz.rating == "corrente" else ("y", "base_altre")
    diverso = lambda col: "TRUE" if opz.rivincite else f"avv <> {col}"
    soglia_s = opz.soglia * 60
    fascia_pausa = f"""CASE WHEN pausa_s <= 15 THEN 0 WHEN pausa_s <= 60 THEN 1 WHEN pausa_s <= 300 THEN 2
                            WHEN pausa_s <= {soglia_s} THEN 3 WHEN pausa_s <= 21600 THEN 4 ELSE 5 END"""
    base = f"FROM {analisi} WHERE {filtri_comuni(gruppo, opz)}"
    # Ogni SELECT definisce un tipo di coppia: "cond" e' l'esito precedente (0 o 1), "val" l'esito corretto.
    coppie = f"""
        SELECT gid, 'd1' AS tipo, classe, {SQL_FASCIA_RATING} AS fr, {fascia_pausa} AS fp,
               prec_punteggio AS cond, {col_y} - {col_base} AS val
        {base} AND pos_blocco > 1 AND {diverso('prec_avv')}
        UNION ALL
        SELECT gid, 'd1_senza_base', classe, 0, 0, prec_punteggio, {col_y}
        {base} AND pos_blocco > 1 AND {diverso('prec_avv')}
        UNION ALL
        SELECT gid, 'd2', classe, 0, 0, prec2_punteggio, {col_y} - {col_base}
        {base} AND pos_blocco > 2 AND {diverso('prec2_avv')}
        UNION ALL
        SELECT gid, 'd3', classe, 0, 0, prec3_punteggio, {col_y} - {col_base}
        {base} AND pos_blocco > 3 AND {diverso('prec3_avv')}
        UNION ALL
        SELECT gid, 'x', classe, {SQL_FASCIA_RATING}, {fascia_pausa}, prec_punteggio, y_x - base_x
        {base} AND coppia_x AND {diverso('prec_avv')}
    """
    df = con.execute(f"""
        SELECT gid, tipo, classe, fr, fp,
               COALESCE(SUM(CASE WHEN cond = 0 THEN val END), 0) AS sL, COUNT(CASE WHEN cond = 0 THEN val END) AS nL,
               COALESCE(SUM(CASE WHEN cond = 1 THEN val END), 0) AS sW, COUNT(CASE WHEN cond = 1 THEN val END) AS nW
        FROM ({coppie}) WHERE val IS NOT NULL AND cond IN (0, 1)
        GROUP BY ALL
    """).df()
    d1, x = df["tipo"] == "d1", df["tipo"] == "x"
    celle = [("H1a: stessa sessione, partita +1", d1)]
    celle += [(f"classe {c}", d1 & (df["classe"] == c)) for c in CLASSI]
    celle += [(f"rating {f}", d1 & (df["fr"] == i)) for i, f in enumerate(FASCE_RATING)]
    celle += [(f"pausa {FASCE_PAUSA[i]}", d1 & (df["fp"] == i)) for i in range(4)]
    celle += [("pausa fino a 5 min", d1 & (df["fp"] <= 2)),
              ("CONTROLLO NEGATIVO: oltre la soglia (altra sessione)", x),
              (f"pausa {FASCE_PAUSA[4]}", x & (df["fp"] == 4)), (f"pausa {FASCE_PAUSA[5]}", x & (df["fp"] == 5)),
              ("distanza +2 (stesso blocco)", df["tipo"] == "d2"), ("distanza +3 (stesso blocco)", df["tipo"] == "d3"),
              ("senza base del giocatore (confronto quasi ingenuo)", df["tipo"] == "d1_senza_base")]
    contrasti = [("H1b: pausa fino a 5 min - controllo negativo", "pausa fino a 5 min",
                  "CONTROLLO NEGATIVO: oltre la soglia (altra sessione)"),
                 ("H1c: bullet - rapid", "classe bullet", "classe rapid")]
    tab, (media_g, es_g, n_g) = differenze_con_bootstrap(df, celle, opz, rng, contrasti)
    for col in ("valore", "ic95_da", "ic95_a", "err_std"):
        tab[col] = 100 * tab[col]
    reg.tabella("STIMATORE A (tra sessioni): tau in pp = dopo sconfitta - dopo vittoria",
                tab.round({"valore": 2, "ic95_da": 2, "ic95_a": 2, "err_std": 2, "p": 4}))
    reg.scrivi(f"\nStimatore A, H1a con peso uguale per giocatore ({n_g:,} giocatori con almeno 5 + 5 coppie): "
               f"{100 * media_g:.2f} pp  (errore standard {100 * es_g:.2f})")
    for r in tab.itertuples():
        righe_csv.append(("A", r.cella, r.valore, r.ic95_da, r.ic95_a, r.err_std, r.p, r.n_dopo_sconfitta + r.n_dopo_vittoria))


def fotofinish(con, analisi, gruppo, opz, rng, reg, righe_csv):
    """Verifica causale 1: partite senza incremento perse per tempo con il vincitore a pochi secondi.

    Chi vince e chi perde hanno giocato la STESSA partita (stessa durata, ora, tensione)
    e l'esito e' quasi un lancio di moneta: confronto la loro partita successiva.
    Qui uso entrambi i lati: perdente e vincitore giocano poi partite diverse.
    """
    filtro = f"{filtri_comuni(gruppo, opz, con_lato=False)} AND pos_blocco > 1 AND avv <> prec_avv AND prec_punteggio IN (0, 1)"
    df = con.execute(f"""
        SELECT gid, classe,
               (prec_clk_fin_vinc <= 3) AS entro3, COALESCE(prec_clk_fin_perd <= 10, FALSE) AS perd10,
               COALESCE(SUM(CASE WHEN prec_punteggio = 0 THEN y - base_altre END), 0) AS sL, COUNT(CASE WHEN prec_punteggio = 0 THEN y - base_altre END) AS nL,
               COALESCE(SUM(CASE WHEN prec_punteggio = 1 THEN y - base_altre END), 0) AS sW, COUNT(CASE WHEN prec_punteggio = 1 THEN y - base_altre END) AS nW
        FROM {analisi} WHERE {filtro} AND prec_clk_fin_vinc <= 5 AND base_altre IS NOT NULL
        GROUP BY ALL
    """).df()
    if len(df) == 0:
        reg.scrivi("\nFotofinish: nessuna coppia disponibile.")
        return
    celle = [("fotofinish: vincitore entro 3 s", df["entro3"]),
             ("robustezza: vincitore entro 5 s", np.ones(len(df), dtype=bool)),
             ("robustezza: entro 3 s e perdente entro 10 s", df["entro3"] & df["perd10"])]
    celle += [(f"entro 3 s, classe {c}", df["entro3"] & (df["classe"] == c)) for c in CLASSI]
    tab, _ = differenze_con_bootstrap(df, celle, opz, rng)
    for col in ("valore", "ic95_da", "ic95_a", "err_std"):
        tab[col] = 100 * tab[col]
    reg.tabella("VERIFICA CAUSALE 1 - finali al fotofinish: tau in pp nella partita successiva "
                "(perdente - vincitore, ciascuno rispetto alla propria base)",
                tab.round({"valore": 2, "ic95_da": 2, "ic95_a": 2, "err_std": 2, "p": 4}))
    for r in tab.itertuples():
        righe_csv.append(("fotofinish", r.cella, r.valore, r.ic95_da, r.ic95_a, r.err_std, r.p, r.n_dopo_sconfitta + r.n_dopo_vittoria))

    # Bilanciamento: PRIMA del fotofinish, perdenti e vincitori erano simili?
    # g = la riga della partita al fotofinish (G), n = la riga della partita successiva.
    bil = con.execute(f"""
        WITH n AS (SELECT gid, prec_game_id, prec_punteggio FROM {analisi}
                   WHERE {filtro} AND prec_clk_fin_vinc <= 3 AND base_altre IS NOT NULL)
        SELECT CASE WHEN n.prec_punteggio = 0 THEN 'perdenti' ELSE 'vincitori' END AS chi, COUNT(*) AS n,
               AVG(g.elo - g.elo_avv) AS vantaggio_rating, STDDEV(g.elo - g.elo_avv) AS sd_vantaggio,
               AVG(g.atteso) AS atteso_in_G, STDDEV(g.atteso) AS sd_atteso,
               AVG(g.rating_rif) AS rating, STDDEV(g.rating_rif) AS sd_rating,
               AVG(g.pos) AS posizione_sessione, STDDEV(g.pos) AS sd_pos,
               AVG(g.base_altre) * 100 AS base_pp, STDDEV(g.base_altre) * 100 AS sd_base,
               AVG(g.prec_punteggio) AS punteggio_prima_di_G, STDDEV(g.prec_punteggio) AS sd_prima
        FROM n JOIN {analisi} g ON g.gid = n.gid AND g.game_id = n.prec_game_id
        GROUP BY 1 ORDER BY 1
    """).df()
    if len(bil) == 2:
        righe = []
        for media, sd in (("vantaggio_rating", "sd_vantaggio"), ("atteso_in_G", "sd_atteso"), ("rating", "sd_rating"),
                          ("posizione_sessione", "sd_pos"), ("base_pp", "sd_base"), ("punteggio_prima_di_G", "sd_prima")):
            p, v = bil[media].iloc[0], bil[media].iloc[1]
            sd_comune = np.sqrt((bil[sd].iloc[0] ** 2 + bil[sd].iloc[1] ** 2) / 2)
            righe.append((media, p, v, (p - v) / sd_comune if sd_comune > 0 else np.nan))
        reg.tabella(f"Bilanciamento prima del fotofinish (perdenti n={bil['n'].iloc[0]:,}, vincitori n={bil['n'].iloc[1]:,}); "
                    "differenza standardizzata: sotto 0,1 in valore assoluto = gruppi simili",
                    pd.DataFrame(righe, columns=["variabile", "perdenti", "vincitori", "diff_standardizzata"]).round(3))


def stanchezza_e_interruzione(con, analisi, gruppo, opz, rng, reg, righe_csv):
    # Curva della stanchezza: residuo medio (prima della correzione) per posizione nella sessione.
    df = con.execute(f"""
        SELECT gid, classe, fascia_pos, SUM(resid) AS sL, COUNT(resid) AS nL, 0.0 AS sW, 1000 AS nW
        FROM {analisi} WHERE {filtri_comuni(gruppo, opz)} AND resid IS NOT NULL GROUP BY ALL
    """).df()
    nomi_pos = ["1", "2", "3", "4-5", "6-10", "11-20", "21+"]
    celle = [(f"{c}, partita {nomi_pos[i]}", (df["classe"] == c) & (df["fascia_pos"] == i + 1))
             for c in CLASSI for i in range(7)]
    tab, _ = differenze_con_bootstrap(df, celle, opz, rng)
    tab = tab.drop(columns=["n_dopo_vittoria", "p"]).rename(columns={"n_dopo_sconfitta": "partite", "valore": "residuo_pp"})
    for col in ("residuo_pp", "ic95_da", "ic95_a", "err_std"):
        tab[col] = 100 * tab[col]
    reg.tabella("Curva della stanchezza: residuo medio per posizione nella sessione (pp)", tab.round(2))
    for r in tab.itertuples():
        righe_csv.append(("stanchezza", r.cella, r.residuo_pp, r.ic95_da, r.ic95_a, r.err_std, np.nan, r.partite))

    # Selezione: dopo una sconfitta si chiude la sessione piu' spesso che dopo una vittoria?
    # Escludo le ultime ore del mese, dove non si puo' sapere se la sessione continua.
    t_max = con.execute(f"SELECT MAX(t_inizio) FROM {analisi}").fetchone()[0]
    df = con.execute(f"""
        SELECT gid, classe,
               SUM(CASE WHEN punteggio = 0 THEN (pos = n_sessione)::INTEGER ELSE 0 END) AS sL, SUM((punteggio = 0)::INTEGER) AS nL,
               SUM(CASE WHEN punteggio = 1 THEN (pos = n_sessione)::INTEGER ELSE 0 END) AS sW, SUM((punteggio = 1)::INTEGER) AS nW
        FROM {analisi}
        WHERE {filtri_comuni(gruppo, opz, con_lato=False)} AND punteggio IN (0, 1) AND t_inizio < {t_max} - 6 * 3600
        GROUP BY ALL
    """).df()
    celle = [("tutte le classi", np.ones(len(df), dtype=bool))] + [(f"classe {c}", df["classe"] == c) for c in CLASSI]
    tab, _ = differenze_con_bootstrap(df, celle, opz, rng)
    tot = df[["sL", "nL", "sW", "nW"]].sum()
    for col in ("valore", "ic95_da", "ic95_a", "err_std"):
        tab[col] = 100 * tab[col]
    reg.tabella(f"Selezione: probabilita' di chiudere la sessione dopo sconfitta ({100 * tot.sL / tot.nL:.1f}%) "
                f"- dopo vittoria ({100 * tot.sW / tot.nW:.1f}%), differenza in pp", tab.round(2))
    for r in tab.itertuples():
        righe_csv.append(("interruzione", r.cella, r.valore, r.ic95_da, r.ic95_a, r.err_std, np.nan, r.n_dopo_sconfitta + r.n_dopo_vittoria))

    # Selezione: dopo una sconfitta si gioca la rivincita piu' spesso che dopo una vittoria?
    # Dice quanto contano i tipi di selezione (P11): le rivincite non fanno da esito.
    df = con.execute(f"""
        SELECT gid, classe,
               SUM(CASE WHEN prec_punteggio = 0 THEN (avv = prec_avv)::INTEGER ELSE 0 END) AS sL, SUM((prec_punteggio = 0)::INTEGER) AS nL,
               SUM(CASE WHEN prec_punteggio = 1 THEN (avv = prec_avv)::INTEGER ELSE 0 END) AS sW, SUM((prec_punteggio = 1)::INTEGER) AS nW
        FROM {analisi}
        WHERE {filtri_comuni(gruppo, opz, con_lato=False)} AND pos_blocco > 1 AND prec_punteggio IN (0, 1)
        GROUP BY ALL
    """).df()
    celle = [("tutte le classi", np.ones(len(df), dtype=bool))] + [(f"classe {c}", df["classe"] == c) for c in CLASSI]
    tab, _ = differenze_con_bootstrap(df, celle, opz, rng)
    tot = df[["sL", "nL", "sW", "nW"]].sum()
    for col in ("valore", "ic95_da", "ic95_a", "err_std"):
        tab[col] = 100 * tab[col]
    reg.tabella(f"Selezione: probabilita' che la partita seguente dello stesso blocco sia una rivincita, dopo sconfitta "
                f"({100 * tot.sL / max(tot.nL, 1):.1f}%) - dopo vittoria ({100 * tot.sW / max(tot.nW, 1):.1f}%), differenza in pp", tab.round(2))
    for r in tab.itertuples():
        righe_csv.append(("rivincita", r.cella, r.valore, r.ic95_da, r.ic95_a, r.err_std, np.nan, r.n_dopo_sconfitta + r.n_dopo_vittoria))


def main():
    parser = argparse.ArgumentParser(description="Stimatori del tilt (domanda 1)")
    parser.add_argument("--gruppo", choices=["esplorazione", "conferma"], default="esplorazione")
    parser.add_argument("--codice-bloccato", action="store_true",
                        help="obbligatorio con --gruppo conferma: dichiari che il codice non cambiera' piu'")
    parser.add_argument("--rimescolamenti", type=int, default=200)
    parser.add_argument("--bootstrap", type=int, default=1000)
    parser.add_argument("--seme", type=int, default=20170501)
    parser.add_argument("--memoria", default="3GB")
    # Varianti di robustezza
    parser.add_argument("--soglia", type=int, default=30, help="soglia di sessione in minuti (serve 05 e 06 con la stessa soglia)")
    parser.add_argument("--rivincite", action="store_true", help="include le rivincite")
    parser.add_argument("--rating", choices=["riferimento", "corrente"], default="riferimento")
    parser.add_argument("--due-lati", action="store_true", help="usa entrambi i giocatori di ogni partita come esito")
    parser.add_argument("--senza-corte", action="store_true", help="esclude partite sotto 10 semimosse e Abandoned")
    parser.add_argument("--stabile", choices=["base", "largo", "stretto"], default="base")
    parser.add_argument("--peso-min-giocatore", type=float, default=2.0,
                        help="peso minimo (circa 8 coppie) per entrare nella stima a peso uguale per giocatore")
    opz = parser.parse_args()
    opz.col_stabile = {"base": "stabile", "largo": "stabile_largo", "stretto": "stabile_stretto"}[opz.stabile]

    if opz.gruppo == "conferma" and not opz.codice_bloccato:
        sys.exit("Il gruppo di conferma si analizza UNA volta sola, a codice bloccato.\n"
                 "Se il codice e' definitivo (commit fatto), rilancia aggiungendo --codice-bloccato")

    variante = "".join([f"_s{opz.soglia}" if opz.soglia != 30 else "", "_rivincite" if opz.rivincite else "",
                        "_ratingcorrente" if opz.rating == "corrente" else "", "_duelati" if opz.due_lati else "",
                        "_senzacorte" if opz.senza_corte else "", f"_{opz.stabile}" if opz.stabile != "base" else ""])
    suffisso = f"_s{opz.soglia}" if opz.soglia != 30 else ""
    analisi = f"read_parquet('{(CARTELLA_DATI / f'analisi{suffisso}').as_posix()}/*.parquet')"
    reg = Registro(f"08_tilt_{opz.gruppo}{variante}")
    reg.scrivi(f"Gruppo: {opz.gruppo} | variante: {variante or 'principale'} | seme {opz.seme}")
    con = apri_duckdb(opz.memoria)
    rng = np.random.default_rng(opz.seme)
    righe_csv = []
    inizio = time.time()

    stimatore_B(con, analisi, opz.gruppo, opz, rng, reg, righe_csv)
    stimatore_A(con, analisi, opz.gruppo, opz, rng, reg, righe_csv)
    fotofinish(con, analisi, opz.gruppo, opz, rng, reg, righe_csv)
    stanchezza_e_interruzione(con, analisi, opz.gruppo, opz, rng, reg, righe_csv)

    file_csv = CARTELLA_OUTPUT / f"08_stime_{opz.gruppo}{variante}.csv"
    pd.DataFrame(righe_csv, columns=["analisi", "cella", "stima_pp", "ic95_da", "ic95_a", "err_std", "p", "n"]).to_csv(file_csv, index=False)
    reg.scrivi(f"\nStime salvate in {file_csv} - tempo totale {(time.time() - inizio) / 60:.1f} minuti")
    reg.chiudi()


if __name__ == "__main__":
    main()
