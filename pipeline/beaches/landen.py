"""Stranden van andere landen (Spanje, Frankrijk, België), met dezelfde meetkunde als Portugal.

Portugal blijft in data/beaches/stranden.geojson (build.py, ongewijzigd). Elk ander land krijgt
data/beaches/landen/<land>.geojson met dezelfde eigenschappen per strand, plus "land".

Verschillen met build.py:
- bron: het Geofabrik-bestand van het land, de nauwkeurige landveelhoeken rond het land, en de
  EEA-zwemwateren van dat land (met bladeren: Spanje en Frankrijk hebben er meer dan 1000);
- projectie: build.py rekent in PT-TM06, een Transverse Mercator rond Portugal. Voor grotere landen
  wordt per strook van 2 lengtegraden een Transverse Mercator rond het midden van de strook gebruikt,
  zodat noord op de kaart overal binnen een graad van het echte noorden ligt (zoals in Portugal);
- provincie (admin_level 6) in plaats van het Portugese district; geen IPMA-code.

Gebruik:  python -m pipeline.beaches.landen ophalen es    (in GitHub Actions)
          python -m pipeline.beaches.landen bouwen es
"""

from __future__ import annotations

import csv
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

from pipeline.beaches import fetch

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "beaches" / "landen"

# Per land: Geofabrik-bestand, EEA-landcode, rechthoek rond het vasteland (lon0, lat0, lon1, lat1)
# en een extra regel om eilanden weg te laten (zoals Portugal alleen het vasteland heeft).
LANDEN = {
    "es": {"naam": "Spanje", "geofabrik": "europe/spain", "eea": "ES", "bbox": (-9.45, 35.95, 3.4, 43.85)},
    "fr": {"naam": "Frankrijk", "geofabrik": "europe/france", "eea": "FR", "bbox": (-5.3, 42.3, 8.3, 51.15)},
    "be": {"naam": "België", "geofabrik": "europe/belgium", "eea": "BE", "bbox": (2.4, 50.9, 3.5, 51.45)},
}
# Ruime rechthoek voor de stralen (300 km): van de Atlantische Oceaan tot Italië en de Noordzee.
RAY_BBOX = (-16.0, 30.0, 16.0, 58.0)
BAND_GRADEN = 2.0
RAND_GRADEN = 0.6  # nauwkeurig land rond een strook: ruim meer dan de 20 km van de nauwkeurige stralen


def vasteland(land: str, lon: float, lat: float) -> bool:
    x0, y0, x1, y1 = LANDEN[land]["bbox"]
    if not (x0 <= lon <= x1 and y0 <= lat <= y1):
        return False
    if land == "es" and lat < 40.5 and lon > 0.5:  # Balearen
        return False
    return not (land == "fr" and lon > 8.0)  # Corsica


def raw(land: str) -> Path:
    p = ROOT / "data" / "raw" / land
    p.mkdir(parents=True, exist_ok=True)
    return p


# --- ophalen (GitHub Actions) -------------------------------------------------


def ophalen(land: str) -> None:
    import io
    import zipfile

    import shapefile  # pyshp
    from pyproj import Transformer
    from shapely.geometry import box, mapping, shape
    from shapely.ops import transform

    cfg, d = LANDEN[land], raw(land)
    # 1. OSM: stranden en provincies
    pbf = fetch.download(f"https://download.geofabrik.de/{cfg['geofabrik']}-latest.osm.pbf", d / "land.osm.pbf")
    for name, expr, geom in [("osm_beaches", "nwr/natural=beach", "point,polygon"),
                             ("osm_districts_raw", "r/admin_level=6", "point,polygon")]:
        flt = d / f"{name}.osm.pbf"
        fetch.run("osmium", "tags-filter", "--overwrite", "-o", str(flt), str(pbf), expr)
        fetch.run("osmium", "export", "--overwrite", "-a", "type,id", f"--geometry-types={geom}",
                  "-f", "geojsonseq", "-o", str(d / f"{name}.geojsonseq"), str(flt))
    pbf.unlink()
    provincies = []
    for f in fetch_seq(d / "osm_districts_raw.geojsonseq"):
        p = f["properties"]
        if (p.get("boundary") != "administrative" or str(p.get("admin_level")) != "6"
                or f["geometry"]["type"] not in ("Polygon", "MultiPolygon") or not p.get("name")):
            continue
        g = shape(f["geometry"]).simplify(0.0005, preserve_topology=True)
        provincies.append({"type": "Feature", "geometry": mapping(g), "properties": {"name": p["name"]}})
    (d / "osm_districts.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": provincies}))
    print(f"provincies: {len(provincies)}", flush=True)
    # Ook vereenvoudigd in git (data/gebieden/<land>.geojson): weerwaarschuwingen per gebied, ook voor klimplekken.
    gebieden = ROOT / "data" / "gebieden"
    gebieden.mkdir(parents=True, exist_ok=True)
    (gebieden / f"{land}.geojson").write_text(json.dumps({
        "type": "FeatureCollection", "land": land, "bron": "OpenStreetMap (admin_level 6), vereenvoudigd",
        "features": [f | {"geometry": mapping(shape(f["geometry"]).simplify(0.005, preserve_topology=True))}
                     for f in provincies]}, ensure_ascii=False, separators=(",", ":")))

    # 2. Nauwkeurig land rond het vasteland (zelfde bron als Portugal), ongeknipt per tegel bewaard.
    x0, y0, x1, y1 = cfg["bbox"]
    clip = (x0 - RAND_GRADEN, y0 - RAND_GRADEN, x1 + RAND_GRADEN, y1 + RAND_GRADEN)
    z = fetch.download(fetch.LAND_FULL, ROOT / "data" / "raw" / "land_full.zip")
    feats = []
    with zipfile.ZipFile(z) as zf:
        base = next(n[:-4] for n in zf.namelist() if n.endswith(".shp"))
        r = shapefile.Reader(shp=io.BytesIO(zf.read(base + ".shp")), shx=io.BytesIO(zf.read(base + ".shx")),
                             dbf=io.BytesIO(zf.read(base + ".dbf")))
        for rec in r.iterShapes():
            bx0, by0, bx1, by1 = rec.bbox
            if bx1 < clip[0] or bx0 > clip[2] or by1 < clip[1] or by0 > clip[3]:
                continue
            g = shape(rec.__geo_interface__).intersection(box(*clip))
            if not g.is_empty:
                feats.append({"type": "Feature", "geometry": mapping(g), "properties": {}})
    (d / "land_full.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": feats}))
    print(f"nauwkeurige landstukken: {len(feats)}", flush=True)

    # 3. Vereenvoudigd land voor de stralen ver weg (zelfde bron als Portugal, grotere rechthoek).
    z = fetch.download(fetch.LAND, ROOT / "data" / "raw" / "land.zip")
    to_wgs = Transformer.from_crs(3857, 4326, always_xy=True).transform
    to_merc = Transformer.from_crs(4326, 3857, always_xy=True).transform
    clip_merc = transform(to_merc, box(*RAY_BBOX))
    cx0, cy0, cx1, cy1 = clip_merc.bounds
    out = []
    with zipfile.ZipFile(z) as zf:
        base = next(n[:-4] for n in zf.namelist() if n.endswith(".shp"))
        r = shapefile.Reader(shp=io.BytesIO(zf.read(base + ".shp")), shx=io.BytesIO(zf.read(base + ".shx")),
                             dbf=io.BytesIO(zf.read(base + ".dbf")))
        for rec in r.iterShapes():
            bx0, by0, bx1, by1 = rec.bbox
            if bx1 < cx0 or bx0 > cx1 or by1 < cy0 or by0 > cy1:
                continue
            g = shape(rec.__geo_interface__).intersection(clip_merc)
            if not g.is_empty:
                out.append({"type": "Feature", "geometry": mapping(transform(to_wgs, g)), "properties": {}})
    (d / "land_simplified.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": out}))
    print(f"vereenvoudigde landveelhoeken: {len(out)}", flush=True)

    # 4. EEA-zwemwateren van het land, met bladeren.
    (d / "eea.json").write_text(json.dumps(eea(cfg["eea"], cfg["bbox"]), ensure_ascii=False))


def fetch_seq(path: Path):
    for line in path.read_text().splitlines():
        line = line.lstrip("\x1e").strip()
        if line:
            yield json.loads(line)


def eea(code: str, bbox) -> list[dict]:
    """Kust- en overgangszwemwateren van één land uit de recentste EEA-dienst die punten heeft."""
    folder = fetch.get_json(f"{fetch.ARCGIS}/BathingWater", {"f": "json"})
    services = [x for x in folder.get("services", []) if x["type"] in ("MapServer", "FeatureServer")]
    beste: tuple[int, list[dict]] | None = None
    for svc in services:
        m = re.search(r"(20\d\d)$", svc["name"])
        jaar = int(m.group(1)) if m else 0
        base = f"{fetch.ARCGIS}/{svc['name']}/{svc['type']}"
        try:
            info = fetch.get_json(base, {"f": "json"})
        except Exception as e:  # noqa: BLE001
            print("fout", base, e)
            continue
        for lyr in info.get("layers", []):
            if lyr.get("geometryType") != "esriGeometryPoint" or lyr.get("subLayerIds"):
                continue
            punten, offset = [], 0
            while True:
                try:
                    res = fetch.get_json(f"{base}/{lyr['id']}/query", {
                        "where": f"countryCode='{code}'", "geometry": ",".join(map(str, bbox)),
                        "geometryType": "esriGeometryEnvelope", "inSR": 4326, "spatialRel": "esriSpatialRelIntersects",
                        "outFields": "*", "outSR": 4326, "f": "json", "resultOffset": offset, "resultRecordCount": 1000,
                    })
                except Exception as e:  # noqa: BLE001
                    print("fout", base, lyr["id"], e)
                    break
                if "error" in res:  # laag zonder veld countryCode
                    break
                feats = res.get("features", [])
                punten += [f["attributes"] for f in feats]
                if not feats or not res.get("exceededTransferLimit"):
                    break
                offset += len(feats)
            if punten and "bathingWaterIdentifier" in punten[0]:
                print(f"{svc['name']} laag {lyr['id']}: {len(punten)} zwemwateren", flush=True)
                if beste is None or (jaar, len(punten)) > (beste[0], len(beste[1])):
                    beste = (jaar, [p | {"_jaar": jaar} for p in punten])
    if beste is None:
        raise RuntimeError(f"geen EEA-zwemwateren voor {code}")
    return beste[1]


# --- bouwen -------------------------------------------------------------------


def bouwen(land: str) -> None:
    from pyproj import Transformer
    from shapely import STRtree
    from shapely.geometry import LineString, Point, box, shape
    from shapely.geometry.polygon import orient
    from shapely.ops import transform, unary_union
    from shapely.prepared import prep

    from pipeline.beaches import build as b

    d = raw(land)
    land_full = [shape(f["geometry"]) for f in json.loads((d / "land_full.geojson").read_text())["features"]]
    land_full_tree = STRtree(land_full)
    far_wgs = [shape(f["geometry"]) for f in json.loads((d / "land_simplified.geojson").read_text())["features"]]
    provincies = [(f["properties"]["name"], shape(f["geometry"]))
                  for f in json.loads((d / "osm_districts.geojson").read_text())["features"]]

    # Stranden (WGS84) en zwemwateren van het vasteland.
    osm_all = []
    for f in fetch_seq(d / "osm_beaches.geojsonseq"):
        p = f["properties"]
        if p.get("natural") != "beach" or f["geometry"]["type"] == "LineString":
            continue
        g = shape(f["geometry"])
        c = g.representative_point()
        if not vasteland(land, c.x, c.y):
            continue
        oid = f"{p['@type']}/{p['@id']}" if "@id" in p else None
        osm_all.append({"osm_id": oid, "naam": p.get("name"), "tags": p, "wgs": g, "lon": c.x})
    eea_all, seen = [], set()
    for r in json.loads((d / "eea.json").read_text()):
        cat = r.get("bwWaterCategory") or ""
        if cat not in ("Coastal", "Transitional") or r["bathingWaterIdentifier"] in seen:
            continue
        lon, lat = float(r["longitude"]), float(r["latitude"])
        if not vasteland(land, lon, lat):
            continue
        seen.add(r["bathingWaterIdentifier"])
        eea_all.append({"eea_id": r["bathingWaterIdentifier"], "eea_naam": r.get("bathingWaterName"), "eea_type": cat,
                        "eea_jaar": r.get("_jaar"), "wgs": Point(lon, lat), "lon": lon})
    print(f"{LANDEN[land]['naam']}: {len(osm_all)} OSM-stranden, {len(eea_all)} zwemwateren", flush=True)

    features, uncertain, skipped = [], [], defaultdict(list)
    tellers = defaultdict(int)
    x0, _, x1, _ = LANDEN[land]["bbox"]
    n_band = max(1, math.ceil((x1 - x0) / BAND_GRADEN))
    for k in range(n_band):
        lo, hi = x0 + k * BAND_GRADEN, min(x1, x0 + (k + 1) * BAND_GRADEN)
        last = k == n_band - 1
        osm = [x for x in osm_all if lo <= x["lon"] < hi or (last and x["lon"] == hi)]
        eea_band = [x for x in eea_all if lo <= x["lon"] < hi or (last and x["lon"] == hi)]
        if not osm and not eea_band:
            continue
        # Projectie van deze strook: Transverse Mercator rond het midden.
        lon0 = (lo + hi) / 2
        tm = f"+proj=tmerc +lat_0=0 +lon_0={lon0} +k=1 +x_0=0 +y_0=0 +ellps=GRS80 +units=m +no_defs"
        b.TO_M = Transformer.from_crs(4326, tm, always_xy=True).transform
        b.TO_LL = Transformer.from_crs(tm, 4326, always_xy=True).transform
        to_m = b.TO_M

        # Nauwkeurig land rond de strook (zoals build.load_land: dammen weg, land links van de rand).
        y_lo = min(x["wgs"].bounds[1] for x in osm + eea_band) - RAND_GRADEN
        y_hi = max(x["wgs"].bounds[3] for x in osm + eea_band) + RAND_GRADEN
        clip = box(lo - RAND_GRADEN, y_lo, hi + RAND_GRADEN, y_hi)
        r_ = b.PARAMS["dammen_weg_m"]
        # Eerst de tegels samenvoegen (naden weg, zoals fetch.land_full voor Portugal), dan dammen weg.
        stukken = [g for i in land_full_tree.query(clip) if not (g := land_full[i].intersection(clip)).is_empty]
        g = transform(to_m, unary_union(stukken)).buffer(-r_).buffer(r_)
        land_m = unary_union([x for x in getattr(g, "geoms", [g]) if x.area > 2000])
        # Randen van de uitsnede en van de oorspronkelijke tegels zijn geen kust.
        edge = prep(transform(to_m, clip.boundary.segmentize(0.01)).buffer(50))
        lines = []
        for poly in getattr(land_m, "geoms", [land_m]):
            if poly.is_empty:
                continue
            poly = orient(poly, 1.0)
            for ring in [poly.exterior, *poly.interiors]:
                run: list = []
                for q in ring.coords:
                    if edge.contains(Point(q)):
                        if len(run) > 1:
                            lines += list(b.chunks(LineString(run)))
                        run = []
                    else:
                        run.append(q)
                if len(run) > 1:
                    lines += list(b.chunks(LineString(run)))
        far = [seg for g in far_wgs for ring in _rings(g) for seg in b.chunks(transform(to_m, ring))]
        coast = b.Coast(lines, far, land_m)
        districts = [(n, transform(to_m, g)) for n, g in provincies
                     if g.intersects(clip)]

        for x in osm:
            x["geom"] = transform(to_m, x["wgs"])
        for x in eea_band:
            x["geom"] = transform(to_m, x["wgs"])
        near = []
        for x in osm:
            if not x["naam"]:
                continue
            _, dist = coast.nearest(x["geom"])
            if dist <= b.PARAMS["max_afstand_kust_m"]:
                near.append(x)
        beaches = b.merge_same_name(near)
        tellers["osm_met_naam_bij_kust"] += len(near)
        added = []
        if beaches:
            tree = STRtree([x["geom"] for x in beaches])
        unnamed = [x for x in osm if not x["naam"]]
        unnamed_tree = STRtree([x["geom"] for x in unnamed]) if unnamed else None
        for e in eea_band:
            if beaches:
                i = tree.nearest(e["geom"])
                if beaches[i]["geom"].distance(e["geom"]) <= b.PARAMS["eea_koppel_m"]:
                    beaches[i].setdefault("eea", []).append(e)
                    continue
            base = {"osm_id": None, "naam": e["eea_naam"], "tags": {}, "geom": e["geom"], "eea": [e], "bron": "eea"}
            if unnamed_tree is not None:
                j = unnamed_tree.nearest(e["geom"])
                u = unnamed[j]
                if u["geom"].distance(e["geom"]) <= b.PARAMS["eea_koppel_m"]:
                    base |= {"osm_id": u["osm_id"], "geom": u["geom"], "bron": "eea+osm zonder naam"}
            added.append(base)
        tellers["eea_toegevoegd"] += len(added)
        for x in beaches + added:
            a = b.analyse(coast, districts, x)
            if a["district"] is None:
                skipped[f"buiten {LANDEN[land]['naam']} (in geen enkele provincie)"].append(x["naam"])
                continue
            props = eigenschappen(b, land, x, a)
            features.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": a["punt"]},
                             "properties": props})
            if props["onzeker"]:
                uncertain.append(props | {"lon": a["punt"][0], "lat": a["punt"][1]})
        print(f"strook {lo:.1f}..{hi:.1f}: {len(features)} stranden tot nu", flush=True)

    # Dubbels over de rand van een strook heen (zelfde id): de eerste blijft.
    uniek, ids = [], set()
    for f in features:
        if f["properties"]["id"] not in ids:
            ids.add(f["properties"]["id"])
            uniek.append(f)
    features = sorted(uniek, key=lambda f: (-f["geometry"]["coordinates"][1], f["geometry"]["coordinates"][0]))
    OUT.mkdir(parents=True, exist_ok=True)
    fc = {"type": "FeatureCollection", "land": land,
          "licentie": "ODbL 1.0, © OpenStreetMap-bijdragers; zwemwateren: EEA (CC BY 4.0)",
          "bron": "pipeline/beaches/landen.py", "parameters": b.PARAMS, "features": features}
    (OUT / f"{land}.geojson").write_text(json.dumps(fc, ensure_ascii=False, indent=0) + "\n")
    with open(OUT / f"{land}_onzeker.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "naam", "lat", "lon", "kijkrichting", "zekerheid", "redenen", "google_maps"])
        for u in sorted(uncertain, key=lambda u: -u["lat"]):
            w.writerow([u["id"], u["naam"], u["lat"], u["lon"], u["kijkrichting"], u["richting_zekerheid"],
                        "; ".join(u["redenen"]), f"https://www.google.com/maps/@{u['lat']},{u['lon']},17z/data=!3m1!1e3"])
    per = defaultdict(int)
    for f in features:
        per[f["properties"]["district"]] += 1
    verslag = {"land": LANDEN[land]["naam"], "osm_stranden_vasteland": len(osm_all), **tellers,
               "eea_kustzwemwateren": len(eea_all), "stranden_totaal": len(features), "onzeker": len(uncertain),
               "kandidaat_besloten_water": sum(f["properties"]["kandidaat_besloten_water"] for f in features),
               "weggelaten": {k: len(v) for k, v in skipped.items()}, "per_provincie": dict(sorted(per.items()))}
    (OUT / f"{land}_verslag.json").write_text(json.dumps(verslag, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({k: v for k, v in verslag.items() if k != "per_provincie"}, ensure_ascii=False))


def _rings(g):
    for poly in getattr(g, "geoms", [g]):
        if poly.geom_type != "Polygon":
            continue
        yield poly.exterior
        yield from poly.interiors


def eigenschappen(b, land: str, x: dict, a: dict) -> dict:
    """Zelfde eigenschappen als build.build() voor Portugal, plus het land."""
    e = x.get("eea", [])
    if x.get("bron") == "eea" and a["afstand_kust_m"] > b.PARAMS["max_afstand_kust_m"]:
        a["redenen"].append(f"officieel zwemwater op {a['afstand_kust_m']} m van de OSM-kustlijn")
        a["onzeker"] = True
    if any(re.search("transit|transi", y["eea_type"], re.I) for y in e):
        a["redenen"].append("overgangswater (monding of lagune) volgens EEA")
        a["onzeker"] = True
    osm_id = x.get("osm_id")
    fid = osm_id or (f"eea/{e[0]['eea_id']}" if e else f"punt/{a['punt'][1]:.5f},{a['punt'][0]:.5f}")
    return {
        "id": fid, "land": land,
        "naam": x["naam"] or (e[0]["eea_naam"] if e else None),
        "osm_ids": x.get("osm_ids") or ([osm_id] if osm_id else []),
        "eea_ids": [y["eea_id"] for y in e], "eea_namen": [y["eea_naam"] for y in e],
        "eea_type": sorted({y["eea_type"] for y in e}), "bron": x.get("bron", "osm"),
        **{k: v for k, v in a.items() if k not in ("punt", "ipma_area")},
        "ipma_area": None, "besloten_water": False, "getij_voorkeur": None,
    }


if __name__ == "__main__":
    stap, land = sys.argv[1], sys.argv[2]
    {"ophalen": ophalen, "bouwen": bouwen}[stap](land)
