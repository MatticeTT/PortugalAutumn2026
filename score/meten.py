"""Metingen voor een regelwijziging: afwijking op de 100 (getallen zoals in regels.json, nr 85 telt niet mee),
cijfers bij een drempel, en hoe vaak elke plank de beste is in de 1000 per regio.
Gebruik: python3 meten.py <map met regels.json en referentie.py> [drempel]
"""
import importlib.util, json, math, sys
from collections import Counter

d = sys.argv[1]
drempel = float(sys.argv[2]) if len(sys.argv) > 2 else 3.8
spec = importlib.util.spec_from_file_location("ref", d + "/referentie.py")
R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)
P = {k: {q: R.X(k, q) for q in R.KEYS} for k in R.PL}
alfa = R.REGELS["score"]["alfa"]["waarde"]
HIER = __file__.rsplit("/", 1)[0]


def reken(r):
    s = R.situatie(r)
    return R.score(R.kenmerken(s, R.bereken(s)), P, alfa)


honderd = json.load(open(HIER + "/testset_100.json"))["situaties"]
ae, per = [], {k: [] for k in R.PL}
tp = fp = fn = zwaar = 0
for r in honderd:
    if r["nr"] == 85:
        continue
    u = reken(r)
    for k in R.PL:
        h, g = r["hand"][k], u[k][0]
        ae.append(abs(h - g)); per[k].append(abs(h - g))
        H, G = math.floor(h + 0.5) >= 4, g >= drempel
        tp += H and G; fp += G and not H; fn += H and not G; zwaar += G and h < 3
uit = {"afwijking_100": round(sum(ae) / len(ae), 4), "per_plank": {k: round(sum(v) / len(v), 3) for k, v in per.items()},
       f"drempel_{drempel}": dict(JA_klopt=round(tp / (tp + fp), 3), echte_JA_gevonden=round(tp / (tp + fn), 3), tp=tp, fp=fp, fn=fn, zwaar_fout=zwaar)}
REGIO = {"België + Nederland": ("België", "Nederland"), "Portugal + Zuidwest-Frankrijk": ("Portugal", "Zuidwest-Frankrijk")}
duizend = json.load(open(HIER + "/testset_1000.json"))["situaties"]
for naam, kusten in REGIO.items():
    c = Counter()
    for r in duizend:
        if r["ruw"].get("getij_kust") in kusten:
            u = reken(r)
            c[max(R.PL, key=lambda k: u[k][0])] += 1
    uit["beste_plank " + naam] = {k: c.get(k, 0) for k in R.PL}
print(json.dumps(uit, ensure_ascii=False, indent=1))
