"""M1, stap 1: ruwe brondata ophalen (draait in GitHub Actions).

Schrijft naar data/raw/:
- osm_beaches.geojsonseq     natural=beach uit het Geofabrik-bestand van Portugal
- osm_coastline.geojsonseq   natural=coastline
- osm_districts.geojson      distritos (admin_level=6), vereenvoudigd
- land_full.geojson          nauwkeurige landveelhoeken van osmdata.openstreetmap.de rond Portugal
- land_simplified.geojson    vereenvoudigde landveelhoeken van osmdata.openstreetmap.de,
                             uitgesneden rond Iberië en Marokko (voor stralen ver weg)
- eea_bathing.json           officiële zwemwateren van Portugal (EEA/APA)
- eea_schema.json            tabellen en kolommen die bij EEA gevonden werden

Vereist: osmium-tool, shapely, pyproj, pyshp.
"""

from __future__ import annotations

import io
import json
import subprocess
import sys
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
UA = "surfkaart-portugal/0.1 (niet-commercieel, besloten)"

GEOFABRIK = "https://download.geofabrik.de/europe/portugal-latest.osm.pbf"
LAND = "https://osmdata.openstreetmap.de/download/simplified-land-polygons-complete-3857.zip"
LAND_FULL = "https://osmdata.openstreetmap.de/download/land-polygons-split-4326.zip"
# Rechthoek voor de nauwkeurige landveelhoeken: het vasteland met wat Spanje errond.
FULL_BBOX = (-10.2, 36.6, -6.6, 42.4)
DISCODATA = "https://discodata.eea.europa.eu/sql"
# Ruime rechthoek voor stralen: Iberië, Marokko, Golf van Biskaje.
RAY_BBOX = (-14.0, 33.0, -1.0, 45.5)


def download(url: str, dest: Path) -> Path:
    if dest.exists():
        return dest
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=600) as r, open(dest, "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)
    return dest


def run(*args: str) -> None:
    print("+", " ".join(args), flush=True)
    subprocess.run(args, check=True)


def osm() -> None:
    pbf = download(GEOFABRIK, RAW / "portugal-latest.osm.pbf")
    for name, expr in [
        ("osm_beaches", "nwr/natural=beach"),
        ("osm_coastline", "w/natural=coastline"),
        ("osm_districts_raw", "r/admin_level=6"),
    ]:
        flt = RAW / f"{name}.osm.pbf"
        run("osmium", "tags-filter", "--overwrite", "-o", str(flt), str(pbf), expr)
        out = str(RAW / f"{name}.geojsonseq")
        geom = "linestring" if name == "osm_coastline" else "point,polygon"
        run("osmium", "export", "--overwrite", "-a", "type,id", f"--geometry-types={geom}",
            "-f", "geojsonseq", "-o", out, str(flt))
    simplify_districts()


def simplify_districts() -> None:
    from shapely.geometry import mapping, shape

    out = []
    for line in (RAW / "osm_districts_raw.geojsonseq").read_text().splitlines():
        line = line.lstrip("\x1e").strip()
        if not line:
            continue
        f = json.loads(line)
        p = f["properties"]
        if p.get("boundary") != "administrative" or f["geometry"]["type"] not in ("Polygon", "MultiPolygon"):
            continue
        g = shape(f["geometry"]).simplify(0.0005, preserve_topology=True)
        props = {k: p.get(k) for k in ("name", "ref", "dicofre", "ISO3166-2")}
        props["osm_id"] = f"{p.get('@type')}/{p.get('@id')}"
        out.append({"type": "Feature", "geometry": mapping(g), "properties": props})
    (RAW / "osm_districts.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": out}))
    print(f"distritos: {len(out)}")


def land() -> None:
    import shapefile  # pyshp
    from pyproj import Transformer
    from shapely.geometry import box, mapping, shape
    from shapely.ops import transform

    z = download(LAND, RAW / "land.zip")
    to_wgs = Transformer.from_crs(3857, 4326, always_xy=True).transform
    to_merc = Transformer.from_crs(4326, 3857, always_xy=True).transform
    clip_wgs = box(*RAY_BBOX)
    clip_merc = transform(to_merc, clip_wgs)
    with zipfile.ZipFile(z) as zf:
        base = next(n[:-4] for n in zf.namelist() if n.endswith(".shp"))
        r = shapefile.Reader(shp=io.BytesIO(zf.read(base + ".shp")), shx=io.BytesIO(zf.read(base + ".shx")),
                             dbf=io.BytesIO(zf.read(base + ".dbf")))
        out = []
        cx0, cy0, cx1, cy1 = clip_merc.bounds
        for i, rec in enumerate(r.iterShapes()):
            x0, y0, x1, y1 = rec.bbox
            if x1 < cx0 or x0 > cx1 or y1 < cy0 or y0 > cy1:
                continue
            g = shape(rec.__geo_interface__).intersection(clip_merc)
            if g.is_empty:
                continue
            out.append({"type": "Feature", "geometry": mapping(transform(to_wgs, g)), "properties": {"i": i}})
    (RAW / "land_simplified.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": out}))
    print(f"landveelhoeken: {len(out)}")


def land_full() -> None:
    """Nauwkeurige landveelhoeken rond Portugal, met de naden van de tegels weggewerkt."""
    import shapefile  # pyshp
    from shapely.geometry import box, mapping, shape
    from shapely.ops import unary_union

    z = download(LAND_FULL, RAW / "land_full.zip")
    clip = box(*FULL_BBOX)
    parts = []
    with zipfile.ZipFile(z) as zf:
        base = next(n[:-4] for n in zf.namelist() if n.endswith(".shp"))
        r = shapefile.Reader(shp=io.BytesIO(zf.read(base + ".shp")), shx=io.BytesIO(zf.read(base + ".shx")),
                             dbf=io.BytesIO(zf.read(base + ".dbf")))
        for rec in r.iterShapes():
            x0, y0, x1, y1 = rec.bbox
            if x1 < FULL_BBOX[0] or x0 > FULL_BBOX[2] or y1 < FULL_BBOX[1] or y0 > FULL_BBOX[3]:
                continue
            g = shape(rec.__geo_interface__).intersection(clip)
            if not g.is_empty:
                parts.append(g)
    land = unary_union(parts)
    geoms = list(getattr(land, "geoms", [land]))
    feats = [{"type": "Feature", "geometry": mapping(g), "properties": {}} for g in geoms if g.area > 0]
    (RAW / "land_full.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": feats}))
    print(f"nauwkeurige landveelhoeken: {len(feats)}")


def sql(query: str, n: int = 5000):
    url = f"{DISCODATA}?{urllib.parse.urlencode({'query': query, 'p': 1, 'nrOfHits': n})}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def eea() -> None:
    """Zoek in WISE_BWD de tabel met zwemwateren en coördinaten, en haal Portugal op."""
    tables = sql("SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME FROM [WISE_BWD].INFORMATION_SCHEMA.COLUMNS")
    (RAW / "eea_antwoord.json").write_text(json.dumps(tables, ensure_ascii=False)[:20000])
    rows = tables.get("results", tables) if isinstance(tables, dict) else tables
    if not isinstance(rows, list) or (rows and not isinstance(rows[0], dict)):
        raise RuntimeError(f"onverwacht antwoord van discodata: {json.dumps(tables)[:300]}")
    schema: dict[str, list[str]] = {}
    for r in rows:
        schema.setdefault(f"[WISE_BWD].[{r['TABLE_SCHEMA']}].[{r['TABLE_NAME']}]", []).append(r["COLUMN_NAME"])
    (RAW / "eea_schema.json").write_text(json.dumps(schema, indent=1))

    def score(cols: list[str]) -> int:
        lc = [c.lower() for c in cols]
        has = lambda *ks: any(any(k in c for k in ks) for c in lc)  # noqa: E731
        return (has("lat") and has("lon")) * 4 + has("country") + has("bathingwatername", "name") + has("type")

    cands = sorted(((score(c), t) for t, c in schema.items() if ".[latest]." in t), reverse=True)
    print("kandidaten:", cands[:6])
    for s, t in cands[:6]:
        if s < 4:
            break
        cols = schema[t]
        country = next((c for c in cols if c.lower() in ("countrycode", "country_code", "cyear_countrycode")), None)
        where = f"WHERE [{country}] = 'PT'" if country else ""
        try:
            res = sql(f"SELECT * FROM {t} {where}", n=20000)
        except Exception as e:  # noqa: BLE001
            print("fout", t, e)
            continue
        data = res.get("results", res)
        if data:
            (RAW / "eea_bathing.json").write_text(json.dumps({"tabel": t, "rijen": data}, ensure_ascii=False))
            print(f"EEA: {len(data)} rijen uit {t}")
            return
    raise RuntimeError("geen EEA-tabel met coördinaten gevonden; zie eea_schema.json")


STEPS = {"osm": osm, "land": land, "land_full": land_full, "eea": eea}

if __name__ == "__main__":
    RAW.mkdir(parents=True, exist_ok=True)
    failed = []
    for name in sys.argv[1:] or list(STEPS):
        try:
            STEPS[name]()
        except Exception as e:  # noqa: BLE001
            print(f"FOUT {name}: {type(e).__name__}: {e}", flush=True)
            failed.append(name)
    sys.exit(1 if failed else 0)
