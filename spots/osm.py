"""Surfspots en bodemkenmerken uit OpenStreetMap via Overpass (ODbL)."""

from __future__ import annotations

import json
import time
from pathlib import Path

import requests

SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]
UA = {"User-Agent": "surfkaart (github.com/MatticeTT/PortugalAutumn2026)"}

VRAAG_SPOTS = """
[out:json][timeout:900];
nwr["sport"="surfing"];
out tags center bb;
"""


def overpass(vraag: str, pogingen: int = 8) -> dict:
    """Vraag aan Overpass; bij storing wachten en de volgende server proberen."""
    fout = None
    for p in range(pogingen):
        url = SERVERS[p % len(SERVERS)]
        try:
            r = requests.post(url, data={"data": vraag}, timeout=1000, headers=UA)
            if r.status_code == 200:
                return r.json()
            fout = f"{url}: {r.status_code}"
        except (requests.RequestException, ValueError) as e:
            fout = f"{url}: {e}"
        print(f"Overpass-poging {p + 1} mislukt ({fout})", flush=True)
        time.sleep(min(30 * (p + 1), 180))
    raise RuntimeError(f"Overpass gaf geen antwoord na {pogingen} pogingen: {fout}")


def haal_spots(uit: Path) -> dict:
    data = overpass(VRAAG_SPOTS)
    uit.write_text(json.dumps(data))
    return data


def haal_buurt(spots: list[dict], straal_m: int, uit: Path, blok: int = 150) -> list[dict]:
    """Stranden en riffen binnen straal_m van elke spot, per blok spots."""
    gevonden: dict[str, dict] = {}
    for i in range(0, len(spots), blok):
        delen = "".join(
            f'nwr(around:{straal_m},{s["lat"]:.6f},{s["lon"]:.6f})["natural"~"^(beach|reef)$"];'
            for s in spots[i:i + blok]
        )
        data = overpass(f"[out:json][timeout:300];({delen});out tags geom;")
        for el in data["elements"]:
            gevonden[f'{el["type"]}/{el["id"]}'] = el
    lijst = list(gevonden.values())
    uit.write_text(json.dumps({"elements": lijst}))
    return lijst


class NietKlaar(Exception):
    """De tijd is op; de opgehaalde vakken staan bewaard, een volgende run doet verder."""


def haal_kust(punten: list[tuple[float, float]], bereik_km: float, map_: Path, tot: float | None = None) -> list:
    """OSM-kustlijn (natural=coastline) rond de spots, per vak van 1 graad, met marge 'bereik_km'.

    Elk vak wordt bewaard in map_, zodat een herstart niet alles opnieuw vraagt.
    Geeft de lijnen terug (lon/lat), in de OSM-richting: land links.
    """
    import math
    import shapely

    map_.mkdir(parents=True, exist_ok=True)
    vakken = sorted({(math.floor(lat), math.floor(lon)) for lon, lat in punten})
    lijnen, gezien = [], set()
    for n, (la, lo) in enumerate(vakken, 1):
        bestand = map_ / f"kust_{la}_{lo}.json"
        if bestand.exists():
            data = json.loads(bestand.read_text())
        else:
            if tot is not None and time.time() > tot:
                klaar = sum(1 for v in vakken if (map_ / f"kust_{v[0]}_{v[1]}.json").exists())
                raise NietKlaar(f"{klaar} van {len(vakken)} kustvakken opgehaald")
            mlat = bereik_km / 111.0 + 0.05
            mlon = bereik_km / (111.0 * max(math.cos(math.radians(la + 0.5)), 0.05)) + 0.05
            s, w = max(la - mlat, -90), lo - mlon
            n_, e = min(la + 1 + mlat, 90), lo + 1 + mlon
            dozen = []
            if w < -180:
                dozen += [(s, w + 360, n_, 180), (s, -180, n_, e)]
            elif e > 180:
                dozen += [(s, w, n_, 180), (s, -180, n_, e - 360)]
            else:
                dozen.append((s, w, n_, e))
            delen = "".join(f'way["natural"="coastline"]({a:.4f},{b:.4f},{c:.4f},{d:.4f});' for a, b, c, d in dozen)
            data = overpass(f"[out:json][timeout:600];({delen});out geom;")
            bestand.write_text(json.dumps(data))
            print(f"kust {n}/{len(vakken)}: vak {la},{lo}: {len(data['elements'])} lijnen", flush=True)
        for el in data["elements"]:
            if el["id"] in gezien or "geometry" not in el:
                continue
            gezien.add(el["id"])
            c = [(p["lon"], p["lat"]) for p in el["geometry"]]
            if len(c) >= 2:
                lijnen.append(shapely.LineString(c))
    return lijnen


def vorm(el: dict):
    """Shapely-vorm (lon/lat) van een Overpass-element met 'out geom'."""
    import shapely

    if el["type"] == "node":
        return shapely.Point(el["lon"], el["lat"])
    if el["type"] == "way" and "geometry" in el:
        c = [(p["lon"], p["lat"]) for p in el["geometry"]]
        if len(c) >= 4 and c[0] == c[-1]:
            return shapely.Polygon(c)
        return shapely.LineString(c) if len(c) >= 2 else shapely.Point(c[0])
    lijnen = []
    for m in el.get("members", []):
        g = m.get("geometry")
        if g and len(g) >= 2:
            lijnen.append([(p["lon"], p["lat"]) for p in g])
    if lijnen:
        poly = shapely.polygonize([shapely.LineString(l) for l in lijnen])
        return poly if not poly.is_empty else shapely.MultiLineString(lijnen)
    return None


def punt(el: dict) -> tuple[float, float] | None:
    if "lat" in el:
        return el["lon"], el["lat"]
    if "center" in el:
        return el["center"]["lon"], el["center"]["lat"]
    return None
