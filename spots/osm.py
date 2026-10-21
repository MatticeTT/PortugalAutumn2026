"""Surfspots en bodemkenmerken uit OpenStreetMap via Overpass (ODbL)."""

from __future__ import annotations

import json
import time
from pathlib import Path

import requests

OVERPASS = "https://overpass-api.de/api/interpreter"

VRAAG_SPOTS = """
[out:json][timeout:900];
nwr["sport"="surfing"];
out tags center bb;
"""


def overpass(vraag: str, pogingen: int = 4) -> dict:
    for p in range(pogingen):
        r = requests.post(OVERPASS, data={"data": vraag}, timeout=1000,
                          headers={"User-Agent": "surfkaart (github.com/MatticeTT/PortugalAutumn2026)"})
        if r.status_code == 200:
            return r.json()
        time.sleep(2 ** (p + 1) * 5)
    r.raise_for_status()
    raise RuntimeError("Overpass gaf geen antwoord")


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
