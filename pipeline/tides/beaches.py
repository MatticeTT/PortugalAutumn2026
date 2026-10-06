"""M2: elk strand aan zijn getijstations koppelen.

Schrijft data/tides/stranden_getij.json: per strand de twee stations, het gewicht en
hoe zeker de getijtijden zijn. De site rekent er zelf de hoog- en laagwaters mee uit
(pipeline/tides/interp.py doet hetzelfde in Python).
"""

from __future__ import annotations

import json
from pathlib import Path

from pipeline.tides import interp

ROOT = Path(__file__).resolve().parents[2]
BEACHES = ROOT / "data" / "beaches" / "stranden.geojson"
OUT = ROOT / "data" / "tides" / "stranden_getij.json"


def accuracy(p: dict, a: str, b: str) -> tuple[str, str | None]:
    """Verwachte nauwkeurigheid, op basis van de controle tegen de getijtafel (OPEN.md)."""
    if any(t == "Transitional" for t in p.get("eea_type", [])) or p.get("kandidaat_besloten_water"):
        return "onzeker", "monding, lagune of baai: het getij kan er een half uur later vallen"
    if b == "huelva":
        return "±15 min", "oostelijke Algarve: geen Portugees peilstation ten oosten van Lagos"
    return "±5 min", None


def main():
    stations = interp.load_stations()
    fc = json.loads(BEACHES.read_text())
    out = {}
    for f in fc["features"]:
        lon, lat = f["geometry"]["coordinates"]
        a, b, w, km = interp.weights(lon, lat, stations)
        acc, note = accuracy(f["properties"], a, b)
        out[f["properties"]["id"]] = {"a": a, "b": b, "w": round(w, 3), "km": round(km, 1),
                                      "nauwkeurigheid": acc, "nota": note}
    OUT.write_text(json.dumps(out, ensure_ascii=False) + "\n")
    from collections import Counter
    print(len(out), Counter(v["nauwkeurigheid"] for v in out.values()))


if __name__ == "__main__":
    main()
