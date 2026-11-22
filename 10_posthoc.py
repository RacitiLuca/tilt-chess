"""
10_posthoc.py - Approfondimenti POST HOC sulla domanda 1 (decisione 13 di HANDOFF.md)

ATTENZIONE: analisi ESPLORATIVE, non pre-registrate, scritte DOPO aver visto la
conferma. Non cambiano nessun verdetto confermativo: servono a scrivere la frase
giusta sulla persistenza e sul fotofinish. Le regole di lettura sono state fissate
prima di eseguire (HANDOFF.md, "Specifica degli approfondimenti post hoc") e sono
ripetute nell'output.

08_tilt.py e' bloccato e non si tocca: qui se ne riusano le funzioni.

  Controllo d'identita'  Senza restrizioni lo script deve ridare i numeri di 08
                         (stessi rimescolamenti, stessi ricampionamenti).
  PH1  Stimatore B sullo stesso campione della stima congiunta (esiti con almeno 4
       partite prima nel blocco) e sul complemento (da 1 a 3 partite prima).
  PH4  Fotofinish stratificato per punteggio atteso, con placebo (la partita PRIMA
       del fotofinish) e riga di selezione.
  PH3  Stima congiunta con sei distanze.
  PH2  Stima congiunta per classe e per fascia di rating.
  PH6  Stima congiunta per pausa prima della partita (fino a 60 secondi / oltre).
  (PH5, asimmetria tra sconfitta e vittoria: non scritto.)

Uso (PowerShell, nella cartella C:\\tilt; prima esplorazione, poi conferma):
    .\\.venv\\Scripts\\python 10_posthoc.py
    .\\.venv\\Scripts\\python 10_posthoc.py --gruppo conferma
"""

import argparse
import importlib
import time

import numpy as np
import pandas as pd

from tilt_utils import CARTELLA_DATI, CARTELLA_OUTPUT, CLASSI, Registro, apri_duckdb

m08 = importlib.import_module("08_tilt")      # il nome comincia con una cifra: non si puo' scrivere "import 08_tilt"
bootstrap_somme, intervallo, p_normale = m08.bootstrap_somme, m08.intervallo, m08.p_normale


def fdr(p):
    """Correzione di Benjamini-Hochberg: per ogni p, il piu' piccolo livello FDR a cui sarebbe rifiutato."""
    p = np.asarray(p, dtype=np.float64)
    q = np.full(len(p), np.nan)
    validi = np.flatnonzero(np.isfinite(p))
    if len(validi) == 0:
        return q
    ordine = validi[np.argsort(p[validi])]
    grezzi = p[ordine] * len(validi) / np.arange(1, len(validi) + 1)
    q[ordine] = np.minimum(np.minimum.accumulate(grezzi[::-1])[::-1], 1.0)
    return q


def riga(analisi, cella, stima, boot, n, p=None):
    """Una riga del riepilogo: stima e ricampionamenti in frazione -> punti percentuali."""
    lo, hi, es = intervallo(boot)
    return {"analisi": analisi, "cella": cella, "stima_pp": 100 * stima, "ic95_da": 100 * lo, "ic95_a": 100 * hi,
            "err_std": 100 * es, "p": p_normale(stima, es) if p is None else p, "n": n}


# --------------------------------------------------------------------------
# Controllo d'identita' e PH1: stimatore B con restrizioni sugli esiti
# --------------------------------------------------------------------------
def b_con_restrizioni(dati, opz, reg, righe):
    """Stimatore B (versione "residuo" di 08) su tre insiemi di esiti, con gli STESSI rimescolamenti.

    Il generatore casuale e' usato nello stesso ordine di 08_tilt.py: per questo, senza
    restrizioni, stima, distorsione b e intervallo coincidono con quelli di 08.
    """
    t0 = time.time()
    base = dati.esito_ok.copy()
    maschere = {"tutti gli esiti (come 08)": base,
                "PH1: almeno 4 partite prima (pos >= 4)": base & (dati.pos >= 4),
                "PH1: da 1 a 3 partite prima (pos 1-3)": base & (dati.pos >= 1) & (dati.pos <= 3)}
    rng = np.random.default_rng(opz.seme)
    K = opz.rimescolamenti
    in_ordine = np.arange(dati.n)
    oss, rim, tau_rim, coppie, blocchi = {}, {}, {}, {}, {}
    for nome, maschera in maschere.items():
        dati.esito_ok = maschera
        w, num, _, ok = dati.regressione(in_ordine, 1)
        oss[nome] = dati.somme_giocatore(w, num)
        rim[nome] = np.zeros_like(oss[nome])
        tau_rim[nome] = np.empty((K, m08.N_CELLE_B))
        classe_ok, classe_w = dati.classe_blk[dati.blk[ok]], dati.classe_blk[w > 0]
        coppie[nome] = [int(ok.sum())] + [int((classe_ok == i).sum()) for i in range(len(CLASSI))]
        blocchi[nome] = [int((w > 0).sum())] + [int((classe_w == i).sum()) for i in range(len(CLASSI))]
    for k in range(K):
        ordine = dati.ordine_casuale(rng, entro_tipo=True)
        for nome, maschera in maschere.items():
            dati.esito_ok = maschera
            w, num, _, _ = dati.regressione(ordine, 1)
            Mk = dati.somme_giocatore(w, num)
            rim[nome] += Mk / K
            tau_rim[nome][k] = m08.tau_e_pendenza(Mk.sum(axis=0))[0]
        rng.random(dati.n)       # 08 qui estrae anche lo schema "libero": lo salto, ma consumo gli stessi numeri casuali
        if (k + 1) % 50 == 0:
            print(f"  rimescolamento {k + 1}/{K} - {time.time() - t0:.0f} s")
    dati.esito_ok = base
    # 08 fa un bootstrap (regressioni separate per distanza) prima di quello di B: consumo gli stessi numeri
    bootstrap_somme(np.zeros((dati.n_gioc, 1)), opz.bootstrap, rng)
    tabelle, identita = [], None
    celle = ["tutte"] + [f"classe {c}" for c in CLASSI]
    for nome in maschere:
        tau_oss, b, tau_B, _, _ = m08.stime_B(oss[nome].sum(axis=0), rim[nome].sum(axis=0))
        centro = tau_rim[nome].mean(axis=0)
        p_perm = (1 + (np.abs(tau_rim[nome] - centro) >= np.abs(tau_oss - centro)).sum(axis=0)) / (K + 1)
        S = bootstrap_somme(np.hstack([oss[nome], rim[nome]]), opz.bootstrap, rng)
        nc = oss[nome].shape[1]
        tau_boot = m08.stime_B(S[:, :nc], S[:, nc:])[2]
        lo, hi, es = intervallo(tau_boot)
        for j, cella in enumerate(celle):
            tabelle.append({"esiti": nome, "cella": cella, "coppie": coppie[nome][j], "blocchi": blocchi[nome][j],
                            "tau_dentro_blocco_pp": 100 * tau_oss[j], "distorsione_b_pp": 100 * b[j], "tau_B_pp": 100 * tau_B[j],
                            "ic95_da": 100 * lo[j], "ic95_a": 100 * hi[j], "err_std": 100 * es[j], "p_permutazione": p_perm[j]})
            if nome.startswith("PH1"):
                righe.append({"analisi": "PH1", "cella": f"{nome} | {cella}", "stima_pp": 100 * tau_B[j], "ic95_da": 100 * lo[j],
                              "ic95_a": 100 * hi[j], "err_std": 100 * es[j], "p": p_perm[j], "n": coppie[nome][j]})
        if identita is None:
            identita = (100 * tau_B[0], 100 * lo[0], 100 * hi[0])
    reg.tabella(f"CONTROLLO D'IDENTITA' E PH1 - stimatore B per insieme di esiti ({K} rimescolamenti, {opz.bootstrap} ricampionamenti)",
                pd.DataFrame(tabelle).round({"tau_dentro_blocco_pp": 2, "distorsione_b_pp": 2, "tau_B_pp": 2, "ic95_da": 2,
                                             "ic95_a": 2, "err_std": 2, "p_permutazione": 4}))
    reg.scrivi("Lettura PH1 (fissata prima): tau_B con pos >= 4, cella 'tutte': sopra -0,35 -> lo scarto tra B e congiunta viene dal "
               "TERMINE DI PARAGONE (dipendenza diffusa sulle partite vicine); sotto -0,50 -> viene dal CAMPIONE (la persistenza sta "
               "nei blocchi lunghi); in mezzo -> entrambe. Previsione scritta prima: circa -0,5.")
    reg.scrivi(f"(B con restrizioni: {time.time() - t0:.0f} s)")
    return identita


def congiunta(dati, opz, maschera=None):
    """Stima congiunta di 08 (P10) su un sottoinsieme di esiti. Restituisce tau, ricampionamenti, coppie, matrice."""
    base = dati.esito_ok
    if maschera is not None:
        dati.esito_ok = base & maschera
    M, coppie = dati.somme_congiunte(per_tipo=True)
    dati.esito_ok = base
    tau = m08.stime_congiunte(M.sum(axis=0))[0]
    # stesso generatore di 08 per la congiunta: senza restrizioni l'intervallo coincide; e tutte le
    # celle usano gli stessi ricampionamenti dei giocatori, quindi le differenze tra celle sono coerenti
    boot = m08.stime_congiunte(bootstrap_somme(M, opz.bootstrap, np.random.default_rng([opz.seme, 10])))
    return tau, boot, coppie, M


def controlla_identita(opz, reg, identita_B, tau_c, boot_c):
    """Confronta con output/08_stime_<gruppo>.csv, se c'e'."""
    lo, hi, _ = intervallo(boot_c)
    miei = {("B", "tutte"): identita_B}
    for j in range(3):
        miei[("B_distanza", f"partita +{j + 1}")] = (100 * tau_c[j], 100 * lo[j], 100 * hi[j])
    file_08 = CARTELLA_OUTPUT / f"08_stime_{opz.gruppo}.csv"
    reg.scrivi("\n== CONTROLLO D'IDENTITA' con 08_tilt.py (variante principale) ==")
    if not file_08.exists():
        reg.scrivi(f"{file_08} non trovato: confronta a mano con 08_tilt_{opz.gruppo}.txt "
                   "(conferma: tau_B -0,07 (-0,24; 0,09); congiunta -0,68 / -0,69 / -0,34).")
        for chiave, v in miei.items():
            reg.scrivi(f"  {chiave[0]:11s} {chiave[1]:11s} qui: {v[0]:.4f} ({v[1]:.4f}; {v[2]:.4f})")
        return None
    csv = pd.read_csv(file_08)
    tutto_ok = True
    for chiave, v in miei.items():
        r = csv[(csv["analisi"] == chiave[0]) & (csv["cella"] == chiave[1])]
        if len(r) == 0:
            reg.scrivi(f"  {chiave}: riga non trovata nel CSV di 08")
            tutto_ok = False
            continue
        atteso = r[["stima_pp", "ic95_da", "ic95_a"]].iloc[0].to_numpy(dtype=np.float64)
        scarto = np.abs(np.array(v) - atteso).max()
        tutto_ok &= bool(scarto < 1e-6)
        reg.scrivi(f"  {chiave[0]:11s} {chiave[1]:11s} qui: {v[0]:.4f} ({v[1]:.4f}; {v[2]:.4f})   08: {atteso[0]:.4f} "
                   f"({atteso[1]:.4f}; {atteso[2]:.4f})   scarto massimo {scarto:.1e}")
    reg.scrivi("IDENTITA' VERIFICATA: gli stessi numeri di 08." if tutto_ok else
               "ATTENZIONE: I NUMERI NON COINCIDONO CON 08. C'e' un errore (o dati/opzioni diversi): NON usare i risultati qui sotto.")
    return tutto_ok


# --------------------------------------------------------------------------
# PH4: fotofinish stratificato per atteso, con placebo
# --------------------------------------------------------------------------
N_FASCE_ATTESO = 14      # fasce di 0,05 da 0,20 a 0,80, con le due code unite


def somme_strati(valore, perde, strato, gioc, n_gioc, n_strati, tieni):
    """Matrice giocatori x (strati x 4): somma e numero dei valori di perdenti e vincitori in ogni strato."""
    M = np.zeros((n_gioc, n_strati * 4))
    for j, m in enumerate((tieni & perde, tieni & ~perde)):
        indice = gioc[m] * n_strati + strato[m]
        M[:, 2 * j::4] = np.bincount(indice, weights=valore[m], minlength=n_gioc * n_strati).reshape(n_gioc, n_strati)
        M[:, 2 * j + 1::4] = np.bincount(indice, minlength=n_gioc * n_strati).reshape(n_gioc, n_strati)
    return M


def stima_strati(S):
    """Dalle somme per strato: media pesata delle differenze perdenti - vincitori, pesi nL*nW/(nL+nW)."""
    S = np.atleast_2d(S)
    sL, nL, sW, nW = S[:, 0::4], S[:, 1::4], S[:, 2::4], S[:, 3::4]
    with np.errstate(divide="ignore", invalid="ignore"):
        valido = (nL > 0) & (nW > 0)
        peso = np.where(valido, nL * nW / np.where(valido, nL + nW, 1.0), 0.0)
        diff = np.where(valido, sL / np.where(valido, nL, 1.0) - sW / np.where(valido, nW, 1.0), 0.0)
        return (peso * diff).sum(axis=1) / peso.sum(axis=1)


def fotofinish_stratificato(con, analisi, opz, reg, righe):
    filtro = m08.filtri_comuni(opz.gruppo, opz, con_lato=False)
    # n = partita successiva al fotofinish G (stesse righe del fotofinish di 08); g = la riga di G dello
    # stesso giocatore; p = la partita che precede G nello stesso blocco (per il placebo)
    d = con.execute(f"""
        WITH n AS (SELECT gid, classe, prec_game_id, prec_punteggio, y - base_altre AS val, prec_clk_fin_vinc
                   FROM {analisi}
                   WHERE {filtro} AND pos_blocco > 1 AND avv <> prec_avv AND prec_punteggio IN (0, 1)
                     AND prec_clk_fin_vinc <= 5 AND base_altre IS NOT NULL AND y IS NOT NULL)
        SELECT n.gid, {m08.SQL_CLASSE_ID.replace('CASE classe', 'CASE n.classe')} AS classe_id, (n.prec_punteggio = 0) AS perde,
               n.val, n.prec_clk_fin_vinc AS clk_vinc,
               g.atteso, (g.elo - g.elo_avv)::DOUBLE AS vantaggio, g.rating_rif::DOUBLE AS rating, g.pos::DOUBLE AS pos,
               100 * g.base_altre AS base_pp, g.prec_punteggio AS prima,
               CASE WHEN g.pos_blocco > 1 AND p.base_altre IS NOT NULL THEN p.y - p.base_altre END AS placebo
        FROM n
        JOIN {analisi} g ON g.gid = n.gid AND g.game_id = n.prec_game_id
        LEFT JOIN {analisi} p ON p.gid = g.gid AND p.game_id = g.prec_game_id
    """).df()
    reg.scrivi("\n################ PH4 - FOTOFINISH STRATIFICATO PER ATTESO, CON PLACEBO ################")
    if len(d) == 0:
        reg.scrivi("Nessuna coppia disponibile.")
        return
    giocatori, gioc = np.unique(d["gid"].to_numpy(), return_inverse=True)
    n_gioc = len(giocatori)
    perde = d["perde"].to_numpy().astype(bool)
    val = d["val"].to_numpy(dtype=np.float64)
    placebo = d["placebo"].to_numpy(dtype=np.float64)
    ha_p = np.isfinite(placebo)
    classe = d["classe_id"].to_numpy().astype(np.int64)
    atteso = d["atteso"].to_numpy(dtype=np.float64)
    ha_atteso = np.isfinite(atteso)                                                         # manca solo in casi rari: fuori dagli strati
    fascia = np.clip(np.floor(np.nan_to_num(atteso, nan=0.5) / 0.05 + 1e-9).astype(np.int64), 3, 16) - 3   # 0 = sotto 0,20 ... 13 = da 0,80
    strato = classe * N_FASCE_ATTESO + fascia
    n_strati = len(CLASSI) * N_FASCE_ATTESO
    entro3 = d["clk_vinc"].to_numpy() <= 3
    rng_seme = [opz.seme, 104]
    tab, tab_p = [], []
    celle = [("tutte", np.ones(len(d), dtype=bool))] + [(c, classe == CLASSI.index(c)) for c in ("bullet", "blitz")]
    for soglia, m_soglia in (("3 s", entro3), ("5 s", np.ones(len(d), dtype=bool))):
        for nome, m_cella in celle:
            m = m_soglia & m_cella
            if (m & perde).sum() < m08.N_MIN_CELLA or (m & ~perde).sum() < m08.N_MIN_CELLA:
                continue
            etichetta = f"vincitore entro {soglia}, {nome}"
            # non stratificato (deve ridare il fotofinish di 08) e stratificato, con gli stessi ricampionamenti
            uno = np.zeros(len(d), dtype=np.int64)
            ms = m & ha_atteso
            M = np.hstack([somme_strati(val, perde, uno, gioc, n_gioc, 1, m), somme_strati(val, perde, strato, gioc, n_gioc, n_strati, ms),
                           somme_strati(val, perde, strato, gioc, n_gioc, n_strati, ms & ha_p),
                           somme_strati(np.nan_to_num(placebo), perde, strato, gioc, n_gioc, n_strati, ms & ha_p)])
            tot, S = M.sum(axis=0), bootstrap_somme(M, opz.bootstrap, np.random.default_rng(rng_seme))
            tagli = np.cumsum([0, 4, 4 * n_strati, 4 * n_strati, 4 * n_strati])
            stime = [stima_strati(tot[a:b])[0] for a, b in zip(tagli[:-1], tagli[1:])]
            boot = [stima_strati(S[:, a:b]) for a, b in zip(tagli[:-1], tagli[1:])]
            for j, tipo in enumerate(("non stratificato (come 08)", "STRATIFICATO per atteso")):
                r = riga("PH4", f"{etichetta} | {tipo}", stime[j], boot[j], int(m.sum()))
                tab.append({"cella": etichetta, "stima": tipo, "perdenti": int((m & perde).sum()), "vincitori": int((m & ~perde).sum()),
                            **{k: r[k] for k in ("stima_pp", "ic95_da", "ic95_a", "err_std", "p")}})
                righe.append(r)
            n_p = int((ms & ha_p).sum())
            for tipo, stima, b in (("dopo il fotofinish, solo chi ha la partita prima", stime[2], boot[2]),
                                   ("PLACEBO: la partita PRIMA del fotofinish", stime[3], boot[3]),
                                   ("differenza dopo - prima", stime[2] - stime[3], boot[2] - boot[3])):
                r = riga("PH4_placebo", f"{etichetta} | {tipo}", stima, b, n_p)
                tab_p.append({"cella": etichetta, "stima": tipo, "coppie": n_p, **{k: r[k] for k in ("stima_pp", "ic95_da", "ic95_a", "err_std", "p")}})
                righe.append(r)
    arrot = {"stima_pp": 2, "ic95_da": 2, "ic95_a": 2, "err_std": 2, "p": 4}
    reg.tabella("PH4 - partita successiva al fotofinish: perdente - vincitore (pp), ciascuno rispetto alla propria base. "
                "Strati: atteso nella partita del fotofinish (fasce di 0,05, code unite) x classe; pesi nL*nW/(nL+nW)",
                pd.DataFrame(tab).round(arrot))
    reg.tabella("PH4 - PLACEBO: stessa stima sulla partita che PRECEDE il fotofinish nello stesso blocco (stessi strati e pesi)",
                pd.DataFrame(tab_p).round(arrot))
    # Controllo semplice: solo partite quasi alla pari, senza strati
    m = entro3 & ha_atteso & (np.abs(np.nan_to_num(atteso) - 0.5) <= 0.05)
    tab_s = []
    for nome, m_cella in celle:
        mm = m & m_cella
        if (mm & perde).sum() < m08.N_MIN_CELLA or (mm & ~perde).sum() < m08.N_MIN_CELLA:
            continue
        M = somme_strati(val, perde, np.zeros(len(d), dtype=np.int64), gioc, n_gioc, 1, mm)
        r = riga("PH4_alla_pari", f"entro 3 s, atteso tra 0,45 e 0,55, {nome}", stima_strati(M.sum(axis=0))[0],
                 stima_strati(bootstrap_somme(M, opz.bootstrap, np.random.default_rng(rng_seme))), int(mm.sum()))
        tab_s.append({k: r[k] for k in ("cella", "n", "stima_pp", "ic95_da", "ic95_a", "err_std", "p")})
        righe.append(r)
    if tab_s:
        reg.tabella("PH4 - controllo semplice: solo fotofinish con atteso tra 0,45 e 0,55, senza strati", pd.DataFrame(tab_s).round(arrot))

    # Bilanciamento con i pesi di strato (entro 3 s): differenze nell'unita' della variabile e standardizzate
    variabili = [("vantaggio di rating in G (punti)", d["vantaggio"].to_numpy(dtype=np.float64)),
                 ("atteso in G (pp)", 100 * atteso), ("rating di riferimento (punti)", d["rating"].to_numpy(dtype=np.float64)),
                 ("posizione nella sessione (partite)", d["pos"].to_numpy(dtype=np.float64)),
                 ("base del giocatore (pp)", d["base_pp"].to_numpy(dtype=np.float64)),
                 ("punteggio prima di G (pp)", 100 * d["prima"].to_numpy(dtype=np.float64))]
    tab_b = []
    for nome_cella, m_cella in celle:
        for nome, x in variabili:
            m = entro3 & m_cella & ha_atteso & np.isfinite(x)
            if (m & perde).sum() < m08.N_MIN_CELLA or (m & ~perde).sum() < m08.N_MIN_CELLA:
                continue
            xs = np.nan_to_num(x)
            grezza = xs[m & perde].mean() - xs[m & ~perde].mean()
            pesata = stima_strati(somme_strati(xs, perde, strato, gioc, n_gioc, n_strati, m).sum(axis=0))[0]
            sd = xs[m].std()
            tab_b.append({"cella": nome_cella, "variabile": nome, "diff_grezza": grezza, "diff_con_strati": pesata,
                          "std_grezza": grezza / sd if sd > 0 else np.nan, "std_con_strati": pesata / sd if sd > 0 else np.nan})
    reg.tabella("PH4 - bilanciamento prima del fotofinish (entro 3 s): perdenti - vincitori, senza strati e con i pesi di strato; "
                "'std' = differenza divisa per la deviazione standard", pd.DataFrame(tab_b).round(3))

    # Selezione: chi ha una partita successiva utilizzabile?
    sel = con.execute(f"""
        WITH g AS (SELECT gid, game_id, classe, punteggio FROM {analisi}
                   WHERE {filtro} AND clk_fin_vinc <= 3 AND punteggio IN (0, 1)),
             n AS (SELECT gid, prec_game_id FROM {analisi}
                   WHERE {filtro} AND pos_blocco > 1 AND avv <> prec_avv AND base_altre IS NOT NULL AND y IS NOT NULL)
        SELECT g.classe, COUNT(CASE WHEN g.punteggio = 0 THEN 1 END) AS perdenti,
               ROUND(100.0 * AVG(CASE WHEN g.punteggio = 0 THEN (n.gid IS NOT NULL)::INTEGER END), 1) AS perc_perdenti_con_successiva,
               COUNT(CASE WHEN g.punteggio = 1 THEN 1 END) AS vincitori,
               ROUND(100.0 * AVG(CASE WHEN g.punteggio = 1 THEN (n.gid IS NOT NULL)::INTEGER END), 1) AS perc_vincitori_con_successiva
        FROM g LEFT JOIN n ON n.gid = g.gid AND n.prec_game_id = g.game_id
        GROUP BY ROLLUP (g.classe) ORDER BY 1 NULLS FIRST
    """).df()
    sel["classe"] = sel["classe"].fillna("tutte")
    reg.tabella("PH4 - selezione: quota di perdenti e vincitori di un fotofinish (entro 3 s) con una partita successiva utilizzabile "
                "(stesso blocco, avversario diverso). Il confronto e' solo tra chi continua", sel)
    reg.scrivi("Lettura PH4 (fissata prima): cella da guardare = blitz, entro 3 s. Placebo con IC95 che contiene lo zero E sotto 0,3 pp in "
               "valore assoluto -> 'confronto meno confuso', e alla stima stratificata si applica la regola di 1 pp. Altrimenti si riporta "
               "solo la differenza (dopo - prima), come descrittiva. In nessun caso 'causale': lo strato per atteso bilancia il rating, "
               "non la forma del momento.")
    reg.scrivi("Avvertenza dal collaudo su dati simulati (tutte, entro 3 s, stratificato). SENZA alcun tilt, con la sola forma della "
               "giornata: dopo -2,8, placebo -2,8, differenza -0,3 (IC95 -2,1; 1,6): chi e' in cattiva forma perde piu' spesso il "
               "fotofinish, e gli strati per atteso non lo correggono; il placebo invece lo riconosce. CON un tilt inserito di -3,9 pp: "
               "dopo -7,8, placebo -7,0, differenza -0,8: anche il placebo diventa negativo, perche' chi ha perso la partita prima perde "
               "piu' spesso il fotofinish. Quindi (dopo - prima) NON e' una stima del tilt: dice solo se dopo il fotofinish va peggio "
               "di quanto andasse gia' prima.")


def main():
    parser = argparse.ArgumentParser(description="Approfondimenti post hoc sulla domanda 1")
    parser.add_argument("--gruppo", choices=["esplorazione", "conferma"], default="esplorazione")
    parser.add_argument("--rimescolamenti", type=int, default=200)
    parser.add_argument("--bootstrap", type=int, default=1000)
    parser.add_argument("--seme", type=int, default=20170501)
    parser.add_argument("--memoria", default="3GB")
    opz = parser.parse_args()
    # Le opzioni della variante principale di 08_tilt.py
    opz.rivincite, opz.rating, opz.due_lati, opz.senza_corte = False, "riferimento", False, False
    opz.col_stabile, opz.soglia = "stabile", 30

    analisi = f"read_parquet('{(CARTELLA_DATI / 'analisi').as_posix()}/*.parquet')"
    reg = Registro(f"10_posthoc_{opz.gruppo}")
    reg.scrivi("ANALISI POST HOC, ESPLORATIVE: non pre-registrate, scritte dopo aver visto la conferma")
    reg.scrivi(f"Gruppo: {opz.gruppo} | opzioni della variante principale di 08 | seme {opz.seme} | "
               f"{opz.rimescolamenti} rimescolamenti, {opz.bootstrap} ricampionamenti")
    reg.scrivi("Nessuna di queste analisi puo' cambiare i verdetti confermativi. p_fdr: correzione di Benjamini-Hochberg su tutte le celle.")
    con = apri_duckdb(opz.memoria)
    inizio = time.time()
    righe = []

    dati = m08.DatiBlocchi(con, analisi, opz.gruppo, opz)
    reg.scrivi(f"\n{dati.n:,} partite in {dati.nb:,} blocchi di {dati.n_gioc:,} giocatori")

    # ---- Controllo d'identita' e PH1 ----
    identita_B = b_con_restrizioni(dati, opz, reg, righe)
    tau_c, boot_c, coppie_c, _ = congiunta(dati, opz)
    controlla_identita(opz, reg, identita_B, tau_c, boot_c)

    # ---- PH4 ----
    fotofinish_stratificato(con, analisi, opz, reg, righe)

    # ---- PH3: sei distanze ----
    reg.scrivi("\n################ PH3 - STIMA CONGIUNTA CON SEI DISTANZE ################")
    tab = []
    m08.N_DISTANZE = 6                       # somme_congiunte e stime_congiunte leggono la costante a ogni chiamata
    try:
        tau6, boot6, coppie6, _ = congiunta(dati, opz)
    finally:
        m08.N_DISTANZE = 3
    tau3, boot3, coppie3, _ = congiunta(dati, opz, dati.pos >= 7)
    for j in range(6):
        r = riga("PH3", f"sei distanze | partita +{j + 1}", tau6[j], boot6[:, j], coppie6[j])
        righe.append(r)
        tab.append({"distanza": f"partita +{j + 1}", "coppie": coppie6[j], **{k: r[k] for k in ("stima_pp", "ic95_da", "ic95_a", "err_std", "p")}})
    for j in range(3):
        r = riga("PH3", f"tre distanze, stessi esiti (pos >= 7) | partita +{j + 1}", tau3[j], boot3[:, j], coppie3[j])
        righe.append(r)
        tab.append({"distanza": f"confronto, tre distanze con pos >= 7: +{j + 1}", "coppie": coppie3[j],
                    **{k: r[k] for k in ("stima_pp", "ic95_da", "ic95_a", "err_std", "p")}})
    for j in range(3):
        tab.append({"distanza": f"per memoria, tre distanze, tutti gli esiti (08): +{j + 1}", "coppie": coppie_c[j], "stima_pp": 100 * tau_c[j],
                    "ic95_da": 100 * intervallo(boot_c[:, j])[0], "ic95_a": 100 * intervallo(boot_c[:, j])[1]})
    reg.tabella("PH3 - effetto del risultato inatteso di 1...6 partite prima, a parita' delle altre. Paragone: partite almeno 7 posti "
                "prima (blocchi da 8 in su)", pd.DataFrame(tab).round({"stima_pp": 2, "ic95_da": 2, "ic95_a": 2, "err_std": 2, "p": 4}))
    reg.scrivi("Lettura PH3 (fissata prima): IC95 di +4, +5, +6 che contengono lo zero -> l'ipotesi 'dopo 3 partite l'effetto e' finito' "
               "e' accettabile. Ancora negativi -> persistenza lenta, la congiunta a tre distanze e' schiacciata verso zero: in quel caso "
               "dire se l'IC95 di +1 a sei distanze resta dentro +-1 pp (sensibilita', non sostituisce il verdetto). Un effetto che non "
               "cala resta invisibile anche qui.")

    # ---- PH2: congiunta per classe e per livello ----
    reg.scrivi("\n################ PH2 - STIMA CONGIUNTA PER CLASSE E PER FASCIA DI RATING ################")
    tab, matrici = [], {}
    classe_riga, fascia_riga = dati.classe_blk[dati.blk], dati.fascia_blk[dati.blk]
    celle = [(f"classe {c}", classe_riga == i) for i, c in enumerate(CLASSI)] + \
            [(f"rating {nome}", fascia_riga == i) for i, nome in enumerate(m08.FASCE_RATING)]
    for nome, maschera in celle:
        tau, boot, coppie, matrici[nome] = congiunta(dati, opz, maschera)
        for j in range(3):
            r = riga("PH2", f"{nome} | partita +{j + 1}", tau[j], boot[:, j], coppie[j])
            righe.append(r)
            tab.append({"cella": nome, "distanza": f"+{j + 1}", "coppie": coppie[j], **{k: r[k] for k in ("stima_pp", "ic95_da", "ic95_a", "err_std", "p")}})
    # Contrasto bullet - rapid a +1: le due matrici affiancate e ricampionate insieme (come fa 08)
    a, b = matrici["classe bullet"], matrici["classe rapid"]
    S = bootstrap_somme(np.hstack([a, b]), opz.bootstrap, np.random.default_rng([opz.seme, 10]))
    diff_boot = m08.stime_congiunte(S[:, :a.shape[1]])[:, 0] - m08.stime_congiunte(S[:, a.shape[1]:])[:, 0]
    diff = m08.stime_congiunte(a.sum(axis=0))[0, 0] - m08.stime_congiunte(b.sum(axis=0))[0, 0]
    r = riga("PH2", "congiunta +1: bullet - rapid", diff, diff_boot, 0)
    righe.append(r)
    tab.append({"cella": "bullet - rapid", "distanza": "+1", "coppie": 0, **{k: r[k] for k in ("stima_pp", "ic95_da", "ic95_a", "err_std", "p")}})
    reg.tabella("PH2 - stima congiunta per cella (nessun rimescolamento)", pd.DataFrame(tab).round({"stima_pp": 2, "ic95_da": 2, "ic95_a": 2, "err_std": 2, "p": 4}))
    reg.scrivi("Lettura PH2 (fissata prima): 'bullet - rapid' a +1 con lo stesso segno di B (positivo) -> l'ordine rapid > blitz > bullet "
               "non dipende dallo stimatore. Anche con lo stesso segno, il confronto tra cadenze resta 'per partita' e non alla pari.")

    # ---- PH6: pausa prima della partita ----
    reg.scrivi("\n################ PH6 (facoltativo) - STIMA CONGIUNTA PER PAUSA PRIMA DELLA PARTITA ################")
    pausa = np.asarray(con.execute(f"""
        SELECT pausa_s FROM {analisi}
        WHERE gruppo = '{opz.gruppo}' AND blocco IS NOT NULL AND n_blocco >= 2 AND {opz.col_stabile}
        ORDER BY gid, blocco, pos_blocco
    """).fetchnumpy()["pausa_s"], dtype=np.float64)
    if len(pausa) != dati.n:
        reg.scrivi("Righe non allineate con quelle di 08: PH6 saltato.")
    else:
        pausa = np.where(np.isfinite(pausa), pausa, np.inf)
        tab, mat = [], {}
        for nome, maschera in (("pausa fino a 60 s", pausa <= 60), ("pausa oltre 60 s", pausa > 60)):
            tau, boot, coppie, mat[nome] = congiunta(dati, opz, maschera)
            for j in range(3):
                r = riga("PH6", f"{nome} | partita +{j + 1}", tau[j], boot[:, j], coppie[j])
                righe.append(r)
                tab.append({"cella": nome, "distanza": f"+{j + 1}", "coppie": coppie[j], **{k: r[k] for k in ("stima_pp", "ic95_da", "ic95_a", "err_std", "p")}})
        a, b = mat["pausa fino a 60 s"], mat["pausa oltre 60 s"]
        S = bootstrap_somme(np.hstack([a, b]), opz.bootstrap, np.random.default_rng([opz.seme, 10]))
        diff_boot = m08.stime_congiunte(S[:, :a.shape[1]])[:, 0] - m08.stime_congiunte(S[:, a.shape[1]:])[:, 0]
        diff = m08.stime_congiunte(a.sum(axis=0))[0, 0] - m08.stime_congiunte(b.sum(axis=0))[0, 0]
        r = riga("PH6", "congiunta +1: pausa fino a 60 s - oltre 60 s", diff, diff_boot, 0)
        righe.append(r)
        tab.append({"cella": "fino a 60 s - oltre", "distanza": "+1", "coppie": 0, **{k: r[k] for k in ("stima_pp", "ic95_da", "ic95_a", "err_std", "p")}})
        reg.tabella("PH6 - stima congiunta secondo la pausa tra la partita precedente e l'esito",
                    pd.DataFrame(tab).round({"stima_pp": 2, "ic95_da": 2, "ic95_a": 2, "err_std": 2, "p": 4}))
        reg.scrivi("Lettura PH6: descrittiva. La pausa la sceglie il giocatore: una differenza non e' un effetto della pausa.")
    reg.scrivi("\nPH5 (asimmetria tra risultato inatteso positivo e negativo): non eseguito in questo script.")

    # ---- Riepilogo con correzione FDR ----
    riepilogo = pd.DataFrame(righe)
    riepilogo["p_fdr"] = fdr(riepilogo["p"].to_numpy())
    riepilogo = riepilogo[["analisi", "cella", "stima_pp", "ic95_da", "ic95_a", "err_std", "p", "p_fdr", "n"]]
    reg.tabella("RIEPILOGO di tutte le celle post hoc, con p corretto (FDR di Benjamini-Hochberg sulle celle di questo script)",
                riepilogo.round({"stima_pp": 2, "ic95_da": 2, "ic95_a": 2, "err_std": 2, "p": 4, "p_fdr": 4}))
    file_csv = CARTELLA_OUTPUT / f"10_posthoc_{opz.gruppo}.csv"
    riepilogo.to_csv(file_csv, index=False)
    reg.scrivi(f"\nStime salvate in {file_csv} - tempo totale {(time.time() - inizio) / 60:.1f} minuti")
    reg.chiudi()


if __name__ == "__main__":
    main()
