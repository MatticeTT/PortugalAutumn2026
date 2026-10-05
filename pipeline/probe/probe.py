"""Mijlpaal 0: één echte aanroep per bron.

Elk antwoord wordt opgeslagen in tests/fixtures/probe/ en de veldnamen gaan
naar tests/fixtures/probe/FIELDS.md. Een bron die faalt, faalt niet de hele
run: de status staat in manifest.json.

Gebruik:
    python -m pipeline.probe.probe            # alle bronnen
    python -m pipeline.probe.probe ipma_warnings openmeteo_gfs_wind
"""

from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "tests" / "fixtures" / "probe"
UA = "surfkaart-portugal/0.1 (niet-commercieel, besloten)"

# Referentiepunt: zeevak voor Arrifana, een paar km uit de kust.
SEA_LAT, SEA_LON = 37.30, -8.92
# Strandpunt voor de wind: Praia da Rocha.
WIND_LAT, WIND_LON = 37.115, -8.535

WIND_VARS = "wind_speed_10m,wind_gusts_10m,wind_direction_10m"
WAVE_VARS = ",".join(
    [
        "wave_height", "wave_period", "wave_peak_period", "wave_direction",
        "swell_wave_height", "swell_wave_period", "swell_wave_peak_period", "swell_wave_direction",
        "secondary_swell_wave_height", "secondary_swell_wave_period", "secondary_swell_wave_direction",
        "wind_wave_height", "wind_wave_period", "wind_wave_peak_period", "wind_wave_direction",
    ]
)

EMODNET = "https://data-erddap.emodnet-physics.eu/erddap"
# Kaderrechthoek rond het vasteland, ruim genomen.
BBOX = dict(minLat=36.5, maxLat=42.3, minLon=-10.5, maxLon=-7.0)


def get(url: str, params: dict | None = None, timeout: int = 60) -> bytes:
    if params:
        url = f"{url}?{urllib.parse.urlencode(params, safe=',')}"
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def get_json(url: str, params: dict | None = None):
    return json.loads(get(url, params))


# --- bronnen -----------------------------------------------------------------


def openmeteo_wind(model: str):
    def run():
        return get_json(
            "https://api.open-meteo.com/v1/forecast",
            dict(latitude=WIND_LAT, longitude=WIND_LON, hourly=WIND_VARS, models=model,
                 wind_speed_unit="kn", timezone="UTC", forecast_days=2),
        )
    return run


def openmeteo_gfswave():
    return get_json(
        "https://marine-api.open-meteo.com/v1/marine",
        dict(latitude=SEA_LAT, longitude=SEA_LON, hourly=WAVE_VARS, models="ncep_gfswave016",
             timezone="UTC", forecast_days=2),
    )


def ipma_warnings():
    return get_json("https://api.ipma.pt/open-data/forecast/warnings/warnings_www.json")


def ipma_stations():
    return get_json("https://api.ipma.pt/open-data/observation/meteorology/stations/stations.json")


def ipma_observations():
    data = get_json("https://api.ipma.pt/open-data/observation/meteorology/stations/observations.json")
    # Het volledige bestand is groot (24 uur x alle stations). Bewaar het laatste uur.
    last = sorted(data)[-1]
    return {"_ingekort": f"alleen het laatste tijdstip van {len(data)}", last: data[last]}


def emodnet_search():
    """Zoek golfdatasets in de kaderrechthoek van Portugal."""
    params = dict(searchFor="wave", page=1, itemsPerPage=100, **BBOX)
    return get_json(f"{EMODNET}/search/advanced.json", params)


def emodnet_platforms():
    """Golfplatformen binnen de kaderrechthoek, uit de catalogus van EMODnet."""
    cons = (f"&latitude>={BBOX['minLat']}&latitude<={BBOX['maxLat']}"
            f"&longitude>={BBOX['minLon']}&longitude<={BBOX['maxLon']}")
    url = f"{EMODNET}/tabledap/ERD_EP_WAVES_INSITU_METADATA.json?{urllib.parse.quote(cons, safe='=&><.-')}"
    t = json.loads(get(url))["table"]
    return [dict(zip(t["columnNames"], r, strict=False)) for r in t["rows"]]


def emodnet_buoy():
    """Golfplatformen in Portugal uit de catalogus, daarna één dag metingen van één platform.

    Stap 1: de catalogus VHM0 (golfhoogte) filteren op de kaderrechthoek.
    Stap 2: per platform in de ERDDAP-zoekfunctie de datasets met dat platform zoeken
    en de eerste met VHM0 een dag laten teruggeven.
    """
    tried = []
    platforms = []
    for cat in ("ERD_EP_TS_VHM0_NRT_METADATA", "ERD_EP_WAVES_INSITU_METADATA"):
        cons = (f"&latitude>={BBOX['minLat']}&latitude<={BBOX['maxLat']}"
                f"&longitude>={BBOX['minLon']}&longitude<={BBOX['maxLon']}")
        url = f"{EMODNET}/tabledap/{cat}.json?{urllib.parse.quote(cons, safe='=&><.-')}"
        try:
            t = json.loads(get(url))["table"]
        except Exception as e:  # noqa: BLE001
            tried.append(f"{cat}: {e}")
            continue
        platforms = [dict(zip(t["columnNames"], r, strict=False)) for r in t["rows"]]
        catalog = cat
        break
    if not platforms:
        raise RuntimeError("geen platformcatalogus; " + " | ".join(tried))
    end = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    start = end - timedelta(days=1)
    found = {}
    for pf in platforms[:12]:
        code = pf.get("PLATFORMCODE")
        try:
            res = get_json(f"{EMODNET}/search/index.json", dict(searchFor=code, page=1, itemsPerPage=20))
            rows = [dict(zip(res["table"]["columnNames"], r, strict=False)) for r in res["table"]["rows"]]
        except Exception as e:  # noqa: BLE001
            tried.append(f"zoek {code}: {e}")
            continue
        found[code] = [r["Dataset ID"] for r in rows]
        for r in rows:
            if not r.get("tabledap") or r["Dataset ID"].endswith("_METADATA"):
                continue
            ds = r["Dataset ID"]
            try:
                info = get_json(f"{EMODNET}/info/{ds}/index.json")
            except Exception as e:  # noqa: BLE001
                tried.append(f"{ds}: info {e}")
                continue
            names = [x[1] for x in info["table"]["rows"] if x[0] == "variable"]
            if "VHM0" not in names:
                continue
            cols = [v for v in ("time", "latitude", "longitude", "PLATFORMCODE", "VHM0", "VTPK", "VMDR", "VTM02")
                    if v in names]
            cons = f"&time>={start:%Y-%m-%dT%H:%M:%SZ}&time<={end:%Y-%m-%dT%H:%M:%SZ}"
            if "PLATFORMCODE" in names:
                cons += f'&PLATFORMCODE="{code}"'
            url = f"{EMODNET}/tabledap/{ds}.json?{urllib.parse.quote(','.join(cols) + cons, safe='=&,><:-')}"
            try:
                data = json.loads(get(url, timeout=120))
            except Exception as e:  # noqa: BLE001
                tried.append(f"{ds}/{code}: data {e}")
                continue
            return {"catalogus": catalog, "platformen": platforms, "datasets_per_platform": found,
                    "dataset": ds, "platform": code, "variables": names, "query": url, "data": data,
                    "geprobeerd": tried}
    raise RuntimeError(json.dumps({"catalogus": catalog, "platformen": [
        {k: p.get(k) for k in ("PLATFORMCODE", "call_name", "latitude", "longitude", "lastDateObservation")}
        for p in platforms], "datasets_per_platform": found, "geprobeerd": tried}, ensure_ascii=False))


def hidrografico_collections():
    return get_json("https://api-features.hidrografico.pt/collections", {"f": "json"})


def openfreemap_style():
    style = get_json("https://tiles.openfreemap.org/styles/liberty")
    return {k: style[k] for k in ("version", "name", "sources", "glyphs", "sprite") if k in style} | {
        "_layers": len(style.get("layers", []))
    }


def copernicus_ibi():
    user = os.environ.get("COPERNICUSMARINE_SERVICE_USERNAME")
    if not user or not os.environ.get("COPERNICUSMARINE_SERVICE_PASSWORD"):
        raise SkipSource("geen Copernicus-account in de omgeving (COPERNICUSMARINE_SERVICE_USERNAME/PASSWORD)")
    import copernicusmarine  # noqa: PLC0415

    now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    ds = copernicusmarine.open_dataset(
        dataset_id="cmems_mod_ibi_wav_anfc_0.027deg_PT1H-i",
        minimum_longitude=SEA_LON - 0.03, maximum_longitude=SEA_LON + 0.03,
        minimum_latitude=SEA_LAT - 0.03, maximum_latitude=SEA_LAT + 0.03,
        start_datetime=now.isoformat(), end_datetime=(now + timedelta(hours=23)).isoformat(),
    )
    pt = ds.sel(latitude=SEA_LAT, longitude=SEA_LON, method="nearest")
    out = {
        "dataset_id": "cmems_mod_ibi_wav_anfc_0.027deg_PT1H-i",
        "punt": {"latitude": float(pt.latitude), "longitude": float(pt.longitude)},
        "variabelen": {v: {"long_name": ds[v].attrs.get("long_name"), "units": ds[v].attrs.get("units")}
                       for v in ds.data_vars},
        "time": [str(t)[:19] for t in pt.time.values],
    }
    for v in ds.data_vars:
        out[v] = [None if x != x else round(float(x), 3) for x in pt[v].values]
    return out


SOURCES = {
    "openmeteo_gfs_wind": openmeteo_wind("gfs_seamless"),
    "openmeteo_ecmwf_wind": openmeteo_wind("ecmwf_ifs"),
    "openmeteo_gfswave": openmeteo_gfswave,
    "copernicus_ibi": copernicus_ibi,
    "emodnet_search": emodnet_search,
    "emodnet_platforms": emodnet_platforms,
    "emodnet_buoy": emodnet_buoy,
    "ipma_warnings": ipma_warnings,
    "ipma_stations": ipma_stations,
    "ipma_observations": ipma_observations,
    "hidrografico_collections": hidrografico_collections,
    "openfreemap_style": openfreemap_style,
}


class SkipSource(Exception):
    pass


# --- veldnamen ---------------------------------------------------------------


def field_paths(obj, prefix="", depth=0, out=None):
    """Lijst van sleutelpaden, lijsten samengevat als [] en grote dicts met ID's ingekort."""
    out = out if out is not None else []
    if depth > 6:
        return out
    if isinstance(obj, dict):
        keys = list(obj)
        # Dicts met tijdstempels of station-ID's als sleutel: één voorbeeld volstaat.
        if len(keys) > 20 and all(not k.isidentifier() or k[:1].isdigit() for k in keys[:20]):
            out.append(f"{prefix}{{<{len(keys)} sleutels, bv. {keys[0]}>}}")
            return field_paths(obj[keys[0]], f"{prefix}{{*}}.", depth + 1, out)
        for k in keys:
            v = obj[k]
            out.append(f"{prefix}{k}: {type(v).__name__}")
            if isinstance(v, (dict, list)):
                field_paths(v, f"{prefix}{k}.", depth + 1, out)
    elif isinstance(obj, list) and obj:
        first = next((x for x in obj if isinstance(x, (dict, list))), None)
        if first is not None:
            field_paths(first, f"{prefix}[].", depth + 1, out)
    return out


def main(argv: list[str]) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    names = argv or list(SOURCES)
    manifest_path = OUT / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%MZ")
    for name in names:
        try:
            data = SOURCES[name]()
            (OUT / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n")
            manifest[name] = {"status": "ok", "op": stamp, "via": os.environ.get("PROBE_VIA", "lokaal")}
            print(f"OK    {name}")
        except SkipSource as e:
            manifest[name] = {"status": "overgeslagen", "op": stamp, "reden": str(e)}
            print(f"SKIP  {name}: {e}")
        except Exception as e:  # noqa: BLE001
            manifest[name] = {"status": "fout", "op": stamp, "reden": f"{type(e).__name__}: {e}"[:4000]}
            print(f"FOUT  {name}: {type(e).__name__}: {e}")
    manifest_path.write_text(json.dumps(dict(sorted(manifest.items())), ensure_ascii=False, indent=1) + "\n")
    write_fields(manifest)
    return 0


def write_fields(manifest: dict) -> None:
    lines = ["# Veldnamen per bron", "", "Gegenereerd door `pipeline/probe/probe.py`. Niet met de hand bewerken.", ""]
    for name, meta in manifest.items():
        lines += [f"## {name}", "", f"Status: {meta['status']} ({meta['op']}, via {meta.get('via', '?')})", ""]
        f = OUT / f"{name}.json"
        if meta["status"] == "ok" and f.exists():
            lines += ["```"] + field_paths(json.loads(f.read_text()))[:120] + ["```", ""]
        elif meta.get("reden"):
            lines += [f"Reden: {meta['reden']}", ""]
    (OUT / "FIELDS.md").write_text("\n".join(lines))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
