"""Plankscore per spot per kwartier, met de regels uit de overdracht (score/regels.json, score/referentie.py).

Invoer: data/spotinvoer.json.gz (pipeline/spotinvoer.py) en spots/spots.json (strandrichting, spotkennis).
Per kwartier:
  golven  per systeem (deining 1, deining 2, windzee) hoogte, piekperiode en richting, lineair tussen de uren
          (richting als vector); de hoek t.o.v. de loodlijn op de kust, met het teken van de point (zie onder)
  wind    u, v en windstoot lineair tussen de stappen van ECMWF; rel = 0 offshore, 180 onshore
  getij   waterstand om de 10 minuten; stand = (water - laagwater) / (hoogwater - laagwater) tussen het vorige en het
          volgende uiterste; getijverschil van die cyclus
  donker  zon dieper dan 6 graden onder de horizon: veiligheid, score 1
Spotvelden (regels.json > vlaggen_uit_spotkennis):
  tanb             strandhelling: uit het diepteprofiel van EMODnet (Portugal) als dat binnen 1,5 km ligt, anders
                   leeg; leeg op een rif of point (dan telt de vorm uit de spotkennis)
  vorm             tekst uit de spotkennis, met 'point' erbij voor een point
  werkt_bij_tij    uit de spotkennis
  deining_venster  uit de spotkennis (beste deining) als die er is, anders de richtingen met open zee rond de
                   strandrichting (spots/kust.py)
  vlaggen          ondiep (spotkennis 'ondiep' en laag tij), terugslag (strekdam en hoog tij), pier
Hoek: richting waar de deining vandaan komt min de strandrichting, met de klok mee positief. Op een point telt de kant
van de punt als positief: voor een rechtse golf (vanaf het strand gezien begint hij rechts) blijft het teken, voor een
linkse keert het om.

Uitvoer: per spot de score per plank per kwartier en de tijdvakken met minstens 3 uur goed (kaartdrempel).
Gebruik: python -m pipeline.spotscore --invoer data/spotinvoer.json.gz --uit web/public/data/spots
"""

from __future__ import annotations

import argparse
import bisect
import datetime as dt
import gzip
import json
import math
from pathlib import Path

from score import referentie as R

KWARTIER = dt.timedelta(minutes=15)
MS_NAAR_KN = 1.943844
BODEM = Path(__file__).resolve().parent.parent / "spots" / "bodem" / "emodnet_pt.json"
HELLING_DIEPTE_M = 2.0  # helling van de waterlijn tot deze diepte (ongeveer waar golven van 1,5 m breken)
P = {k: {q: R.X(k, q) for q in R.KEYS} for k in R.PL}
ALFA = R.REGELS["score"]["alfa"]["waarde"]
DREMPEL = R.REGELS["score"]["kaart_drempel"]["waarde"]
MIN_UREN = R.REGELS["score"]["kaart_uren"]["waarde"]


def tijd(s: str) -> dt.datetime:
    return dt.datetime.strptime(s, "%Y-%m-%dT%H:%MZ").replace(tzinfo=dt.UTC)


def iso(t: dt.datetime) -> str:
    return t.strftime("%Y-%m-%dT%H:%MZ")


def hoekverschil(a: float, b: float) -> float:
    """a - b in graden, tussen -180 en 180."""
    return (a - b + 180) % 360 - 180


def zonhoogte(t: dt.datetime, lat: float, lon: float) -> float:
    """Hoogte van de zon in graden (NOAA-benadering, ruim nauwkeurig genoeg voor schemering)."""
    n = (t - dt.datetime(2000, 1, 1, 12, tzinfo=dt.UTC)).total_seconds() / 86400
    L = (280.460 + 0.9856474 * n) % 360
    g = math.radians((357.528 + 0.9856003 * n) % 360)
    lam = math.radians(L + 1.915 * math.sin(g) + 0.020 * math.sin(2 * g))
    eps = math.radians(23.439 - 0.0000004 * n)
    dec = math.asin(math.sin(eps) * math.sin(lam))
    ra = math.degrees(math.atan2(math.cos(eps) * math.sin(lam), math.cos(lam)))
    gmst = (280.46061837 + 360.98564736629 * n) % 360
    h = math.radians((gmst + lon - ra + 180) % 360 - 180)
    phi = math.radians(lat)
    return math.degrees(math.asin(math.sin(phi) * math.sin(dec) + math.cos(phi) * math.cos(dec) * math.cos(h)))


class Reeks:
    """Waarden op tijdstippen; lineair ertussen. None als een buur ontbreekt of t erbuiten valt."""

    def __init__(self, tijden: list[str], waarden: list):
        self.t = [tijd(x).timestamp() for x in tijden]
        self.w = waarden

    def op(self, t: dt.datetime):
        x = t.timestamp()
        k = bisect.bisect_right(self.t, x) - 1
        if k < 0 or k >= len(self.t):
            return None
        if self.t[k] == x:
            return self.w[k]
        if k + 1 >= len(self.t):
            return None
        a, b = self.w[k], self.w[k + 1]
        if a is None or b is None:
            return None
        f = (x - self.t[k]) / (self.t[k + 1] - self.t[k])
        if isinstance(a, (int, float)):
            return a + f * (b - a)
        return [None if (p is None or q is None) else p + f * (q - p) for p, q in zip(a, b)]


def golfsysteem(reeks: Reeks, t: dt.datetime):
    """[H, richting, Tp] met de richting als vector geïnterpoleerd."""
    x = t.timestamp()
    k = bisect.bisect_right(reeks.t, x) - 1
    if k < 0 or k >= len(reeks.t):
        return None
    if reeks.t[k] == x:
        return reeks.w[k]
    if k + 1 >= len(reeks.t) or reeks.w[k] is None or reeks.w[k + 1] is None:
        return None
    (h1, d1, t1), (h2, d2, t2) = reeks.w[k], reeks.w[k + 1]
    if None in (d1, d2, t1, t2):
        return None
    f = (x - reeks.t[k]) / (reeks.t[k + 1] - reeks.t[k])
    sx = (1 - f) * h1 * math.sin(math.radians(d1)) + f * h2 * math.sin(math.radians(d2))
    cy = (1 - f) * h1 * math.cos(math.radians(d1)) + f * h2 * math.cos(math.radians(d2))
    return [h1 + f * (h2 - h1), math.degrees(math.atan2(sx, cy)) % 360, t1 + f * (t2 - t1)]


class Getij:
    def __init__(self, g: dict):
        self.start = tijd(g["start"]).timestamp()
        self.stap = g["stap_min"] * 60
        self.h = g["h"]
        self.ext = [(tijd(t).timestamp(), s, v) for t, s, v in g["uitersten"]]
        self.ext_t = [e[0] for e in self.ext]

    def op(self, t: dt.datetime):
        """(waterstand, stand 0..1, getijverschil, bakje) of None buiten de reeks."""
        x = t.timestamp()
        y = (x - self.start) / self.stap
        k = int(math.floor(y))
        if k < 0 or k + 1 >= len(self.h):
            return None
        h = self.h[k] + (y - k) * (self.h[k + 1] - self.h[k])
        i = bisect.bisect_right(self.ext_t, x)
        if i == 0 or i >= len(self.ext):
            return None
        a, b = self.ext[i - 1], self.ext[i]
        laag, hoog = (a[2], b[2]) if a[1] == "laag" else (b[2], a[2])
        return h, R.getij_stand(h, laag, hoog), hoog - laag, R.getij_bakje(h, laag, hoog)


def helling_uit_profiel(profiel: list, stap: float = 25.0) -> float | None:
    """Van de waterlijn (diepte 0) tot HELLING_DIEPTE_M diep, in de kijkrichting."""
    x0 = None
    for k, d in enumerate(profiel):
        if d is None:
            continue
        if x0 is None and d >= 0:
            x0 = k * stap
        if x0 is not None and d >= HELLING_DIEPTE_M:
            afstand = max(k * stap - x0, stap)
            return round(min(0.2, max(0.005, HELLING_DIEPTE_M / afstand)), 4)
    return None


def bodem_index():
    if not BODEM.exists():
        return []
    return json.loads(BODEM.read_text())["stranden"]


def dichtste_profiel(stranden: list[dict], lat: float, lon: float, max_km: float = 1.5):
    beste, bd = None, max_km
    for s in stranden:
        d = math.hypot((s["lon"] - lon) * 111.32 * math.cos(math.radians(lat)), (s["lat"] - lat) * 110.57)
        if d < bd:
            beste, bd = s, d
    return beste, bd


def spotvelden(spot: dict, stranden: list[dict]) -> dict:
    """Vaste velden per spot voor de regels, met de herkomst van elk veld."""
    k = spot.get("kennis", {})
    soort = k.get("soort") or ("strand" if spot.get("labels", {}).get("natural") == "beach" else None)
    point = soort == "point"
    zand = soort in ("strand", "zandbank", "riviermonding") or (soort is None and not point)
    teken = -1 if (point and k.get("richting_golf") == "links") else 1
    f = spot["richting"]
    herkomst = {}
    tanb = None
    if zand:
        prof, d = dichtste_profiel(stranden, spot["lat"], spot["lon"])
        if prof:
            tanb = helling_uit_profiel(prof["profiel"])
            if tanb is not None:
                herkomst["tanb"] = f"EMODnet-diepteprofiel {prof['naam']} ({d:.1f} km)"
    if tanb is None:
        herkomst["tanb"] = "onbekend" if zand else "niet van toepassing (rif of point)"
    vorm = (k.get("vorm") or "").strip()
    if point and "point" not in vorm:
        vorm = (vorm + " point").strip()
    venster = None
    if k.get("deining_beste"):
        van, tot = k["deining_beste"]
        a, b = teken * hoekverschil(van, f), teken * hoekverschil(tot, f)
        venster = [min(a, b), max(a, b)]
        herkomst["deining_venster"] = "spotkennis (beste deining)"
    else:
        for van, tot in spot.get("venster", []):
            if van == 0 and tot == 360:
                break
            a, b = hoekverschil(van, f), hoekverschil(tot, f)
            if a <= 0 <= b or (a > b and (a <= 0 or 0 <= b)):  # het open stuk waar de strandrichting in ligt
                venster = [teken * a, teken * b] if teken == 1 else [teken * b, teken * a]
                herkomst["deining_venster"] = "open zee uit de kustlijn (GSHHG)"
                break
    return {"f": f, "teken": teken, "point": point, "open": soort in ("strand", "zandbank") or soort is None and not point,
            "spot": {"tanb": tanb, "vorm": vorm, "werkt_bij_tij": k.get("werkt_bij_tij"), "deining_venster": venster},
            "vlaggen_kennis": set(k.get("vlaggen") or []), "herkomst": herkomst, "soort": soort}


def situatie(v: dict, systemen: dict, wind: tuple, getij, donker: bool) -> dict:
    f, teken = v["f"], v["teken"]
    sys_ = []
    for naam, w in systemen.items():
        if w is None or w[0] is None or w[0] <= 0.01 or w[1] is None or w[2] is None:
            continue
        sys_.append((naam, w[0], w[2], teken * hoekverschil(w[1], f)))
    flags = []
    bakje = getij[3] if getij else None
    if "ondiep" in v["vlaggen_kennis"] and bakje == "laag":
        flags.append("ondiep")
    if "strekdam" in v["vlaggen_kennis"] and bakje == "hoog":
        flags.append("terugslag")
    if "pier" in v["vlaggen_kennis"]:
        flags.append("pier")
    if donker:
        flags.append("donker")
    return dict(spot=v["spot"], sys=sys_, wind=wind, stroom=0.0, langs_factor=1.0, flags=flags, open=v["open"],
                groep="Point break" if v["point"] else "", getij=bakje,
                getij_stand=getij[1] if getij else None, getij_bereik_m=getij[2] if getij else None)


def tijdvakken(tijden: list[dt.datetime], scores: list[float | None]) -> list[list[str]]:
    """Aaneengesloten stukken met score >= kaartdrempel van minstens MIN_UREN uur, als [van, tot]."""
    uit, start = [], None
    for k, s in enumerate(scores + [None]):
        goed = s is not None and s >= DREMPEL
        if goed and start is None:
            start = k
        if not goed and start is not None:
            if (k - start) * 0.25 >= MIN_UREN:
                uit.append([iso(tijden[start]), iso(tijden[k - 1] + KWARTIER)])
            start = None
    return uit


def reken_spot(spot: dict, invoer: dict, stranden: list[dict], van: dt.datetime, tot: dt.datetime) -> dict | None:
    if not invoer.get("golven") or not invoer.get("wind"):
        return None
    v = spotvelden(spot, stranden)
    gw = invoer["golven"]
    sysr = {k: Reeks(gw["tijden"], gw[k]) for k in ("deining1", "deining2", "windzee")}
    wi = invoer["wind"]
    u, w_, st = Reeks(wi["tijden"], wi["u"]), Reeks(wi["tijden"], wi["v"]), Reeks(wi["tijden"], wi["stoot"])
    gt = Getij(invoer["getij"]) if invoer.get("getij") else None
    tijden, per_plank, grenzen, rijen = [], {p: [] for p in R.PL}, {p: [] for p in R.PL}, []
    t = van
    while t <= tot:
        systemen = {k: golfsysteem(r, t) for k, r in sysr.items()}
        uu, vv = u.op(t), w_.op(t)
        if uu is None or vv is None or all(x is None for x in systemen.values()):
            t += KWARTIER
            continue
        kn = math.hypot(uu, vv) * MS_NAAR_KN
        vandaan = math.degrees(math.atan2(-uu, -vv)) % 360
        rel = abs(hoekverschil(vandaan, (v["f"] + 180) % 360))
        stoot = st.op(t)
        stoot = kn if stoot is None else max(kn, stoot * MS_NAAR_KN)
        g = gt.op(t) if gt else None
        donker = zonhoogte(t, spot["lat"], spot["lon"]) < -6
        s = situatie(v, systemen, (kn, rel, stoot), g, donker)
        fk = R.kenmerken(s, R.bereken(s))
        uit = R.score(fk, P, ALFA)
        tijden.append(t)
        for p in R.PL:
            per_plank[p].append(uit[p][0])
            grenzen[p].append(uit[p][2])
        rijen.append({"t": iso(t), "wind_kn": round(kn, 1), "wind_rel": round(rel), "stoot_kn": round(stoot, 1),
                      "golven": {k: (None if x is None else [round(x[0], 2), round(x[1]), round(x[2], 1)]) for k, x in systemen.items()},
                      "Hb": round(fk["Hb"], 2), "getij": None if g is None else {"h": round(g[0], 2), "stand": round(g[1], 2), "bakje": g[3]},
                      "expert": R.expert_label(fk)})
        t += KWARTIER
    if not tijden:
        return None
    vakken = {p: tijdvakken(tijden, per_plank[p]) for p in R.PL}
    return {"naam": spot["naam"], "lat": spot["lat"], "lon": spot["lon"], "richting": v["f"], "soort": v["soort"],
            "velden": {**v["spot"], "open": v["open"]}, "herkomst": v["herkomst"],
            "golfbron": invoer["golven"]["bron"], "golfcel": invoer["golven"]["cel"],
            "start": iso(tijden[0]), "scores": per_plank, "grenzen": grenzen, "tijdvakken": vakken, "uur": rijen[::4]}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--invoer", type=Path, default=Path("data/spotinvoer.json.gz"))
    p.add_argument("--spots", type=Path, default=Path("spots/spots.json"))
    p.add_argument("--uit", type=Path, default=Path("web/public/data/spots"))
    a = p.parse_args(argv)
    with gzip.open(a.invoer, "rt") as f:
        inv = json.load(f)
    spots = {(s["naam"], s["lat"], s["lon"]): s for s in json.loads(a.spots.read_text())["spots"]}
    stranden = bodem_index()
    van = tijd(inv["run"])
    tot = van + dt.timedelta(days=10)
    a.uit.mkdir(parents=True, exist_ok=True)
    lijst = []
    for n, i in enumerate(inv["spots"]):
        s = spots.get((i["naam"], i["lat"], i["lon"]))
        if s is None:
            continue
        r = reken_spot(s, i, stranden, van, tot)
        if r is None:
            continue
        (a.uit / f"{n}.json").write_text(json.dumps(r, ensure_ascii=False, separators=(",", ":")))
        best = {pl: max(r["scores"][pl]) for pl in R.PL}
        lijst.append({"id": n, "naam": r["naam"], "lat": r["lat"], "lon": r["lon"], "tijdvakken": r["tijdvakken"],
                      "max": best})
    (a.uit / "index.json").write_text(json.dumps({"run": inv["run"], "drempel": DREMPEL, "min_uren": MIN_UREN,
                                                  "spots": lijst}, ensure_ascii=False, separators=(",", ":")))
    print(f"{len(lijst)} spots gescoord", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
