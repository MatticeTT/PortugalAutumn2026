"""Surfspots wereldwijd ophalen uit twee open bronnen. Draait in GitHub Actions (de bronnen zijn niet bereikbaar
vanuit de ontwikkelomgeving).

OpenStreetMap via de Overpass API -> spots/osm_surfing.json
  objecten met sport=surfing, of met een label surfing=* (bv. een strand of rif met surfing=yes);
  per object het OSM-type en -id, de positie (middelpunt bij lijnen en vlakken) en alle labels.
  Licentie: © OpenStreetMap-bijdragers, ODbL 1.0. Een afgeleide spotlijst valt ook onder de ODbL.
Wikidata via de SPARQL-dienst -> spots/wikidata_surfing.json
  items met sport (P641) surfen (Q159992) en coördinaten (P625), met naam en soort (P31).
  Licentie: CC0.
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
VRAAG = '[out:json][timeout:600];(nwr["sport"="surfing"];nwr["surfing"];);out center tags;'
UIT = Path(__file__).parent / "osm_surfing.json"
AGENT = "surfkaart/1.0 (persoonlijk project; github.com/MatticeTT/PortugalAutumn2026)"


def vraag(server: str) -> dict:
    data = urllib.parse.urlencode({"data": VRAAG}).encode()
    req = urllib.request.Request(server, data=data, headers={"User-Agent": AGENT})
    with urllib.request.urlopen(req, timeout=900) as r:
        return json.load(r)


WIKIDATA = "https://query.wikidata.org/sparql"
SPARQL = """
SELECT ?item ?naam ?coord (GROUP_CONCAT(DISTINCT ?soortNaam; separator="|") AS ?soorten) WHERE {
  ?item wdt:P641 wd:Q159992; wdt:P625 ?coord.
  OPTIONAL { ?item wdt:P31 ?soort. ?soort rdfs:label ?soortNaam. FILTER(LANG(?soortNaam) = "en") }
  OPTIONAL { ?item rdfs:label ?naam. FILTER(LANG(?naam) = "en") }
} GROUP BY ?item ?naam ?coord
"""
UIT_WD = Path(__file__).parent / "wikidata_surfing.json"


def wikidata() -> int:
    url = WIKIDATA + "?" + urllib.parse.urlencode({"query": SPARQL, "format": "json"})
    for poging in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": AGENT, "Accept": "application/sparql-results+json"})
            with urllib.request.urlopen(req, timeout=300) as r:
                rijen = json.load(r)["results"]["bindings"]
            break
        except Exception as e:  # noqa: BLE001
            print(f"Wikidata: {e}", flush=True)
            time.sleep(30 * (poging + 1))
    else:
        return 1
    uit = []
    for b in rijen:
        punt = b["coord"]["value"]  # "Point(lon lat)"
        try:
            lon, lat = (float(x) for x in punt[punt.index("(") + 1:punt.index(")")].split())
        except ValueError:
            continue
        uit.append({"wikidata": b["item"]["value"].rsplit("/", 1)[-1], "naam": b.get("naam", {}).get("value"),
                    "soorten": [x for x in b.get("soorten", {}).get("value", "").split("|") if x], "lat": lat, "lon": lon})
    uit.sort(key=lambda x: x["wikidata"])
    UIT_WD.write_text(json.dumps({"bron": "Wikidata, sport (P641) = surfen (Q159992)", "licentie": "CC0",
                                  "opgehaald": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime()), "items": uit},
                                 ensure_ascii=False, indent=0))
    print(f"{len(uit)} Wikidata-items", flush=True)
    return 0


def main() -> int:
    wd = wikidata()
    osm = osm_ophalen()
    return wd or osm


def osm_ophalen() -> int:
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
