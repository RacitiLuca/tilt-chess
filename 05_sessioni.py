"""
05_sessioni.py - Sessioni di gioco, "partita successiva" e blocchi di analisi

Cosa fa:
  Parte da data/partite.parquet (una riga per partita) e data/orologi.parquet
  (orologi per partita) e crea:

  1. data/giocatori.parquet -> un codice numerico (gid) per ogni giocatore e il
     gruppo di analisi (20% esplorazione, 80% conferma). E' l'UNICO file nuovo
     che contiene i nomi utente: NON va nel repository pubblico.

  2. data/giocatore_partita/ -> una riga per (giocatore, partita): ogni partita
     compare due volte, una dal punto di vista di ciascun giocatore. Per ogni
     riga: fine stimata, pausa dalla partita precedente, sessione, posizione
     nella sessione, esito della partita precedente, blocco di analisi, rating
     di riferimento.

Scelte importanti (da saper difendere):
  - Ordino SEMPRE per (inizio, game_id): il file di Lichess non e' in ordine.
  - L'orario di fine non esiste nei dati: lo stimo come inizio + tempo consumato
    dai due orologi. E' una stima per difetto (mancano ritardi di rete e attese).
  - Sessione = partite dello stesso giocatore con pause fino a 30 minuti.
  - Blocco = sequenza ininterrotta, dentro una sessione, di partite valide,
    fuori torneo, della stessa classe di cadenza e non sovrapposte. Dentro un
    blocco ogni partita (tranne la prima) ha una "partita precedente" valida.
  - Lavoro a "secchi" di giocatori (gid % 8): le finestre SQL sono per giocatore,
    quindi posso elaborare un ottavo dei giocatori alla volta senza cambiare il
    risultato e senza superare la RAM.

Uso (PowerShell, nella cartella C:\\tilt):
    .\\.venv\\Scripts\\python 05_sessioni.py
Prova veloce sul 2% dei giocatori:
    .\\.venv\\Scripts\\python 05_sessioni.py --percento 2
Robustezza (soglia di sessione a 10 o 60 minuti; scrive in una cartella a parte):
    .\\.venv\\Scripts\\python 05_sessioni.py --soglia 10
"""

import argparse
import hashlib
import shutil
import time

import pyarrow as pa

from tilt_utils import CARTELLA_DATI, CLASSI, PERCENTO_ESPLORAZIONE, Registro, apri_duckdb

N_SECCHI = 8
LISTA_CLASSI = ", ".join(f"'{c}'" for c in CLASSI)


def hash_100(nome):
    """Numero da 0 a 99 ricavato dal nome con MD5: stabile su ogni PC e versione.

    Serve a dividere i giocatori in gruppi in modo casuale ma riproducibile.
    """
    return int(hashlib.md5(nome.lower().encode("utf-8")).hexdigest()[:8], 16) % 100


def crea_giocatori(con, file_partite):
    """Tabella giocatori: nome, gid (codice numerico), h100 (hash 0-99), gruppo."""
    nomi = con.execute(f"""
        SELECT white AS nome FROM read_parquet('{file_partite}') WHERE white IS NOT NULL
        UNION
        SELECT black FROM read_parquet('{file_partite}') WHERE black IS NOT NULL
        ORDER BY 1
    """).fetchnumpy()["nome"]
    tabella = pa.table({
        "nome": pa.array(nomi, type=pa.string()),
        "gid": pa.array(range(1, len(nomi) + 1), type=pa.int32()),
        "h100": pa.array([hash_100(n) for n in nomi], type=pa.int16()),
    })
    con.register("giocatori_arrow", tabella)
    con.execute(f"""
        CREATE OR REPLACE TABLE giocatori AS
        SELECT nome, gid, h100,
               CASE WHEN h100 < {PERCENTO_ESPLORAZIONE} THEN 'esplorazione' ELSE 'conferma' END AS gruppo
        FROM giocatori_arrow
    """)
    con.unregister("giocatori_arrow")
    return len(nomi)


def crea_partite_estese(con, file_partite, file_orologi):
    """Una riga per partita con i campi derivati: classe, durata, fine stimata.

    Formato dell'orologio di Lichess: [%clk] e' il tempo rimasto a chi ha appena
    mosso, incremento gia' aggiunto. L'incremento parte dalla seconda mossa.
    Quindi il tempo pensato da un giocatore in tutta la partita e':
        primo orologio - ultimo orologio + incremento * (mosse - 1)
    """
    con.execute(f"""
        CREATE OR REPLACE TABLE partite_x AS
        WITH grezzo AS (
            SELECT p.game_id, gw.gid AS gid_w, gb.gid AS gid_b, gw.h100 AS h_w, gb.h100 AS h_b,
                   p.result, p.start_utc, epoch(p.start_utc)::BIGINT AS t_inizio,
                   p.speed, p.is_tournament, p.termination, p.n_clk, p.has_eval,
                   p.white_elo, p.black_elo, p.white_rating_diff, p.black_rating_diff,
                   TRY_CAST(split_part(p.time_control, '+', 1) AS INTEGER) AS base_s,
                   TRY_CAST(split_part(p.time_control, '+', 2) AS INTEGER) AS inc_s,
                   o.w_clk_first, o.w_clk_m10, o.w_clk_last, COALESCE(o.w_n_moves, 0) AS w_n,
                   o.b_clk_first, o.b_clk_m10, o.b_clk_last, COALESCE(o.b_n_moves, 0) AS b_n
            FROM read_parquet('{file_partite}') p
            JOIN giocatori gw ON p.white = gw.nome
            JOIN giocatori gb ON p.black = gb.nome
            LEFT JOIN read_parquet('{file_orologi}') o USING (game_id)
            WHERE p.start_utc IS NOT NULL
        ),
        classi AS (
            SELECT *,
                -- Classi con le soglie ATTUALI di Lichess sulla durata stimata
                -- (tempo iniziale + 40 * incremento). Nel 2017 "Rapid" non esisteva.
                CASE WHEN speed = 'Correspondence' OR base_s IS NULL OR inc_s IS NULL THEN 'correspondence'
                     WHEN base_s + 40 * inc_s < 30 THEN 'ultrabullet'
                     WHEN base_s + 40 * inc_s < 180 THEN 'bullet'
                     WHEN base_s + 40 * inc_s < 480 THEN 'blitz'
                     WHEN base_s + 40 * inc_s < 1500 THEN 'rapid'
                     ELSE 'classical' END AS classe,
                -- Berserk (solo tornei): il giocatore dimezza il proprio tempo e
                -- rinuncia all'incremento. Si riconosce dal primo orologio.
                COALESCE(is_tournament AND base_s >= 2 AND w_clk_first <= 0.55 * base_s, FALSE) AS berserk_w,
                COALESCE(is_tournament AND base_s >= 2 AND b_clk_first <= 0.55 * base_s, FALSE) AS berserk_b
            FROM grezzo
        ),
        consumi AS (
            SELECT *,
                CASE WHEN berserk_w THEN 0 ELSE COALESCE(inc_s, 0) END AS inc_w,
                CASE WHEN berserk_b THEN 0 ELSE COALESCE(inc_s, 0) END AS inc_b
            FROM classi
        ),
        durate AS (
            SELECT *,
                CASE WHEN w_n >= 1 AND w_clk_first IS NOT NULL
                     THEN GREATEST(0, w_clk_first - w_clk_last + inc_w * (w_n - 1)) ELSE 0 END
              + CASE WHEN b_n >= 1 AND b_clk_first IS NOT NULL
                     THEN GREATEST(0, b_clk_first - b_clk_last + inc_b * (b_n - 1)) ELSE 0 END
                -- Caduta della bandierina: chi doveva muovere ha consumato anche
                -- tutto il tempo che gli restava (tocca al Bianco se w_n = b_n).
              + CASE WHEN termination = 'Time forfeit'
                     THEN COALESCE(CASE WHEN w_n = b_n THEN w_clk_last ELSE b_clk_last END, 0) ELSE 0 END
                AS durata_s
            FROM consumi
        )
        SELECT * EXCLUDE (durata_s),
               durata_s::DOUBLE AS durata_s,
               t_inizio + durata_s::DOUBLE AS t_fine,
               -- Finale "al fotofinish": senza incremento, perso per tempo, partita
               -- decisa. Salvo gli ultimi orologi di vincitore e perdente: la soglia
               -- (3 secondi) si applica in analisi, cosi' si puo' variare.
               CASE WHEN inc_s = 0 AND termination = 'Time forfeit' AND result = '1-0' THEN w_clk_last
                    WHEN inc_s = 0 AND termination = 'Time forfeit' AND result = '0-1' THEN b_clk_last END AS clk_fin_vinc,
               CASE WHEN inc_s = 0 AND termination = 'Time forfeit' AND result = '1-0' THEN b_clk_last
                    WHEN inc_s = 0 AND termination = 'Time forfeit' AND result = '0-1' THEN w_clk_last END AS clk_fin_perd
        FROM durate
    """)


def sql_secchio(secchio, soglia_s, percento):
    """SQL che costruisce le righe (giocatore, partita) per un secchio di giocatori.

    Ogni blocco WITH aggiunge un livello di funzioni finestra. Le finestre:
      w  = tutte le partite del giocatore in ordine di inizio
      ws = le partite di una sessione;  wb = le partite di un blocco
    """
    comuni = """game_id, start_utc, t_inizio, t_fine, durata_s, speed, classe, base_s, inc_s,
                is_tournament, termination, n_clk, has_eval, clk_fin_vinc, clk_fin_perd,
                (white_rating_diff IS NOT NULL AND black_rating_diff IS NOT NULL) AS diff_ok"""
    ordine = "ORDER BY t_inizio, game_id"
    return f"""
    WITH lato AS (
        -- Punto di vista del Bianco...
        SELECT gid_w AS gid, gid_b AS avv, h_w AS h100, TRUE AS bianco,
               CASE result WHEN '1-0' THEN 1.0 WHEN '0-1' THEN 0.0 WHEN '1/2-1/2' THEN 0.5 END AS punteggio,
               white_elo AS elo, black_elo AS elo_avv, white_rating_diff AS diff_rating,
               w_clk_first AS clk_first, w_clk_m10 AS clk_m10, w_clk_last AS clk_last,
               w_n AS n_mosse, berserk_w AS berserk, inc_w AS inc_eff, {comuni}
        FROM partite_x
        WHERE gid_w % {N_SECCHI} = {secchio} AND h_w < {percento} AND classe <> 'correspondence'
        UNION ALL
        -- ...e del Nero: stessa partita, ruoli scambiati.
        SELECT gid_b, gid_w, h_b, FALSE,
               CASE result WHEN '1-0' THEN 0.0 WHEN '0-1' THEN 1.0 WHEN '1/2-1/2' THEN 0.5 END,
               black_elo, white_elo, black_rating_diff,
               b_clk_first, b_clk_m10, b_clk_last, b_n, berserk_b, inc_b, {comuni}
        FROM partite_x
        WHERE gid_b % {N_SECCHI} = {secchio} AND h_b < {percento} AND classe <> 'correspondence'
    ),
    a0 AS (
        SELECT *,
            -- Partita valida: ha un esito e i rating (prima e variazione) di entrambi.
            (punteggio IS NOT NULL AND elo IS NOT NULL AND elo_avv IS NOT NULL AND diff_ok) AS valida,
            -- Partita "corta" (per i controlli di robustezza).
            (n_clk < 10 OR termination = 'Abandoned') AS corta,
            (termination = 'Time forfeit' AND punteggio = 0.0) AS persa_tempo,
            -- Ritmo: secondi per mossa dalla mossa 2 alla 10 (9 mosse).
            CASE WHEN clk_m10 IS NOT NULL THEN (clk_first - clk_m10 + 9 * inc_eff) / 9.0 END AS ritmo_10,
            -- Ogni partita conta come esito per UN solo giocatore: la scelta e'
            -- la parita' dell'ultimo carattere del game_id (casuale, 50 e 50).
            ((ascii(right(game_id, 1)) % 2 = 0) = bianco) AS lato_scelto
        FROM lato
    ),
    a1 AS (
        SELECT *,
            (valida AND NOT is_tournament AND classe IN ({LISTA_CLASSI})) AS elig,
            -- Pausa = inizio di questa partita - fine stimata della precedente.
            t_inizio - LAG(t_fine) OVER w AS pausa_s
        FROM a0 WINDOW w AS (PARTITION BY gid {ordine})
    ),
    a2 AS (
        SELECT *,
            -- Nuova sessione quando la pausa supera la soglia (o e' la prima partita).
            SUM(CASE WHEN pausa_s IS NULL OR pausa_s > {soglia_s} THEN 1 ELSE 0 END) OVER w AS sessione,
            LAG(game_id) OVER w AS prec_game_id,
            LAG(punteggio) OVER w AS prec_punteggio,
            LAG(avv) OVER w AS prec_avv,
            LAG(elig) OVER w AS prec_elig,
            LAG(classe) OVER w AS prec_classe,
            LAG(speed) OVER w AS prec_speed,
            LAG(corta) OVER w AS prec_corta,
            LAG(persa_tempo) OVER w AS prec_persa_tempo,
            LAG(clk_fin_vinc) OVER w AS prec_clk_fin_vinc,
            LAG(clk_fin_perd) OVER w AS prec_clk_fin_perd
        FROM a1 WINDOW w AS (PARTITION BY gid {ordine})
    ),
    a3 AS (
        SELECT *,
            ROW_NUMBER() OVER ws AS pos,
            COUNT(*) OVER (PARTITION BY gid, sessione) AS n_sessione,
            -- Rating di riferimento: quello che il giocatore aveva PRIMA della sua
            -- prima partita di questa categoria di rating (2017) nella sessione.
            -- Non dipende dagli esiti della sessione, a differenza del rating corrente.
            FIRST_VALUE(elo IGNORE NULLS) OVER (PARTITION BY gid, sessione, speed {ordine}) AS rating_rif,
            -- La coppia (precedente, questa) e' utilizzabile dentro la sessione?
            COALESCE(elig AND prec_elig AND prec_classe = classe
                     AND LAG(sessione) OVER w = sessione AND pausa_s >= -10, FALSE) AS continua
        FROM a2 WINDOW w AS (PARTITION BY gid {ordine}), ws AS (PARTITION BY gid, sessione {ordine})
    ),
    a4 AS (
        SELECT *,
            -- Numero del blocco: aumenta a ogni partita utilizzabile che NON continua il blocco prima.
            CASE WHEN elig THEN SUM(CASE WHEN elig AND NOT continua THEN 1 ELSE 0 END) OVER w END AS blocco,
            -- Per le coppie a cavallo di due sessioni (controllo negativo): il rating
            -- di riferimento della sessione PRECEDENTE, non toccato dall'esito studiato.
            CASE WHEN pos = 1 AND prec_speed = speed THEN LAG(rating_rif) OVER w END AS rating_rif_x
        FROM a3 WINDOW w AS (PARTITION BY gid {ordine})
    ),
    a5 AS (
        SELECT *,
            CASE WHEN blocco IS NOT NULL THEN ROW_NUMBER() OVER wb END AS pos_blocco,
            CASE WHEN blocco IS NOT NULL THEN COUNT(*) OVER (PARTITION BY gid, blocco) END AS n_blocco,
            -- Esito e avversario di due e tre partite prima, nello stesso blocco.
            CASE WHEN blocco IS NOT NULL THEN LAG(punteggio, 2) OVER wb END AS prec2_punteggio,
            CASE WHEN blocco IS NOT NULL THEN LAG(avv, 2) OVER wb END AS prec2_avv,
            CASE WHEN blocco IS NOT NULL THEN LAG(punteggio, 3) OVER wb END AS prec3_punteggio,
            CASE WHEN blocco IS NOT NULL THEN LAG(avv, 3) OVER wb END AS prec3_avv,
            -- Serie di risultati uguali: "cambio" segna l'inizio di una nuova serie.
            CASE WHEN punteggio IS DISTINCT FROM LAG(punteggio) OVER wb THEN 1 ELSE 0 END AS cambio
        FROM a4 WINDOW wb AS (PARTITION BY gid, blocco {ordine})
    ),
    a6 AS (
        SELECT *, SUM(cambio) OVER (PARTITION BY gid, blocco {ordine}) AS isola FROM a5
    ),
    a7 AS (
        SELECT *,
            -- Serie in corso, questa partita compresa: +3 = terza vittoria di fila,
            -- -2 = seconda sconfitta di fila, 0 = patta.
            CASE WHEN blocco IS NULL THEN NULL
                 WHEN punteggio = 1.0 THEN ROW_NUMBER() OVER wi
                 WHEN punteggio = 0.0 THEN -ROW_NUMBER() OVER wi
                 ELSE 0 END AS serie
        FROM a6 WINDOW wi AS (PARTITION BY gid, blocco, isola {ordine})
    )
    SELECT gid, game_id, avv, bianco, lato_scelto,
           CASE WHEN h100 < {PERCENTO_ESPLORAZIONE} THEN 'esplorazione' ELSE 'conferma' END AS gruppo,
           start_utc, t_inizio, t_fine, durata_s, pausa_s,
           speed, classe, base_s, inc_s, is_tournament, berserk, termination, n_clk, has_eval,
           punteggio, elo, elo_avv, diff_rating, valida, elig, corta, persa_tempo, ritmo_10,
           clk_fin_vinc, clk_fin_perd,
           sessione::INTEGER AS sessione, pos::INTEGER AS pos, n_sessione::INTEGER AS n_sessione,
           rating_rif, rating_rif_x,
           blocco::INTEGER AS blocco, pos_blocco::INTEGER AS pos_blocco, n_blocco::INTEGER AS n_blocco,
           prec_game_id, prec_punteggio, prec_avv, prec_corta, prec_persa_tempo,
           prec_clk_fin_vinc, prec_clk_fin_perd,
           -- Coppia a cavallo di due sessioni: la precedente e' utilizzabile e della stessa classe.
           COALESCE(pos = 1 AND elig AND prec_elig AND prec_classe = classe, FALSE) AS coppia_x,
           prec2_punteggio, prec2_avv, prec3_punteggio, prec3_avv,
           CASE WHEN blocco IS NOT NULL THEN LAG(serie) OVER (PARTITION BY gid, blocco {ordine}) END AS serie_prec
    FROM a7
    """


def diagnostiche(con, sorgente, reg, soglia_min):
    """Controlli sulla STRUTTURA dei dati (nessun esito di partita viene confrontato)."""
    reg.tabella("Dimensioni", con.sql(f"""
        SELECT gruppo, COUNT(*) AS righe, COUNT(DISTINCT gid) AS giocatori,
               SUM(CASE WHEN pos = 1 THEN 1 ELSE 0 END) AS sessioni,
               ROUND(COUNT(*) / SUM(CASE WHEN pos = 1 THEN 1 ELSE 0 END), 2) AS partite_per_sessione,
               SUM(CASE WHEN pos_blocco > 1 THEN 1 ELSE 0 END) AS coppie_in_blocco,
               SUM(CASE WHEN coppia_x THEN 1 ELSE 0 END) AS coppie_tra_sessioni
        FROM {sorgente} GROUP BY ALL ORDER BY 1 DESC
    """).df())
    reg.tabella("Pause: quota negativa (attesa sotto l'1%)", con.sql(f"""
        SELECT COUNT(*) AS pause,
               ROUND(100.0 * AVG(CASE WHEN pausa_s < 0 THEN 1 ELSE 0 END), 2) AS perc_negative,
               ROUND(100.0 * AVG(CASE WHEN pausa_s < -10 THEN 1 ELSE 0 END), 2) AS perc_sotto_meno_10s,
               ROUND(MEDIAN(pausa_s), 1) AS mediana_s
        FROM {sorgente} WHERE pausa_s IS NOT NULL
    """).df())
    reg.tabella(f"Istogramma di log10(pausa in secondi); la soglia di {soglia_min} min e' a "
                f"{__import__('math').log10(soglia_min * 60):.2f}. Attese due gobbe con una valle vicino alla soglia",
                con.sql(f"""
        SELECT ROUND(FLOOR(LOG10(GREATEST(pausa_s, 1)) * 4) / 4, 2) AS log10_da, COUNT(*) AS n,
               REPEAT('#', (60.0 * COUNT(*) / MAX(COUNT(*)) OVER ())::INTEGER) AS barra
        FROM {sorgente} WHERE pausa_s >= 0 GROUP BY 1 ORDER BY 1
    """).df())
    reg.tabella("Categoria di rating 2017 (speed) per classe ricodificata", con.sql(f"""
        SELECT speed, classe, COUNT(*) AS righe, ROUND(MEDIAN(durata_s)) AS durata_mediana_s,
               ROUND(100.0 * AVG(is_tournament::INTEGER), 1) AS perc_torneo,
               ROUND(100.0 * AVG(CASE WHEN is_tournament THEN berserk::INTEGER END), 1) AS perc_berserk_nei_tornei
        FROM {sorgente} GROUP BY ALL ORDER BY 3 DESC
    """).df())
    reg.tabella("Blocchi per classe (solo struttura)", con.sql(f"""
        SELECT classe, COUNT(*) AS blocchi, ROUND(AVG(n_blocco), 2) AS lunghezza_media,
               MEDIAN(n_blocco) AS mediana, MAX(n_blocco) AS massimo,
               SUM(CASE WHEN n_blocco >= 2 THEN 1 ELSE 0 END) AS blocchi_da_2_in_su
        FROM {sorgente} WHERE pos_blocco = 1 GROUP BY 1 ORDER BY 2 DESC
    """).df())
    reg.tabella("Finali al fotofinish (senza incremento, persi per tempo): ultimo orologio del vincitore", con.sql(f"""
        SELECT classe,
               SUM(CASE WHEN clk_fin_vinc IS NOT NULL THEN 1 ELSE 0 END) AS persi_per_tempo,
               SUM(CASE WHEN clk_fin_vinc <= 3 THEN 1 ELSE 0 END) AS vincitore_entro_3s,
               SUM(CASE WHEN clk_fin_vinc <= 5 THEN 1 ELSE 0 END) AS vincitore_entro_5s
        FROM {sorgente} WHERE elig AND bianco GROUP BY 1 ORDER BY 2 DESC
    """).df())


def main():
    parser = argparse.ArgumentParser(description="Costruisce sessioni, partita successiva e blocchi")
    parser.add_argument("--soglia", type=int, default=30, help="pausa massima dentro una sessione, in minuti (default 30)")
    parser.add_argument("--percento", type=int, default=100, help="quota di giocatori da elaborare (per prove veloci)")
    parser.add_argument("--memoria", default="4GB", help="limite di memoria per DuckDB (default 4GB)")
    args = parser.parse_args()

    file_partite = (CARTELLA_DATI / "partite.parquet").as_posix()
    file_orologi = (CARTELLA_DATI / "orologi.parquet").as_posix()
    suffisso = "" if args.soglia == 30 else f"_s{args.soglia}"
    cartella_out = CARTELLA_DATI / f"giocatore_partita{suffisso}"
    if cartella_out.exists():
        shutil.rmtree(cartella_out)
    cartella_out.mkdir(parents=True)
    file_db = CARTELLA_DATI / "lavoro_05.duckdb"
    file_db.unlink(missing_ok=True)

    reg = Registro(f"05_diagnostiche{suffisso}")
    con = apri_duckdb(args.memoria, file_db)
    inizio = time.time()

    n = crea_giocatori(con, file_partite)
    reg.scrivi(f"Giocatori: {n:,}")
    con.execute(f"COPY giocatori TO '{(CARTELLA_DATI / 'giocatori.parquet').as_posix()}' (FORMAT parquet, COMPRESSION zstd)")

    crea_partite_estese(con, file_partite, file_orologi)
    n_partite, n_doppie = con.execute("SELECT COUNT(*), COUNT(*) - COUNT(DISTINCT game_id) FROM partite_x").fetchone()
    reg.scrivi(f"Partite: {n_partite:,} (game_id ripetuti: {n_doppie:,}, atteso 0) - {time.time() - inizio:.0f} s")

    for secchio in range(N_SECCHI):
        destinazione = (cartella_out / f"secchio_{secchio}.parquet").as_posix()
        con.execute(f"COPY ({sql_secchio(secchio, args.soglia * 60, args.percento)}) "
                    f"TO '{destinazione}' (FORMAT parquet, COMPRESSION zstd)")
        print(f"  secchio {secchio + 1}/{N_SECCHI} scritto - {time.time() - inizio:.0f} s")

    sorgente = f"read_parquet('{cartella_out.as_posix()}/*.parquet')"
    diagnostiche(con, sorgente, reg, args.soglia)
    reg.scrivi(f"\nFatto in {(time.time() - inizio) / 60:.1f} minuti -> {cartella_out}")
    reg.chiudi()
    con.close()
    file_db.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
