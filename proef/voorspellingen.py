"""Voorspellingen van Open-Meteo: wind via de Previous Runs API, golven en watertemperatuur via de Marine API."""

import pandas as pd

from .fouten import UREN
from .logboek import Logboek

PREVIOUS_RUNS = "https://previous-runs-api.open-meteo.com/v1/forecast"
MARINE = "https://marine-api.open-meteo.com/v1/marine"

WINDMODELLEN = ["best_match", "ecmwf_ifs025", "gfs_seamless"]
GOLFMODELLEN = ["best_match", "ecmwf_wam025", "meteofrance_wave", "ncep_gfswave025"]
HORIZONNEN = {1: "1 dag", 3: "3 dagen", 5: "5 dagen"}

WINDVARS = {"wind_speed_10m": "wind_kn", "wind_direction_10m": "windrichting", "wind_gusts_10m": "vlaag_kn"}
GOLFVARS = {"wave_height": "hs_m", "wave_period": "tm_s", "wave_peak_period": "tp_s",
            "wave_direction": "golfrichting", "sea_surface_temperature": "sst_c"}

PERIODE = {"start_date": "2026-09-01", "end_date": "2026-09-30", "timezone": "GMT"}


class OpenMeteoFout(Exception):
    pass


def _vraag(log: Logboek, url: str, params: dict) -> dict:
    r = log.get(url, params=params)
    try:
        j = r.json()
    except ValueError:
        raise OpenMeteoFout(f"HTTP {r.status_code}: {r.text[:200]}")
    if not r.ok or j.get("error"):
        raise OpenMeteoFout(j.get("reason", f"HTTP {r.status_code}"))
    n = len(params.get("hourly", "").split(","))
    # Open-Meteo telt aanvragen met >10 variabelen of >2 weken als meerdere (schatting).
    log.gewicht_open_meteo += max(1.0, n / 10) * (30 / 14)
    return j


def _tabel(j: dict) -> pd.DataFrame:
    h = j["hourly"]
    df = pd.DataFrame({k: v for k, v in h.items() if k != "time"})
    df.index = pd.to_datetime(h["time"], utc=True)
    return df.apply(pd.to_numeric, errors="coerce").reindex(UREN)


def wind(log: Logboek, lat, lon, model: str, vlagen: bool = True) -> tuple[pd.DataFrame, dict]:
    """Kolommen <variabele>_d<N> voor horizon N dagen; plus de rastercel die Open-Meteo koos."""
    vars_ = [v for v in WINDVARS if vlagen or v != "wind_gusts_10m"]
    hourly = [f"{v}_previous_day{n}" for n in HORIZONNEN for v in vars_]
    j = _vraag(log, PREVIOUS_RUNS, {"latitude": lat, "longitude": lon, "hourly": ",".join(hourly),
                                    "wind_speed_unit": "kn", "models": model, **PERIODE})
    ruw = _tabel(j)
    uit = pd.DataFrame(index=UREN)
    for n in HORIZONNEN:
        for v, naam in WINDVARS.items():
            k = f"{v}_previous_day{n}"
            if k in ruw:
                uit[f"{naam}_d{n}"] = ruw[k]
    return uit, {"cel_lat": j.get("latitude"), "cel_lon": j.get("longitude")}


def marine(log: Logboek, lat, lon, model: str, variabelen) -> tuple[pd.DataFrame, dict]:
    j = _vraag(log, MARINE, {"latitude": lat, "longitude": lon, "hourly": ",".join(variabelen),
                             "models": model, "cell_selection": "sea", **PERIODE})
    ruw = _tabel(j)
    uit = pd.DataFrame(index=UREN)
    for v in variabelen:
        if v in ruw:
            uit[GOLFVARS[v]] = ruw[v]
    return uit, {"cel_lat": j.get("latitude"), "cel_lon": j.get("longitude")}


def probe(log: Logboek, url: str, params: dict) -> tuple[bool, str]:
    """Kleine controle-aanvraag (één dag) voor stap 0."""
    p = {**params, "start_date": "2026-09-01", "end_date": "2026-09-01", "timezone": "GMT"}
    try:
        j = _vraag(log, url, p)
    except OpenMeteoFout as e:
        return False, str(e)
    leeg = [k for k, v in j.get("hourly", {}).items() if k != "time" and all(x is None for x in v)]
    return True, ("alle waarden leeg: " + ", ".join(leeg)) if leeg else "ok"
