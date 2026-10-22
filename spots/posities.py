"""Posities van de spots uit de spotkennis (spots/kennis/*.json) opzoeken in OpenStreetMap via Nominatim.

Per spot het veld 'zoek' (bv. "Praia do Medão, Peniche"); het eerste resultaat geeft de positie en het OSM-object.
Nominatim: hooguit 1 vraag per seconde, met een eigen User-Agent (gebruiksregels van de OSMF). Data ODbL 1.0.
Draait in GitHub Actions. Schrijft spots/kennis/<regio>_posities.json; spots die al een positie hebben worden niet
opnieuw gevraagd.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

MAP = Path(__file__).parent / "kennis"
URL = "https://nominatim.openstreetmap.org/search"
AGENT = "surfkaart/1.0 (persoonlijk project; github.com/MatticeTT/PortugalAutumn2026)"
LAND = {"portugal": "pt"}


def zoek(q: str, land: str | None) -> dict | None:
    par = {"q": q, "format": "jsonv2", "limit": 1}
    if land:
        par["countrycodes"] = land
    req = urllib.request.Request(URL + "?" + urllib.parse.urlencode(par), headers={"User-Agent": AGENT})
    with urllib.request.urlopen(req, timeout=60) as r:
        res = json.load(r)
    if not res:
        return None
    x = res[0]
    return {"lat": float(x["lat"]), "lon": float(x["lon"]), "osm": f"{x['osm_type']}/{x['osm_id']}",
            "soort": f"{x.get('category')}={x.get('type')}", "gevonden": x.get("display_name")}


def main() -> int:
    fouten = 0
    for pad in sorted(MAP.glob("*.json")):
        if pad.stem.endswith("_posities"):
            continue
        uitpad = MAP / f"{pad.stem}_posities.json"
        oud = json.loads(uitpad.read_text()) if uitpad.exists() else {}
        uit = {}
        for s in json.loads(pad.read_text())["spots"]:
            q = s.get("zoek") or s["naam"]
            if q in oud and oud[q] is not None:
                uit[q] = oud[q]
                continue
            try:
                uit[q] = zoek(q, LAND.get(pad.stem))
                if uit[q] is None:  # tweede poging: alleen de naam vóór de komma met de plaats
                    time.sleep(1.1)
                    uit[q] = zoek(s["naam"] + ", " + q.split(",")[-1].strip(), LAND.get(pad.stem))
            except Exception as e:  # noqa: BLE001
                print(f"{q}: {e}", flush=True)
                uit[q] = None
                fouten += 1
            print(f"{q}: {uit[q] and uit[q]['gevonden']}", flush=True)
            time.sleep(1.1)
        uitpad.write_text(json.dumps(uit, ensure_ascii=False, indent=1))
        print(f"{pad.stem}: {sum(v is not None for v in uit.values())}/{len(uit)} gevonden", flush=True)
    return 1 if fouten else 0


if __name__ == "__main__":
    sys.exit(main())
