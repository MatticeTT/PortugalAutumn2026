"""Databestanden voor de laag Klimmen op de site.

Schrijft web/public/data/klim/:
- kaart.json         alle plekken (pipeline/klim/plekken.py), met per plek het weerbestand (w)
- rood.json          per plek-id per uur één teken: 0 geen, 1 het regent, 2 zandsteen nat, - geen weer
- status.json        per bron: gelukt of niet, en wanneer opgehaald (de site toont een melding bij een fout)
- weer/<plek>.json   per plek (weer op de plek zelf) per uur: neerslag (mm), luchtvochtigheid (%),
                     temperatuur (°C), wind (kn), uren sinds de laatste regen, regen in de 24 uur ervoor
Uren op dezelfde tijdas als de surfdata (index.json).
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from pipeline.klim.plekken import MAP, alle
from pipeline.klim.weer import per_uur

ROOT = Path(__file__).resolve().parents[2]
FC = ROOT / "data" / "forecast"


def bestand(k: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", k)


def main(axis: list[str], out: Path) -> None:
    plekken = alle()
    if not plekken:
        print("klim: geen plekken")
        return
    weer = json.loads((FC / "klim_weer.json").read_text()) if (FC / "klim_weer.json").exists() else {}
    tijd = weer.get("_tijd", [])
    pos = {t: k for k, t in enumerate(tijd)}
    doel = out / "klim"
    shutil.rmtree(doel, ignore_errors=True)
    (doel / "weer").mkdir(parents=True, exist_ok=True)
    rood: dict[str, str] = {}
    met_weer = 0
    for q in plekken:
        w = weer.get(q["id"])
        reeks = (w or {}).get("precipitation") or []
        q["w"] = None
        if not w:
            continue
        rood[q["id"]] = "".join(per_uur({"rots": q["rots"]}, reeks, pos[t])["rood"]
                                if pos.get(t) is not None and pos[t] < len(reeks) else "-" for t in axis)
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
        q["w"] = bestand(q["id"])
        (doel / "weer" / f"{q['w']}.json").write_text(json.dumps(serie, separators=(",", ":")))
        met_weer += 1
    (doel / "kaart.json").write_text(json.dumps(plekken, ensure_ascii=False, separators=(",", ":")))
    (doel / "rood.json").write_text(json.dumps(rood, separators=(",", ":")))
    status = MAP / "status.json"
    (doel / "status.json").write_text(status.read_text() if status.exists() else "{}")
    print(f"klim: {len(plekken)} plekken, {met_weer} met weer")
