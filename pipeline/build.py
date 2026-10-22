"""Wereldwijde wind en golven per tijdstip omzetten naar compacte afbeeldingen voor de browser.

Wind: ECMWF IFS open data (CC BY 4.0), hetzelfde model dat Windy standaard toont, raster van 0,25 graad:
  10u, 10v (stream oper): wind op 10 m, oost- en noordcomponent in m/s.
De runs van 00 en 12 UTC lopen tot 360 uur (15 dagen): per 3 uur tot +144, daarna per 6 uur.
Golven: Copernicus Marine, deining en windzee apart, tot ongeveer 10 dagen vooruit (zie golven.py).
Zonder Copernicus-login (of met --ecmwf-golven) vallen de golven terug op ECMWF WAM (swh, mwd, pp1d), één laag.
Per veld wordt alleen het nodige stuk van het GRIB2-bestand opgehaald (byte-range via het .index-bestand).

Uitvoer (map --out, standaard web/public/data), lossless WebP:
  manifest.json                     run, tijdstippen, rasters en codering
  <uur>/wind.webp                   wereldraster van 1 graad, of 0,5 graad na --fine-hours tot --mid-hours
  <uur>/swell.webp, windsea.webp    deining en windzee, zelfde rasters, zolang het golfmodel loopt
  <uur>/wind/<rij>_<kol>.webp enz.  fijn raster (0,25 graad) in tegels van 45 x 45 graden, tot --fine-hours
                                    (windzee tot --windsea-fine-hours)

Codering (alle pixels ondoorzichtig):
  wind  R,G = u,v (m/s) met wortelcompressie: s = teken(x) * sqrt(|x| / WIND_MAX), byte = (s + 1) * 127.5
  golf  R,G = looprichting (eenheidsvector, oost/noord) maal (0.3 + 0.7 * T / T_MAX), byte = (x + 1) * 127.5
        B   = 0 op land; anders 1 + 254 * sqrt(Hs / H_MAX)
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import eccodes
import numpy as np
from PIL import Image

from pipeline import golven

# Spiegels van dezelfde bestanden; Google Cloud remt het minst.
MIRRORS = (
    "https://storage.googleapis.com/ecmwf-open-data",
    "https://ecmwf-forecasts.s3.eu-central-1.amazonaws.com",
    "https://data.ecmwf.int/forecasts",
)
WIND_MAX = 50.0  # m/s
H_MAX = 20.0  # m
T_MAX = 25.0  # s
NI, NJ = 1440, 721  # 0,25 graad; na het verschuiven: lengte 0..359,75 oost, breedte 90 noord .. 90 zuid
TILE_DEG = 45
TILE_PX = TILE_DEG * 4  # 180 cellen; de tegel krijgt er één rij en kolom bij voor naadloos interpoleren
EXT = "webp"

WIND_FIELDS = ("10u", "10v")
WAVE_FIELDS = ("swh", "mwd", "pp1d")


def hours(max_hour: int) -> list[int]:
    """Alle stappen van ECMWF: per 3 uur tot 144, daarna per 6 uur."""
    return [h for h in range(0, max_hour + 1, 3) if h <= 144 or h % 6 == 0]


def path(run: dt.datetime, stream: str, h: int, ext: str) -> str:
    d, c = run.strftime("%Y%m%d"), run.strftime("%H")
    return f"{d}/{c}z/ifs/0p25/{stream}/{d}{c}0000-{h}h-{stream}-fc.{ext}"


def http_get(rel: str, byte_range: tuple[int, int] | None = None, tries: int = 6) -> bytes:
    headers = {"Range": f"bytes={byte_range[0]}-{byte_range[1]}"} if byte_range else {}
    err: Exception | None = None
    for i in range(tries):
        base = MIRRORS[i % len(MIRRORS)]
        try:
            with urllib.request.urlopen(urllib.request.Request(f"{base}/{rel}", headers=headers), timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404 and i >= len(MIRRORS) - 1:
                raise
            err = e
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            err = e
        time.sleep(min(30, 2**i))
    raise RuntimeError(f"{rel}: {err}")


def exists(rel: str) -> bool:
    try:
        req = urllib.request.Request(f"{MIRRORS[0]}/{rel}", method="HEAD")
        with urllib.request.urlopen(req, timeout=30):
            return True
    except urllib.error.HTTPError:
        return False


def latest_run(last_hour: int, now: dt.datetime | None = None) -> dt.datetime:
    """Nieuwste run van 00 of 12 UTC waarvan wind en golven tot het laatste uur klaarstaan."""
    now = now or dt.datetime.now(dt.UTC)
    t = now.replace(minute=0, second=0, microsecond=0, hour=now.hour - now.hour % 12)
    for _ in range(6):
        if exists(path(t, "oper", last_hour, "index")) and exists(path(t, "wave", last_hour, "index")):
            return t
        t -= dt.timedelta(hours=12)
    raise RuntimeError("Geen volledige ECMWF-run gevonden in de laatste 3 dagen")


def fetch_fields(run: dt.datetime, stream: str, h: int, wanted: tuple[str, ...]) -> dict[str, np.ndarray]:
    """Haalt de gevraagde velden op als (NJ, NI)-raster vanaf lengte 0, NaN waar geen waarde is."""
    entries = [json.loads(line) for line in http_get(path(run, stream, h, "index")).decode().splitlines() if line]
    out: dict[str, np.ndarray] = {}
    for p in wanted:
        e = [x for x in entries if x["param"] == p and x.get("levtype") == "sfc"]
        if len(e) != 1:
            raise RuntimeError(f"{p} niet eenduidig in {stream} +{h}h")
        off, n = e[0]["_offset"], e[0]["_length"]
        out[p] = decode(http_get(path(run, stream, h, "grib2"), (off, off + n - 1)))
    return out


def decode(msg: bytes) -> np.ndarray:
    g = eccodes.codes_new_from_message(msg)
    try:
        ni, nj = eccodes.codes_get(g, "Ni"), eccodes.codes_get(g, "Nj")
        lon0 = eccodes.codes_get(g, "longitudeOfFirstGridPointInDegrees") % 360
        if (ni, nj) != (NI, NJ) or eccodes.codes_get(g, "jScansPositively") != 0:
            raise RuntimeError(f"Onverwacht raster {ni}x{nj}")
        if eccodes.codes_get(g, "latitudeOfFirstGridPointInDegrees") != 90:
            raise RuntimeError("Raster begint niet op 90 noord")
        missing = eccodes.codes_get(g, "missingValue")
        vals = eccodes.codes_get_values(g).astype(np.float32)
    finally:
        eccodes.codes_release(g)
    vals[vals == missing] = np.nan
    grid = vals.reshape(NJ, NI)
    # ECMWF begint op 180 graden (= -180); verschuiven zodat kolom 0 op lengte 0 ligt.
    return np.roll(grid, -int(round(lon0 * 4)) % NI, axis=1) if lon0 else grid


COAST_FILL = 4  # cellen (van 0,25 graad) dat golfwaarden landinwaarts worden doorgetrokken


def fill_coast(hs: np.ndarray, dirp: np.ndarray, per: np.ndarray, cells: int = COAST_FILL):
    """Golfwaarden een paar cellen landinwaarts doortrekken (gemiddelde van de zeeburen).

    Het golfmodel rekent kustcellen vaak als land, waardoor er een strook zonder golven langs de kust blijft.
    De browser tekent de golven onder de landlaag van de basiskaart, die ze precies op de kustlijn afsnijdt;
    daarvoor moeten er tot aan die kustlijn waarden zijn. Richting wordt als eenheidsvector gemiddeld.
    """
    to = np.radians(dirp)
    fields = [hs.copy(), np.sin(to), np.cos(to), per.copy()]
    for _ in range(cells):
        known = np.isfinite(fields[0])
        sums = [np.zeros_like(f) for f in fields]
        count = np.zeros(hs.shape, np.float32)
        for dj in (-1, 0, 1):
            for di in (-1, 0, 1):
                if dj == di == 0:
                    continue
                k = np.roll(np.roll(known, dj, axis=0), di, axis=1)
                if dj == 1:
                    k[0] = False
                elif dj == -1:
                    k[-1] = False
                count += k
                for t, f in zip(sums, fields):
                    t += np.where(k, np.roll(np.roll(np.nan_to_num(f), dj, axis=0), di, axis=1), 0)
        new = ~known & (count > 0)
        for t, f in zip(sums, fields):
            f[new] = t[new] / count[new]
    h, sx, cy, t = fields
    return h, np.degrees(np.arctan2(sx, cy)) % 360, t


def encode_wind(u: np.ndarray, v: np.ndarray) -> np.ndarray:
    def comp(x):
        s = np.sign(x) * np.sqrt(np.minimum(np.abs(np.nan_to_num(x)), WIND_MAX) / WIND_MAX)
        return np.clip(np.rint((s + 1) * 127.5), 0, 255).astype(np.uint8)

    rgb = np.zeros(u.shape + (3,), np.uint8)
    rgb[..., 0], rgb[..., 1] = comp(u), comp(v)
    return rgb


def encode_wave(hs: np.ndarray, dirp: np.ndarray, per: np.ndarray) -> np.ndarray:
    sea = np.isfinite(hs) & np.isfinite(dirp)
    # mwd is de richting waar de golven vandaan komen (meteorologisch, graden vanaf noord).
    # Looprichting = die richting + 180 graden.
    to = np.radians(np.nan_to_num(dirp) + 180.0)
    t = np.clip(np.nan_to_num(per, nan=8.0), 0, T_MAX) / T_MAX
    scale = 0.3 + 0.7 * t
    ex, ny = np.sin(to) * scale, np.cos(to) * scale
    rgb = np.zeros(hs.shape + (3,), np.uint8)
    rgb[..., 0] = np.clip(np.rint((ex + 1) * 127.5), 0, 255)
    rgb[..., 1] = np.clip(np.rint((ny + 1) * 127.5), 0, 255)
    h = np.clip(np.nan_to_num(hs), 0, H_MAX)
    rgb[..., 2] = np.where(sea, np.clip(np.rint(1 + 254 * np.sqrt(h / H_MAX)), 1, 255), 0)
    rgb[~sea, 0:2] = 128
    return rgb


def save_img(rgb: np.ndarray, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.ascontiguousarray(rgb), "RGB").save(dest, "WEBP", lossless=True, quality=90, method=4)


def box_mean(x: np.ndarray, w: np.ndarray | None = None) -> np.ndarray:
    """Gemiddelde over de 3 x 3 buren (lengte loopt rond), eventueel gewogen; NaN telt niet mee."""
    w = np.isfinite(x).astype(np.float32) if w is None else w * np.isfinite(x)
    xs = np.nan_to_num(x) * w
    num = np.zeros_like(xs)
    den = np.zeros_like(xs)
    pad_x = np.pad(xs, ((1, 1), (0, 0)), mode="edge")
    pad_w = np.pad(w, ((1, 1), (0, 0)), mode="edge")
    for dj in (0, 1, 2):
        for di in (-1, 0, 1):
            num += np.roll(pad_x[dj : dj + NJ], di, axis=1)
            den += np.roll(pad_w[dj : dj + NJ], di, axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(den > 0, num / den, np.nan)


def coarse_wind(u: np.ndarray, v: np.ndarray, step: int) -> np.ndarray:
    return encode_wind(box_mean(u)[::step, ::step], box_mean(v)[::step, ::step])


def coarse_wave(hs: np.ndarray, dirp: np.ndarray, per: np.ndarray, step: int) -> np.ndarray:
    """Grof golfraster: richting als gemiddelde van de looprichtingen, gewogen naar golfhoogte; het land/zee-
    masker van de middelste cel blijft behouden, zodat de kustlijn niet opschuift."""
    sea = np.isfinite(hs) & np.isfinite(dirp)
    to = np.radians(dirp)
    w = np.where(sea, np.nan_to_num(hs), 0).astype(np.float32) + 1e-3
    sx, cy = box_mean(np.sin(to), w), box_mean(np.cos(to), w)
    d = np.degrees(np.arctan2(sx, cy)) % 360
    h, t = box_mean(np.where(sea, hs, np.nan)), box_mean(np.where(sea, per, np.nan))
    h, d, t = (np.where(sea, x, np.nan)[::step, ::step] for x in (h, d, t))
    return encode_wave(h, d, t)


def write_tiles(rgb: np.ndarray, base: Path, name: str) -> None:
    """Fijne tegels (0,25 graad) van één veld."""
    wrapped = np.concatenate([rgb, rgb[:, :1]], axis=1)  # kolom 1440 = kolom 0 (lengte 360 = 0)
    for r in range(180 // TILE_DEG):
        for c in range(360 // TILE_DEG):
            j0, i0 = r * TILE_PX, c * TILE_PX
            save_img(wrapped[j0 : j0 + TILE_PX + 1, i0 : i0 + TILE_PX + 1], base / name / f"{r}_{c}.{EXT}")


def write_waves(base: Path, name: str, hs: np.ndarray, dirp: np.ndarray, per: np.ndarray, step: int, fine: bool) -> None:
    hs, dirp, per = fill_coast(hs, dirp, per)
    save_img(coarse_wave(hs, dirp, per, step), base / f"{name}.{EXT}")
    if fine:
        write_tiles(encode_wave(hs, dirp, per), base, name)


def process_hour(run: dt.datetime, h: int, out: Path, fine: bool, coarse_deg: float,
                 bron: "golven.Bron | None", windsea_fine: bool) -> tuple[int, bool]:
    """Eén tijdstip; geeft terug of er golven voor zijn."""
    wind = fetch_fields(run, "oper", h, WIND_FIELDS)
    base = out / f"{h:03d}"
    step = int(coarse_deg * 4)
    u, v = (wind[k] for k in WIND_FIELDS)
    save_img(coarse_wind(u, v, step), base / f"wind.{EXT}")
    if fine:
        write_tiles(encode_wind(u, v), base, "wind")
    t = run + dt.timedelta(hours=h)
    if bron is not None:
        if not bron.heeft(t):
            return h, False
        for name in golven.SYSTEMEN:
            write_waves(base, name, *bron.velden(t, name), step, fine and (name == "swell" or windsea_fine))
        return h, True
    # Reserve zonder Copernicus: ECMWF WAM, één laag (totale zee) als deining getoond.
    wave = fetch_fields(run, "wave", h, WAVE_FIELDS)
    write_waves(base, "swell", *(wave[k] for k in WAVE_FIELDS), step, fine)
    return h, True


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--out", type=Path, default=Path("web/public/data"))
    p.add_argument("--max-hour", type=int, default=360)
    # Vercel (gratis plan) aanvaardt hooguit 100 MB per publicatie: de verre toekomst grover.
    p.add_argument("--fine-hours", type=int, default=120, help="fijne tegels (0,25 graad) tot dit uur")
    p.add_argument("--mid-hours", type=int, default=240, help="daarna wereldraster van 0,5 graad tot dit uur, dan 1")
    p.add_argument("--windsea-fine-hours", type=int, default=48, help="fijne tegels voor de windzee tot dit uur")
    p.add_argument("--ecmwf-golven", action="store_true", help="golven van ECMWF WAM in plaats van Copernicus")
    p.add_argument("--workers", type=int, default=4)
    a = p.parse_args(argv)

    hs = hours(a.max_hour)

    def coarse_deg(h: int) -> float:
        return 0.5 if a.fine_hours < h <= a.mid_hours else 1.0

    run = latest_run(hs[-1])
    print(f"ECMWF-run {run:%Y-%m-%d %H}Z, {len(hs)} tijdstippen", flush=True)
    bron = None
    if not a.ecmwf_golven:
        if not golven.beschikbaar():
            raise SystemExit("Geen Copernicus-login (COPERNICUSMARINE_SERVICE_USERNAME/PASSWORD); gebruik --ecmwf-golven")
        bron = golven.Bron()
        print(f"Copernicus-golven tot {bron.laatste:%Y-%m-%d %H}Z", flush=True)
    a.out.mkdir(parents=True, exist_ok=True)
    met_golven: dict[int, bool] = {}
    with ThreadPoolExecutor(a.workers) as ex:
        for h, g in ex.map(lambda h: process_hour(run, h, a.out, h <= a.fine_hours, coarse_deg(h), bron,
                                                   h <= a.windsea_fine_hours), hs):
            met_golven[h] = g
            print(f"  +{h:03d} u klaar{'' if g else ' (geen golven)'}", flush=True)

    manifest = {
        "run": run.strftime("%Y-%m-%dT%H:%MZ"),
        "source": "Wind: ECMWF IFS open data 0,25 graad (CC BY 4.0). Golven: "
                  + ("ECMWF WAM" if bron is None else "Generated using E.U. Copernicus Marine Service Information (MFWAM)"),
        "ext": EXT,
        "times": [{"h": h, "time": (run + dt.timedelta(hours=h)).strftime("%Y-%m-%dT%H:%MZ"),
                   "coarseDeg": coarse_deg(h), "fine": h <= a.fine_hours,
                   "waves": met_golven[h], "wavesFine": met_golven[h] and h <= a.fine_hours,
                   "windsea": met_golven[h] and bron is not None,
                   "windseaFine": met_golven[h] and bron is not None and h <= min(a.fine_hours, a.windsea_fine_hours)}
                  for h in hs],
        "fine": {"deg": 0.25, "tileDeg": TILE_DEG, "tilePx": TILE_PX + 1,
                 "rows": 180 // TILE_DEG, "cols": 360 // TILE_DEG},
        "encoding": {"windMax": WIND_MAX, "waveHMax": H_MAX, "wavePeriodMax": T_MAX},
    }
    (a.out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
