"""De planning voor de komende 4 weken (tabblad /planning; eigenaar en rekenchat).

Score van de rekenchat (versie 2.1, pipeline/rules/score.py). Per strand en per categorie (17 categorieën:
7 golfsporten, 10 windsporten) en voor stille waters: de blokken van minstens 3 opeenvolgende uren met een score
van 60 of meer ("ga", cijfer 3 of 4), met de gemiddelde score over het blok. Klimmen: elke klimplek (sport of
trad), minstens 4 opeenvolgende uren zonder regen en geen regen in de 24 uur ervoor.

De site kiest per dag één plan: de bezoeker kiest een categorie voor golfsporten en een voor windsporten, en de
volgorde van voorrang (standaard golfsporten, windsporten, stille waters, klimmen). Per sport eerst de beste
gemiddelde score (afgerond), dan de kortste rijtijd vanaf het verblijf; klimmen: het langste blok, dan de kortste
rijtijd. De scores zijn gerekend met het standaardgewicht (75 kg).

Algemeen
- Een uur telt alleen mee als het begint tussen 30 min voor zonsopgang en 30 min na zonsondergang.
- Afstand = rijtijd met de auto vanaf Ferragudo (OSRM, data/beaches/rijtijd.json) zolang er geen verblijf is.
- Dagen zonder voorspelling: "nog geen voorspelling".
- Aankomsten en terugvluchten (data/planning/reizen.json) staan bij hun dag; de planning loopt minstens 4 weken
  en zeker tot de laatste vlucht.

Schrijft web/public/data/planning.json (Portugal en klimmen) en planning_<land>.json (compact, andere landen).
"""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from pipeline.rules.score import GO
from pipeline.site.zon_getij import zon

LIS = ZoneInfo("Europe/Lisbon")
FERRAGUDO = (37.1238, -8.5195)
DAGEN = 28
RIJ: dict[str, dict | None] = {}
# Per strand: naam, ligging, land en per categorie (en "stil") de score per uur (0-100, 255 = geen score).
# Gevuld door build_data.strand().
SCORES: dict[str, dict] = {}


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


def maak(axis: list[str], out: Path, klimweer: dict, klimplekken: list[dict]) -> dict:
    uren = [datetime.fromisoformat(t).replace(tzinfo=UTC) for t in axis]
    per_dag: dict[str, dict[str, list]] = {}

    def voeg(dag: str, sport: str, b: dict):
        per_dag.setdefault(dag, {}).setdefault(sport, []).append(b)

    # Andere landen: per land een eigen, compact bestand planning_<land>.json; de site laadt een land pas als
    # het binnen de rijtijd van het verblijf kan liggen.
    per_land: dict[str, dict[str, dict[str, list]]] = {}
    per_land_plekken: dict[str, dict[str, list]] = {}

    # Stranden: per categorie de blokken van minstens 3 uur met een score van 60 of meer.
    for pid, st in SCORES.items():
        plek = {"naam": st["naam"], "id": pid, "lat": st["lat"], "lon": st["lon"]}
        land = st["land"] if st["land"] != "pt" else None
        licht = [telt(st["lat"], st["lon"], t) for t in uren]
        if land:
            per_land_plekken.setdefault(land, {})[pid] = [st["naam"], round(st["lat"], 5), round(st["lon"], 5)]
        for sport, reeks in st["scores"].items():
            ok = [licht[i] and reeks[i] != 255 and reeks[i] >= GO for i in range(len(uren))]
            for a, b in blokken(uren, ok, 3):
                sc = [reeks[i] for i in range(a, b + 1)]
                bl = blok(plek, uren, a, b, score=round(sum(sc) / len(sc), 1))
                if land:
                    per_land.setdefault(land, {}).setdefault(bl["dag"], {}).setdefault(sport, []).append(bl)
                else:
                    voeg(bl["dag"], sport, bl)

    # Klimmen: elke klimplek met sport of trad (boulderen wordt niet gepland), per plek de droge blokken.
    kt = [datetime.fromisoformat(t).replace(tzinfo=UTC) for t in klimweer.get("_tijd", [])]
    for kp in klimplekken:
        if not ({"sport", "trad"} & set(kp.get("disciplines") or [])):
            continue
        kw = klimweer.get(kp["id"])
        if not kw:
            continue
        regen = kw.get("precipitation") or []
        kplek = {"naam": kp["naam"], "id": kp["id"], "lat": kp["lat"], "lon": kp["lon"]}
        droog = [x is not None and x == 0 for x in regen]
        ok = [droog[i] and telt(kp["lat"], kp["lon"], kt[i]) for i in range(min(len(kt), len(droog)))]
        for a, b in blokken(kt, ok, 4):
            # geen regen in de 24 uur vóór het begin van het blok (en die 24 uur moeten in de reeks zitten)
            if a < 24 or any(x is None or x > 0 for x in regen[a - 24:a]):
                continue
            if kt[a] < uren[0]:
                continue
            bl = blok(kplek, kt, a, b)
            land = kp.get("land")
            if land and land != "pt":
                per_land_plekken.setdefault(land, {})[kp["id"]] = [kp["naam"], round(kp["lat"], 5), round(kp["lon"], 5)]
                dagen_land = per_land.setdefault(land, {}).setdefault(bl["dag"], {})
                dagen_land.setdefault("klim", []).append(bl | {"rij": None})
            else:
                voeg(bl["dag"], "klim", bl)

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
        # Alle blokken per sport (categorie, stil, klim); de site kiest daarmee vanaf het verblijf van de bezoeker.
        kandidaten = {k: [dict(b) for b in v] for k, v in per_dag.get(s, {}).items()}
        keuze = None
        dagen.append({"dag": s, "voorspelling": True, "keuze": keuze, "kandidaten": kandidaten,
                      "reizen": per_reisdag.get(s, [])})
    uit = {"gemaakt": datetime.now(UTC).strftime("%Y-%m-%dT%H:%MZ"), "dagen": dagen}
    (out / "planning.json").write_text(json.dumps(uit, ensure_ascii=False, separators=(",", ":")))
    # Compact: elke plek één keer (naam, lat, lon), per dag per sport [id, van, tot, score].
    for land, dagen_land in per_land.items():
        kort = {dag: {sp: [[b["id"], b["van"], b["tot"], b.get("score")] for b in bs] for sp, bs in sporten.items()}
                for dag, sporten in dagen_land.items()}
        (out / f"planning_{land}.json").write_text(json.dumps(
            {"land": land, "plekken": per_land_plekken.get(land, {}), "dagen": kort},
            ensure_ascii=False, separators=(",", ":")))
    return uit


def main(axis: list[str], out: Path, root: Path) -> None:
    rij = root / "data" / "beaches" / "rijtijd.json"
    RIJ.clear()
    if rij.exists():
        RIJ.update(json.loads(rij.read_text())["plekken"])
    else:
        print("planning: nog geen rijtijden (data/beaches/rijtijd.json); geen surf in de planning")
    fc = root / "data" / "forecast"
    kw = json.loads((fc / "klim_weer.json").read_text()) if (fc / "klim_weer.json").exists() else {}
    from pipeline.klim.plekken import alle
    p = maak(axis, out, kw, alle())
    n = sum(1 for d in p["dagen"] if any(k.startswith(("golfsurfen", "longboard", "shortboard"))
                                         for k in d.get("kandidaten") or {}))
    print(f"planning: {len(p['dagen'])} dagen, {n} met een golfsportblok in Portugal")


if __name__ == "__main__":  # pragma: no cover
    ROOT = Path(__file__).resolve().parents[2]
    ax = json.loads((ROOT / "web" / "public" / "data" / "index.json").read_text())["tijd"]
    main(ax, ROOT / "web" / "public" / "data", ROOT)
