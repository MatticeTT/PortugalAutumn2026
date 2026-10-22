"""Invoer voor de plankscore per spot: golven, wind en getij per uur (golven, getij) of per 3 uur (wind).

Bronnen
  golven  Copernicus Marine. Waar de spot in het gebied van IBI ligt (26..56 N, 19 W..5 O): IBI, 1/36 graad, per uur.
          Elders: het wereldmodel MFWAM, 1/12 graad, per 3 uur. Per spot de dichtstbijzijnde zeecel bij het
          startpunt voor de kust (spots/kust.py). Per systeem (deining 1, deining 2, windzee): hoogte, richting
          (vandaan) en piekperiode Tp = Tm01 / 0,835.
  wind    ECMWF IFS open data 0,25 graad: 10u, 10v (wind op 10 m) en 10fg (windstoot), bilineair op het kustpunt.
  onweer  ECMWF mucape en cp: zie ONWEER_CAPE en ONWEER_CP_MM.
  getij   EOT20 (DGFI-TUM, CC BY 4.0) met pyTMD, om de 10 minuten op het kustpunt; met hoog- en laagwater van elke
          cyclus.

Schrijft één JSON-bestand (gzip) met per spot de reeksen, in UTC. De score (pipeline/spotscore.py) rekent daarmee.

Gebruik: python -m pipeline.spotinvoer --spots spots/spots.json --getij <map met EOT20> --uit data/spotinvoer.json.gz
"""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import math
import time
from pathlib import Path

import numpy as np

from pipeline import build, golven

IBI = "cmems_mod_ibi_wav_anfc_0.027deg_PT1H-i"
GLO = golven.DATASET
VARS = {"deining1": ("VHM0_SW1", "VMDR_SW1", "VTM01_SW1"), "deining2": ("VHM0_SW2", "VMDR_SW2", "VTM01_SW2"),
        "windzee": ("VHM0_WW", "VMDR_WW", "VTM01_WW")}
ZOEK_GRADEN = 0.25  # zeecel zoeken binnen deze afstand rond het startpunt


def utc(t) -> dt.datetime:
    return np.datetime64(t, "s").astype(dt.datetime).replace(tzinfo=dt.UTC)


def iso(t: dt.datetime) -> str:
    return t.strftime("%Y-%m-%dT%H:%MZ")


class Golfbron:
    """Eén Copernicus-dataset: zeecel per spot kiezen en per tijdstip alle variabelen op die cellen lezen."""

    def __init__(self, dataset: str):
        import copernicusmarine

        alle = [v for s in VARS.values() for v in s]
        self.ds = copernicusmarine.open_dataset(dataset_id=dataset, variables=alle + ["VHM0"])
        self.lat = self.ds["latitude"].values.astype(float)
        self.lon = self.ds["longitude"].values.astype(float)
        self.tijden = [utc(t) for t in self.ds["time"].values]
        self.naam = dataset

    def binnen(self, lat: float, lon: float) -> bool:
        return self.lat.min() + 0.2 <= lat <= self.lat.max() - 0.2 and self.lon.min() + 0.2 <= lon <= self.lon.max() - 0.2

    def kies_cellen(self, punten: list[tuple[float, float]], t: dt.datetime) -> list[tuple[int, int] | None]:
        """Dichtstbijzijnde cel met een golfwaarde rond elk punt (lat, lon)."""
        tt = np.datetime64(t.replace(tzinfo=None), "ns")
        veld = self.ds["VHM0"].sel(time=tt)
        uit = []
        for lat, lon in punten:
            j0, j1 = np.searchsorted(self.lat, [lat - ZOEK_GRADEN, lat + ZOEK_GRADEN])
            i0, i1 = np.searchsorted(self.lon, [lon - ZOEK_GRADEN, lon + ZOEK_GRADEN])
            blok = np.asarray(veld.isel(latitude=slice(j0, j1), longitude=slice(i0, i1)).values, dtype=float)
            jj, ii = np.nonzero(np.isfinite(blok))
            if not len(jj):
                uit.append(None)
                continue
            kx = math.cos(math.radians(lat))
            d = ((self.lat[j0 + jj] - lat) ** 2 + ((self.lon[i0 + ii] - lon) * kx) ** 2)
            k = int(np.argmin(d))
            uit.append((int(j0 + jj[k]), int(i0 + ii[k])))
        return uit

    def lees(self, t: dt.datetime, cellen: list[tuple[int, int]]) -> dict[str, np.ndarray]:
        """Alle variabelen op de gegeven cellen voor één tijdstip (één blok rond alle cellen, dan indexeren)."""
        tt = np.datetime64(t.replace(tzinfo=None), "ns")
        js, is_ = np.array([c[0] for c in cellen]), np.array([c[1] for c in cellen])
        j0, j1, i0, i1 = js.min(), js.max() + 1, is_.min(), is_.max() + 1
        uit = {}
        for v in [v for s in VARS.values() for v in s]:
            blok = np.asarray(self.ds[v].sel(time=tt).isel(latitude=slice(j0, j1), longitude=slice(i0, i1)).values,
                              dtype=np.float32)
            uit[v] = blok[js - j0, is_ - i0]
        return uit


def golven_per_spot(spots: list[dict], van: dt.datetime, tot: dt.datetime) -> tuple[list[dict | None], dict]:
    """Per spot: bron, cel en per tijdstip de drie systemen [H, richting, Tp]."""
    bronnen = {}
    res: list[dict | None] = [None] * len(spots)
    groepen: dict[str, list[int]] = {}
    ibi = Golfbron(IBI)
    for n, s in enumerate(spots):
        p = s.get("startpunt") or s["kustpunt"]
        groepen.setdefault(IBI if ibi.binnen(p[1], p[0]) else GLO, []).append(n)
    for naam, idx in groepen.items():
        bron = ibi if naam == IBI else Golfbron(GLO)
        tijden = [t for t in bron.tijden if van <= t <= tot]
        punten = [((spots[n].get("startpunt") or spots[n]["kustpunt"])[1], (spots[n].get("startpunt") or spots[n]["kustpunt"])[0]) for n in idx]
        cellen = bron.kies_cellen(punten, tijden[0])
        ok = [(n, c) for n, c in zip(idx, cellen) if c is not None]
        print(f"{naam}: {len(ok)}/{len(idx)} spots met een zeecel, {len(tijden)} tijdstippen", flush=True)
        reeks = {n: {k: [] for k in VARS} for n, _ in ok}
        t0 = time.time()
        for m, t in enumerate(tijden):
            w = bron.lees(t, [c for _, c in ok])
            for q, (n, _) in enumerate(ok):
                for k, (vh, vd, vt) in VARS.items():
                    h, d, tm = (float(w[x][q]) for x in (vh, vd, vt))
                    reeks[n][k].append(None if not np.isfinite(h) else
                                       [round(h, 2), round(d % 360, 1) if np.isfinite(d) else None,
                                        round(tm / golven.TM01_GEDEELD_DOOR_TP, 2) if np.isfinite(tm) else None])
            if m % 24 == 0:
                print(f"  {naam} {iso(t)}  {time.time() - t0:.0f} s", flush=True)
        for n, c in ok:
            res[n] = {"bron": naam, "cel": [round(float(bron.lat[c[0]]), 4), round(float(bron.lon[c[1]]), 4)],
                      "tijden": [iso(t) for t in tijden], **reeks[n]}
        bronnen[naam] = len(ok)
    return res, bronnen


def bilineair(veld: np.ndarray, lat: float, lon: float) -> float:
    """Veld (721, 1440) op 0,25 graad, breedte 90 .. -90, lengte 0 .. 359,75."""
    y, x = (90 - lat) * 4, (lon % 360) * 4
    j, i = int(math.floor(y)), int(math.floor(x))
    fy, fx = y - j, x - i
    j1, i1 = min(j + 1, veld.shape[0] - 1), (i + 1) % veld.shape[1]
    return float((1 - fy) * ((1 - fx) * veld[j, i] + fx * veld[j, i1]) + fy * ((1 - fx) * veld[j1, i] + fx * veld[j1, i1]))


def stoot_veld(run: dt.datetime, h: int) -> np.ndarray | None:
    """Windstoot 10fg: soms staan er twee in de index (max over de laatste 3 en over de laatste 6 uur); de kortste
    periode is het dichtst bij het uur zelf."""
    regels = [json.loads(x) for x in build.http_get(build.path(run, "oper", h, "index")).decode().splitlines() if x]
    e = [x for x in regels if x["param"] == "10fg" and x.get("levtype") == "sfc"]
    if not e:
        return None

    def duur(x):
        st = str(x.get("step", ""))
        a, _, b = st.partition("-")
        return (int(b) - int(a)) if b else 0

    x = min(e, key=duur)
    off, n = x["_offset"], x["_length"]
    return build.decode(build.http_get(build.path(run, "oper", h, "grib2"), (off, off + n - 1)))


# Onweer: geen bliksemveld in de open data. Voorzichtige aanwijzing (liever een vals alarm dan onweer missen):
# buiachtige neerslag (cp) in de stap ervoor EN onstabiele lucht (mucape) ergens in de 3 x 3 cellen rond de spot
# (ongeveer 25 km; de regel zegt bliksem binnen 16 km).
ONWEER_CAPE = 100.0  # J/kg; ECMWF maskeert de vertrekhoogte van MUCAPE onder 100 J/kg (geen diepe convectie)
ONWEER_CP_MM = 0.1  # mm buiachtige neerslag in de stap


def buurmax(veld: np.ndarray, lat: float, lon: float) -> float:
    j, i = int(round((90 - lat) * 4)), int(round((lon % 360) * 4)) % veld.shape[1]
    js = slice(max(j - 1, 0), min(j + 2, veld.shape[0]))
    blok = veld[js][:, [(i - 1) % veld.shape[1], i, (i + 1) % veld.shape[1]]]
    return float(np.nanmax(blok)) if np.isfinite(blok).any() else float("nan")


def wind_per_spot(spots: list[dict], max_uur: int) -> tuple[dt.datetime, list[dict]]:
    run = build.latest_run(max_uur)
    uren = build.hours(max_uur)
    res = [{"tijden": [], "u": [], "v": [], "stoot": [], "onweer": []} for _ in spots]
    cp_vorig = None
    for h in uren:
        f = build.fetch_fields(run, "oper", h, ("10u", "10v", "mucape", "cp"))
        cp_stap = None if cp_vorig is None else (f["cp"] - cp_vorig) * 1000  # m -> mm in deze stap
        cp_vorig = f["cp"]
        g = stoot_veld(run, h) if h > 0 else None
        if g is not None:
            f["10fg"] = g
        t = iso(run + dt.timedelta(hours=h))
        for n, s in enumerate(spots):
            lon, lat = s["kustpunt"]
            r = res[n]
            r["tijden"].append(t)
            r["u"].append(round(bilineair(f["10u"], lat, lon), 2))
            r["v"].append(round(bilineair(f["10v"], lat, lon), 2))
            r["stoot"].append(round(bilineair(f["10fg"], lat, lon), 2) if "10fg" in f else None)
            if cp_stap is None:
                r["onweer"].append(None)
            else:
                r["onweer"].append(bool(buurmax(f["mucape"], lat, lon) >= ONWEER_CAPE
                                        and buurmax(cp_stap, lat, lon) >= ONWEER_CP_MM))
    print(f"wind: ECMWF-run {iso(run)}, {len(uren)} stappen", flush=True)
    return run, res


def uitersten(h: np.ndarray) -> list[tuple[int, str, float]]:
    """Hoog- en laagwater: lokale uitersten, afwisselend hoog en laag."""
    ext: list[tuple[int, str, float]] = []
    for k in range(1, len(h) - 1):
        if (h[k] >= h[k - 1] and h[k] > h[k + 1]) or (h[k] <= h[k - 1] and h[k] < h[k + 1]):
            soort = "hoog" if h[k] > h[k - 1] else "laag"
            if ext and ext[-1][1] == soort:
                if (soort == "hoog") == (h[k] > ext[-1][2]):
                    ext[-1] = (k, soort, float(h[k]))
                continue
            ext.append((k, soort, float(h[k])))
    return ext


def getij_per_spot(spots: list[dict], map_: Path, van: dt.datetime, tot: dt.datetime) -> list[dict | None]:
    """Getij om de 10 minuten (m, t.o.v. gemiddeld zeeniveau) en de hoog- en laagwaters erin, alle spots in één keer
    (pyTMD 'time series': elke spot is een station)."""
    import pyTMD.compute

    stap = dt.timedelta(minutes=10)
    n_t = int((tot - van) / stap) + 1
    tijden = np.array([np.datetime64((van + k * stap).replace(tzinfo=None), "ns") for k in range(n_t)])
    lon = np.array([s["kustpunt"][0] for s in spots], dtype=float)
    lat = np.array([s["kustpunt"][1] for s in spots], dtype=float)
    tp = pyTMD.compute.tide_elevations(lon, lat, tijden, directory=map_, model="EOT20", type="time series",
                                       standard="datetime", extrapolate=True, cutoff=25.0)
    if "station" in tp.dims:
        tp = tp.transpose("station", ...)
    h_alle = np.asarray(tp.values, dtype=float).reshape(len(spots), -1)
    res: list[dict | None] = []
    for s, h in zip(spots, h_alle):
        if not np.isfinite(h).all():
            print(f"getij {s['naam']}: geen waarde (te ver van het getijmodel)", flush=True)
            res.append(None)
            continue
        res.append({"start": iso(van), "stap_min": 10, "h": [round(float(x), 3) for x in h],
                    "uitersten": [[iso(van + k * stap), soort, round(v, 3)] for k, soort, v in uitersten(h)]})
    return res


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--spots", type=Path, default=Path("spots/spots.json"))
    p.add_argument("--getij", type=Path, required=True, help="map die EOT20/ocean_tides bevat")
    p.add_argument("--uit", type=Path, default=Path("data/spotinvoer.json.gz"))
    p.add_argument("--uren", type=int, default=240)
    p.add_argument("--max", type=int, default=0, help="alleen de eerste n spots (om te testen)")
    a = p.parse_args(argv)

    from pipeline import spotscore

    alle = json.loads(a.spots.read_text())["spots"]
    stranden = spotscore.bodem_index()
    # Alleen spots die een score kunnen krijgen (zandstrand zonder gekende helling wordt niet gescoord).
    spots = [s for s in alle if spotscore.spotvelden(s, stranden)["herkomst"].get("tanb") != "onbekend"]
    print(f"{len(spots)} van {len(alle)} spots", flush=True)
    if a.max:
        spots = spots[:a.max]
    t0 = time.time()
    run, wind = wind_per_spot(spots, a.uren)
    van, tot = run, run + dt.timedelta(hours=a.uren)
    print(f"wind klaar na {time.time() - t0:.0f} s", flush=True)
    getij = getij_per_spot(spots, a.getij, van - dt.timedelta(hours=12), tot + dt.timedelta(hours=12))
    print(f"getij klaar na {time.time() - t0:.0f} s: {sum(g is not None for g in getij)}/{len(spots)}", flush=True)
    golf, bronnen = golven_per_spot(spots, van, tot)
    print(f"golven klaar na {time.time() - t0:.0f} s: {bronnen}", flush=True)

    uit = {"run": iso(run), "gemaakt": iso(dt.datetime.now(dt.UTC)),
           "bronnen": {"golven": "Generated using E.U. Copernicus Marine Service Information (IBI, MFWAM)",
                       "wind": "ECMWF IFS open data (CC BY 4.0)", "getij": "EOT20, DGFI-TUM (CC BY 4.0), via pyTMD"},
           "spots": [{"naam": s["naam"], "lat": s["lat"], "lon": s["lon"], "golven": g, "wind": w, "getij": h}
                     for s, g, w, h in zip(spots, golf, wind, getij)]}
    a.uit.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(a.uit, "wt") as f:
        json.dump(uit, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{a.uit}: {a.uit.stat().st_size / 1e6:.1f} MB", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
