"""Kustlijn van Portugal uit OpenStreetMap (tot op de meter), zodat land, stranden en wegen op elkaar passen.

Invoer: de kustlijnen (natural=coastline) uit het uittreksel van Geofabrik, als GeoJSON-lijnen (osmium export), en de
GSHHG-kust (basis/land-fijn.geojson, ongeveer 100 m). Binnen OSMBOX worden de kustlijnen samen met de rand van het
vak tot vlakken gemaakt; een vlak is land als het grotendeels op het GSHHG-land ligt. Buiten OSMBOX (de stukjes Spanje
in het kader) blijft de GSHHG-kust.

Uit: basis/land-osm.geojson, voor de kaart vanaf zoom 9. © OpenStreetMap-bijdragers (ODbL).
Gebruik: python -m pipeline.kust_osm --kust kust.geojson --gshhg web/public/basis/land-fijn.geojson --uit web/public/basis
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import shapely
from shapely.geometry import box, mapping, shape
from shapely.ops import polygonize, unary_union

# Portugal vasteland: het vak snijdt de kust net ten zuiden van de Minho en net ten westen van de Guadiana (de grenzen),
# zodat elke kustlijn die het vak in komt er ook weer uit gaat.
OSMBOX = (-9.65, 36.9, -7.42, 41.865)
VEREENVOUDIG = 0.00002  # graden, ongeveer 2 m
DECIMALEN = 6


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--kust", type=Path, required=True)
    p.add_argument("--gshhg", type=Path, required=True)
    p.add_argument("--uit", type=Path, default=Path("web/public/basis"))
    a = p.parse_args(argv)
    vak = box(*OSMBOX)
    lijnen = []
    for f in json.loads(a.kust.read_text())["features"]:
        g = f.get("geometry")
        if g and g["type"] in ("LineString", "MultiLineString"):
            s = shape(g).intersection(vak)
            if not s.is_empty:
                lijnen.append(s)
    gshhg = shapely.union_all([shape(f["geometry"]).buffer(0) for f in json.loads(a.gshhg.read_text())["features"]])
    net = unary_union(lijnen + [vak.boundary])
    land, zee = [], 0
    for stuk in polygonize(net):
        if stuk.area <= 0:
            continue
        deel = stuk.intersection(gshhg).area / stuk.area
        # Kleine stukjes (rotsen, eilandjes) zijn land als ze dicht bij de GSHHG-kust liggen; OSM is daar beter.
        if deel > 0.5 or (stuk.area < 1e-6 and deel > 0.05):
            land.append(stuk)
        else:
            zee += 1
    osm = unary_union(land)
    print(f"{len(lijnen)} kustlijnen, {len(land)} landvlakken, {zee} zeevlakken; land {osm.area:.4f} vs GSHHG {gshhg.intersection(vak).area:.4f}",
          flush=True)
    # Controle: het OSM-land mag niet veel van het GSHHG-land verschillen (anders klopt de indeling niet).
    verschil = osm.symmetric_difference(gshhg.intersection(vak)).area / gshhg.intersection(vak).area
    print(f"verschil met GSHHG: {verschil:.2%}", flush=True)
    if verschil > 0.02:
        raise SystemExit("OSM-land wijkt te veel af van GSHHG: niet bewaard")
    geheel = unary_union([gshhg.difference(vak), osm]).simplify(VEREENVOUDIG, preserve_topology=True)
    tekst = json.dumps({"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {}, "geometry": mapping(g)}
                                                                  for g in getattr(geheel, "geoms", [geheel])]}, separators=(",", ":"))
    tekst = json.dumps(json.loads(tekst, parse_float=lambda x: round(float(x), DECIMALEN)), separators=(",", ":"))
    (a.uit / "land-osm.geojson").write_text(tekst)
    print(f"land-osm: {len(tekst) / 1e6:.2f} MB", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
