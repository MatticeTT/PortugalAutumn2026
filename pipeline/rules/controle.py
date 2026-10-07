"""Controles op de stranddata (document "Surfkaart rekenmodel v2"), voor alle stranden.

python -m pipeline.rules.controle      → overzicht op het scherm
Schrijft ook web/public/data/controle.json voor het controlescherm (web/controle.html).
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from pipeline.rules.hulp import KOMPAS, controle

ROOT = Path(__file__).resolve().parents[2]


def alle() -> list[dict]:
    fc = json.loads((ROOT / "data" / "beaches" / "stranden.geojson").read_text())
    out = []
    for f in fc["features"]:
        p = f["properties"]
        c = controle(p["kijkrichting"], p["venster"])
        out.append({"id": p["id"], "naam": p["naam"], "district": p["district"], "kust": p["kijkrichting"],
                    "venster": p["venster"], **c})
    return out


def main():
    rij = alle()
    for soort in ("blokkerend", "nakijken"):
        n = sum(1 for r in rij if r[soort])
        print(f"{n:4d} van {len(rij)} stranden {soort}")
        for s, k in Counter(f.split(":")[0] for r in rij for f in r[soort]).most_common():
            print(f"       {k:4d}  {s}")
    out = ROOT / "web" / "public" / "data"
    out.mkdir(parents=True, exist_ok=True)
    (out / "controle.json").write_text(json.dumps({"kompas": KOMPAS, "stranden": rij}, ensure_ascii=False,
                                                  separators=(",", ":")))
    return rij


if __name__ == "__main__":
    main()
