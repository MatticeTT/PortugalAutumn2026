"""Databestanden voor de klimplekken op de site.

Schrijft web/public/data/klim/:
- kaart.json         per plek: id, naam, soort (M muurklimmen, B boulderen), ligging, label (graad of "?"),
                     rotssoort, wandrichting, de vier graden, en het weerpunt
- rood.json          per plek (zelfde volgorde) per uur één teken: 0 geen, 1 het regent, 2 zandsteen nat,
                     - geen weer
- weer/<punt>.json   per weerpunt per uur: neerslag (mm), luchtvochtigheid (%), temperatuur (°C), wind (kn),
                     uren sinds de laatste regen en of het in de 24 uur ervoor geregend heeft
Uren op dezelfde tijdas als de surfdata (index.json).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from pipeline.klim.weer import label, per_uur

ROOT = Path(__file__).resolve().parents[2]
PLEKKEN = ROOT / "data" / "klim" / "plekken.json"
FC = ROOT / "data" / "forecast"


def bestand(k: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", k)


def main(axis: list[str], out: Path) -> None:
    if not PLEKKEN.exists():
        print("klim: nog geen data/klim/plekken.json")
        return
    plekken = json.loads(PLEKKEN.read_text())["plekken"]
    weer = json.loads((FC / "klim_weer.json").read_text()) if (FC / "klim_weer.json").exists() else {}
    punt_van = json.loads((FC / "klim_punten.json").read_text()) if (FC / "klim_punten.json").exists() else {}
    tijd = weer.get("_tijd", [])
    (out / "klim" / "weer").mkdir(parents=True, exist_ok=True)

    # Per weerpunt: de reeksen vanaf 2 dagen terug, en de plaats van elk uur van de tijdas daarin.
    pos = {t: k for k, t in enumerate(tijd)}
    kaart, rood = [], []
    gedaan: set[str] = set()
    for q in plekken:
        k = punt_van.get(q["id"])
        w = weer.get(k) if k else None
        rij = []
        reeks = (w or {}).get("precipitation") or []
        for t in axis:
            j = pos.get(t)
            rij.append(per_uur(q, reeks, j)["rood"] if w and j is not None and j < len(reeks) else "-")
        rood.append("".join(rij))
        if w and k not in gedaan:
            gedaan.add(k)
            serie = {"neerslag": [], "vocht": [], "temp": [], "wind": [], "sinds": [], "regen24": []}
            for t in axis:
                j = pos.get(t)
                ok = j is not None and j < len(reeks)
                oordeel = per_uur({}, reeks, j) if ok else {"sinds": None, "regen24": None}
                serie["neerslag"].append(reeks[j] if ok else None)
                for naam, var in (("vocht", "relative_humidity_2m"), ("temp", "temperature_2m"),
                                  ("wind", "wind_speed_10m")):
                    v = w.get(var) or []
                    serie[naam].append(v[j] if ok and j < len(v) else None)
                serie["sinds"].append(oordeel["sinds"])
                serie["regen24"].append(None if oordeel["regen24"] is None else int(oordeel["regen24"]))
            serie["terug"] = pos.get(axis[0], 0)  # zoveel uur reeks vóór het eerste uur ("meer dan ... uur")
            (out / "klim" / "weer" / f"{bestand(k)}.json").write_text(json.dumps(serie, separators=(",", ":")))
        kaart.append({
            "id": q["id"], "n": q["naam"], "s": "B" if q["soort"] == "boulderen" else "M",
            "x": q["lon"], "y": q["lat"], "g": label(q), "rots": q["rots"], "richting": q["richting"],
            "graden": {g: q[g] for g in ("french:min", "french:max", "font:min", "font:max")},
            "w": bestand(k) if w else None,
        })
    (out / "klim" / "kaart.json").write_text(json.dumps(kaart, ensure_ascii=False, separators=(",", ":")))
    (out / "klim" / "rood.json").write_text(json.dumps(rood, separators=(",", ":")))
    print(f"klim: {len(kaart)} plekken, {len(gedaan)} weerpunten")
