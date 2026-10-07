"""Klimplekken in Portugal uit OpenStreetMap (eigenaar en rekenchat, 7 oktober 2026).

Regels:
- objecten in Portugal met sport=climbing, geen klimhallen binnen (leisure=sports_centre);
- alleen climbing=crag en climbing=area, plus boulders (climbing=boulder of climbing:boulder=yes);
  geen losse routes of haken (route, route_bottom, route_top, bolt) als eigen plek;
- boulderen als climbing=boulder of climbing:boulder=yes, al de rest is muurklimmen;
- ligt een crag binnen een area, dan alleen de crag (de area valt weg);
- per plek: naam, rotssoort (climbing:rock), wandrichting (climbing:orientation) en de graden.

Draait in GitHub Actions (klim.yml): Overpass is vanuit de ontwikkelomgeving niet bereikbaar.
Schrijft data/klim/plekken.json en drukt een telling af.
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "klim" / "plekken.json"
# Overpass is soms overbelast (504): dan opnieuw, ook via spiegelservers.
OVERPASS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter",
            "https://overpass.private.coffee/api/interpreter"]
UA = "surfkaart-portugal/0.1 (niet-commercieel, besloten)"
QUERY = """[out:json][timeout:180];
area["ISO3166-1"="PT"][admin_level=2]->.pt;
nwr["sport"="climbing"](area.pt);
out tags center geom;"""
GRADEN = ["climbing:grade:french:min", "climbing:grade:french:max",
          "climbing:grade:font:min", "climbing:grade:font:max"]


def soort(tags: dict) -> str:
    return "boulderen" if tags.get("climbing") == "boulder" or tags.get("climbing:boulder") == "yes" else "muurklimmen"


def getoond(tags: dict) -> bool:
    """Alleen crags, areas en boulders; geen klimhallen, losse routes of haken."""
    if tags.get("leisure") == "sports_centre":
        return False
    return soort(tags) == "boulderen" or tags.get("climbing") in ("crag", "area")


def ringen(e: dict) -> list[list[tuple[float, float]]]:
    """De omtrek van een way of relation als ringen (lon, lat); een node heeft er geen."""
    if e["type"] == "way" and e.get("geometry"):
        return [[(g["lon"], g["lat"]) for g in e["geometry"]]]
    if e["type"] == "relation":
        uit, los = [], []
        for m in e.get("members", []):
            if m.get("role") in ("outer", "") and m.get("geometry"):
                r = [(g["lon"], g["lat"]) for g in m["geometry"]]
                (uit if r[0] == r[-1] else los).append(r)
        if los:  # stukken van de buitenrand: achter elkaar als één ring (benadering)
            uit.append([pt for r in los for pt in r])
        return uit
    return []


def binnen(lon: float, lat: float, ring: list[tuple[float, float]]) -> bool:
    """Punt in veelhoek (straalmethode)."""
    ok = False
    for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1], strict=True):
        if (y0 > lat) != (y1 > lat) and lon < x0 + (lat - y0) * (x1 - x0) / (y1 - y0):
            ok = not ok
    return ok


def midden(e: dict) -> tuple[float, float]:
    """Ligging: de node zelf, anders het midden (Overpass geeft met "geom" soms geen center, wel bounds)."""
    if "lon" in e:
        return e["lon"], e["lat"]
    if "center" in e:
        return e["center"]["lon"], e["center"]["lat"]
    b = e["bounds"]
    return (b["minlon"] + b["maxlon"]) / 2, (b["minlat"] + b["maxlat"]) / 2


def plekken(elementen: list[dict]) -> list[dict]:
    kandidaten = [e for e in elementen if getoond(e.get("tags", {}))]
    crags = [midden(e) for e in kandidaten if e["tags"].get("climbing") == "crag"]
    uit = []
    for e in kandidaten:
        t = e["tags"]
        if t.get("climbing") == "area" and any(binnen(x, y, r) for r in ringen(e) for x, y in crags):
            continue  # er ligt een crag in deze area: alleen de crag tonen
        lon, lat = midden(e)
        uit.append({
            "id": f"{e['type']}/{e['id']}", "naam": t.get("name"), "soort": soort(t),
            "lon": round(lon, 5), "lat": round(lat, 5),
            "rots": t.get("climbing:rock"), "richting": t.get("climbing:orientation"),
            **{g.removeprefix("climbing:grade:"): t.get(g) for g in GRADEN},
            "climbing": t.get("climbing"),
        })
    return uit


def telling(p: list[dict]) -> str:
    regels = []
    for s in ("muurklimmen", "boulderen"):
        x = [q for q in p if q["soort"] == s]
        graad = "french"
        n_graad = sum(1 for q in x if q[graad + ":min"] or q[graad + ":max"])
        n_rots = sum(1 for q in x if q["rots"])
        n_richting = sum(1 for q in x if q["richting"])
        regels.append(f"{s}: {len(x)} plekken; met {graad}-graad {n_graad}, met rotssoort {n_rots}, "
                      f"met wandrichting {n_richting}")
    return "\n".join(regels)


def vraag() -> list[dict]:
    fout = None
    for poging in range(6):
        url = OVERPASS[poging % len(OVERPASS)]
        try:
            req = urllib.request.Request(url, data=urllib.parse.urlencode({"data": QUERY}).encode(),
                                         headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.loads(r.read())["elements"]
        except Exception as e:  # noqa: BLE001
            fout = e
            print(f"{url}: {e}; opnieuw", flush=True)
            time.sleep(20 * (poging + 1))
    raise RuntimeError(f"Overpass niet bereikbaar: {fout}")


def main():
    elementen = vraag()
    p = plekken(elementen)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"bron": "OpenStreetMap (ODbL), sport=climbing", "aantal_osm": len(elementen),
                               "plekken": p}, ensure_ascii=False, indent=0) + "\n")
    print(f"{len(elementen)} objecten met sport=climbing, {len(p)} getoond (crags, areas zonder crag, boulders)")
    print(telling(p))


if __name__ == "__main__":
    main()
