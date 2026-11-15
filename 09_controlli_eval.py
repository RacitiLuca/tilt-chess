"""
09_controlli_eval.py - Le partite con valutazioni del motore sono un campione distorto?

Su Lichess una partita ha le valutazioni solo se qualcuno ha chiesto l'analisi.
Se si chiede piu' spesso dopo una sconfitta (o dopo una partita "interessante"),
misurare gli errori solo su queste partite falserebbe il confronto.

Tre controlli (decisi nel piano, prima di guardare gli errori):
  1. Partite con e senza valutazioni: differenze standardizzate sulle
     caratteristiche (rating, lunghezza, cadenza, torneo, terminazione, risultato).
  2. Per giocatore: la probabilita' che una partita sia analizzata dipende dal
     suo risultato o dall'esito della partita precedente? E' il controllo che
     conta per il tilt. Regola: oltre il 10% di differenza relativa, gli errori
     dopo sconfitta si misurano solo sugli "analizzatori sistematici" e con il
     piano B (Stockfish in locale su un campione estratto a caso).
  3. Quanta parte delle partite analizzate viene da "analizzatori sistematici"
     (almeno 30 partite, almeno 80% analizzate): per loro la scelta non dipende
     dalla singola partita.

Uso (PowerShell, nella cartella C:\\tilt):
    .\\.venv\\Scripts\\python 09_controlli_eval.py
"""

import argparse

import pandas as pd

from tilt_utils import CARTELLA_DATI, CLASSI, Registro, apri_duckdb

LISTA_CLASSI = ", ".join(f"'{c}'" for c in CLASSI)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gruppo", choices=["esplorazione", "conferma"], default="esplorazione")
    parser.add_argument("--memoria", default="3GB")
    args = parser.parse_args()
    con = apri_duckdb(args.memoria)
    reg = Registro(f"09_controlli_eval_{args.gruppo}")
    partite = f"read_parquet('{(CARTELLA_DATI / 'partite.parquet').as_posix()}')"
    analisi = f"read_parquet('{(CARTELLA_DATI / 'analisi').as_posix()}/*.parquet')"

    # ---- Controllo 1: differenze standardizzate (tutte le partite; nessun confronto tra esiti di tilt)
    variabili = {
        "rating medio dei due": "(white_elo + black_elo) / 2.0",
        "differenza di rating (assoluta)": "ABS(white_elo - black_elo)",
        "semimosse": "n_clk",
        "bullet": "(speed = 'Bullet')::INTEGER", "blitz": "(speed = 'Blitz')::INTEGER",
        "classical (2017)": "(speed = 'Classical')::INTEGER",
        "torneo": "is_tournament::INTEGER",
        "finita per tempo": "(termination = 'Time forfeit')::INTEGER",
        "patta": "(result = '1/2-1/2')::INTEGER", "vince il Bianco": "(result = '1-0')::INTEGER",
    }
    colonne = ", ".join(f"AVG({e}) AS m{i}, VAR_SAMP({e}) AS v{i}" for i, e in enumerate(variabili.values()))
    r = con.execute(f"SELECT has_eval, COUNT(*) AS n, {colonne} FROM {partite} WHERE speed <> 'Correspondence' "
                    f"GROUP BY has_eval ORDER BY has_eval").df()
    senza, con_eval = r.iloc[0], r.iloc[1]
    righe = [(nome, senza[f"m{i}"], con_eval[f"m{i}"],
              (con_eval[f"m{i}"] - senza[f"m{i}"]) / ((con_eval[f"v{i}"] + senza[f"v{i}"]) / 2) ** 0.5)
             for i, nome in enumerate(variabili)]
    reg.tabella(f"Controllo 1 - partite senza valutazioni (n={int(senza['n']):,}) e con (n={int(con_eval['n']):,}). "
                "Differenza standardizzata: sotto 0,1 trascurabile, oltre 0,25 rilevante",
                pd.DataFrame(righe, columns=["variabile", "senza_eval", "con_eval", "diff_standardizzata"]).round(3))

    # ---- Controllo 2: l'analisi dipende dal risultato?
    base = f"FROM {analisi} WHERE gruppo = '{args.gruppo}' AND elig"
    t = con.execute(f"""
        SELECT 'risultato della partita stessa' AS rispetto_a, punteggio AS esito, COUNT(*) AS n,
               100.0 * AVG(has_eval::INTEGER) AS perc_analizzate {base} GROUP BY ALL
        UNION ALL
        SELECT 'esito della partita precedente (stesso blocco)', prec_punteggio, COUNT(*),
               100.0 * AVG(has_eval::INTEGER) {base} AND pos_blocco > 1 GROUP BY ALL
        ORDER BY 1, 2
    """).df()
    reg.tabella("Controllo 2a - quota di partite analizzate per esito (0 = sconfitta, 0.5 = patta, 1 = vittoria)", t.round(2))
    verdetti = []
    for nome, g in t.groupby("rispetto_a"):
        q = g.set_index("esito")["perc_analizzate"]
        rel = 100 * (q.get(0.0) / q.get(1.0) - 1)
        verdetti.append(f"{nome}: sconfitta contro vittoria = {rel:+.1f}% relativo "
                        f"({'OLTRE' if abs(rel) > 10 else 'entro'} la soglia del 10%)")
    # Stesso confronto dentro ogni giocatore (chi analizza a volte si', a volte no):
    # elimina il fatto che chi perde spesso potrebbe essere un tipo di giocatore che analizza di piu'.
    g = con.execute(f"""
        WITH per_giocatore AS (
            SELECT gid,
                   AVG(CASE WHEN punteggio = 0 THEN has_eval::INTEGER END) AS dopo_propria_sconfitta,
                   AVG(CASE WHEN punteggio = 1 THEN has_eval::INTEGER END) AS dopo_propria_vittoria,
                   AVG(CASE WHEN pos_blocco > 1 AND prec_punteggio = 0 THEN has_eval::INTEGER END) AS prec_sconfitta,
                   AVG(CASE WHEN pos_blocco > 1 AND prec_punteggio = 1 THEN has_eval::INTEGER END) AS prec_vittoria
            {base} GROUP BY gid
            HAVING COUNT(*) >= 30 AND AVG(has_eval::INTEGER) BETWEEN 0.05 AND 0.95
        )
        SELECT COUNT(*) AS giocatori,
               100 * AVG(dopo_propria_sconfitta) AS analizzate_se_persa, 100 * AVG(dopo_propria_vittoria) AS analizzate_se_vinta,
               100 * AVG(prec_sconfitta) AS analizzate_se_precedente_persa, 100 * AVG(prec_vittoria) AS analizzate_se_precedente_vinta
        FROM per_giocatore
    """).df()
    reg.tabella("Controllo 2b - stesso confronto dentro il giocatore (almeno 30 partite, tra 5% e 95% analizzate): medie delle quote individuali", g.round(2))
    reg.scrivi()
    for v in verdetti:
        reg.scrivi("VERDETTO " + v)

    # ---- Controllo 3: analizzatori sistematici
    s = con.execute(f"""
        WITH per_giocatore AS (
            SELECT gid, COUNT(*) AS n, SUM(has_eval::INTEGER) AS analizzate {base} GROUP BY gid
        )
        SELECT COUNT(*) AS giocatori,
               SUM((n >= 30 AND analizzate >= 0.8 * n)::INTEGER) AS sistematici,
               SUM(analizzate) AS partite_analizzate,
               100.0 * SUM(CASE WHEN n >= 30 AND analizzate >= 0.8 * n THEN analizzate ELSE 0 END) / SUM(analizzate) AS perc_da_sistematici,
               SUM((analizzate = 0)::INTEGER) AS giocatori_mai_analizzati
        FROM per_giocatore
    """).df()
    reg.tabella("Controllo 3 - analizzatori sistematici (almeno 30 partite, almeno 80% analizzate)", s.round(1))
    reg.chiudi()


if __name__ == "__main__":
    main()
