"""Stap 1: spotlijst bouwen.

    python -m spots.bouw --kustlijn pad/naar/lines.shp [--osm data/spots/ruw/osm_spots.json] [--buurt ...]

Zonder --osm haalt het script de spots zelf op bij Overpass.
Uitvoer in data/spots/: spots.geojson, spots.csv, na_te_kijken.csv, uitgesloten.csv.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import pyproj
import shapely
import yaml

from spots import kust as K
from spots import osm

ROOT = Path(__file__).resolve().parents[1]
UIT = ROOT / "data" / "spots"


def regels() -> dict:
    return yaml.safe_load((ROOT / "regels" / "spots.yaml").read_text())


def satelliet(lat, lon):
    return f"https://www.google.com/maps/@{lat:.6f},{lon:.6f},400m/data=!3m1!1e3"


def osm_link(el):
    return f"https://www.openstreetmap.org/{el['type']}/{el['id']}"


def past(tags: dict, sleutel: str) -> bool:
    """'a=b&c=d' past als alle paren in de tags staan."""
    for paar in sleutel.split("&"):
        k, v = paar.split("=", 1)
        if tags.get(k) != v:
            return False
    return True


def kies(tags: dict, tabel: dict) -> str | None:
    for sleutel in sorted(tabel, key=lambda s: -s.count("&")):
        if past(tags, sleutel):
            return tabel[sleutel]
    return None


def grootte_m(el) -> float:
    b = el.get("bounds")
    if not b:
        return 0.0
    dy = (b["maxlat"] - b["minlat"]) * 111_000
    dx = (b["maxlon"] - b["minlon"]) * 111_000 * math.cos(math.radians((b["maxlat"] + b["minlat"]) / 2))
    return math.hypot(dx, dy)


def bodem(el, lon, lat, buurt, r) -> tuple[str | None, str, str, str | None]:
    """(bodem, soort, bron, twijfel)."""
    tags = el.get("tags", {})
    b = kies(tags, r["bodem"]["tag_naar_bodem"])
    if b:
        return b, "expert", "OSM-tag op de spot", None
    straal = r["bodem"]["zoekstraal_m"]["waarde"]
    proj = pyproj.Transformer.from_crs(
        "EPSG:4326", f"+proj=aeqd +lat_0={lat} +lon_0={lon} +datum=WGS84 +units=m", always_xy=True)
    gevonden = set()
    for g_ll, b_tags, ref in buurt:
        g = shapely.transform(g_ll, lambda c: __import__("numpy").column_stack(proj.transform(c[:, 0], c[:, 1])))
        if g.distance(shapely.Point(0, 0)) <= straal:
            s = kies(b_tags, r["bodem"]["buurt_naar_bodem"])
            if s:
                gevonden.add((s, ref))
    soorten = sorted({s for s, _ in gevonden})
    if len(soorten) == 1:
        refs = ", ".join(sorted(ref for _, ref in gevonden))
        return soorten[0], "berekend", f"OSM binnen {straal} m: {refs}", None
    if len(soorten) > 1:
        return None, "nog te meten", "", f"bodem: binnen {straal} m liggen {' en '.join(soorten)}"
    return None, "nog te meten", "", None


def buurt_index(elementen):
    """Lijst (vorm, tags, ref) plus STRtree, voor snelle zoektocht per spot."""
    items = []
    for el in elementen:
        g = osm.vorm(el)
        if g is not None and not g.is_empty:
            items.append((g, el.get("tags", {}), f"{el['type']}/{el['id']}"))
    boom = shapely.STRtree([g for g, _, _ in items]) if items else None
    return items, boom


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--kustlijn", required=True, help="OSM coastlines-split-4326 lines.shp (of ander lijnbestand)")
    ap.add_argument("--osm", help="opgeslagen Overpass-antwoord met de spots")
    ap.add_argument("--buurt", help="opgeslagen Overpass-antwoord met stranden en riffen")
    ap.add_argument("--uit", default=str(UIT))
    a = ap.parse_args(argv)
    r = regels()
    uit = Path(a.uit)
    (uit / "ruw").mkdir(parents=True, exist_ok=True)

    ruw = json.loads(Path(a.osm).read_text()) if a.osm else osm.haal_spots(uit / "ruw" / "osm_spots.json")
    stand_osm = ruw.get("osm3s", {}).get("timestamp_osm_base", "onbekend")

    spots, uitgesloten, twijfel = [], [], []
    for el in ruw["elements"]:
        tags = el.get("tags", {})
        p = osm.punt(el)
        naam = tags.get("name", "")
        if p is None:
            continue
        lon, lat = p
        weg = [t for t in r["uitsluiten_als_tag"] if t in tags]
        if weg:
            uitgesloten.append({"osm": osm_link(el), "naam": naam, "lat": lat, "lon": lon,
                                "reden": "zaak of school: " + ", ".join(f"{t}={tags[t]}" for t in weg)})
            continue
        spots.append((el, lon, lat, naam))

    buurt_el = []
    if a.buurt:
        buurt_el = json.loads(Path(a.buurt).read_text())["elements"]
    elif spots:
        buurt_el = osm.haal_buurt([{"lat": la, "lon": lo} for _, lo, la, _ in spots],
                                  r["bodem"]["zoekstraal_m"]["waarde"], uit / "ruw" / "osm_buurt.json")
    items, boom = buurt_index(buurt_el)

    kustlijn = K.Kustlijn.uit_bestand(a.kustlijn)
    max_vlak = r["positie"]["max_grootte_vlak_m"]["waarde"]
    rijen = []
    for el, lon, lat, naam in spots:
        id_ = f"{el['type']}/{el['id']}"
        redenen = []
        if grootte_m(el) > max_vlak:
            redenen.append(f"positie: spot is een vlak van {grootte_m(el):.0f} m, middelpunt onzeker")
        res = K.bereken(kustlijn, lon, lat, r)
        positie_fout = any(t.startswith(("positie", "geen kustlijn", "kant onzeker")) for t in res.twijfel)
        redenen += res.twijfel

        dichtbij = []
        if boom is not None:
            d = 0.01
            idx = boom.query(shapely.box(lon - d * 3, lat - d * 3, lon + d * 3, lat + d * 3))
            dichtbij = [items[i] for i in idx]
        b, b_soort, b_bron, b_twijfel = bodem(el, lon, lat, dichtbij, r)
        if b_twijfel:
            redenen.append(b_twijfel)

        for reden in redenen:
            twijfel.append({"id": id_, "naam": naam, "lat": round(lat, 6), "lon": round(lon, 6), "reden": reden,
                            "satelliet": satelliet(lat, lon), "osm": osm_link(el)})
        if positie_fout or "positie:" in " ".join(redenen):
            continue  # hele spot uit de berekening tot nagekeken

        rijen.append({
            "id": id_, "naam": naam, "lat": round(lat, 6), "lon": round(lon, 6),
            "afstand_kust_m": round(res.afstand_kust_m), "kant": res.spot_kant,
            "strandrichting": res.strandrichting,
            "venster_van": res.venster_van, "venster_tot": res.venster_tot, "venster_breedte": res.venster_breedte,
            "rekenpunt_lon": round(res.rekenpunt_lonlat[0], 6) if res.rekenpunt_lonlat else None,
            "rekenpunt_lat": round(res.rekenpunt_lonlat[1], 6) if res.rekenpunt_lonlat else None,
            "bodem": b, "helling": None,
            "bronnen": {
                "positie": {"bron": f"OSM {id_}", "soort": "expert"},
                "strandrichting": {"bron": "OSM-kustlijn", "soort": "berekend" if res.strandrichting is not None else "nog te meten"},
                "swellvenster": {"bron": f"OSM-kustlijn, stralen tot {r['swellvenster']['bereik_km']['waarde']} km",
                                 "soort": "berekend" if res.venster_van is not None else "nog te meten"},
                "bodem": {"bron": b_bron, "soort": b_soort},
                "helling": {"bron": "", "soort": "nog te meten"},
            },
        })

    schrijf(uit, rijen, twijfel, uitgesloten, stand_osm)
    print(f"{len(rijen)} spots, {len(twijfel)} punten na te kijken, {len(uitgesloten)} uitgesloten")


def schrijf(uit: Path, rijen, twijfel, uitgesloten, stand_osm):
    meta = {"gemaakt": datetime.now(timezone.utc).isoformat(timespec="seconds"), "stand_osm": stand_osm,
            "licentie": "ODbL 1.0, © OpenStreetMap-bijdragers"}
    fc = {"type": "FeatureCollection", "meta": meta, "features": [
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [s["lon"], s["lat"]]},
         "properties": {k: v for k, v in s.items() if k not in ("lat", "lon")}} for s in rijen]}
    (uit / "spots.geojson").write_text(json.dumps(fc, ensure_ascii=False))
    velden = [k for k in rijen[0] if k != "bronnen"] + ["bodem_soort", "bodem_bron"] if rijen else []
    with open(uit / "spots.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=velden)
        w.writeheader()
        for s in rijen:
            rij = {k: v for k, v in s.items() if k != "bronnen"}
            rij["bodem_soort"] = s["bronnen"]["bodem"]["soort"]
            rij["bodem_bron"] = s["bronnen"]["bodem"]["bron"]
            w.writerow(rij)
    for naam, lijst, velden in [
        ("na_te_kijken.csv", twijfel, ["id", "naam", "lat", "lon", "reden", "satelliet", "osm"]),
        ("uitgesloten.csv", uitgesloten, ["osm", "naam", "lat", "lon", "reden"]),
    ]:
        with open(uit / naam, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=velden)
            w.writeheader()
            w.writerows(lijst)
    (uit / "meta.json").write_text(json.dumps(meta, indent=1))


if __name__ == "__main__":
    main()
