# Controllo degli STIMANDI, seconda serie (revisione critica, 16 novembre 2026, notte).
# Scritto DOPO la conferma: non tocca nessun verdetto. Serve a dire che cosa B e la stima
# congiunta NON possono vedere. Stesse funzioni di tests/controllo_stimandi.py (solo numpy,
# nessun dato vero). Va committato dopo l'etichetta `codice-bloccato`, dichiarato come tale.
#
# Uso:  python controllo_stimandi_2.py [numero_di_blocchi] [seme]
#       (default 600000 blocchi, seme 2; circa 4 minuti e 1,5 GB di RAM per seme)
#
# Scenari:
#   (1) tilt che NON cala: ogni risultato inatteso sposta tutte le partite successive del blocco;
#   (2) tilt che cala piano: effetto beta * lam^(d-1) a distanza d;
#   (3) la stessa deriva della forma osservata a ritmi diversi (rho per partita alto = partite brevi);
#   (4) effetti simmetrici: dopo un risultato forte, in un verso o nell'altro, si fa peggio;
#   (5) tilt che non cala piu' tilt di una partita: che cosa resta visibile.
#
# Risultati, media su 5 semi (2, 11, 12, 13, 14) +- errore standard della media, in pp:
#   scenario                                      B             congiunta +1   +2            +3
#   nessuna dipendenza                            0,02 +- 0,04  -0,01 +- 0,06   0,00 +- 0,05   0,01 +- 0,04
#   tilt -1,00 solo a +1 (lam 0)                 -0,95 +- 0,03  -0,97 +- 0,02   0,03 +- 0,03   0,03 +- 0,04
#   tilt -1,00, lam 0,5  (vero -0,50; -0,25)     -0,81 +- 0,02  -1,01 +- 0,02  -0,44 +- 0,05  -0,17 +- 0,03
#   tilt -1,00, lam 0,8  (vero -0,80; -0,64)     -0,41 +- 0,06  -0,58 +- 0,07  -0,40 +- 0,01  -0,21 +- 0,06
#   tilt -1,00, lam 0,95 (vero -0,95; -0,90)     -0,16 +- 0,06  -0,23 +- 0,04  -0,14 +- 0,02  -0,13 +- 0,03
#   tilt -1,00 che non cala (lam 1)              -0,01 +- 0,02  -0,03 +- 0,04  -0,10 +- 0,05   0,04 +- 0,05
#   tilt -2,00 che non cala (lam 1)               0,04 +- 0,06   0,03 +- 0,08  -0,01 +- 0,03   0,06 +- 0,03
#   deriva AR(1), rho 0,98                       -0,17 +- 0,03  -0,23 +- 0,06  -0,24 +- 0,04  -0,02 +- 0,05
#   deriva AR(1), rho 0,95                       -0,35 +- 0,05  -0,53 +- 0,06  -0,42 +- 0,07  -0,35 +- 0,05
#   deriva AR(1), rho 0,9                        -0,60 +- 0,03  -0,88 +- 0,03  -0,64 +- 0,04  -0,48 +- 0,02
#   deriva AR(1), rho 0,8                        -0,90 +- 0,04  -1,28 +- 0,05  -0,85 +- 0,03  -0,52 +- 0,05
#   deriva AR(1), rho 0,6                        -1,03 +- 0,02  -1,35 +- 0,02  -0,65 +- 0,03  -0,30 +- 0,04
#   -1 pp dopo sconfitta E dopo vittoria          0,03 +- 0,03   0,06 +- 0,03  -0,04 +- 0,07   0,00 +- 0,05
#   non cala -1,00 + solo a +1 -1,00 (vero -2)   -1,03 +- 0,04  -1,05 +- 0,06  -0,03 +- 0,04  -0,06 +- 0,04
#
# Lettura: B e la congiunta misurano DIFFERENZE dentro il blocco (quanto pesa la partita
# precedente piu' delle altre). Un effetto che non cala e' invisibile a entrambi; uno che cala
# piano e' visto solo in parte; due effetti dello stesso segno dopo sconfitta e vittoria si
# annullano; la stessa deriva pesa di piu' per partita quando le partite sono lunghe.
import sys
import numpy as np

NB = int(sys.argv[1]) if len(sys.argv) > 1 else 600_000
SEME = int(sys.argv[2]) if len(sys.argv) > 2 else 2
rng = np.random.default_rng(SEME)
LMAX, SD = 40, 0.47
L = np.minimum(2 + rng.geometric(0.22, NB) - 1, LMAX)          # lunghezze dei blocchi (mediana 4, media ~5.5)
mask = np.arange(LMAX)[None, :] < L[:, None]


def B(y, nshuf=12):
    def tau(a):
        x, yy, m = a[:, :-1], a[:, 1:], mask[:, 1:]
        n = m.sum(1); ok = n >= 2
        sx, sy = (x*m).sum(1), (yy*m).sum(1)
        w = (x*x*m).sum(1) - sx*sx/np.maximum(n, 1); num = (x*yy*m).sum(1) - sx*sy/np.maximum(n, 1)
        return -num[ok].sum()/w[ok].sum()
    oss = tau(y); bs = []
    for _ in range(nshuf):
        k = np.where(mask, rng.random(y.shape), 2.0); o = np.argsort(k, 1)
        bs.append(tau(np.take_along_axis(y, o, 1)))
    b = np.mean(bs); return (oss - b)/(1 - b), b


def congiunta(y, lmin=5):
    A, m = np.zeros((3, 3)), np.zeros(3)
    cs = np.cumsum(np.where(mask, y, 0), 1)
    for t in range(4, LMAX):
        ok = (L > t) & (L >= lmin)
        if not ok.any(): break
        far = cs[ok, t-4]/(t-3); yt = y[ok, t]
        xs = [y[ok, t-d] for d in (1, 2, 3)]
        for d in range(3):
            z = xs[d] - far; m[d] += (yt*z).sum()
            for k in range(3): A[d, k] += (xs[k]*z).sum()
    return -np.linalg.solve(A, m)


def rep(nome, y):
    y = np.where(mask, y, 0.0)
    tb, b = B(y); c = congiunta(y)
    print(f"{nome:58s} B {100*tb:6.2f}   congiunta +1 {100*c[0]:6.2f}  +2 {100*c[1]:6.2f}  +3 {100*c[2]:6.2f}", flush=True)


def tilt(beta, lam):
    """y_t = e_t + S_t, con S_t = lam * S_{t-1} + beta * y_{t-1}: l'effetto del risultato
    di d partite prima vale beta * lam^(d-1). lam = 1: non cala mai; lam = 0: solo a +1."""
    e = rng.normal(0, SD, (NB, LMAX)); y = e.copy(); S = np.zeros(NB)
    for t in range(1, LMAX):
        S = lam*S + beta*y[:, t-1]
        y[:, t] += S
    return y


rep("nessuna dipendenza", rng.normal(0, SD, (NB, LMAX)))
print("-- (1)(2) tilt vero di -1,00 pp a +1; a distanza d vale -1,00 * lam^(d-1)")
for lam in (0.0, 0.5, 0.8, 0.95, 1.0):
    rep(f"tilt -1,00 a +1, lam = {lam} (vero +2 {-lam:.2f}, +3 {-lam*lam:.2f})", tilt(0.01, lam))
rep("tilt -2,00 a +1, lam = 1.0 (non cala mai)", tilt(0.02, 1.0))
print("-- (3) stessa deriva (sd 0,075), ritmi diversi: rho per partita")
for rho in (0.98, 0.95, 0.9, 0.8, 0.6):
    f = np.zeros((NB, LMAX)); f[:, 0] = rng.normal(0, 0.075, NB)
    for t in range(1, LMAX): f[:, t] = rho*f[:, t-1] + rng.normal(0, 0.075*np.sqrt(1-rho**2), NB)
    rep(f"deriva della forma AR(1), rho = {rho}", rng.normal(0, SD, (NB, LMAX)) + f)
print("-- (4) effetti simmetrici: -1 pp dopo un risultato forte, in entrambi i versi")
e = rng.normal(0, SD, (NB, LMAX)); y = e.copy()
for t in range(1, LMAX):
    y[:, t] -= 0.01 * (np.abs(y[:, t-1]) > 0.3)        # dopo una partita "decisa" (vinta o persa) -1 pp
rep("dopo sconfitta -1 pp e dopo vittoria -1 pp", y)
print("-- (5) tilt che non cala (-1 pp) piu' tilt a +1 (-1 pp): che cosa resta visibile")
e = rng.normal(0, SD, (NB, LMAX)); y = e.copy(); C = np.zeros(NB)
for t in range(1, LMAX):
    C = C + 0.01*y[:, t-1]
    y[:, t] += C + 0.01*y[:, t-1]
rep("permanente -1,00 + solo a +1 -1,00 (vero a +1: -2,00)", y)
