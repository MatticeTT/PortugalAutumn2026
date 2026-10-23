"""Plankgetallen opnieuw afstemmen op de 100 nagekeken situaties, alleen voor de gekozen planken.
Zelfde doel als toets.py: kwadratische fout tegenover de handscores plus een lichte band met de expertinschatting.
Grenzen: 0,4 tot 1,8 keer de inschatting, en waar regels.json een 'min' of 'max' vastlegt, die. alfa en de andere
planken blijven ongemoeid. Schrijft de nieuwe waarden in regels.json.
Gebruik: python3 afstemmen.py MID FI
"""
import json, os, sys
import numpy as np
from scipy.optimize import minimize

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)
import referentie as R  # noqa: E402

planken = sys.argv[1:]
rows = [r for r in json.load(open(os.path.join(HIER, "testset_100.json")))["situaties"]]
PARS = [(k, q) for k in planken for q in R.KEYS if "afgestemd" in str(R.REGELS["planken"][k][q].get("status", ""))]
prior = np.array([R.REGELS["planken"][k][q]["inschatting"] for k, q in PARS])
grenzen = []
for (k, q), p in zip(PARS, prior):
    v = R.REGELS["planken"][k][q]
    grenzen.append((max(0.4 * p, v.get("min", -np.inf)), min(1.8 * p, v.get("max", np.inf))))
alfa = R.REGELS["score"]["alfa"]["waarde"]
F = []
for r in rows:
    s = R.situatie(r); F.append(R.kenmerken(s, R.bereken(s)))


def zet(v):
    for (k, q), x in zip(PARS, v):
        R.REGELS["planken"][k][q]["waarde"] = float(x)


def doel(v):
    zet(v)
    P = {k: {q: R.X(k, q) for q in R.KEYS} for k in R.PL}
    sse = sum((R.score(F[i], P, alfa)[k][0] - rows[i]["hand"][k]) ** 2 for i in range(len(rows)) for k in planken)
    return sse + float(np.sum(((v - prior) / prior) ** 2))


start = np.clip(prior, [g[0] for g in grenzen], [g[1] for g in grenzen])
res = minimize(doel, start, method="Powell", bounds=grenzen, options=dict(maxfev=40000, xtol=1e-4, ftol=1e-5))
zet(res.x)
print(f"doel {doel(start):.2f} -> {res.fun:.2f} ({res.nfev} stappen)", file=sys.stderr)
regels = json.load(open(os.path.join(HIER, "regels.json")))
for (k, q), x in zip(PARS, res.x):
    regels["planken"][k][q]["waarde"] = float(x)
    print(f"{k}.{q}: {x:.3f}  (inschatting {regels['planken'][k][q]['inschatting']}, grenzen {grenzen[PARS.index((k, q))][0]:.2f}-{grenzen[PARS.index((k, q))][1]:.2f})")
json.dump(regels, open(os.path.join(HIER, "regels.json"), "w"), ensure_ascii=False, indent=1)
