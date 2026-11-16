"""
06_atteso.py - Punteggio atteso, residui e tabella di analisi

Cosa fa:
  Parte da data/giocatore_partita/ (creata da 05_sessioni.py) e crea
  data/analisi/ : le stesse righe (giocatore, partita) con in piu':

  1. rating stabile (per giocatore e classe);
  2. punteggio atteso E e residuo = punteggio - E;
  3. y = residuo corretto per la posizione nella sessione (stanchezza media);
  4. la "base" del giocatore: media dei suoi y in tutte le ALTRE sessioni.

Uso (PowerShell, nella cartella C:\\tilt):
    .\\.venv\\Scripts\\python 06_atteso.py
Robustezza (dopo 05_sessioni.py --soglia 10):
    .\\.venv\\Scripts\\python 06_atteso.py --soglia 10
"""

import argparse
import shutil
import time

import numpy as np
import pandas as pd

from tilt_utils import CARTELLA_DATI, CLASSI, Registro, apri_duckdb

N_SECCHI = 8
LISTA_CLASSI = ", ".join(f"'{c}'" for c in CLASSI)
D_MAX = 600          # differenze di rating oltre +-600 vengono trattate come +-600
LARGHEZZA_FASCIA = 25
MIN_PER_FASCIA = 200  # partite minime perche' una fascia entri nella curva
MIN_BASE = 20         # partite minime nelle altre sessioni per calcolare la base

# Posizione nella sessione, a fasce: 1, 2, 3, 4-5, 6-10, 11-20, 21+
FASCIA_POS = """CASE WHEN pos <= 3 THEN pos WHEN pos <= 5 THEN 4 WHEN pos <= 10 THEN 5
                     WHEN pos <= 20 THEN 6 ELSE 7 END"""


def crea_stabilita(con, sorgente):
    """Rating stabile: abbastanza partite nella classe e variazioni di rating piccole.

    Un rating nuovo si muove di 25 punti e piu' a partita: l'atteso non e' affidabile.
    Tre versioni: quella del piano e due per la robustezza (piu' larga, piu' stretta).
    """
    con.execute(f"""
        CREATE OR REPLACE TABLE stabilita AS
        SELECT gid, classe, COUNT(*) AS n_valide, MEDIAN(ABS(diff_rating)) AS mediana_diff,
               (COUNT(*) >= 50 AND MEDIAN(ABS(diff_rating)) <= 15) AS stabile,
               (COUNT(*) >= 30 AND MEDIAN(ABS(diff_rating)) <= 20) AS stabile_largo,
               (COUNT(*) >= 100 AND MEDIAN(ABS(diff_rating)) <= 12) AS stabile_stretto
        FROM {sorgente}
        WHERE valida AND classe IN ({LISTA_CLASSI})
        GROUP BY gid, classe
    """)


def crea_curva_atteso(con, sorgente, reg):
    """Curva empirica del punteggio atteso per classe, colore e differenza di rating.

    1. Medie per fasce di 25 punti sulle prime partite di sessione (pos = 1).
    2. Interpolazione lineare tra i centri delle fasce, per ogni differenza intera
       da -600 a +600: cosi' E cambia in modo continuo e non a gradini.
    """
    fasce = con.execute(f"""
        SELECT g.classe, g.bianco,
               FLOOR(GREATEST(-{D_MAX}, LEAST({D_MAX} - 1, g.elo - g.elo_avv)) / {LARGHEZZA_FASCIA}.0)::INTEGER AS fascia,
               COUNT(*) AS n, AVG(g.elo - g.elo_avv) AS d_medio, AVG(g.punteggio) AS e_medio
        FROM {sorgente} g JOIN stabilita s USING (gid, classe)
        WHERE g.pos = 1 AND g.elig AND s.stabile
        GROUP BY ALL ORDER BY 1, 2, 3
    """).df()
    griglia = np.arange(-D_MAX, D_MAX + 1)
    pezzi = []
    for (classe, bianco), f in fasce.groupby(["classe", "bianco"]):
        f = f[(f["n"] >= MIN_PER_FASCIA) & (f["e_medio"] > 0.02) & (f["e_medio"] < 0.98)]
        if len(f) < 3:
            continue
        x, e_fascia, peso = f["d_medio"].to_numpy(), f["e_medio"].to_numpy(), f["n"].to_numpy()
        # Dentro l'intervallo coperto dai dati: interpolazione lineare tra le fasce.
        e = np.interp(griglia, x, e_fascia)
        # Fuori (code con poche partite): curva logistica stimata sugli stessi dati,
        # E = 1 / (1 + 10^-(a + b*d)), con una retta pesata sul logit delle fasce;
        # la traslo perche' si raccordi senza salti all'ultima fascia affidabile.
        b, a = np.polyfit(x, np.log10(e_fascia / (1 - e_fascia)), 1, w=np.sqrt(peso))
        logistica = lambda d: 1 / (1 + 10 ** -(a + b * d))
        sotto, sopra = griglia < x[0], griglia > x[-1]
        e[sotto] = logistica(griglia[sotto]) + (e_fascia[0] - logistica(x[0]))
        e[sopra] = logistica(griglia[sopra]) + (e_fascia[-1] - logistica(x[-1]))
        e = np.clip(e, 0.005, 0.995)
        pezzi.append(pd.DataFrame({"classe": classe, "bianco": bianco, "d": griglia, "e": e,
                                   "punti_per_decuplo": 1 / b, "dati_da": x[0], "dati_a": x[-1]}))
    curva = pd.concat(pezzi, ignore_index=True)
    con.register("curva_df", curva)
    con.execute("CREATE OR REPLACE TABLE atteso AS SELECT classe, bianco, d::INTEGER AS d, e FROM curva_df")
    con.unregister("curva_df")

    # "punti_per_decuplo": quanti punti di rating moltiplicano per 10 il rapporto
    # vittorie/sconfitte. Nella formula Elo sono 400: e' la pendenza della curva.
    riassunto = curva[curva["d"].isin([-200, -100, 0, 100, 200])].pivot_table(
        index=["classe", "bianco", "punti_per_decuplo", "dati_da", "dati_a"],
        columns="d", values="e").round(3).reset_index().round({"punti_per_decuplo": 0, "dati_da": 0, "dati_a": 0})
    reg.tabella("Curva del punteggio atteso (E) ad alcune differenze di rating (io - avversario). "
                "Formula Elo teorica: -200 -> 0.240, -100 -> 0.360, 0 -> 0.500, +100 -> 0.640, +200 -> 0.760",
                riassunto)
    reg.tabella("Partite usate per la curva", fasce.groupby(["classe", "bianco"], as_index=False)["n"].sum())
    return curva


def sql_residui(sorgente, filtro=""):
    """Righe con stabilita' e i tre residui (stessa curva, tre rating diversi per 'me')."""
    def unione(alias, rating):
        return (f"LEFT JOIN atteso {alias} ON {alias}.classe = g.classe AND {alias}.bianco = g.bianco "
                f"AND {alias}.d = GREATEST(-{D_MAX}, LEAST({D_MAX}, ({rating})::INTEGER - g.elo_avv::INTEGER))")
    return f"""
        SELECT g.*, COALESCE(s.stabile, FALSE) AS stabile,
               COALESCE(s.stabile_largo, FALSE) AS stabile_largo,
               COALESCE(s.stabile_stretto, FALSE) AS stabile_stretto,
               {FASCIA_POS} AS fascia_pos,
               a1.e AS atteso,
               g.punteggio - a1.e AS resid,          -- rating di riferimento (analisi principale)
               g.punteggio - a2.e AS resid_cor,      -- rating corrente (robustezza)
               g.punteggio - a3.e AS resid_x         -- riferimento della sessione precedente (coppie tra sessioni)
        FROM {sorgente} g
        LEFT JOIN stabilita s USING (gid, classe)
        {unione('a1', 'g.rating_rif')}
        {unione('a2', 'g.elo')}
        {unione('a3', 'g.rating_rif_x')}
        WHERE g.valida {filtro}
    """


def crea_correzione_posizione(con, sorgente):
    """Residuo medio per classe e posizione nella sessione: la 'stanchezza media'.

    La sottraggo dal residuo, cosi' il confronto dopo sconfitta / dopo vittoria non
    scambia per tilt il semplice fatto che le partite tardive vanno peggio.
    """
    con.execute(f"""
        CREATE OR REPLACE TABLE corr_pos AS
        SELECT classe, fascia_pos, COUNT(*) AS n, AVG(resid) AS corr, AVG(resid_cor) AS corr_cor
        FROM ({sql_residui(sorgente)})
        WHERE elig AND stabile
        GROUP BY classe, fascia_pos
    """)


def sql_secchio(sorgente, secchio):
    """Tabella finale per un secchio di giocatori: y e basi del giocatore."""
    return f"""
    WITH r AS (
        {sql_residui(sorgente, f"AND g.gid % {N_SECCHI} = {secchio}")}
    ),
    y AS (
        SELECT r.*,
               r.resid - c.corr AS y,
               r.resid_cor - c.corr_cor AS y_cor,
               r.resid_x - c.corr AS y_x
        FROM r LEFT JOIN corr_pos c USING (classe, fascia_pos)
    ),
    -- Somme per giocatore e classe (tot) e per sessione (ses), sulle partite
    -- utilizzabili (valide, fuori torneo). Servono per la media "tutte le altre sessioni".
    tot AS (
        SELECT gid, classe, SUM(y) AS s, COUNT(y) AS n, SUM(y_cor) AS s_cor
        FROM y WHERE elig GROUP BY gid, classe
    ),
    ses AS (
        SELECT gid, classe, sessione, SUM(y) AS s, COUNT(y) AS n, SUM(y_cor) AS s_cor
        FROM y WHERE elig GROUP BY gid, classe, sessione
    )
    SELECT y.gid, y.game_id, y.avv, y.bianco, y.lato_scelto, y.gruppo,
           y.start_utc, y.t_inizio, y.t_fine, y.pausa_s,
           y.classe, y.base_s, y.inc_s, y.is_tournament, y.berserk, y.termination, y.n_clk, y.has_eval,
           y.punteggio, y.elo, y.elo_avv, y.rating_rif, y.rating_rif_x,
           y.elig, y.corta, y.persa_tempo, y.ritmo_10, y.clk_fin_vinc, y.clk_fin_perd,
           y.sessione, y.pos, y.n_sessione, y.fascia_pos, y.blocco, y.pos_blocco, y.n_blocco,
           y.prec_game_id, y.prec_punteggio, y.prec_avv, y.prec_corta, y.prec_persa_tempo,
           y.prec_clk_fin_vinc, y.prec_clk_fin_perd, y.coppia_x,
           y.prec2_punteggio, y.prec2_avv, y.prec3_punteggio, y.prec3_avv, y.serie_prec,
           y.stabile, y.stabile_largo, y.stabile_stretto,
           y.atteso, y.resid, y.resid_cor, y.y, y.y_cor, y.y_x,
           -- Base = media degli y del giocatore (stessa classe) in tutte le altre sessioni.
           CASE WHEN t.n - COALESCE(s.n, 0) >= {MIN_BASE}
                THEN (t.s - COALESCE(s.s, 0)) / (t.n - COALESCE(s.n, 0)) END AS base_altre,
           CASE WHEN t.n - COALESCE(s.n, 0) >= {MIN_BASE}
                THEN (t.s_cor - COALESCE(s.s_cor, 0)) / (t.n - COALESCE(s.n, 0)) END AS base_altre_cor,
           -- Per le coppie tra due sessioni escludo ENTRAMBE le sessioni: la precedente
           -- contiene la partita che definisce "dopo sconfitta / dopo vittoria".
           CASE WHEN y.coppia_x AND t.n - COALESCE(s.n, 0) - COALESCE(sp.n, 0) >= {MIN_BASE}
                THEN (t.s - COALESCE(s.s, 0) - COALESCE(sp.s, 0)) / (t.n - COALESCE(s.n, 0) - COALESCE(sp.n, 0)) END AS base_x
    FROM y
    LEFT JOIN tot t ON t.gid = y.gid AND t.classe = y.classe
    LEFT JOIN ses s ON s.gid = y.gid AND s.classe = y.classe AND s.sessione = y.sessione
    LEFT JOIN ses sp ON sp.gid = y.gid AND sp.classe = y.classe AND sp.sessione = y.sessione - 1
    """


def diagnostiche(con, analisi, reg):
    reg.tabella("Rating stabile: coppie (giocatore, classe)", con.sql("""
        SELECT classe, COUNT(*) AS giocatori_classe, SUM(stabile::INTEGER) AS stabili,
               SUM(stabile_largo::INTEGER) AS stabili_largo, SUM(stabile_stretto::INTEGER) AS stabili_stretto
        FROM stabilita GROUP BY 1 ORDER BY 2 DESC
    """).df())
    reg.tabella("Righe utilizzabili come esito (stabili, fuori torneo, lato scelto) e coppie", con.sql(f"""
        SELECT gruppo, classe, COUNT(*) AS esiti,
               SUM(CASE WHEN pos_blocco > 1 AND avv <> prec_avv AND prec_punteggio <> 0.5 THEN 1 ELSE 0 END) AS coppie_primarie,
               SUM(CASE WHEN pos_blocco > 1 AND avv = prec_avv THEN 1 ELSE 0 END) AS rivincite_escluse,
               SUM(CASE WHEN coppia_x AND avv <> prec_avv AND prec_punteggio <> 0.5 THEN 1 ELSE 0 END) AS coppie_tra_sessioni,
               ROUND(100.0 * AVG(CASE WHEN base_altre IS NULL THEN 1 ELSE 0 END), 1) AS perc_senza_base
        FROM {analisi} WHERE elig AND stabile AND lato_scelto GROUP BY ALL ORDER BY 1 DESC, 3 DESC
    """).df())
    reg.tabella("SOLO ESPLORAZIONE - residuo medio per posizione nella sessione (prima della correzione), in punti percentuali",
                con.sql(f"""
        SELECT classe, fascia_pos, COUNT(*) AS n, ROUND(100 * AVG(resid), 2) AS resid_pp,
               ROUND(100 * AVG(resid_cor), 2) AS resid_rating_corrente_pp
        FROM {analisi} WHERE gruppo = 'esplorazione' AND elig AND stabile GROUP BY ALL ORDER BY 1, 2
    """).df())


def main():
    parser = argparse.ArgumentParser(description="Punteggio atteso, residui e tabella di analisi")
    parser.add_argument("--soglia", type=int, default=30, help="soglia di sessione usata in 05 (default 30)")
    parser.add_argument("--memoria", default="4GB", help="limite di memoria per DuckDB (default 4GB)")
    args = parser.parse_args()

    suffisso = "" if args.soglia == 30 else f"_s{args.soglia}"
    sorgente = f"read_parquet('{(CARTELLA_DATI / f'giocatore_partita{suffisso}').as_posix()}/*.parquet')"
    cartella_out = CARTELLA_DATI / f"analisi{suffisso}"
    if cartella_out.exists():
        shutil.rmtree(cartella_out)
    cartella_out.mkdir(parents=True)
    file_db = CARTELLA_DATI / "lavoro_06.duckdb"
    file_db.unlink(missing_ok=True)

    reg = Registro(f"06_diagnostiche{suffisso}")
    con = apri_duckdb(args.memoria, file_db)
    inizio = time.time()

    crea_stabilita(con, sorgente)
    crea_curva_atteso(con, sorgente, reg)
    crea_correzione_posizione(con, sorgente)
    print(f"  stabilita', curva e correzione pronte - {time.time() - inizio:.0f} s")

    for secchio in range(N_SECCHI):
        destinazione = (cartella_out / f"secchio_{secchio}.parquet").as_posix()
        con.execute(f"COPY ({sql_secchio(sorgente, secchio)}) TO '{destinazione}' (FORMAT parquet, COMPRESSION zstd)")
        print(f"  secchio {secchio + 1}/{N_SECCHI} scritto - {time.time() - inizio:.0f} s")

    con.execute(f"COPY atteso TO '{(CARTELLA_DATI / f'curva_atteso{suffisso}.parquet').as_posix()}' (FORMAT parquet)")
    analisi = f"read_parquet('{cartella_out.as_posix()}/*.parquet')"
    diagnostiche(con, analisi, reg)
    reg.scrivi(f"\nFatto in {(time.time() - inizio) / 60:.1f} minuti -> {cartella_out}")
    reg.chiudi()
    con.close()
    file_db.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
