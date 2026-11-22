"""
11_pressione.py - Domanda 2: con poco tempo sull'orologio si sbaglia di piu'? (H2a, H2b)

Unita': la mossa, nelle partite con valutazioni del motore e SENZA incremento.
Esito: errore grave (perdita di almeno 15 punti di Win%, giudizio = 3 in 07_mosse.py);
in parallelo la perdita media di Win% per mossa.
Esposizione: tempo residuo prima di pensare (clk_prima), in 8 fasce:
    <3, 3-5, 5-10, 10-20, 20-40, 40-80, 80-160, >=160 secondi.

Il confronto e' DENTRO la stessa partita e lo stesso giocatore (la "coppia"), a parita'
di fase (numero di mossa, catture gia' avvenute) e di equilibrio (Win% prima della
mossa): 6 x 7 x 7 = 294 strati.

Due modelli (precisazione P13):

  MOLTIPLICATIVO (primario). Probabilita' di errore grave della mossa =
        a[coppia] * B[fascia di tempo] * C[strato]
    B[k] / B[riferimento] e' il rapporto di rischio (RR): quante volte piu' spesso si
    sbaglia nella fascia k, nella stessa partita e nello stesso tipo di posizione.
    "Tolgo la media della coppia" qui vuol dire: ogni coppia ha il SUO livello di
    errore a[coppia], e il tempo lo moltiplica. E' un modello di Poisson a effetti
    fissi; e' corretto anche se gli errori non seguono una Poisson, basta che la
    media abbia quella forma.

  ADDITIVO (come nel piano: "sottraggo la media della coppia partita-giocatore").
        errore grave = a[coppia] + beta[fascia] + gamma[strato]
    Resta in tabella, in punti percentuali. Sui dati simulati SENZA alcun effetto del
    tempo da' un falso aumento (+0,3 / +0,7 pp) quando le coppie hanno livelli di
    errore diversi (chi sbaglia di piu' peggiora di piu' anche in valore assoluto col
    passare delle mosse): per questo non e' il modello primario.

Test confermativi (sul BLITZ, come nel piano):
  H2a  log RR "meno di 10 secondi" contro "10 secondi o piu'", tutti i livelli.
  H2b  pendenza di quel log RR sulle 5 fasce di livello (per fascia, circa 200 punti).
Intervalli e p: bootstrap a grappolo sui giocatori. Si ricampionano i CONTRIBUTI di
ogni giocatore alla stima (la sua somma di "mossa per mossa: osservato meno previsto",
trasformata dalle equazioni del modello): costa poco e tiene conto anche
dell'incertezza sugli strati.

Collaudo su mosse simulate (tests/simula_mosse.py, tests/collaudo_11.py; numeri in P13):
  - senza alcun effetto del tempo il log RR primario sta tra -0,06 e +0,03 (RR tra
    0,94 e 1,03): per questo il verdetto chiede che l'intervallo del RR stia oltre 1,10;
  - con un effetto vero il log RR e' schiacciato verso zero del 5-25% (prudente);
  - la pendenza per livello (H2b) ha un errore fino a +0,035, nel verso contrario
    all'ipotesi; l'additivo senza effetto da' +0,3 / +0,7 pp; il confronto tra i due
    giocatori nella stessa finestra da' +0,1 di log RR senza effetto se chi pensa di
    piu' sbaglia di piu': e' una robustezza debole, da leggere solo nel segno.
Limite dichiarato nel piano: una posizione difficile fa consumare tempo e resta
difficile. Nessuna stima e' causale.

Uso (PowerShell, nella cartella C:\\tilt):
    .\\.venv\\Scripts\\python 11_pressione.py                       (gruppo esplorazione)
    .\\.venv\\Scripts\\python 11_pressione.py --gruppo conferma --codice-bloccato
Robustezza (una variante alla volta):  --senza-tornei | --stabile
"""

import argparse
import math
import sys
import time

import numpy as np
import pandas as pd

from tilt_utils import CARTELLA_DATI, CARTELLA_OUTPUT, CLASSI, Registro, apri_duckdb

SOGLIE_TEMPO = [3, 5, 10, 20, 40, 80, 160]
FASCE_TEMPO = ["<3 s", "3-5 s", "5-10 s", "10-20 s", "20-40 s", "40-80 s", "80-160 s", ">=160 s"]
K = len(FASCE_TEMPO)
RIF = 4                                   # fascia di riferimento delle curve: 20-40 s (esiste in ogni classe)
SOTTO_10 = np.array([0, 0, 0, 1, 1, 1, 1, 1])   # 0 = meno di 10 secondi, 1 = 10 secondi o piu'
SOGLIE_MOSSA = [11, 21, 31, 41, 51]       # numero di mossa del giocatore: 1-10, 11-20, ..., 51+
SOGLIE_CATTURE = [4, 8, 12, 16, 20, 24]   # catture gia' avvenute: 0-3, 4-7, ..., 24+
SOGLIE_WIN = [15, 30, 45, 55, 70, 85]     # Win% prima della mossa; sotto 15 l'errore grave e' impossibile
N_STRATI = (len(SOGLIE_MOSSA) + 1) * (len(SOGLIE_CATTURE) + 1) * (len(SOGLIE_WIN) + 1)
SOGLIE_RATING = [1400, 1600, 1800, 2000]
FASCE_RATING = ["<1400", "1400-1599", "1600-1799", "1800-1999", ">=2000"]
PESI_PENDENZA = np.array([-2.0, -1.0, 0.0, 1.0, 2.0]) / 10.0   # pendenza ai minimi quadrati su 5 punti equidistanti
N_MIN_ERRORI = 200                        # errori gravi minimi sotto i 10 secondi per riportare un RR
# Regole di lettura (P13), fissate prima di qualsiasi esecuzione sui dati veri
RR_RILEVANTE = 1.10                       # H2a confermata solo se l'IC95 del RR sta tutto sopra 1,10 (smentita: tutto sotto 0,90)
MARGINE_H2B = 0.04                        # H2b smentita solo se l'IC95 della pendenza sta tutto sopra +0,04
# p-value dei quattro test confermativi della domanda 1 (output/08_tilt_conferma.txt, RISULTATI.md):
# servono solo per scrivere la tabella di Holm sulla famiglia dei sei test.
P_DOMANDA_1 = {"H1a": 0.42, "H1b": 0.94, "H1c": 0.0009, "H1d": 0.49}


def sql_fasce(colonna, soglie):
    """CASE SQL: 0 se colonna < soglie[0], 1 se < soglie[1], ..., len(soglie) altrimenti."""
    return "CASE " + " ".join(f"WHEN {colonna} < {s} THEN {i}" for i, s in enumerate(soglie)) + f" ELSE {len(soglie)} END"


# --------------------------------------------------------------------------
# p-value e intervalli (come in 08_tilt.py)
# --------------------------------------------------------------------------
def p_normale(stima, err_std):
    """p-value a due code da stima / errore standard (approssimazione normale)."""
    if not np.isfinite(stima) or not np.isfinite(err_std) or err_std <= 0:
        return np.nan
    return math.erfc(abs(stima / err_std) / math.sqrt(2))


def intervallo(valori):
    """Intervallo al 95% (percentili 2,5 e 97,5 dei ricampionamenti) ed errore standard."""
    return np.nanpercentile(valori, 2.5, axis=0), np.nanpercentile(valori, 97.5, axis=0), np.nanstd(valori, axis=0)


# --------------------------------------------------------------------------
# Nucleo numerico: modelli con un effetto per coppia partita-giocatore
# --------------------------------------------------------------------------
def somma_coppie(gruppo_nz, col_nz, val_nz, peso_gruppo, J, blocco=4_000_000):
    """Somma su tutti i gruppi di peso_g * c_g c_g', con c_g vettore sparso di lunghezza J.

    (gruppo_nz, col_nz, val_nz) sono gli elementi non nulli, ordinati per gruppo.
    Tratto insieme i gruppi con lo stesso numero r di elementi: ognuno da' r x r prodotti.
    """
    S = np.zeros(J * J)
    if len(gruppo_nz) == 0:
        return S.reshape(J, J)
    inizio = np.flatnonzero(np.r_[True, gruppo_nz[1:] != gruppo_nz[:-1]])
    quanti = np.diff(np.r_[inizio, len(gruppo_nz)])
    for r in np.unique(quanti):
        ini = inizio[quanti == r]
        passo = max(1, blocco // (r * r))
        for a in range(0, len(ini), passo):
            righe = ini[a:a + passo, None] + np.arange(r)[None, :]
            c, v = col_nz[righe], val_nz[righe]
            w = peso_gruppo[gruppo_nz[ini[a:a + passo]]]
            indice = (c[:, :, None] * J + c[:, None, :]).ravel()
            pesi = (v[:, :, None] * v[:, None, :] * w[:, None, None]).ravel()
            S += np.bincount(indice, weights=pesi, minlength=J * J)
    return S.reshape(J, J)


class Struttura:
    """Le mosse di una cella di analisi.

    gruppo = cio' di cui si toglie il livello (la coppia partita-giocatore);
    fascia = fascia di tempo residuo (0..K-1); strato = tipo di posizione (0..S-1);
    gioc = indice del giocatore (0..n_gioc-1), per il bootstrap.
    """

    def __init__(self, gruppo, fascia, strato, gioc, n_gioc, n_fasce, n_strati):
        _, gruppo = np.unique(gruppo, return_inverse=True)
        self.K, self.S, self.J = n_fasce, n_strati, n_fasce + n_strati
        self.n, self.ng, self.n_gioc = len(gruppo), int(gruppo.max()) + 1, n_gioc
        # Interi a 32 bit per risparmiare memoria: controllo che le chiavi composte ci stiano
        assert self.ng * max(self.K, self.S) < 2 ** 31 and n_gioc * self.J < 2 ** 31, "troppi gruppi per gli interi a 32 bit"
        # elementi non nulli della tabella gruppo x strato (np.unique li ordina per gruppo)
        unici, inv_nz = np.unique(gruppo * self.S + strato, return_inverse=True)
        self.g_nz, self.s_nz, self.inv_nz = unici // self.S, unici % self.S, inv_nz.astype(np.int32)
        self.gruppo, self.fascia = gruppo.astype(np.int32), fascia.astype(np.int32, copy=False)
        self.strato, self.gioc = strato.astype(np.int32, copy=False), gioc.astype(np.int32, copy=False)

    def normali(self, w=None):
        """Matrice delle equazioni normali per le dummy di fascia (K) e di strato (S),
        dopo aver tolto la media (pesata con w) di ogni gruppo:
            N = Z' W Z - somma_g (1 / W_g) c_g c_g',    c_g = somma_m w_m z_m
        Con w = 1 e' la regressione a effetti fissi; con w = errori attesi e' la
        matrice d'informazione del modello moltiplicativo.
        """
        K, S = self.K, self.S
        w = np.ones(self.n) if w is None else w
        Wg = np.bincount(self.gruppo, weights=w, minlength=self.ng)
        inv = np.where(Wg > 0, 1.0 / np.where(Wg > 0, Wg, 1.0), 0.0)
        cb = np.bincount(self.gruppo * K + self.fascia, weights=w, minlength=self.ng * K).reshape(self.ng, K)
        v_nz = np.bincount(self.inv_nz, weights=w, minlength=len(self.g_nz))
        N = np.zeros((self.J, self.J))
        N[:K, :K] = np.diag(cb.sum(axis=0)) - (cb * inv[:, None]).T @ cb
        N[:K, K:] = np.bincount(self.fascia * S + self.strato, weights=w, minlength=K * S).reshape(K, S)
        for k in range(K):
            N[k, K:] -= np.bincount(self.s_nz, weights=v_nz * inv[self.g_nz] * cb[self.g_nz, k], minlength=S)
        N[K:, :K] = N[:K, K:].T
        tieni = v_nz > 0
        N[K:, K:] = np.diag(np.bincount(self.strato, weights=w, minlength=S)) \
            - somma_coppie(self.g_nz[tieni], self.s_nz[tieni], v_nz[tieni], inv, S)
        return N

    def somme_z(self, v):
        """Z' v: somma di v per fascia e per strato."""
        return np.r_[np.bincount(self.fascia, weights=v, minlength=self.K), np.bincount(self.strato, weights=v, minlength=self.S)]

    def contributi(self, residuo, Q):
        """Matrice giocatori x colonne di Q: per ogni giocatore, somma sulle sue mosse di residuo_m * (z_m' Q).

        z_m sono le dummy della mossa (la sua fascia e il suo strato), Q ha J righe. Calcolo
        z_m' Q mossa per mossa, cosi' non serve mai una matrice giocatori x J (con 100.000
        giocatori e 302 colonne sarebbero 240 MB).
        """
        out = np.empty((self.n_gioc, Q.shape[1]))
        for j in range(Q.shape[1]):
            peso = residuo * (Q[self.fascia, j] + Q[self.K + self.strato, j])
            out[:, j] = np.bincount(self.gioc, weights=peso, minlength=self.n_gioc)
        return out


def aggrega(mappa, n_fasce, n_strati):
    """Matrice che somma le fasce di tempo in fasce piu' larghe (mappa[k] = nuova fascia di k)."""
    Kb = int(mappa.max()) + 1
    A = np.zeros((Kb + n_strati, n_fasce + n_strati))
    A[mappa, np.arange(n_fasce)] = 1.0
    A[Kb:, n_fasce:] = np.eye(n_strati)
    return A


def stima_additiva(st, y, mappa):
    """Modello del piano: y = a[gruppo] + beta[fascia] + gamma[strato]. Minimi quadrati esatti.

    Restituisce beta (uno per fascia; conta solo la differenza tra fasce) e i
    CONTRIBUTI per giocatore (righe = giocatori, colonne = fasce): la stima su un
    ricampionamento dei giocatori e' beta + somma dei contributi dei giocatori estratti.
    Sono i residui del giocatore passati per l'inversa delle equazioni normali, cioe'
    la formula dell'errore standard robusto a grappolo: gamma e' stimato, non fissato.
    """
    A = aggrega(mappa, st.K, st.S)
    Kb = A.shape[0] - st.S
    N = A @ st.normali() @ A.T
    media = np.bincount(st.gruppo, weights=y, minlength=st.ng) / np.bincount(st.gruppo, minlength=st.ng)
    theta = np.linalg.lstsq(N, A @ st.somme_z(y - media[st.gruppo]), rcond=1e-10)[0]
    res = y - theta[mappa.astype(np.int32)[st.fascia]] - theta[Kb + st.strato]
    res -= (np.bincount(st.gruppo, weights=res, minlength=st.ng) / np.bincount(st.gruppo, minlength=st.ng))[st.gruppo]
    contributi = st.contributi(res, A.T @ np.linalg.pinv(N, rcond=1e-10)[:, :Kb])
    return theta[:Kb], contributi


def stima_moltiplicativa(st, e, mappa, n_ipf=30, max_newton=25, tol=1e-9):
    """Modello moltiplicativo: valore atteso di e = a[gruppo] * B[fascia] * C[strato].

    log B[k] - log B[j] = log del rapporto di rischio tra la fascia k e la fascia j.
    Stima di massima verosimiglianza di Poisson, in due tempi:
      1. aggiustamento proporzionale: a turno, ogni fattore (a, B, C) e' riscalato in
         modo che gli errori attesi coincidano con quelli osservati nei suoi livelli;
      2. passi di Newton fino a convergenza (a[gruppo] e' sempre ricalcolato in modo
         che in ogni gruppo attesi = osservati).
    Le coppie senza errori, e gli strati senza errori (per esempio chi e' gia' perso),
    non danno informazione e pesano zero da soli.
    Restituisce log B, i contributi per giocatore (come stima_additiva), il numero di
    passi e lo scarto finale (osservati - attesi per fascia, in valore assoluto).
    """
    S = st.S
    A = aggrega(mappa, st.K, S)
    Kb = A.shape[0] - S
    fb = mappa.astype(np.int32)[st.fascia]
    Eg = np.bincount(st.gruppo, weights=e, minlength=st.ng)
    Ek = np.bincount(fb, weights=e, minlength=Kb)
    Es = np.bincount(st.strato, weights=e, minlength=S)
    dividi = lambda x, y: np.where(y > 0, x / np.where(y > 0, y, 1.0), 0.0)
    livello = lambda B, C: dividi(Eg, np.bincount(st.gruppo, weights=B[fb] * C[st.strato], minlength=st.ng))[st.gruppo]
    B, C = np.ones(Kb), np.ones(S)
    for _ in range(n_ipf):
        a = livello(B, C)
        B = dividi(Ek, np.bincount(fb, weights=a * C[st.strato], minlength=Kb))
        C = dividi(Es, np.bincount(st.strato, weights=a * B[fb], minlength=S))
        C = C / C[C > 0].mean()
    passi = n_ipf
    for _ in range(max_newton):
        mu = livello(B, C) * B[fb] * C[st.strato]
        H = A @ st.normali(mu) @ A.T
        punteggio = np.r_[np.bincount(fb, weights=e - mu, minlength=Kb), np.bincount(st.strato, weights=e - mu, minlength=S)]
        passo = np.clip(np.linalg.lstsq(H, punteggio, rcond=1e-10)[0], -1.0, 1.0)
        B, C = B * np.exp(passo[:Kb]), C * np.exp(passo[Kb:])
        passi += 1
        vivi = B > 0
        if np.abs(passo[:Kb][vivi] - passo[:Kb][vivi][0]).max() < tol:
            break
    mu = livello(B, C) * B[fb] * C[st.strato]
    scarto = np.abs(np.bincount(fb, weights=e - mu, minlength=Kb)).max()
    contributi = st.contributi(e - mu, A.T @ np.linalg.pinv(H, rcond=1e-10)[:, :Kb])
    with np.errstate(divide="ignore"):
        return np.log(B), contributi, passi, scarto


# --------------------------------------------------------------------------
# Caricamento
# --------------------------------------------------------------------------
def crea_coppie(con, analisi, opz):
    """Tabella delle coppie partita-giocatore analizzabili (una riga per lato di ogni partita)."""
    filtro = f"gruppo = '{opz.gruppo}' AND has_eval AND inc_s = 0 AND classe IN ({', '.join(repr(c) for c in CLASSI)})"
    if opz.senza_tornei:
        filtro += " AND NOT is_tournament"
    if opz.stabile:
        filtro += " AND stabile"
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE coppie AS
        SELECT game_id, bianco, gid, classe,
               (ROW_NUMBER() OVER (ORDER BY gid, game_id))::INTEGER AS coppia,
               (DENSE_RANK() OVER (ORDER BY game_id))::INTEGER AS partita,
               (COUNT(*) OVER (PARTITION BY game_id) = 2) AS due_lati,
               ({sql_fasce('rating_rif', SOGLIE_RATING)})::TINYINT AS livello,
               (CASE WHEN elo - elo_avv <= -50 THEN 0 WHEN elo - elo_avv < 50 THEN 1 ELSE 2 END)::TINYINT AS f_scarto
        FROM {analisi}
        WHERE {filtro} AND rating_rif IS NOT NULL
    """)
    return con.execute("SELECT classe, COUNT(*) AS coppie, COUNT(DISTINCT gid) AS giocatori, COUNT(DISTINCT game_id) AS partite, "
                       "SUM(due_lati::INTEGER) / 2 AS partite_con_due_lati FROM coppie GROUP BY 1 ORDER BY 1").df()


def carica_mosse(con, mosse, classe):
    """Le mosse di una classe, come vettori numpy compatti (una riga per mossa)."""
    n_mossa = "(semimossa + 1) // 2"
    d = con.execute(f"""
        SELECT c.coppia, c.gid, c.livello, c.partita, c.due_lati, c.f_scarto,
               ({sql_fasce('m.clk_prima', SOGLIE_TEMPO)})::TINYINT AS fascia,
               ((({sql_fasce(n_mossa, SOGLIE_MOSSA)}) * {len(SOGLIE_CATTURE) + 1}
                 + ({sql_fasce('m.n_catture', SOGLIE_CATTURE)})) * {len(SOGLIE_WIN) + 1}
                 + ({sql_fasce('m.win_prima', SOGLIE_WIN)}))::SMALLINT AS strato,
               ({sql_fasce('m.win_prima', SOGLIE_WIN)})::TINYINT AS f_win,
               ((m.semimossa - 1) // 10)::SMALLINT AS finestra,
               (m.giudizio = 3)::TINYINT AS grave,
               GREATEST(m.perdita, 0)::REAL AS perdita
        FROM {mosse} m JOIN coppie c ON c.game_id = m.game_id AND c.bianco = m.bianco
        WHERE c.classe = '{classe}' AND m.perdita IS NOT NULL AND m.clk_prima IS NOT NULL AND m.win_prima IS NOT NULL
    """).fetchnumpy()
    return {k: np.asarray(v) for k, v in d.items()}


# --------------------------------------------------------------------------
# Analisi di una classe
# --------------------------------------------------------------------------
class Ricampionatore:
    """Bootstrap a grappolo sui giocatori, con gli STESSI ricampionamenti per tutte le stime di una
    classe: cosi' le differenze tra celle (per esempio tra fasce di livello) tengono conto dei
    giocatori in comune. I conteggi (quante volte ogni giocatore e' estratto in ogni
    ricampionamento) si generano una volta sola e si tengono in memoria a 8 bit.
    """

    def __init__(self, n_gioc, opz, indice):
        rng = np.random.default_rng([opz.seme, 11, indice])
        self.conteggi = np.empty((opz.bootstrap, n_gioc), dtype=np.uint8)
        probabilita = np.full(n_gioc, 1.0 / n_gioc)
        for inizio in range(0, opz.bootstrap, 50):
            quanti = min(50, opz.bootstrap - inizio)
            self.conteggi[inizio:inizio + quanti] = np.minimum(rng.multinomial(n_gioc, probabilita, size=quanti), 255)

    def somme(self, matrice):
        """Somme per colonna di `matrice` (una riga per giocatore) in ogni ricampionamento."""
        risultati = np.empty((len(self.conteggi), matrice.shape[1]))
        for inizio in range(0, len(self.conteggi), 50):
            risultati[inizio:inizio + 50] = self.conteggi[inizio:inizio + 50].astype(np.float64) @ matrice
        return risultati


def riga_contrasto(nome, stima, boot, n):
    lo, hi, es = intervallo(boot)
    return {"cella": nome, "n": n, "stima": stima, "ic95_da": lo, "ic95_a": hi, "err_std": es, "p": p_normale(stima, es)}


def analizza_cella(d, maschera, n_gioc, ric, con_curva=True):
    """Tutte le stime di una cella (una classe, tutti i livelli o una fascia di livello).

    Restituisce un dizionario: stime puntuali e vettori dei ricampionamenti (per i contrasti tra celle).
    """
    # Con la cella "tutti i livelli" la maschera prende tutto: niente copie (con 15 milioni di mosse sono centinaia di MB)
    prendi = (lambda v: v) if maschera.all() else (lambda v: v[maschera])
    e = prendi(d["grave"]).astype(np.float64)
    fascia = prendi(d["fascia"]).astype(np.int32)
    sotto = fascia <= 2
    ris = {"mosse": int(maschera.sum()), "mosse_sotto_10": int(sotto.sum()), "errori_sotto_10": int(e[sotto].sum()),
           "coppie": 0, "coppie_miste": 0}
    if ris["errori_sotto_10"] < N_MIN_ERRORI or sotto.all():
        return ris
    st = Struttura(prendi(d["coppia"]), fascia, prendi(d["strato"]), prendi(d["gioc"]), n_gioc, K, N_STRATI)
    n_sotto = np.bincount(st.gruppo, weights=sotto, minlength=st.ng)
    ris["coppie"] = st.ng
    ris["coppie_miste"] = int(((n_sotto > 0) & (n_sotto < np.bincount(st.gruppo, minlength=st.ng))).sum())
    # Tassi grezzi sotto i 10 secondi e sopra, con le somme per giocatore (per ricampionarli)
    grezzi = np.column_stack([np.bincount(st.gioc, weights=w, minlength=n_gioc) for w in (e * sotto, sotto, e * ~sotto, ~sotto)])
    Sg = ric.somme(grezzi)
    ris["p1"], ris["p0"] = grezzi[:, 0].sum() / grezzi[:, 1].sum(), grezzi[:, 2].sum() / grezzi[:, 3].sum()
    p1_boot = Sg[:, 0] / Sg[:, 1]
    # Moltiplicativo, due fasce: log RR sotto 10 secondi contro 10 o piu'
    logB, C, passi, scarto = stima_moltiplicativa(st, e, SOTTO_10)
    ris["log_rr"], ris["passi"], ris["scarto"] = logB[0] - logB[1], passi, scarto
    ris["log_rr_boot"] = ris["log_rr"] + ric.somme((C[:, 0] - C[:, 1])[:, None])[:, 0]
    # ...tradotto in punti percentuali tra le mosse giocate sotto i 10 secondi:
    # tasso osservato meno tasso che le stesse mosse avrebbero senza il rapporto di rischio
    ris["pp_esposti"] = 100 * ris["p1"] * (1 - np.exp(-ris["log_rr"]))
    ris["pp_esposti_boot"] = 100 * p1_boot * (1 - np.exp(-ris["log_rr_boot"]))
    # Additivo (come nel piano), due fasce, in punti percentuali
    beta, C = stima_additiva(st, 100 * e, SOTTO_10)
    ris["add_pp"] = beta[0] - beta[1]
    ris["add_pp_boot"] = ris["add_pp"] + ric.somme((C[:, 0] - C[:, 1])[:, None])[:, 0]
    # Perdita media di Win% per mossa: rapporto (moltiplicativo) e differenza (additivo)
    perdita = prendi(d["perdita"]).astype(np.float64)
    logB, C, _, _ = stima_moltiplicativa(st, perdita, SOTTO_10)
    ris["perdita_log_r"] = logB[0] - logB[1]
    ris["perdita_log_r_boot"] = ris["perdita_log_r"] + ric.somme((C[:, 0] - C[:, 1])[:, None])[:, 0]
    beta, C = stima_additiva(st, perdita, SOTTO_10)
    ris["perdita_add"] = beta[0] - beta[1]
    ris["perdita_add_boot"] = ris["perdita_add"] + ric.somme((C[:, 0] - C[:, 1])[:, None])[:, 0]
    ris["perdita_media"] = (perdita[sotto].mean(), perdita[~sotto].mean())
    if con_curva:
        # Curva a 8 fasce, rispetto a 20-40 secondi
        tutte = np.arange(K)
        logB, C, _, _ = stima_moltiplicativa(st, e, tutte)
        with np.errstate(invalid="ignore"):
            ris["curva"] = logB - logB[RIF]
            ris["curva_boot"] = ris["curva"] + ric.somme(C - C[:, [RIF]])
            # "Impennata" sotto i 10 secondi: il salto tra 10-20 e 5-10 e' piu' grande del salto tra 20-40 e 10-20?
            v = np.zeros(K); v[2], v[3], v[4] = 1.0, -2.0, 1.0
            ris["impennata"] = float(logB @ v)
            ris["impennata_boot"] = ris["impennata"] + ric.somme((C @ v)[:, None])[:, 0]
        beta, C = stima_additiva(st, 100 * e, tutte)
        ris["curva_add"] = beta - beta[RIF]
        ris["curva_add_boot"] = ris["curva_add"] + ric.somme(C - C[:, [RIF]])
        n_k = np.bincount(fascia, minlength=K)
        ris["mosse_fascia"], ris["errori_fascia"] = n_k, np.bincount(fascia, weights=e, minlength=K)
        ris["perdita_fascia"] = np.bincount(fascia, weights=perdita, minlength=K) / np.maximum(n_k, 1)
    return ris


def finestre(d, n_gioc, ric):
    """Robustezza del piano: i DUE giocatori nella stessa finestra di 10 semimosse.

    Gruppo = (partita, finestra): stessa posizione e stessa complessita' per entrambi,
    orologi diversi. Strati = equilibrio di chi muove x scarto di rating dall'avversario.
    Solo le partite in cui entrambi i giocatori sono nel campione analizzato.
    """
    m = d["due_lati"].astype(bool)
    if m.sum() == 0:
        return None
    e = d["grave"][m].astype(np.float64)
    fascia = d["fascia"][m].astype(np.int64)
    if e[fascia <= 2].sum() < N_MIN_ERRORI:
        return None
    gruppo = d["partita"][m].astype(np.int64) * 64 + np.minimum(d["finestra"][m], 63)
    strato = d["f_win"][m].astype(np.int64) * 3 + d["f_scarto"][m]
    st = Struttura(gruppo, fascia, strato, d["gioc"][m], n_gioc, K, 3 * (len(SOGLIE_WIN) + 1))
    logB, C, _, _ = stima_moltiplicativa(st, e, SOTTO_10)
    beta, Ca = stima_additiva(st, 100 * e, SOTTO_10)
    return (int(m.sum()), logB[0] - logB[1], logB[0] - logB[1] + ric.somme((C[:, 0] - C[:, 1])[:, None])[:, 0],
            beta[0] - beta[1], beta[0] - beta[1] + ric.somme((Ca[:, 0] - Ca[:, 1])[:, None])[:, 0])


def osservati_attesi(d, n_gioc, ric):
    """H2b, prima parte (descrittiva): i forti sbagliano meno a OGNI livello di tempo?

    Per ogni fascia di livello e di tempo: errori gravi osservati / errori attesi se il
    giocatore sbagliasse come la media della classe nello stesso strato e nella stessa
    fascia di tempo. Sotto 1 = sbaglia meno della media a parita' di posizione e di tempo.
    """
    e = d["grave"].astype(np.float64)
    cella = d["strato"].astype(np.int64) * K + d["fascia"]
    norma = np.bincount(cella, weights=e, minlength=N_STRATI * K) / np.maximum(np.bincount(cella, minlength=N_STRATI * K), 1)
    atteso = norma[cella]
    chiave = (d["gioc"].astype(np.int64) * 5 + d["livello"]) * K + d["fascia"]
    O = np.bincount(chiave, weights=e, minlength=n_gioc * 5 * K).reshape(n_gioc, 5 * K)
    E = np.bincount(chiave, weights=atteso, minlength=n_gioc * 5 * K).reshape(n_gioc, 5 * K)
    n = np.bincount(d["livello"].astype(np.int64) * K + d["fascia"], minlength=5 * K).reshape(5, K)
    with np.errstate(divide="ignore", invalid="ignore"):
        oe = (O.sum(axis=0) / E.sum(axis=0)).reshape(5, K)
        oe_boot = (ric.somme(O) / ric.somme(E)).reshape(-1, 5, K)
        tasso = 100 * O.sum(axis=0).reshape(5, K) / n
    return oe, oe_boot, tasso, n, O.sum(axis=0).reshape(5, K)


def analizza_classe(con, mosse, classe, indice, opz, reg, righe_csv):
    t0 = time.time()
    d = carica_mosse(con, mosse, classe)
    if len(d["coppia"]) == 0:
        reg.scrivi(f"\n[{classe}] nessuna mossa disponibile.")
        return None
    giocatori, gioc = np.unique(d["gid"], return_inverse=True)
    n_gioc, d["gioc"] = len(giocatori), gioc.astype(np.int32)
    del d["gid"], gioc
    ric = Ricampionatore(n_gioc, opz, indice)
    reg.scrivi(f"\n################ CLASSE {classe.upper()} ################")
    reg.scrivi(f"Mosse {len(d['coppia']):,} di {n_gioc:,} giocatori (caricate in {time.time() - t0:.0f} s)")

    celle = {"tutti": analizza_cella(d, np.ones(len(d["coppia"]), dtype=bool), n_gioc, ric)}
    for f, nome in enumerate(FASCE_RATING):
        celle[nome] = analizza_cella(d, d["livello"] == f, n_gioc, ric)
        print(f"  [{classe}] livello {nome} fatto - {time.time() - t0:.0f} s")

    # --- Tabella 1: curva per fascia di tempo ---
    righe = []
    for nome, r in celle.items():
        if "curva" not in r:
            continue
        lo, hi, _ = intervallo(np.exp(r["curva_boot"]))
        lo_a, hi_a, _ = intervallo(r["curva_add_boot"])
        for k in range(K):
            righe.append({"livello": nome, "tempo": FASCE_TEMPO[k], "mosse": int(r["mosse_fascia"][k]),
                          "errori_gravi": int(r["errori_fascia"][k]),
                          "tasso_grezzo_perc": 100 * r["errori_fascia"][k] / max(r["mosse_fascia"][k], 1),
                          "perdita_media": r["perdita_fascia"][k],
                          "RR": np.exp(r["curva"][k]), "ic95_da": lo[k], "ic95_a": hi[k],
                          "additivo_pp": r["curva_add"][k], "add_ic95_da": lo_a[k], "add_ic95_a": hi_a[k]})
            righe_csv.append((f"curva_RR_{classe}", f"{nome} | {FASCE_TEMPO[k]}", np.exp(r["curva"][k]), lo[k], hi[k], np.nan, np.nan, int(r["mosse_fascia"][k])))
            righe_csv.append((f"curva_additiva_pp_{classe}", f"{nome} | {FASCE_TEMPO[k]}", r["curva_add"][k], lo_a[k], hi_a[k], np.nan, np.nan, int(r["mosse_fascia"][k])))
    if righe:
        reg.tabella(f"[{classe}] CURVA PER TEMPO RESIDUO - RR = rapporto di rischio di errore grave rispetto a 20-40 s, "
                    "stessa partita, stesso giocatore, stesso strato (moltiplicativo); additivo_pp = modello del piano",
                    pd.DataFrame(righe).round({"tasso_grezzo_perc": 2, "perdita_media": 2, "RR": 3, "ic95_da": 3, "ic95_a": 3,
                                               "additivo_pp": 2, "add_ic95_da": 2, "add_ic95_a": 2}))

    # --- Tabella 2: sotto i 10 secondi contro 10 secondi o piu' ---
    righe = []
    for nome, r in celle.items():
        base = {"livello": nome, "mosse": r["mosse"], "mosse_sotto_10": r["mosse_sotto_10"], "coppie_miste": r["coppie_miste"]}
        if "log_rr" not in r:
            righe.append(base)
            continue
        lo, hi, es = intervallo(r["log_rr_boot"])
        lo_p, hi_p, _ = intervallo(r["pp_esposti_boot"])
        lo_a, hi_a, es_a = intervallo(r["add_pp_boot"])
        righe.append({**base, "tasso_sotto_10": 100 * r["p1"], "tasso_10_o_piu": 100 * r["p0"],
                      "RR": np.exp(r["log_rr"]), "ic95_da": np.exp(lo), "ic95_a": np.exp(hi), "log_RR": r["log_rr"], "err_std": es,
                      "p": p_normale(r["log_rr"], es), "pp_tra_esposti": r["pp_esposti"], "pp_da": lo_p, "pp_a": hi_p,
                      "additivo_pp": r["add_pp"], "add_da": lo_a, "add_a": hi_a, "add_p": p_normale(r["add_pp"], es_a)})
        righe_csv.append((f"RR_sotto10_{classe}", nome, np.exp(r["log_rr"]), np.exp(lo), np.exp(hi), es, p_normale(r["log_rr"], es), r["mosse_sotto_10"]))
        righe_csv.append((f"pp_tra_esposti_{classe}", nome, r["pp_esposti"], lo_p, hi_p, np.nan, np.nan, r["mosse_sotto_10"]))
        righe_csv.append((f"additivo_pp_sotto10_{classe}", nome, r["add_pp"], lo_a, hi_a, es_a, p_normale(r["add_pp"], es_a), r["mosse_sotto_10"]))
    reg.tabella(f"[{classe}] MENO DI 10 SECONDI CONTRO 10 O PIU' - errore grave. RR moltiplicativo (primario); pp_tra_esposti = "
                "tasso osservato sotto i 10 s meno quello che le stesse mosse avrebbero senza il RR; additivo_pp = modello del piano",
                pd.DataFrame(righe).round({"tasso_sotto_10": 2, "tasso_10_o_piu": 2, "RR": 3, "ic95_da": 3, "ic95_a": 3, "log_RR": 4,
                                           "err_std": 4, "pp_tra_esposti": 2, "pp_da": 2, "pp_a": 2, "additivo_pp": 2, "add_da": 2, "add_a": 2}))

    # --- Tabella 3: perdita media, impennata, pendenza per livello, finestre ---
    righe = []
    r = celle["tutti"]
    if "log_rr" in r:
        righe.append(riga_contrasto("perdita media di Win%: log del rapporto sotto 10 s / 10 s o piu' (moltiplicativo)",
                                    r["perdita_log_r"], r["perdita_log_r_boot"], r["mosse_sotto_10"]))
        righe.append(riga_contrasto(f"perdita media di Win%: differenza additiva (grezze: {r['perdita_media'][0]:.2f} e {r['perdita_media'][1]:.2f})",
                                    r["perdita_add"], r["perdita_add_boot"], r["mosse_sotto_10"]))
    if "impennata" in r and np.isfinite(r["impennata"]):
        righe.append(riga_contrasto("impennata: [log RR(5-10) - log RR(10-20)] - [log RR(10-20) - log RR(20-40)]",
                                    r["impennata"], r["impennata_boot"], r["mosse_sotto_10"]))
    livelli = [celle[n] for n in FASCE_RATING]
    pendenza = None
    if all("log_rr" in x for x in livelli):
        for chiave, nome in (("log_rr", "pendenza di log RR per fascia di livello (moltiplicativo)"),
                             ("add_pp", "pendenza dell'effetto additivo (pp) per fascia di livello"),
                             ("perdita_log_r", "pendenza del log rapporto di perdita media per fascia di livello")):
            stima = float(PESI_PENDENZA @ np.array([x[chiave] for x in livelli]))
            boot = np.column_stack([x[chiave + "_boot"] for x in livelli]) @ PESI_PENDENZA
            righe.append(riga_contrasto(nome, stima, boot, sum(x["mosse_sotto_10"] for x in livelli)))
            if chiave == "log_rr":
                pendenza = righe[-1]
        diff = livelli[4]["log_rr"] - livelli[0]["log_rr"]
        righe.append(riga_contrasto("log RR (>=2000) - log RR (<1400)", diff, livelli[4]["log_rr_boot"] - livelli[0]["log_rr_boot"],
                                    livelli[4]["mosse_sotto_10"] + livelli[0]["mosse_sotto_10"]))
    fin = finestre(d, n_gioc, ric)
    if fin is not None:
        righe.append(riga_contrasto("ROBUSTEZZA due giocatori, stessa finestra di 10 semimosse: log RR sotto 10 s", fin[1], fin[2], fin[0]))
        righe.append(riga_contrasto("ROBUSTEZZA due giocatori, stessa finestra: differenza additiva (pp)", fin[3], fin[4], fin[0]))
    if righe:
        tab = pd.DataFrame(righe)
        reg.tabella(f"[{classe}] ALTRE STIME (tutti i livelli salvo dove indicato)", tab.round({"stima": 4, "ic95_da": 4, "ic95_a": 4, "err_std": 4}))
        reg.scrivi("ROBUSTEZZA a finestre: non toglie le differenze tra i due giocatori (chi pensa di piu' puo' anche sbagliare di piu'): "
                   "si legge solo nel segno e non entra nei verdetti.")
        for x in tab.itertuples():
            righe_csv.append((f"altre_{classe}", x.cella, x.stima, x.ic95_da, x.ic95_a, x.err_std, x.p, x.n))

    # --- Tabella 4: osservati / attesi per livello e tempo ---
    oe, oe_boot, tasso, n, errori = osservati_attesi(d, n_gioc, ric)
    righe = []
    with np.errstate(invalid="ignore"), __import__("warnings").catch_warnings():
        __import__("warnings").simplefilter("ignore")
        lo, hi, _ = intervallo(oe_boot[:, 4, :] - oe_boot[:, 0, :])
    for k in range(K):
        riga = {"tempo": FASCE_TEMPO[k]}
        for f, nome in enumerate(FASCE_RATING):
            riga[f"O/A {nome}"] = oe[f, k] if errori[f, k] >= 30 else np.nan
        pochi = min(errori[0, k], errori[4, k]) < 30
        riga.update({"forti - deboli": np.nan if pochi else oe[4, k] - oe[0, k], "ic95_da": np.nan if pochi else lo[k],
                     "ic95_a": np.nan if pochi else hi[k], "tasso_perc <1400": tasso[0, k], "tasso_perc >=2000": tasso[4, k]})
        righe.append(riga)
        righe_csv.append((f"OA_forti_meno_deboli_{classe}", FASCE_TEMPO[k], riga["forti - deboli"], riga["ic95_da"], riga["ic95_a"],
                          np.nan, np.nan, int(n[0, k] + n[4, k])))
    reg.tabella(f"[{classe}] ERRORI GRAVI OSSERVATI / ATTESI per livello e tempo (atteso = media della classe nello stesso strato "
                "e nella stessa fascia di tempo); forti - deboli = (>=2000) - (<1400); vuoto = meno di 30 errori",
                pd.DataFrame(righe).round(3))
    con_dati = [k for k in range(K) if min(errori[0, k], errori[4, k]) >= 30]
    sotto_zero = [k for k in con_dati if hi[k] < 0]
    r = celle["tutti"]
    if "passi" in r:
        reg.scrivi(f"Controllo numerico (tutti i livelli, due fasce): {r['passi']} passi; errori attesi - osservati per fascia, "
                   f"massimo {r['scarto']:.1e} (deve essere circa zero)")
    reg.scrivi(f"({classe}: {time.time() - t0:.0f} s)")
    return {"tutti": celle["tutti"], "pendenza": pendenza, "forti_meno": (len(sotto_zero), len(con_dati))}


def tabella_holm(p_h2a, p_h2b):
    """Holm al 5% sulla famiglia dei sei test confermativi (i quattro della domanda 1 sono gia' noti)."""
    p = dict(P_DOMANDA_1, H2a=p_h2a, H2b=p_h2b)
    ordine = sorted(p, key=lambda h: (not np.isfinite(p[h]), p[h]))
    righe, fermo = [], False
    for i, h in enumerate(ordine):
        soglia = 0.05 / (len(ordine) - i)
        rifiutata = (not fermo) and np.isfinite(p[h]) and p[h] <= soglia
        fermo = fermo or not rifiutata
        righe.append({"test": h, "p": p[h], "soglia_holm": soglia, "uguaglianza_rifiutata": "si'" if rifiutata else "no"})
    return pd.DataFrame(righe)


def main():
    parser = argparse.ArgumentParser(description="Pressione del tempo ed errori gravi (domanda 2)")
    parser.add_argument("--gruppo", choices=["esplorazione", "conferma"], default="esplorazione")
    parser.add_argument("--codice-bloccato", action="store_true",
                        help="obbligatorio con --gruppo conferma: dichiari che il codice non cambiera' piu'")
    parser.add_argument("--bootstrap", type=int, default=1000)
    parser.add_argument("--seme", type=int, default=20170501)
    parser.add_argument("--memoria", default="2GB", help="limite di memoria per DuckDB (numpy ne usa circa 1 GB in piu')")
    # Varianti di robustezza
    parser.add_argument("--senza-tornei", action="store_true", help="esclude le partite di torneo (quindi anche il berserk)")
    parser.add_argument("--stabile", action="store_true", help="solo giocatori con rating stabile nella classe")
    opz = parser.parse_args()

    if opz.gruppo == "conferma" and not opz.codice_bloccato:
        sys.exit("Il gruppo di conferma si analizza UNA volta sola, a codice bloccato.\n"
                 "Se il codice e' definitivo (commit fatto), rilancia aggiungendo --codice-bloccato")

    variante = ("_senzatornei" if opz.senza_tornei else "") + ("_stabile" if opz.stabile else "")
    analisi = f"read_parquet('{(CARTELLA_DATI / 'analisi').as_posix()}/*.parquet')"
    mosse = f"read_parquet('{(CARTELLA_DATI / 'mosse.parquet').as_posix()}')"
    reg = Registro(f"11_pressione_{opz.gruppo}{variante}")
    reg.scrivi(f"DOMANDA 2 - pressione del tempo | gruppo: {opz.gruppo} | variante: {variante or 'principale'} | seme {opz.seme} | "
               f"{opz.bootstrap} ricampionamenti dei giocatori")
    reg.scrivi(f"Mosse di partite con valutazioni, senza incremento; strati: {N_STRATI}; riferimento delle curve: {FASCE_TEMPO[RIF]}")
    con = apri_duckdb(opz.memoria)
    inizio = time.time()
    reg.tabella("Campione: coppie partita-giocatore analizzabili", crea_coppie(con, analisi, opz))

    righe_csv, risultati = [], {}
    for indice, classe in enumerate(CLASSI):
        risultati[classe] = analizza_classe(con, mosse, classe, indice, opz, reg, righe_csv)

    # ---------------- Test confermativi (blitz) ----------------
    reg.scrivi("\n################ TEST CONFERMATIVI (blitz) ################")
    blitz = risultati.get("blitz")
    p_h2a = p_h2b = np.nan
    righe = []
    if blitz is not None and "log_rr" in blitz["tutti"]:
        r = blitz["tutti"]
        riga = riga_contrasto("H2a: log RR sotto 10 s contro 10 s o piu', blitz, tutti i livelli", r["log_rr"], r["log_rr_boot"], r["mosse_sotto_10"])
        p_h2a = riga["p"]
        righe.append(riga)
    if blitz is not None and blitz["pendenza"] is not None:
        riga = dict(blitz["pendenza"], cella="H2b: pendenza di log RR per fascia di livello, blitz")
        p_h2b = riga["p"]
        righe.append(riga)
    if righe:
        tab = pd.DataFrame(righe)
        reg.tabella("Statistiche dei due test (previsione: H2a > 0, H2b < 0; p a due code, normale, errore standard dal bootstrap; "
                    "p = 0 vuol dire sotto 1e-300)",
                    tab.round({"stima": 4, "ic95_da": 4, "ic95_a": 4, "err_std": 4}).assign(p=tab["p"].map("{:.2e}".format)))
        for x in tab.itertuples():
            righe_csv.append(("confermativo", x.cella, x.stima, x.ic95_da, x.ic95_a, x.err_std, x.p, x.n))
        if "log_rr" in blitz["tutti"]:
            lo, hi, _ = intervallo(blitz["tutti"]["log_rr_boot"])
            reg.scrivi(f"H2a come rapporto di rischio: RR = {math.exp(blitz['tutti']['log_rr']):.3f} (IC95 {math.exp(lo):.3f}; {math.exp(hi):.3f})")
    else:
        reg.scrivi("Dati insufficienti per i test confermativi.")
    holm = tabella_holm(p_h2a, p_h2b)
    reg.tabella("Holm al 5% sui SEI test confermativi (p della domanda 1 da 08_tilt_conferma.txt). "
                "Vale come verdetto solo per il gruppo conferma",
                holm.round({"soglia_holm": 4}).assign(p=holm["p"].map("{:.2e}".format)))
    rifiutata = dict(zip(holm["test"], holm["uguaglianza_rifiutata"] == "si'"))
    reg.scrivi("\n== VERDETTI secondo le regole di P13" + (" ==" if opz.gruppo == "conferma" else
               " - SOLO INDICATIVI: questo e' il gruppo esplorazione, serve a provare il codice =="))
    if blitz is not None and "log_rr" in blitz["tutti"]:
        r = blitz["tutti"]
        lo, hi, _ = intervallo(r["log_rr_boot"])
        lo, hi = math.exp(lo), math.exp(hi)
        if rifiutata["H2a"] and lo >= RR_RILEVANTE:
            v = "CONFERMATA"
        elif rifiutata["H2a"] and hi <= 1 / RR_RILEVANTE:
            v = "SMENTITA (meno errori gravi con poco tempo)"
        elif lo >= 1 / RR_RILEVANTE and hi <= RR_RILEVANTE:
            v = "EFFETTO TRASCURABILE (IC95 del RR tutto tra 0,91 e 1,10)"
        else:
            v = "INCONCLUDENTE"
        reg.scrivi(f"H2a: {v}. RR = {math.exp(r['log_rr']):.3f} (IC95 {lo:.3f}; {hi:.3f}); Holm: uguaglianza "
                   f"{'rifiutata' if rifiutata['H2a'] else 'non rifiutata'}; soglia di rilevanza: IC95 tutto sopra {RR_RILEVANTE}.")
        if "impennata" in r and np.isfinite(r["impennata"]):
            lo_i, hi_i, _ = intervallo(r["impennata_boot"])
            reg.scrivi(f"     Impennata sotto i 10 secondi (descrittiva): {r['impennata']:.3f} (IC95 {lo_i:.3f}; {hi_i:.3f}) -> "
                       + ("si puo' scrivere 'con un'impennata sotto i 10 secondi'." if lo_i > 0 else
                          "NON scrivere 'impennata': il salto sotto i 10 secondi non e' piu' grande del precedente."))
    if blitz is not None and blitz["pendenza"] is not None:
        x = blitz["pendenza"]
        if rifiutata["H2b"] and x["stima"] < 0:
            v = "seconda parte CONFERMATA (l'aumento relativo e' minore per i forti)"
        elif rifiutata["H2b"] and x["ic95_da"] > MARGINE_H2B:
            v = "seconda parte SMENTITA (l'aumento relativo e' maggiore per i forti)"
        else:
            v = "seconda parte NON CONFERMATA"
        quante, su = blitz["forti_meno"]
        reg.scrivi(f"H2b: {v}. Pendenza = {x['stima']:.4f} per fascia di livello (IC95 {x['ic95_da']:.4f}; {x['ic95_a']:.4f}); Holm: uguaglianza "
                   f"{'rifiutata' if rifiutata['H2b'] else 'non rifiutata'}; smentita solo con IC95 tutto sopra +{MARGINE_H2B}.")
        reg.scrivi(f"     Prima parte (descrittiva): i forti (>=2000) hanno un rapporto osservati/attesi piu' basso dei deboli (<1400) "
                   f"in {quante} fasce di tempo su {su} con dati (IC95 tutto sotto zero)"
                   + (": 'a ogni livello di tempo' regge." if su > 0 and quante == su else ": 'a ogni livello di tempo' NON regge per intero."))
    reg.scrivi("Regole di lettura complete: PRECISAZIONI.md, P13. Nessuna stima e' causale.")

    file_csv = CARTELLA_OUTPUT / f"11_stime_{opz.gruppo}{variante}.csv"
    pd.DataFrame(righe_csv, columns=["analisi", "cella", "stima", "ic95_da", "ic95_a", "err_std", "p", "n"]).to_csv(file_csv, index=False)
    reg.scrivi(f"\nStime salvate in {file_csv} - tempo totale {(time.time() - inizio) / 60:.1f} minuti")
    reg.chiudi()


if __name__ == "__main__":
    main()
