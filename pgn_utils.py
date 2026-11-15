"""
pgn_utils.py - Funzioni comuni per leggere i file Lichess (.pgn.zst).

Questo file non si esegue da solo: lo usano gli altri script.

Idea chiave: i file di Lichess sono compressi con zstd e, decompressi, pesano
decine di GB. Con 8 GB di RAM non possiamo caricarli in memoria. Quindi li
leggiamo in STREAMING: decomprimiamo un pezzo alla volta e leggiamo il testo
riga per riga, tenendo in memoria una sola partita alla volta.
"""

import io
from datetime import datetime

import zstandard


def apri_pgn_zst(percorso):
    """Apre un file .pgn.zst e restituisce un flusso di testo da leggere riga per riga.

    Il file NON viene decompresso su disco: la decompressione avviene al volo.
    max_window_size alto evita errori con file compressi con finestre grandi.
    """
    file_binario = open(percorso, "rb")
    decompressore = zstandard.ZstdDecompressor(max_window_size=2**31)
    lettore = decompressore.stream_reader(file_binario, read_size=2**20)
    return io.TextIOWrapper(lettore, encoding="utf-8", errors="replace")


def leggi_partite(percorso, con_testo=False):
    """Generatore: restituisce le partite una alla volta.

    Per ogni partita restituisce una tupla:
      - intestazioni: dizionario, es. {"White": "pippo", "Result": "1-0", ...}
      - mosse: stringa con le mosse e i commenti, es. "1. e4 { [%clk 0:05:00] } ..."
      - testo: il testo PGN originale della partita (solo se con_testo=True)

    Formato PGN di Lichess: ogni partita inizia con la riga [Event "..."],
    seguono le altre intestazioni [Chiave "Valore"], una riga vuota,
    la riga delle mosse e un'altra riga vuota.
    """
    intestazioni = {}
    mosse = []
    righe = []

    with apri_pgn_zst(percorso) as testo:
        for riga in testo:
            # Una nuova riga [Event ...] significa che la partita precedente e' finita
            if riga.startswith("[Event ") and intestazioni:
                yield intestazioni, " ".join(mosse), ("".join(righe) if con_testo else None)
                intestazioni, mosse, righe = {}, [], []

            if con_testo:
                righe.append(riga)

            riga = riga.strip()
            if not riga:
                continue

            if riga[0] == "[":
                # Esempio: [WhiteElo "1500"]  ->  chiave = WhiteElo, valore = 1500
                spazio = riga.find(" ")
                chiave = riga[1:spazio]
                valore = riga[spazio + 2 : -2]  # toglie lo spazio+virgolette iniziali e le virgolette+parentesi finali
                intestazioni[chiave] = valore
            else:
                mosse.append(riga)

        # L'ultima partita del file
        if intestazioni:
            yield intestazioni, " ".join(mosse), ("".join(righe) if con_testo else None)


def intero(valore):
    """Converte in intero ("1500" -> 1500, "+12" -> 12). Restituisce None se non e' un numero (es. "?")."""
    if valore is None:
        return None
    try:
        return int(valore)
    except ValueError:
        return None


def data_ora(utc_date, utc_time):
    """Unisce UTCDate ("2017.05.01") e UTCTime ("13:45:10") in un datetime. None se mancano."""
    try:
        return datetime(
            int(utc_date[0:4]), int(utc_date[5:7]), int(utc_date[8:10]),
            int(utc_time[0:2]), int(utc_time[3:5]), int(utc_time[6:8]),
        )
    except (TypeError, ValueError):
        return None


def cadenza(event):
    """Ricava la cadenza dal campo Event.

    Esempi: "Rated Blitz game" -> "Blitz"; "Rated Bullet tournament https://..." -> "Bullet".
    """
    parti = (event or "").split()
    return parti[1] if len(parti) > 1 else None
