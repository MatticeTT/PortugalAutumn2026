"""Klimplekken ophalen uit de bronnen (eigenaar, 7 oktober 2026). Draait wekelijks in GitHub Actions
(klim.yml); de bronnen zijn vanuit de ontwikkelomgeving niet bereikbaar.

Bron 1  OpenStreetMap via Overpass, de query van de eigenaar letterlijk.
Bron 2  Camptocamp: de lijst van waypoints (wtyp=climbing_outdoor, area 14123) en per waypoint het
        volledige document. De antwoorden worden ongewijzigd bewaard; het uitlezen gebeurt in
        pipeline/klim/plekken.py, met de veldnamen zoals ze in de JSON staan.

Schrijft data/klim/bron_osm.json en data/klim/bron_c2c.json. Lukt een bron niet, dan blijft het vorige
bestand staan en staat de fout in data/klim/status.json (de site toont dan een melding).

Andere landen (Spanje, Frankrijk, België; het vasteland, zoals bij de stranden): dezelfde twee bronnen,
in data/klim/<land>/bron_osm.json en bron_c2c.json. Overpass per vak van 2 x 2 graden (een heel land in
één keer loopt vast), Camptocamp met het gebied van dat land.

Gebruik: python -m pipeline.klim.ophalen            Portugal (zoals altijd)
         python -m pipeline.klim.ophalen es fr be   andere landen
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
# Andere landen: ISO-code, rechthoek (lon0, lat0, lon1, lat1) en de naam van het land bij Camptocamp.
LANDEN = {
    "es": {"iso": "ES", "bbox": (-9.4, 35.95, 3.4, 43.85), "c2c": ("Espagne", "España", "Spain")},
    "fr": {"iso": "FR", "bbox": (-5.2, 42.3, 8.3, 51.15), "c2c": ("France",)},
    "be": {"iso": "BE", "bbox": (2.5, 49.45, 6.45, 51.55), "c2c": ("Belgique", "België", "Belgium")},
    "nl": {"iso": "NL", "bbox": (3.3, 50.7, 7.25, 53.7), "c2c": ("Pays-Bas", "Nederland", "Netherlands")},
}
VAK = 2.0


def vakken(bbox):
    x0, y0, x1, y1 = bbox
    x = x0
    while x < x1:
        y = y0
        while y < y1:
            yield (y, x, min(y + VAK, y1), min(x + VAK, x1))  # zuid, west, noord, oost (Overpass)
            y += VAK
        x += VAK


def http(url: str, data: bytes | None = None, timeout: int = 300) -> bytes:
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def overpass(query: str) -> list[dict]:
    fout = None
    for poging in range(6):
        url = OVERPASS[poging % len(OVERPASS)]
        try:
            return json.loads(http(url, urllib.parse.urlencode({"data": query}).encode()))["elements"]
        except Exception as e:  # noqa: BLE001
            fout = e
            print(f"{url}: {e}; opnieuw", flush=True)
            time.sleep(20 * (poging + 1))
    raise RuntimeError(f"Overpass: {fout}")


def osm() -> dict:
    return {"elementen": overpass(QUERY)}


def osm_land(land: str) -> dict:
    cfg, uit, gezien = LANDEN[land], [], set()
    for s, w, n, o in vakken(cfg["bbox"]):
        q = (f'[out:json][timeout:300];area["ISO3166-1"="{cfg["iso"]}"][admin_level=2]->.a;'
             f'(nwr["climbing"](area.a)({s},{w},{n},{o});nwr["sport"="climbing"](area.a)({s},{w},{n},{o}););'
             "out center tags;")
        for e in overpass(q):
            k = (e["type"], e["id"])
            if k not in gezien:
                gezien.add(k)
                uit.append(e)
        print(f"overpass {land} {s},{w}: {len(uit)} elementen", flush=True)
        time.sleep(5)
    return {"elementen": uit}


def c2c_gebied(namen: tuple[str, ...]) -> int:
    """Het gebied (land) van Camptocamp met een van deze namen."""
    offset = 0
    while True:
        p = json.loads(http(f"{C2C}/areas?limit=100&offset={offset}"))
        for d in p.get("documents", []):
            titels = {loc.get("title") for loc in d.get("locales", [])}
            if d.get("area_type") == "country" and titels & set(namen):
                return d["document_id"]
        if not p.get("documents"):
            raise RuntimeError(f"geen Camptocamp-gebied voor {namen}")
        offset += 100
        time.sleep(0.5)


def c2c(gebied: int = 14123) -> dict:
    lijst, offset = [], 0
    while True:
        p = json.loads(http(f"{C2C}/waypoints?a={gebied}&wtyp=climbing_outdoor&limit=100&offset={offset}"))
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


def main(land: str | None = None):
    doel = MAP / land if land else MAP
    doel.mkdir(parents=True, exist_ok=True)
    statuspad = MAP / "status.json"
    status = json.loads(statuspad.read_text()) if statuspad.exists() else {}
    nu = datetime.now(UTC).strftime("%Y-%m-%dT%H:%MZ")
    bronnen = (("osm", osm), ("c2c", c2c)) if not land else (
        ("osm", lambda: osm_land(land)), ("c2c", lambda: c2c(c2c_gebied(LANDEN[land]["c2c"]))))
    for naam, functie in bronnen:
        sleutel = f"{naam}_{land}" if land else naam
        try:
            data = functie()
            data["opgehaald"] = nu
            (doel / f"bron_{naam}.json").write_text(json.dumps(data, ensure_ascii=False) + "\n")
            status[sleutel] = {"ok": True, "opgehaald": nu}
            print(f"OK   {sleutel}", flush=True)
        except Exception as e:  # noqa: BLE001
            vorige = status.get(sleutel, {}).get("opgehaald")
            status[sleutel] = {"ok": False, "fout": f"{type(e).__name__}: {e}"[:300], "geprobeerd": nu,
                               "opgehaald": vorige}
            print(f"FOUT {sleutel}: {e}", flush=True)
    statuspad.write_text(json.dumps(status, indent=1) + "\n")


if __name__ == "__main__":
    import sys

    for land in sys.argv[1:] or [None]:
        main(land)
