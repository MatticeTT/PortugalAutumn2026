"""Surfline naast onze app leggen: alle Surfline-spots in Portugal (mapview) en per spot de voorspelling
(golven, wind, beoordeling, getij) voor 5 dagen, per uur. Ruw bewaard in vergelijk/surfline/<tijd>.json.gz."""
import gzip
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = "https://services.surfline.com/kbyg"
KOP = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36",
       "Accept": "application/json"}
EENHEDEN = {"units[waveHeight]": "M", "units[windSpeed]": "KTS", "units[swellHeight]": "M", "units[tideHeight]": "M"}


def haal(pad, **q):
    url = f"{API}/{pad}?{urllib.parse.urlencode({**q, **EENHEDEN})}"
    for poging in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=KOP), timeout=30) as r:
                return json.load(r)
        except Exception as e:  # noqa: BLE001
            print("  fout", pad, q.get("spotId", ""), e, file=sys.stderr)
            time.sleep(3 * (poging + 1))
    return None


def main():
    spots = {}
    # Portugal (vasteland) in vakken van 1 graad, zodat geen limiet op het aantal spots per vraag speelt.
    for zuid in range(36, 43):
        for west in range(-10, -5):
            r = haal("mapview", south=zuid, west=west, north=zuid + 1, east=west + 1)
            for s in ((r or {}).get("data") or {}).get("spots", []):
                spots[s["_id"]] = s
            time.sleep(0.5)
    print(len(spots), "spots van Surfline")
    uit = {"opgehaald": datetime.now(timezone.utc).isoformat(timespec="minutes"), "spots": spots, "voorspelling": {}}
    for k, sid in enumerate(spots):
        v = {}
        for soort, extra in (("wave", {"intervalHours": 1}), ("wind", {"intervalHours": 1}), ("rating", {"intervalHours": 1}), ("tides", {})):
            v[soort] = haal(f"spots/forecasts/{soort}", spotId=sid, days=5, **extra)
            time.sleep(0.4)
        uit["voorspelling"][sid] = v
        print(k + 1, spots[sid].get("name"))
    pad = Path("vergelijk/surfline") / (uit["opgehaald"][:13].replace(":", "") + ".json.gz")
    pad.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(pad, "wt") as f:
        json.dump(uit, f)
    print("bewaard", pad)


if __name__ == "__main__":
    main()
