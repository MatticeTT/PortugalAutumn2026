"""M6, stap 0: kunnen we de nauwkeurigheid meten met historische gegevens?

Eén proef per bron, zoals in M0. Schrijft data/validate/proef.json met per bron de status
en een korte samenvatting. Draait in GitHub Actions (netwerk open, Copernicus-account).
"""

from __future__ import annotations

import gzip
import io
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
    """Copernicus In-Situ (IBI): welke golfboeien in Portugal hebben recente metingen?"""
    if not os.environ.get("COPERNICUSMARINE_SERVICE_USERNAME"):
        raise RuntimeError("geen Copernicus-account")
    import copernicusmarine

    desc = copernicusmarine.describe(product_id="INSITU_IBI_PHYBGCWAV_DISCRETE_MYNRT_013_033")
    datasets = []
    for prod in desc.products:
        for ds in prod.datasets:
            datasets.append(ds.dataset_id)
    out = {"datasets": datasets}
    # De lijst met platformen staat in een indexbestand; zoek boeien bij Portugal.
    for ds_id in datasets:
        if "nrt" not in ds_id and "mynrt" not in ds_id:
            continue
        try:
            res = copernicusmarine.get(dataset_id=ds_id, filter="*index_platform*",
                                       output_directory=str(OUT / "insitu"), disable_progress_bar=True)
            files = [str(f.file_path) for f in getattr(res, "files", [])]
            out[ds_id] = {"indexbestanden": files}
            for f in files:
                txt = Path(f).read_text(errors="replace").splitlines()
                pt = [ln for ln in txt if any(k in ln for k in ("Sines", "Leixoes", "Leixões", "Faro", "Nazare",
                                                                  "6201081", "6201077", "6201079"))]
                out[ds_id]["portugal"] = pt[:30]
        except Exception as e:  # noqa: BLE001
            out[ds_id] = f"fout: {type(e).__name__}: {e}"[:300]
    return out


def meteostat():
    """Meteostat bulk: uurlijkse metingen van een kuststation (Faro, 08554)."""
    raw = gzip.decompress(get("https://bulk.meteostat.net/v2/hourly/08554.csv.gz", timeout=300))
    rows = list(io.StringIO(raw.decode()).read().splitlines())
    recent = [r for r in rows if r[:10] >= START.isoformat()]
    return {"regels": len(rows), "laatste": rows[-1][:80] if rows else None, "recent": len(recent),
            "kolommen": "date,hour,temp,dwpt,rhum,prcp,snow,wdir,wspd,wpgt,pres,tsun,coco"}


PROBES = {
    "open_meteo_previous_runs_wind": previous_runs_wind,
    "open_meteo_historical_forecast_wind": historical_forecast_wind,
    "open_meteo_golven_verleden": marine_past,
    "copernicus_ibi_verleden": ibi_past,
    "copernicus_insitu_boeien": insitu_buoys,
    "meteostat_wind_faro": meteostat,
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
