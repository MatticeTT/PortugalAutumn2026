"""Gebied (district of provincie) van een plek, en de weerwaarschuwingen van MeteoAlarm die daar gelden.

- gebied(land, lon, lat): de naam uit data/gebieden/<land>.geojson (punt in veelhoek, zonder extra bibliotheek).
- waarschuwingen(...): MeteoAlarm geeft per waarschuwing de namen van de gebieden. Portugal, Frankrijk en België
  gebruiken de namen van district, departement of provincie: die moeten gelijk zijn. Spanje gebruikt kustzones
  en delen van een provincie ("Litoral de Cádiz"): daar volstaat de provincienaam als woord in de zonenaam.
  Een Belgische kustwaarschuwing ("kust", "côte", "coast") geldt voor alle Belgische stranden.
  Nederland: provincies (admin_level 4); een strand op de Waddeneilanden telt ook als gebied "Waddeneilanden".
"""

from __future__ import annotations

import json
import re
import unicodedata
from functools import cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GEBIEDEN = ROOT / "data" / "gebieden"
SOORT_STRAND = {"wind", "coastalevent", "thunderstorm", "fog"}
SOORT_KLIM = {"rain", "thunderstorm", "wind", "snow-ice", "rain-flood", "flooding"}
NAAM = {"wind": "wind", "coastalevent": "kust", "thunderstorm": "onweer", "fog": "mist", "rain": "regen",
        "snow-ice": "sneeuw of ijzel", "rain-flood": "regen en overstroming", "flooding": "overstroming"}


def plat(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def delen(naam: str) -> list[str]:
    """"Alacant / Alicante" -> ["alacant", "alicante"]; "Región de Murcia" -> ["murcia"]."""
    uit = []
    for d in naam.split("/"):
        d = plat(d)
        d = re.sub(r"^(region de|provincia de|province de|province of) ", "", d)
        if len(d) >= 3:
            uit.append(d)
    return uit


@cache
def _veelhoeken(land: str):
    p = GEBIEDEN / f"{land}.geojson"
    if not p.exists():
        return []
    uit = []
    for f in json.loads(p.read_text())["features"]:
        g = f["geometry"]
        polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        for poly in polys:
            xs = [x for x, _ in poly[0]]
            ys = [y for _, y in poly[0]]
            uit.append((f["properties"]["name"], (min(xs), min(ys), max(xs), max(ys)), poly))
    return uit


def _in_ring(x: float, y: float, ring) -> bool:
    binnen = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:], strict=False):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            binnen = not binnen
    return binnen


def gebied(land: str, lon: float, lat: float) -> str | None:
    for naam, (x0, y0, x1, y1), poly in _veelhoeken(land):
        if x0 <= lon <= x1 and y0 <= lat <= y1 and _in_ring(lon, lat, poly[0]) \
                and not any(_in_ring(lon, lat, gat) for gat in poly[1:]):
            return naam
    return None


# Nederland: OpenStreetMap schrijft de provincie in het Fries, MeteoAlarm (KNMI) in het Nederlands.
NL_NAAM = {"fryslan": "friesland"}


def geldt(w: dict, land: str, naam: str | None) -> bool:
    """naam mag meerdere gebieden bevatten, gescheiden door "|" (bv. "Fryslân|Waddeneilanden")."""
    if w["land"] != land or not naam:
        return False
    eigen = [NL_NAAM.get(d, d) if land == "nl" else d for n in naam.split("|") for d in delen(n)]
    for g in w["gebieden"]:
        gp = plat(g)
        if land == "be" and re.search(r"\b(kust|cote|coast|kuste)\b", gp):
            return True
        if land == "es":
            if any(re.search(rf"\b{re.escape(d)}\b", gp) for d in eigen):
                return True
        elif gp in eigen or any(gp == d for d in eigen):
            return True
    return False


def per_uur(ws: list[dict], land: str, naam: str | None, soorten: set[str], axis: list[str]):
    """Per uur het hoogste niveau ("0" tot "3") en de lijst van waarschuwingen die gelden."""
    hier = [w for w in ws if w["soort"] in soorten and geldt(w, land, naam)]
    reeks = "".join(str(max([w["niveau"] for w in hier if w["van"] <= t < w["tot"]] or [0])) for t in axis)
    lijst = sorted({(w["niveau"], w["soort"], w["van"], w["tot"]) for w in hier}, key=lambda x: (x[2], -x[0]))
    return reeks, [{"niveau": n, "soort": NAAM.get(s, s), "van": v, "tot": t} for n, s, v, t in lijst]
