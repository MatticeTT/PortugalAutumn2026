# ruff: noqa: E501
"""De TypeScript-versie (web/src/score.ts) geeft exact dezelfde uitkomst als pipeline/rules/score.py.

Bundelt score.ts met esbuild, draait het met node op duizenden willekeurige gevallen en vergelijkt."""
import json
import random
import shutil
import subprocess
from pathlib import Path

import pytest

from pipeline.rules import score as py

ROOT = Path(__file__).resolve().parents[1]
ESBUILD = ROOT / "web" / "node_modules" / ".bin" / "esbuild"


def gevallen(n=5000, seed=7):
    rnd = random.Random(seed)
    uit = []
    for _ in range(n):
        c = dict(wind=round(rnd.uniform(0, 50), 1), windhoek=round(rnd.uniform(0, 180)),
                 golfhoogte=round(rnd.uniform(0, 7), 2), periode=round(rnd.uniform(1, 22), 1),
                 golfhoek=round(rnd.uniform(0, 90)), golf_aan_strand=round(rnd.uniform(0, 3), 2))
        c["vlaag"] = round(c["wind"] + rnd.uniform(0, 20), 1)
        if rnd.random() < .5:
            c["stroming"], c["stroming_tov_wind"] = round(rnd.uniform(0, 3), 2), rnd.choice(["tegen", "mee", "dwars"])
        if rnd.random() < .3:
            c["aandeel_hoofdgolf"] = round(rnd.random(), 2)
        if rnd.random() < .3:
            c["neerslag"] = round(rnd.uniform(0, 10), 1)
        if rnd.random() < .2:
            c["gewicht"] = rnd.choice([55, 65, 75, 85, 100])
        if rnd.random() < .03:
            c["onweer"] = True
        if rnd.random() < .1:
            c["hb"] = round(rnd.uniform(0, 5), 2)
        uit.append((c, rnd.choice([None, "beginner", "gemiddeld", "ervaren"])))
    return uit


def verwacht(c, niveau):
    r = py.strand_uur(c, niveau)
    return {"golf": {k: r["golf"][k] for k in ("cijfer", "rand", "beste", "scores", "te_veel")},
            "wind": {k: r["wind"][k] for k in ("cijfer", "rand", "beste", "scores", "te_veel")},
            "stil": [r["stille_waters"]["score"], r["stille_waters"]["cijfer"]],
            "storm": r["storm"], "gevaar": r["te_gevaarlijk"],
            "w": {k: py.waarschuwingen(k, c) for k in py.CATEGORIES}}


def test_parameters_gelijk():
    a = json.loads((ROOT / "pipeline/rules/score_parameters.json").read_text())
    b = json.loads((ROOT / "web/src/score_parameters.json").read_text())
    assert a == b


@pytest.mark.skipif(not ESBUILD.exists() or not shutil.which("node"), reason="esbuild of node ontbreekt")
def test_ts_gelijk_aan_python(tmp_path):
    bundel = tmp_path / "score.mjs"
    subprocess.run([str(ESBUILD), str(ROOT / "web/src/score.ts"), "--bundle", "--format=esm",
                    "--platform=node", f"--outfile={bundel}"], check=True, capture_output=True)
    gs = gevallen()
    (tmp_path / "in.json").write_text(json.dumps([[c, n] for c, n in gs]))
    (tmp_path / "run.mjs").write_text("""
import { readFileSync } from 'node:fs'
import * as s from './score.mjs'
const gs = JSON.parse(readFileSync(new URL('./in.json', import.meta.url)))
const uit = gs.map(([c, n]) => {
  const r = s.strandUur(c, n)
  const g = (x) => ({ cijfer: x.cijfer, rand: x.rand, beste: x.beste, scores: x.scores, te_veel: x.te_veel })
  return { golf: g(r.golf), wind: g(r.wind), stil: [r.stille_waters.score, r.stille_waters.cijfer],
           storm: r.storm, gevaar: r.te_gevaarlijk, w: Object.fromEntries(s.CATEGORIES.map((k) => [k, s.waarschuwingen(k, c)])) }
})
console.log(JSON.stringify(uit))
""")
    out = subprocess.run(["node", str(tmp_path / "run.mjs")], check=True, capture_output=True, text=True).stdout
    ts = json.loads(out)
    fouten = []
    for (c, n), t in zip(gs, ts, strict=True):
        p = json.loads(json.dumps(verwacht(c, n)))
        if p != t:
            fouten.append((c, n, p, t))
    assert not fouten, f"{len(fouten)} verschillen, eerste: {fouten[0]}"
