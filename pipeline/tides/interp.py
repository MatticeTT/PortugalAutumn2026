"""M2: getij langs de kust tussen de peilstations.

Elk punt (strand of haven) krijgt een plaats op een lijn langs de kust, van Caminha tot
Vila Real de Santo António. Tussen twee stations worden de tijd en de hoogte van elk
hoog- en laagwater lineair verdeeld volgens die plaats (PLAN.md 3.2, stap 3).
Voorbij het laatste station (ten oosten van Lagos, ten noorden van Viana) geldt het
dichtste station.
"""

from __future__ import annotations

import json
from bisect import bisect_left
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import LineString, Point

ROOT = Path(__file__).resolve().parents[2]
STATIONS_FILE = ROOT / "data" / "tides" / "stations.json"
TO_M = Transformer.from_crs(4326, 3763, always_xy=True).transform

# Lijn langs de kust, van noord naar zuid en dan oost (lon, lat). Grof; dient alleen
# om stranden en stations te ordenen.
SPINE = [
    (-8.87, 41.87), (-8.84, 41.69), (-8.70, 41.19), (-8.75, 40.64), (-8.87, 40.15), (-9.07, 39.59),
    (-9.40, 39.36), (-9.50, 38.78), (-9.42, 38.69), (-9.21, 38.41), (-8.89, 37.95), (-8.99, 37.02),
    (-8.94, 37.00), (-8.67, 37.10), (-7.92, 36.98), (-7.41, 37.17),
]
SPINE_M = LineString([TO_M(x, y) for x, y in SPINE])
PAIR_WINDOW_MIN = 180  # zelfde hoog- of laagwater bij het buurstation: binnen 3 uur


def chainage(lon: float, lat: float) -> float:
    """Afstand langs de kust in km, vanaf Caminha."""
    return SPINE_M.project(Point(TO_M(lon, lat))) / 1000


def load_stations(path: Path = STATIONS_FILE):
    data = json.loads(path.read_text())
    sts = sorted(data["stations"], key=lambda s: chainage(s["lon"], s["lat"]))
    for s in sts:
        s["km"] = chainage(s["lon"], s["lat"])
    return sts


def weights(lon: float, lat: float, stations) -> tuple[str, str, float, float]:
    """(station_a, station_b, gewicht_b, km). Gewicht 0 = helemaal station a."""
    km = chainage(lon, lat)
    kms = [s["km"] for s in stations]
    if km <= kms[0]:
        return stations[0]["id"], stations[0]["id"], 0.0, km
    if km >= kms[-1]:
        return stations[-1]["id"], stations[-1]["id"], 0.0, km
    i = bisect_left(kms, km)
    a, b = stations[i - 1], stations[i]
    return a["id"], b["id"], (km - a["km"]) / (b["km"] - a["km"]), km


def interpolate(ev_a, ev_b, w: float):
    """Extremen [[minuten, cm, hoog], ...] van a en b mengen met gewicht w voor b."""
    if w == 0 or ev_a is ev_b:
        return [list(e) for e in ev_a]
    tb = [e[0] for e in ev_b]
    out = []
    for t, h, hi in ev_a:
        i = bisect_left(tb, t)
        best = None
        for j in (i - 2, i - 1, i, i + 1):
            if 0 <= j < len(ev_b) and ev_b[j][2] == hi and abs(ev_b[j][0] - t) <= PAIR_WINDOW_MIN:
                if best is None or abs(ev_b[j][0] - t) < abs(best[0] - t):
                    best = ev_b[j]
        if best is None:
            continue
        out.append([round(t + w * (best[0] - t)), round(h + w * (best[1] - h)), hi])
    return out


def predict_at(lon: float, lat: float, stations=None):
    stations = stations or load_stations()
    a, b, w, _ = weights(lon, lat, stations)
    by = {s["id"]: s for s in stations}
    return interpolate(by[a]["extremen"], by[b]["extremen"], w)
