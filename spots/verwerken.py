"""Van de ruwe lijsten (OpenStreetMap, Wikidata) naar één lijst surfspots met strandrichting en open zee.

Stappen
  1. Alleen surfplekken: winkels, scholen, clubs, sportcentra, zwembaden, gebouwen, verhuur, logies, golfbaden en
     windsurf/kite/sup-plekken eruit (op labels en op woorden in de naam). Een naam is verplicht.
  2. Dubbels samen: zelfde of overlappende naam binnen 2 km is één spot (OSM-punt met surfing-label gaat voor,
     dan Wikidata, dan het middelpunt van een strand).
  3. Kust (spots/kust.py, GSHHG): dichtste kustpunt, strandrichting binnen 500 m en 2 km, open zee per 5 graden.
  4. Twijfel gaat naar spots/na_te_kijken.csv met de reden en een satellietlink, niet naar de app:
       ver_van_kust     meer dan 1,5 km van de kustlijn (rivier, meer, golfbad, verkeerde positie)
       geen_richting    geen duidelijke kust bij het kustpunt
       richting_draait  richting binnen 500 m en 2 km verschilt meer dan 45 graden (kaap, baai, riviermonding)
       geen_open_zee    binnen 45 graden van de strandrichting nergens 20 km open water (meer, rivier, beschutte baai)

Uitvoer
  spots/spots.json       goede spots: naam, positie, bronnen, kustpunt, richting (graden waarnaar het strand
                         kijkt), open_km (per 5 graden vanaf 0 = noord), venster (richtingen met minstens 100 km
                         open zee: daar kan deining vandaan komen)
  spots/na_te_kijken.csv twijfelgevallen

Gebruik: python -m spots.verwerken --gshhg <map met gshhs_f.dat en gshhsmeta_f.dat>
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import time
import unicodedata
from pathlib import Path

from spots.kust import Kust, km_per_graad

MAP = Path(__file__).parent
SAMEN_KM = 2.0
MAX_KUST_KM = 1.5
MAX_DRAAI = 45
OPEN_MIN_KM = 20
VENSTER_KM = 100

# Labels die op een zaak, gebouw of andere sport wijzen.
WEG_LABELS = {
    "shop": None, "office": None, "craft": None, "building": None, "club": None, "healthcare": None,
    "amenity": None, "tourism": {"hotel", "hostel", "guest_house", "apartment", "camp_site", "motel", "chalet",
                                 "information", "museum", "gallery"},
    "leisure": {"sports_centre", "swimming_pool", "fitness_centre", "sports_hall", "water_park", "pitch",
                "swimming_area", "resort", "beach_resort", "playground", "park", "stadium", "marina", "track"},
    "natural": {"water", "wetland"}, "waterway": None, "landuse": None, "highway": None, "man_made": {"pier"},
}
WEG_WOORDEN = re.compile(
    r"\b(school|schule|escuela|escola|ecole|scuola|skola|academy|academia|camp|surfcamp|shop|store|boutique|"
    r"rental|rentals|hire|alquiler|aluguer|location|club|clube|centre|center|centro|shack|hostel|lodge|house|"
    r"hotel|resort|villa|apartments?|surf co|company|windsurf|kite|kitesurf|sup|stand ?up|wakeboard|skate|"
    r"wave ?pool|wavegarden|surf ?park|lessons?|coaching|bar|cafe|restaurant)\b|surfschool|surfshop|ecole de surf|"
    r"escola de surf|escuela de surf|surf ?school", re.I)
WD_WEG = re.compile(r"shop|store|company|business|club|school|organi[sz]ation|team|event|competition|pool|park|"
                    r"human|person|film|brand|magazine|museum|hotel|river|lake|artificial|building", re.I)
ALGEMEEN = re.compile(r"\b(praia|playa|plage|beach|spiaggia|strand|platja|spot|surf|de|da|do|la|le|el|the|du|des)\b")


def plat(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return " ".join(ALGEMEEN.sub(" ", s).split())


def sleutel(naam: str) -> str:
    """Naam zonder accenten en algemene woorden; schrift zonder Latijnse letters blijft zoals het is."""
    return plat(naam) or naam.strip().lower()


def afstand_km(a: dict, b: dict) -> float:
    kx, ky = km_per_graad((a["lat"] + b["lat"]) / 2)
    dlon = (a["lon"] - b["lon"] + 180) % 360 - 180
    return math.hypot(dlon * kx, (a["lat"] - b["lat"]) * ky)


def osm_kandidaten(objecten: list[dict]) -> tuple[list[dict], dict]:
    uit, weg = [], {}
    for o in objecten:
        t = o["tags"]
        naam = t.get("name:en") or t.get("name")
        reden = None
        if t.get("surfing") in ("no", "wave_pool", "artificial"):
            reden = "surfing=" + t["surfing"]
        elif not naam:
            reden = "geen naam"
        else:
            for k, waarden in WEG_LABELS.items():
                if k in t and (waarden is None or t[k] in waarden):
                    reden = f"{k}={t[k]}"
                    break
            if reden is None and WEG_WOORDEN.search(naam):
                reden = "naam lijkt een zaak of andere sport"
        if reden:
            sleutel = reden.split("=")[0]
            weg[sleutel] = weg.get(sleutel, 0) + 1
            continue
        rang = 0 if "surfing" in t else (2 if t.get("natural") == "beach" else 1)
        uit.append({"naam": t.get("name") or naam, "naam_en": t.get("name:en"), "lat": o["lat"], "lon": o["lon"],
                    "bronnen": ["osm:" + o["osm"]], "rang": rang,
                    "labels": {k: v for k, v in t.items() if k in ("natural", "surfing", "surf_spot", "description")}})
    return uit, weg


def wd_kandidaten(items: list[dict]) -> tuple[list[dict], dict]:
    uit, weg = [], {}
    for it in items:
        naam = it.get("naam")
        soorten = " ".join(it.get("soorten") or [])
        if not naam:
            reden = "geen naam"
        elif soorten and WD_WEG.search(soorten) and not re.search(r"beach|break|reef|bay|surf spot|point", soorten, re.I):
            reden = "soort: " + soorten[:40]
        elif WEG_WOORDEN.search(naam):
            reden = "naam lijkt een zaak of andere sport"
        else:
            reden = None
        if reden:
            weg[reden.split(":")[0]] = weg.get(reden.split(":")[0], 0) + 1
            continue
        uit.append({"naam": naam, "naam_en": None, "lat": it["lat"], "lon": it["lon"],
                    "bronnen": ["wikidata:" + it["wikidata"]], "rang": 1, "labels": {"soort": soorten}})
    return uit, weg


def samenvoegen(kand: list[dict]) -> list[dict]:
    """Zelfde of overlappende naam binnen SAMEN_KM wordt één spot; de beste bron geeft de positie."""
    kand = sorted(kand, key=lambda k: k["rang"])
    rooster: dict[tuple[int, int], list[dict]] = {}
    uit = []
    for k in kand:
        sleutels = {sleutel(k["naam"])} | ({sleutel(k["naam_en"])} if k.get("naam_en") else set())
        sleutels.discard("")
        cel = (int(k["lat"] // 0.05), int(k["lon"] // 0.05))
        gevonden = None
        for dj in (-1, 0, 1):
            for di in (-1, 0, 1):
                for s in rooster.get((cel[0] + dj, cel[1] + di), []):
                    if afstand_km(k, s) > SAMEN_KM:
                        continue
                    if any(a == b or (len(a) > 3 and len(b) > 3 and (a in b or b in a)) for a in sleutels for b in s["_sleutels"]):
                        gevonden = s
                        break
                if gevonden:
                    break
            if gevonden:
                break
        if gevonden:
            gevonden["bronnen"] += k["bronnen"]
            gevonden["_sleutels"] |= sleutels
            for a, b in k["labels"].items():
                gevonden["labels"].setdefault(a, b)
            continue
        k = dict(k, _sleutels=sleutels)
        rooster.setdefault(cel, []).append(k)
        uit.append(k)
    return uit


def vensters(open_km: list[float], stap: int = 5) -> list[list[int]]:
    """Aaneengesloten richtingen met minstens VENSTER_KM open zee, als [van, tot] in graden (met de klok mee)."""
    vrij = [d >= VENSTER_KM for d in open_km]
    n = len(vrij)
    if all(vrij):
        return [[0, 360]]
    if not any(vrij):
        return []
    start = next(i for i in range(n) if not vrij[i])  # begin na een dichte richting
    uit, i = [], 0
    while i < n:
        j = (start + i) % n
        if vrij[j]:
            k = i
            while k + 1 < n and vrij[(start + k + 1) % n]:
                k += 1
            uit.append([j * stap, ((start + k) % n) * stap])
            i = k + 1
        else:
            i += 1
    return uit


def twijfel(r) -> str | None:
    if r is None or r.kust_km > MAX_KUST_KM:
        return "ver_van_kust"
    if r.richting_500m is None and r.richting_2km is None:
        return "geen_richting"
    if r.richting_500m is not None and r.richting_2km is not None:
        if abs((r.richting_500m - r.richting_2km + 180) % 360 - 180) > MAX_DRAAI:
            return "richting_draait"
    f = r.richting_500m if r.richting_500m is not None else r.richting_2km
    if r.open_km is None:
        return "geen_open_zee"
    voor = [d for i, d in enumerate(r.open_km) if abs((i * 5 - f + 180) % 360 - 180) <= 45]
    if max(voor) < OPEN_MIN_KM:
        return "geen_open_zee"
    return None


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--gshhg", type=Path, required=True)
    p.add_argument("--max", type=int, default=0, help="alleen de eerste n spots (om te testen)")
    a = p.parse_args(argv)

    osm = json.loads((MAP / "osm_surfing.json").read_text())
    wd_pad = MAP / "wikidata_surfing.json"
    wd = json.loads(wd_pad.read_text()) if wd_pad.exists() else {"items": []}
    k1, w1 = osm_kandidaten(osm["objecten"])
    k2, w2 = wd_kandidaten(wd["items"])
    spots = samenvoegen(k1 + k2)
    print(f"OSM {len(osm['objecten'])} -> {len(k1)} (weg: {w1}); Wikidata {len(wd['items'])} -> {len(k2)} (weg: {w2}); "
          f"na samenvoegen {len(spots)}", flush=True)
    if a.max:
        spots = spots[:a.max]

    t0 = time.time()
    kust = Kust(a.gshhg)
    print(f"kustlijn geladen in {time.time() - t0:.0f} s", flush=True)
    goed, nakijken, redenen = [], [], {}
    for n, s in enumerate(spots):
        r = kust.analyse(s["lon"], s["lat"])
        reden = twijfel(r)
        rij = {"naam": s["naam"], "lat": round(s["lat"], 5), "lon": round(s["lon"], 5), "bronnen": s["bronnen"],
               "labels": s["labels"]}
        if reden:
            redenen[reden] = redenen.get(reden, 0) + 1
            nakijken.append({**rij, "reden": reden,
                             "kust_km": None if r is None else r.kust_km,
                             "richting_500m": None if r is None else r.richting_500m,
                             "richting_2km": None if r is None else r.richting_2km})
        else:
            f = r.richting_500m if r.richting_500m is not None else r.richting_2km
            goed.append({**rij, "kustpunt": r.kustpunt, "kust_km": r.kust_km, "richting": f,
                         "richting_2km": r.richting_2km, "open_km": r.open_km, "venster": vensters(r.open_km)})
        if n % 200 == 0:
            print(f"  {n}/{len(spots)}  {time.time() - t0:.0f} s", flush=True)

    bron = {"osm": osm.get("opgehaald"), "wikidata": wd.get("opgehaald")}
    (MAP / "spots.json").write_text(json.dumps({
        "bronnen": "OpenStreetMap (© OpenStreetMap-bijdragers, ODbL 1.0), Wikidata (CC0), kustlijn GSHHG (LGPL)",
        "opgehaald": bron, "aantal": len(goed), "spots": goed}, ensure_ascii=False, indent=0))
    with open(MAP / "na_te_kijken.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["naam", "reden", "lat", "lon", "kust_km", "richting_500m", "richting_2km", "bronnen", "satelliet"])
        for r in sorted(nakijken, key=lambda x: (x["reden"], x["naam"] or "")):
            w.writerow([r["naam"], r["reden"], r["lat"], r["lon"], r["kust_km"], r["richting_500m"], r["richting_2km"],
                        " ".join(r["bronnen"]),
                        f"https://www.google.com/maps/@{r['lat']},{r['lon']},1500m/data=!3m1!1e3"])
    print(f"{len(goed)} spots, {len(nakijken)} na te kijken {redenen}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
