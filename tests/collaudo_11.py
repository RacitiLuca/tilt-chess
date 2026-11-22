"""
tests/collaudo_11.py - Collaudo di 11_pressione.py su mosse simulate (tabella di P13)

Per ogni scenario e seme: simula le mosse (tests/simula_mosse.py), lancia
11_pressione.py sul gruppo "conferma" dei dati SIMULATI e confronta le stime del
blitz con la risposta vera. Lavora in cartelle temporanee: non tocca i dati veri.

Uso (dalla cartella degli script; circa 1 minuto per riga):
    python tests\\collaudo_11.py                  (tutti gli scenari)
    python tests\\collaudo_11.py nullo 3          (uno scenario, 3 semi)
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

QUI = Path(__file__).resolve().parent
SCENARI = {
    "nullo": (["--effetto", "nessuno"], 6),
    "nullo_difficolta": (["--effetto", "nessuno", "--difficolta", "0.5"], 2),
    "nullo_resa": (["--effetto", "nessuno", "--resa-senza-tempo", "0.3"], 2),
    "molt": (["--effetto", "moltiplicativo"], 6),
    "molt_uguale": (["--effetto", "moltiplicativo", "--pendenza-livello", "0"], 4),
    "molt_difficolta": (["--effetto", "moltiplicativo", "--difficolta", "0.5"], 2),
    "additivo": (["--effetto", "additivo"], 2),
}


def una_prova(argomenti, seme, partite=120000):
    with tempfile.TemporaryDirectory() as cartella:
        subprocess.run([sys.executable, str(QUI / "simula_mosse.py"), "--partite", str(partite), "--giocatori", str(partite // 12),
                        "--seme", str(seme)] + argomenti, cwd=cartella, check=True, capture_output=True)
        subprocess.run([sys.executable, str(QUI.parent / "11_pressione.py"), "--gruppo", "conferma", "--codice-bloccato",
                        "--bootstrap", "300"], cwd=cartella, check=True, capture_output=True)
        verita = json.loads((Path(cartella) / "data" / "verita_mosse.json").read_text())
        csv = pd.read_csv(Path(cartella) / "output" / "11_stime_conferma.csv")

    def stima(analisi, inizio):
        r = csv[(csv["analisi"] == analisi) & csv["cella"].str.startswith(inizio)]
        return (float(r["stima"].iloc[0]), float(r["err_std"].iloc[0])) if len(r) else (np.nan, np.nan)

    h2a, h2b = stima("confermativo", "H2a"), stima("confermativo", "H2b")
    return {"H2a_vero": np.log(verita["per_classe"]["rr_rapporto"][1]), "H2a": h2a[0], "H2a_es": h2a[1],
            "H2b_vero": verita["h2b_vero_blitz"], "H2b": h2b[0], "H2b_es": h2b[1],
            "additivo_pp": stima("additivo_pp_sotto10_blitz", "tutti")[0],
            "finestra": stima("altre_blitz", "ROBUSTEZZA due giocatori, stessa finestra di")[0],
            "impennata": stima("altre_blitz", "impennata")[0]}


def main():
    scelti = [sys.argv[1]] if len(sys.argv) > 1 else list(SCENARI)
    for nome in scelti:
        argomenti, semi = SCENARI[nome]
        semi = int(sys.argv[2]) if len(sys.argv) > 2 else semi
        prove = pd.DataFrame([una_prova(argomenti, 100 + s) for s in range(semi)])
        media, es = prove.mean(), prove.std(ddof=1) / np.sqrt(len(prove))
        print(f"{nome} ({semi} semi): " + "; ".join(f"{c} {media[c]:.3f}" + (f" (+-{es[c]:.3f})" if not c.endswith(("_vero", "_es")) else "")
                                                   for c in prove.columns), flush=True)
        if semi >= 4:
            print(f"    dispersione tra semi / errore standard del bootstrap: H2a {prove['H2a'].std(ddof=1) / prove['H2a_es'].mean():.2f}, "
                  f"H2b {prove['H2b'].std(ddof=1) / prove['H2b_es'].mean():.2f}", flush=True)


if __name__ == "__main__":
    main()
