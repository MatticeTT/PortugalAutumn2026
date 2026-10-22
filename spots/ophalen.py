"""Surfspots wereldwijd uit OpenStreetMap (sport=surfing) ophalen via de Overpass API.

Draait in GitHub Actions (Overpass is niet bereikbaar vanuit de ontwikkelomgeving). Schrijft spots/osm_surfing.json:
per object het OSM-type en -id, de positie (middelpunt bij lijnen en vlakken) en alle labels.
Licentie: © OpenStreetMap-bijdragers, ODbL 1.0. Een afgeleide spotlijst valt ook onder de ODbL.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

SERVERS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
)
VRAAG = '[out:json][timeout:600];nwr["sport"="surfing"];out center tags;'
UIT = Path(__file__).parent / "osm_surfing.json"
AGENT = "surfkaart/1.0 (persoonlijk project; github.com/MatticeTT/PortugalAutumn2026)"


def vraag(server: str) -> dict:
    data = urllib.parse.urlencode({"data": VRAAG}).encode()
    req = urllib.request.Request(server, data=data, headers={"User-Agent": AGENT})
    with urllib.request.urlopen(req, timeout=900) as r:
        return json.load(r)


def main() -> int:
    for poging in range(8):
        server = SERVERS[poging % len(SERVERS)]
        try:
            d = vraag(server)
        except Exception as e:  # noqa: BLE001 - volgende server proberen
            print(f"{server}: {e}", flush=True)
            time.sleep(min(120, 15 * 2**poging))
            continue
        uit = []
        for el in d.get("elements", []):
            pos = el.get("center") or {"lat": el.get("lat"), "lon": el.get("lon")}
            if pos.get("lat") is None:
                continue
            uit.append({"osm": f"{el['type']}/{el['id']}", "lat": pos["lat"], "lon": pos["lon"], "tags": el.get("tags", {})})
        uit.sort(key=lambda x: x["osm"])
        UIT.write_text(json.dumps({"bron": "OpenStreetMap, sport=surfing, via " + server,
                                   "licentie": "© OpenStreetMap-bijdragers, ODbL 1.0",
                                   "opgehaald": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime()),
                                   "osm_basis": d.get("osm3s", {}).get("timestamp_osm_base"),
                                   "objecten": uit}, ensure_ascii=False, indent=0))
        print(f"{len(uit)} objecten van {server}", flush=True)
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
