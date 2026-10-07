"""OpenBeta natellen voor Portugal (gratis, open data): hoeveel gebieden, routes en boulders, en hoeveel
met een graad. Alleen tellen, niets op de kaart. Draait in GitHub Actions (klim.yml).

Schrijft data/klim/openbeta_telling.json en drukt de telling af.
"""

from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "klim" / "openbeta_telling.json"
API = "https://api.openbeta.io/"
UA = "surfkaart-portugal/0.1 (niet-commercieel, besloten)"


def vraag(query: str, variabelen: dict) -> dict:
    body = json.dumps({"query": query, "variables": variabelen}).encode()
    for poging in range(4):
        try:
            req = urllib.request.Request(API, data=body,
                                         headers={"Content-Type": "application/json", "User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                antwoord = json.loads(r.read())
            if antwoord.get("errors"):
                raise RuntimeError(json.dumps(antwoord["errors"])[:800])
            return antwoord["data"]
        except Exception as e:  # noqa: BLE001
            print(f"OpenBeta: {e}; opnieuw", flush=True)
            time.sleep(10 * (poging + 1))
    raise RuntimeError("OpenBeta niet bereikbaar")


ZOEK = """query($naam: String!) { areas(filter: {area_name: {match: $naam, exactMatch: true}}) {
  uuid area_name pathTokens totalClimbs } }"""
GEBIED = """query($uuid: ID) { area(uuid: $uuid) { uuid area_name totalClimbs
  metadata { leaf isBoulder lat lng }
  children { uuid }
  climbs { uuid type { sport trad bouldering } grades { french font yds vscale uiaa } } } }"""


def main():
    land = [a for a in vraag(ZOEK, {"naam": "Portugal"})["areas"] if len(a.get("pathTokens") or []) <= 2]
    print("gevonden:", json.dumps(land)[:500], flush=True)
    if not land:
        raise RuntimeError("Portugal niet gevonden in OpenBeta")
    wacht, gezien = [land[0]["uuid"]], set()
    gebieden = boulder_gebieden = 0
    routes = {"sport/trad": 0, "boulder": 0}
    met_graad = {"sport/trad": 0, "boulder": 0}
    with_coord = 0
    while wacht:
        u = wacht.pop()
        if u in gezien:
            continue
        gezien.add(u)
        a = vraag(GEBIED, {"uuid": u})["area"]
        gebieden += 1
        m = a.get("metadata") or {}
        boulder_gebieden += bool(m.get("isBoulder"))
        with_coord += m.get("lat") is not None
        wacht += [c["uuid"] for c in a.get("children") or []]
        for c in a.get("climbs") or []:
            soort = "boulder" if (c.get("type") or {}).get("bouldering") else "sport/trad"
            routes[soort] += 1
            g = c.get("grades") or {}
            boulder_graad = g.get("font") or g.get("vscale")
            route_graad = g.get("french") or g.get("yds") or g.get("uiaa")
            if boulder_graad if soort == "boulder" else route_graad:
                met_graad[soort] += 1
        time.sleep(0.2)
    telling = {"gebieden": gebieden, "boulder_gebieden": boulder_gebieden, "gebieden_met_ligging": with_coord,
               "routes": routes, "routes_met_graad": met_graad,
               "totalClimbs_volgens_openbeta": land[0].get("totalClimbs")}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(telling, indent=1) + "\n")
    print(json.dumps(telling, indent=1))


if __name__ == "__main__":
    main()
