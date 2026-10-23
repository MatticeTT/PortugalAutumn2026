"""Gedetailleerde kustlijn uit OpenStreetMap (land polygons van osmdata.openstreetmap.de, ODbL) voor een gebied.

De grove wereldkaart (Natural Earth, web/public/basis/land.geojson) is vereenvoudigd tot ongeveer 800 m; ingezoomd ligt
de kust er dan naast de stranden. Dit maakt voor het gebied BBOX:
  basis/land-fijn.geojson    land uit OpenStreetMap, vereenvoudigd tot ongeveer 3 m
  basis/land-buiten.geojson  de grove wereldkaart zonder dat gebied (zodat ze ingezoomd niet over elkaar liggen)
De kaart toont de grove kaart uitgezoomd en de fijne vanaf zoom 7.

Gebruik (GitHub Actions): python -m pipeline.kustlijn --zip land-polygons-split-4326.zip --uit web/public/basis
"""

from __future__ import annotations

import argparse
import io
import json
import zipfile
from pathlib import Path

import shapefile  # pyshp
import shapely
from shapely.geometry import box, mapping, shape

BBOX = (-10.2, 36.6, -6.0, 42.4)  # Portugal (lengte, breedte), met marge
VEREENVOUDIG = 0.00003  # graden, ongeveer 3 m
DECIMALEN = 5


def afronden(g):
    return json.loads(json.dumps(mapping(g)), parse_float=lambda x: round(float(x), DECIMALEN))


def fijn(zip_pad: Path):
    z = zipfile.ZipFile(zip_pad)
    naam = next(n[:-4] for n in z.namelist() if n.endswith(".shp"))
    r = shapefile.Reader(shp=io.BytesIO(z.read(naam + ".shp")), shx=io.BytesIO(z.read(naam + ".shx")),
                         dbf=io.BytesIO(z.read(naam + ".dbf")))
    vak = box(*BBOX)
    delen = []
    for sh in r.iterShapes():
        x0, y0, x1, y1 = sh.bbox
        if x1 < BBOX[0] or x0 > BBOX[2] or y1 < BBOX[1] or y0 > BBOX[3]:
            continue
        g = shape(sh.__geo_interface__)
        g = g.intersection(vak)
        if not g.is_empty:
            delen.append(g)
    land = shapely.union_all(delen).simplify(VEREENVOUDIG, preserve_topology=True)
    print(f"fijn: {len(delen)} stukken", flush=True)
    return land


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--zip", type=Path, required=True)
    p.add_argument("--uit", type=Path, default=Path("web/public/basis"))
    a = p.parse_args(argv)
    land = fijn(a.zip)
    geos = list(getattr(land, "geoms", [land]))
    (a.uit / "land-fijn.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {}, "geometry": afronden(g)} for g in geos]}, separators=(",", ":")))
    print(f"land-fijn: {(a.uit / 'land-fijn.geojson').stat().st_size / 1e6:.1f} MB", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
