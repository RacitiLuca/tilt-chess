"""
tests/simula_dati.py - Dati SIMULATI con un effetto tilt noto, per collaudare gli stimatori

Perche' esiste:
  Prima di fidarmi di uno stimatore sui dati veri, lo provo su dati inventati in
  cui conosco la risposta. Qui ogni giocatore ha una forza vera, una "forma" che
  cambia a ogni sessione (la giornata storta), un rating con errore, e - se lo
  chiedo - un calo di forza nella partita subito dopo una sconfitta (il tilt).
  Se gli script 05-08 ritrovano l'effetto inserito (e zero quando non c'e'),
  il metodo e' collaudato.

Crea data/partite.parquet e data/orologi.parquet con lo stesso formato dei dati veri.

Uso (da una cartella di prova, NON dalla cartella dei dati veri):
    python ..\\tests\\simula_dati.py --tilt 0      (nessun tilt)
    python ..\\tests\\simula_dati.py --tilt 30     (30 punti Elo persi dopo una sconfitta)
"""

import argparse
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

CONTROLLI = [("60+0", "Bullet", 60), ("180+0", "Blitz", 180), ("300+0", "Blitz", 300), ("600+0", "Classical", 600)]
ALFABETO = np.array(list("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"))


def atteso_elo(diff):
    return 1.0 / (1.0 + 10 ** (-diff / 400.0))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tilt", type=float, default=0.0, help="punti Elo persi nella partita dopo una sconfitta")
    parser.add_argument("--tilt2", type=float, default=0.0, help="punti Elo persi se la partita di DUE prima era una sconfitta")
    parser.add_argument("--forma", type=float, default=40.0, help="deviazione standard della forma di sessione (Elo)")
    parser.add_argument("--stop-sconfitta", type=float, default=0.19,
                        help="probabilita' di chiudere la sessione dopo una sconfitta (dopo vittoria o patta: 0.15)")
    parser.add_argument("--giocatori", type=int, default=4000)
    parser.add_argument("--seme", type=int, default=1)
    args = parser.parse_args()

    rng = np.random.default_rng(args.seme)
    P = args.giocatori
    forza = rng.normal(1600, 250, P)
    rating0 = forza + rng.normal(0, 40, P)          # il rating iniziale ha un errore
    preferito = rng.choice(len(CONTROLLI), size=P, p=[0.3, 0.2, 0.3, 0.2])
    t0 = datetime(2017, 5, 1)

    righe, orologi = [], []
    n_fantasmi = 0
    for i in range(P):
        rating = float(round(rating0[i]))
        nome = f"giocatore{i:05d}"
        inizi = np.sort(rng.uniform(0, 30 * 86400, rng.poisson(28)))
        libero = 0.0
        for inizio_sess in inizi:
            t = max(inizio_sess, libero + 3600)      # almeno un'ora tra due sessioni
            forma = rng.normal(0, args.forma)
            tc, speed, base = CONTROLLI[preferito[i] if rng.random() < 0.9 else rng.integers(len(CONTROLLI))]
            torneo = rng.random() < 0.10
            prec_esito, prec2_esito, prec_avv, prec_rating_avv, pos = None, None, None, None, 0
            while True:
                pos += 1
                if prec_avv is not None and rng.random() < 0.12:      # rivincita
                    avv, rating_avv = prec_avv, prec_rating_avv
                    forza_avv = rating_avv + rng.normal(0, 60)
                else:
                    n_fantasmi += 1
                    avv = f"fantasma{n_fantasmi:07d}"
                    rating_avv = float(round(rating + rng.normal(0, 40)))
                    forza_avv = rating_avv + rng.normal(0, 60)
                bianco = rng.random() < 0.5
                mia_forza = forza[i] + forma - (args.tilt if prec_esito == 0.0 else 0.0) - (args.tilt2 if prec2_esito == 0.0 else 0.0)
                p_vittoria = atteso_elo(mia_forza - forza_avv + (35 if bianco else -35))
                u = rng.random()
                punteggio = 0.5 if u < 0.04 else (1.0 if rng.random() < p_vittoria else 0.0)
                diff = int(round(20 * (punteggio - atteso_elo(rating - rating_avv))))

                # Orologi: mosse, tempo consumato, eventuale caduta della bandierina
                n_w = int(rng.integers(15, 45)); n_b = n_w - int(rng.random() < 0.5)
                per_tempo = punteggio != 0.5 and rng.random() < 0.30
                vince_bianco = (punteggio == 1.0) == bianco
                ult_w, ult_b = rng.uniform(0.05, 0.7, 2) * base
                if per_tempo:
                    stretto = rng.random() < 0.25
                    if vince_bianco:
                        n_b = n_w - 1; n_w_eff = n_w                 # tocca al Nero, che perde
                        ult_b = rng.uniform(0, 3); ult_w = rng.uniform(0, 4) if stretto else ult_w
                    else:
                        n_b = n_w                                    # tocca al Bianco, che perde
                        ult_w = rng.uniform(0, 3); ult_b = rng.uniform(0, 4) if stretto else ult_b
                ult_w, ult_b = float(int(ult_w)), float(int(ult_b))
                durata = (base - ult_w) + (base - ult_b) + ((ult_b if vince_bianco else ult_w) if per_tempo else 0)

                gid = "".join(rng.choice(ALFABETO, 8))
                inizio = t0 + timedelta(seconds=int(t))
                esito_pgn = "1/2-1/2" if punteggio == 0.5 else ("1-0" if vince_bianco else "0-1")
                w, b = (nome, avv) if bianco else (avv, nome)
                we, be = (rating, rating_avv) if bianco else (rating_avv, rating)
                wd, bd = (diff, -diff) if bianco else (-diff, diff)
                righe.append((gid, f"Rated {speed} {'tournament https://lichess.org/tournament/x' if torneo else 'game'}",
                              speed, torneo, w, b, esito_pgn, inizio, int(we), int(be), wd, bd, None, None,
                              "A00", "Sim", tc, "Time forfeit" if per_tempo else "Normal", n_w + n_b, rng.random() < 0.08))
                orologi.append((gid, float(base), ult_w + 5 if n_w >= 10 else None, ult_w, n_w,
                                float(base), ult_b + 5 if n_b >= 10 else None, ult_b, n_b))

                rating += diff
                prec2_esito = prec_esito
                prec_esito, prec_avv, prec_rating_avv = punteggio, avv, rating_avv - diff
                t += durata + 4 + rng.exponential(25)
                # Selezione: dopo una sconfitta si smette un po' piu' spesso
                if rng.random() < (args.stop_sconfitta if punteggio == 0.0 else 0.15) or pos >= 60:
                    break
            libero = t

    schema_p = pa.schema([("game_id", pa.string()), ("event", pa.string()), ("speed", pa.string()),
                          ("is_tournament", pa.bool_()), ("white", pa.string()), ("black", pa.string()),
                          ("result", pa.string()), ("start_utc", pa.timestamp("s")), ("white_elo", pa.int16()),
                          ("black_elo", pa.int16()), ("white_rating_diff", pa.int16()), ("black_rating_diff", pa.int16()),
                          ("white_title", pa.string()), ("black_title", pa.string()), ("eco", pa.string()),
                          ("opening", pa.string()), ("time_control", pa.string()), ("termination", pa.string()),
                          ("n_clk", pa.int16()), ("has_eval", pa.bool_())])
    schema_o = pa.schema([("game_id", pa.string()), ("w_clk_first", pa.float32()), ("w_clk_m10", pa.float32()),
                          ("w_clk_last", pa.float32()), ("w_n_moves", pa.int16()), ("b_clk_first", pa.float32()),
                          ("b_clk_m10", pa.float32()), ("b_clk_last", pa.float32()), ("b_n_moves", pa.int16())])
    Path("data").mkdir(exist_ok=True)
    # Come nel file vero, le righe NON sono in ordine di inizio: le mescolo.
    ordine = rng.permutation(len(righe))
    pq.write_table(pa.Table.from_arrays([pa.array([righe[j][k] for j in ordine], type=f.type)
                                         for k, f in enumerate(schema_p)], schema=schema_p), "data/partite.parquet")
    pq.write_table(pa.Table.from_arrays([pa.array([orologi[j][k] for j in ordine], type=f.type)
                                         for k, f in enumerate(schema_o)], schema=schema_o), "data/orologi.parquet")
    print(f"Simulate {len(righe):,} partite di {P:,} giocatori (tilt = {args.tilt} Elo, tilt a distanza 2 = {args.tilt2} Elo, forma = {args.forma} Elo)")


if __name__ == "__main__":
    main()
