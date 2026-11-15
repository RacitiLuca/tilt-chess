"""
01_campione.py - Primo sguardo ai dati (qualche minuto)

Cosa fa:
  1. Legge l'inizio del file Lichess in streaming (senza decomprimerlo su disco).
  2. Calcola statistiche di base sulle prime N partite (default 200.000):
     quante hanno i tempi dell'orologio, quante le valutazioni del motore,
     cadenze, risultati, quante partite gioca ogni giocatore, ecc.
  3. Salva un piccolo campione di partite (20 qualsiasi + 10 con valutazioni)
     da allegare a Fable, cosi' vede la struttura reale dei dati.

Uso (PowerShell, nella cartella C:\\tilt):
    .\\.venv\\Scripts\\python 01_campione.py data\\lichess_db_standard_rated_2017-05.pgn.zst

Risultati nella cartella "output":
    campione_partite.pgn       -> da allegare a Fable
    statistiche_campione.txt   -> da allegare a Fable
"""

import sys
import time
from collections import Counter
from pathlib import Path

from pgn_utils import cadenza, data_ora, intero, leggi_partite

N_PARTITE = 200_000      # quante partite analizzare per le statistiche
N_CAMPIONE_NORMALI = 20  # partite qualsiasi da salvare nel campione
N_CAMPIONE_EVAL = 10     # partite con valutazioni del motore da salvare


def percentuale(parte, totale):
    return f"{100 * parte / totale:.1f}%" if totale else "n/d"


def main():
    if len(sys.argv) < 2:
        print("Uso: python 01_campione.py <file .pgn.zst>")
        sys.exit(1)

    percorso = Path(sys.argv[1])
    if not percorso.exists():
        print(f"File non trovato: {percorso}")
        sys.exit(1)

    cartella_output = Path("output")
    cartella_output.mkdir(exist_ok=True)

    # Contatori per le statistiche
    totale = 0
    con_orologio = 0
    con_eval = 0
    cadenze = Counter()
    risultati = Counter()
    terminazioni = Counter()
    controlli_tempo = Counter()
    partite_per_giocatore = Counter()
    in_torneo = 0
    rating = []
    chiavi_intestazioni = Counter()
    ordine_non_crescente = 0
    ultimo_inizio = None
    primo_inizio = None

    campione_normali = []
    campione_eval = []

    inizio = time.time()
    print(f"Leggo le prime {N_PARTITE:,} partite di {percorso.name} ...")

    for intestazioni, mosse, testo in leggi_partite(percorso, con_testo=True):
        totale += 1

        ha_orologio = "[%clk" in mosse
        ha_eval = "[%eval" in mosse
        con_orologio += ha_orologio
        con_eval += ha_eval

        event = intestazioni.get("Event", "")
        cadenze[cadenza(event)] += 1
        in_torneo += "tournament" in event or "swiss" in event
        risultati[intestazioni.get("Result")] += 1
        terminazioni[intestazioni.get("Termination")] += 1
        controlli_tempo[intestazioni.get("TimeControl")] += 1
        partite_per_giocatore[intestazioni.get("White")] += 1
        partite_per_giocatore[intestazioni.get("Black")] += 1
        chiavi_intestazioni.update(intestazioni.keys())

        for chiave in ("WhiteElo", "BlackElo"):
            valore = intero(intestazioni.get(chiave))
            if valore is not None:
                rating.append(valore)

        # Le partite sono in ordine cronologico? (serve per ricostruire le sessioni)
        inizio_partita = data_ora(intestazioni.get("UTCDate"), intestazioni.get("UTCTime"))
        if inizio_partita:
            if primo_inizio is None:
                primo_inizio = inizio_partita
            if ultimo_inizio and inizio_partita < ultimo_inizio:
                ordine_non_crescente += 1
            ultimo_inizio = inizio_partita

        if len(campione_normali) < N_CAMPIONE_NORMALI:
            campione_normali.append(testo)
        if ha_eval and len(campione_eval) < N_CAMPIONE_EVAL:
            campione_eval.append(testo)

        if totale >= N_PARTITE:
            break

    durata = time.time() - inizio

    # --- Salvo il campione di partite ---
    with open(cartella_output / "campione_partite.pgn", "w", encoding="utf-8") as f:
        f.write("".join(campione_normali))
        f.write("".join(campione_eval))

    # --- Preparo il testo delle statistiche ---
    rating.sort()

    def quantile(lista, q):
        return lista[int(q * (len(lista) - 1))] if lista else None

    giocate = sorted(partite_per_giocatore.values())
    righe = [
        f"STATISTICHE SULLE PRIME {totale:,} PARTITE DI {percorso.name}",
        f"(lette in {durata:.0f} secondi, circa {totale / max(durata, 1):,.0f} partite al secondo)",
        "",
        f"Periodo coperto dal campione: da {primo_inizio} a {ultimo_inizio}",
        f"Partite con tempi dell'orologio [%clk]: {con_orologio:,} ({percentuale(con_orologio, totale)})",
        f"Partite con valutazioni del motore [%eval]: {con_eval:,} ({percentuale(con_eval, totale)})",
        f"Partite giocate in un torneo: {in_torneo:,} ({percentuale(in_torneo, totale)})",
        f"Partite con orario di inizio precedente alla partita prima nel file: {ordine_non_crescente:,} "
        f"({percentuale(ordine_non_crescente, totale)}) -> se alto, il file non e' in ordine cronologico",
        "",
        "Cadenze:",
        *[f"  {k}: {v:,} ({percentuale(v, totale)})" for k, v in cadenze.most_common()],
        "",
        "Controlli di tempo piu' frequenti (secondi iniziali + incremento):",
        *[f"  {k}: {v:,} ({percentuale(v, totale)})" for k, v in controlli_tempo.most_common(10)],
        "",
        "Risultati:",
        *[f"  {k}: {v:,} ({percentuale(v, totale)})" for k, v in risultati.most_common()],
        "",
        "Terminazioni:",
        *[f"  {k}: {v:,} ({percentuale(v, totale)})" for k, v in terminazioni.most_common()],
        "",
        "Rating (Glicko-2) dei giocatori:",
        f"  minimo {quantile(rating, 0)}, 10% {quantile(rating, 0.1)}, mediana {quantile(rating, 0.5)}, "
        f"90% {quantile(rating, 0.9)}, massimo {quantile(rating, 1)}",
        "",
        f"Giocatori diversi nel campione: {len(giocate):,}",
        f"Partite per giocatore: mediana {quantile(giocate, 0.5)}, 90% {quantile(giocate, 0.9)}, "
        f"99% {quantile(giocate, 0.99)}, massimo {quantile(giocate, 1)}",
        f"Giocatori con almeno 10 partite nel campione: {sum(1 for g in giocate if g >= 10):,}",
        "",
        "Intestazioni presenti (quante partite le hanno):",
        *[f"  {k}: {v:,}" for k, v in chiavi_intestazioni.most_common()],
    ]
    testo_statistiche = "\n".join(righe)

    with open(cartella_output / "statistiche_campione.txt", "w", encoding="utf-8") as f:
        f.write(testo_statistiche + "\n")

    print()
    print(testo_statistiche)
    print()
    print(f"Campione salvato in: {cartella_output / 'campione_partite.pgn'} "
          f"({len(campione_normali)} partite qualsiasi + {len(campione_eval)} con valutazioni)")
    print(f"Statistiche salvate in: {cartella_output / 'statistiche_campione.txt'}")


if __name__ == "__main__":
    main()
