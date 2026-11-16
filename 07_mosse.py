"""
07_mosse.py - Una riga per mossa: valutazione, probabilita' di vittoria persa, tempo

Cosa fa:
  Legge data/mosse_con_eval.parquet (testo delle mosse delle partite analizzate
  dal motore) e crea:

  1. data/mosse.parquet -> una riga per semimossa: orologio, valutazione,
     perdita di probabilita' di vittoria, giudizio (imprecisione, errore, errore grave).
  2. data/errori_partita.parquet -> una riga per (partita, colore): perdita
     media e numero di errori. E' l'esito secondario per la domanda 1.

Uso (PowerShell, nella cartella C:\\tilt):
    .\\.venv\\Scripts\\python 07_mosse.py
Prova veloce sulle prime 20.000 partite:
    .\\.venv\\Scripts\\python 07_mosse.py --max 20000
"""

import argparse
import re
import time

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from tilt_utils import CARTELLA_DATI, apri_duckdb

# Una mossa nel testo di Lichess:  "12... Qd7? { [%eval 0.47] [%clk 0:04:34] }"
#   gruppo 1 = mossa (con eventuali ?! ? ??), 2 = valutazione, 3-5 = ore, minuti, secondi
RE_MOSSA = re.compile(
    r"(?:\d+\.+\s+)?([^\s{}]+)\s+\{\s*(?:\[%eval\s+([^\]]+)\]\s*)?(?:\[%clk\s+(\d+):(\d\d):(\d\d)\]\s*)?\}"
)
K_WIN = 0.00368208
CP_MAX = 1000.0

SCHEMA = pa.schema([
    ("game_id", pa.string()),
    ("semimossa", pa.int16()),       # 1 = prima mossa del Bianco, 2 = prima del Nero, ...
    ("bianco", pa.bool_()),          # chi ha mosso
    ("clk", pa.int32()),             # secondi sull'orologio di chi ha mosso, DOPO la mossa
    ("clk_prima", pa.int32()),       # secondi che aveva PRIMA di pensare (tempo residuo)
    ("cp", pa.int16()),              # valutazione dopo la mossa, centipedoni, lato Bianco, limitata a +-1000
    ("win_prima", pa.float32()),     # Win% di chi muove prima della mossa
    ("perdita", pa.float32()),       # Win% persa con la mossa (puo' essere negativa: rumore del motore)
    ("giudizio", pa.int8()),         # 0 nessuno, 1 imprecisione, 2 errore, 3 errore grave
    ("cattura", pa.bool_()),
    ("n_catture", pa.int16()),       # catture gia' avvenute prima della mossa (misura del materiale scambiato)
])


def win_percento(cp):
    """Probabilita' di vittoria del Bianco (0-100) da una valutazione in centipedoni."""
    return 50.0 + 50.0 * (2.0 / (1.0 + np.exp(-K_WIN * cp)) - 1.0)


def elabora_blocco(ids, testi):
    """Trasforma un blocco di partite in colonne, una riga per semimossa."""
    partita, cp, clk, cattura, matto_dato = [], [], [], [], []
    for i, testo in enumerate(testi):
        for m in RE_MOSSA.finditer(testo):
            mossa, val, ore, minuti, secondi = m.groups()
            partita.append(i)
            cattura.append("x" in mossa)
            matto_dato.append(mossa[-1] == "#" or mossa.rstrip("?!")[-1] == "#")
            if val is None:
                cp.append(np.nan)
            elif val[0] == "#":                       # "#3" = matto in 3 per il Bianco, "#-3" per il Nero
                cp.append(-CP_MAX if val[1] == "-" else CP_MAX)
            else:
                cp.append(round(float(val) * 100.0))   # arrotondo: 2.03 * 100 = 202.99999... in virgola mobile
            clk.append(-1 if ore is None else int(ore) * 3600 + int(minuti) * 60 + int(secondi))
    if not partita:
        return None

    partita = np.asarray(partita, dtype=np.int64)
    n = len(partita)
    nuova = np.r_[True, partita[1:] != partita[:-1]]          # prima semimossa di ogni partita
    inizio = np.maximum.accumulate(np.where(nuova, np.arange(n), 0))
    semimossa = np.arange(n) - inizio + 1
    bianco = semimossa % 2 == 1
    cp = np.clip(np.asarray(cp, dtype=np.float64), -CP_MAX, CP_MAX)
    # La mossa che da' matto di solito non ha valutazione: vale +1000 per chi l'ha data.
    matto_dato = np.asarray(matto_dato, dtype=bool) & np.isnan(cp)
    cp[matto_dato] = np.where(bianco[matto_dato], CP_MAX, -CP_MAX)

    # Win% del Bianco dopo ogni mossa, e dopo la mossa precedente (= prima di questa)
    win_dopo_b = win_percento(cp)
    win_prima_b = np.r_[np.nan, win_dopo_b[:-1]]
    win_prima_b[nuova] = np.nan                               # la prima mossa non ha un "prima"
    # Dal punto di vista di chi muove: per il Nero e' 100 - Win% del Bianco
    win_prima = np.where(bianco, win_prima_b, 100.0 - win_prima_b)
    win_dopo = np.where(bianco, win_dopo_b, 100.0 - win_dopo_b)
    perdita = win_prima - win_dopo
    giudizio = np.zeros(n, dtype=np.int8)
    with np.errstate(invalid="ignore"):
        giudizio[perdita >= 5] = 1
        giudizio[perdita >= 10] = 2
        giudizio[perdita >= 15] = 3
    senza_perdita = np.isnan(perdita)

    # Tempo residuo: l'orologio dello stesso giocatore due semimosse prima.
    # Nelle prime due semimosse l'orologio non e' ancora partito: uso quello della mossa stessa.
    clk = np.asarray(clk, dtype=np.int64)
    clk_prima = np.r_[clk[:2], clk[:-2]]
    clk_prima[semimossa <= 2] = clk[semimossa <= 2]

    cattura = np.asarray(cattura, dtype=bool)
    cumulate = np.cumsum(cattura) - cattura                   # catture prima di questa riga, su tutto il blocco
    n_catture = cumulate - cumulate[inizio]                   # ...meno quelle delle partite precedenti

    return pa.Table.from_arrays([
        pa.array(np.asarray(ids, dtype=object)[partita], type=pa.string()),
        pa.array(semimossa, type=pa.int16()),
        pa.array(bianco),
        pa.array(clk, type=pa.int32(), mask=clk < 0),
        pa.array(clk_prima, type=pa.int32(), mask=clk_prima < 0),
        pa.array(np.nan_to_num(cp), type=pa.int16(), mask=np.isnan(cp)),
        pa.array(win_prima.astype(np.float32), mask=np.isnan(win_prima)),
        pa.array(perdita.astype(np.float32), mask=senza_perdita),
        pa.array(giudizio, type=pa.int8(), mask=senza_perdita),
        pa.array(cattura),
        pa.array(n_catture, type=pa.int16()),
    ], schema=SCHEMA)


def main():
    parser = argparse.ArgumentParser(description="Estrae valutazioni e tempi mossa per mossa")
    parser.add_argument("--max", type=int, default=None, help="numero massimo di partite (per fare prove)")
    parser.add_argument("--memoria", default="4GB")
    args = parser.parse_args()

    sorgente = pq.ParquetFile(CARTELLA_DATI / "mosse_con_eval.parquet")
    file_mosse = CARTELLA_DATI / "mosse.parquet"
    scrittore = pq.ParquetWriter(file_mosse, SCHEMA, compression="zstd")
    partite = righe = 0
    inizio = time.time()
    try:
        # 20.000 partite alla volta: circa 1,3 milioni di righe in memoria, poi su disco.
        for blocco in sorgente.iter_batches(batch_size=20_000, columns=["game_id", "movetext"]):
            ids = blocco.column("game_id").to_pylist()
            testi = blocco.column("movetext").to_pylist()
            if args.max and partite + len(ids) > args.max:
                ids, testi = ids[:args.max - partite], testi[:args.max - partite]
            tabella = elabora_blocco(ids, testi)
            if tabella is not None:
                scrittore.write_table(tabella)
                righe += tabella.num_rows
            partite += len(ids)
            if partite % 100_000 == 0:
                print(f"  {partite:,} partite, {righe:,} mosse - {time.time() - inizio:.0f} s")
            if args.max and partite >= args.max:
                break
    finally:
        scrittore.close()
    print(f"Mosse: {righe:,} righe da {partite:,} partite -> {file_mosse} ({time.time() - inizio:.0f} s)")

    # Riassunto per (partita, colore). La perdita negativa (rumore) conta come zero nella media.
    con = apri_duckdb(args.memoria)
    file_errori = CARTELLA_DATI / "errori_partita.parquet"
    con.execute(f"""
        COPY (
            SELECT game_id, bianco,
                   COUNT(perdita) AS mosse_valutate,
                   AVG(GREATEST(perdita, 0)) AS perdita_media,
                   SUM((giudizio = 1)::INTEGER) AS imprecisioni,
                   SUM((giudizio = 2)::INTEGER) AS errori,
                   SUM((giudizio = 3)::INTEGER) AS errori_gravi
            FROM read_parquet('{file_mosse.as_posix()}')
            GROUP BY game_id, bianco
        ) TO '{file_errori.as_posix()}' (FORMAT parquet, COMPRESSION zstd)
    """)
    print(con.sql(f"""
        SELECT COUNT(*) AS righe_partita_colore, ROUND(AVG(mosse_valutate), 1) AS mosse_valutate_medie,
               ROUND(AVG(perdita_media), 2) AS perdita_media_pp,
               ROUND(AVG(imprecisioni), 2) AS imprecisioni, ROUND(AVG(errori), 2) AS errori,
               ROUND(AVG(errori_gravi), 2) AS errori_gravi
        FROM read_parquet('{file_errori.as_posix()}')
    """).df().to_string(index=False))
    print(f"Riassunto per partita -> {file_errori}")


if __name__ == "__main__":
    main()
