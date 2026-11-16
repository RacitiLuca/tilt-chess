# Controllo degli STIMANDI (non del codice di 08): che cosa vedono B e la stima congiunta
# quando la dipendenza tra partite e' (1) un tilt solo a +1, (2) una deriva lenta della forma,
# (3) una tendenza individuale nel blocco, (4) una prima partita "a freddo" diversa da giocatore a giocatore.
import numpy as np
rng = np.random.default_rng(1)
NB, LMAX, SD = 600_000, 40, 0.47
L = np.minimum(2 + rng.geometric(0.22, NB) - 1, LMAX)          # lunghezze dei blocchi (mediana 4, media ~5.5)
mask = np.arange(LMAX)[None, :] < L[:, None]

def B(y, nshuf=12):
    def tau(a):
        x, yy, m = a[:, :-1], a[:, 1:], mask[:, 1:]
        n = m.sum(1); ok = n >= 2
        sx, sy = (x*m).sum(1), (yy*m).sum(1)
        w = (x*x*m).sum(1) - sx*sx/np.maximum(n,1); num = (x*yy*m).sum(1) - sx*sy/np.maximum(n,1)
        return -num[ok].sum()/w[ok].sum()
    oss = tau(y); bs = []
    for _ in range(nshuf):
        k = np.where(mask, rng.random(y.shape), 2.0); o = np.argsort(k, 1)
        bs.append(tau(np.take_along_axis(y, o, 1)))
    b = np.mean(bs); return (oss - b)/(1 - b), b

def congiunta(y, lmin=5):
    A, m = np.zeros((3,3)), np.zeros(3)
    cs = np.cumsum(np.where(mask, y, 0), 1)
    for t in range(4, LMAX):
        ok = (L > t) & (L >= lmin)
        if not ok.any(): break
        far = cs[ok, t-4]/(t-3); yt = y[ok, t]
        xs = [y[ok, t-d] for d in (1,2,3)]
        for d in range(3):
            z = xs[d] - far; m[d] += (yt*z).sum()
            for k in range(3): A[d,k] += (xs[k]*z).sum()
    return -np.linalg.solve(A, m)

def B_lunghi(y):   # B solo sui blocchi da 5 in su
    global mask, L
    keep = L >= 5; m0, L0 = mask, L
    mask, L = mask[keep], L[keep]; r = B(y[keep]); mask, L = m0, L0; return r

def rep(nome, y):
    y = np.where(mask, y, 0.0)
    tb, b = B(y); tl, _ = B_lunghi(y); c = congiunta(y)
    print(f"{nome:44s} B {100*tb:6.2f} (b {100*b:5.1f})  B blocchi>=5 {100*tl:6.2f}  congiunta +1 {100*c[0]:6.2f}  +2 {100*c[1]:6.2f}  +3 {100*c[2]:6.2f}")

e = rng.normal(0, SD, (NB, LMAX))
rep("nessuna dipendenza", e)
y = e.copy()
for t in range(1, LMAX): y[:, t] += 0.0094*y[:, t-1]
rep("tilt solo a +1 (-0,94 pp)", y)
for rho, sf in ((0.9, 0.075), (0.8, 0.075), (0.6, 0.085)):
    f = np.zeros((NB, LMAX)); f[:, 0] = rng.normal(0, sf, NB)
    for t in range(1, LMAX): f[:, t] = rho*f[:, t-1] + rng.normal(0, sf*np.sqrt(1-rho**2), NB)
    rep(f"deriva della forma AR(1) rho={rho}, sd={sf}", e + f)
a = rng.normal(0, 0.012, NB)[:, None]
rep("tendenza individuale (sd 1,2 pp a partita)", e + a*(np.arange(LMAX)[None,:] - (L[:,None]-1)/2))
d = np.zeros((NB, LMAX)); d[:, 0] = rng.normal(0, 0.10, NB)
rep("prima partita 'a freddo' (sd 10 pp)", e + d)
