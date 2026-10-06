"""M6, stap 0: kunnen we de nauwkeurigheid meten met historische gegevens?

Eén proef per bron, zoals in M0. Schrijft data/validate/proef.json met per bron de status
en een korte samenvatting. Draait in GitHub Actions (netwerk open, Copernicus-account).
"""

from __future__ import annotations

import json
import os
import traceback
import urllib.parse
import urllib.request
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "validate"
UA = "surfkaart-portugal/0.1 (niet-commercieel, besloten)"

# Sines kustboei en een punt bij Faro (kuststation) als proefpunten.
SINES = (37.921, -8.929)
FARO = (37.017, -7.967)
END = date.today() - timedelta(days=2)
START = END - timedelta(days=30)


def get(url: str, params: dict | None = None, timeout: int = 120) -> bytes:
    if params:
        url = f"{url}?{urllib.parse.urlencode(params, safe=',')}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def summarize_hourly(d: dict) -> dict:
    h = d.get("hourly", {})
    out = {"tijd": [h.get("time", [None])[0], h.get("time", [None])[-1]], "uren": len(h.get("time", []))}
    for k, v in h.items():
        if k == "time":
            continue
        vals = [x for x in v if x is not None]
        out[k] = {"n": len(vals), "gemiddeld": round(sum(vals) / len(vals), 2) if vals else None}
    return out


def previous_runs_wind():
    """Open-Meteo Previous Runs: dezelfde uren, voorspeld 1, 2 en 3 dagen vooraf."""
    hourly = ",".join(["wind_speed_10m"] + [f"wind_speed_10m_previous_day{i}" for i in (1, 2, 3)])
    out = {}
    for model in ("gfs_seamless", "ecmwf_ifs"):
        d = json.loads(get("https://previous-runs-api.open-meteo.com/v1/forecast", {
            "latitude": FARO[0], "longitude": FARO[1], "hourly": hourly, "models": model,
            "wind_speed_unit": "kn", "start_date": START.isoformat(), "end_date": END.isoformat(), "timezone": "UTC"}))
        out[model] = summarize_hourly(d)
    return out


def historical_forecast_wind():
    """Open-Meteo Historical Forecast: de eerste uren van elke run aan elkaar geplakt."""
    out = {}
    for model in ("gfs_seamless", "ecmwf_ifs"):
        d = json.loads(get("https://historical-forecast-api.open-meteo.com/v1/forecast", {
            "latitude": FARO[0], "longitude": FARO[1], "hourly": "wind_speed_10m,wind_gusts_10m",
            "models": model, "wind_speed_unit": "kn", "start_date": START.isoformat(),
            "end_date": END.isoformat(), "timezone": "UTC"}))
        out[model] = summarize_hourly(d)
    return out


def marine_past():
    """GFS-Wave in het verleden: Marine API met start- en einddatum, en Previous Runs voor golven."""
    out = {}
    d = json.loads(get("https://marine-api.open-meteo.com/v1/marine", {
        "latitude": SINES[0], "longitude": SINES[1] - 0.05, "hourly": "wave_height,wave_period",
        "models": "ncep_gfswave016", "start_date": START.isoformat(), "end_date": END.isoformat(), "timezone": "UTC"}))
    out["marine_api"] = summarize_hourly(d)
    try:
        d = json.loads(get("https://previous-runs-api.open-meteo.com/v1/marine", {
            "latitude": SINES[0], "longitude": SINES[1] - 0.05,
            "hourly": "wave_height,wave_height_previous_day1,wave_height_previous_day2",
            "models": "ncep_gfswave016", "start_date": START.isoformat(), "end_date": END.isoformat(),
            "timezone": "UTC"}))
        out["previous_runs_marine"] = summarize_hourly(d)
    except Exception as e:  # noqa: BLE001
        out["previous_runs_marine"] = f"fout: {e}"
    return out


def ibi_past():
    """Copernicus IBI-golven 30 dagen terug (analyse en voorspelling in hetzelfde product)."""
    if not os.environ.get("COPERNICUSMARINE_SERVICE_USERNAME"):
        raise RuntimeError("geen Copernicus-account")
    import copernicusmarine

    ds = copernicusmarine.open_dataset(
        dataset_id="cmems_mod_ibi_wav_anfc_0.027deg_PT1H-i", variables=["VHM0", "VTPK"],
        minimum_longitude=SINES[1] - 0.1, maximum_longitude=SINES[1] + 0.02,
        minimum_latitude=SINES[0] - 0.05, maximum_latitude=SINES[0] + 0.05,
        start_datetime=f"{START}T00:00:00", end_datetime=f"{END}T23:00:00",
    )
    return {"tijd": [str(ds.time.values[0])[:16], str(ds.time.values[-1])[:16]], "uren": int(ds.time.size),
            "VHM0_gemiddeld": round(float(ds["VHM0"].mean()), 2)}


def insitu_buoys():
    """Copernicus In-Situ (IBI): bestanden van de Portugese golfboeien zoeken op hun code."""
    if not os.environ.get("COPERNICUSMARINE_SERVICE_USERNAME"):
        raise RuntimeError("geen Copernicus-account")
    import copernicusmarine

    ds_id = "cmems_obs-ins_ibi_phybgcwav_mynrt_na_irr"
    out = {}
    for code in ("6201081", "6201077", "6201079", "Sines", "Leixoes", "Faro", "Nazare", "6200192", "6200199"):
        try:
            res = copernicusmarine.get(dataset_id=ds_id, filter=f"*{code}*", dry_run=True, disable_progress_bar=True)
            files = [getattr(f, "s3_url", None) or getattr(f, "https_url", None) or str(f) for f in res.files]
            recent = [f for f in files if "/latest/" in f or "/monthly/" in f]
            out[code] = {"aantal": len(files), "voorbeeld": sorted(files)[-5:], "recent": sorted(recent)[-5:]}
        except Exception as e:  # noqa: BLE001
            out[code] = f"fout: {type(e).__name__}: {e}"[:300]
    return out


def noaa_isd():
    """NOAA Global Hourly (ISD), publiek domein: welke Portugese stations, en Faro dit jaar."""
    out = {}
    for url in ("https://www.ncei.noaa.gov/pub/data/noaa/isd-history.csv",
                "https://www1.ncdc.noaa.gov/pub/data/noaa/isd-history.csv"):
        try:
            hist = get(url, timeout=300).decode(errors="replace")
            rows = [r for r in hist.splitlines() if ',"PO",' in r]
            out["stations_po"] = len(rows)
            out["recent"] = [r[:110] for r in rows if r.rstrip().split(",")[-1].strip('"') >= "20260901"][:60]
            break
        except Exception as e:  # noqa: BLE001
            out[url] = str(e)
    for sid in ("08554099999", "08554599999", "08536099999", "08545099999", "08533099999"):
        url = f"https://www.ncei.noaa.gov/data/global-hourly/access/2026/{sid}.csv"
        try:
            lines = get(url, timeout=300).decode().splitlines()
            out[sid] = {"regels": len(lines), "kop": lines[0][:200], "laatste": lines[-1][:160]}
        except Exception as e:  # noqa: BLE001
            out[sid] = str(e)
    return out


PROBES = {
    "open_meteo_previous_runs_wind": previous_runs_wind,
    "open_meteo_historical_forecast_wind": historical_forecast_wind,
    "open_meteo_golven_verleden": marine_past,
    "copernicus_ibi_verleden": ibi_past,
    "copernicus_insitu_boeien": insitu_buoys,
    "noaa_isd_wind": noaa_isd,
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    res = {"gemaakt": datetime.now(UTC).strftime("%Y-%m-%dT%H:%MZ"), "periode": [str(START), str(END)]}
    for name, fn in PROBES.items():
        try:
            res[name] = {"status": "ok", "resultaat": fn()}
            print("OK  ", name, flush=True)
        except Exception as e:  # noqa: BLE001
            res[name] = {"status": "fout", "reden": f"{type(e).__name__}: {e}"[:500],
                         "spoor": traceback.format_exc()[-800:]}
            print("FOUT", name, e, flush=True)
    (OUT / "proef.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str) + "\n")


if __name__ == "__main__":
    main()
