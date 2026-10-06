"""De databestanden voor de site maken.

Leest de strandentabel, de voorspelling (tak `data`), het getij en de IPMA-waarschuwingen,
en rekent per strand, per uur en per sport het cijfer van 1 tot 5 uit (pipeline/sport).
Wind: ECMWF IFS. Golven: Copernicus IBI, met GFS-Wave waar IBI ophoudt (M6: IBI zit het
dichtst bij de boeien, data/validate/golven.json).

Schrijft web/public/data/:
- index.json          tijdas, sporten, schaal, redenen, bronvermelding
- kaart.json          per strand: id, naam, ligging
- sport/<sport>.json  per strand (zelfde volgorde als kaart.json) een reeks cijfers, één per uur (0 = geen)
- getij.json          hoog- en laagwaters per station
- strand/<id>.json    alles voor de fiche: de voorspelling, GOLF, RUW, het getij en per sport
                      de cijfers en de redenen (elk een reeks, één teken per uur; reden 0 = geen)
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path

import yaml

from pipeline.sport.score import Invoer, bereken, sporten, strandfactor, tij_op
from pipeline.tides.interp import interpolate

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
OUT = ROOT / "web" / "public" / "data"
IPMA_URL = "https://api.ipma.pt/open-data/forecast/warnings/warnings_www.json"
HOURS = 240
WIND = "wind_ecmwf"
GOLF = ["golf_ibi", "golf_gfswave"]   # de eerste bron wint, de volgende vult aan
BRON = "ECMWF IFS 9 km (wind) en Copernicus IBI 3 km (golven; GFS-Wave 16 km waar IBI ophoudt)"
WAVE_KEYS = [
    ("wave_height", "wave_period", "wave_direction"),
    ("swell_wave_height", "swell_wave_period", "swell_wave_direction"),
    ("secondary_swell_wave_height", "secondary_swell_wave_period", "secondary_swell_wave_direction"),
    ("wind_wave_height", "wind_wave_period", "wind_wave_direction"),
]
TIJ_CODE = {"laag": 0, "opkomend": 1, "hoog": 2, "afgaand": 3}


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


def eigen() -> dict:
    path = DATA / "beaches" / "sport.yaml"
    return (yaml.safe_load(path.read_text()) or {}) if path.exists() else {}


def main(fetch_ipma: bool = True):
    fc = json.loads((DATA / "beaches" / "stranden.geojson").read_text())
    punten = load("punten")
    src = {n: load(n) for n in (WIND, *GOLF) if (DATA / "forecast" / f"{n}.json").exists()}
    axis = time_axis(src[WIND])
    minuten = [datetime.fromisoformat(t).replace(tzinfo=UTC).timestamp() / 60 for t in axis]
    warn = ipma_levels(fetch_ipma)
    getij = json.loads((DATA / "tides" / "stranden_getij.json").read_text())
    stations = json.loads((DATA / "tides" / "stations.json").read_text())
    ext_by = {s["id"]: s["extremen"] for s in stations["stations"]}
    cfg = sporten()
    namen = list(cfg["sporten"])
    eigen_k = eigen()

    (OUT / "strand").mkdir(parents=True, exist_ok=True)
    (OUT / "sport").mkdir(parents=True, exist_ok=True)
    kaart = []
    per_sport: dict[str, list[str]] = {s: [] for s in namen}
    for f in fc["features"]:
        p = f["properties"]
        pid = p["id"]
        lon, lat = f["geometry"]["coordinates"]
        pt = punten.get(pid)
        if pt is None:  # nieuw strand: de voorspelling volgt bij de volgende run
            continue
        e = eigen_k.get(pid) or {}
        K, k_bron = strandfactor(p["blootstelling"], p["redenen"])
        if e.get("K") is not None:
            K, k_bron = float(e["K"]), "eigen invoer"
        besttij = e.get("BESTTIJ")
        droog = e.get("DROOG") in (True, "ja")
        luwte = tuple(e["LUWTE"]) if e.get("LUWTE") else None

        g = getij.get(pid)
        ext = interpolate(ext_by[g["a"]], ext_by[g["b"]], g["w"]) if g else []
        tij = [tij_op(ext, m) for m in minuten]

        wsrc = src[WIND]
        ws = align(wsrc, pt["wind"], "wind_speed_10m", axis)
        wg = align(wsrc, pt["wind"], "wind_gusts_10m", axis)
        wd = align(wsrc, pt["wind"], "wind_direction_10m", axis)
        waves: dict[str, list] = {}
        for gname in reversed(GOLF):
            gs = src.get(gname)
            if gs is None:
                continue
            for trio in WAVE_KEYS:
                for v in trio:
                    vals = align(gs, pt["golf"], v, axis)
                    old = waves.get(v, [None] * len(axis))
                    waves[v] = [n if n is not None else o for n, o in zip(vals, old, strict=True)]
        # T is de piekperiode: IBI geeft ze (VTPK); waar IBI ophoudt, de periode van GFS-Wave
        # (die ligt dicht bij de gemeten piekperiode, zie pipeline/validate/waves.py).
        piek = align(src["golf_ibi"], pt["golf"], "wave_peak_period", axis) if "golf_ibi" in src else [None] * len(axis)
        gfs_t = (align(src["golf_gfswave"], pt["golf"], "wave_period", axis)
                 if "golf_gfswave" in src else [None] * len(axis))
        T = [a if a is not None else b for a, b in zip(piek, gfs_t, strict=True)]

        cijfers = {s: [] for s in namen}
        redenen = {s: [] for s in namen}
        golf_s, ruw_s = [], []
        for i in range(len(axis)):
            uit = bereken(Invoer(N=p["kijkrichting"], K=K, BESTTIJ=besttij, DROOG=droog, LUWTE=luwte,
                                 H=waves["wave_height"][i], T=T[i], GR=waves["wave_direction"][i],
                                 V=ws[i], G=wg[i], WR=wd[i], TIJ=tij[i]))
            for s in namen:
                cijfers[s].append(str(uit.cijfers[s]) if uit else "0")
                redenen[s].append(str(uit.redenen[s]) if uit else "0")
            golf_s.append(None if uit is None else round(uit.GOLF, 2))
            ruw_s.append(None if uit is None else round(uit.RUW, 2))
        for s in namen:
            per_sport[s].append("".join(cijfers[s]))

        detail = {
            "id": pid, "naam": p["naam"], "lat": lat, "lon": lon, "kijkrichting": p["kijkrichting"],
            "district": p["district"], "onzeker": p["onzeker"], "redenen_onzeker": p["redenen"],
            "getij": g, "K": K, "K_bron": k_bron, "BESTTIJ": besttij, "DROOG": droog, "LUWTE": luwte,
            "wind": [r1(x) for x in ws], "vlagen": [r1(x) for x in wg],
            "windrichting": [None if x is None else round(x) for x in wd],
            **{k: [None if x is None else (round(x) if "direction" in k else round(x, 1)) for x in v]
               for k, v in waves.items()},
            "piekperiode": [r1(x) for x in T],
            "GOLF": golf_s, "RUW": ruw_s,
            "tij": [None if t is None else TIJ_CODE[t] for t in tij],
            "ipma": [warning_at(warn, p.get("ipma_area"), t) for t in axis],
            "cijfers": {s: "".join(v) for s, v in cijfers.items()},
            "redenen": {s: "".join(v) for s, v in redenen.items()},
        }
        kaart.append({"id": pid, "n": p["naam"], "x": lon, "y": lat})
        (OUT / "strand" / f"{re.sub(r'[^A-Za-z0-9_.-]', '_', pid)}.json").write_text(
            json.dumps(detail, ensure_ascii=False, separators=(",", ":")))
    for s, rows in per_sport.items():
        (OUT / "sport" / f"{s}.json").write_text(json.dumps(rows, separators=(",", ":")))
    (OUT / "getij.json").write_text(json.dumps(
        {"stations": {s["id"]: {"naam": s["naam"], "lat": s["lat"], "lon": s["lon"], "e": s["extremen"]}
                      for s in stations["stations"]}}, separators=(",", ":")))
    (OUT / "kaart.json").write_text(json.dumps(kaart, ensure_ascii=False, separators=(",", ":")))
    index = {
        "gemaakt": datetime.now(UTC).strftime("%Y-%m-%dT%H:%MZ"),
        "opgehaald": {n: s.get("_opgehaald") for n, s in src.items()},
        "tijd": axis, "bron": BRON,
        "sporten": [{"id": s, **c} for s, c in cfg["sporten"].items()],
        "groepen": cfg["groepen"], "schaal": cfg["schaal"],
        "redenen": {str(k): v for k, v in cfg["redenen"].items()},
        "nauwkeurigheid": json.loads((DATA / "validate" / "golven.json").read_text())
        if (DATA / "validate" / "golven.json").exists() else None,
        "ipma": warn,
    }
    (OUT / "index.json").write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")))
    print(f"{len(kaart)} stranden, {len(axis)} uur, {len(namen)} sporten, {len(warn)} IPMA-waarschuwingen")


if __name__ == "__main__":
    main(fetch_ipma="--geen-ipma" not in sys.argv)
