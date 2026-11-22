"""
tests/verifica_11.py - Controlli d'identita' sul nucleo numerico di 11_pressione.py

Tre controlli, su dati piccoli inventati (non servono i dati veri):
  1. modello additivo: stesse differenze tra fasce di una regressione "a forza bruta"
     con una dummy per ogni coppia partita-giocatore; stesso errore standard robusto;
  2. modello moltiplicativo: stessi log RR di una Poisson a forza bruta con una dummy
     per ogni coppia;
  3. se i dati sono davvero moltiplicativi (e il tempo non dipende dal passato), lo
     stimatore ritrova il RR inserito, e l'errore standard dei contributi coincide con
     la dispersione delle stime su molte repliche.

Uso (dalla cartella degli script):
    python tests\\verifica_11.py
"""

import importlib
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
p11 = importlib.import_module("11_pressione")


def dati(rng, n_gruppi=150, n_fasce=8, n_strati=12, rr=None, mosse=(8, 40)):
    """Coppie con livelli di errore diversi; il tempo cala lungo la partita; strati a caso."""
    lunghezze = rng.integers(mosse[0], mosse[1], n_gruppi)
    gruppo = np.repeat(np.arange(n_gruppi), lunghezze)
    posizione = np.concatenate([np.arange(l) / l for l in lunghezze])
    lento = np.repeat(rng.random(n_gruppi), lunghezze)                 # chi pensa di piu' arriva prima a corto di tempo
    fascia = np.clip(((1 - posizione) * n_fasce * (1.3 - lento) + rng.normal(0, 0.7, len(gruppo))).astype(int), 0, n_fasce - 1)
    strato = np.clip((posizione * n_strati + rng.normal(0, 2, len(gruppo))).astype(int), 0, n_strati - 1)
    gioc = np.repeat(rng.integers(0, n_gruppi // 3, n_gruppi), lunghezze)
    livello = np.repeat(np.exp(rng.normal(-2.6, 0.6, n_gruppi)) * (1 + lento[np.cumsum(lunghezze) - 1]), lunghezze)
    effetto_strato = np.linspace(0.5, 1.6, n_strati)[strato]
    rr = np.ones(n_fasce) if rr is None else rr
    p = np.clip(livello * effetto_strato * rr[fascia], 0, 1)
    e = (rng.random(len(gruppo)) < p).astype(np.float64)
    return gruppo, fascia, strato, gioc, e


def forza_bruta_additivo(gruppo, fb, strato, gioc, y, n_fb, n_strati):
    n = len(y)
    X = np.zeros((n, gruppo.max() + 1 + n_fb + n_strati))
    X[np.arange(n), gruppo] = 1
    X[np.arange(n), gruppo.max() + 1 + fb] = 1
    X[np.arange(n), gruppo.max() + 1 + n_fb + strato] = 1
    theta = np.linalg.lstsq(X, y, rcond=None)[0]
    res = y - X @ theta
    inv = np.linalg.pinv(X.T @ X)
    punteggi = np.zeros((gioc.max() + 1, X.shape[1]))
    np.add.at(punteggi, gioc, X * res[:, None])
    V = inv @ (punteggi.T @ punteggi) @ inv
    c = np.zeros(X.shape[1]); c[gruppo.max() + 1], c[gruppo.max() + 2] = 1, -1
    return theta[gruppo.max() + 1:gruppo.max() + 1 + n_fb], float(np.sqrt(c @ V @ c))


def forza_bruta_poisson(gruppo, fb, strato, e, n_fb, n_strati):
    tieni = np.bincount(gruppo, weights=e)[gruppo] > 0                 # le coppie senza errori non danno informazione
    gruppo, fb, strato, e = np.unique(gruppo[tieni], return_inverse=True)[1], fb[tieni], strato[tieni], e[tieni]
    n, ng = len(e), gruppo.max() + 1
    X = np.zeros((n, ng + n_fb - 1 + n_strati - 1))
    X[np.arange(n), gruppo] = 1
    X[fb > 0, ng + fb[fb > 0] - 1] = 1
    X[strato > 0, ng + n_fb - 1 + strato[strato > 0] - 1] = 1
    theta = np.zeros(X.shape[1]); theta[:ng] = np.log(e.mean())
    for _ in range(200):
        mu = np.exp(X @ theta)
        passo = np.linalg.lstsq(X.T @ (X * mu[:, None]), X.T @ (e - mu), rcond=None)[0]
        theta += np.clip(passo, -2, 2)
        if np.abs(passo).max() < 1e-11:
            break
    return np.r_[0.0, theta[ng:ng + n_fb - 1]]


def main():
    rng = np.random.default_rng(11)
    tutto_ok = True

    def esito(nome, scarto, soglia):
        nonlocal tutto_ok
        ok = scarto < soglia
        tutto_ok &= ok
        print(f"  {'OK ' if ok else 'ERRORE'} {nome}: scarto massimo {scarto:.2e} (soglia {soglia:.0e})")

    print("1. Modello additivo contro la regressione a forza bruta")
    gruppo, fascia, strato, gioc, e = dati(rng, rr=np.array([3, 2.4, 1.7, 1.25, 1.1, 1, 1, 1.0]))
    st = p11.Struttura(gruppo, fascia, strato, gioc, gioc.max() + 1, 8, 12)
    for nome, mappa in (("8 fasce", np.arange(8)), ("2 fasce", p11.SOTTO_10)):
        beta, contributi = p11.stima_additiva(st, 100 * e, mappa)
        bruta, es_bruto = forza_bruta_additivo(gruppo, mappa[fascia], strato, gioc, 100 * e, mappa.max() + 1, 12)
        esito(f"differenze tra fasce, {nome}", np.abs((beta - beta[-1]) - (bruta - bruta[-1])).max(), 1e-7)
        es = np.sqrt(((contributi[:, 0] - contributi[:, 1]) ** 2).sum())
        esito(f"errore standard robusto, {nome} (scarto relativo)", abs(es / es_bruto - 1), 1e-3)
        esito(f"i contributi sommano a zero, {nome}", np.abs(contributi.sum(axis=0) - contributi.sum(axis=0).mean()).max(), 1e-7)

    print("2. Modello moltiplicativo contro la Poisson a forza bruta")
    for nome, mappa in (("8 fasce", np.arange(8)), ("2 fasce", p11.SOTTO_10)):
        logB, _, passi, scarto = p11.stima_moltiplicativa(st, e, mappa)
        bruta = forza_bruta_poisson(gruppo, mappa[fascia], strato, e, mappa.max() + 1, 12)
        esito(f"log RR, {nome} ({passi} passi)", np.abs((logB - logB[0]) - bruta).max(), 1e-6)
        esito(f"attesi = osservati per fascia, {nome}", scarto, 1e-6)

    print("3. Dati moltiplicativi: il RR inserito viene ritrovato? L'errore standard e' giusto?")
    for nome, rr_vero in (("RR = 1 (nessun effetto)", 1.0), ("RR = 2", 2.0)):
        rr = np.where(p11.SOTTO_10 == 0, rr_vero, 1.0)
        stime, errori, additive = [], [], []
        for _ in range(150):
            gruppo, fascia, strato, gioc, e = dati(rng, n_gruppi=1500, rr=rr)
            st = p11.Struttura(gruppo, fascia, strato, gioc, gioc.max() + 1, 8, 12)
            logB, C, _, _ = p11.stima_moltiplicativa(st, e, p11.SOTTO_10)
            stime.append(logB[0] - logB[1])
            errori.append(np.sqrt(((C[:, 0] - C[:, 1]) ** 2).sum()))
            beta, _ = p11.stima_additiva(st, 100 * e, p11.SOTTO_10)
            additive.append(beta[0] - beta[1])
        media, es_media = np.mean(stime), np.std(stime, ddof=1) / np.sqrt(len(stime))
        rapporto = np.std(stime, ddof=1) / np.mean(errori)
        print(f"  {nome}: log RR vero {np.log(rr_vero):.3f}; media delle stime {media:.3f} (+-{es_media:.3f}); "
              f"dispersione / errore standard = {rapporto:.2f}; additivo medio {np.mean(additive):.2f} pp")
        esito(f"stima entro 3 errori standard dal vero, {nome}", abs(media - np.log(rr_vero)) / es_media, 3.0)
        esito(f"errore standard calibrato (tra 0,8 e 1,25), {nome}", abs(np.log(rapporto)), np.log(1.25))

    print("\nTUTTI I CONTROLLI SUPERATI" if tutto_ok else "\nATTENZIONE: almeno un controllo NON superato")
    sys.exit(0 if tutto_ok else 1)


if __name__ == "__main__":
    main()
