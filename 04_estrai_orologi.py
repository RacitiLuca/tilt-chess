"""
04_estrai_orologi.py - Seconda passata: i tempi dell'orologio di TUTTE le partite

Perche' serve:
  partite.parquet non contiene i tempi dell'orologio, e senza quelli non si puo'
  stimare quando una partita e' finita (l'orario di fine non e' nelle intestazioni).
  La fine stimata serve per calcolare la pausa tra due partite, e quindi per
  definire le sessioni e la "partita successiva". Servono anche per il ritmo di
  gioco nelle prime 10 mosse, per i finali al "fotofinish" e per riconoscere il
  berserk nei tornei (tempo iniziale dimezzato).

Cosa fa:
  Rilegge il file Lichess in streaming e, per ogni partita e per ogni colore, salva:
    - primo orologio      = tempo rimasto dopo la prima mossa di quel giocatore
    - orologio mossa 10   = tempo rimasto dopo la sua decima mossa (vuoto se non ci arriva)
    - ultimo orologio     = tempo rimasto dopo la sua ultima mossa
    - numero di mosse     = quante mosse ha giocato (= quanti tempi registrati)
  I valori sono in secondi, esattamente come scritti nei commenti [%clk h:mm:ss].
  Le partite senza tempi hanno questi campi vuoti (NULL).

Risultato: data/orologi.parquet, una riga per partita, da unire a partite.parquet
con la colonna game_id.

Uso (PowerShell, nella cartella C:\\tilt):
  Prova veloce:   .\\.venv\\Scripts\\python 04_estrai_orologi.py data\\lichess_db_standard_rated_2017-05.pgn.zst --max 100000
  Tutto il mese:  .\\.venv\\Scripts\\python 04_estrai_orologi.py data\\lichess_db_standard_rated_2017-05.pgn.zst
"""

import argparse
import re
import time
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from pgn_utils import leggi_partite

DIMENSIONE_BLOCCO = 200_000

# Riconosce [%clk 0:04:58] (e, per sicurezza, anche eventuali decimali: [%clk 0:04:58.3])
REGEX_OROLOGIO = re.compile(r"\[%clk (\d+):(\d+):(\d+(?:\.\d+)?)\]")

SCHEMA = pa.schema([
    ("game_id", pa.string()),
    ("w_clk_first", pa.float32()),   # Bianco: secondi rimasti dopo la 1a mossa
    ("w_clk_m10", pa.float32()),     # Bianco: secondi rimasti dopo la 10a mossa
    ("w_clk_last", pa.float32()),    # Bianco: secondi rimasti dopo l'ultima mossa
    ("w_n_moves", pa.int16()),       # Bianco: mosse giocate con tempo registrato
    ("b_clk_first", pa.float32()),   # Nero: come sopra
    ("b_clk_m10", pa.float32()),
    ("b_clk_last", pa.float32()),
    ("b_n_moves", pa.int16()),
])


def riassunto_colore(tempi):
    """Da una lista di tempi (in secondi) di un colore -> (primo, mossa 10, ultimo, numero)."""
    if not tempi:
        return None, None, None, 0
    return tempi[0], (tempi[9] if len(tempi) >= 10 else None), tempi[-1], min(len(tempi), 32767)


def main():
    parser = argparse.ArgumentParser(description="Estrae i tempi dell'orologio di tutte le partite")
    parser.add_argument("file", help="file .pgn.zst di Lichess")
    parser.add_argument("--max", type=int, default=None, help="numero massimo di partite (per fare prove)")
    args = parser.parse_args()

    percorso = Path(args.file)
    file_output = Path("data") / "orologi.parquet"
    scrittore = pq.ParquetWriter(file_output, SCHEMA, compression="zstd")
    colonne = {nome: [] for nome in SCHEMA.names}

    totale = 0
    con_orologio = 0
    inizio = time.time()
    print(f"Estraggo gli orologi da {percorso.name} ... (aggiornamento ogni 500.000 partite)")

    try:
        for intestazioni, mosse, _ in leggi_partite(percorso):
            # Tutti i tempi della partita, in ordine: Bianco, Nero, Bianco, Nero, ...
            tempi = [int(h) * 3600 + int(m) * 60 + float(s) for h, m, s in REGEX_OROLOGIO.findall(mosse)]
            bianco = riassunto_colore(tempi[0::2])  # posizioni pari = mosse del Bianco
            nero = riassunto_colore(tempi[1::2])    # posizioni dispari = mosse del Nero
            con_orologio += bool(tempi)

            colonne["game_id"].append(intestazioni.get("Site", "").rsplit("/", 1)[-1])
            for prefisso, valori in (("w", bianco), ("b", nero)):
                colonne[f"{prefisso}_clk_first"].append(valori[0])
                colonne[f"{prefisso}_clk_m10"].append(valori[1])
                colonne[f"{prefisso}_clk_last"].append(valori[2])
                colonne[f"{prefisso}_n_moves"].append(valori[3])

            totale += 1
            if len(colonne["game_id"]) >= DIMENSIONE_BLOCCO:
                scrittore.write_table(pa.Table.from_pydict(colonne, schema=SCHEMA))
                for lista in colonne.values():
                    lista.clear()

            if totale % 500_000 == 0:
                trascorso = time.time() - inizio
                print(f"  {totale:,} partite - {trascorso / 60:.1f} min - {totale / trascorso:,.0f} partite/s")

            if args.max and totale >= args.max:
                break

        if colonne["game_id"]:
            scrittore.write_table(pa.Table.from_pydict(colonne, schema=SCHEMA))
    finally:
        scrittore.close()

    trascorso = time.time() - inizio
    print()
    print(f"Fatto in {trascorso / 60:.1f} minuti.")
    print(f"Partite: {totale:,}, di cui con orologio: {con_orologio:,} ({100 * con_orologio / max(totale, 1):.1f}%)")
    print(f"File creato: {file_output} ({file_output.stat().st_size / 1e6:,.0f} MB)")


if __name__ == "__main__":
    main()
