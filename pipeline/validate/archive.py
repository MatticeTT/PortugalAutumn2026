"""M6: bij elke run een klein archief bijhouden om later de voorspelling per vooruitzicht te meten.

Open-Meteo bewaart wel oude windvoorspellingen per vooruitzicht (Previous Runs API), maar niet
voor golven, en IPMA geeft alleen de metingen van de laatste 24 uur. Daarom bewaart elke run:
- de voorspelling van alle modellen op de punten bij de boeien en de IPMA-kuststations;
- de IPMA-metingen van de laatste 24 uur.

Schrijft archief/<YYYY-MM-DD>/<HH>Z.json (een paar honderd kB per run), voor de tak `archief`.
"""

from __future__ import annotations

import json
import math
import sys
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FC = ROOT / "data" / "forecast"
UA = "surfkaart-portugal/0.1 (niet-commercieel, besloten)"
IPMA_OBS = "https://api.ipma.pt/open-data/observation/meteorology/stations/observations.json"
IPMA_ST = "https://api.ipma.pt/open-data/observation/meteorology/stations/stations.json"

# Boeien met golfmetingen (Copernicus In-Situ), lon/lat.
BOEIEN = {"Leixoes-coast-buoy": (-8.983, 41.317), "Sines-coast-buoy": (-8.929, 37.921),
          "Faro-coast-buoy": (-7.898, 36.905)}
UREN = 120          # 5 dagen vooruit
MAX_STATIONS = 10   # verspreid langs de kust
WIND_VARS = ("wind_speed_10m", "wind_gusts_10m", "wind_direction_10m")
GOLF_VARS = ("wave_height", "wave_period", "wave_peak_period")
OBS_VARS = ("intensidadeVentoKM", "idDireccVento")


def slim(rec: dict, keys) -> dict:
    return {k: [None if x is None else round(x, 1) for x in rec[k][:UREN]] for k in keys if rec.get(k)}


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def nearest(points: dict, lon: float, lat: float) -> str:
    def d(k):
        la, lo = map(float, k.split(","))
        return (la - lat) ** 2 + ((lo - lon) * math.cos(math.radians(lat))) ** 2
    return min((k for k in points if not k.startswith("_")), key=d)


def main(out_dir: Path):
    now = datetime.now(UTC)
    src = {n: json.loads((FC / f"{n}.json").read_text()) for n in ("wind_gfs", "wind_ecmwf", "golf_gfswave", "golf_ibi")
           if (FC / f"{n}.json").exists()}
    rec = {"gemaakt": now.strftime("%Y-%m-%dT%H:%MZ"), "opgehaald": {n: s.get("_opgehaald") for n, s in src.items()},
           "tijd": {n: s["_tijd"][:UREN] for n, s in src.items()}, "boeien": {}, "ipma_stations": {}}
    for code, (lon, lat) in BOEIEN.items():
        rec["boeien"][code] = {n: slim(s[nearest(s, lon, lat)], GOLF_VARS) for n, s in src.items()
                               if n.startswith("golf")}
    try:
        stations = get_json(IPMA_ST)
        obs = get_json(IPMA_OBS)
        coastal = {}
        for f in stations:
            lon, lat = f["geometry"]["coordinates"]
            sid = str(f["properties"]["idEstacao"])
            # Kuststations: binnen ongeveer 5 km van een windpunt dat bij een strand hoort.
            k = nearest(src["wind_gfs"], lon, lat)
            la, lo = map(float, k.split(","))
            if math.hypot(la - lat, (lo - lon) * math.cos(math.radians(lat))) < 0.05:
                coastal[sid] = {"naam": f["properties"]["localEstacao"], "lon": lon, "lat": lat, "windpunt": k}
        # Verspreid langs de kust: gesorteerd op breedte, om de zoveel een station.
        order = sorted(coastal, key=lambda k: -coastal[k]["lat"])
        step = max(1, len(order) // MAX_STATIONS)
        keep = {k: coastal[k] for k in order[::step][:MAX_STATIONS]}
        for sid, st in keep.items():
            st["metingen"] = {t: {k: (v.get(sid) or {}).get(k) for k in OBS_VARS} for t, v in obs.items()
                              if v.get(sid)}
            st["voorspelling"] = {n: slim(s[st["windpunt"]], WIND_VARS) for n, s in src.items() if n.startswith("wind")}
        rec["ipma_stations"] = keep
    except Exception as e:  # noqa: BLE001
        rec["ipma_fout"] = str(e)[:300]
    path = out_dir / now.strftime("%Y-%m-%d") / f"{now:%H}Z.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rec, separators=(",", ":")))
    print(path, round(path.stat().st_size / 1024), "kB,", len(rec["ipma_stations"]), "IPMA-kuststations")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "archief")
