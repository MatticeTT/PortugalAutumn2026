"""Verkenning van de Copernicus-golfproducten voor de kaart (deining en windzee apart).

Draait in GitHub Actions (Copernicus is niet bereikbaar vanuit de ontwikkelomgeving).
Schrijft pipeline/verkenning/copernicus.json: datasets, variabelen, tijdbereik, roosters,
een proefwaarde op een paar punten en hoe lang één wereldwijd tijdstip ophalen duurt.
"""

import json
import time
from pathlib import Path

import copernicusmarine
import numpy as np

PRODUCTEN = [
    "GLOBAL_ANALYSISFORECAST_WAV_001_027",
    "IBI_ANALYSISFORECAST_WAV_005_005",
    "NWSHELF_ANALYSISFORECAST_WAV_004_014",
]
VARS = ["VHM0", "VMDR", "VTPK", "VHM0_SW1", "VMDR_SW1", "VTM01_SW1",
        "VHM0_SW2", "VMDR_SW2", "VTM01_SW2", "VHM0_WW", "VMDR_WW", "VTM01_WW"]
PUNTEN = {"Nazaré": (39.62, -9.20), "Hossegor": (43.67, -1.55), "Oostende": (51.25, 2.85)}
UIT = Path(__file__).parent / "verkenning" / "copernicus.json"


def beschrijf(product_id: str) -> dict:
    cat = copernicusmarine.describe(product_id=product_id).model_dump()
    uit = {}
    for p in cat.get("products", []):
        for ds in p.get("datasets", []):
            info = uit.setdefault(ds["dataset_id"], {"versies": []})
            for v in ds.get("versions", []):
                for part in v.get("parts", []):
                    for s in part.get("services", []):
                        if s.get("service_name") not in ("arco-geo-series", "arco-time-series"):
                            continue
                        info["versies"].append({
                            "versie": v.get("label"), "dienst": s.get("service_name"),
                            "variabelen": {
                                var.get("short_name"): {
                                    "naam": var.get("standard_name"), "eenheid": var.get("units"),
                                    "coordinaten": {c.get("coordinate_id"): {k: c.get(k) for k in (
                                        "minimum_value", "maximum_value", "step", "values")
                                        if c.get(k) is not None and k != "values"}
                                        for c in var.get("coordinates", [])},
                                } for var in s.get("variables", [])
                            },
                        })
    return uit


def proef(dataset_id: str, variabelen: list[str]) -> dict:
    t0 = time.time()
    ds = copernicusmarine.open_dataset(dataset_id=dataset_id, variables=variabelen)
    uit = {"open_s": round(time.time() - t0, 1), "dims": {k: int(v) for k, v in ds.sizes.items()},
           "tijd_eerste": str(ds["time"].values[0]), "tijd_laatste": str(ds["time"].values[-1]),
           "tijdstap_uur": float((ds["time"].values[1] - ds["time"].values[0]) / np.timedelta64(1, "h")),
           "punten": {}}
    laatste = ds["time"].values[-1]
    for naam, (lat, lon) in PUNTEN.items():
        try:
            p = ds.sel(latitude=lat, longitude=lon, method="nearest").sel(time=laatste)
            uit["punten"][naam] = {v: (None if np.isnan(float(p[v])) else round(float(p[v]), 2)) for v in variabelen}
        except Exception as e:  # noqa: BLE001 - punt buiten het gebied van dit product
            uit["punten"][naam] = str(e)[:120]
    t0 = time.time()
    veld = ds[variabelen[0]].sel(time=laatste).values
    uit["een_tijdstip_een_variabele_s"] = round(time.time() - t0, 1)
    uit["rooster"] = list(veld.shape)
    uit["zee_cellen"] = int(np.isfinite(veld).sum())
    ds.close()
    return uit


def main():
    rapport = {}
    for prod in PRODUCTEN:
        try:
            rapport[prod] = {"datasets": beschrijf(prod)}
        except Exception as e:  # noqa: BLE001
            rapport[prod] = {"fout": str(e)[:500]}
            continue
        for ds_id, info in rapport[prod]["datasets"].items():
            beschikbaar = set()
            for v in info["versies"]:
                beschikbaar |= set(v["variabelen"])
            gevraagd = [v for v in VARS if v in beschikbaar]
            if "anfc" in ds_id and gevraagd:
                try:
                    info["proef"] = proef(ds_id, gevraagd)
                except Exception as e:  # noqa: BLE001
                    info["proef"] = {"fout": str(e)[:500]}
            print(ds_id, sorted(beschikbaar), flush=True)
    UIT.parent.mkdir(parents=True, exist_ok=True)
    UIT.write_text(json.dumps(rapport, indent=1, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
