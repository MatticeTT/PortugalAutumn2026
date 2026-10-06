"""M4: de databestanden voor de site maken.

Leest de strandentabel, de voorspelling (tak `data`), het getij en de IPMA-waarschuwingen,
en rekent per strand en per uur WIND, WAVE en het label uit, voor twee standen:

- "wg":   zelfde model als Windguru (GFS-wind, GFS-Wave)
- "fijn": ECMWF-wind en Copernicus IBI-golven (GFS-Wave waar IBI ophoudt)

Schrijft web/public/data/:
- index.json          tijdas, standen, labels en nota's (als codes), bronvermelding
- kaart.json          per strand: naam, ligging, en per stand een reeks "WIND WAVE" cijfers per uur
- getij.json          hoog- en laagwaters per station + per strand de stations en het gewicht
- strand/<id>.json    alles voor de fiche: de ruwe tabel en per uur
                      [WIND, WAVE, label, [nota's], [redenen], Hb, [bereik], windsurf, waarschuwing, windklasse]
                      (label, nota's, redenen, windsurf en waarschuwing als nummer in index.json)
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path

from pipeline.rules.score import Strand, Uur, rules, score

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
OUT = ROOT / "web" / "public" / "data"
IPMA_URL = "https://api.ipma.pt/open-data/forecast/warnings/warnings_www.json"
HOURS = 240

STANDEN = {
    "wg": {"naam": "Windguru-model", "wind": "wind_gfs", "golf": ["golf_gfswave"],
           "bron": "GFS 13 km en GFS-Wave 16 km"},
    "fijn": {"naam": "Fijner model", "wind": "wind_ecmwf", "golf": ["golf_ibi", "golf_gfswave"],
             "bron": "ECMWF IFS 9 km en Copernicus IBI 3 km"},
}
WAVE_KEYS = [
    ("wave_height", "wave_period", "wave_direction"),
    ("swell_wave_height", "swell_wave_period", "swell_wave_direction"),
    ("secondary_swell_wave_height", "secondary_swell_wave_period", "secondary_swell_wave_direction"),
    ("wind_wave_height", "wind_wave_period", "wind_wave_direction"),
]


def load(name: str):
    return json.loads((DATA / "forecast" / f"{name}.json").read_text())


def time_axis(src) -> list[str]:
    t0 = datetime.fromisoformat(src["_tijd"][0]).replace(tzinfo=UTC)
    return [(t0 + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M") for i in range(HOURS)]


def align(src, key: str, var: str, axis: list[str]):
    rec = src.get(key)
    if rec is None or rec.get(var) is None:
        return [None] * len(axis)
    idx = {t: i for i, t in enumerate(src["_tijd"])}
    vals = rec[var]
    return [vals[idx[t]] if t in idx and idx[t] < len(vals) else None for t in axis]


def ipma_levels(fetch: bool) -> list[dict]:
    """Waarschuwingen 'Agitação Marítima' als [{area, level, start, end}] (tijden: Lissabon, als UTC benaderd)."""
    path = DATA / "forecast" / "ipma_warnings.json"
    raw = None
    if fetch:
        try:
            req = urllib.request.Request(IPMA_URL, headers={"User-Agent": "surfkaart-portugal/0.1"})
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = json.loads(r.read())
            path.write_text(json.dumps(raw, ensure_ascii=False))
        except Exception as e:  # noqa: BLE001
            print("IPMA niet bereikbaar:", e)
    if raw is None and path.exists():
        raw = json.loads(path.read_text())
    out = []
    for r in raw or []:
        if r.get("awarenessTypeName") == "Agitação Marítima" and r.get("awarenessLevelID") != "green":
            out.append({"area": r["idAreaAviso"], "level": r["awarenessLevelID"],
                        "start": r["startTime"][:16], "end": r["endTime"][:16]})
    return out


def warning_at(warn: list[dict], area: str | None, t: str) -> str:
    order = ["green", "yellow", "orange", "red"]
    lvl = "green"
    for w in warn:
        if w["area"] == area and w["start"] <= t < w["end"] and order.index(w["level"]) > order.index(lvl):
            lvl = w["level"]
    return lvl


def r1(x):
    return None if x is None else round(x, 1)


def main(fetch_ipma: bool = True):
    fc = json.loads((DATA / "beaches" / "stranden.geojson").read_text())
    punten = load("punten")
    src = {n: load(n) for n in ("wind_gfs", "wind_ecmwf", "golf_gfswave", "golf_ibi")
           if (DATA / "forecast" / f"{n}.json").exists()}
    axis = time_axis(src["wind_gfs"])
    warn = ipma_levels(fetch_ipma)
    getij = json.loads((DATA / "tides" / "stranden_getij.json").read_text())

    labels: list[str] = []
    notas: list[str] = []
    teksten: list[str] = []   # redenen, windsurfregels en waarschuwingen: één keer bewaard, per uur een nummer

    def code(lst, s):
        if s not in lst:
            lst.append(s)
        return lst.index(s)

    (OUT / "strand").mkdir(parents=True, exist_ok=True)
    kaart = []
    for f in fc["features"]:
        p = f["properties"]
        pid = p["id"]
        lon, lat = f["geometry"]["coordinates"]
        pt = punten.get(pid)
        if pt is None:  # nieuw strand: de voorspelling volgt bij de volgende run
            continue
        strand = Strand(kijkrichting=p["kijkrichting"], blootstelling=p["blootstelling"],
                        richting_onzeker=p["onzeker"], besloten_water=p["besloten_water"])
        detail = {"id": pid, "naam": p["naam"], "lat": lat, "lon": lon, "kijkrichting": p["kijkrichting"],
                  "district": p["district"], "onzeker": p["onzeker"], "redenen_onzeker": p["redenen"],
                  "venster": p["venster"], "getij": getij.get(pid), "standen": {}}
        k_entry = {"id": pid, "n": p["naam"], "x": lon, "y": lat}
        for mode, cfg in STANDEN.items():
            wsrc = src.get(cfg["wind"])
            if wsrc is None:
                continue
            ws = align(wsrc, pt["wind"], "wind_speed_10m", axis)
            wg = align(wsrc, pt["wind"], "wind_gusts_10m", axis)
            wd = align(wsrc, pt["wind"], "wind_direction_10m", axis)
            waves = {}
            for gname in reversed(cfg["golf"]):  # de eerste bron wint, de volgende vult aan
                g = src.get(gname)
                if g is None:
                    continue
                for trio in WAVE_KEYS:
                    for v in trio:
                        vals = align(g, pt["golf"], v, axis)
                        old = waves.get(v, [None] * len(axis))
                        waves[v] = [n if n is not None else o for n, o in zip(vals, old, strict=True)]
                if gname == "golf_ibi":
                    waves["wave_peak_period"] = align(g, pt["golf"], "wave_peak_period", axis)
            digits, rows = [], []
            for i, t in enumerate(axis):
                if ws[i] is None or waves.get("wave_height", [None])[i] is None:
                    digits.append("00")
                    rows.append(None)
                    continue
                parts = [tuple(waves[k][i] or 0 for k in trio) for trio in WAVE_KEYS[1:]]
                u = Uur(wind_kn=ws[i], vlagen_kn=wg[i] or ws[i], windrichting=wd[i] or 0, deelgolven=parts,
                        golfhoogte_totaal=waves["wave_height"][i], golfperiode_totaal=waves["wave_period"][i],
                        golfrichting_totaal=waves["wave_direction"][i],
                        ipma_zeegang=warning_at(warn, p.get("ipma_area"), t))
                s = score(u, strand)
                digits.append(f"{s.wind}{s.wave}")
                rows.append([s.wind, s.wave, code(labels, s.label), [code(notas, n) for n in s.notas],
                             [code(teksten, r) for r in s.redenen], s.hb, list(s.hb_bereik),
                             code(teksten, s.windsurf) if s.windsurf else None,
                             code(teksten, s.waarschuwing) if s.waarschuwing else None, s.windklasse])
            k_entry[mode] = "".join(digits)
            detail["standen"][mode] = {
                "bron": cfg["bron"],
                "wind": [r1(x) for x in ws], "vlagen": [r1(x) for x in wg],
                "windrichting": [None if x is None else round(x) for x in wd],
                **{k: [None if x is None else (round(x) if "direction" in k else round(x, 1)) for x in v]
                   for k, v in waves.items()},
                "score": rows,
            }
        kaart.append(k_entry)
        (OUT / "strand" / f"{re.sub(r'[^A-Za-z0-9_.-]', '_', pid)}.json").write_text(
            json.dumps(detail, ensure_ascii=False, separators=(",", ":")))
    stations = json.loads((DATA / "tides" / "stations.json").read_text())
    (OUT / "getij.json").write_text(json.dumps(
        {"stations": {s["id"]: {"naam": s["naam"], "lat": s["lat"], "lon": s["lon"], "e": s["extremen"]}
                      for s in stations["stations"]}}, separators=(",", ":")))
    (OUT / "kaart.json").write_text(json.dumps(kaart, ensure_ascii=False, separators=(",", ":")))
    index = {
        "gemaakt": datetime.now(UTC).strftime("%Y-%m-%dT%H:%MZ"),
        "opgehaald": {n: s.get("_opgehaald") for n, s in src.items()},
        "tijd": axis, "standen": {m: {"naam": c["naam"], "bron": c["bron"]} for m, c in STANDEN.items()},
        "labels": labels, "notas": notas, "teksten": teksten, "ipma": warn,
        "regels": rules(),
    }
    (OUT / "index.json").write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")))
    print(f"{len(kaart)} stranden, {len(axis)} uur, {len(labels)} labels, {len(notas)} nota's, "
          f"{len(warn)} IPMA-waarschuwingen")


if __name__ == "__main__":
    main(fetch_ipma="--geen-ipma" not in sys.argv)
