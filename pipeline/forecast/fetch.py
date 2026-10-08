"""M3: de voorspelling per strand ophalen (draait elke 6 uur in GitHub Actions).

Bronnen (PLAN.md 3.1):
- wind GFS 13 km      Open-Meteo, models=gfs_seamless     ("zelfde model als Windguru")
- wind ECMWF IFS 9 km Open-Meteo, models=ecmwf_ifs
- golven GFS-Wave     Open-Meteo Marine, models=ncep_gfswave016 ("zelfde model als Windguru")
- golven IBI 3 km     Copernicus Marine, cmems_mod_ibi_wav_anfc_0.027deg_PT1H-i

Wind wordt opgevraagd op het strand, golven in het zeevak (5 km uit de kust).
Stranden die dicht bij elkaar liggen delen een punt (afgerond op PUNT_RASTER graden):
dat houdt het aantal aanroepen onder de grens van Open-Meteo (10.000 per dag).

Schrijft data/forecast/:
- punten.json        per strand het windpunt en het golfpunt
- wind_<model>.json  per windpunt de uurreeksen
- golf_<model>.json  per golfpunt de uurreeksen
- klim_weer.json     per klimplek neerslag, luchtvochtigheid, temperatuur en wind, vanaf 1 dag terug

Andere landen (Spanje, Frankrijk, België; data/beaches/landen/): alleen wind GFS en golven GFS-Wave,
bij elke run (één keer per dag, zoals Portugal). Stranden in hetzelfde modelvak delen één aanroep: per vak wordt
het punt van het eerste strand opgevraagd, en Open-Meteo geeft voor elk punt in dat vak hetzelfde
rasterpunt terug. Zo blijft het totaal onder de grens van Open-Meteo. Bestanden: punten_landen.json,
wind_gfs_landen.json, golf_gfswave_landen.json.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BEACHES = ROOT / "data" / "beaches" / "stranden.geojson"
OUT = ROOT / "data" / "forecast"
UA = "surfkaart-portugal/0.1 (niet-commercieel, besloten)"
PUNT_RASTER = 0.05   # graden; ongeveer 5 km, kleiner dan de modelvakken (9 tot 16 km)
DAGEN = 10
PER_AANROEP = 50     # locaties per aanroep naar Open-Meteo

WIND_VARS = ["wind_speed_10m", "wind_gusts_10m", "wind_direction_10m"]
WAVE_VARS = [
    "wave_height", "wave_period", "wave_direction",
    "swell_wave_height", "swell_wave_period", "swell_wave_direction",
    "secondary_swell_wave_height", "secondary_swell_wave_period", "secondary_swell_wave_direction",
    "wind_wave_height", "wind_wave_period", "wind_wave_direction",
]
# IBI-variabelen, met de naam die ze in onze bestanden krijgen (zelfde namen als bij Open-Meteo).
IBI_VARS = {
    "VHM0": "wave_height", "VTPK": "wave_peak_period", "VMDR": "wave_direction",
    "VHM0_SW1": "swell_wave_height", "VTM01_SW1": "swell_wave_period", "VMDR_SW1": "swell_wave_direction",
    "VHM0_SW2": "secondary_swell_wave_height", "VTM01_SW2": "secondary_swell_wave_period",
    "VMDR_SW2": "secondary_swell_wave_direction",
    "VHM0_WW": "wind_wave_height", "VTM01_WW": "wind_wave_period", "VMDR_WW": "wind_wave_direction",
}


def snap(lon: float, lat: float) -> tuple[float, float]:
    r = PUNT_RASTER
    return round(round(lon / r) * r, 3), round(round(lat / r) * r, 3)


def key(pt: tuple[float, float]) -> str:
    return f"{pt[1]:.3f},{pt[0]:.3f}"


def points():
    fc = json.loads(BEACHES.read_text())
    per_beach, wind, wave = {}, {}, {}
    for f in fc["features"]:
        p = f["properties"]
        w = snap(*f["geometry"]["coordinates"])
        s = snap(*p["zeevak"])
        wind[key(w)] = w
        wave[key(s)] = s
        per_beach[p["id"]] = {"wind": key(w), "golf": key(s)}
    return per_beach, wind, wave


LANDEN = ROOT / "data" / "beaches" / "landen"
WIND_VAK = 0.125   # graden: rastervak van GFS (13 km)
GOLF_VAK = 0.16    # graden: rastervak van GFS-Wave (ncep_gfswave016)


def vak(lon: float, lat: float, r: float) -> str:
    return f"{round(lat / r)},{round(lon / r)}"


def points_landen():
    per_beach, wind, wave = {}, {}, {}
    for path in sorted(LANDEN.glob("*.geojson")):
        for f in json.loads(path.read_text())["features"]:
            p = f["properties"]
            lon, lat = f["geometry"]["coordinates"]
            kw, kg = vak(lon, lat, WIND_VAK), vak(*p["zeevak"], GOLF_VAK)
            wind.setdefault(kw, (round(lon, 4), round(lat, 4)))
            wave.setdefault(kg, (round(p["zeevak"][0], 4), round(p["zeevak"][1], 4)))
            per_beach[p["id"]] = {"wind": kw, "golf": kg}
    return per_beach, wind, wave


STROOM_VAK = 0.08   # graden: rastervak van de stroming bij Open-Meteo Marine (SMOC, 1/12 graad)
STROOM_VARS = ["ocean_current_velocity", "ocean_current_direction"]
NAAR_KN = {"km/h": 1 / 1.852, "m/s": 3.6 / 1.852, "kn": 1.0, "mph": 1.609344 / 1.852}


def points_stroom():
    """Stroming per vakje van het strand (rekenchat), voor Portugal en de andere landen."""
    per_beach, pts = {}, {}
    paden = [BEACHES, *sorted(LANDEN.glob("*.geojson"))]
    for path in paden:
        if not path.exists():
            continue
        for f in json.loads(path.read_text())["features"]:
            lon, lat = f["geometry"]["coordinates"]
            k = vak(lon, lat, STROOM_VAK)
            pts.setdefault(k, (round(lon, 4), round(lat, 4)))
            per_beach.setdefault(f["properties"]["id"], k)
    return per_beach, pts


def stroom(pts: dict) -> dict:
    """Snelheid (kn) en richting waarheen, per uur. Open-Meteo zegt in hourly_units welke eenheid het geeft."""
    keys = list(pts)
    out = {}
    for i in range(0, len(keys), PER_AANROEP):
        chunk = keys[i : i + PER_AANROEP]
        res = get_json("https://marine-api.open-meteo.com/v1/marine", {
            "latitude": ",".join(str(pts[k][1]) for k in chunk), "longitude": ",".join(str(pts[k][0]) for k in chunk),
            "hourly": ",".join(STROOM_VARS), "timezone": "UTC", "forecast_days": DAGEN, "cell_selection": "sea"})
        res = res if isinstance(res, list) else [res]
        for k, r in zip(chunk, res, strict=True):
            h = r["hourly"]
            eenheid = (r.get("hourly_units") or {}).get("ocean_current_velocity", "km/h")
            if eenheid not in NAAR_KN:
                raise RuntimeError(f"onbekende eenheid voor de stroming: {eenheid}")
            f = NAAR_KN[eenheid]
            snelheid = h.get("ocean_current_velocity") or []
            out[k] = {"rasterpunt": [r["longitude"], r["latitude"]],
                      "stroom_kn": [None if v is None else round(v * f, 2) for v in snelheid],
                      "stroom_naar": h.get("ocean_current_direction")}
            out.setdefault("_tijd", h["time"])
        time.sleep(4)
    return out


def get_json(url: str, params: dict, tries: int = 4):
    full = f"{url}?{urllib.parse.urlencode(params, safe=',')}"
    for i in range(tries):
        try:
            req = urllib.request.Request(full, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read())
        except Exception as e:  # noqa: BLE001
            if i == tries - 1:
                raise
            print(f"opnieuw ({e})", flush=True)
            time.sleep(2 ** (i + 1))


def open_meteo(url: str, pts: dict, model: str | None, variables: list[str], extra: dict | None = None,
               pauze: float = 1) -> dict:
    keys = list(pts)
    out = {}
    for i in range(0, len(keys), PER_AANROEP):
        chunk = keys[i : i + PER_AANROEP]
        params = {
            "latitude": ",".join(str(pts[k][1]) for k in chunk),
            "longitude": ",".join(str(pts[k][0]) for k in chunk),
            "hourly": ",".join(variables), "timezone": "UTC", "forecast_days": DAGEN,
            **({"models": model} if model else {}),  # geen model: Open-Meteo kiest zelf (standaard)
            **(extra or {}),
        }
        res = get_json(url, params)
        res = res if isinstance(res, list) else [res]
        for k, r in zip(chunk, res, strict=True):
            h = r["hourly"]
            out[k] = {"rasterpunt": [r["longitude"], r["latitude"]], **{v: h.get(v) for v in variables}}
            out.setdefault("_tijd", h["time"])
        time.sleep(pauze)
    return out


# Rekenmodel v2: heeft een bron per deining een piekperiode, dan telt die. Weigert de bron die
# variabelen, dan zonder (de gemiddelde periode blijft dan staan).
PIEK_VARS = ["swell_wave_peak_period", "secondary_swell_wave_peak_period", "wind_wave_peak_period"]


def golf_met_piek(pts: dict, pauze: float = 1) -> dict:
    url = "https://marine-api.open-meteo.com/v1/marine"
    try:
        return open_meteo(url, pts, "ncep_gfswave016", WAVE_VARS + PIEK_VARS, pauze=pauze)
    except Exception as e:  # noqa: BLE001
        print("piekperiode niet beschikbaar:", e)
        return open_meteo(url, pts, "ncep_gfswave016", WAVE_VARS, pauze=pauze)


KLIM = ROOT / "data" / "klim" / "bron_osm.json"
KLIM_VARS = ["precipitation", "relative_humidity_2m", "temperature_2m", "wind_speed_10m"]


def klim_weer() -> dict:
    """Weer per uur op de klimplek zelf (rekenchat): Open-Meteo met de standaard modelkeuze, neerslag,
    luchtvochtigheid, temperatuur en wind, plus de voorbije 24 uur (past_days=1)."""
    from pipeline.klim.plekken import alle

    pts = {q["id"]: (q["lon"], q["lat"]) for q in alle() if not q.get("land")}  # Portugal: per plek
    return open_meteo("https://api.open-meteo.com/v1/forecast", pts, None, KLIM_VARS,
                      {"wind_speed_unit": "kn", "past_days": 1})


KLIM_VAK = 0.05  # graden (ongeveer 5 km): klimplekken van de andere landen delen het weer per vak


def punten_klim_landen():
    from pipeline.klim.plekken import alle

    per_plek, pts = {}, {}
    for q in alle():
        if q.get("land"):
            k = vak(q["lon"], q["lat"], KLIM_VAK)
            pts.setdefault(k, (round(q["lon"], 4), round(q["lat"], 4)))
            per_plek[q["id"]] = k
    return per_plek, pts


def klim_weer_landen() -> dict:
    """Zelfde weer als klim_weer (rekenchat), voor de klimplekken van Spanje, Frankrijk en België, per vak."""
    per_plek, pts = punten_klim_landen()
    (OUT / "punten_klim_landen.json").write_text(json.dumps(per_plek) + "\n")
    print(f"klimweer andere landen: {len(per_plek)} plekken, {len(pts)} vakken", flush=True)
    return open_meteo("https://api.open-meteo.com/v1/forecast", pts, None, KLIM_VARS,
                      {"wind_speed_unit": "kn", "past_days": 1}, pauze=6)


def ibi(pts: dict) -> dict:
    """IBI-golven per punt. Kustcellen zonder data (NaN) krijgen de dichtste cel met data."""
    if not os.environ.get("COPERNICUSMARINE_SERVICE_USERNAME"):
        raise RuntimeError("geen Copernicus-account in de omgeving")
    import copernicusmarine
    import numpy as np
    import xarray as xr

    lons = [p[0] for p in pts.values()]
    lats = [p[1] for p in pts.values()]
    now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    ds = copernicusmarine.open_dataset(
        dataset_id="cmems_mod_ibi_wav_anfc_0.027deg_PT1H-i", variables=list(IBI_VARS),
        minimum_longitude=min(lons) - 0.1, maximum_longitude=max(lons) + 0.1,
        minimum_latitude=min(lats) - 0.1, maximum_latitude=max(lats) + 0.1,
        start_datetime=now.isoformat(), end_datetime=(now + timedelta(days=DAGEN)).isoformat(),
    )
    mask = np.isfinite(ds["VHM0"].isel(time=0).values)  # (lat, lon)
    glat, glon = ds.latitude.values, ds.longitude.values
    vy, vx = np.nonzero(mask)
    iy, ix = [], []
    for lon, lat in zip(lons, lats, strict=True):
        d2 = (glat[vy] - lat) ** 2 + ((glon[vx] - lon) * np.cos(np.radians(lat))) ** 2
        j = int(np.argmin(d2))
        iy.append(int(vy[j]))
        ix.append(int(vx[j]))
    sel = ds.isel(latitude=xr.DataArray(iy, dims="p"), longitude=xr.DataArray(ix, dims="p")).load()
    out = {"_tijd": [str(t)[:16] for t in sel.time.values]}
    for n, k in enumerate(pts):
        rec = {"rasterpunt": [round(float(glon[ix[n]]), 4), round(float(glat[iy[n]]), 4)]}
        for v, name in IBI_VARS.items():
            vals = sel[v].isel(p=n).values
            rec[name] = [None if not np.isfinite(x) else round(float(x), 2) for x in vals]
        out[k] = rec
    return out


def main(argv: list[str]) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    per_beach, wind_pts, wave_pts = points()
    (OUT / "punten.json").write_text(json.dumps(per_beach) + "\n")
    print(f"{len(per_beach)} stranden, {len(wind_pts)} windpunten, {len(wave_pts)} golfpunten", flush=True)
    sb, sp = points_stroom()
    (OUT / "punten_stroom.json").write_text(json.dumps(sb) + "\n")
    print(f"stroming: {len(sb)} stranden, {len(sp)} vakken", flush=True)
    lb, lw, lg = points_landen()
    if lb:
        (OUT / "punten_landen.json").write_text(json.dumps(lb) + "\n")
        print(f"andere landen: {len(lb)} stranden, {len(lw)} windvakken, {len(lg)} golfvakken", flush=True)
    # Andere landen bij elke run (één keer per dag). Rustiger tempo: Open-Meteo telt een aanroep met
    # meer dan 10 variabelen als meer, en staat 600 per minuut toe.
    landen_nu = bool(lb)
    jobs = {
        "wind_gfs": lambda: open_meteo("https://api.open-meteo.com/v1/forecast", wind_pts, "gfs_seamless",
                                       WIND_VARS, {"wind_speed_unit": "kn"}),
        **({"wind_gfs_landen": lambda: open_meteo("https://api.open-meteo.com/v1/forecast", lw, "gfs_seamless",
                                                  WIND_VARS, {"wind_speed_unit": "kn"}, pauze=6),
            "golf_gfswave_landen": lambda: golf_met_piek(lg, pauze=8)} if landen_nu else {}),
        "wind_ecmwf": lambda: open_meteo("https://api.open-meteo.com/v1/forecast", wind_pts, "ecmwf_ifs",
                                         WIND_VARS, {"wind_speed_unit": "kn"}),
        "golf_gfswave": lambda: golf_met_piek(wave_pts),
        "golf_ibi": lambda: ibi(wave_pts),
        "klim_weer": klim_weer,
        "stroom": lambda: stroom(sp),
        "klim_weer_landen": klim_weer_landen,
        "meteoalarm": lambda: __import__("pipeline.forecast.waarschuwingen", fromlist=["ophalen"]).ophalen(),
    }
    failed = []
    stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%MZ")
    for name in argv or list(jobs):
        if name == "klim_weer" and not KLIM.exists():
            print("klim_weer: nog geen data/klim/plekken.json", flush=True)
            continue
        try:
            data = jobs[name]()
            data["_opgehaald"] = stamp
            (OUT / f"{name}.json").write_text(json.dumps(data, separators=(",", ":")) + "\n")
            print(f"OK   {name}: {len(data) - 2} punten", flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"FOUT {name}: {type(e).__name__}: {e}", flush=True)
            failed.append(name)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
