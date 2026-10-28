"""Vergelijking: dezelfde stranden bij Open-Meteo, die de modellen van Windy (ECMWF) en Windguru (GFS) gratis aanbiedt.
Golven (marine-api): ECMWF WAM, Météo-France MFWAM, NOAA GFS-Wave. Wind (api): ECMWF IFS, GFS, ICON.
Punt: een paar km voor de kust in de kijkrichting van het strand (de golfmodellen hebben aan de kust vaak land).
Uit: vergelijk/openmeteo/<datum>.json
"""
import json, math, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

SPOTS = {"Bordeira": (37.19944, -8.90039, 318), "Cordoama": (37.10923, -8.93721, 304), "Praia da Rocha": (37.11551, -8.53208, 175)}
KM = 6  # zo ver voor de kust


def haal(url, q):
    u = url + "?" + urllib.parse.urlencode(q)
    for p in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "surfkaart-vergelijking"}), timeout=60) as r:
                return json.load(r)
        except Exception as e:  # noqa: BLE001
            print("fout", e, file=sys.stderr); time.sleep(5 * (p + 1))
    return None


uit = {"opgehaald": datetime.now(timezone.utc).isoformat(timespec="minutes"), "spots": {}}
for naam, (lat, lon, richting) in SPOTS.items():
    r = math.radians(richting)
    plat = lat + KM / 111 * math.cos(r)
    plon = lon + KM / (111 * math.cos(math.radians(lat))) * math.sin(r)
    golf = haal("https://marine-api.open-meteo.com/v1/marine", {
        "latitude": round(plat, 4), "longitude": round(plon, 4), "forecast_days": 10, "timezone": "UTC",
        "models": "ecmwf_wam025,meteofrance_wave,ncep_gfswave025",
        "hourly": "wave_height,swell_wave_height,swell_wave_direction,swell_wave_peak_period,swell_wave_period,wind_wave_height"})
    wind = haal("https://api.open-meteo.com/v1/forecast", {
        "latitude": lat, "longitude": lon, "forecast_days": 10, "timezone": "UTC", "wind_speed_unit": "kn",
        "models": "ecmwf_ifs025,gfs_seamless,icon_seamless",
        "hourly": "wind_speed_10m,wind_direction_10m,wind_gusts_10m"})
    uit["spots"][naam] = {"punt_golf": [round(plat, 4), round(plon, 4)], "golf": golf, "wind": wind}
    print(naam, "golf", bool(golf), "wind", bool(wind))
pad = Path("vergelijk/openmeteo") / (uit["opgehaald"][:13].replace(":", "") + ".json")
pad.parent.mkdir(parents=True, exist_ok=True)
json.dump(uit, open(pad, "w"))
print("bewaard", pad)
