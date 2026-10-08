"""Rijtijd met de auto van Ferragudo naar elk strand (en de extra plekken van de planning).

Bron: OSRM (Open Source Routing Machine) op OpenStreetMap-wegen, de openbare server router.project-osrm.org
(één aanvraag per seconde). Draait in GitHub Actions (rijtijd.yml); schrijft data/beaches/rijtijd.json:
{plek-id: {"min": rijtijd in minuten, "km": afstand over de weg}}. Plekken zonder route krijgen null.
"""

from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "beaches" / "rijtijd.json"
FERRAGUDO = (-8.5195, 37.1238)  # lon, lat
OSRM = "https://router.project-osrm.org/table/v1/driving/"
UA = "surfkaart-portugal/0.1 (niet-commercieel, besloten)"
EXTRA = {"ria-de-alvor": (-8.59756, 37.122296), "eigen/bensafrim": (-8.73129, 37.15338)}
PER_KEER = 90


def plekken() -> dict[str, tuple[float, float]]:
    fc = json.loads((ROOT / "data" / "beaches" / "stranden.geojson").read_text())
    uit = {f["properties"]["id"]: tuple(f["geometry"]["coordinates"][:2]) for f in fc["features"]}
    return {**uit, **EXTRA}


def main():
    p = plekken()
    ids = list(p)
    uit: dict[str, dict | None] = {}
    for i in range(0, len(ids), PER_KEER):
        deel = ids[i:i + PER_KEER]
        coords = ";".join(f"{x:.6f},{y:.6f}" for x, y in [FERRAGUDO, *[p[k] for k in deel]])
        url = f"{OSRM}{coords}?sources=0&annotations=duration,distance"
        for poging in range(5):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=120) as r:
                    a = json.loads(r.read())
                break
            except Exception as e:  # noqa: BLE001
                print(f"OSRM: {e}; opnieuw", flush=True)
                time.sleep(5 * (poging + 1))
        else:
            raise RuntimeError("OSRM niet bereikbaar")
        for k, s, m in zip(deel, a["durations"][0][1:], a["distances"][0][1:], strict=True):
            uit[k] = None if s is None else {"min": round(s / 60), "km": round(m / 1000)}
        print(f"{len(uit)} van {len(ids)}", flush=True)
        time.sleep(1.5)
    OUT.write_text(json.dumps({"bron": "OSRM (router.project-osrm.org), OpenStreetMap-wegen", "van": "Ferragudo",
                               "plekken": uit}, ensure_ascii=False, indent=0) + "\n")
    binnen = sum(1 for v in uit.values() if v and v["min"] <= 120)
    print(f"klaar: {len(uit)} plekken, {binnen} binnen 2 uur rijden")


if __name__ == "__main__":
    main()
