"""Wereldwijde wind (GFS) en golven (GFS-Wave / WaveWatch III) per tijdstip omzetten naar PNG's.

Bron: NOAA GFS op AWS Open Data (noaa-gfs-bdp-pds), raster van 0,25 graad. Per veld wordt alleen het
nodige stuk van het GRIB2-bestand opgehaald (byte-range via het .idx-bestand).

Uitvoer (map --out, standaard web/public/data):
  manifest.json                 run, tijdstippen, rasters en codering
  <uur>/wind.png, <uur>/wave.png      grof wereldraster (1 graad, 360 x 181)
  <uur>/wind/<rij>_<kol>.png enz.      fijn raster (0,25 graad) in tegels van 45 x 45 graden

Codering (alle pixels ondoorzichtig, alfa 255):
  wind  R,G = u,v (m/s) met wortelcompressie: s = teken(x) * sqrt(|x| / WIND_MAX), byte = (s + 1) * 127.5
  golf  R,G = looprichting (eenheidsvector, oost/noord) maal (0.3 + 0.7 * T / T_MAX), byte = (x + 1) * 127.5
        B   = 0 op land; anders 1 + 254 * sqrt(Hs / H_MAX)
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import eccodes
import numpy as np
from PIL import Image

BUCKET = "https://noaa-gfs-bdp-pds.s3.amazonaws.com"
WIND_MAX = 50.0  # m/s
H_MAX = 20.0  # m
T_MAX = 25.0  # s
NI, NJ = 1440, 721  # 0,25 graad, lengte 0..359,75 oost, breedte 90 noord .. 90 zuid
TILE_DEG = 45
TILE_PX = TILE_DEG * 4  # 180 cellen; de tegel krijgt er één rij en kolom bij voor naadloos interpoleren
COARSE_STEP = 4  # 1 graad

WIND_FIELDS = ("UGRD:10 m above ground", "VGRD:10 m above ground")
WAVE_FIELDS = ("HTSGW:surface", "DIRPW:surface", "PERPW:surface")


def hours(max_hour: int, step: int) -> list[int]:
    return list(range(0, max_hour + 1, step))


def atmos_url(day: str, cycle: str, h: int) -> str:
    return f"{BUCKET}/gfs.{day}/{cycle}/atmos/gfs.t{cycle}z.pgrb2.0p25.f{h:03d}"


def wave_url(day: str, cycle: str, h: int) -> str:
    return f"{BUCKET}/gfs.{day}/{cycle}/wave/gridded/gfswave.t{cycle}z.global.0p25.f{h:03d}.grib2"


def http_get(url: str, byte_range: tuple[int, int | None] | None = None, tries: int = 4) -> bytes:
    headers = {}
    if byte_range:
        a, b = byte_range
        headers["Range"] = f"bytes={a}-{'' if b is None else b}"
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise
            err = e
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            err = e
        if i < tries - 1:
            import time

            time.sleep(2 ** (i + 1))
    raise RuntimeError(f"{url}: {err}")


def exists(url: str) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=30):
            return True
    except urllib.error.HTTPError:
        return False


def latest_run(last_hour: int, now: dt.datetime | None = None) -> dt.datetime:
    """Nieuwste run waarvan zowel wind als golven tot het laatste uur klaarstaan."""
    now = now or dt.datetime.now(dt.UTC)
    t = now.replace(minute=0, second=0, microsecond=0, hour=now.hour - now.hour % 6)
    for _ in range(8):
        day, cycle = t.strftime("%Y%m%d"), t.strftime("%H")
        if exists(atmos_url(day, cycle, last_hour) + ".idx") and exists(wave_url(day, cycle, last_hour) + ".idx"):
            return t
        t -= dt.timedelta(hours=6)
    raise RuntimeError("Geen volledige GFS-run gevonden in de laatste 48 uur")


def fetch_fields(url: str, wanted: tuple[str, ...]) -> dict[str, np.ndarray]:
    """Haalt de gevraagde velden op en geeft ze als (NJ, NI)-raster, NaN waar geen waarde is."""
    idx = http_get(url + ".idx").decode().strip().splitlines()
    starts = [(int(line.split(":")[1]), line) for line in idx]
    out: dict[str, np.ndarray] = {}
    for key in wanted:
        var, level = key.split(":")
        for n, (start, line) in enumerate(starts):
            parts = line.split(":")
            if parts[3] == var and parts[4] == level:
                end = starts[n + 1][0] - 1 if n + 1 < len(starts) else None
                out[key] = decode(http_get(url, (start, end)))
                break
        else:
            raise RuntimeError(f"{key} ontbreekt in {url}")
    return out


def decode(msg: bytes) -> np.ndarray:
    g = eccodes.codes_new_from_message(msg)
    try:
        ni, nj = eccodes.codes_get(g, "Ni"), eccodes.codes_get(g, "Nj")
        if (ni, nj) != (NI, NJ) or eccodes.codes_get(g, "jScansPositively") != 0:
            raise RuntimeError(f"Onverwacht raster {ni}x{nj}")
        missing = eccodes.codes_get(g, "missingValue")
        vals = eccodes.codes_get_values(g).astype(np.float32)
    finally:
        eccodes.codes_release(g)
    vals[vals == missing] = np.nan
    return vals.reshape(NJ, NI)


def encode_wind(u: np.ndarray, v: np.ndarray) -> np.ndarray:
    def comp(x):
        s = np.sign(x) * np.sqrt(np.minimum(np.abs(np.nan_to_num(x)), WIND_MAX) / WIND_MAX)
        return np.clip(np.rint((s + 1) * 127.5), 0, 255).astype(np.uint8)

    rgb = np.zeros(u.shape + (3,), np.uint8)
    rgb[..., 0], rgb[..., 1] = comp(u), comp(v)
    return rgb


def encode_wave(hs: np.ndarray, dirp: np.ndarray, per: np.ndarray) -> np.ndarray:
    sea = np.isfinite(hs) & np.isfinite(dirp)
    # DIRPW is de richting waar de golven vandaan komen (meteorologisch, graden vanaf noord).
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


def save_png(rgb: np.ndarray, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgb, "RGB").save(path, optimize=True)


def write_levels(rgb: np.ndarray, base: Path, name: str) -> None:
    """Grof wereldraster en fijne tegels van één veld."""
    save_png(rgb[::COARSE_STEP, ::COARSE_STEP], base / f"{name}.png")
    wrapped = np.concatenate([rgb, rgb[:, :1]], axis=1)  # kolom 1440 = kolom 0 (lengte 360 = 0)
    for r in range(180 // TILE_DEG):
        for c in range(360 // TILE_DEG):
            j0, i0 = r * TILE_PX, c * TILE_PX
            save_png(wrapped[j0 : j0 + TILE_PX + 1, i0 : i0 + TILE_PX + 1], base / name / f"{r}_{c}.png")


def process_hour(day: str, cycle: str, h: int, out: Path) -> int:
    wind = fetch_fields(atmos_url(day, cycle, h), WIND_FIELDS)
    wave = fetch_fields(wave_url(day, cycle, h), WAVE_FIELDS)
    base = out / f"{h:03d}"
    write_levels(encode_wind(*(wind[k] for k in WIND_FIELDS)), base, "wind")
    write_levels(encode_wave(*(wave[k] for k in WAVE_FIELDS)), base, "wave")
    return h


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--out", type=Path, default=Path("web/public/data"))
    p.add_argument("--max-hour", type=int, default=120)
    p.add_argument("--step", type=int, default=3)
    p.add_argument("--workers", type=int, default=6)
    a = p.parse_args(argv)

    hs = hours(a.max_hour, a.step)
    run = latest_run(hs[-1])
    day, cycle = run.strftime("%Y%m%d"), run.strftime("%H")
    print(f"GFS-run {day} {cycle}Z, {len(hs)} tijdstippen", flush=True)
    a.out.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(a.workers) as ex:
        for h in ex.map(lambda h: process_hour(day, cycle, h, a.out), hs):
            print(f"  +{h:03d} u klaar", flush=True)

    manifest = {
        "run": run.strftime("%Y-%m-%dT%H:%MZ"),
        "source": "NOAA GFS 0.25 (wind 10 m) en GFS-Wave / WaveWatch III 0.25 (golven)",
        "times": [{"h": h, "time": (run + dt.timedelta(hours=h)).strftime("%Y-%m-%dT%H:%MZ")} for h in hs],
        "coarse": {"deg": COARSE_STEP / 4, "width": NI // COARSE_STEP, "height": (NJ - 1) // COARSE_STEP + 1},
        "fine": {"deg": 0.25, "tileDeg": TILE_DEG, "tilePx": TILE_PX + 1,
                 "rows": 180 // TILE_DEG, "cols": 360 // TILE_DEG},
        "encoding": {"windMax": WIND_MAX, "waveHMax": H_MAX, "wavePeriodMax": T_MAX},
    }
    (a.out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
