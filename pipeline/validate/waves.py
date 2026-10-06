"""M6: golfmodellen naast boeimetingen (Copernicus In-Situ, laatste ±30 dagen).

Per boei: de gemeten significante golfhoogte (VHM0) en periodes, naast
- GFS-Wave 16 km (Open-Meteo Marine, het model van Windguru)
- Copernicus IBI 3 km
op hetzelfde uur. Beide modellen zijn hier hun "beste schatting" van dat uur
(analyse en eerste uren van de voorspelling), niet een voorspelling van dagen vooraf.

Schrijft data/validate/golven.json (statistiek per boei en per model) en meldt ook
welke andere variabelen de boeien meten (bv. wind), voor latere metingen.
"""

from __future__ import annotations

import json
import math
import os
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "validate"
DL = OUT / "insitu"
UA = "surfkaart-portugal/0.1 (niet-commercieel, besloten)"
DATASET = "cmems_obs-ins_ibi_phybgcwav_mynrt_na_irr"

BUOYS = {
    "Leixões (open zee)": "6201077",
    "Leixões (kustboei)": "Leixoes-coast-buoy",
    "Sines (kustboei)": "Sines-coast-buoy",
    "Faro (open zee)": "6201079",
    "Faro (kustboei)": "Faro-coast-buoy",
}


def download(code: str) -> list[Path]:
    import copernicusmarine

    target = DL / code
    copernicusmarine.get(dataset_id=DATASET, filter=f"*/latest/*_{code}_*", output_directory=str(target),
                         no_directories=True, disable_progress_bar=True, overwrite=True)
    return sorted(target.glob("*.nc"))


def read_obs(files: list[Path]):
    """Uurgemiddelden van VHM0, VTPK en VTM02 met goede kwaliteitsvlag, plus de ligging."""
    import numpy as np
    import xarray as xr

    hourly: dict[str, dict[str, list[float]]] = {}
    lat = lon = None
    other: set[str] = set()
    for f in files:
        ds = xr.open_dataset(f)
        other |= {v for v in ds.data_vars if not v.endswith("_QC") and not v.endswith("_DM")}
        lat = float(np.nanmean(ds["LATITUDE"].values)) if "LATITUDE" in ds else lat
        lon = float(np.nanmean(ds["LONGITUDE"].values)) if "LONGITUDE" in ds else lon
        times = ds["TIME"].values
        for v in ("VHM0", "VTPK", "VTM02", "VGHS"):
            if v not in ds:
                continue
            vals = ds[v].values
            vals = vals.reshape(len(times), -1)[:, 0] if vals.ndim > 1 else vals
            qc = ds.get(f"{v}_QC")
            qcv = None if qc is None else (qc.values.reshape(len(times), -1)[:, 0] if qc.ndim > 1 else qc.values)
            for i, t in enumerate(times):
                x = float(vals[i])
                if not math.isfinite(x) or (qcv is not None and int(qcv[i]) not in (1, 2)):
                    continue
                key = str(t)[:13] + ":00"
                # Boeien in open zee geven de golfhoogte als VGHS (generic significant height).
                hourly.setdefault(key, {}).setdefault("VHM0" if v == "VGHS" else v, []).append(x)
        ds.close()
    obs = {t: {v: sum(xs) / len(xs) for v, xs in d.items()} for t, d in hourly.items()}
    return obs, lat, lon, sorted(other)


def gfswave(lat: float, lon: float, start: str, end: str) -> dict[str, dict[str, float]]:
    q = urllib.parse.urlencode({"latitude": lat, "longitude": lon, "hourly": "wave_height,wave_period",
                                "models": "ncep_gfswave016", "start_date": start, "end_date": end, "timezone": "UTC"})
    req = urllib.request.Request(f"https://marine-api.open-meteo.com/v1/marine?{q}", headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.loads(r.read())
    h = d["hourly"]
    # wave_period van GFS-Wave ligt dicht bij de gemeten piekperiode (VTPK), niet bij VTM02.
    return {t: {"VHM0": a, "VTPK": b} for t, a, b in zip(h["time"], h["wave_height"], h["wave_period"], strict=True)
            if a is not None}, (d["longitude"], d["latitude"])


def ibi(lat: float, lon: float, start: str, end: str):
    import copernicusmarine
    import numpy as np

    ds = copernicusmarine.open_dataset(
        dataset_id="cmems_mod_ibi_wav_anfc_0.027deg_PT1H-i", variables=["VHM0", "VTPK", "VTM02"],
        minimum_longitude=lon - 0.1, maximum_longitude=lon + 0.1,
        minimum_latitude=lat - 0.1, maximum_latitude=lat + 0.1,
        start_datetime=f"{start}T00:00:00", end_datetime=f"{end}T23:00:00")
    mask = np.isfinite(ds["VHM0"].isel(time=0).values)
    yy, xx = np.nonzero(mask)
    glat, glon = ds.latitude.values, ds.longitude.values
    j = int(np.argmin((glat[yy] - lat) ** 2 + ((glon[xx] - lon) * math.cos(math.radians(lat))) ** 2))
    pt = ds.isel(latitude=int(yy[j]), longitude=int(xx[j])).load()
    out = {}
    for i, t in enumerate(pt.time.values):
        rec = {v: float(pt[v].values[i]) for v in ("VHM0", "VTPK", "VTM02") if math.isfinite(float(pt[v].values[i]))}
        if rec:
            out[str(t)[:16]] = rec
    return out, (float(glon[xx[j]]), float(glat[yy[j]]))


def stats(pairs: list[tuple[float, float]]) -> dict | None:
    if len(pairs) < 24:
        return None
    n = len(pairs)
    mo = sum(o for o, _ in pairs) / n
    mm = sum(m for _, m in pairs) / n
    bias = mm - mo
    rmse = math.sqrt(sum((m - o) ** 2 for o, m in pairs) / n)
    so = math.sqrt(sum((o - mo) ** 2 for o, _ in pairs) / n)
    sm = math.sqrt(sum((m - mm) ** 2 for _, m in pairs) / n)
    cov = sum((o - mo) * (m - mm) for o, m in pairs) / n
    return {"n": n, "gemiddeld_gemeten": round(mo, 3), "afwijking": round(bias, 3), "rmse": round(rmse, 3),
            "spreidingsindex": round(rmse / mo, 3) if mo else None,
            "correlatie": round(cov / (so * sm), 3) if so and sm else None}


def main():
    if not os.environ.get("COPERNICUSMARINE_SERVICE_USERNAME"):
        raise SystemExit("geen Copernicus-account")
    OUT.mkdir(parents=True, exist_ok=True)
    result = {"gemaakt": datetime.now(UTC).strftime("%Y-%m-%dT%H:%MZ"), "boeien": {}}
    for name, code in BUOYS.items():
        rec: dict = {"code": code}
        try:
            files = download(code)
            obs, lat, lon, other = read_obs(files)
            rec |= {"bestanden": len(files), "uren_gemeten": len(obs), "ligging": [lon, lat], "variabelen": other}
            if not obs:
                raise RuntimeError("geen bruikbare metingen")
            times = sorted(obs)
            start = times[0][:10]
            end = min(times[-1][:10], (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%d"))
            rec["periode"] = [times[0], times[-1]]
            models = {}
            try:
                models["GFS-Wave"], rec["gfswave_rasterpunt"] = gfswave(lat, lon, start, end)
            except Exception as e:  # noqa: BLE001
                rec["gfswave_fout"] = str(e)[:200]
            try:
                models["IBI"], rec["ibi_rasterpunt"] = ibi(lat, lon, start, end)
            except Exception as e:  # noqa: BLE001
                rec["ibi_fout"] = str(e)[:200]
            rec["vergelijking"] = {}
            for mname, m in models.items():
                rec["vergelijking"][mname] = {}
                for var in ("VHM0", "VTM02", "VTPK"):
                    pairs = [(obs[t][var], m[t][var]) for t in times if var in obs[t] and t in m and var in m[t]]
                    s = stats(pairs)
                    if s:
                        rec["vergelijking"][mname][var] = s
        except Exception as e:  # noqa: BLE001
            rec["fout"] = f"{type(e).__name__}: {e}"[:400]
        result["boeien"][name] = rec
        print(name, json.dumps(rec.get("vergelijking", rec.get("fout")), ensure_ascii=False)[:600], flush=True)
    (OUT / "golven.json").write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n")


if __name__ == "__main__":
    main()
