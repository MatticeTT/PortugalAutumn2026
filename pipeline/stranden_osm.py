"""Strandvlakken (natural=beach) van Portugal uit OpenStreetMap voor de kaart: web/public/basis/stranden.geojson.

Invoer: een uittreksel van Geofabrik, gefilterd met osmium (zie .github/workflows/stranden.yml). Vereenvoudigd tot op
een paar meter en afgerond, zodat het bestand klein blijft. © OpenStreetMap-bijdragers (ODbL)."""
import json
import sys

from shapely.geometry import mapping, shape

TOL = 0.00003  # ongeveer 3 m


def main(invoer, uit):
    feats = []
    for f in json.load(open(invoer))["features"]:
        g = f.get("geometry")
        if not g or g["type"] not in ("Polygon", "MultiPolygon"):
            continue
        s = shape(g).buffer(0).simplify(TOL, preserve_topology=True)
        if s.is_empty or s.area < 2e-9:
            continue
        m = mapping(s)
        rond = lambda c: [[round(x, 5), round(y, 5)] for x, y in c]
        if m["type"] == "Polygon":
            m = {"type": "Polygon", "coordinates": [rond(r) for r in m["coordinates"]]}
        else:
            m = {"type": "MultiPolygon", "coordinates": [[rond(r) for r in p] for p in m["coordinates"]]}
        feats.append({"type": "Feature", "properties": {}, "geometry": m})
    json.dump({"type": "FeatureCollection", "features": feats}, open(uit, "w"), separators=(",", ":"))
    print(len(feats), "stranden")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
