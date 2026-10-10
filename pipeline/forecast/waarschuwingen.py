"""Officiële weerwaarschuwingen voor Portugal, Spanje, Frankrijk en België via MeteoAlarm (EUMETNET).

MeteoAlarm bundelt de waarschuwingen van IPMA, AEMET, Météo-France en het KMI in één vorm (CAP), dus
alle landen werken hetzelfde. Per waarschuwing: niveau (geel, oranje, rood), soort (wind, kust, onweer,
regen, ...), begin en einde, en de gebieden (naam en EMMA_ID). De feed geeft geen kaartvorm; de site-bouw
koppelt een waarschuwing aan een strand of klimplek via de naam van het gebied (pipeline/site/gebied.py).

Schrijft data/forecast/meteoalarm.json: {"_opgehaald", "landen": {land: {"ok", "fout"?}},
"waarschuwingen": [{land, niveau 1-3, soort, van, tot, gebieden: [namen], emma: [codes]}]}.
"""

from __future__ import annotations

import json
import urllib.request
from datetime import UTC, datetime

FEEDS = {"pt": "portugal", "es": "spain", "fr": "france", "be": "belgium", "nl": "netherlands"}
URL = "https://feeds.meteoalarm.org/api/v1/warnings/feeds-{}"
UA = "surfkaart-portugal/0.1 (niet-commercieel, besloten)"
# awareness_level in CAP van MeteoAlarm: 1 groen (geen), 2 geel, 3 oranje, 4 rood.
NIVEAU = {2: 1, 3: 2, 4: 3}


def _param(info: dict, naam: str) -> str | None:
    for p in info.get("parameter") or []:
        if (p.get("valueName") or "").lower() == naam:
            return p.get("value")
    return None


def utc(t: str | None) -> str | None:
    """CAP-tijd met tijdzone ("2026-10-08T18:00:00+02:00") -> UTC zoals de tijdas van de site ("2026-10-08T16:00")."""
    if not t:
        return None
    try:
        d = datetime.fromisoformat(t.replace("Z", "+00:00"))
    except ValueError:
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=UTC)
    return d.astimezone(UTC).strftime("%Y-%m-%dT%H:%M")


def lees(land: str, feed: dict) -> list[dict]:
    uit = []
    for w in feed.get("warnings") or []:
        alert = w.get("alert") or w
        infos = alert.get("info") or []
        if isinstance(infos, dict):
            infos = [infos]
        if not infos:
            continue
        lvl = _param(infos[0], "awareness_level") or ""
        soort = _param(infos[0], "awareness_type") or ""
        try:
            niveau = NIVEAU.get(int(lvl.split(";")[0].strip()), 0)
        except ValueError:
            niveau = 0
        if not niveau:
            continue
        namen, emma = set(), set()
        for info in infos:  # elke taal: alle gebiedsnamen bewaren (Belgisch: Nederlands, Frans, Duits)
            areas = info.get("area") or []
            for a in areas if isinstance(areas, list) else [areas]:
                if a.get("areaDesc"):
                    namen.add(a["areaDesc"].strip())
                for g in a.get("geocode") or []:
                    if (g.get("valueName") or "").upper() == "EMMA_ID" and g.get("value"):
                        emma.add(g["value"])
        info = infos[0]
        van, tot = utc(info.get("onset") or info.get("effective")), utc(info.get("expires"))
        if not van or not tot:
            continue
        uit.append({"land": land, "niveau": niveau,
                    "soort": soort.split(";")[-1].strip().lower() if soort else "",
                    "van": van, "tot": tot,
                    "gebieden": sorted(namen), "emma": sorted(emma)})
    return uit


def ophalen() -> dict:
    uit = {"_opgehaald": datetime.now(UTC).strftime("%Y-%m-%dT%H:%MZ"), "landen": {}, "waarschuwingen": []}
    for land, naam in FEEDS.items():
        try:
            req = urllib.request.Request(URL.format(naam), headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=180) as r:
                feed = json.loads(r.read())
            ws = lees(land, feed)
            voorbeeld = (feed.get("warnings") or [None])[0]
            print(f"MeteoAlarm {land}: {len(feed.get('warnings') or [])} berichten, {len(ws)} geel of hoger; "
                  f"voorbeeld: {json.dumps(voorbeeld, ensure_ascii=False)[:600]}", flush=True)
            uit["waarschuwingen"] += ws
            uit["landen"][land] = {"ok": True, "berichten": len(ws)}
        except Exception as e:  # noqa: BLE001
            print(f"MeteoAlarm {land}: {e}", flush=True)
            uit["landen"][land] = {"ok": False, "fout": f"{type(e).__name__}: {e}"[:200]}
    if not any(v["ok"] for v in uit["landen"].values()):
        raise RuntimeError("MeteoAlarm niet bereikbaar")
    return uit
