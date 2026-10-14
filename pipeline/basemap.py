"""Basiskaart uit Natural Earth (publiek domein): land, meren, landsgrenzen en plaatsnamen.

Eén keer draaien; de uitvoer staat in web/public/basis/ en hoort bij de code. Vereenvoudigd en afgerond
zodat het geheel klein blijft (de site serveert het gecomprimeerd).

    python -m pipeline.basemap
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

from shapely.geometry import mapping, shape

SRC = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson"
OUT = Path("web/public/basis")


def load(name: str) -> dict:
    with urllib.request.urlopen(f"{SRC}/{name}.geojson", timeout=120) as r:
        return json.load(r)


def rounded(geom: dict, nd: int) -> dict:
    def rnd(c):
        if isinstance(c[0], (int, float)):
            return [round(c[0], nd), round(c[1], nd)]
        return [rnd(x) for x in c]

    return {"type": geom["type"], "coordinates": rnd(geom["coordinates"])}


def simplified(features: list[dict], tol: float, nd: int = 3, min_area: float = 0.0) -> list[dict]:
    out = []
    for f in features:
        g = shape(f["geometry"])
        if min_area and g.area < min_area:
            continue
        g = g.simplify(tol, preserve_topology=True)
        if g.is_empty:
            continue
        out.append({"type": "Feature", "properties": {}, "geometry": rounded(mapping(g), nd)})
    return out


def write(name: str, features: list[dict]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"{name}.geojson"
    p.write_text(json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":")))
    print(f"{p}: {len(features)} objecten, {p.stat().st_size // 1000} kB")


def main() -> int:
    write("land", simplified(load("ne_10m_land")["features"], 0.008))
    write("meren", simplified(load("ne_50m_lakes")["features"], 0.01, min_area=0.05))
    write("grenzen", simplified(load("ne_10m_admin_0_boundary_lines_land")["features"], 0.01))
    places = []
    for f in load("ne_10m_populated_places_simple")["features"]:
        p = f["properties"]
        if p["min_zoom"] > 6.1:
            continue
        places.append({"type": "Feature", "geometry": rounded(f["geometry"], 3),
                       "properties": {"naam": p["name"], "z": p["min_zoom"], "hoofdstad": int(p["adm0cap"] or 0)}})
    places.sort(key=lambda f: (f["properties"]["z"], -f["properties"]["hoofdstad"]))
    write("plaatsen", places)
    return 0


if __name__ == "__main__":
    sys.exit(main())
