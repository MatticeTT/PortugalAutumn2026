"""Klimplekken ophalen uit de bronnen (eigenaar, 7 oktober 2026). Draait wekelijks in GitHub Actions
(klim.yml); de bronnen zijn vanuit de ontwikkelomgeving niet bereikbaar.

Bron 1  OpenStreetMap via Overpass, de query van de eigenaar letterlijk.
Bron 2  Camptocamp: de lijst van waypoints (wtyp=climbing_outdoor, area 14123) en per waypoint het
        volledige document. De antwoorden worden ongewijzigd bewaard; het uitlezen gebeurt in
        pipeline/klim/plekken.py, met de veldnamen zoals ze in de JSON staan.

Schrijft data/klim/bron_osm.json en data/klim/bron_c2c.json. Lukt een bron niet, dan blijft het vorige
bestand staan en staat de fout in data/klim/status.json (de site toont dan een melding).
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAP = ROOT / "data" / "klim"
UA = "surfkaart-portugal/0.1 (niet-commercieel, besloten)"
OVERPASS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter",
            "https://overpass.private.coffee/api/interpreter"]
QUERY = """[out:json][timeout:120];
area["ISO3166-1"="PT"][admin_level=2]->.pt;
(
  nwr["climbing"](area.pt)(36.8,-9.7,42.3,-6.0);
  nwr["sport"="climbing"](area.pt)(36.8,-9.7,42.3,-6.0);
);
out center tags;"""
C2C = "https://api.camptocamp.org"


def http(url: str, data: bytes | None = None, timeout: int = 300) -> bytes:
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def osm() -> dict:
    fout = None
    for poging in range(6):
        url = OVERPASS[poging % len(OVERPASS)]
        try:
            antwoord = json.loads(http(url, urllib.parse.urlencode({"data": QUERY}).encode()))
            return {"elementen": antwoord["elements"]}
        except Exception as e:  # noqa: BLE001
            fout = e
            print(f"{url}: {e}; opnieuw", flush=True)
            time.sleep(20 * (poging + 1))
    raise RuntimeError(f"Overpass: {fout}")


def c2c() -> dict:
    lijst, offset = [], 0
    while True:
        p = json.loads(http(f"{C2C}/waypoints?a=14123&wtyp=climbing_outdoor&limit=100&offset={offset}"))
        lijst += p.get("documents", [])
        print(f"camptocamp: {len(lijst)} van {p.get('total')}", flush=True)
        if not p.get("documents") or len(lijst) >= (p.get("total") or 0):
            break
        offset += 100
        time.sleep(1)
    documenten = []
    for d in lijst:
        documenten.append(json.loads(http(f"{C2C}/waypoints/{d['document_id']}")))
        time.sleep(0.5)
    return {"lijst": lijst, "documenten": documenten}


def main():
    MAP.mkdir(parents=True, exist_ok=True)
    statuspad = MAP / "status.json"
    status = json.loads(statuspad.read_text()) if statuspad.exists() else {}
    nu = datetime.now(UTC).strftime("%Y-%m-%dT%H:%MZ")
    for naam, functie in (("osm", osm), ("c2c", c2c)):
        try:
            data = functie()
            data["opgehaald"] = nu
            (MAP / f"bron_{naam}.json").write_text(json.dumps(data, ensure_ascii=False) + "\n")
            status[naam] = {"ok": True, "opgehaald": nu}
            print(f"OK   {naam}", flush=True)
        except Exception as e:  # noqa: BLE001
            vorige = status.get(naam, {}).get("opgehaald")
            status[naam] = {"ok": False, "fout": f"{type(e).__name__}: {e}"[:300], "geprobeerd": nu,
                            "opgehaald": vorige}
            print(f"FOUT {naam}: {e}", flush=True)
    statuspad.write_text(json.dumps(status, indent=1) + "\n")


if __name__ == "__main__":
    main()
