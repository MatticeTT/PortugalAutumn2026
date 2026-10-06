"""M1, stap 2: de strandentabel bouwen uit data/raw/.

Per strand:
- een punt op de kustlijn (het dichtste punt bij het strand);
- de kijkrichting: de richting loodrecht op de kustlijn, naar zee (land ligt links van
  een OSM-kustlijn, dus zee ligt rechts: richting van de lijn + 90 graden);
- het deiningsvenster: stralen om de 5 graden vanuit een punt net voor de kust;
- de blootstellingsfactor f per golfrichting (om de 10 graden);
- het district en de IPMA-code voor de waarschuwingen;
- de koppeling met de officiële lijst van zwemwateren (EEA/APA).

Schrijft data/beaches/stranden.geojson, onzeker.csv, verslag.json en een steekproef
van 30 stranden in docs/steekproef/.

Alle meetkundige keuzes staan in PARAMS, met hun bewijsniveau (zie PLAN.md 2.3).
"""

from __future__ import annotations

import csv
import json
import math
import random
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

import numpy as np
from pyproj import Transformer
from shapely import STRtree
from shapely.geometry import LineString, Point, box, shape
from shapely.geometry.polygon import orient
from shapely.ops import nearest_points, transform, unary_union
from shapely.prepared import prep

from pipeline.beaches.fetch import FULL_BBOX  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "beaches"
SAMPLE = ROOT / "docs" / "steekproef"

# Eigen keuzes (meetkunde, geen meting). Te ijken in M7.
PARAMS = {
    "max_afstand_kust_m": 300,       # plan 3.3
    "dammen_weg_m": 25,              # land smaller dan 50 m (dammen, pieren, strandhoofden) telt niet
    "kustlijn_straal_m": 400,        # stuk kust rond het strand voor de kijkrichting
    "zekerheid_min": 0.5,            # lengte van de gemiddelde normaalvector (0 tot 1)
    "max_afwijking_venster_graden": 45,  # kijkrichting tegenover het midden van het grootste open venster
    "startpunt_zee_m": 150,          # stralen vertrekken zoveel meter voor de kust
    "straal_stap_graden": 5,
    "straal_lengte_km": 300,
    "open_vanaf_km": 20,             # dichter land telt als afscherming
    "nauw_water_km": 3,              # land recht vooruit binnen deze afstand: baai, lagune of monding
    "sector_halve_breedte_graden": 15,
    "samenvoegen_zelfde_naam_m": 150,
    "eea_koppel_m": 400,
}

# District (naam in OSM) -> code van de IPMA-waarschuwingen (OPEN.md punt 6).
IPMA_AREA = {
    "Viana do Castelo": "VCT", "Braga": "BRG", "Porto": "PTO", "Aveiro": "AVR", "Coimbra": "CBR",
    "Leiria": "LRA", "Lisboa": "LSB", "Setúbal": "STB", "Beja": "BJA", "Faro": "FAR",
    "Santarém": "STM", "Évora": "EVR", "Portalegre": "PTG", "Castelo Branco": "CBO", "Guarda": "GDA",
    "Viseu": "VIS", "Vila Real": "VRL", "Bragança": "BGC",
}

# Vasteland: alles oostelijker dan 10 W en tussen 36,8 en 42,2 N.
MAINLAND = (-10.0, 36.8, -6.0, 42.2)

TO_M = Transformer.from_crs(4326, 3763, always_xy=True).transform     # PT-TM06, meter
TO_LL = Transformer.from_crs(3763, 4326, always_xy=True).transform


def read_seq(path: Path):
    for line in path.read_text().splitlines():
        line = line.lstrip("\x1e").strip()
        if line:
            yield json.loads(line)


def in_mainland(lon: float, lat: float) -> bool:
    return MAINLAND[0] <= lon <= MAINLAND[2] and MAINLAND[1] <= lat <= MAINLAND[3]


def norm_name(s: str | None) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\b(praia|da|de|do|das|dos|a|o)\b", " ", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def bearing(dx: float, dy: float) -> float:
    """Kompasrichting in graden (0 = noord, 90 = oost) van een vector in het raster."""
    return math.degrees(math.atan2(dx, dy)) % 360


def angdiff(a: float, b: float) -> float:
    return (a - b + 180) % 360 - 180


# --- invoer -------------------------------------------------------------------


def chunks(line: LineString, n: int = 64):
    """Lange lijnen in stukken knippen: sneller zoeken in de STRtree."""
    c = list(line.coords)
    for i in range(0, len(c) - 1, n):
        yield LineString(c[i : i + n + 1])


def load_land():
    """Land als veelhoeken in meter, met dammen en pieren smaller dan 2 x r weggefilterd.

    De randen worden zo gericht dat land links ligt (buitenrand tegen de klok in),
    net als bij een OSM-kustlijn. Geeft (land, kustlijnstukken) terug.
    """
    p = RAW / "land_full.geojson"
    if not p.exists():
        return None, [seg for f in read_seq(RAW / "osm_coastline.geojsonseq")
                      if f["geometry"]["type"] == "LineString"
                      for seg in chunks(transform(TO_M, shape(f["geometry"])))]
    r = PARAMS["dammen_weg_m"]
    polys = []
    for f in json.loads(p.read_text())["features"]:
        g = transform(TO_M, shape(f["geometry"])).buffer(-r).buffer(r)
        polys += [x for x in getattr(g, "geoms", [g]) if x.area > 2000]
    # De rand van de uitsnede (FULL_BBOX in fetch.py) is geen kust: die stukken weglaten.
    edge = transform(TO_M, box(*FULL_BBOX).boundary.segmentize(0.01)).buffer(50)
    edge = prep(edge)
    lines = []
    for poly in polys:
        poly = orient(poly, 1.0)
        for ring in [poly.exterior, *poly.interiors]:
            run: list = []
            for q in ring.coords:
                if edge.contains(Point(q)):
                    if len(run) > 1:
                        lines += list(chunks(LineString(run)))
                    run = []
                else:
                    run.append(q)
            if len(run) > 1:
                lines += list(chunks(LineString(run)))
    return unary_union(polys), lines


def load_land_far():
    p = RAW / "land_simplified.geojson"
    if not p.exists():
        return []
    polys = [transform(TO_M, shape(f["geometry"])) for f in json.loads(p.read_text())["features"]]
    # Alleen de randen tellen voor de stralen.
    return [g.boundary for g in polys]


def load_districts():
    p = RAW / "osm_districts.geojson"
    out = []
    if not p.exists():
        return out
    best: dict[str, object] = {}
    for f in json.loads(p.read_text())["features"]:
        name = f["properties"].get("name")
        if name in IPMA_AREA:
            g = transform(TO_M, shape(f["geometry"]))
            # Een concelho kan dezelfde naam hebben als zijn district; het district is het grootste.
            if name not in best or g.area > best[name].area:
                best[name] = g
    return list(best.items())


def load_osm_beaches():
    out = []
    for f in read_seq(RAW / "osm_beaches.geojsonseq"):
        p = f["properties"]
        if p.get("natural") != "beach":
            continue
        g = shape(f["geometry"])
        c = g.representative_point()
        if not in_mainland(c.x, c.y):
            continue
        if f["geometry"]["type"] == "LineString":
            continue  # gesloten lijn: dubbel van de veelhoek
        oid = f"{p['@type']}/{p['@id']}" if "@id" in p else None
        out.append({"osm_id": oid, "naam": p.get("name"), "tags": p,
                    "geom": transform(TO_M, g)})
    return out


def load_eea():
    """Officiële zwemwateren van het vasteland (kust- en overgangswater) uit de recentste EEA-dienst."""
    p = RAW / "eea_bathing_arcgis.json"
    if not p.exists():
        return []
    d = json.loads(p.read_text())

    def year(lyr):
        m = re.search(r"(20\d\d)$", lyr["dienst"])
        return int(m.group(1)) if m else 0

    layers = [lyr for lyr in d["lagen"] if "bathingWaterIdentifier" in lyr["velden"]]
    if not layers:
        return []
    lyr = max(layers, key=lambda x: (year(x), len(x["punten"])))
    out, seen = [], set()
    for r in lyr["punten"]:
        cat = r.get("bwWaterCategory") or ""
        if r.get("countryCode") != "PT" or cat not in ("Coastal", "Transitional"):
            continue
        lon, lat = float(r["longitude"]), float(r["latitude"])
        if not in_mainland(lon, lat) or r["bathingWaterIdentifier"] in seen:
            continue
        seen.add(r["bathingWaterIdentifier"])
        x, y = TO_M(lon, lat)
        out.append({"eea_id": r["bathingWaterIdentifier"], "eea_naam": r.get("bathingWaterName"), "eea_type": cat,
                    "eea_jaar": year(lyr), "geom": Point(x, y)})
    return out


# --- meetkunde ----------------------------------------------------------------


class Coast:
    def __init__(self, lines, far, land=None):
        self.lines = lines
        self.land = prep(land) if land is not None else None
        self.tree = STRtree(lines)
        self.far = far
        self.far_tree = STRtree(far) if far else None

    def nearest(self, g):
        i = self.tree.nearest(g)
        line = self.lines[i]
        p_line, _ = nearest_points(line, g)
        return p_line, line.distance(g)

    def orientation(self, p: Point):
        """Gewogen gemiddelde van de zeewaartse normaal over de kust binnen de straal."""
        r = PARAMS["kustlijn_straal_m"]
        area = p.buffer(r)
        sx = sy = total = 0.0
        for i in self.tree.query(area):
            part = self.lines[i].intersection(area)
            for seg in getattr(part, "geoms", [part]):
                if seg.is_empty or seg.geom_type != "LineString":
                    continue
                c = np.asarray(seg.coords)
                d = np.diff(c, axis=0)
                ln = np.hypot(d[:, 0], d[:, 1])
                # zee ligt rechts van de lijn: normaal = (dy, -dx)
                sx += float(np.sum(d[:, 1]))
                sy += float(np.sum(-d[:, 0]))
                total += float(np.sum(ln))
        if total == 0:
            return None, 0.0
        return bearing(sx, sy), math.hypot(sx, sy) / total

    def ray_distance(self, origin: Point, deg: float) -> float:
        """Afstand tot het eerste land langs een straal, of de straallengte als er geen land is.

        De straal wordt in oplopende stukken bekeken (1, 5, 20, 300 km), zodat een straal
        die vlak bij de kust op land botst niet over heel Iberie gezocht wordt.
        """
        L = PARAMS["straal_lengte_km"] * 1000
        a = math.radians(deg)
        sx, sy = math.sin(a), math.cos(a)

        def seg(d0, d1):
            return LineString([(origin.x + d0 * sx, origin.y + d0 * sy), (origin.x + d1 * sx, origin.y + d1 * sy)])

        prev = 0.0
        for stop in (1000.0, 5000.0, 20000.0, L):
            piece = seg(prev, stop)
            hits = [origin.distance(h) for i in self.tree.query(piece)
                    if not (h := piece.intersection(self.lines[i])).is_empty]
            # De vereenvoudigde landrand pas vanaf 5 km, dichtbij is ze te grof.
            if self.far_tree is not None and stop > 5000:
                far = seg(max(prev, 5000.0), stop)
                hits += [origin.distance(h) for i in self.far_tree.query(far)
                         if not (h := far.intersection(self.far[i])).is_empty]
            if hits:
                return min(hits)
            prev = stop
        return L


def exposure(dist_km: dict[float, float], facing: float) -> list[float]:
    """Blootstellingsfactor f per golfrichting 0, 10, ..., 350 graden (waar de golf vandaan komt).

    f^2 = gemiddelde over de sector rond die richting van [straal open] x cos(hoek met de kijkrichting).
    f^2 is een energiefactor: in de formule van 2.5 staat f^2 * H^2 * T. De cosinus is de
    afname van de energiestroom bij een schuin invallende golf; afbuiging rond kapen telt niet mee.
    """
    step = PARAMS["straal_stap_graden"]
    half = PARAMS["sector_halve_breedte_graden"]
    out = []
    for theta in range(0, 360, 10):
        vals = []
        for k in range(-half, half + 1, step):
            phi = (theta + k) % 360
            is_open = dist_km.get(phi, 0) >= PARAMS["open_vanaf_km"]
            vals.append(is_open * max(0.0, math.cos(math.radians(angdiff(phi, facing)))))
        out.append(round(math.sqrt(sum(vals) / len(vals)), 2))
    return out


def window(dist_km: dict[float, float]) -> list[list[int]]:
    """Aaneengesloten open sectoren als [van, tot] in graden, met de klok mee."""
    step = PARAMS["straal_stap_graden"]
    dirs = sorted(dist_km)
    open_ = [dist_km[d] >= PARAMS["open_vanaf_km"] for d in dirs]
    if all(open_):
        return [[0, 360]]
    if not any(open_):
        return []
    n = len(dirs)
    start = next(i for i in range(n) if not open_[i])  # begin bij een dichte richting
    out, cur = [], None
    for k in range(1, n + 1):
        i = (start + k) % n
        if open_[i] and cur is None:
            cur = [dirs[i], dirs[i]]
        elif open_[i]:
            cur[1] = dirs[i]
        elif cur is not None:
            out.append(cur)
            cur = None
    if cur is not None:
        out.append(cur)
    return [[int(a), int((b + step) % 360) or 360] for a, b in out]


# --- samenvoegen --------------------------------------------------------------


def merge_same_name(beaches):
    """Stukken van hetzelfde strand (zelfde naam, minder dan 150 m uit elkaar) samenvoegen."""
    groups = defaultdict(list)
    named = []
    for b in beaches:
        (groups[norm_name(b["naam"])] if b["naam"] else named).append(b)
    out = list(named)  # onbenoemde blijven apart
    lim = PARAMS["samenvoegen_zelfde_naam_m"]
    for items in groups.values():
        parent = list(range(len(items)))

        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                if items[i]["geom"].distance(items[j]["geom"]) < lim:
                    parent[find(i)] = find(j)
        clusters = defaultdict(list)
        for i, b in enumerate(items):
            clusters[find(i)].append(b)
        for c in clusters.values():
            if len(c) == 1:
                out.append(c[0])
                continue
            out.append({"osm_id": c[0]["osm_id"], "osm_ids": [b["osm_id"] for b in c], "naam": c[0]["naam"],
                        "tags": c[0]["tags"], "geom": unary_union([b["geom"] for b in c])})
    return out


# --- hoofdlijn ----------------------------------------------------------------


def analyse(coast: Coast, districts, item: dict) -> dict:
    # Het kustpunt bij het midden van het strand, niet het dichtste punt van de hele omtrek:
    # dat laatste kan een uiteinde tegen een dam of rots zijn (zo kreeg Matosinhos eerst 183°).
    _, dist = coast.nearest(item["geom"])
    p, _ = coast.nearest(item["geom"].representative_point())
    facing, conf = coast.orientation(p)
    reasons = []
    if facing is None:
        reasons.append("geen kustlijn in de buurt")
        facing = 0.0
    if conf < PARAMS["zekerheid_min"]:
        reasons.append(f"kustlijn kronkelt (zekerheid {conf:.2f})")
    s = PARAMS["startpunt_zee_m"]
    a = math.radians(facing)
    origin = Point(p.x + s * math.sin(a), p.y + s * math.cos(a))
    if coast.land is not None and coast.land.contains(origin):
        reasons.append("punt voor de kust ligt op land")
    step = PARAMS["straal_stap_graden"]
    dist_km = {d: coast.ray_distance(origin, d) / 1000 for d in range(0, 360, step)}
    ahead = min(dist_km[round(facing / step) * step % 360], dist_km[(round(facing / step) * step + step) % 360])
    narrow = ahead < PARAMS["nauw_water_km"]
    if narrow:
        reasons.append(f"land recht vooruit op {ahead:.1f} km (baai, lagune of monding)")
    win = window(dist_km)
    if not win:
        reasons.append("geen open deiningsvenster")
    else:
        a0, b0 = max(win, key=lambda w: (w[1] - w[0]) % 360 or 360)
        mid = (a0 + ((b0 - a0) % 360 or 360) / 2) % 360
        dev = abs(angdiff(facing, mid))
        if dev > PARAMS["max_afwijking_venster_graden"] and not narrow:
            reasons.append(f"kijkrichting wijkt {dev:.0f}° af van het open water")
    # District: het district dat het strand zelf bevat, anders het dichtste binnen 300 m
    # (een punt kan net in zee liggen). Een Spaans strand aan een grensrivier valt zo weg.
    rp = item["geom"].representative_point()
    district = next((name for name, poly in districts if poly.contains(rp)), None)
    if district is None:
        dists = sorted((poly.distance(rp), name) for name, poly in districts)
        # Een officieel Portugees zwemwater krijgt altijd het dichtste district.
        if dists and (dists[0][0] < 300 or item.get("eea")):
            district = dists[0][1]
    lon, lat = TO_LL(p.x, p.y)
    return {
        "punt": (round(lon, 6), round(lat, 6)),
        "afstand_kust_m": round(dist),
        "kijkrichting": round(facing),
        "richting_zekerheid": round(conf, 2),
        "venster": win,
        "afstand_land_km": {str(d): round(v, 1) for d, v in dist_km.items()},
        "blootstelling": exposure(dist_km, facing),
        "district": district,
        "ipma_area": IPMA_AREA.get(district),
        "kandidaat_besloten_water": narrow,
        "onzeker": bool(reasons),
        "redenen": reasons,
    }


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    land, lines = load_land()
    coast = Coast(lines, load_land_far(), land)
    districts = load_districts()
    osm_all = load_osm_beaches()
    eea = load_eea()

    near, skipped = [], defaultdict(list)
    for b in osm_all:
        if not b["naam"]:
            continue
        if re.search(r"fluvial", b["naam"], re.I):
            skipped["rivierstrand (naam bevat 'fluvial')"].append(b["naam"])
            continue
        _, d = coast.nearest(b["geom"])
        if d <= PARAMS["max_afstand_kust_m"]:
            near.append(b)
    beaches = merge_same_name(near)

    # Koppeling met EEA: elk officieel zwemwater aan het dichtste OSM-strand, anders toevoegen.
    tree = STRtree([b["geom"] for b in beaches])
    unnamed_tree_items = [b for b in osm_all if not b["naam"]]
    unnamed_tree = STRtree([b["geom"] for b in unnamed_tree_items]) if unnamed_tree_items else None
    added = []
    for e in eea:
        i = tree.nearest(e["geom"])
        if beaches[i]["geom"].distance(e["geom"]) <= PARAMS["eea_koppel_m"]:
            beaches[i].setdefault("eea", []).append(e)
            continue
        base = {"osm_id": None, "naam": e["eea_naam"], "tags": {}, "geom": e["geom"], "eea": [e], "bron": "eea"}
        if unnamed_tree is not None:
            j = unnamed_tree.nearest(e["geom"])
            u = unnamed_tree_items[j]
            if u["geom"].distance(e["geom"]) <= PARAMS["eea_koppel_m"]:
                base |= {"osm_id": u["osm_id"], "geom": u["geom"], "bron": "eea+osm zonder naam"}
        added.append(base)
    beaches += added

    features, uncertain = [], []
    for b in beaches:
        a = analyse(coast, districts, b)
        if a["district"] is None:
            skipped["buiten Portugal (in geen enkel district)"].append(b["naam"])
            continue
        e = b.get("eea", [])
        if b.get("bron") == "eea" and a["afstand_kust_m"] > PARAMS["max_afstand_kust_m"]:
            a["redenen"].append(f"officieel zwemwater op {a['afstand_kust_m']} m van de OSM-kustlijn")
            a["onzeker"] = True
        if any(re.search("transit|transi", x["eea_type"], re.I) for x in e):
            a["redenen"].append("overgangswater (monding of lagune) volgens EEA")
            a["onzeker"] = True
        osm_id = b.get("osm_id")
        fid = osm_id or (f"eea/{e[0]['eea_id']}" if e else f"punt/{a['punt'][1]:.5f},{a['punt'][0]:.5f}")
        props = {
            "id": fid,
            "naam": b["naam"] or (e[0]["eea_naam"] if e else None),
            "osm_ids": b.get("osm_ids") or ([osm_id] if osm_id else []),
            "eea_ids": [x["eea_id"] for x in e],
            "eea_namen": [x["eea_naam"] for x in e],
            "eea_type": sorted({x["eea_type"] for x in e}),
            "bron": b.get("bron", "osm"),
            **{k: v for k, v in a.items() if k != "punt"},
            "besloten_water": False,
            "getij_voorkeur": None,
        }
        features.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": a["punt"]},
                         "properties": props})
        if props["onzeker"]:
            uncertain.append(props | {"lon": a["punt"][0], "lat": a["punt"][1]})

    features.sort(key=lambda f: (-f["geometry"]["coordinates"][1], f["geometry"]["coordinates"][0]))
    fc = {
        "type": "FeatureCollection",
        "licentie": "ODbL 1.0, © OpenStreetMap-bijdragers; zwemwateren: EEA/APA (CC BY 4.0)",
        "bron": "pipeline/beaches/build.py",
        "parameters": PARAMS,
        "features": features,
    }
    (OUT / "stranden.geojson").write_text(json.dumps(fc, ensure_ascii=False, indent=0) + "\n")

    with open(OUT / "onzeker.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "naam", "lat", "lon", "kijkrichting", "zekerheid", "redenen", "google_maps"])
        for u in sorted(uncertain, key=lambda u: -u["lat"]):
            w.writerow([u["id"], u["naam"], u["lat"], u["lon"], u["kijkrichting"], u["richting_zekerheid"],
                        "; ".join(u["redenen"]), f"https://www.google.com/maps/@{u['lat']},{u['lon']},17z/data=!3m1!1e3"])

    eea_found = {i for f in features for i in f["properties"]["eea_ids"]}
    report = {
        "osm_stranden_vasteland": len(osm_all),
        "osm_met_naam_bij_kust": len(near),
        "na_samenvoegen": len(beaches) - len(added),
        "eea_kustzwemwateren": len(eea),
        "eea_gekoppeld_aan_osm": len(eea) - len(added),
        "eea_toegevoegd": len(added),
        "eea_niet_teruggevonden": sorted(str(e["eea_id"]) for e in eea if e["eea_id"] not in eea_found),
        "stranden_totaal": len(features),
        "onzeker": len(uncertain),
        "kandidaat_besloten_water": sum(f["properties"]["kandidaat_besloten_water"] for f in features),
        "weggelaten": {k: sorted(set(v)) for k, v in skipped.items()},
    }
    per = defaultdict(int)
    for f in features:
        per[f["properties"]["district"] or "?"] += 1
    report["per_district"] = dict(sorted(per.items()))
    (OUT / "verslag.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "eea_niet_teruggevonden"}, ensure_ascii=False))

    sample(features, coast, osm_all)


def sample(features, coast: Coast, osm_all, n: int = 30):
    """Steekproef van 30 stranden, verspreid over de kust, als kaartjes zonder achtergrondtegels."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    SAMPLE.mkdir(parents=True, exist_ok=True)
    rnd = random.Random(2026)
    srt = sorted(features, key=lambda f: f["geometry"]["coordinates"][1])
    # Gelijk verdeeld langs de kust (op breedtegraad), met een vast zaad.
    chunks = np.array_split(np.arange(len(srt)), n)
    picks = [srt[rnd.choice(list(c))] for c in chunks if len(c)]
    by_id = {b["osm_id"]: b for b in osm_all}
    fig, axes = plt.subplots(6, 5, figsize=(20, 24))
    rows = []
    for k, (ax, f) in enumerate(zip(axes.flat, picks, strict=False), start=1):
        p = f["properties"]
        lon, lat = f["geometry"]["coordinates"]
        x, y = TO_M(lon, lat)
        R = 2500
        box_ = Point(x, y).buffer(R, cap_style=3)
        for i in coast.tree.query(box_):
            part = coast.lines[i].intersection(box_)
            for seg in getattr(part, "geoms", [part]):
                if not seg.is_empty and seg.geom_type == "LineString":
                    xs, ys = seg.xy
                    ax.plot(xs, ys, color="#555", lw=1)
        for oid in p["osm_ids"]:
            g = by_id.get(oid, {}).get("geom")
            if g is not None and g.geom_type in ("Polygon", "MultiPolygon"):
                for poly in getattr(g, "geoms", [g]):
                    ax.fill(*poly.exterior.xy, color="#e8c46a", alpha=0.8)
        # stralen: blauw open, grijs dicht (kort getekend)
        for d, km in p["afstand_land_km"].items():
            a = math.radians(float(d))
            L = min(km * 1000, R)
            ax.plot([x, x + L * math.sin(a)], [y, y + L * math.cos(a)],
                    color="#2a7fff" if km >= PARAMS["open_vanaf_km"] else "#ccc", lw=0.6)
        a = math.radians(p["kijkrichting"])
        ax.annotate("", xy=(x + 1500 * math.sin(a), y + 1500 * math.cos(a)), xytext=(x, y),
                    arrowprops=dict(arrowstyle="-|>", color="#d0021b", lw=2))
        ax.plot([x], [y], "o", color="#d0021b", ms=4)
        ax.set_xlim(x - R, x + R)
        ax.set_ylim(y - R, y + R)
        ax.set_aspect("equal")
        ax.set_xticks([])
        ax.set_yticks([])
        flag = " ⚠" if p["onzeker"] else ""
        ax.set_title(f"{k}. {p['naam'] or '?'}{flag}\nkijkt naar {p['kijkrichting']}°", fontsize=10)
        rows.append((k, p, lat, lon))
    for ax in list(axes.flat)[len(picks):]:
        ax.axis("off")
    fig.suptitle("Steekproef: rood = kijkrichting, blauw = open zee, grijs = land binnen 20 km. "
                 "Elk vak is 5 x 5 km, noord boven.", fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(SAMPLE / "steekproef.png", dpi=80)
    plt.close(fig)

    lines = ["# Steekproef van 30 stranden", "",
             "Bekijk `steekproef.png`. Klopt de rode pijl (de richting waarin het strand naar zee kijkt)?",
             "Klik op de link om het strand in satellietbeeld te zien.", "",
             "| # | Strand | Kijkt naar | Venster (open zee) | Onzeker | Kaart |", "|---|---|---|---|---|---|"]
    for k, p, lat, lon in rows:
        win = ", ".join(f"{a}–{b}°" for a, b in p["venster"]) or "geen"
        lines.append(f"| {k} | {p['naam']} | {p['kijkrichting']}° ({compass(p['kijkrichting'])}) | {win} | "
                     f"{'; '.join(p['redenen']) or 'nee'} | "
                     f"[kaart](https://www.google.com/maps/@{lat},{lon},16z/data=!3m1!1e3) |")
    (SAMPLE / "README.md").write_text("\n".join(lines) + "\n")


def compass(deg: float) -> str:
    names = ["N", "NNO", "NO", "ONO", "O", "OZO", "ZO", "ZZO", "Z", "ZZW", "ZW", "WZW", "W", "WNW", "NW", "NNW"]
    return names[round(deg / 22.5) % 16]


if __name__ == "__main__":
    build()
