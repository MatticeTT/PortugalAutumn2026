"""Eerlijke toets: 5 keer afstemmen op 80 nagekeken situaties, toetsen op de 20 die de regel niet zag.
Start en anker = de expertinschatting (niet de waarden die al op alle 100 afgestemd zijn: dat zou lekken).
Gebruik: python3 toets.py . testset_100.json   (duurt enkele minuten)
"""
import json, sys, math, random, importlib.util
import numpy as np
from scipy.optimize import minimize

d, ts = sys.argv[1], sys.argv[2]
spec = importlib.util.spec_from_file_location("ref", d + "/referentie.py")
R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)
rows = json.load(open(ts))["situaties"]
PL = R.PL
PARS = [(k, q) for k in PL for q in R.KEYS if "afgestemd" in str(R.REGELS["planken"][k][q].get("status", ""))]
prior = np.array([R.REGELS["planken"][k][q]["inschatting"] for k, q in PARS] + [1.0])
F = []
for r in rows:
    s = R.situatie(r); F.append(R.kenmerken(s, R.bereken(s)))
LAMBDA = 1.0


def zet(v):
    for (k, q), x in zip(PARS, v[:-1]):
        R.REGELS["planken"][k][q]["waarde"] = float(x)


def scores(v, idx):
    zet(v)
    P = {k: {q: R.X(k, q) for q in R.KEYS} for k in PL}
    return [R.score(F[i], P, float(v[-1])) for i in idx]


def doel(v, idx):
    u = scores(v, idx)
    sse = sum((u[j][k][0] - rows[i]["hand"][k]) ** 2 for j, i in enumerate(idx) for k in PL)
    return sse + LAMBDA * float(np.sum(((v - prior) / prior) ** 2))


nrs = [i for i, r in enumerate(rows)]
rng = random.Random(2026); rng.shuffle(nrs)
folds = [nrs[f::5] for f in range(5)]
# 0,4 tot 1,8 keer de inschatting; waar regels.json een 'min' of 'max' vastlegt (bv. review 6), die.
VAST = [R.REGELS["planken"][k][q] for k, q in PARS]
bounds = [(max(0.4 * p, v.get("min", -math.inf)), min(1.8 * p, v.get("max", math.inf))) for p, v in zip(prior[:-1], VAST)] + [(0.6, 1.4)]
prior_start = np.clip(prior, [b[0] for b in bounds], [b[1] for b in bounds])
voorspeld = {}
for f, test in enumerate(folds):
    train = [i for i in nrs if i not in test]
    res = minimize(doel, prior_start.copy(), args=(train,), method="Powell", bounds=bounds, options=dict(maxfev=40000, xtol=1e-3, ftol=1e-4))
    u = scores(res.x, test)
    for j, i in enumerate(test): voorspeld[i] = {k: u[j][k][0] for k in PL}
    print(f"vouw {f+1}: doel {res.fun:.1f} start {doel(prior, train):.1f} nfev {res.nfev}", file=sys.stderr)

uit = {}
for thr in (3.5, 3.7, 3.8, 4.0):
    tp = fp = fn = 0; ae = []
    for i, r in enumerate(rows):
        if r["nr"] == 85: continue
        for k in PL:
            h = r["hand"][k]; g = voorspeld[i][k]; ae.append(abs(h - g))
            H = math.floor(h + 0.5) >= 4; G = g >= thr
            tp += H and G; fp += G and not H; fn += H and not G
    uit[thr] = dict(mae=round(sum(ae) / len(ae), 3), prec=round(tp / (tp + fp), 3), rec=round(tp / (tp + fn), 3), tp=tp, fp=fp, fn=fn,
                    zwaar_fout=sum(1 for i, r in enumerate(rows) if r["nr"] != 85 for k in PL if voorspeld[i][k] >= thr and r["hand"][k] < 3))
print(json.dumps(uit))
