"""De planning voor de komende 4 weken (tabblad /planning; eigenaar en rekenchat, 8 oktober 2026).

Per dag precies één resultaat, in deze volgorde (eigenaar; de site laat de volgorde aanpassen):
1 golfsurfen     conclusie "ideaal golfsurfen", alleen stranden tot 2 uur rijden van Ferragudo; daarvan
                 eerst de beste condities (hoogste gemiddelde golfsurfscore over het blok, afgerond), en van
                 die het blok met de kortste rijtijd.
2 windsurfen     anders: conclusie "ideaal windsurfen", zelfde werkwijze als golfsurfen (score windsurfen).
3 stille waters  anders: conclusie "ideaal stille waters", zelfde werkwijze (score stille waters).
4 klimmen        anders: elke klimplek (sport of trad) tot 2 uur rijden, minstens 4 opeenvolgende uren zonder
                 regen en geen regen in de 24 uur ervoor; eerst het langste blok, dan de kortste rijtijd.
Anders niets. Dezelfde regels in alle landen.

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

from pipeline.site.inpakken import conclusies_uitpakken
from pipeline.site.zon_getij import zon

LIS = ZoneInfo("Europe/Lisbon")
FERRAGUDO = (37.1238, -8.5195)
DAGEN = 28
MAX_RIJ_SURF = 120  # minuten (eigenaar: alleen tot 2 uur rijden)
RIJ: dict[str, dict | None] = {}
# Per strand-sport: de conclusie die telt en de kolom van zijn score in "scores" (volgorde van model.VOLGORDE).
STRAND_SPORT = (("golfsurfen", "ideaal golfsurfen", 0), ("windsurf", "ideaal windsurfen", 2),
                ("stil", "ideaal stille waters", 3))


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
        per_dag.setdefault(dag, {"golfsurfen": [], "stil": [], "windsurf": [], "klim": []})[sport].append(b)

    # Andere landen: alleen kandidaten (blokken golfsurfen en stille waters), per land een eigen bestand
    # planning_<land>.json; de site laadt een land pas als het binnen de rijtijd van het verblijf kan liggen.
    per_land: dict[str, dict[str, dict[str, list]]] = {}
    per_land_plekken: dict[str, dict[str, list]] = {}

    # 1 en 2: stranden (de conclusie per uur staat in strand/<id>.json)
    for f in sorted((out / "strand").glob("*.json")):
        d = json.loads(f.read_text())
        plek = {"naam": d["naam"], "id": d["id"], "lat": d["lat"], "lon": d["lon"]}
        land = d.get("land")
        conclusies_uitpakken(d)  # compacte fiche (andere landen): conclusies en scores terug per uur
        if land and land in per_land_plekken and d["id"] in per_land_plekken[land]:
            continue  # al gezien (zelfde strand)
        if land:
            doel = per_land.setdefault(land, {})
            per_land_plekken.setdefault(land, {})[d["id"]] = [d["naam"], round(d["lat"], 5), round(d["lon"], 5)]
            licht = [telt(d["lat"], d["lon"], t) for t in uren]
            for sport, tekst, kolom in STRAND_SPORT:
                ok = [licht[i] and (d["conclusie"][i] or "").startswith(tekst) for i in range(len(uren))]
                for a, b in blokken(uren, ok, 3):
                    s = [d["scores"][i][kolom] for i in range(a, b + 1)]
                    bl = blok(plek, uren, a, b, score=round(sum(s) / len(s), 1)) | {"rij": None}
                    doel.setdefault(uren[a].astimezone(LIS).date().isoformat(), {}).setdefault(sport, []).append(bl)
            continue
        licht = [telt(d["lat"], d["lon"], t) for t in uren]
        for sport, tekst, kolom in STRAND_SPORT:
            ok = [licht[i] and (d["conclusie"][i] or "").startswith(tekst) for i in range(len(uren))]
            for a, b in blokken(uren, ok, 3):
                # gemiddelde score van die activiteit over het blok
                s = [d["scores"][i][kolom] for i in range(a, b + 1)]
                voeg(uren[a].astimezone(LIS).date().isoformat(), sport,
                     blok(plek, uren, a, b, score=round(sum(s) / len(s), 1)))

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
        p = per_dag.get(s, {"golfsurfen": [], "stil": [], "windsurf": [], "klim": []})
        # Alle blokken per sport, vóór de keuze: de site kiest daarmee opnieuw vanaf het verblijf van de bezoeker
        # (eigen plaats en maximale rijtijd); "keuze" is de keuze vanaf Ferragudo met 2 uur rijden.
        kandidaten = {k: [dict(b) for b in v] for k, v in p.items()}
        lengte = lambda b: int(b["tot"][:2]) - int(b["van"][:2])  # noqa: E731
        keuze = None
        # Alleen tot 2 uur rijden; zonder gekende rijtijd telt een plek niet mee.
        for sport in ("golfsurfen", "windsurf", "stil", "klim"):
            bs = [b for b in p[sport] if b["rij"] is not None and b["rij"] <= MAX_RIJ_SURF]
            if not bs:
                continue
            if sport == "klim":  # eerst het langste blok, dan de kortste rijtijd
                langst = max(lengte(b) for b in bs)
                keuze = {"sport": sport, **min([b for b in bs if lengte(b) == langst], key=lambda b: b["rij"])}
            else:  # eerst de beste condities (gemiddelde score, afgerond zoals getoond), dan de kortste rijtijd
                beste = max(round(b["score"]) for b in bs)
                keuze = {"sport": sport, **min([b for b in bs if round(b["score"]) == beste], key=lambda b: b["rij"])}
            break
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
    n = sum(1 for d in p["dagen"] if (d.get("keuze") or {}).get("sport") == "golfsurfen")
    print(f"planning: {len(p['dagen'])} dagen, {n} met golfsurfen")


if __name__ == "__main__":  # pragma: no cover
    ROOT = Path(__file__).resolve().parents[2]
    ax = json.loads((ROOT / "web" / "public" / "data" / "index.json").read_text())["tijd"]
    main(ax, ROOT / "web" / "public" / "data", ROOT)
