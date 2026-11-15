"""Verifica indipendente di 05_sessioni.py: ricalcola sessioni e blocchi con un ciclo Python
(logica riscritta da zero, senza SQL) su un campione di giocatori e confronta riga per riga."""
import duckdb
import pandas as pd
con = duckdb.connect()
df = con.sql("""
  SELECT * FROM read_parquet('data/giocatore_partita/*.parquet')
  WHERE gid IN (SELECT gid FROM read_parquet('data/giocatore_partita/*.parquet') GROUP BY gid HAVING COUNT(*) >= 30 ORDER BY gid LIMIT 150)
  ORDER BY gid, t_inizio, game_id
""").df()
CL = {"bullet", "blitz", "rapid"}
err = 0; n = 0
for gid, g in df.groupby("gid", sort=False):
    sess = 0; pos = 0; blocco = 0; pos_b = 0; prec = None; rif = {}
    for r in g.itertuples():
        pausa = None if prec is None else r.t_inizio - prec.t_fine
        if prec is None or pausa > 1800:
            sess += 1; pos = 0; rif = {}
        pos += 1
        rif.setdefault(r.speed, r.elo)
        elig = bool(r.valida) and not r.is_tournament and r.classe in CL
        continua = (elig and prec is not None and prec_elig and prec.classe == r.classe
                    and prec_sess == sess and pausa >= -10)
        if elig:
            if continua: pos_b += 1
            else: blocco += 1; pos_b = 1
        atteso = (sess, pos, rif[r.speed], blocco if elig else None, pos_b if elig else None,
                  None if prec is None or pd.isna(prec.punteggio) else float(prec.punteggio))
        avuto = (r.sessione, r.pos, r.rating_rif, None if pd.isna(r.blocco) else int(r.blocco),
                 None if pd.isna(r.pos_blocco) else int(r.pos_blocco),
                 None if pd.isna(r.prec_punteggio) else float(r.prec_punteggio))
        n += 1
        if atteso != avuto:
            err += 1
            if err <= 5: print("DIVERSO", gid, r.game_id, atteso, avuto)
        prec, prec_elig, prec_sess = r, elig, sess
print(f"righe controllate: {n:,} - differenze: {err}")
# controlli a campione su serie e coppie a distanza 2
print(con.sql("""
  SELECT COUNT(*) righe, SUM((pos_blocco>1)::INT) coppie, SUM((pos_blocco>2 AND prec2_punteggio IS NOT NULL)::INT) dist2,
         SUM((pos_blocco>1 AND avv = prec_avv)::INT) rivincite, SUM(lato_scelto::INT) scelti,
         MIN(serie_prec) min_serie, MAX(serie_prec) max_serie, SUM(coppia_x::INT) coppie_x, SUM((coppia_x AND rating_rif_x IS NULL)::INT) x_senza_rif
  FROM read_parquet('data/giocatore_partita/*.parquet')""").df().to_string(index=False))
print(con.sql("""SELECT gid, pos_blocco, punteggio, prec_punteggio, prec2_punteggio, serie_prec, avv, prec_avv, round(pausa_s) pausa, elo, rating_rif
  FROM read_parquet('data/giocatore_partita/*.parquet') WHERE gid = (SELECT MIN(gid) FROM read_parquet('data/giocatore_partita/*.parquet') WHERE n_blocco = 9) AND n_blocco = 9 ORDER BY t_inizio LIMIT 9""").df().to_string(index=False))
