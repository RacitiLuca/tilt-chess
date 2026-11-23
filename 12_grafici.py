"""
12_grafici.py - Grafici del progetto Tilt (domanda 1, domanda 2, post hoc PH4).

Legge SOLO i file gia' prodotti in output/ (nessun calcolo nuovo, nessuna stima nuova)
e scrive PNG in figures/. Testo dei grafici in inglese (repository e articolo).

File letti (quelli mancanti fanno saltare solo il grafico che li usa):
  output/08_stime_conferma.csv                 domanda 1, variante principale
  output/08_stime_conferma_<variante>.csv      domanda 1, le otto varianti di robustezza
  output/08_stime_esplorazione.csv             domanda 1, esplorazione (punti sbiaditi nel grafico per distanza)
  output/11_stime_conferma.csv                 domanda 2, variante principale
  output/11_stime_conferma_senzatornei.csv     domanda 2, robustezza
  output/11_stime_conferma_stabile.csv         domanda 2, robustezza
  output/11_pressione_conferma.txt             domanda 2: numero di errori gravi per cella (regola P14)
                                               e rapporti osservati/attesi per livello
  output/10_posthoc_conferma.csv               post hoc PH4 (fotofinish con placebo)

Uso (da C:\\tilt):
  .\\.venv\\Scripts\\python 12_grafici.py
Opzioni: --output CARTELLA  --figure CARTELLA
"""
import argparse
import re
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import transforms  # noqa: E402
from matplotlib.ticker import FixedLocator, NullLocator  # noqa: E402

# ------------------------------------------------------------------ palette e stile
SUPERFICIE = "#ffffff"
INK = "#0b0b0b"          # testo principale
INK2 = "#52514e"         # testo secondario
MUTED = "#898781"        # assi, note
GRIGLIA = "#e1e0d9"
ASSE = "#c3c2b7"
FASCIA = "#f0efec"       # fascia "trascurabile"
BLU = "#2a78d6"          # serie principale (slot 1)
GRIGIO_PUNTI = "#8f8d86" # stime che contengono ancora altro
CLASSI = {"bullet": "#2a78d6", "blitz": "#eb6834", "rapid": "#1baf7a"}  # slot 1-3, validati a coppie
LIVELLI = ["<1400", "1400-1599", "1600-1799", "1800-1999", ">=2000"]
RAMPA_LIVELLI = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#0d366b"]  # ordinale, validata
ETICHETTA_LIVELLO = {"<1400": "<1400", "1400-1599": "1400–1599", "1600-1799": "1600–1799",
                     "1800-1999": "1800–1999", ">=2000": "≥2000"}

FONTE = "Data: Lichess rated games, May 2017 · confirmation group (80% of players, split fixed in advance)"
MENO = "\u2212"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Segoe UI", "DejaVu Sans", "Arial", "Helvetica"],
    "font.size": 11,
    "axes.edgecolor": ASSE,
    "axes.linewidth": 0.8,
    "axes.labelcolor": INK2,
    "axes.titlecolor": INK,
    "axes.facecolor": SUPERFICIE,
    "figure.facecolor": SUPERFICIE,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "xtick.labelcolor": INK2,
    "ytick.labelcolor": INK2,
    "grid.color": GRIGLIA,
    "grid.linewidth": 0.8,
    "grid.linestyle": "-",
    "lines.solid_capstyle": "round",
    "lines.solid_joinstyle": "round",
    "axes.unicode_minus": True,
    "savefig.facecolor": SUPERFICIE,
})


def num(x, dec=2, segno=False):
    """Numero con il vero segno meno (e il + se richiesto)."""
    s = f"{x:+.{dec}f}" if segno else f"{x:.{dec}f}"
    return s.replace("-", MENO)


def assi_puliti(ax, griglia="x"):
    for lato in ("top", "right"):
        ax.spines[lato].set_visible(False)
    if griglia in ("x", "both"):
        ax.grid(axis="x", zorder=0)
    if griglia in ("y", "both"):
        ax.grid(axis="y", zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)


def intestazione(fig, titolo, sottotitolo, nota, alto=0.965):
    fig.text(0.02, alto, titolo, fontsize=15, fontweight="bold", color=INK, va="top", ha="left")
    fig.text(0.02, alto - 0.065, sottotitolo, fontsize=11, color=INK2, va="top", ha="left", linespacing=1.4)
    fig.text(0.02, 0.018, nota, fontsize=8.5, color=MUTED, va="bottom", ha="left", linespacing=1.4)


def salva(fig, cartella, nome):
    percorso = cartella / nome
    fig.savefig(percorso, dpi=200)
    plt.close(fig)
    print(f"  scritto {percorso}")


def fascia_trascurabile(ax, verticale=True, etichetta=True, y_testo=None):
    """Fascia grigia tra -1 e +1 pp: la regola di rilevanza pre-registrata."""
    if verticale:
        ax.axvspan(-1, 1, color=FASCIA, zorder=0, lw=0)
        ax.axvline(0, color=ASSE, lw=1, zorder=1)
        if etichetta:
            ax.text(0, 1.0, "negligible zone (±1 pp)", transform=transforms.blended_transform_factory(ax.transData, ax.transAxes),
                    ha="center", va="bottom", fontsize=9, color=MUTED)
    else:
        ax.axhspan(-1, 1, color=FASCIA, zorder=0, lw=0)
        ax.axhline(0, color=ASSE, lw=1, zorder=1)


def punto_ic(ax, x, y, lo, hi, colore, orizzontale=True, ms=7, vuoto=False, zorder=3):
    """Punto con intervallo al 95%: linea 2px, punto >= 8px con anello del colore di fondo."""
    if orizzontale:
        ax.plot([lo, hi], [y, y], color=colore, lw=2, zorder=zorder)
    else:
        ax.plot([x, x], [lo, hi], color=colore, lw=2, zorder=zorder)
    ax.plot([x], [y], "o", ms=ms, color=SUPERFICIE if vuoto else colore, mec=colore if vuoto else SUPERFICIE,
            mew=2 if vuoto else 1.5, zorder=zorder + 1)


# ------------------------------------------------------------------ lettura
class Dati:
    def __init__(self, cartella):
        self.cartella = cartella

    def csv(self, nome):
        f = self.cartella / nome
        if not f.exists():
            return None
        df = pd.read_csv(f)
        return df.rename(columns={"stima_pp": "stima"})

    def testo(self, nome):
        f = self.cartella / nome
        return f.read_text(encoding="utf-8", errors="replace") if f.exists() else None


def riga(df, analisi, cella):
    r = df[(df["analisi"] == analisi) & (df["cella"] == cella)]
    if len(r) != 1:
        raise KeyError(f"riga non trovata o doppia: {analisi} | {cella}")
    r = r.iloc[0]
    return float(r["stima"]), float(r["ic95_da"]), float(r["ic95_a"])


def tabella_dal_testo(testo, intestazione_re):
    """Righe della tabella che segue l'intestazione indicata in un file .txt di 11 (fino alla riga vuota)."""
    righe = testo.splitlines()
    for i, r in enumerate(righe):
        if re.search(intestazione_re, r):
            out = []
            for r2 in righe[i + 2:]:
                if not r2.strip() or r2.startswith("==") or r2.startswith("Controllo") or r2.startswith("("):
                    break
                out.append(r2.split())
            return out
    return None


def conteggi_errori(testo, classe):
    """(livello, tempo) -> errori gravi, dalla tabella della curva di 11_pressione_conferma.txt."""
    tab = tabella_dal_testo(testo, rf"== \[{classe}\] CURVA PER TEMPO RESIDUO")
    if tab is None:
        return None
    return {(t[0], f"{t[1]} {t[2]}"): int(t[4]) for t in tab}


# ------------------------------------------------------------------ DOMANDA 1
def q1_scala(d, out):
    df = d.csv("08_stime_conferma.csv")
    if df is None:
        return print("  SALTATO q1_1: manca 08_stime_conferma.csv")
    voci = [
        ("Naive comparison", "player differences, form, matchmaking", riga(df, "A", "senza base del giocatore (confronto quasi ingenuo)"), GRIGIO_PUNTI),
        ("Same session, next game (estimator A)", "form of the day", riga(df, "A", "H1a: stessa sessione, partita +1"), GRIGIO_PUNTI),
        ("After a break of 30+ min (negative control)", "multi-day form: cannot be immediate tilt", riga(df, "A", "CONTROLLO NEGATIVO: oltre la soglia (altra sessione)"), GRIGIO_PUNTI),
        ("Block fixed effects, as pre-registered", "biased: −1.06 in simulations with no tilt", riga(df, "B_preregistrato", "tutte"), GRIGIO_PUNTI),
        ("Joint estimate, next game (control)", "compares the last 3 games with older ones", riga(df, "B_distanza", "partita +1"), BLU),
        ("Block fixed effects, bias-corrected (primary)", "previous game vs rest of the block", riga(df, "B", "tutte"), BLU),
    ]
    fig, ax = plt.subplots(figsize=(10, 5.6))
    fig.subplots_adjust(left=0.40, right=0.96, top=0.76, bottom=0.17)
    fascia_trascurabile(ax)
    tr = transforms.blended_transform_factory(ax.transAxes, ax.transData)
    for i, (nome, nota, (s, lo, hi), col) in enumerate(voci):
        y = len(voci) - 1 - i
        punto_ic(ax, s, y, lo, hi, col)
        ax.text(hi + 0.08, y, num(s), va="center", ha="left", fontsize=10, color=INK, fontweight="bold" if col == BLU else "normal")
        ax.text(-0.02, y + 0.10, nome, transform=tr, ha="right", va="bottom", fontsize=10.5, color=INK)
        ax.text(-0.02, y + 0.05, nota, transform=tr, ha="right", va="top", fontsize=8.8, color=MUTED)
    ax.set_ylim(-0.6, len(voci) - 0.4)
    ax.set_xlim(-3.3, 1.3)
    ax.yaxis.set_major_locator(NullLocator())
    ax.set_xlabel("Score after a loss − score after a win, next game (percentage points; 1 pp ≈ 7 Elo)")
    assi_puliti(ax)
    ax.spines["left"].set_visible(False)
    intestazione(fig, "Most of the “tilt” in a naive comparison is something else",
                 "Each step removes a piece that is not a reaction to the last result. Both final estimates sit inside ±1 pp:\n"
                 "a next-game tilt of 1 pp or more is ruled out (confirmatory test H1a: negligible).",
                 FONTE + " · 3.1M game pairs, 63,695 players\nPoints: estimate; lines: 95% CI (player-level bootstrap). "
                 "Grey points still contain other effects (right-hand notes).")
    salva(fig, out, "q1_1_ladder.png")


def q1_distanza(d, out):
    df = d.csv("08_stime_conferma.csv")
    if df is None:
        return print("  SALTATO q1_2: manca 08_stime_conferma.csv")
    esp = d.csv("08_stime_esplorazione.csv")
    fig, ax = plt.subplots(figsize=(9.5, 5.8))
    fig.subplots_adjust(left=0.10, right=0.82, top=0.70, bottom=0.16)
    fascia_trascurabile(ax, verticale=False)
    ax.axhline(-1, color=MUTED, lw=1, zorder=1)
    ax.text(3.32, -1, "relevance\nthreshold (−1 pp)", va="center", ha="left", fontsize=8.8, color=MUTED)
    xs = np.array([1, 2, 3])
    conf = [riga(df, "B_distanza", f"partita +{k}") for k in xs]
    if esp is not None:
        try:
            e = [riga(esp, "B_distanza", f"partita +{k}") for k in xs]
            print("  controllo q1_2, esplorazione +1/+2/+3 (attesi circa -0.94 / -0.75 / -0.43): "
                  + " / ".join(f"{v[0]:.2f}" for v in e))
            for x, (s, lo, hi) in zip(xs - 0.12, e):
                punto_ic(ax, x, s, lo, hi, "#9ec5f4", orizzontale=False, vuoto=True)
            ax.plot(xs - 0.12, [v[0] for v in e], color="#9ec5f4", lw=1.2, zorder=2)
            ax.plot([], [], "o", ms=7, color=SUPERFICIE, mec="#9ec5f4", mew=2, label="exploration (20% of players)")
        except KeyError:
            print("  nota: 08_stime_esplorazione.csv senza righe B_distanza, solo conferma")
    for k, (x, (s, lo, hi)) in enumerate(zip(xs + 0.12, conf)):
        punto_ic(ax, x, s, lo, hi, BLU, orizzontale=False)
        sopra = k != 1          # a +2 la linea sale verso +3: etichetta sotto
        ax.text(x + 0.07, s + (0.05 if sopra else -0.05), num(s), va="bottom" if sopra else "top", ha="left",
                fontsize=10, color=INK, fontweight="bold")
    ax.plot(xs + 0.12, [v[0] for v in conf], color=BLU, lw=2, zorder=2)
    ax.plot([], [], "o", ms=7, color=BLU, mec=SUPERFICIE, label="confirmation (80% of players)")
    h, l = ax.get_legend_handles_labels()
    ax.legend(h[::-1], l[::-1], loc="upper left", frameon=False, ncol=2, fontsize=9.5, bbox_to_anchor=(0, 1.1))
    ax.set_xticks(xs)
    ax.set_xticklabels(["next game (+1)", "two games later (+2)", "three games later (+3)"])
    ax.set_xlim(0.45, 3.3)
    ax.set_ylim(-1.55, 0.45)
    ax.set_ylabel("Effect of an unexpected result (pp)")
    assi_puliti(ax, griglia="y")
    h1b = riga(df, "B_distanza", "H1b: (+1) - (+2)")
    intestazione(fig, "Nearby games resemble each other, but the last game is not special",
                 "Joint estimate at distance +1, +2, +3 within the same block.\n"
                 f"Flat between +1 and +2 (H1b: {num(h1b[0], segno=True)} pp, 95% CI {num(h1b[1])}; {num(h1b[2])}): "
                 "not the shape of a one-game tilt.\n"
                 "Small (0.3–0.7 pp) and not attributable: a tilt lasting several games and a drifting form look the same.",
                 FONTE + "\nPoints: estimate; bars: 95% CI (player-level bootstrap).")
    salva(fig, out, "q1_2_distance.png")


VARIANTI_Q1 = [("", "Main specification"), ("_rivincite", "Rematches included"),
               ("_ratingcorrente", "Current rating (not session start)"), ("_duelati", "Both players of each game"),
               ("_senzacorte", "Without short games"), ("_largo", "Stable rating, wide definition"),
               ("_stretto", "Stable rating, narrow definition"), ("_s10", "Session break: 10 min"),
               ("_s60", "Session break: 60 min")]


def q1_robustezza(d, out):
    righe = []
    for suff, nome in VARIANTI_Q1:
        df = d.csv(f"08_stime_conferma{suff}.csv")
        if df is None:
            print(f"  nota q1_3: manca 08_stime_conferma{suff}.csv, variante saltata")
            continue
        righe.append((nome, riga(df, "B", "tutte"), riga(df, "B_distanza", "partita +1")))
    if len(righe) < 2:
        return print("  SALTATO q1_3: servono la principale e almeno una variante")
    fig, assi = plt.subplots(1, 2, figsize=(11, 6.2), sharey=True)
    fig.subplots_adjust(left=0.27, right=0.97, top=0.70, bottom=0.15, wspace=0.08)
    for k, (ax, titolo) in enumerate(zip(assi, ["Primary estimator (bias-corrected B)", "Joint estimate, next game"])):
        fascia_trascurabile(ax, etichetta=False)
        for i, (nome, b, c) in enumerate(righe):
            y = len(righe) - 1 - i
            s, lo, hi = (b, c)[k]
            punto_ic(ax, s, y, lo, hi, BLU if i == 0 else GRIGIO_PUNTI)
        ax.set_xlim(-1.6, 1.25)
        ax.set_title(titolo, fontsize=11, color=INK, loc="left", pad=22)
        ax.text(0, len(righe) - 0.45, "negligible zone (±1 pp)", ha="center", va="bottom", fontsize=8.8, color=MUTED)
        ax.set_xlabel("pp (after a loss − after a win)")
        assi_puliti(ax)
        ax.spines["left"].set_visible(False)
    assi[0].set_yticks(range(len(righe)))
    assi[0].set_yticklabels([r[0] for r in righe][::-1], fontsize=10, color=INK)
    assi[0].set_ylim(-0.6, len(righe) - 0.5)
    intestazione(fig, "The verdict does not depend on the analysis choices",
                 f"Both estimators stay inside ±1 pp in all {len(righe)} specifications. "
                 "Including rematches pushes the estimate down: the opponent who just won\n"
                 "is often stronger than their rating says, which is why rematches are excluded in the main analysis.",
                 FONTE + "\nPoints: estimate; lines: 95% CI (player-level bootstrap). Blue: main specification.")
    salva(fig, out, "q1_3_robustness.png")


def q1_pausa(d, out):
    df = d.csv("08_stime_conferma.csv")
    if df is None:
        return print("  SALTATO q1_4: manca 08_stime_conferma.csv")
    voci = [("up to 15 s", "pausa fino a 15 s", BLU), ("15–60 s", "pausa 15-60 s", BLU),
            ("1–5 min", "pausa 1-5 min", BLU), ("5–30 min", "pausa 5 min - soglia", BLU),
            ("more than 30 min (negative control)", "CONTROLLO NEGATIVO: oltre la soglia (altra sessione)", GRIGIO_PUNTI),
            ("   of which 30 min – 6 h", "pausa soglia - 6 h", "#b9b7af"), ("   of which more than 6 h", "pausa oltre 6 h", "#b9b7af")]
    fig, ax = plt.subplots(figsize=(9.5, 5.4))
    fig.subplots_adjust(left=0.30, right=0.95, top=0.76, bottom=0.17)
    ax.axvline(0, color=ASSE, lw=1)
    for i, (nome, cella, col) in enumerate(voci):
        y = len(voci) - 1 - i
        s, lo, hi = riga(df, "A", cella)
        punto_ic(ax, s, y, lo, hi, col)
        ax.text(hi + 0.07, y, num(s), va="center", ha="left", fontsize=10, color=INK)
    ax.axhline(2.5, color=GRIGLIA, lw=1)
    ax.set_yticks(range(len(voci)))
    ax.set_yticklabels([v[0] for v in voci][::-1], fontsize=10, color=INK)
    ax.set_ylim(-0.6, len(voci) - 0.5)
    ax.set_xlim(-4.8, 0.4)
    ax.set_xlabel("Score after a loss − score after a win, next game (pp) · estimator A")
    assi_puliti(ax)
    ax.spines["left"].set_visible(False)
    intestazione(fig, "Even after a long break the gap stays: it is mostly form, not reaction",
                 "Estimator A by break length before the next game. Descriptive only: the player chooses the break.\n"
                 "After more than 30 minutes nothing can be an immediate tilt, yet the gap is still −1.5 pp.",
                 FONTE + "\nPoints: estimate; lines: 95% CI (player-level bootstrap).")
    salva(fig, out, "q1_4_break.png")


def q1_classe_livello(d, out):
    df = d.csv("08_stime_conferma.csv")
    if df is None:
        return print("  SALTATO q1_5: manca 08_stime_conferma.csv")
    pannelli = [("By time control", [("Bullet", "classe bullet"), ("Blitz", "classe blitz"), ("Rapid", "classe rapid")]),
                ("By rating band", [("<1400", "rating <1400"), ("1400–1599", "rating 1400-1599"), ("1600–1799", "rating 1600-1799"),
                                    ("1800–1999", "rating 1800-1999"), ("≥2000", "rating >=2000")])]
    fig, assi = plt.subplots(1, 2, figsize=(11, 5.2), gridspec_kw={"width_ratios": [1, 1]})
    fig.subplots_adjust(left=0.08, right=0.98, top=0.74, bottom=0.17, wspace=0.18)
    for ax, (titolo, celle) in zip(assi, pannelli):
        fascia_trascurabile(ax, verticale=False)
        for x, (nome, cella) in enumerate(celle):
            s, lo, hi = riga(df, "B", cella)
            punto_ic(ax, x, s, lo, hi, BLU, orizzontale=False)
            ax.text(x + 0.1, s, num(s), va="center", ha="left", fontsize=9.5, color=INK)
        ax.set_xticks(range(len(celle)))
        ax.set_xticklabels([c[0] for c in celle], color=INK)
        ax.set_xlim(-0.5, len(celle) - 0.4)
        ax.set_ylim(-1.35, 1.1)
        ax.set_title(titolo, fontsize=11, color=INK, loc="left", pad=8)
        assi_puliti(ax, griglia="y")
    assi[0].set_ylabel("Primary estimator τ_B (pp)")
    c = riga(df, "B", "H1c: tau_B bullet - tau_B rapid")
    pend = riga(df, "B", "H1d: pendenza di tau_B per +200 punti di rating")
    intestazione(fig, "Faster games do not mean more tilt: the order is the opposite of the prediction",
                 f"H1c predicted bullet below rapid; observed bullet − rapid = {num(c[0], segno=True)} pp (95% CI {num(c[1])}; {num(c[2])}): "
                 f"prediction refuted.\nH1d: slope per +200 rating points {num(pend[0], segno=True)} pp "
                 f"(95% CI {num(pend[1])}; {num(pend[2])}), not confirmed. No cell reaches −1 pp.",
                 FONTE + "\nPoints: estimate; bars: 95% CI (player-level bootstrap). Grey band: negligible zone (±1 pp).")
    salva(fig, out, "q1_5_time_control_and_rating.png")


def q1_posizione(d, out):
    df = d.csv("08_stime_conferma.csv")
    if df is None:
        return print("  SALTATO q1_6: manca 08_stime_conferma.csv")
    pos = ["1", "2", "3", "4-5", "6-10", "11-20", "21+"]
    etich = ["1st", "2nd", "3rd", "4–5", "6–10", "11–20", "21+"]
    fig, ax = plt.subplots(figsize=(9.5, 5.4))
    fig.subplots_adjust(left=0.10, right=0.86, top=0.76, bottom=0.17)
    ax.axhline(0, color=ASSE, lw=1)
    xs = np.arange(len(pos))
    for classe, col in CLASSI.items():
        v = np.array([riga(df, "stanchezza", f"{classe}, partita {p}") for p in pos])
        ax.fill_between(xs, v[:, 1], v[:, 2], color=col, alpha=0.12, lw=0, zorder=1)
        ax.plot(xs, v[:, 0], color=col, lw=2, zorder=3, label=classe.capitalize())
        ax.plot(xs, v[:, 0], "o", ms=6.5, color=col, mec=SUPERFICIE, mew=1.5, zorder=4)
        ax.text(xs[-1] + 0.15, v[-1, 0], classe.capitalize(), va="center", ha="left", fontsize=10, color=INK)
    ax.set_xticks(xs)
    ax.set_xticklabels(etich)
    ax.set_xlabel("Position of the game in the session")
    ax.set_ylabel("Mean score above expectation (pp)")
    ax.set_xlim(-0.3, len(pos) - 0.4)
    ax.legend(loc="upper left", frameon=False, ncol=3, fontsize=10, bbox_to_anchor=(0, 1.08))
    assi_puliti(ax, griglia="y")
    intestazione(fig, "No sign of fatigue: later games are not worse than the first",
                 "From the 2nd game on, players score above what their rating predicts. In rapid the gain fades in long sessions\n"
                 "(few of them: wide band). Descriptive: warm-up, or selection (players who are winning keep playing).",
                 FONTE + "\nLines: mean residual (score − expected score); bands: 95% CI.")
    salva(fig, out, "q1_6_session_position.png")


# ------------------------------------------------------------------ DOMANDA 2
BANDE = [">=160 s", "80-160 s", "40-80 s", "20-40 s", "10-20 s", "5-10 s", "3-5 s", "<3 s"]   # il tempo scende ->
ETICH_BANDE = ["≥160", "80–160", "40–80", "20–40", "10–20", "5–10", "3–5", "<3"]
SOGLIA_P14 = 30


def q2_curva(d, out):
    df = d.csv("11_stime_conferma.csv")
    if df is None:
        return print("  SALTATO q2_1: manca 11_stime_conferma.csv")
    testo = d.testo("11_pressione_conferma.txt")
    if testo is None:
        print("  nota q2_1: manca 11_pressione_conferma.txt; regola P14 approssimata con meno di 1000 mosse")
    fig, assi = plt.subplots(1, 3, figsize=(13, 6.2), sharey=True)
    fig.subplots_adjust(left=0.07, right=0.985, top=0.68, bottom=0.15, wspace=0.07)
    xs = np.arange(len(BANDE))
    esclusi = []
    for ax, classe in zip(assi, ["bullet", "blitz", "rapid"]):
        cont = conteggi_errori(testo, classe) if testo else None
        ax.axhline(1, color=ASSE, lw=1, zorder=1)

        def valida(livello, banda):
            r = df[(df["analisi"] == f"curva_RR_{classe}") & (df["cella"] == f"{livello} | {banda}")]
            if len(r) != 1:
                return None
            r = r.iloc[0]
            ok = cont[(livello, banda)] >= SOGLIA_P14 if cont else r["n"] >= 1000
            if not ok:
                esclusi.append(f"{classe} {livello} {banda}")
                return None
            return float(r["stima"]), float(r["ic95_da"]), float(r["ic95_a"])

        tutti = [valida("tutti", b) for b in BANDE]
        m = np.array([t is not None for t in tutti])
        tv = np.array([t if t is not None else (np.nan,) * 3 for t in tutti])
        ax.fill_between(xs[m], tv[m, 1], tv[m, 2], color="#b9b7af", alpha=0.35, lw=0, zorder=1)
        for livello, col in zip(LIVELLI, RAMPA_LIVELLI):
            v = [valida(livello, b) for b in BANDE]
            mm = np.array([t is not None for t in v])
            yv = np.array([t[0] if t is not None else np.nan for t in v])
            ax.plot(xs[mm], yv[mm], color=col, lw=2, zorder=3, label=ETICHETTA_LIVELLO[livello])
            ax.plot(xs[mm], yv[mm], "o", ms=5, color=col, mec=SUPERFICIE, mew=1.2, zorder=4)
        ax.plot([3], [1], "o", ms=7, color=INK, mec=SUPERFICIE, mew=1.5, zorder=5)
        rr = riga(df, f"RR_sotto10_{classe}", "tutti")
        sotto = " (confirmatory test H2a)" if classe == "blitz" else ""
        ax.set_title(f"{classe.capitalize()}{sotto}", fontsize=11.5, color=INK, loc="left", pad=22, fontweight="bold")
        ax.text(0, 1.015, f"under 10 s vs 10 s or more: ×{rr[0]:.2f} (95% CI {rr[1]:.2f}–{rr[2]:.2f})",
                transform=ax.transAxes, fontsize=9.5, color=INK2, va="bottom", ha="left")
        ax.set_yscale("log")
        ax.set_ylim(0.4, 2.5)
        tick = [0.5, 0.75, 1, 1.5, 2]
        ax.yaxis.set_major_locator(FixedLocator(tick))
        ax.yaxis.set_minor_locator(NullLocator())
        ax.set_yticklabels([f"×{t:g}" for t in tick])
        ax.set_xticks(xs)
        ax.set_xticklabels(ETICH_BANDE, fontsize=9.5)
        ax.set_xlim(-0.4, len(BANDE) - 0.6)
        ax.set_xlabel("Seconds left on the clock  →  running out", fontsize=10)
        assi_puliti(ax, griglia="y")
    assi[0].set_ylabel("Blunder risk vs 20–40 s left (log scale)")
    h, l = assi[0].get_legend_handles_labels()
    fig.text(0.02, 0.815, "Rating band:", fontsize=9.5, color=INK2, va="center")
    fig.legend(h, l, loc="center left", bbox_to_anchor=(0.085, 0.815), ncol=5, frameon=False, fontsize=9.5)
    fig.text(0.60, 0.815, "Grey band: 95% CI, all rating bands together · black dot: reference cell",
             fontsize=9, color=INK2, va="center")
    imp = riga(df, "altre_blitz", "impennata: [log RR(5-10) - log RR(10-20)] - [log RR(10-20) - log RR(20-40)]")
    intestazione(fig, "Blunder risk rises steadily as the clock runs down: every time control, every level",
                 "Risk of a blunder compared with the same player, in the same game, in the same type of position, with 20–40 s left\n"
                 f"(294 strata: move number × captures × Win%). No sudden jump below 10 s (blitz: {num(imp[0], 3)}, 95% CI {num(imp[1], 3)}; {num(imp[2], 3)}).",
                 FONTE + ". Blunder = a move that loses at least 15 Win% points.\n"
                 f"Cells with fewer than {SOGLIA_P14} blunders are not drawn (pre-registered reporting rule P14)"
                 + (f": {len(esclusi)} cells, all bullet with 160 s or more left." if esclusi and all(e.startswith("bullet") and e.endswith(">=160 s") for e in esclusi)
                    else f": {len(esclusi)} cells." if esclusi else "."),
                 alto=0.975)
    salva(fig, out, "q2_1_risk_curve.png")


def q2_ogni100(d, out):
    df = d.csv("11_stime_conferma.csv")
    if df is None:
        return print("  SALTATO q2_2: manca 11_stime_conferma.csv")
    fig, ax = plt.subplots(figsize=(9.5, 5.8))
    fig.subplots_adjust(left=0.09, right=0.97, top=0.70, bottom=0.17)
    larg = 0.22
    for i, classe in enumerate(["bullet", "blitz", "rapid"]):
        rr = riga(df, f"RR_sotto10_{classe}", "tutti")[0]
        pp, pp_lo, pp_hi = riga(df, f"pp_tra_esposti_{classe}", "tutti")
        oss = pp / (1 - 1 / rr)          # tasso osservato sotto i 10 s (pp = oss - oss/RR)
        senza = oss - pp                 # le stesse mosse senza l'effetto del tempo
        for dx, val, col in ((-larg / 2 - 0.015, senza, "#c9c7c0"), (larg / 2 + 0.015, oss, BLU)):
            ax.bar(i + dx, val, width=larg, color=col, zorder=2)
            ax.text(i + dx, val + 0.15, f"{val:.1f}", ha="center", va="bottom", fontsize=10.5, color=INK, fontweight="bold" if col == BLU else "normal")
        ax.text(i, oss + 1.15, f"+{pp:.1f}  (95% CI {pp_lo:.1f}–{pp_hi:.1f})", ha="center", va="bottom", fontsize=9.5, color=INK2)
    ax.set_xticks(range(3))
    ax.set_xticklabels(["Bullet", "Blitz\n(confirmatory test H2a)", "Rapid"], color=INK)
    ax.set_ylim(0, 13.2)
    ax.set_xlim(-0.6, 2.6)
    ax.set_ylabel("Blunders per 100 moves")
    assi_puliti(ax, griglia="y")
    ax.bar([0], [0], color="#c9c7c0", label="same moves, expected without the time effect")
    ax.bar([0], [0], color=BLU, label="observed, moves played with under 10 s left")
    ax.legend(loc="upper left", frameon=False, ncol=2, fontsize=9.5, bbox_to_anchor=(0, 1.1))
    intestazione(fig, "What running low on time costs: about 2 extra blunders every 100 moves",
                 "Moves played with under 10 seconds left, against what the same moves would give without the time effect\n"
                 "(observed rate ÷ risk ratio). Blitz: from 6.5 to 8.2 blunders per 100 moves, +25%.",
                 FONTE + "\nBlunder = a move that loses at least 15 Win% points. "
                 "Difference above the bars: 95% CI (player-level bootstrap).")
    salva(fig, out, "q2_2_blunders_per_100_moves.png")


def q2_forti_deboli(d, out):
    df = d.csv("11_stime_conferma.csv")
    testo = d.testo("11_pressione_conferma.txt")
    if df is None or testo is None:
        return print("  SALTATO q2_3: servono 11_stime_conferma.csv e 11_pressione_conferma.txt")
    tab = tabella_dal_testo(testo, r"== \[blitz\] ERRORI GRAVI OSSERVATI / ATTESI")
    oa = {f"{t[0]} {t[1]}": (float(t[2]), float(t[6])) for t in tab}   # tempo -> (O/A <1400, O/A >=2000)
    xs = np.arange(len(BANDE))
    deboli = np.array([oa[b][0] for b in BANDE])
    forti = np.array([oa[b][1] for b in BANDE])
    fig, ax = plt.subplots(figsize=(9.5, 5.4))
    fig.subplots_adjust(left=0.10, right=0.86, top=0.76, bottom=0.17)
    ax.axhline(1, color=ASSE, lw=1)
    ax.text(3, 1.012, "class average", fontsize=8.8, color=MUTED, va="bottom", ha="center")
    ax.fill_between(xs, forti, deboli, color="#86b6ef", alpha=0.12, lw=0)
    for v, col, nome in ((deboli, RAMPA_LIVELLI[0], "Rated <1400"), (forti, RAMPA_LIVELLI[-1], "Rated ≥2000")):
        ax.plot(xs, v, color=col, lw=2, zorder=3, label=nome)
        ax.plot(xs, v, "o", ms=6.5, color=col, mec=SUPERFICIE, mew=1.5, zorder=4)
        ax.text(xs[-1] + 0.15, v[-1], f"{nome}\n{v[-1]:.2f}", va="center", ha="left", fontsize=9.5, color=INK, linespacing=1.3)
    g0 = riga(df, "OA_forti_meno_deboli_blitz", ">=160 s")
    g1 = riga(df, "OA_forti_meno_deboli_blitz", "<3 s")
    ax.text(0.12, 0.86, f"gap {num(g0[0])}\n({num(g0[1])}; {num(g0[2])})", fontsize=9, color=INK2, va="center", ha="left",
            linespacing=1.3)
    ax.text(xs[-1] - 0.1, (forti[-1] + deboli[-1]) / 2 + 0.02, f"gap {num(g1[0])}\n({num(g1[1])}; {num(g1[2])})",
            fontsize=9, color=INK2, va="center", ha="right", linespacing=1.3)
    ax.set_xticks(xs)
    ax.set_xticklabels(ETICH_BANDE)
    ax.set_xlim(-0.4, len(BANDE) - 0.5)
    ax.set_ylim(0.35, 1.65)
    ax.set_xlabel("Seconds left on the clock  →  running out")
    ax.set_ylabel("Blunders: observed ÷ expected")
    ax.legend(loc="upper left", frameon=False, ncol=2, fontsize=10, bbox_to_anchor=(0, 1.08))
    assi_puliti(ax, griglia="y")
    intestazione(fig, "In the last seconds, strong players lose their edge",
                 "Blitz. Expected = average blunder rate of the class in the same type of position and the same time band.\n"
                 "With plenty of time, players rated ≥2000 blunder half as often as average; under 3 s, about as often as anyone.",
                 FONTE + ". Descriptive. Gap = (≥2000) − (<1400), with 95% CI.")
    salva(fig, out, "q2_3_strong_vs_weak.png")


def q2_robustezza(d, out):
    df = d.csv("11_stime_conferma.csv")
    if df is None:
        return print("  SALTATO q2_4: manca 11_stime_conferma.csv")
    voci = [("Blitz, main specification (H2a)", riga(df, "RR_sotto10_blitz", "tutti"), BLU)]
    for nome_file, nome in (("11_stime_conferma_senzatornei.csv", "Blitz, without tournament games"),
                            ("11_stime_conferma_stabile.csv", "Blitz, stable ratings only")):
        v = d.csv(nome_file)
        if v is None:
            print(f"  nota q2_4: manca {nome_file}, riga saltata")
        else:
            voci.append((nome, riga(v, "RR_sotto10_blitz", "tutti"), GRIGIO_PUNTI))
    voci += [("Bullet", riga(df, "RR_sotto10_bullet", "tutti"), GRIGIO_PUNTI),
             ("Rapid", riga(df, "RR_sotto10_rapid", "tutti"), GRIGIO_PUNTI)]
    fig, ax = plt.subplots(figsize=(9.5, 4.8))
    fig.subplots_adjust(left=0.30, right=0.95, top=0.72, bottom=0.19)
    ax.axvline(1.0, color=ASSE, lw=1)
    ax.axvline(1.10, color=MUTED, lw=1)
    ax.text(1.10, len(voci) - 0.45, "relevance threshold ×1.10\n(pre-registered)", ha="center", va="bottom", fontsize=8.8, color=MUTED)
    ax.text(1.0, len(voci) - 0.45, "no effect", ha="center", va="bottom", fontsize=8.8, color=MUTED)
    for i, (nome, (s, lo, hi), col) in enumerate(voci):
        y = len(voci) - 1 - i
        punto_ic(ax, s, y, lo, hi, col)
        ax.text(hi + 0.01, y, f"×{s:.2f}", va="center", ha="left", fontsize=10, color=INK, fontweight="bold" if col == BLU else "normal")
    ax.set_yticks(range(len(voci)))
    ax.set_yticklabels([v[0] for v in voci][::-1], fontsize=10, color=INK)
    ax.set_ylim(-0.6, len(voci) - 0.5)
    ax.set_xlim(0.95, 1.52)
    ax.set_xlabel("Blunder risk, under 10 s vs 10 s or more (risk ratio)")
    assi_puliti(ax)
    ax.spines["left"].set_visible(False)
    intestazione(fig, "Time pressure: every estimate clears the pre-registered threshold",
                 "Confirmatory test H2a (blitz) and its checks. Whole 95% CI above ×1.10 in every row.",
                 FONTE + "\nPoints: estimate; lines: 95% CI (player-level bootstrap).")
    salva(fig, out, "q2_4_robustness.png")


def ph4_placebo(d, out):
    df = d.csv("10_posthoc_conferma.csv")
    if df is None:
        return print("  SALTATO ph4: manca 10_posthoc_conferma.csv")
    base = "vincitore entro 3 s, blitz | "
    voci = [("Game before the photo finish (placebo)", riga(df, "PH4_placebo", base + "PLACEBO: la partita PRIMA del fotofinish"), GRIGIO_PUNTI),
            ("Game after the photo finish", riga(df, "PH4_placebo", base + "dopo il fotofinish, solo chi ha la partita prima"), GRIGIO_PUNTI),
            ("Difference: after − before", riga(df, "PH4_placebo", base + "differenza dopo - prima"), BLU)]
    n = int(df[(df["analisi"] == "PH4_placebo") & (df["cella"] == base + "differenza dopo - prima")]["n"].iloc[0])
    fig, ax = plt.subplots(figsize=(9.5, 4.8))
    fig.subplots_adjust(left=0.33, right=0.95, top=0.68, bottom=0.20)
    fascia_trascurabile(ax)
    for i, (nome, (s, lo, hi), col) in enumerate(voci):
        y = len(voci) - 1 - i
        punto_ic(ax, s, y, lo, hi, col)
        ax.text(hi + 0.07, y, num(s), va="center", ha="left", fontsize=10, color=INK, fontweight="bold" if col == BLU else "normal")
    ax.axhline(0.5, color=GRIGLIA, lw=1)
    ax.set_yticks(range(len(voci)))
    ax.set_yticklabels([v[0] for v in voci][::-1], fontsize=10, color=INK)
    ax.set_ylim(-0.6, len(voci) - 0.45)
    ax.set_xlim(-3.0, 1.6)
    ax.set_xlabel("Losers − winners of the photo finish (pp of score)")
    assi_puliti(ax)
    ax.spines["left"].set_visible(False)
    intestazione(fig, "The photo-finish “exception” was already there before the photo finish",
                 "Blitz games won with under 3 s left on the winner's clock. The losers did worse in the next game, but they were\n"
                 "already doing worse in the game before: the difference is indistinguishable from zero. Both stratified by expected score.",
                 FONTE + f" · {n:,} player-games with a previous game\nPost hoc and exploratory (added after the confirmation run). "
                 "Points: estimate; lines: 95% CI (player-level bootstrap).")
    salva(fig, out, "ph4_photo_finish_placebo.png")


def main():
    p = argparse.ArgumentParser(description="Grafici del progetto Tilt (solo lettura dei risultati)")
    p.add_argument("--output", default="output", help="cartella con i risultati (default: output)")
    p.add_argument("--figure", default="figures", help="cartella dove scrivere i PNG (default: figures)")
    opz = p.parse_args()
    d = Dati(Path(opz.output))
    out = Path(opz.figure)
    out.mkdir(parents=True, exist_ok=True)
    print(f"Lettura da {d.cartella.resolve()}, grafici in {out.resolve()}")
    for f in (q1_scala, q1_distanza, q1_robustezza, q1_pausa, q1_classe_livello, q1_posizione,
              q2_curva, q2_ogni100, q2_forti_deboli, q2_robustezza, ph4_placebo):
        f(d, out)
    print("Fatto.")


if __name__ == "__main__":
    main()
