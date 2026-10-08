"""De databestanden voor de site maken, met het rekenmodel v2 (pipeline/rules/model.py).

Per strand en per uur de vier lagen van het model:
1. WAVE  (level uit E_zee: hoogte en periode)
2. WIND  (level uit wind en vlaag)
3. de extra's per strand (bereikt %, E, WAVE_strand, periode, H_strand, windhoek, tij_pct, tijgewicht, verval)
4. de vijf scores en de conclusie
Gegevens zoals Windguru: wind van GFS, golven van GFS-Wave (open zee, per deining apart).

Schrijft web/public/data/:
- index.json        tijdas, bron, meldingen over de data
- kaart.json        per strand: id, naam, district, ligging
- sport/ww.json     per strand (zelfde volgorde als kaart.json) per uur vijf tekens: WIND, WAVE (00 = geen),
                    rood (0 niets, 1 wind van land, 2 golf komt niet aan, 3 beide), de conclusie-letter
                    (G O S R ideaal, g o s r andere, W te wild) en bij ideaal de score (75..100 als a..z, anders 0)
- getij.json        hoog- en laagwaters per station
- controle.json     de controles op de stranddata (pipeline/rules/controle.py)
- strand/<id>.json  alles voor de fiche (zie main())
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path

from pipeline.klim import bouw as klim
from pipeline.rules import controle as stranddata
from pipeline.rules.hulp import controle, krachtigste
from pipeline.rules.model import NAAM, VOLGORDE, bereken, hoek
from pipeline.site import planning
from pipeline.site.zon_getij import daglicht, getij_fractie
from pipeline.tides.interp import interpolate

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
OUT = ROOT / "web" / "public" / "data"
IPMA_URL = "https://api.ipma.pt/open-data/forecast/warnings/warnings_www.json"
HOURS = 240
WIND = "wind_gfs"
GOLF = "golf_gfswave"
BRON = "GFS 13 km (wind) en GFS-Wave 16 km (golven), zoals Windguru"
# Per deining: hoogte, periode, piekperiode (telt als de bron ze geeft), richting.
DEININGEN = [
    ("swell_wave_height", "swell_wave_period", "swell_wave_peak_period", "swell_wave_direction"),
    ("secondary_swell_wave_height", "secondary_swell_wave_period", "secondary_swell_wave_peak_period",
     "secondary_swell_wave_direction"),
    ("wind_wave_height", "wind_wave_period", "wind_wave_peak_period", "wind_wave_direction"),
]
# Letter per conclusie voor de kaartkleuren: hoofdletter = ideaal, kleine letter = andere, W = te wild.
LETTER = {"golfsurfen": "G", "windsurfen_op_golven": "O", "windsurfen": "S", "stille_waters": "R"}
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


def conclusie_letter(tekst: str) -> str:
    """De conclusie van model.conclusie() als één letter (W te wild, hoofdletter ideaal, kleine letter andere)."""
    if tekst.startswith("te wild"):
        return "W"
    for naam, letter in LETTER.items():
        if tekst == "ideaal " + NAAM[naam]:
            return letter
        if tekst.startswith(f"andere: {NAAM[naam]} "):
            return letter.lower()
    raise ValueError(f"onbekende conclusie: {tekst}")


def meldingen(paren: list[tuple[float, float]]) -> list[str]:
    """Model v2: is de vlaag in de data elk uur exact gelijk aan de wind, dan klopt de vlagenbron niet."""
    uit = []
    if paren and all(v == w for v, w in paren):
        uit.append("De vlaag is elk uur exact gelijk aan de wind: de vlagenbron klopt niet.")
    lager = sum(1 for v, w in paren if v < w)
    if lager:
        uit.append(f"In {round(100 * lager / len(paren))}% van de uren is de vlaag in de data lager dan de wind; "
                   "daar rekent het model met de wind.")
    return uit


def strand(f: dict, punten: dict, wsrc: dict, gsrc: dict, getij: dict, ext_by: dict, warn: list, axis: list[str],
           minuten: list[float], vlaag_paren: list, land: str = "pt"):
    """Eén strand: de vier lagen per uur. Geeft (kaart-item, ww-rij, detail) of None zonder voorspelling."""
    p = f["properties"]
    pid = p["id"]
    lon, lat = f["geometry"]["coordinates"]
    pt = punten.get(pid)
    if pt is None:  # nieuw strand: de voorspelling volgt bij de volgende run
        return None
    g = getij.get(pid)
    ext = interpolate(ext_by[g["a"]], ext_by[g["b"]], g["w"]) if g else []

    ws = rnd(align(wsrc, pt["wind"], "wind_speed_10m", axis), 1)
    wg_ruw = rnd(align(wsrc, pt["wind"], "wind_gusts_10m", axis), 1)
    wd = rnd(align(wsrc, pt["wind"], "wind_direction_10m", axis), 0)
    vlaag_paren += [(v, w) for v, w in zip(wg_ruw, ws, strict=True) if v is not None and w is not None]
    # Model v2, invoer: is de vlaag lager dan de wind, reken dan met de wind.
    wg = [None if v is None else max(v, w or 0) for v, w in zip(wg_ruw, ws, strict=True)]
    golf = {v: rnd(align(gsrc, pt["golf"], v, axis), 2 if "height" in v else 1 if "period" in v else 0)
            for v in (*TOTAAL, *(x for d in DEININGEN for x in d))}
    piek = any(x is not None for _h, _t, tp, _r in DEININGEN for x in golf[tp])
    c = controle(p["kijkrichting"], p["venster"])
    vensters = [tuple(v) for v in p["venster"]]  # 0 tot 3 vensters; geen venster: factor 0 (rekenchat)

    n = len(axis)
    rij = {k: [None] * n for k in ("zee_h", "zee_t", "zee_r", "E_zee", "bereikt", "E", "periode", "H", "windhoek",
                                    "tij", "tijgewicht", "verval", "scores", "conclusie")}
    wave, wind, laag3, letter, licht, rood = [], [], [], [], [], []
    for i in range(n):
        licht.append("1" if daglicht(lat, lon, minuten[i]) else "0")
        dein = [(golf[h][i], golf[tp][i] if golf[tp][i] is not None else golf[t][i], golf[r][i])
                for h, t, tp, r in DEININGEN]
        if ws[i] is None or golf["wave_height"][i] is None:  # geen voorspelling voor dit uur
            wave.append("0"), wind.append("0"), laag3.append("0"), letter.append("-"), rood.append("0")
            continue
        # Een deining zonder hoogte, periode of richting bestaat op dit uur niet.
        dein = [d for d in dein if None not in d and d[0] > 0 and d[1] > 0]
        tij, verval = getij_stand(ext, minuten[i])
        # Zonder getij rekent het model met zijn standaardwaarden niet: dan geen laag 3 en 4.
        heeft_getij = tij is not None
        r = bereken(p["kijkrichting"], vensters, ws[i], wg[i], wd[i] or 0, dein,
                    tij_pct=tij if heeft_getij else 50, verval=verval if heeft_getij else 2.4)
        wave.append(str(r["WAVE"]))
        wind.append(str(r["WIND"]))
        # Rood omkaderd (eigenaar): WIND bij wind van land (windhoek vanaf 112,5°: schuin of recht aflandig);
        # WAVE als er op zee golf staat (WAVE 2 of meer) maar op het strand te weinig aankomt (WAVE_strand 1).
        rood_wind = hoek(wd[i] or 0, p["kijkrichting"]) >= 112.5
        rood_wave = heeft_getij and r["WAVE"] >= 2 and r["WAVE_strand"] == 1
        rood.append(str(rood_wind + 2 * rood_wave))
        k = krachtigste(dein)
        rij["E_zee"][i] = r["E_zee"]  # de krachtigste deining: daaruit komt het level WAVE
        if k is not None:
            rij["zee_h"][i], rij["zee_t"][i], rij["zee_r"][i] = dein[k][0], dein[k][1], dein[k][2]
        if not heeft_getij:
            laag3.append("0"), letter.append(".")
            continue
        laag3.append(str(r["WAVE_strand"]))
        rij["bereikt"][i], rij["E"][i], rij["periode"][i] = r["bereikt_pct"], r["E"], r["periode"]
        rij["H"][i], rij["windhoek"][i] = r["H_strand"], r["windhoek"]
        rij["tij"][i], rij["tijgewicht"][i], rij["verval"][i] = round(tij), r["tijgewicht"], round(verval, 2)
        rij["scores"][i] = [r[x] for x in (*VOLGORDE, "te_wild")]
        rij["conclusie"][i] = r["conclusie"]
        letter.append(conclusie_letter(r["conclusie"]))
    # Per uur 5 tekens: WIND, WAVE, rood kader, conclusie-letter, en bij een ideale conclusie de score
    # van die activiteit (75..100 als a..z), anders 0. De kaart kiest daarmee per sport de route.
    sc = []
    for i, lt in enumerate(letter):
        kol = "GOSR".find(lt)
        ideaal = kol >= 0 and rij["scores"][i]
        sc.append(chr(ord("a") + max(0, min(25, rij["scores"][i][kol] - 75))) if ideaal else "0")
    ww = "".join(a + b + c + d + e for a, b, c, d, e in zip(wind, wave, rood, letter, sc, strict=True))

    detail = {
        "id": pid, "naam": p["naam"], "lat": lat, "lon": lon, "kust": p["kijkrichting"],
        "venster": p["venster"], "district": p["district"], "getij": g, "controle": c, "piekperiode": piek,
        "wind": ws, "vlagen": wg, "windrichting": wd, "WAVE": "".join(wave), "WIND": "".join(wind),
        "WAVE_strand": "".join(laag3), "letter": "".join(letter), "rood": "".join(rood),
        "licht": "".join(licht), **rij,
        "ipma": [warning_at(warn, p.get("ipma_area"), t) for t in axis],
    }
    if land != "pt":
        detail["land"] = land
        if land in VASTE_NOTA:
            detail["nota"] = VASTE_NOTA[land]
    item = {"id": pid, "n": p["naam"], "d": p["district"], "x": lon, "y": lat, **({"l": land} if land != "pt" else {})}
    return item, ww, detail


# Vaste nota per land (rekenchat, 8 oktober 2026).
VASTE_NOTA = {"be": "Sterke getijstroom aan deze kust; die zit niet in de berekening."}
LANDEN_DIR = DATA / "beaches" / "landen"


def schrijf_detail(detail: dict) -> None:
    (OUT / "strand" / f"{re.sub(r'[^A-Za-z0-9_.-]', '_', detail['id'])}.json").write_text(
        json.dumps(detail, ensure_ascii=False, separators=(",", ":")))


def landen_stations(axis: list[str]) -> list[dict]:
    """Getijstations van de andere landen, ingekort tot de tijdas (plus een dag): anders wordt getij.json te groot."""
    p = DATA / "tides" / "stations_landen.json"
    if not p.exists():
        return []
    t0 = datetime.fromisoformat(axis[0]).replace(tzinfo=UTC).timestamp() / 60 - 1440
    t1 = datetime.fromisoformat(axis[-1]).replace(tzinfo=UTC).timestamp() / 60 + 1440
    return [s | {"extremen": [e for e in s["extremen"] if t0 <= e[0] <= t1]}
            for s in json.loads(p.read_text())["stations"]]


def andere_landen(axis: list[str], minuten: list[float], ext_by: dict, vlaag_paren: list):
    """Stranden van de andere landen, met hun eigen voorspelling en getij. Ontbreekt iets, dan dat land niet."""
    fc_dir = DATA / "forecast"
    nodig = [fc_dir / "punten_landen.json", fc_dir / "wind_gfs_landen.json", fc_dir / "golf_gfswave_landen.json",
             DATA / "tides" / "stranden_getij_landen.json"]
    if not LANDEN_DIR.exists() or not all(x.exists() for x in nodig):
        return
    punten = load("punten_landen")
    wsrc, gsrc = load("wind_gfs_landen"), load("golf_gfswave_landen")
    getij = json.loads((DATA / "tides" / "stranden_getij_landen.json").read_text())
    for path in sorted(LANDEN_DIR.glob("*.geojson")):
        land = path.stem
        for f in json.loads(path.read_text())["features"]:
            if f["properties"]["id"] not in getij:
                continue  # geen getijstation binnen bereik: zonder getij geen laag 3 en 4
            uit = strand(f, punten, wsrc, gsrc, getij, ext_by, [], axis, minuten, vlaag_paren, land)
            if uit is not None:
                yield (land, *uit)


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
    vlaag_paren: list[tuple[float, float]] = []
    for f in fc["features"]:
        uit = strand(f, punten, wsrc, gsrc, getij, ext_by, warn, axis, minuten, vlaag_paren)
        if uit is None:
            continue
        item, ww, detail = uit
        kaart.append(item)
        ww_rijen.append(ww)
        schrijf_detail(detail)
    # Andere landen (Spanje, Frankrijk, België): zelfde berekening, eigen bronbestanden.
    stations_landen = landen_stations(axis)
    for s_ in stations_landen:
        ext_by[s_["id"]] = s_["extremen"]
    for land, item, ww, detail in andere_landen(axis, minuten, ext_by, vlaag_paren):
        kaart.append(item)
        ww_rijen.append(ww)
        schrijf_detail(detail)
    (OUT / "sport" / "ww.json").write_text(json.dumps(ww_rijen, separators=(",", ":")))
    (OUT / "getij.json").write_text(json.dumps(
        {"stations": {s["id"]: {"naam": s["naam"], "lat": s["lat"], "lon": s["lon"], "e": s["extremen"]}
                      for s in [*stations["stations"], *stations_landen]}}, separators=(",", ":")))
    (OUT / "kaart.json").write_text(json.dumps(kaart, ensure_ascii=False, separators=(",", ":")))
    index = {
        "gemaakt": datetime.now(UTC).strftime("%Y-%m-%dT%H:%MZ"),
        "opgehaald": {WIND: wsrc.get("_opgehaald"), GOLF: gsrc.get("_opgehaald")},
        "tijd": axis, "bron": BRON, "namen": NAAM, "ipma": warn, "meldingen": meldingen(vlaag_paren),
    }
    stranddata.main()
    klim.main(axis, OUT)
    planning.main(axis, OUT, ROOT)
    (OUT / "index.json").write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")))
    print(f"{len(kaart)} stranden, {len(axis)} uur")


if __name__ == "__main__":
    main(fetch_ipma="--geen-ipma" not in sys.argv)
