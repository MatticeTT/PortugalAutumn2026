"""Invoer per strand en per uur voor de score van de rekenchat (pipeline/rules/score.py, versie 2.1).

Zie docs/rekenchat/instructie_app.md, tabel "Invoer per strand en per uur". Geen eigen rekenregels:
- golfhoogte op het strand per golfsysteem zoals model.bereken het rekent: H x wortel(cos θ x vensterfactor) x
  stroomfactor (pipeline/rules/model.py);
- hoofdgolfsysteem = het systeem dat op het strand het hoogst breekt (score.breaking_height);
- aandeel_hoofdgolf = H_hoofd² / som H²; golf_aan_strand = wortel(som H²), alles op het strand;
- stroming_tov_wind: tegen of mee als de stroom binnen 45 graden van de windas loopt, anders dwars;
- onweer: weercode 95, 96 of 99 van het weermodel; donker en uur_tot_donker uit de zonnestand.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime

from pipeline.rules.model import hoek, stroomfactor, vensterfactor
from pipeline.rules.score import (
    CATEGORIES,
    GO,
    LEVEL,
    RAND,
    algemeen,
    breaking_height,
    cijfer,
    is_storm,
    score,
    stille_waters,
    te_veel,
)
from pipeline.rules.score import GOLF as GOLF_CATS
from pipeline.rules.score import WIND as WIND_CATS
from pipeline.site.zon_getij import daglicht, zon

ONWEER_CODES = {95, 96, 99}
NIVEAUS = (None, "beginner", "gemiddeld", "ervaren")


# Bewaarde invoer in de fiche (kort veld: sleutel in condities) en de afronding ervan.
BEWAAR = {"wh": "windhoek", "gh": "golfhoogte", "gt": "periode", "gk": "golfhoek", "ga": "aandeel_hoofdgolf",
          "gs": "golf_aan_strand", "ns": "neerslag", "ud": "uur_tot_donker"}
AFRONDING = {"windhoek": 0, "golfhoogte": 2, "periode": 1, "golfhoek": 0, "aandeel_hoofdgolf": 2,
             "golf_aan_strand": 2, "neerslag": 1, "uur_tot_donker": 1, "stroming": 1, "wind": 1, "vlaag": 1}
TOV = {"tegen": "t", "mee": "m", "dwars": "d"}


def afronden(c: dict) -> dict:
    """Zoals de fiche het bewaart: daarmee rekenen kaart en fiche exact hetzelfde."""
    uit = dict(c)
    for k, nd in AFRONDING.items():
        if uit.get(k) is not None:
            uit[k] = round(uit[k], nd)
            if nd == 0:
                uit[k] = int(uit[k])
    return uit


def golfsystemen(kust: float, vensters: list, deiningen: list, stroom_kn: float, stroom_naar: float) -> list[dict]:
    """Per golfsysteem de hoogte op het strand (m), periode en golfhoek (0-90)."""
    uit = []
    for h, t, r in deiningen:
        theta = hoek(r, kust)
        a = math.cos(math.radians(theta)) if theta < 90 else 0.0
        a *= vensterfactor(r, vensters)
        f = stroomfactor(t, r, stroom_kn, stroom_naar)
        uit.append({"h": h * math.sqrt(a) * f, "t": t, "hoek": min(theta, 90.0)})
    return uit


def tov_wind(stroom_naar: float, windrichting: float) -> str:
    """Stroom tegen de wind in (naar waar de wind vandaan komt) of mee (naar waar hij heen waait)."""
    if hoek(stroom_naar, windrichting) <= 45:
        return "tegen"
    if hoek(stroom_naar, windrichting + 180) <= 45:
        return "mee"
    return "dwars"


def uur_tot_donker(lat: float, lon: float, t_min: float) -> float | None:
    z = zon(lat, lon, datetime.fromtimestamp(t_min * 60, UTC))
    return None if z is None else max(0.0, (z[1] - t_min) / 60)


def condities(kust: float, vensters: list, lat: float, lon: float, t_min: float, wind: float, vlaag: float,
              windrichting: float, deiningen: list, stroom_kn: float | None, stroom_naar: float | None,
              neerslag: float | None, weercode: float | None) -> dict:
    sk, sn = stroom_kn or 0.0, stroom_naar or 0.0
    sys_ = golfsystemen(kust, vensters, deiningen, sk, sn)
    c = {"wind": wind, "vlaag": vlaag, "windhoek": hoek(windrichting, kust)}
    if sys_:
        hoofd = max(sys_, key=lambda s: breaking_height(s["h"], s["t"]))
        som = sum(s["h"] ** 2 for s in sys_)
        c.update(golfhoogte=hoofd["h"], periode=hoofd["t"], golfhoek=hoofd["hoek"],
                 aandeel_hoofdgolf=hoofd["h"] ** 2 / som if som > 0 else None, golf_aan_strand=math.sqrt(som))
    else:
        c.update(golfhoogte=0.0, periode=0.0, golfhoek=0.0, aandeel_hoofdgolf=None, golf_aan_strand=0.0)
    if stroom_kn is not None:
        c.update(stroming=stroom_kn, stroming_tov_wind=tov_wind(sn, windrichting))
    if neerslag is not None:
        c["neerslag"] = neerslag
    if weercode is not None and int(weercode) in ONWEER_CODES:
        c["onweer"] = True
    if not daglicht(lat, lon, t_min):
        c["donker"] = True
    else:
        c["uur_tot_donker"] = uur_tot_donker(lat, lon, t_min)
    return c


def groep(scores: dict, cats: list, c: dict, niveau: str | None) -> dict:
    """Zelfde als score.algemeen, maar met de 17 scores die al berekend zijn (sneller: één keer per uur)."""
    cats = [k for k in cats if niveau is None or k.endswith(niveau)]
    sc = {k: scores[k] for k in cats}
    beste = max(sc, key=sc.get)
    n = cijfer(sc[beste])
    rand = None
    if n >= 3:
        rand = RAND[min(LEVEL[k.rsplit("_", 1)[1]] for k, v in sc.items() if v >= GO)]
    return {"cijfer": n, "rand": rand, "beste": beste, "scores": sc, "te_veel": n < 3 and te_veel(cats, c)}


# Eén teken per groep (golf of wind) per uur voor de kaart:
# 0 1 2 = cijfer zonder meer; a b c = cijfer 0 1 2 en te veel (zwart); 3 4 met de rand: g o r (3) en G O R (4).
def teken(g: dict) -> str:
    if g["cijfer"] >= 3:
        k = "gor"[RAND.index(g["rand"])]
        return k if g["cijfer"] == 3 else k.upper()
    return "abc"[g["cijfer"]] if g["te_veel"] else str(g["cijfer"])


def stil_teken(st_cijfer: int, storm: bool) -> str:
    """Stille waters 0-4, en storm (achtergrond zwart) als S T U V W."""
    return "STUVW"[st_cijfer] if storm else str(st_cijfer)


def uur(c: dict) -> dict:
    """Alles voor één strand en één uur, voor alle niveaus (standaardgewicht)."""
    scores = {k: score(k, c)["score"] for k in CATEGORIES}
    st = stille_waters(c)
    uit = {"scores": scores, "stil": st["score"], "stil_cijfer": cijfer(st["score"]), "storm": is_storm(c)}
    for n in NIVEAUS:
        uit[n] = (groep(scores, GOLF_CATS, c, n), groep(scores, WIND_CATS, c, n))
    return uit


__all__ = ["condities", "uur", "teken", "stil_teken", "groep", "algemeen", "NIVEAUS"]
