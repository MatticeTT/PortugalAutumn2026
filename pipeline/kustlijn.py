"""Fijne kustlijn voor een gebied uit GSHHG (volle resolutie, ongeveer 100 m; Wessel & Smith, LGPL).

De grove wereldkaart (Natural Earth, web/public/basis/land.geojson) is vereenvoudigd tot ongeveer 800 m; ingezoomd ligt
de kust er dan naast de stranden. Dit maakt voor het gebied BBOX:
  basis/land-fijn.geojson    land (met meren eruit), vereenvoudigd tot ongeveer 30 m
De kaart toont vanaf zoom 7 deze kust plus basis/land-buiten.geojson (de wereldkaart zonder het gebied).
(OpenStreetMap land polygons waren vanuit GitHub Actions niet bereikbaar.)

Gebruik: python -m pipeline.kustlijn --gshhg <map met gshhs_f.dat en gshhsmeta_f.dat> --uit web/public/basis
GSHHG ophalen: pip download basemap-data-hires en uitpakken (mpl_toolkits/basemap_data).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import Polygon, box, mapping

BBOX = (-10.2, 36.6, -6.0, 42.4)  # Portugal (lengte, breedte), met marge
VEREENVOUDIG = 0.0003  # graden, ongeveer 30 m
DECIMALEN = 5


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--gshhg", type=Path, required=True)
    p.add_argument("--uit", type=Path, default=Path("web/public/basis"))
    a = p.parse_args(argv)
    vak = box(*BBOX)
    meta = [r.split() for r in (a.gshhg / "gshhsmeta_f.dat").read_text().splitlines() if r.strip()]
    raw = np.fromfile(a.gshhg / "gshhs_f.dat", dtype="<f4")
    land, meer = [], []
    for m in meta:
        niveau, start, n = int(m[0]), int(m[5]), int(m[6])
        pts = raw[start // 4:(start + n) // 4].reshape(-1, 2).astype(float)
        if len(pts) < 4 or pts[:, 0].max() < BBOX[0] or pts[:, 0].min() > BBOX[2] or pts[:, 1].max() < BBOX[1] or pts[:, 1].min() > BBOX[3]:
            continue
        g = Polygon(pts).buffer(0).intersection(vak)
        if not g.is_empty:
            (land if niveau in (1, 3, 5) else meer).append(g)
    geheel = shapely.union_all(land)
    if meer:
        geheel = geheel.difference(shapely.union_all(meer))
    geheel = geheel.simplify(VEREENVOUDIG, preserve_topology=True)
    tekst = json.dumps({"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {}, "geometry": mapping(g)}
                                                                  for g in getattr(geheel, "geoms", [geheel])]}, separators=(",", ":"))
    tekst = json.dumps(json.loads(tekst, parse_float=lambda x: round(float(x), DECIMALEN)), separators=(",", ":"))
    (a.uit / "land-fijn.geojson").write_text(tekst)
    print(f"land-fijn: {len(tekst) / 1e6:.2f} MB", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
