"""Getij voor de stranden van Spanje, Frankrijk en België: elk strand aan het dichtste getijstation.

Voor Portugal wordt tussen twee stations geïnterpoleerd langs een lijn langs de kust (interp.py).
Zo'n lijn bestaat hier niet; daarom geldt het dichtste station aan open zee (gewicht 0). Stations
in een riviermonding of landinwaarts, en stations op eilanden of in Afrika, tellen niet mee.

Leest data/tides/stations_landen.json (landen.mjs) en data/beaches/landen/<land>.geojson.
Schrijft data/tides/stranden_getij_landen.json: per strand {a, b, w, km, nauwkeurigheid, nota}
in dezelfde vorm als stranden_getij.json, zodat de site-bouw beide op dezelfde manier gebruikt.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATIONS = ROOT / "data" / "tides" / "stations_landen.json"
LANDEN = ROOT / "data" / "beaches" / "landen"
OUT = ROOT / "data" / "tides" / "stranden_getij_landen.json"

# Niet aan open zee: riviermondingen en havens landinwaarts (Seine, Adour, Gironde, Loire, Seudre,
# Canche, Odet, Guadalquivir), en eilanden of Afrika (Balearen, Alborán, Ceuta, Melilla).
NIET = ("Balise a Rouen", "Bayonne Pont Blanc", "Villefranque", "Donges", "Montoir-de-Bretagne", "Pauillac",
        "Lamena", "Richard", "Pont Seudre", "Etaples Vigicrues", "Benodet Vigicrues", "Sevilla", "Bonanza",
        "Alboran", "Alcudia", "Formentera", "Palma", "POLLENSA", "COLONIA SANT PERE", "Ceuta", "Melilla")
MAX_KM = 160  # Côte d'Azur: Toulon is het dichtste station; het getij is er maar enkele decimeter


def km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    t = math.pi / 180
    h = (math.sin((lat2 - lat1) * t / 2) ** 2
         + math.cos(lat1 * t) * math.cos(lat2 * t) * math.sin((lon2 - lon1) * t / 2) ** 2)
    return 2 * 6371 * math.asin(math.sqrt(h))


def bruikbaar(s: dict) -> bool:
    return not any(s["naam"].startswith(n) for n in NIET)


def main() -> None:
    stations = [s for s in json.loads(STATIONS.read_text())["stations"] if bruikbaar(s)]
    out = {}
    for path in sorted(LANDEN.glob("*.geojson")):
        for f in json.loads(path.read_text())["features"]:
            lon, lat = f["geometry"]["coordinates"]
            afstand, s = min(((km(lat, lon, s["lat"], s["lon"]), s) for s in stations), key=lambda x: x[0])
            if afstand > MAX_KM:
                continue
            p = f["properties"]
            besloten = any(t == "Transitional" for t in p.get("eea_type", [])) or p.get("kandidaat_besloten_water")
            out[p["id"]] = {
                "a": s["id"], "b": s["id"], "w": 0, "km": round(afstand, 1),
                "nauwkeurigheid": "onzeker" if besloten else "niet gecontroleerd",
                "nota": (f"dichtste getijstation: {s['naam']} op {afstand:.0f} km; niet vergeleken met een getijtafel"
                         + ("; monding, lagune of baai: het getij kan er later vallen" if besloten else "")),
            }
    OUT.write_text(json.dumps(out, ensure_ascii=False) + "\n")
    print(len(out), "stranden met getij")


if __name__ == "__main__":
    main()
