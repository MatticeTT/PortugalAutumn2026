"""De planning voor de komende 4 weken (tabblad /planning; eigenaar en rekenchat, 8 oktober 2026).

Per dag precies één resultaat, in deze volgorde (eigenaar):
1 golfsurfen     conclusie "ideaal golfsurfen", alleen stranden tot 2 uur rijden van Ferragudo; daarvan
                 eerst de beste condities (hoogste gemiddelde golfsurfscore over het blok, afgerond), en van
                 die het blok met de kortste rijtijd.
2 windsurfles    anders: Ria de Alvor (lagune): wind van Alvor, geen swell-venster; WIND level 2,
                 geen "te wild"; de windrichting telt niet mee. Eén plek zonder score: het langste blok.
3 stille waters  anders: conclusie "ideaal stille waters", alleen tot 2 uur rijden; eerst de beste condities
                 (hoogste gemiddelde score stille waters, afgerond), en van die de kortste rijtijd.
4 klimmen        anders: Bensafrim, minstens 4 opeenvolgende uren zonder regen en geen regen in de 24 uur ervoor.
Anders niets.

Algemeen
- Een uur telt alleen mee als het begint tussen 30 min voor zonsopgang en 30 min na zonsondergang.
- Een blok = minstens 3 opeenvolgende ideale uren op dezelfde plek (klimmen: 4).
- Afstand = rijtijd met de auto vanaf Ferragudo (OSRM, data/beaches/rijtijd.json); ook de vogelvlucht staat erbij.
- Dagen zonder voorspelling: "nog geen voorspelling".
- Aankomsten en terugvluchten (data/planning/reizen.json) staan bij hun dag; de planning loopt minstens 4 weken
  en zeker tot de laatste vlucht.

Schrijft web/public/data/planning.json.
"""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from pipeline.rules.model import bereken
from pipeline.site.zon_getij import zon

LIS = ZoneInfo("Europe/Lisbon")
FERRAGUDO = (37.1238, -8.5195)
DAGEN = 28
# Ria de Alvor: de wind van het windpunt van Alvor (dat ook Praia do Alvor gebruikt); als ligging
# Praia do Alvor Poente, aan de monding van de ria (uit de stranddata).
ALVOR_WIND = "37.100,-8.600"
ALVOR = {"naam": "Ria de Alvor", "id": "ria-de-alvor", "lat": 37.122296, "lon": -8.59756}
MAX_RIJ_SURF = 120  # minuten (eigenaar: golfsurfen en stille waters alleen tot 2 uur rijden)
RIJ: dict[str, dict | None] = {}
BENSAFRIM = "eigen/bensafrim"


def km(lat: float, lon: float) -> float:
    r, t = 6371.0, math.radians
    dp, dl = t(lat - FERRAGUDO[0]), t(lon - FERRAGUDO[1])
    h = math.sin(dp / 2) ** 2 + math.cos(t(FERRAGUDO[0])) * math.cos(t(lat)) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def telt(lat: float, lon: float, t: datetime) -> bool:
    """Het uur begint tussen 30 min voor zonsopgang en 30 min na zonsondergang."""
    z = zon(lat, lon, t)
    m = t.timestamp() / 60
    return z is not None and z[0] - 30 <= m <= z[1] + 30


def blokken(uren: list[datetime], ok: list[bool], minimum: int) -> list[tuple[int, int]]:
    """Reeksen van minstens `minimum` opeenvolgende goede uren op dezelfde lokale dag: [(eerste, laatste)]."""
    uit, start = [], None
    for i in range(len(uren) + 1):
        goed = i < len(uren) and ok[i] and (start is None or (
            uren[i] - uren[i - 1] == timedelta(hours=1)
            and uren[i].astimezone(LIS).date() == uren[start].astimezone(LIS).date()))
        if goed and start is None:
            start = i
        elif not goed and start is not None:
            if i - start >= minimum:
                uit.append((start, i - 1))
            start = i if i < len(uren) and ok[i] else None
    return uit


def blok(plek: dict, uren: list[datetime], a: int, b: int, **extra) -> dict:
    van = uren[a].astimezone(LIS)
    tot = (uren[b] + timedelta(hours=1)).astimezone(LIS)
    rij = RIJ.get(plek.get("id") or "")
    return {"plek": plek["naam"], "id": plek.get("id"), "van": van.strftime("%H:00"), "tot": tot.strftime("%H:00"),
            "km": round(km(plek["lat"], plek["lon"])), "rij": rij["min"] if rij else None,
            "lat": round(plek["lat"], 5), "lon": round(plek["lon"], 5),
            "dag": van.date().isoformat(), **extra}


def maak(axis: list[str], out: Path, wind_bron: dict, klimweer: dict) -> dict:
    uren = [datetime.fromisoformat(t).replace(tzinfo=UTC) for t in axis]
    per_dag: dict[str, dict[str, list]] = {}

    def voeg(dag: str, sport: str, b: dict):
        per_dag.setdefault(dag, {"golfsurfen": [], "stil": [], "windsurf": [], "klim": []})[sport].append(b)

    # 1 en 2: stranden (de conclusie per uur staat in strand/<id>.json)
    for f in sorted((out / "strand").glob("*.json")):
        d = json.loads(f.read_text())
        plek = {"naam": d["naam"], "id": d["id"], "lat": d["lat"], "lon": d["lon"]}
        licht = [telt(d["lat"], d["lon"], t) for t in uren]
        for sport, tekst in (("golfsurfen", "ideaal golfsurfen"), ("stil", "ideaal stille waters")):
            ok = [licht[i] and (d["conclusie"][i] or "").startswith(tekst) for i in range(len(uren))]
            for a, b in blokken(uren, ok, 3):
                # gemiddelde score van die activiteit over het blok (golfsurfen: kolom 0, stille waters: kolom 3)
                kolom = 0 if sport == "golfsurfen" else 3
                s = [d["scores"][i][kolom] for i in range(a, b + 1)]
                voeg(uren[a].astimezone(LIS).date().isoformat(), sport,
                     blok(plek, uren, a, b, score=round(sum(s) / len(s), 1)))

    # 3: windsurfles op de Ria de Alvor
    w = wind_bron.get(ALVOR_WIND)
    if w:
        idx = {t: k for k, t in enumerate(wind_bron["_tijd"])}
        ok = []
        for i, t in enumerate(axis):
            k = idx.get(t)
            ws = w["wind_speed_10m"][k] if k is not None else None
            if ws is None or not telt(ALVOR["lat"], ALVOR["lon"], uren[i]):
                ok.append(False)
                continue
            vl = max(w["wind_gusts_10m"][k] or ws, ws)  # vlaag lager dan de wind: reken met de wind (model v2)
            r = bereken(0, [], ws, vl, w["wind_direction_10m"][k] or 0, [])  # geen venster, geen golven
            ok.append(r["WIND"] == 2 and r["te_wild"] < 50)
        for a, b in blokken(uren, ok, 3):
            voeg(uren[a].astimezone(LIS).date().isoformat(), "windsurf", blok(ALVOR, uren, a, b))

    # 4: klimmen in Bensafrim
    kw = klimweer.get(BENSAFRIM)
    if kw:
        kt = [datetime.fromisoformat(t).replace(tzinfo=UTC) for t in klimweer["_tijd"]]
        regen = kw.get("precipitation") or []
        k_lat, k_lon = 37.15338, -8.73129
        kplek = {"naam": "Bensafrim", "id": BENSAFRIM, "lat": k_lat, "lon": k_lon}
        droog = [x is not None and x == 0 for x in regen]
        ok = [droog[i] and telt(k_lat, k_lon, kt[i]) for i in range(len(kt))]
        for a, b in blokken(kt, ok, 4):
            # geen regen in de 24 uur vóór het begin van het blok (en die 24 uur moeten in de reeks zitten)
            if a < 24 or any(x is None or x > 0 for x in regen[a - 24:a]):
                continue
            if kt[a] < uren[0]:
                continue
            voeg(kt[a].astimezone(LIS).date().isoformat(), "klim", blok(kplek, kt, a, b))

    # Per dag kiezen wat getoond wordt
    vandaag = datetime.now(LIS).date()
    # Een dag telt pas als de voorspelling tot minstens 20:00 die dag loopt (anders "nog geen voorspelling").
    laatste = (uren[-1].astimezone(LIS) - timedelta(hours=20)).date()
    reispad = Path(__file__).resolve().parents[2] / "data" / "planning" / "reizen.json"
    reizen = json.loads(reispad.read_text())["reizen"] if reispad.exists() else []
    per_reisdag: dict[str, list] = {}
    for r in reizen:
        per_reisdag.setdefault(r["dag"], []).append({"soort": r["soort"], "wie": r["wie"]})
    eind = max([vandaag + timedelta(days=DAGEN - 1)] + [datetime.fromisoformat(r["dag"]).date() for r in reizen])
    dagen = []
    for n in range((eind - vandaag).days + 1):
        dag = vandaag + timedelta(days=n)
        s = dag.isoformat()
        if dag > laatste:
            dagen.append({"dag": s, "voorspelling": False, "reizen": per_reisdag.get(s, [])})
            continue
        p = per_dag.get(s, {"golfsurfen": [], "stil": [], "windsurf": [], "klim": []})
        # Alle blokken per sport, vóór de keuze: de site kiest daarmee opnieuw vanaf het verblijf van de bezoeker
        # (eigen plaats en maximale rijtijd); "keuze" is de keuze vanaf Ferragudo met 2 uur rijden.
        kandidaten = {k: [dict(b) for b in v] for k, v in p.items()}
        lengte = lambda b: int(b["tot"][:2]) - int(b["van"][:2])  # noqa: E731
        keuze = None
        # Surf alleen tot 2 uur rijden; zonder gekende rijtijd telt een strand niet mee.
        p["golfsurfen"] = [b for b in p["golfsurfen"] if b["rij"] is not None and b["rij"] <= MAX_RIJ_SURF]
        if p["golfsurfen"]:
            # Eerst de beste condities (hoogste gemiddelde golfsurfscore, afgerond zoals getoond),
            # dan van die blokken de kortste rijtijd.
            beste = max(round(b["score"]) for b in p["golfsurfen"])
            top = [b for b in p["golfsurfen"] if round(b["score"]) == beste]
            keuze = {"sport": "golfsurfen", **min(top, key=lambda b: b["rij"])}
        elif p["windsurf"]:
            keuze = {"sport": "windsurf", **max(p["windsurf"], key=lengte)}
        elif stil := [b for b in p["stil"] if b["rij"] is not None and b["rij"] <= MAX_RIJ_SURF]:
            beste = max(round(b["score"]) for b in stil)
            keuze = {"sport": "stil", **min([b for b in stil if round(b["score"]) == beste], key=lambda b: b["rij"])}
        elif p["klim"]:
            keuze = {"sport": "klim", **max(p["klim"], key=lengte)}
        dagen.append({"dag": s, "voorspelling": True, "keuze": keuze, "kandidaten": kandidaten,
                      "reizen": per_reisdag.get(s, [])})
    uit = {"gemaakt": datetime.now(UTC).strftime("%Y-%m-%dT%H:%MZ"), "dagen": dagen}
    (out / "planning.json").write_text(json.dumps(uit, ensure_ascii=False, separators=(",", ":")))
    return uit


def main(axis: list[str], out: Path, root: Path) -> None:
    rij = root / "data" / "beaches" / "rijtijd.json"
    RIJ.clear()
    if rij.exists():
        RIJ.update(json.loads(rij.read_text())["plekken"])
    else:
        print("planning: nog geen rijtijden (data/beaches/rijtijd.json); geen surf in de planning")
    fc = root / "data" / "forecast"
    wind = json.loads((fc / "wind_gfs.json").read_text()) if (fc / "wind_gfs.json").exists() else {}
    kw = json.loads((fc / "klim_weer.json").read_text()) if (fc / "klim_weer.json").exists() else {}
    p = maak(axis, out, wind, kw)
    n = sum(1 for d in p["dagen"] if (d.get("keuze") or {}).get("sport") == "golfsurfen")
    print(f"planning: {len(p['dagen'])} dagen, {n} met golfsurfen")


if __name__ == "__main__":  # pragma: no cover
    ROOT = Path(__file__).resolve().parents[2]
    ax = json.loads((ROOT / "web" / "public" / "data" / "index.json").read_text())["tijd"]
    main(ax, ROOT / "web" / "public" / "data", ROOT)
