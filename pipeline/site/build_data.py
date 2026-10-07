"""De databestanden voor de site maken.

Per strand en per uur: WAVE en WIND (level 1 tot 4) en precies één uitkomst (te wild, golfsurfen,
windsurfen op golven, windsurfen, stille waters), met de regels van pipeline/rules/uitkomst.py.
Gegevens zoals Windguru: wind van GFS, golven van GFS-Wave (open zee, per deining apart).

Schrijft web/public/data/:
- index.json        tijdas, uitkomsten, bronvermelding
- kaart.json        per strand: id, naam, ligging
- sport/ww.json     per strand (zelfde volgorde als kaart.json) per uur twee cijfers: WIND en WAVE (00 = geen)
- getij.json        hoog- en laagwaters per station
- strand/<id>.json  alles voor de fiche: de voorspelling per uur, het getij, en per uur
                    "uitkomst" (W, G, O, S, R; "." = past niets echt; "-" = geen voorspelling),
                    "straf" (strafpunten van de winnaar), "WAVE", "WIND" (level) en "licht" (1 = daglicht)
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path

from pipeline.rules.dagplan import daglicht, getij_fractie
from pipeline.rules.uitkomst import UITKOMSTEN, Deining, Strand, Uur, bereken, getoond
from pipeline.tides.interp import interpolate

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
OUT = ROOT / "web" / "public" / "data"
IPMA_URL = "https://api.ipma.pt/open-data/forecast/warnings/warnings_www.json"
HOURS = 240
WIND = "wind_gfs"
GOLF = "golf_gfswave"
BRON = "GFS 13 km (wind) en GFS-Wave 16 km (golven), zoals Windguru"
DEININGEN = [
    ("swell_wave_height", "swell_wave_period", "swell_wave_direction"),
    ("secondary_swell_wave_height", "secondary_swell_wave_period", "secondary_swell_wave_direction"),
    ("wind_wave_height", "wind_wave_period", "wind_wave_direction"),
]
TOTAAL = ("wave_height", "wave_period", "wave_direction")


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


def rnd(xs: list, nd: int) -> list:
    return [None if x is None else round(x, nd) for x in xs]


def getij_stand(ext: list[list], t_min: float) -> tuple[float | None, float | None]:
    """Tij% (0 laagwater, 100 hoogwater) en verval (m) van de getijslag waarin t valt."""
    p = getij_fractie(ext, t_min)
    if p is None:
        return None, None
    for e0, e1 in zip(ext, ext[1:], strict=False):
        if e0[0] <= t_min < e1[0]:
            return p * 100, abs(e1[1] - e0[1]) / 100
    return None, None


def main(fetch_ipma: bool = True):
    fc = json.loads((DATA / "beaches" / "stranden.geojson").read_text())
    punten = load("punten")
    wsrc, gsrc = load(WIND), load(GOLF)
    axis = time_axis(wsrc)
    minuten = [datetime.fromisoformat(t).replace(tzinfo=UTC).timestamp() / 60 for t in axis]
    warn = ipma_levels(fetch_ipma)
    getij = json.loads((DATA / "tides" / "stranden_getij.json").read_text())
    stations = json.loads((DATA / "tides" / "stations.json").read_text())
    ext_by = {s["id"]: s["extremen"] for s in stations["stations"]}

    (OUT / "strand").mkdir(parents=True, exist_ok=True)
    (OUT / "sport").mkdir(parents=True, exist_ok=True)
    kaart, ww_rijen = [], []
    for f in fc["features"]:
        p = f["properties"]
        pid = p["id"]
        lon, lat = f["geometry"]["coordinates"]
        pt = punten.get(pid)
        if pt is None:  # nieuw strand: de voorspelling volgt bij de volgende run
            continue
        strand = Strand(kust=p["kijkrichting"], venster=p["venster"])
        g = getij.get(pid)
        ext = interpolate(ext_by[g["a"]], ext_by[g["b"]], g["w"]) if g else []

        ws = rnd(align(wsrc, pt["wind"], "wind_speed_10m", axis), 1)
        wg = rnd(align(wsrc, pt["wind"], "wind_gusts_10m", axis), 1)
        wd = rnd(align(wsrc, pt["wind"], "wind_direction_10m", axis), 0)
        # Een vlaag is nooit zwakker dan de gemiddelde wind; GFS geeft er soms een lagere.
        wg = [None if v is None else max(v, w or 0) for v, w in zip(wg, ws, strict=True)]
        golf = {v: rnd(align(gsrc, pt["golf"], v, axis), 2 if "height" in v else 1 if "period" in v else 0)
                for trio in (TOTAAL, *DEININGEN) for v in trio}

        uitk, straf, wave, wind, licht = [], [], [], [], []
        for i in range(len(axis)):
            licht.append("1" if daglicht(lat, lon, minuten[i]) else "0")
            if ws[i] is None or golf["wave_height"][i] is None:
                for lijst, leeg in ((uitk, "-"), (straf, "0"), (wave, "0"), (wind, "0")):
                    lijst.append(leeg)
                continue
            deiningen = [Deining(golf[h][i] or 0, golf[t][i] or 0, golf[r][i] or 0) for h, t, r in DEININGEN]
            tij, verval = getij_stand(ext, minuten[i])
            r = bereken(Uur(wind=ws[i], vlaag=wg[i] if wg[i] is not None else ws[i], windrichting=wd[i] or 0,
                            deiningen=deiningen, tij=tij, verval=verval), strand)
            uitk.append(getoond(r) or ".")  # "." = geen uitkomst die echt past
            straf.append(str(min(r.strafpunten, 9)))
            wave.append(str(r.wave))
            wind.append(str(r.wind))
        ww_rijen.append("".join(a + b for a, b in zip(wind, wave, strict=True)))

        detail = {
            "id": pid, "naam": p["naam"], "lat": lat, "lon": lon, "kust": p["kijkrichting"],
            "venster": p["venster"], "district": p["district"], "getij": g,
            "wind": ws, "vlagen": wg, "windrichting": wd, **golf,
            "uitkomst": "".join(uitk), "straf": "".join(straf), "WAVE": "".join(wave), "WIND": "".join(wind),
            "licht": "".join(licht),
            "ipma": [warning_at(warn, p.get("ipma_area"), t) for t in axis],
        }
        kaart.append({"id": pid, "n": p["naam"], "x": lon, "y": lat})
        (OUT / "strand" / f"{re.sub(r'[^A-Za-z0-9_.-]', '_', pid)}.json").write_text(
            json.dumps(detail, ensure_ascii=False, separators=(",", ":")))
    (OUT / "sport" / "ww.json").write_text(json.dumps(ww_rijen, separators=(",", ":")))
    (OUT / "getij.json").write_text(json.dumps(
        {"stations": {s["id"]: {"naam": s["naam"], "lat": s["lat"], "lon": s["lon"], "e": s["extremen"]}
                      for s in stations["stations"]}}, separators=(",", ":")))
    (OUT / "kaart.json").write_text(json.dumps(kaart, ensure_ascii=False, separators=(",", ":")))
    index = {
        "gemaakt": datetime.now(UTC).strftime("%Y-%m-%dT%H:%MZ"),
        "opgehaald": {WIND: wsrc.get("_opgehaald"), GOLF: gsrc.get("_opgehaald")},
        "tijd": axis, "bron": BRON, "uitkomsten": UITKOMSTEN, "ipma": warn,
    }
    (OUT / "index.json").write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")))
    print(f"{len(kaart)} stranden, {len(axis)} uur")


if __name__ == "__main__":
    main(fetch_ipma="--geen-ipma" not in sys.argv)
