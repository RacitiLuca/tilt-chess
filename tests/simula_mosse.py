"""
tests/simula_mosse.py - Mosse SIMULATE con un effetto noto della pressione del tempo

Perche' esiste:
  Per collaudare 11_pressione.py (domanda 2) servono dati in cui la risposta e'
  nota. Qui ogni mossa ha una probabilita' di errore grave che dipende da:
    - livello del giocatore, fase, catture, equilibrio (cose che lo script controlla);
    - un effetto della coppia partita-giocatore (giornata, avversario), legato
      anche al ritmo di gioco;
    - il tempo residuo (l'effetto che cerco), se lo chiedo;
    - se lo chiedo, una "difficolta'" nascosta della posizione, che fa pensare di
      piu' E sbagliare di piu' (il limite dichiarato nel piano).
  La partita finisce in modo realistico: chi e' perso abbandona, chi sta vincendo
  da' matto, chi non ha piu' tempo perde per tempo. Quindi la LUNGHEZZA della
  partita dipende dagli errori: e' la trappola che il collaudo deve misurare.

Crea, nella cartella corrente:
  data/mosse.parquet               stesso formato di 07_mosse.py
  data/analisi/secchio_0.parquet   solo le colonne che servono a 11_pressione.py
  data/verita_mosse.json           la risposta vera (per classe e fascia di livello)

Uso (da una cartella di prova, NON dalla cartella dei dati veri):
    python ..\\tests\\simula_mosse.py --effetto nessuno
    python ..\\tests\\simula_mosse.py --effetto moltiplicativo
    python ..\\tests\\simula_mosse.py --effetto moltiplicativo --pendenza-livello 0
    python ..\\tests\\simula_mosse.py --effetto additivo --senza-fine-partita
    python ..\\tests\\simula_mosse.py --effetto nessuno --difficolta 0.5
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

# Le stesse fasce di 11_pressione.py (qui servono solo a costruire la verita')
SOGLIE_TEMPO = np.array([3, 5, 10, 20, 40, 80, 160])
SOGLIE_MOSSA = np.array([11, 21, 31, 41, 51])
SOGLIE_CATTURE = np.array([4, 8, 12, 16, 20, 24])
SOGLIE_WIN = np.array([15, 30, 45, 55, 70, 85])
SOGLIE_RATING = np.array([1400, 1600, 1800, 2000])
CLASSI = ("bullet", "blitz", "rapid")

# Moltiplicatori della probabilita' di errore grave per fascia (scelti a mano)
M_MOSSA = np.array([0.30, 1.00, 1.30, 1.30, 1.20, 1.10])
M_CATTURE = np.array([1.00, 1.10, 1.20, 1.20, 1.10, 1.00, 0.90])
M_WIN = np.array([0.00, 0.80, 1.10, 1.00, 1.10, 1.00, 0.70])   # sotto 15 l'errore grave e' impossibile
# Effetto del tempo: rapporto di rischio per fascia di tempo residuo, al livello centrale
RR_TEMPO = np.array([3.00, 2.40, 1.70, 1.25, 1.10, 1.00, 1.00, 1.00])
# Versione additiva: punti (frazione) in piu' per fascia
ADD_TEMPO = np.array([0.080, 0.050, 0.030, 0.010, 0.004, 0.0, 0.0, 0.0])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--partite", type=int, default=60000)
    parser.add_argument("--giocatori", type=int, default=6000)
    parser.add_argument("--seme", type=int, default=1)
    parser.add_argument("--effetto", choices=["nessuno", "moltiplicativo", "additivo"], default="moltiplicativo")
    parser.add_argument("--pendenza-livello", type=float, default=-0.15,
                        help="quanto cambia l'eccesso (RR - 1) per ogni fascia di livello sopra quella centrale: "
                             "-0.15 = i forti peggiorano meno in proporzione; 0 = uguale per tutti (H2b falsa)")
    parser.add_argument("--difficolta", type=float, default=0.0,
                        help="peso della difficolta' nascosta della posizione (0 = assente): fa pensare di piu' e sbagliare di piu'")
    parser.add_argument("--eterogeneita", type=float, default=0.4,
                        help="deviazione standard (log) dell'effetto della coppia partita-giocatore sugli errori")
    parser.add_argument("--senza-fine-partita", action="store_true",
                        help="nessun abbandono e nessun matto: la lunghezza della partita non dipende dagli errori")
    parser.add_argument("--resa-senza-tempo", type=float, default=1.0,
                        help="moltiplicatore della probabilita' di abbandonare quando si hanno meno di 10 secondi "
                             "(1 = uguale; 0.3 = a corto di tempo non si abbandona quasi mai)")
    args = parser.parse_args()
    rng = np.random.default_rng(args.seme)
    G, P = args.partite, args.giocatori

    # ---------------- giocatori e partite ----------------
    forza = np.clip(rng.normal(1650, 250, P), 900, 2500)
    gruppo_gioc = np.where(rng.random(P) < 0.2, "esplorazione", "conferma")
    stabile_gioc = rng.random(P) < 0.9
    ordine_forza = np.argsort(forza)
    rango = np.empty(P, dtype=np.int64); rango[ordine_forza] = np.arange(P)
    bianco_g = rng.integers(0, P, G)
    # l'avversario ha un rating vicino (rango entro +-40)
    nero_g = ordine_forza[np.clip(rango[bianco_g] + rng.integers(-40, 41, G), 0, P - 1)]
    stesso = nero_g == bianco_g
    nero_g[stesso] = ordine_forza[(rango[bianco_g[stesso]] + 1) % P]
    gioc = np.column_stack([bianco_g, nero_g])                    # (G, 2): 0 = Bianco, 1 = Nero
    base = rng.choice([60, 180, 300, 600, 1800], size=G, p=[0.25, 0.25, 0.30, 0.15, 0.05]).astype(np.float64)
    inc = np.where(rng.random(G) < 0.08, 2, 0)                    # 8% con incremento: lo script deve scartarle
    durata_stimata = base + 40 * inc
    classe = np.select([durata_stimata < 180, durata_stimata < 480, durata_stimata < 1500], CLASSI, "classical")
    torneo = rng.random(G) < 0.10
    rating = forza[gioc] + rng.normal(0, 30, (G, 2))              # rating di riferimento della coppia
    livello = np.searchsorted(SOGLIE_RATING, rating, side="right")  # 0..4
    base_errore = 0.10 * np.exp(-(forza[gioc] - 1600) / 600)      # i forti sbagliano meno
    z_ritmo = rng.normal(0, 1, (G, 2))
    ritmo = np.exp(0.35 * z_ritmo)                                # chi pensa a lungo...
    etero = np.exp(args.eterogeneita * (0.3 * z_ritmo + np.sqrt(1 - 0.09) * rng.normal(0, 1, (G, 2))))  # ...sbaglia un po' di piu'
    eccesso_livello = 1 + args.pendenza_livello * (livello - 2)   # moltiplica (RR - 1)

    # ---------------- stato della partita ----------------
    orologio = np.column_stack([base, base]).copy()
    win_b = np.clip(52 + rng.normal(0, 2, G), 1, 99)              # Win% del Bianco
    catture = np.zeros(G, dtype=np.int64)
    diff = np.zeros(G)                                            # difficolta' nascosta della posizione
    viva = np.ones(G, dtype=bool)
    punteggio_b = np.full(G, 0.5)
    per_tempo = np.zeros(G, dtype=bool)
    col = {k: [] for k in ("g", "semimossa", "bianco", "clk", "clk_prima", "win_prima", "perdita", "n_catture", "cattura")}
    # verita': somme di p con e senza l'effetto del tempo, per classe x livello x fascia di tempo
    ver_con = np.zeros((3, 5, 8)); ver_senza = np.zeros((3, 5, 8)); ver_n = np.zeros((3, 5, 8))
    classe_id = np.select([classe == c for c in CLASSI], [0, 1, 2], -1)

    for t in range(1, 241):
        s = (t - 1) % 2
        idx = np.flatnonzero(viva)
        if len(idx) == 0:
            break
        n_mossa = (t + 1) // 2
        resto = orologio[idx, s]
        win_prima = win_b[idx] if s == 0 else 100 - win_b[idx]
        u = rng.random((6, len(idx)))
        # 1. Chi e' perso abbandona (prima di muovere): la fine dipende dagli errori gia' fatti
        p_resa = np.where(win_prima < 10, 0.30, np.where(win_prima < 20, 0.05, 0.0)) * (n_mossa > 8)
        p_resa = p_resa * np.where(resto < 10, args.resa_senza_tempo, 1.0)
        resa = (u[0] < p_resa) & (not args.senza_fine_partita)
        # 2. Chi non ha piu' tempo perde per tempo
        bandiera = ~resa & (resto < 2.5) & (u[1] < 0.25) & (inc[idx] == 0)
        finita = resa | bandiera
        punteggio_b[idx[finita]] = 1.0 - (s == 0)                 # chi doveva muovere ha perso
        per_tempo[idx[bandiera]] = True
        viva[idx[finita]] = False
        idx, resto, win_prima = idx[~finita], resto[~finita], win_prima[~finita]
        u = u[:, ~finita]
        if len(idx) == 0:
            continue
        # 3. Tempo pensato
        pensato = base[idx] / 40 * np.exp(0.7 * rng.normal(0, 1, len(idx))) * ritmo[idx, s] \
            * np.exp(0.5 * args.difficolta * diff[idx]) * (0.35 if n_mossa <= 8 else 1.0)
        pensato = np.where(resto < 30, np.minimum(pensato, resto * (0.04 + 0.26 * u[2])), np.minimum(pensato, 0.5 * resto))
        pensato = np.maximum(pensato, 0.1)
        dopo = np.maximum(resto - pensato, 0.0) + inc[idx]
        orologio[idx, s] = dopo
        # 4. Probabilita' di errore grave
        f_tempo = np.searchsorted(SOGLIE_TEMPO, np.floor(resto), side="right")
        f_mossa = np.searchsorted(SOGLIE_MOSSA, n_mossa, side="right")
        f_catt = np.searchsorted(SOGLIE_CATTURE, catture[idx], side="right")
        f_win = np.searchsorted(SOGLIE_WIN, win_prima, side="right")
        p0 = base_errore[idx, s] * M_MOSSA[f_mossa] * M_CATTURE[f_catt] * M_WIN[f_win] * etero[idx, s] \
            * np.exp(args.difficolta * diff[idx])
        if args.effetto == "moltiplicativo":
            p1 = p0 * (1 + (RR_TEMPO[f_tempo] - 1) * eccesso_livello[idx, s])
        elif args.effetto == "additivo":
            p1 = p0 + ADD_TEMPO[f_tempo] * (win_prima >= 15)
        else:
            p1 = p0
        p0, p1 = np.clip(p0, 0, 0.9), np.clip(p1, 0, 0.9)
        grave = u[3] < p1
        # 5. Perdita di Win% e nuova valutazione
        piccola = np.minimum(-1.2 * np.log(u[4]), 14.0) * np.where(rng.random(len(idx)) < 0.3, -0.4, 1.0)
        grande = 15.0 + u[5] * np.maximum(np.minimum(win_prima, 60.0) - 15.0, 0.0)
        perdita = np.where(grave, grande, piccola)
        win_dopo = np.clip(win_prima - perdita, 0.5, 99.5)
        # chi sta stravincendo ogni tanto da' matto: la partita finisce, lui ha vinto
        matto = (win_prima > 96) & ~grave & (rng.random(len(idx)) < 0.12) & (not args.senza_fine_partita)
        win_dopo[matto] = 100.0
        perdita = win_prima - win_dopo
        win_b[idx] = win_dopo if s == 0 else 100 - win_dopo
        punteggio_b[idx[matto]] = 1.0 * (s == 0)
        viva[idx[matto]] = False
        # 6. Catture, difficolta', patte
        cattura = (rng.random(len(idx)) < 0.22) & (catture[idx] < 30)
        col["g"].append(idx.astype(np.int32)); col["semimossa"].append(np.full(len(idx), t, dtype=np.int16))
        col["bianco"].append(np.full(len(idx), s == 0)); col["clk"].append(np.floor(dopo).astype(np.int32))
        col["clk_prima"].append(np.floor(resto).astype(np.int32))
        col["win_prima"].append((win_prima if t > 1 else np.full(len(idx), np.nan)).astype(np.float32))
        col["perdita"].append((perdita if t > 1 else np.full(len(idx), np.nan)).astype(np.float32))
        col["n_catture"].append(catture[idx].astype(np.int16)); col["cattura"].append(cattura)
        if t > 1:
            buone = (classe_id[idx] >= 0) & (inc[idx] == 0)
            chiave = (classe_id[idx] * 5 + livello[idx, s]) * 8 + f_tempo
            for somma, valori in ((ver_con, p1), (ver_senza, p0), (ver_n, np.ones(len(idx)))):
                somma += np.bincount(chiave[buone], weights=valori[buone], minlength=120).reshape(3, 5, 8)
        catture[idx] += cattura
        diff[idx] = 0.8 * diff[idx] + 0.6 * rng.normal(0, 1, len(idx))
        patta = (t > 60) & (np.abs(win_b[idx] - 50) < 10) & (rng.random(len(idx)) < 0.01) & viva[idx]
        viva[idx[patta]] = False

    # ---------------- scrittura ----------------
    Path("data/analisi").mkdir(parents=True, exist_ok=True)
    g = np.concatenate(col["g"])
    ordine = np.lexsort((np.concatenate(col["semimossa"]), g))    # per partita e semimossa
    ids = np.char.add("s", np.char.zfill(np.arange(G).astype(str), 7))
    perdita = np.concatenate(col["perdita"])[ordine]
    manca = np.isnan(perdita)
    giudizio = np.zeros(len(perdita), dtype=np.int8)
    for soglia, voto in ((5, 1), (10, 2), (15, 3)):
        giudizio[perdita >= soglia] = voto
    pq.write_table(pa.table({
        "game_id": pa.array(ids[g[ordine]], type=pa.string()),
        "semimossa": pa.array(np.concatenate(col["semimossa"])[ordine], type=pa.int16()),
        "bianco": pa.array(np.concatenate(col["bianco"])[ordine]),
        "clk": pa.array(np.concatenate(col["clk"])[ordine], type=pa.int32()),
        "clk_prima": pa.array(np.concatenate(col["clk_prima"])[ordine], type=pa.int32()),
        "cp": pa.array(np.zeros(len(g), dtype=np.int16), type=pa.int16()),
        "win_prima": pa.array(np.concatenate(col["win_prima"])[ordine], mask=manca),
        "perdita": pa.array(perdita, mask=manca),
        "giudizio": pa.array(giudizio, type=pa.int8(), mask=manca),
        "cattura": pa.array(np.concatenate(col["cattura"])[ordine]),
        "n_catture": pa.array(np.concatenate(col["n_catture"])[ordine], type=pa.int16()),
    }), "data/mosse.parquet", compression="zstd")

    lati = []
    for s in (0, 1):
        punteggio = punteggio_b if s == 0 else 1 - punteggio_b
        lati.append(pa.table({
            "gid": pa.array(gioc[:, s] + 1, type=pa.int32()), "game_id": pa.array(ids, type=pa.string()),
            "avv": pa.array(gioc[:, 1 - s] + 1, type=pa.int32()), "bianco": pa.array(np.full(G, s == 0)),
            "gruppo": pa.array(gruppo_gioc[gioc[:, s]], type=pa.string()), "classe": pa.array(classe, type=pa.string()),
            "base_s": pa.array(base.astype(np.int32)), "inc_s": pa.array(inc.astype(np.int32)),
            "is_tournament": pa.array(torneo), "berserk": pa.array(np.zeros(G, dtype=bool)),
            "termination": pa.array(np.where(per_tempo, "Time forfeit", "Normal"), type=pa.string()),
            "has_eval": pa.array(np.ones(G, dtype=bool)), "punteggio": pa.array(punteggio),
            "elo": pa.array(np.round(rating[:, s]).astype(np.int16)), "elo_avv": pa.array(np.round(rating[:, 1 - s]).astype(np.int16)),
            "rating_rif": pa.array(np.round(rating[:, s]).astype(np.int16)),
            "elig": pa.array(~torneo & (classe != "classical")), "stabile": pa.array(stabile_gioc[gioc[:, s]]),
        }))
    pq.write_table(pa.concat_tables(lati), "data/analisi/secchio_0.parquet", compression="zstd")

    # Verita' (tutti i giocatori insieme: i due gruppi sono estratti a caso)
    # "rr" = rischio sotto i 10 secondi diviso rischio delle STESSE mosse senza alcun effetto del tempo;
    # "rr_rapporto" = lo stesso, diviso l'analogo delle mosse con 10 secondi o piu': e' cio' che stima
    # il confronto "sotto i 10 secondi contro 10 secondi o piu'" di 11_pressione.py.
    def riassunto(con, senza, n):
        c, s0, k = con[..., :3].sum(-1), senza[..., :3].sum(-1), n[..., :3].sum(-1)
        with np.errstate(divide="ignore", invalid="ignore"):
            rr, rr_alto = c / s0, con[..., 3:].sum(-1) / senza[..., 3:].sum(-1)
            return {"mosse_sotto_10s": k.tolist(), "delta_pp": (100 * (c - s0) / k).tolist(), "rr": rr.tolist(),
                    "rr_rapporto": (rr / rr_alto).tolist()}
    verita = {"argomenti": vars(args), "classi": CLASSI,
              "per_classe": riassunto(ver_con.sum(1), ver_senza.sum(1), ver_n.sum(1)),
              "per_classe_e_livello": riassunto(ver_con, ver_senza, ver_n)}
    with np.errstate(divide="ignore", invalid="ignore"):
        rif = ver_con[1].sum(0)[4] / ver_senza[1].sum(0)[4]
        verita["curva_rr_blitz_rispetto_a_20_40"] = (ver_con[1].sum(0) / ver_senza[1].sum(0) / rif).tolist()
        rr_liv = np.array(verita["per_classe_e_livello"]["rr_rapporto"])[1]
        verita["h2b_vero_blitz"] = float(np.dot([-0.2, -0.1, 0, 0.1, 0.2], np.log(rr_liv)))
    Path("data/verita_mosse.json").write_text(json.dumps(verita, indent=1))
    n_mosse = len(g)
    print(f"Simulate {G:,} partite, {n_mosse:,} semimosse ({n_mosse / G:.0f} per partita); effetto = {args.effetto}; "
          f"errori gravi {100 * np.mean(giudizio[~manca] == 3):.2f}% delle mosse; perse per tempo {100 * per_tempo.mean():.0f}%")
    print(f"Blitz, sotto 10 s contro 10 s o piu': RR vero {verita['per_classe']['rr_rapporto'][1]:.3f} "
          f"(log {np.log(verita['per_classe']['rr_rapporto'][1]):.3f}); per livello {np.round(rr_liv, 3).tolist()}; "
          f"H2b vero (pendenza di log RR per fascia di livello) {verita['h2b_vero_blitz']:.4f}")


if __name__ == "__main__":
    main()
