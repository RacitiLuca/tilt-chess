"""
03_riassunto.py - Riassunto del dataset completo con DuckDB (SQL)

Cosa fa:
  Interroga data/partite.parquet con SQL (DuckDB) e produce un riassunto
  da allegare a Fable: dimensioni del dataset, cadenze, quante partite gioca
  ogni giocatore e, soprattutto, quanto tempo passa tra una partita e la
  successiva dello stesso giocatore. Quest'ultimo dato serve a Fable per
  decidere come definire una "sessione" di gioco.

DuckDB e' un database che gira dentro Python, senza server, e legge i file
Parquet direttamente. Con il limite di memoria impostato sotto, se i dati
non entrano in RAM li appoggia temporaneamente su disco (cartella data/tmp).

Uso (PowerShell, nella cartella C:\\tilt):
    .\\.venv\\Scripts\\python 03_riassunto.py

Risultato: output/riassunto_dati.txt -> da allegare a Fable
"""

from pathlib import Path

import duckdb

FILE_PARTITE = "data/partite.parquet"

QUERY = {
    "Dimensioni generali": """
        SELECT
            count(*)                                  AS partite,
            min(start_utc)                            AS prima_partita,
            max(start_utc)                            AS ultima_partita,
            round(100 * avg((n_clk > 0)::INT), 1)     AS perc_con_orologio,
            round(100 * avg(has_eval::INT), 1)        AS perc_con_eval,
            round(100 * avg(is_tournament::INT), 1)   AS perc_in_torneo
        FROM partite
    """,
    "Per cadenza": """
        SELECT
            speed                                     AS cadenza,
            count(*)                                  AS partite,
            sum(has_eval::INT)::BIGINT                AS con_eval,
            median((white_elo + black_elo) / 2)       AS rating_medio_mediano,
            median(n_clk)                             AS semimosse_mediane
        FROM partite
        GROUP BY speed
        ORDER BY partite DESC
    """,
    "Terminazioni": """
        SELECT termination AS terminazione, count(*) AS partite,
               round(100 * count(*) / sum(count(*)) OVER (), 1) AS perc
        FROM partite GROUP BY termination ORDER BY partite DESC
    """,
    "Risultati": """
        SELECT result AS risultato, count(*) AS partite,
               round(100 * count(*) / sum(count(*)) OVER (), 1) AS perc
        FROM partite GROUP BY result ORDER BY partite DESC
    """,
    "Partite per giocatore": """
        WITH per_giocatore AS (
            SELECT giocatore, count(*) AS n
            FROM (SELECT white AS giocatore FROM partite
                  UNION ALL
                  SELECT black FROM partite)
            GROUP BY giocatore
        )
        SELECT
            count(*)                                  AS giocatori,
            quantile_cont(n, 0.5)                     AS mediana,
            quantile_cont(n, 0.9)                     AS p90,
            quantile_cont(n, 0.99)                    AS p99,
            max(n)                                    AS massimo,
            sum((n >= 20)::INT)::BIGINT               AS giocatori_almeno_20,
            sum((n >= 100)::INT)::BIGINT              AS giocatori_almeno_100
        FROM per_giocatore
    """,
    "Minuti tra l'inizio di una partita e l'inizio della successiva (stesso giocatore, stessa cadenza)": """
        WITH partite_giocatore AS (
            SELECT white AS giocatore, speed, start_utc FROM partite
            UNION ALL
            SELECT black, speed, start_utc FROM partite
        ),
        intervalli AS (
            SELECT
                speed,
                date_diff('second',
                          lag(start_utc) OVER (PARTITION BY giocatore, speed ORDER BY start_utc),
                          start_utc) / 60.0 AS minuti
            FROM partite_giocatore
        )
        SELECT
            speed                                     AS cadenza,
            count(minuti)                             AS coppie_di_partite,
            round(quantile_cont(minuti, 0.10), 1)     AS p10,
            round(quantile_cont(minuti, 0.25), 1)     AS p25,
            round(quantile_cont(minuti, 0.50), 1)     AS mediana,
            round(quantile_cont(minuti, 0.75), 1)     AS p75,
            round(quantile_cont(minuti, 0.90), 1)     AS p90
        FROM intervalli
        WHERE minuti IS NOT NULL
        GROUP BY speed
        ORDER BY coppie_di_partite DESC
    """,
}


def main():
    if not Path(FILE_PARTITE).exists():
        print(f"Non trovo {FILE_PARTITE}: esegui prima 02_estrai_partite.py")
        return

    Path("data/tmp").mkdir(parents=True, exist_ok=True)
    Path("output").mkdir(exist_ok=True)

    con = duckdb.connect()
    con.execute("SET memory_limit = '3GB'")          # lascia RAM libera al resto del PC
    con.execute("SET threads = 4")
    con.execute("SET temp_directory = 'data/tmp'")   # dove appoggiare i dati se la RAM non basta
    con.execute(f"CREATE VIEW partite AS SELECT * FROM read_parquet('{FILE_PARTITE}')")

    parti = ["RIASSUNTO DEL DATASET (data/partite.parquet)", ""]
    for titolo, query in QUERY.items():
        print(f"Calcolo: {titolo} ...")
        risultato = con.sql(query).df()
        parti += [f"== {titolo} ==", risultato.to_string(index=False), ""]

    testo = "\n".join(parti)
    with open("output/riassunto_dati.txt", "w", encoding="utf-8") as f:
        f.write(testo + "\n")

    print()
    print(testo)
    print("Riassunto salvato in: output/riassunto_dati.txt")


if __name__ == "__main__":
    main()
