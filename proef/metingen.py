"""Metingen ophalen en opschonen: NDBC-boeien, METAR via IEM, Copernicus Marine In Situ.

Elke functie geeft uurwaarden op het raster fouten.UREN met vaste kolomnamen:
wind_kn, windrichting, vlaag_kn, hs_m, tp_s, tm_s, golfrichting, sst_c.
"""

import io
import os
import re
from pathlib import Path

import numpy as np
import pandas as pd

from .fouten import KN_PER_MS, UREN, afstand_km, naar_10m, uurgemiddelde, uurmaximum_vorig_uur
from .logboek import Logboek

START, EIND = UREN[0], UREN[-1]
VENSTER_START = START - pd.Timedelta(hours=1)
VENSTER_EIND = EIND + pd.Timedelta(hours=1)

# ---------------------------------------------------------------- NDBC

NDBC_MAAND = "https://www.ndbc.noaa.gov/data/stdmet/Sep/{id}.txt"
NDBC_REALTIME = "https://www.ndbc.noaa.gov/data/realtime2/{id}.txt"
NDBC_PAGINA = "https://www.ndbc.noaa.gov/station_page.php?station={id}"
# Ontbrekende waarden per kolom volgens NDBC ('MM' in realtime, 99/999/9999 in archief).
# Let op: 99 is een geldige richting, dus per kolom en niet over alles heen.
NDBC_ONTBREKEND = {"WDIR": 999, "MWD": 999, "WSPD": 99, "GST": 99, "WVHT": 99, "DPD": 99, "APD": 99, "WTMP": 999}


def lees_ndbc(tekst: str, log: Logboek, bron: str) -> pd.DataFrame:
    regels = tekst.splitlines()
    kop = next((r for r in regels if r.startswith("#YY") or r.startswith("YY")), None)
    if kop is None:
        raise ValueError("geen kopregel #YY")
    namen = kop.lstrip("#").split()
    data = [r.split() for r in regels if r and not r.startswith("#") and not r.startswith("YY")]
    df = pd.DataFrame([d[: len(namen)] for d in data if len(d) >= len(namen)], columns=namen)
    jaar = df[namen[0]].astype(int)
    jaar = jaar.where(jaar > 100, jaar + 2000)
    tijd = pd.to_datetime(dict(year=jaar, month=df.MM.astype(int), day=df.DD.astype(int),
                               hour=df.hh.astype(int), minute=df.mm.astype(int)), utc=True)
    uit = pd.DataFrame(index=tijd)
    for kol, code in NDBC_ONTBREKEND.items():
        if kol not in df:
            continue
        ruw = df[kol].replace("MM", np.nan)
        w = pd.to_numeric(ruw, errors="coerce").to_numpy(dtype=float, copy=True)
        ontbreekt_mm = ruw.isna().to_numpy()
        code_mask = np.isclose(w, code)
        log.filter(bron, f"{kol}: ontbrekend (MM)", int(ontbreekt_mm.sum()))
        log.filter(bron, f"{kol}: ontbrekend (code {code})", int(code_mask.sum()))
        w[code_mask] = np.nan
        uit[kol] = w
    uit = uit[~uit.index.duplicated()].sort_index()
    return uit[(uit.index >= VENSTER_START) & (uit.index <= VENSTER_EIND)]


def ndbc_station(log: Logboek, sid: str) -> dict:
    """Positie en anemometerhoogte van de stationspagina van NDBC."""
    r = log.get(NDBC_PAGINA.format(id=sid))
    tekst = re.sub(r"<[^>]+>", " ", r.text) if r.ok else ""
    info = {"id": sid, "lat": None, "lon": None, "anemometer_m": None}
    m = re.search(r"(\d+\.\d+)\s*([NS])\s+(\d+\.\d+)\s*([EW])", tekst)
    if m:
        info["lat"] = float(m.group(1)) * (1 if m.group(2) == "N" else -1)
        info["lon"] = float(m.group(3)) * (1 if m.group(4) == "E" else -1)
    m = re.search(r"Anemometer height:\s*([\d.]+)\s*m", tekst, re.I)
    if m:
        info["anemometer_m"] = float(m.group(1))
    return info


def ndbc(log: Logboek, sid: str) -> tuple[pd.DataFrame, dict]:
    bron = f"NDBC {sid}"
    info = ndbc_station(log, sid)
    delen = []
    for soort, url in (("maandarchief", NDBC_MAAND), ("realtime2", NDBC_REALTIME)):
        r = log.get(url.format(id=sid))
        if not r.ok:
            log.info(f"{bron}: {soort} niet beschikbaar (HTTP {r.status_code})")
            continue
        try:
            df = lees_ndbc(r.text, log, f"{bron} {soort}")
        except ValueError as e:
            log.info(f"{bron}: {soort} onleesbaar ({e})")
            continue
        log.info(f"{bron}: {soort} {len(df)} regels in september")
        delen.append((soort, df))
    if not delen:
        return pd.DataFrame(index=UREN), info
    ruw = delen[0][1]
    if len(delen) == 2:
        voor = ruw.notna().sum().sum()
        ruw = ruw.combine_first(delen[1][1]) if delen[0][0] == "maandarchief" else ruw
        log.info(f"{bron}: realtime2 vult {int(ruw.notna().sum().sum() - voor)} ontbrekende waarden van het maandarchief aan")
    info["bronbestand"] = "+".join(s for s, _ in delen)

    hoogte = info["anemometer_m"]
    uit = pd.DataFrame(index=UREN)
    if "WSPD" in ruw:
        factor = naar_10m(1.0, hoogte) if hoogte else 1.0
        uit["wind_kn"] = uurgemiddelde(ruw.WSPD * KN_PER_MS * factor)
        uit["vlaag_kn"] = uurmaximum_vorig_uur(ruw.GST * KN_PER_MS * factor) if "GST" in ruw else np.nan
        uit["windrichting"] = uurgemiddelde(ruw.WDIR, richting=True) if "WDIR" in ruw else np.nan
    if "WVHT" in ruw:
        uit["hs_m"] = uurgemiddelde(ruw.WVHT)
        uit["tp_s"] = uurgemiddelde(ruw.DPD)
        uit["tm_s"] = uurgemiddelde(ruw.APD)
        uit["golfrichting"] = uurgemiddelde(ruw.MWD, richting=True)
    if "WTMP" in ruw:
        uit["sst_c"] = uurgemiddelde(ruw.WTMP)
    return uit.reindex(UREN), info


# ---------------------------------------------------------------- METAR (IEM)

IEM_NETWERK = "https://mesonet.agron.iastate.edu/geojson/network/{net}.geojson"
IEM_ASOS = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"


def metar_kandidaten(log: Logboek, netwerken, lat, lon, max_km=100.0) -> list[dict]:
    kand = {}
    for net in netwerken:
        r = log.get(IEM_NETWERK.format(net=net))
        if not r.ok:
            log.info(f"IEM-netwerk {net}: HTTP {r.status_code}")
            continue
        for f in r.json().get("features", []):
            p = f["properties"]
            einde = p.get("archive_end")
            if einde and einde < "2026-09-30":
                continue
            x, y = f["geometry"]["coordinates"]
            d = float(afstand_km(lat, lon, y, x))
            if d <= max_km:
                kand[f["id"]] = {"id": f["id"], "naam": p.get("sname"), "lat": y, "lon": x,
                                 "afstand_km": d, "netwerk": net, "hoogte_m": p.get("elevation")}
    return sorted(kand.values(), key=lambda k: k["afstand_km"])


def metar(log: Logboek, station: str) -> pd.DataFrame:
    params = {
        "station": station, "data": ["sknt", "drct", "gust"],
        "sts": VENSTER_START.strftime("%Y-%m-%dT%H:%MZ"), "ets": VENSTER_EIND.strftime("%Y-%m-%dT%H:%MZ"),
        "tz": "Etc/UTC", "format": "onlycomma", "latlon": "yes", "missing": "empty",
        "trace": "empty", "report_type": ["3", "4"],
    }
    r = log.get(IEM_ASOS, params=params)
    bron = f"METAR {station}"
    if not r.ok:
        log.info(f"{bron}: HTTP {r.status_code} {r.text[:200]}")
        return pd.DataFrame(index=UREN)
    df = pd.read_csv(io.StringIO(r.text))
    if df.empty:
        return pd.DataFrame(index=UREN)
    df.index = pd.to_datetime(df["valid"], utc=True)
    for k in ("sknt", "drct", "gust"):
        df[k] = pd.to_numeric(df.get(k), errors="coerce")
    log.filter(bron, "windsnelheid ontbreekt in bericht", int(df.sknt.isna().sum()))
    uit = pd.DataFrame(index=UREN)
    uit["wind_kn"] = uurgemiddelde(df.sknt)
    uit["windrichting"] = uurgemiddelde(df.drct.where(df.sknt > 0), richting=True)
    # Een METAR noemt enkel een vlaag als die er is; zonder vlaaggroep geldt de gemiddelde wind als hoogste waarde.
    uit["vlaag_kn"] = uurmaximum_vorig_uur(df.gust.fillna(df.sknt))
    return uit.reindex(UREN)


# ---------------------------------------------------------------- Copernicus Marine In Situ

CMEMS_DATASET = "cmems_obs-ins_glo_phybgcwav_mynrt_na_irr"
CMEMS_MAAND = "202609"


def copernicus_inloggen(log: Logboek) -> bool:
    ok = bool(os.environ.get("COPERNICUSMARINE_SERVICE_USERNAME")) and bool(os.environ.get("COPERNICUSMARINE_SERVICE_PASSWORD"))
    log.antwoord("Copernicus: namen van de omgevingsvariabelen voor de Toolbox", True,
                 "COPERNICUSMARINE_SERVICE_USERNAME en COPERNICUSMARINE_SERVICE_PASSWORD; "
                 + ("aanwezig in deze run" if ok else "NIET aanwezig in deze run: Copernicus-metingen worden 'geen meting'"))
    return ok


def copernicus_index(log: Logboek, map_: Path) -> pd.DataFrame:
    import copernicusmarine

    map_.mkdir(parents=True, exist_ok=True)
    copernicusmarine.get(dataset_id=CMEMS_DATASET, index_parts=True, no_directories=True,
                         output_directory=map_, overwrite=True)
    pad = map_ / "index_monthly.txt"
    kopregel = None
    with pad.open(encoding="utf-8-sig") as f:
        for i, regel in enumerate(f):
            kol = [c.strip().lstrip("#").strip() for c in regel.strip().split(",")]
            if {"product_id", "file_name"}.issubset(kol):
                kopregel = i
                break
    if kopregel is None:
        raise ValueError("geen kopregel in index_monthly.txt")
    df = pd.read_csv(pad, skiprows=kopregel)
    df.columns = df.columns.str.lstrip("#").str.strip()
    for k in ("geospatial_lat_min", "geospatial_lat_max", "geospatial_lon_min", "geospatial_lon_max"):
        df[k] = pd.to_numeric(df[k], errors="coerce")
    df = df[df.file_name.str.contains(f"/{CMEMS_MAAND}/", regex=False)]
    df["lat"] = (df.geospatial_lat_min + df.geospatial_lat_max) / 2
    df["lon"] = (df.geospatial_lon_min + df.geospatial_lon_max) / 2
    df["vaste_positie"] = ((df.geospatial_lat_max - df.geospatial_lat_min).abs() < 0.05) & \
                          ((df.geospatial_lon_max - df.geospatial_lon_min).abs() < 0.05)
    df["params"] = df.parameters.fillna("").str.split().apply(set)
    df["soort"] = df.file_name.str.extract(r"/monthly/([A-Z]+)/")[0]
    log.info(f"Copernicus-index: {len(df)} bestanden voor {CMEMS_MAAND}; soorten: {df.soort.value_counts().to_dict()}")
    return df


def copernicus_kandidaten(index: pd.DataFrame, variabele: str, lat, lon, max_km=100.0) -> pd.DataFrame:
    k = index[index.params.apply(lambda p: variabele in p) & index.vaste_positie].copy()
    k["afstand_km"] = afstand_km(lat, lon, k.lat.to_numpy(), k.lon.to_numpy())
    return k[k.afstand_km <= max_km].sort_values("afstand_km")


def copernicus_download(file_name: str, map_: Path) -> Path:
    import copernicusmarine

    map_.mkdir(parents=True, exist_ok=True)
    lijst = map_ / "lijst.txt"
    lijst.write_text(file_name + "\n")
    copernicusmarine.get(dataset_id=CMEMS_DATASET, file_list=lijst, output_directory=map_,
                         no_directories=True, skip_existing=True)
    return map_ / file_name.rsplit("/", 1)[-1]


def goede_vlag(qc) -> int | None:
    """Zoek in de attributen van een _QC-variabele welke waarde 'good_data' betekent."""
    waarden = np.atleast_1d(qc.attrs.get("flag_values", []))
    betekenis = str(qc.attrs.get("flag_meanings", "")).split()
    for w, b in zip(waarden, betekenis):
        if b == "good_data":
            return int(w)
    return None


def copernicus_lees(pad: Path, log: Logboek, vlaglog: dict) -> pd.DataFrame:
    import xarray as xr

    bron = f"Copernicus {pad.name}"
    ds = xr.open_dataset(pad, decode_timedelta=False)
    tijd = pd.to_datetime(ds["TIME"].values, utc=True)
    diepte = ds["DEPH"].values if "DEPH" in ds else None
    ruw = {}
    for var in ("VHM0", "VTPK", "VTM02", "VMDR", "TEMP"):
        if var not in ds:
            continue
        x = ds[var].values.astype(float)
        if x.ndim == 1:
            x = x[:, None]
        if f"{var}_QC" in ds:
            qc = ds[f"{var}_QC"]
            goed = goede_vlag(qc)
            vlaglog[var] = goed
            if goed is None:
                goed = 1
            q = qc.values
            if q.ndim == 1:
                q = q[:, None]
            slecht = (q != goed) & ~np.isnan(x)
            log.filter(bron, f"{var}: kwaliteitsvlag niet 'good_data'", int(slecht.sum()))
            x = np.where(q == goed, x, np.nan)
        # Kolom kiezen: TEMP het ondiepste meetpunt, golven de kolom met de meeste geldige waarden.
        if var == "TEMP" and diepte is not None:
            d = diepte if diepte.ndim == 2 else np.broadcast_to(diepte, x.shape)
            gem = np.nanmean(np.where(np.isnan(x), np.nan, np.abs(d)), axis=0)
            kol = int(np.nanargmin(gem)) if np.isfinite(gem).any() else 0
        else:
            kol = int(np.argmax(np.sum(~np.isnan(x), axis=0)))
        ruw[var] = pd.Series(x[:, kol], index=tijd)
    ds.close()
    uit = pd.DataFrame(index=UREN)
    kaart = {"VHM0": "hs_m", "VTPK": "tp_s", "VTM02": "tm_s", "TEMP": "sst_c"}
    for var, naam in kaart.items():
        if var in ruw:
            uit[naam] = uurgemiddelde(ruw[var])
    if "VMDR" in ruw:
        uit["golfrichting"] = uurgemiddelde(ruw["VMDR"], richting=True)
    return uit.reindex(UREN)
