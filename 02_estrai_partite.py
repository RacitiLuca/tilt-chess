"""
02_estrai_partite.py - Trasforma tutto il mese di partite in tabelle Parquet

Cosa fa:
  Legge TUTTO il file Lichess in streaming e crea due file Parquet nella cartella "data":

  1. partite.parquet -> una riga per partita: giocatori, rating, risultato, orario
     di inizio, cadenza, terminazione, numero di mosse con tempo, presenza di
     valutazioni del motore. E' la base per studiare il tilt (sequenze di partite
     dello stesso giocatore).

  2. mosse_con_eval.parquet -> solo per le partite con valutazioni del motore
     (circa il 6%): il testo completo delle mosse, con valutazioni e tempi.
     Servira' per misurare gli errori e la pressione del tempo, senza dover
     rileggere il file enorme.

Perche' Parquet: e' un formato a colonne compresso, molto piu' leggero del testo,
e DuckDB lo interroga in SQL velocemente anche con poca RAM.

La memoria resta bassa: le righe vengono scritte su disco a blocchi di 200.000.

Uso (PowerShell, nella cartella C:\\tilt):
    .\\.venv\\Scripts\\python 02_estrai_partite.py data\\lichess_db_standard_rated_2017-05.pgn.zst

Per una prova veloce su poche partite:
    .\\.venv\\Scripts\\python 02_estrai_partite.py data\\lichess_db_standard_rated_2017-05.pgn.zst --max 100000
"""

import argparse
import time
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from pgn_utils import cadenza, data_ora, intero, leggi_partite

DIMENSIONE_BLOCCO = 200_000

SCHEMA_PARTITE = pa.schema([
    ("game_id", pa.string()),            # codice della partita su lichess.org
    ("event", pa.string()),              # es. "Rated Blitz game"
    ("speed", pa.string()),              # Bullet, Blitz, Rapid, Classical, ...
    ("is_tournament", pa.bool_()),
    ("white", pa.string()),
    ("black", pa.string()),
    ("result", pa.string()),             # "1-0", "0-1", "1/2-1/2"
    ("start_utc", pa.timestamp("s")),    # orario di inizio (UTC)
    ("white_elo", pa.int16()),
    ("black_elo", pa.int16()),
    ("white_rating_diff", pa.int16()),   # variazione di rating dopo la partita
    ("black_rating_diff", pa.int16()),
    ("white_title", pa.string()),        # GM, IM, BOT, ... (se presente)
    ("black_title", pa.string()),
    ("eco", pa.string()),
    ("opening", pa.string()),
    ("time_control", pa.string()),       # es. "300+0" = 5 minuti, nessun incremento
    ("termination", pa.string()),        # Normal, Time forfeit, Abandoned, ...
    ("n_clk", pa.int16()),               # mosse con tempo registrato (circa = semimosse)
    ("has_eval", pa.bool_()),
])

SCHEMA_MOSSE = pa.schema([
    ("game_id", pa.string()),
    ("movetext", pa.string()),
])


def colonne_vuote(schema):
    return {nome: [] for nome in schema.names}


def scrivi_blocco(scrittore, colonne, schema):
    tabella = pa.Table.from_pydict(colonne, schema=schema)
    scrittore.write_table(tabella)
    for lista in colonne.values():
        lista.clear()


def main():
    parser = argparse.ArgumentParser(description="Estrae le partite Lichess in Parquet")
    parser.add_argument("file", help="file .pgn.zst di Lichess")
    parser.add_argument("--max", type=int, default=None, help="numero massimo di partite (per fare prove)")
    args = parser.parse_args()

    percorso = Path(args.file)
    cartella_dati = Path("data")
    cartella_dati.mkdir(exist_ok=True)
    file_partite = cartella_dati / "partite.parquet"
    file_mosse = cartella_dati / "mosse_con_eval.parquet"

    scrittore_partite = pq.ParquetWriter(file_partite, SCHEMA_PARTITE, compression="zstd")
    scrittore_mosse = pq.ParquetWriter(file_mosse, SCHEMA_MOSSE, compression="zstd")
    colonne = colonne_vuote(SCHEMA_PARTITE)
    colonne_mosse = colonne_vuote(SCHEMA_MOSSE)

    totale = 0
    totale_eval = 0
    inizio = time.time()
    print(f"Estraggo le partite da {percorso.name} ... (aggiornamento ogni 500.000 partite)")

    try:
        for intestazioni, mosse, _ in leggi_partite(percorso):
            get = intestazioni.get
            event = get("Event", "")
            game_id = get("Site", "").rsplit("/", 1)[-1]
            ha_eval = "[%eval" in mosse

            colonne["game_id"].append(game_id)
            colonne["event"].append(event)
            colonne["speed"].append(cadenza(event))
            colonne["is_tournament"].append("tournament" in event or "swiss" in event)
            colonne["white"].append(get("White"))
            colonne["black"].append(get("Black"))
            colonne["result"].append(get("Result"))
            colonne["start_utc"].append(data_ora(get("UTCDate"), get("UTCTime")))
            colonne["white_elo"].append(intero(get("WhiteElo")))
            colonne["black_elo"].append(intero(get("BlackElo")))
            colonne["white_rating_diff"].append(intero(get("WhiteRatingDiff")))
            colonne["black_rating_diff"].append(intero(get("BlackRatingDiff")))
            colonne["white_title"].append(get("WhiteTitle"))
            colonne["black_title"].append(get("BlackTitle"))
            colonne["eco"].append(get("ECO"))
            colonne["opening"].append(get("Opening"))
            colonne["time_control"].append(get("TimeControl"))
            colonne["termination"].append(get("Termination"))
            colonne["n_clk"].append(min(mosse.count("[%clk"), 32767))
            colonne["has_eval"].append(ha_eval)

            if ha_eval:
                colonne_mosse["game_id"].append(game_id)
                colonne_mosse["movetext"].append(mosse)
                totale_eval += 1

            totale += 1

            if len(colonne["game_id"]) >= DIMENSIONE_BLOCCO:
                scrivi_blocco(scrittore_partite, colonne, SCHEMA_PARTITE)
            if len(colonne_mosse["game_id"]) >= DIMENSIONE_BLOCCO:
                scrivi_blocco(scrittore_mosse, colonne_mosse, SCHEMA_MOSSE)

            if totale % 500_000 == 0:
                trascorso = time.time() - inizio
                print(f"  {totale:,} partite ({totale_eval:,} con valutazioni) - "
                      f"{trascorso / 60:.1f} min - {totale / trascorso:,.0f} partite/s")

            if args.max and totale >= args.max:
                break

        # Scrivo le ultime righe rimaste
        if colonne["game_id"]:
            scrivi_blocco(scrittore_partite, colonne, SCHEMA_PARTITE)
        if colonne_mosse["game_id"]:
            scrivi_blocco(scrittore_mosse, colonne_mosse, SCHEMA_MOSSE)
    finally:
        scrittore_partite.close()
        scrittore_mosse.close()

    trascorso = time.time() - inizio
    print()
    print(f"Fatto in {trascorso / 60:.1f} minuti.")
    print(f"Partite estratte: {totale:,} -> {file_partite} ({file_partite.stat().st_size / 1e6:,.0f} MB)")
    print(f"Partite con valutazioni: {totale_eval:,} -> {file_mosse} ({file_mosse.stat().st_size / 1e6:,.0f} MB)")


if __name__ == "__main__":
    main()
