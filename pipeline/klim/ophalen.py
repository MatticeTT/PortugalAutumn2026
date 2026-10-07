"""Klimplekken in Portugal uit OpenStreetMap (eigenaar, 7 oktober 2026).

Regels:
- alle objecten in Portugal met sport=climbing;
- boulderen als climbing=boulder of climbing:boulder=yes, al de rest is muurklimmen;
- geen klimhallen binnen (leisure=sports_centre);
- per plek: naam, rotssoort (climbing:rock), wandrichting (climbing:orientation) en de graden
  (climbing:grade:french:min/max, climbing:grade:font:min/max).

Draait in GitHub Actions (klim.yml): Overpass is vanuit de ontwikkelomgeving niet bereikbaar.
Schrijft data/klim/plekken.json en drukt een telling af.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "klim" / "plekken.json"
OVERPASS = "https://overpass-api.de/api/interpreter"
UA = "surfkaart-portugal/0.1 (niet-commercieel, besloten)"
QUERY = """[out:json][timeout:180];
area["ISO3166-1"="PT"][admin_level=2]->.pt;
nwr["sport"="climbing"](area.pt);
out tags center;"""
GRADEN = ["climbing:grade:french:min", "climbing:grade:french:max",
          "climbing:grade:font:min", "climbing:grade:font:max"]


def soort(tags: dict) -> str:
    return "boulderen" if tags.get("climbing") == "boulder" or tags.get("climbing:boulder") == "yes" else "muurklimmen"


def plekken(elementen: list[dict]) -> list[dict]:
    uit = []
    for e in elementen:
        t = e.get("tags", {})
        if t.get("leisure") == "sports_centre":
            continue
        lon, lat = (e["lon"], e["lat"]) if "lon" in e else (e["center"]["lon"], e["center"]["lat"])
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
        graad = "french" if s == "muurklimmen" else "font"
        n_graad = sum(1 for q in x if q[graad + ":min"] or q[graad + ":max"])
        n_rots = sum(1 for q in x if q["rots"])
        n_richting = sum(1 for q in x if q["richting"])
        regels.append(f"{s}: {len(x)} plekken; met {graad}-graad {n_graad}, met rotssoort {n_rots}, "
                      f"met wandrichting {n_richting}")
    return "\n".join(regels)


def main():
    req = urllib.request.Request(OVERPASS, data=urllib.parse.urlencode({"data": QUERY}).encode(),
                                 headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=300) as r:
        elementen = json.loads(r.read())["elements"]
    p = plekken(elementen)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"bron": "OpenStreetMap (ODbL), sport=climbing", "aantal_osm": len(elementen),
                               "plekken": p}, ensure_ascii=False, indent=0) + "\n")
    print(f"{len(elementen)} objecten met sport=climbing, {len(p)} zonder klimhallen")
    print(telling(p))


if __name__ == "__main__":
    main()
