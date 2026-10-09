"""Bodemgegevens per strand (opdracht van de rekenchat). Voegt alleen velden toe; de score verandert niet.

Stap 1  diepteprofiel: EMODnet Bathymetry DTM (raster 1/16 boogminuut, ~115 m). Per strand een lijn van het
        kustpunt 2.000 m de zee in, in de kijkrichting. Het raster wordt in blokken van 1 x 1 graad gedownload
        (WCS) en lokaal uitgelezen (bilineair). EMODnet geeft hoogte: negatief onder water, positief op land.
        diepte = -hoogte, dus positief = water onder het referentievlak (LAT waar het getij groot is, anders MSL).
Stap 2  bodemtype: Global Coastal Characteristics (Zenodo 10.5281/zenodo.11072020, CC BY 4.0), kolom
        coast_type_flag, dichtste punt binnen 1.500 m.
Stap 3  getijverschil: MHWS - MLWS van het gekoppelde TICON-4-station (getij.mjs), voor Portugal geïnterpoleerd
        tussen de twee stations zoals het getij zelf.
Stap 4  afgeleide schattingen (startregels): helling_klasse, getij_voorkeur, bodem_zekerheid.

Schrijft data/beaches/bodem/bodem.json ({strand_id: velden}) en data/beaches/bodem/rapport.json.
"""

from __future__ import annotations

import csv
import json
import math
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BEACHES = ROOT / "data" / "beaches"
TIDES = ROOT / "data" / "tides"
OUT = BEACHES / "bodem"
CACHE = Path("/tmp/emodnet")
UA = {"User-Agent": "surfkaart-portugal/0.1 (niet-commercieel, besloten)"}

AFSTANDEN = [100, 200, 300, 500, 750, 1000, 1500, 2000]
STAP_M = 25
GCC_URL = "https://zenodo.org/api/records/11072020/files/GCC_geophysical.csv/content"
GCC_MAX_M = 1500
WCS = ("https://ows.emodnet-bathymetry.eu/wcs?service=WCS&version=1.0.0&request=GetCoverage&coverage=emodnet:mean"
       "&crs=EPSG:4326&bbox={x0},{y0},{x1},{y1}&format=image/tiff&resx={r}&resy={r}")
RES = 1 / 960  # 1/16 boogminuut
# coast_type_flag van GCC (Hulskamp e.a. 2023): Sandy, Rocky, Muddy, Vegetated, Other of leeg (verkenning2.json).
# Leeg = geen klasse: bodem_type blijft dan leeg.
BODEM = {"sandy": "zand", "rocky": "rots", "muddy": "slik", "vegetated": "anders", "other": "anders"}

VOORKEUR = {("zand", "vlak"): "half tot hoog", ("zand", "gemiddeld"): "half", ("zand", "steil"): "laag"}


def get(url: str, timeout: int = 600) -> bytes:
    for poging in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            print("opnieuw", poging, url[:120], e, flush=True)
            time.sleep(10 * (poging + 1))
    raise RuntimeError(f"niet bereikbaar: {url}")


def stranden() -> list[dict]:
    uit = []
    for land, path in [("pt", BEACHES / "stranden.geojson"), *[(p.stem, p) for p in sorted((BEACHES / "landen").glob("*.geojson"))]]:
        for f in json.loads(path.read_text())["features"]:
            p = f["properties"]
            lon, lat = f["geometry"]["coordinates"]
            uit.append({"id": p["id"], "land": land, "naam": p["naam"], "lon": lon, "lat": lat,
                        "kijkrichting": p["kijkrichting"], "besloten_water": bool(p.get("besloten_water")),
                        "getij_voorkeur": p.get("getij_voorkeur")})
    return uit


def verplaats(lon: float, lat: float, richting: float, m: float) -> tuple[float, float]:
    r = math.radians(richting)
    dlat = m * math.cos(r) / 111_320
    dlon = m * math.sin(r) / (111_320 * math.cos(math.radians(lat)))
    return lon + dlon, lat + dlat


# ---------- stap 1: EMODnet ----------

class Raster:
    """Blokken van 1 x 1 graad, op schijf bewaard; bilineair uitlezen. Geeft hoogte (negatief = onder water)."""

    def __init__(self) -> None:
        CACHE.mkdir(parents=True, exist_ok=True)
        self.blokken: dict[tuple[int, int], tuple | None] = {}
        self.fouten: list[str] = []

    def blok(self, bx: int, by: int):
        if (bx, by) in self.blokken:
            return self.blokken[(bx, by)]
        import rasterio
        p = CACHE / f"{bx}_{by}.tif"
        if not p.exists():
            try:
                b = get(WCS.format(x0=bx, y0=by, x1=bx + 1, y1=by + 1, r=RES), timeout=900)
                if not b.startswith((b"II*", b"MM\x00")):
                    raise RuntimeError(b[:300].decode("utf8", "replace"))
                p.write_bytes(b)
            except Exception as e:  # noqa: BLE001
                self.fouten.append(f"blok {bx},{by}: {e}"[:300])
                self.blokken[(bx, by)] = None
                return None
        with rasterio.open(p) as ds:
            a = ds.read(1).astype("float64")
            if ds.nodata is not None:
                a[a == ds.nodata] = np.nan
            a[np.abs(a) > 20000] = np.nan
            self.blokken[(bx, by)] = (a, ds.transform)
        print("blok", bx, by, a.shape, flush=True)
        return self.blokken[(bx, by)]

    def hoogte(self, lon: float, lat: float) -> float | None:
        b = self.blok(math.floor(lon), math.floor(lat))
        if b is None:
            return None
        a, t = b
        # pixelcentra: kolom = (lon - x0)/dx - 0.5
        c = (lon - t.c) / t.a - 0.5
        r = (lat - t.f) / t.e - 0.5
        c0, r0 = math.floor(c), math.floor(r)
        if not (0 <= c0 < a.shape[1] - 1 and 0 <= r0 < a.shape[0] - 1):
            c0, r0 = min(max(round(c), 0), a.shape[1] - 1), min(max(round(r), 0), a.shape[0] - 1)
            v = a[r0, c0]
            return None if np.isnan(v) else float(v)
        fc, fr = c - c0, r - r0
        w = a[r0:r0 + 2, c0:c0 + 2]
        g = np.array([[(1 - fr) * (1 - fc), (1 - fr) * fc], [fr * (1 - fc), fr * fc]])
        m = ~np.isnan(w)
        if not m.any():
            return None
        return float((w[m] * g[m]).sum() / g[m].sum())


def profiel(rs: Raster, s: dict) -> dict:
    stappen = list(range(0, 2001, STAP_M))
    h = [rs.hoogte(*verplaats(s["lon"], s["lat"], s["kijkrichting"], m)) for m in stappen]
    diepte = {m: (None if v is None else round(-v, 2)) for m, v in zip(stappen, h, strict=True)}
    if all(v is None for v in diepte.values()):
        return {"diepte_profiel": None}

    def eerste(grens: float):
        vorige_m, vorige_d = None, None
        for m in stappen:
            d = diepte[m]
            if d is None:
                continue
            if d >= grens:
                if vorige_d is None or vorige_d >= grens:
                    return m
                return round(vorige_m + (grens - vorige_d) / (d - vorige_d) * (m - vorige_m))
            vorige_m, vorige_d = m, d
        return None

    a5, a10 = eerste(5), eerste(10)
    return {
        "diepte_profiel": {str(m): diepte[m] for m in AFSTANDEN},
        "diepte_kustpunt": diepte[0],
        "afstand_tot_5m_m": a5, "afstand_tot_10m_m": a10,
        "helling_0_5m": round(5 / a5, 4) if a5 else None,
        "helling_0_10m": round(10 / a10, 4) if a10 else None,
        "_ruw": diepte,
    }


# ---------- stap 2: GCC ----------

def gcc_punten(ss: list[dict]) -> dict[tuple[int, int], list]:
    cellen = {(math.floor(s["lon"] * 50), math.floor(s["lat"] * 50)) for s in ss}
    nodig = {(x + dx, y + dy) for x, y in cellen for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
    p = Path("/tmp/GCC_geophysical.csv")
    if not p.exists():
        p.write_bytes(get(GCC_URL, timeout=1800))
    rooster = defaultdict(list)
    waarden = Counter()
    with p.open(encoding="utf8") as fh:
        for row in csv.DictReader(fh):
            lon, lat = float(row["lon"]), float(row["lat"])
            k = (math.floor(lon * 50), math.floor(lat * 50))
            if k in nodig:
                rooster[k].append((lon, lat, row["coast_type_flag"], row["id"]))
                waarden[row["coast_type_flag"]] += 1
    print("GCC coast_type_flag in de buurt van onze stranden:", waarden.most_common(), flush=True)
    return rooster


def km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    t = math.pi / 180
    h = (math.sin((lat2 - lat1) * t / 2) ** 2
         + math.cos(lat1 * t) * math.cos(lat2 * t) * math.sin((lon2 - lon1) * t / 2) ** 2)
    return 2 * 6371 * math.asin(math.sqrt(h))


def bodem(rooster, s: dict) -> dict:
    x, y = math.floor(s["lon"] * 50), math.floor(s["lat"] * 50)
    beste = None
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for lon, lat, flag, gid in rooster.get((x + dx, y + dy), []):
                d = km(s["lat"], s["lon"], lat, lon) * 1000
                if beste is None or d < beste[0]:
                    beste = (d, flag, gid)
    if beste is None or beste[0] > GCC_MAX_M:
        return {"bodem_type": None, "bodem_afstand_m": round(beste[0]) if beste else None, "gcc_kusttype": None}
    flag = (beste[1] or "").strip()
    return {"bodem_type": BODEM.get(flag.lower()), "bodem_afstand_m": round(beste[0]),
            "gcc_kusttype": flag or None, "gcc_id": beste[2]}


# ---------- stap 3: getij ----------

def getij() -> dict[str, float | None]:
    st = json.loads((OUT / "getij_stations.json").read_text())
    uit = {}
    for f in ("stranden_getij.json", "stranden_getij_landen.json"):
        for sid, g in json.loads((TIDES / f).read_text()).items():
            a, b = st.get(g["a"]), st.get(g["b"])
            if a and b:
                uit[sid] = round((1 - g["w"]) * a["verschil_m"] + g["w"] * b["verschil_m"], 2)
    return uit


def klasse_getij(v: float | None) -> str | None:
    if v is None:
        return None
    return "klein" if v < 2 else "middel" if v <= 4 else "groot"


def klasse_helling(h: float | None) -> str | None:
    if h is None:
        return None
    return "vlak" if h < 1 / 50 else "gemiddeld" if h <= 1 / 20 else "steil"


# ---------- alles ----------

def main() -> None:
    ss = stranden()
    print(len(ss), "stranden", Counter(s["land"] for s in ss), flush=True)
    rs = Raster()
    rooster = gcc_punten(ss)
    gv = getij()
    uit, vreemd = {}, []
    for i, s in enumerate(ss):
        if i % 500 == 0:
            print(i, flush=True)
        r = profiel(rs, s)
        ruw = r.pop("_ruw", None)
        r.update(bodem(rooster, s))
        r["getijverschil_m"] = gv.get(s["id"])
        r["getij_klasse"] = klasse_getij(r["getijverschil_m"])
        if not s["besloten_water"]:
            r["helling_klasse"] = klasse_helling(r.get("helling_0_5m"))
            if s["getij_voorkeur"] is None:
                r["getij_voorkeur"] = VOORKEUR.get((r["bodem_type"], r["helling_klasse"]))
                r["getij_voorkeur_bron"] = "geschat" if r["getij_voorkeur"] else None
            d100 = (r.get("diepte_profiel") or {}).get("100")
            ontbreekt = r.get("diepte_profiel") is None or r["bodem_type"] is None
            r["bodem_zekerheid"] = "laag" if ontbreekt or (d100 is not None and d100 > 10) else "middel"
        # onlogisch: land waar zee verwacht wordt
        if ruw:
            land_ver = [m for m, d in ruw.items() if d is not None and d < 0 and m >= 300]
            if land_ver:
                vreemd.append({"id": s["id"], "land": s["land"], "naam": s["naam"], "soort": "land in de kijkrichting",
                               "vanaf_m": land_ver[0], "hoogte_m": -ruw[land_ver[0]]})
            if (r.get("diepte_profiel") or {}).get("100") is not None and r["diepte_profiel"]["100"] > 10:
                vreemd.append({"id": s["id"], "land": s["land"], "naam": s["naam"], "soort": "dieper dan 10 m op 100 m",
                               "diepte_100": r["diepte_profiel"]["100"]})
            if r["afstand_tot_5m_m"] is None and all(d is not None for d in ruw.values()):
                vreemd.append({"id": s["id"], "land": s["land"], "naam": s["naam"], "soort": "geen 5 m diep binnen 2 km",
                               "diepte_2000": ruw[2000]})
        uit[s["id"]] = r

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "bodem.json").write_text(json.dumps(uit, ensure_ascii=False) + "\n")

    rapport: dict = {"per_land": {}, "raster_fouten": rs.fouten, "onlogisch": vreemd}
    for land in sorted({s["land"] for s in ss}):
        ids = [s["id"] for s in ss if s["land"] == land]
        rr = [uit[i] for i in ids]
        rapport["per_land"][land] = {
            "stranden": len(ids),
            "met_profiel": sum(r["diepte_profiel"] is not None for r in rr),
            "met_afstand_5m": sum(r["afstand_tot_5m_m"] is not None for r in rr if r["diepte_profiel"]),
            "met_bodem_type": sum(r["bodem_type"] is not None for r in rr),
            "met_getijverschil": sum(r["getijverschil_m"] is not None for r in rr),
            "helling_klasse": Counter(str(r.get("helling_klasse")) for r in rr).most_common(),
            "bodem_type": Counter(str(r["bodem_type"]) for r in rr).most_common(),
            "gcc_kusttype": Counter(str(r.get("gcc_kusttype")) for r in rr).most_common(),
            "getij_klasse": Counter(str(r["getij_klasse"]) for r in rr).most_common(),
            "getij_voorkeur": Counter(str(r.get("getij_voorkeur")) for r in rr).most_common(),
            "bodem_zekerheid": Counter(str(r.get("bodem_zekerheid")) for r in rr).most_common(),
            "onlogisch": Counter(v["soort"] for v in vreemd if v["land"] == land).most_common(),
        }
    namen = {"be": "KNOKKE-HEIST LEKKERBEK", "fr": "Plage de la Gravière", "es": "Zurriola",
             "pt": "Supertubos (Praia do Medão)"}
    rapport["voorbeelden"] = {}
    for land, naam in namen.items():
        for s in ss:
            if s["land"] == land and s["naam"] == naam:
                rapport["voorbeelden"][f"{land}: {naam}"] = {"id": s["id"], "lon": s["lon"], "lat": s["lat"],
                                                              "kijkrichting": s["kijkrichting"], **uit[s["id"]]}
                break
    (OUT / "rapport.json").write_text(json.dumps(rapport, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({k: v for k, v in rapport.items() if k != "onlogisch"}, ensure_ascii=False, indent=1)[:15000])
    print(len(vreemd), "onlogisch")
    if rs.fouten:
        print("rasterfouten:", rs.fouten[:20], file=sys.stderr)


if __name__ == "__main__":
    main()
