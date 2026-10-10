"""Klimplekken uit de bronnen halen en samenvoegen (eigenaar, 7 oktober 2026). Verzint niets: elk punt,
elke ligging en elke graad komt uit een bron.

Bron 1 OpenStreetMap (data/klim/bron_osm.json), bron 2 Camptocamp (data/klim/bron_c2c.json),
bron 3 eigen invoer (data/klim/eigen.csv; gaat altijd voor).
"""

from __future__ import annotations

import csv
import difflib
import json
import math
import re
import unicodedata
from pathlib import Path

from pipeline.klim import graden as G

ROOT = Path(__file__).resolve().parents[2]
MAP = ROOT / "data" / "klim"
PRECISIE = {"eigen": 3, "bereik": 2, "omgerekend": 1, None: 0}


# ---- OpenStreetMap ----------------------------------------------------------------------------------

def _ja(t: dict, k: str) -> bool:
    return k in t and t[k] != "no"


def disciplines(t: dict) -> list[str]:
    d = []
    if t.get("climbing") == "boulder" or _ja(t, "climbing:boulder"):
        d.append("boulder")
    if _ja(t, "climbing:sport"):
        d.append("sport")
    if _ja(t, "climbing:trad"):
        d.append("trad")
    return d or ["onbekend"]


def soort(t: dict) -> str:
    c = t.get("climbing")
    return {"area": "gebied", "crag": "gebied", "boulder": "boulder", "route_bottom": "route",
            "route": "route"}.get(c, "onbekend")


def aantal_routes(t: dict) -> int | None:
    for k in ("climbing:routes", "climbing:sport", "climbing:boulder"):
        v = (t.get(k) or "").strip()
        if v.isdigit():
            return int(v)
    return None


def _graad_uit(t: dict, schaal: str) -> dict | None:
    """Graad op één schaal ("frans" of "font"), in volgorde van voorkeur:
    1 de graad van de route zelf, 2 het bereik min–max, 4 omgerekend uit UIAA/YDS (frans) of V (font).
    Het gemiddelde (:mean) komt er alleen bij als extra."""
    lees = G.frans if schaal == "frans" else G.font
    sleutel = "french" if schaal == "frans" else "font"
    uit = None
    eigen = lees(t.get(f"climbing:grade:{sleutel}"))
    if eigen:
        lo, hi = G.bereik(eigen[0])
        uit = {"min": lo, "max": hi, "soort": "omgerekend" if eigen[1] else "eigen"}
    else:
        lo = lees(t.get(f"climbing:grade:{sleutel}:min"))
        hi = lees(t.get(f"climbing:grade:{sleutel}:max"))
        if lo or hi:
            alle = (lo[0] if lo else []) + (hi[0] if hi else [])
            a, b = G.bereik(alle)
            uit = {"min": a if lo else None, "max": b if hi else None,
                   "soort": "omgerekend" if (lo and lo[1]) or (hi and hi[1]) else "bereik"}
    if uit is None:
        andere = (("uiaa", G.uiaa), ("yds_class", G.yds), ("yds", G.yds)) if schaal == "frans" else \
                 (("hueco", G.vscale_alias()), ("vscale", G.vschaal), ("v", G.vschaal))
        for k, f in andere:
            vals = [f(t.get(f"climbing:grade:{k}{s}")) for s in ("", ":min", ":max")]
            vals = [v for v in vals if v]
            if vals:
                lo, hi = G.bereik([g for v in vals for g in v[0]])
                uit = {"min": lo, "max": hi, "soort": "omgerekend"}
                break
    gem = lees(t.get(f"climbing:grade:{sleutel}:mean"))
    if gem and uit:
        uit["gemiddeld"] = gem[0][0]
    if uit and any(G.romeins(g or "") for g in (uit["min"], uit["max"])):
        uit["romeins"] = True  # zoals in de bron, niet omgerekend
    return uit


def heeft_graad(t: dict) -> bool:
    return any(k.startswith("climbing:grade:") for k in t)


def overgeslagen(t: dict) -> bool:
    if t.get("leisure") == "sports_centre" or t.get("indoor") == "yes" or "building" in t:
        return True
    if t.get("climbing") == "bolt":
        return True
    return not t.get("name") and not heeft_graad(t)


def uit_osm(data: dict) -> list[dict]:
    uit = []
    for e in data.get("elementen", []):
        t = e.get("tags", {})
        if overgeslagen(t):
            continue
        midden = e if "lat" in e else e.get("center", {})
        lat, lon = midden.get("lat"), midden.get("lon")
        if lat is None:
            continue
        d = disciplines(t)
        frans, font = _graad_uit(t, "frans"), _graad_uit(t, "font")
        uit.append(plek(
            naam=t.get("name"), lat=lat, lon=lon, soort=soort(t), disciplines=d, routes=aantal_routes(t),
            frans=frans, font=font, rots=t.get("climbing:rock"), richting=t.get("climbing:orientation"),
            bron={"bron": "OpenStreetMap", "id": f"{e['type']}/{e['id']}",
                  "link": f"https://www.openstreetmap.org/{e['type']}/{e['id']}", "datum": data.get("opgehaald")}))
    return uit


# ---- samen --------------------------------------------------------------------------------------------

def plek(*, naam, lat, lon, soort, disciplines, routes, frans, font, rots=None, richting=None, bron) -> dict:
    """Eén plek. De getoonde graad: Font als het alleen boulderen is, anders Frans (nooit gemengd)."""
    alleen_boulder = disciplines == ["boulder"]
    g = font if alleen_boulder else frans
    return {"id": bron["id"], "naam": naam, "lat": round(lat, 6), "lon": round(lon, 6), "soort": soort,
            "disciplines": disciplines, "routes": routes, "schaal": "font" if alleen_boulder else "frans",
            "graad": g, "frans": frans, "font": font, "rots": rots, "richting": richting, "bronnen": [bron]}


def _naam(s: str | None) -> str:
    s = unicodedata.normalize("NFD", s or "").encode("ascii", "ignore").decode().lower()
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", s).split())


def gelijke_naam(a: str | None, b: str | None) -> bool:
    """Namen die sterk op elkaar lijken (accenten en hoofdletters tellen niet)."""
    x, y = _naam(a), _naam(b)
    if not x or not y:
        return False
    return x == y or x in y or y in x or difflib.SequenceMatcher(None, x, y).ratio() >= 0.85


def afstand_m(a: dict, b: dict) -> float:
    r = 6371000
    p1, p2 = math.radians(a["lat"]), math.radians(b["lat"])
    dp, dl = p2 - p1, math.radians(b["lon"] - a["lon"])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def _precisie(p: dict) -> int:
    return PRECISIE[(p.get("graad") or {}).get("soort")]


def samenvoegen(lijsten: list[list[dict]]) -> list[dict]:
    """Binnen 150 m en met sterk gelijkende namen = dezelfde plek: de preciesste graad blijft, alle
    bronnen worden bewaard. Eerdere lijsten gaan voor bij gelijke precisie."""
    uit: list[dict] = []
    for lijst in lijsten:
        for p in lijst:
            gelijk = next((q for q in uit if afstand_m(p, q) <= 150 and gelijke_naam(p["naam"], q["naam"])), None)
            if gelijk is None:
                uit.append(p)
                continue
            if _precisie(p) > _precisie(gelijk):
                for k in ("graad", "frans", "font", "schaal"):
                    gelijk[k] = p[k]
            for k in ("routes", "rots", "richting"):
                gelijk[k] = gelijk[k] or p[k]
            gelijk["disciplines"] = sorted(set(gelijk["disciplines"] + p["disciplines"]) - {"onbekend"}) or ["onbekend"]
            gelijk["bronnen"] += p["bronnen"]
    return uit


# ---- bron 2: Camptocamp ----------------------------------------------------------------------------------
# Veldnamen zoals in de JSON van api.camptocamp.org/waypoints/{id} (nagekeken op 7 oktober 2026):
# locales[].title, geometry.geom (GeoJSON-tekst in EPSG:3857), climbing_rating_min/max/median,
# routes_quantity, climbing_outdoor_types (single, multi, bloc, psicobloc), rock_types.

C2C_ROTS = {"calcaire": "limestone", "granit": "granite", "gres": "sandstone", "gneiss": "gneiss",
            "quartzite": "quartzite", "basalte": "basalt", "conglomerat": "conglomerate", "schiste": "schist"}


def mercator_naar_wgs84(x: float, y: float) -> tuple[float, float]:
    """EPSG:3857 naar (lat, lon) in graden."""
    r = 6378137.0
    return math.degrees(2 * math.atan(math.exp(y / r)) - math.pi / 2), math.degrees(x / r)


def uit_c2c(data: dict) -> list[dict]:
    uit = []
    for d in data.get("documenten", []):
        try:
            x, y = json.loads(d["geometry"]["geom"])["coordinates"][:2]
        except (KeyError, TypeError, ValueError):
            continue
        lat, lon = mercator_naar_wgs84(x, y)
        titels = {loc.get("lang"): loc.get("title") for loc in d.get("locales", [])}
        naam = titels.get("pt") or titels.get("en") or titels.get("fr") or next(iter(titels.values()), None)
        types = d.get("climbing_outdoor_types") or []
        # Alleen "bloc" zegt iets over de discipline (boulder); single/multi (één of meer touwlengtes)
        # zeggen niet of het sport of trad is: dan onbekend.
        disc = ["boulder"] if "bloc" in types else []
        disc = disc or ["onbekend"]
        lo = G.frans(d.get("climbing_rating_min"))
        hi = G.frans(d.get("climbing_rating_max"))
        frans = None
        if lo or hi:
            alle = (lo[0] if lo else []) + (hi[0] if hi else [])
            a, b = G.bereik(alle)  # ook als min en max in de bron omgewisseld staan
            frans = {"min": a if lo else None, "max": b if hi else None, "soort": "bereik"}
            mediaan = G.frans(d.get("climbing_rating_median"))
            if mediaan:
                frans["gemiddeld"] = mediaan[0][0]
        rots = ";".join(C2C_ROTS.get(r, r) for r in (d.get("rock_types") or [])) or None
        did = d["document_id"]
        uit.append(plek(
            naam=naam, lat=lat, lon=lon, soort="gebied", disciplines=disc, routes=d.get("routes_quantity"),
            frans=frans, font=None, rots=rots, richting=None,
            bron={"bron": "Camptocamp", "id": f"c2c/{did}", "link": f"https://www.camptocamp.org/waypoints/{did}",
                  "datum": data.get("opgehaald")}))
    return uit


# Andere landen (data/klim/<land>/): zelfde bronnen en dezelfde verwerking; alleen het vasteland, zoals
# bij de stranden (zonder de Balearen en Corsica).
ANDERE_LANDEN = ("es", "fr", "be", "nl")


def vasteland(land: str, lon: float, lat: float) -> bool:
    if land == "es":
        return not (lat < 40.5 and lon > 0.5) and lat >= 35.95
    if land == "fr":
        return lon <= 8.0
    return True


def alle() -> list[dict]:
    lijsten = []
    for naam, functie in (("osm", uit_osm), ("c2c", uit_c2c)):
        pad = MAP / f"bron_{naam}.json"
        if pad.exists():
            lijsten.append(functie(json.loads(pad.read_text())))
    uit = eigen_voor(samenvoegen(lijsten), eigen())
    gezien = {q["id"] for q in uit}
    for land in ANDERE_LANDEN:
        lijsten = []
        for naam, functie in (("osm", uit_osm), ("c2c", uit_c2c)):
            pad = MAP / land / f"bron_{naam}.json"
            if pad.exists():
                lijsten.append(functie(json.loads(pad.read_text())))
        for q in samenvoegen(lijsten):
            if q["id"] not in gezien and vasteland(land, q["lon"], q["lat"]):
                gezien.add(q["id"])
                uit.append(q | {"land": land})
    return uit


# Bron 2 en 3 hieronder.

# ---- bron 3: eigen invoer --------------------------------------------------------------------------------

EIGEN_KOLOMMEN = ["naam", "lat", "lon", "discipline", "graad_min", "graad_max", "bron"]
# Mag er ook in staan: schaal (Frans/Font), aantal_routes (getal of tekst zoals "25-50"),
# omgerekend ("ja ..." = de bron gaf een andere schaal), bron_url, let_op (waarschuwing, bv. toegang).


def eigen_plek(r: dict, nr: int) -> dict | None:
    """Een rij uit de eigen import (CSV of GeoJSON-eigenschappen). Onleesbare rijen vallen weg."""
    try:
        lat, lon = float(str(r["lat"]).replace(",", ".")), float(str(r["lon"]).replace(",", "."))
    except (KeyError, ValueError):
        return None
    disc = [d.strip() for d in re.split(r"[;,/ ]+", (r.get("discipline") or "").lower()) if d.strip()]
    disc = [d for d in disc if d in ("sport", "boulder", "trad")] or ["onbekend"]
    schaal = (r.get("schaal") or "").strip().lower()
    font = schaal == "font" or (not schaal and disc == ["boulder"])
    lees = G.font if font else G.frans
    lo, hi = lees(r.get("graad_min")), lees(r.get("graad_max"))
    graad = None
    if lo or hi:
        om = (r.get("omgerekend") or "").strip().lower().startswith("ja")
        graad = {"min": lo[0][0] if lo else None, "max": hi[0][-1] if hi else None,
                 "soort": "omgerekend" if om else "eigen"}
        if om:
            graad["toelichting"] = r["omgerekend"].strip()
        if any(G.romeins(g or "") for g in (graad["min"], graad["max"])):
            graad["romeins"] = True  # zoals in de bron, niet omgerekend
    routes = (r.get("aantal_routes") or "").strip() or None
    if routes and routes.isdigit():
        routes = int(routes)
    bron = (r.get("bron") or "").strip()
    sleutel = _naam(r.get("naam")).replace(" ", "-") or str(nr)  # vaste id: het weer blijft bij de juiste plek
    p = plek(naam=r.get("naam") or None, lat=lat, lon=lon, soort="onbekend", disciplines=disc, routes=routes,
             frans=None if font else graad, font=graad if font else None,
             bron={"bron": "eigen invoer" + (f" ({bron})" if bron else ""), "id": f"eigen/{sleutel}",
                   "link": (r.get("bron_url") or "").strip() or None, "datum": None})
    p["schaal"] = "font" if font else "frans"
    p["graad"] = graad
    p["eigen"] = True
    p["let_op"] = (r.get("let_op") or "").strip() or None
    return p


def eigen() -> list[dict]:
    rijen = []
    if (MAP / "eigen.csv").exists():
        with open(MAP / "eigen.csv", newline="", encoding="utf-8-sig") as f:
            rijen += list(csv.DictReader(f))
    if (MAP / "eigen.geojson").exists():
        for ft in json.loads((MAP / "eigen.geojson").read_text()).get("features", []):
            lon, lat = ft["geometry"]["coordinates"][:2]
            rijen.append({**ft.get("properties", {}), "lat": lat, "lon": lon})
    uit, gezien = [], set()
    for k, r in enumerate(rijen):
        p = eigen_plek(r, k)
        if p is None:
            continue
        if p["id"] in gezien:  # zelfde naam twee keer: volgnummer erbij, zodat het weer bij de juiste plek blijft
            p["id"] = p["bronnen"][0]["id"] = f"{p['id']}-{k}"
        gezien.add(p["id"])
        uit.append(p)
    return uit


def eigen_voor(plekken: list[dict], eigen_lijst: list[dict]) -> list[dict]:
    """Eigen invoer gaat altijd voor: een overeenkomende plek uit bron 1 of 2 (150 m en gelijke naam) krijgt
    de eigen gegevens; die bronnen blijven vermeld. Anders komt de eigen plek erbij. Eigen plekken worden
    niet met elkaar samengevoegd (bv. "Santo Tirso (boulder)" en "Santo Tirso (routes)" blijven twee)."""
    bronnen = list(plekken)
    for e in eigen_lijst:
        q = next((q for q in bronnen if afstand_m(e, q) <= 150 and gelijke_naam(e["naam"], q["naam"])), None)
        if q is None:
            plekken.append(e)
            continue
        for k in ("naam", "lat", "lon", "disciplines", "schaal", "graad", "frans", "font", "routes", "let_op"):
            if e.get(k) not in (None, ["onbekend"]):
                q[k] = e[k]
        q["bronnen"] = e["bronnen"] + q["bronnen"]
        q["eigen"] = True
        bronnen.remove(q)  # één eigen rij per plek uit de bronnen
    return plekken
