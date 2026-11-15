"""
tilt_utils.py - Funzioni comuni agli script di analisi (da 05 in poi).

Questo file non si esegue da solo: lo usano gli altri script.
"""

from pathlib import Path

import duckdb

CARTELLA_DATI = Path("data")
CARTELLA_OUTPUT = Path("output")

# Classi di cadenza analizzate (soglie attuali di Lichess, vedi 05_sessioni.py)
CLASSI = ("bullet", "blitz", "rapid")

# Quota di giocatori usata per sviluppare il codice (gruppo "esplorazione").
# Il resto (gruppo "conferma") si analizza una volta sola, a codice bloccato.
PERCENTO_ESPLORAZIONE = 20


def apri_duckdb(memoria="4GB", file_db=None):
    """Apre DuckDB con un limite di memoria adatto a un PC da 8 GB.

    - memory_limit: oltre questa soglia DuckDB scrive i dati intermedi su disco
      (cartella temp_directory) invece di esaurire la RAM.
    - preserve_insertion_order=false: permette a DuckDB di lavorare a blocchi
      senza ricordare l'ordine di lettura (noi ordiniamo sempre in modo esplicito).
    - file_db: se indicato, le tabelle intermedie stanno in un file su disco.
    """
    CARTELLA_DATI.mkdir(exist_ok=True)
    cartella_tmp = CARTELLA_DATI / "tmp_duckdb"
    cartella_tmp.mkdir(exist_ok=True)
    con = duckdb.connect(str(file_db) if file_db else ":memory:")
    con.execute(f"SET memory_limit = '{memoria}'")
    con.execute(f"SET temp_directory = '{cartella_tmp.as_posix()}'")
    con.execute("SET preserve_insertion_order = false")
    return con


class Registro:
    """Stampa a schermo e, insieme, salva lo stesso testo in output/<nome>.txt."""

    def __init__(self, nome):
        CARTELLA_OUTPUT.mkdir(exist_ok=True)
        self.percorso = CARTELLA_OUTPUT / f"{nome}.txt"
        self.file = open(self.percorso, "w", encoding="utf-8")

    def scrivi(self, testo=""):
        print(testo)
        self.file.write(str(testo) + "\n")
        self.file.flush()

    def tabella(self, titolo, df):
        self.scrivi()
        self.scrivi(f"== {titolo} ==")
        self.scrivi(df.to_string(index=False))

    def chiudi(self):
        self.file.close()
        print(f"\nRisultati salvati in {self.percorso}")
