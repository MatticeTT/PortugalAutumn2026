# ruff: noqa: E501
"""Kaart en fiche rekenen hetzelfde: de fiche (web/src/invoer.ts + score.ts) rekent uit de bewaarde invoer per uur
exact de tekens die in sport/score_*.json staan (pipeline/site/build_data.py). Alleen als de site-data gebouwd is."""
import json
import random
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "web" / "public" / "data"
ESBUILD = ROOT / "web" / "node_modules" / ".bin" / "esbuild"

pytestmark = pytest.mark.skipif(not (DATA / "sport" / "score_alle.json").exists() or not ESBUILD.exists()
                                or not shutil.which("node"), reason="geen site-data of geen node")


def test_fiche_gelijk_aan_kaart(tmp_path):
    (tmp_path / "entry.ts").write_text(f"""
import {{ readFileSync }} from 'node:fs'
import {{ conditiesUur }} from '{ROOT}/web/src/invoer'
import {{ strandUur }} from '{ROOT}/web/src/score'
import {{ uitpakken }} from '{ROOT}/web/src/inpakken'
import {{ tekenVan }} from '{ROOT}/web/src/scorekaart'
const [kaartPad, scorePad, dataDir, nrs] = process.argv.slice(2)
const kaart = JSON.parse(readFileSync(kaartPad, 'utf8'))
const sc = Object.fromEntries(['alle', 'beginner', 'gemiddeld', 'ervaren'].map((n) => [n, JSON.parse(readFileSync(scorePad.replace('alle', n), 'utf8'))]))
let fout = 0, getest = 0
for (const k of JSON.parse(nrs)) {{
  const s = kaart[k]
  const d = uitpakken(JSON.parse(readFileSync(`${{dataDir}}/strand/${{s.id.replace(/[^A-Za-z0-9_.-]/g, '_')}}.json`, 'utf8')))
  if (d.onzeker) continue
  const n = d.wind.length
  for (let i = 0; i < n; i++) {{
    const c = conditiesUur(d, i)
    if (!c) continue
    for (const nv of ['alle', 'beginner', 'gemiddeld', 'ervaren']) {{
      const u = strandUur(c, nv === 'alle' ? null : nv as any)
      const [g, w, st] = tekenVan(u)
      const rij = sc[nv][k]
      const want = rij.slice(2 * i, 2 * i + 2) + (nv === 'alle' ? rij[2 * n + i] : '')
      const got = g + w + (nv === 'alle' ? st : '')
      getest++
      if (want !== got) {{ fout++; if (fout < 5) console.error(s.id, i, nv, want, got, JSON.stringify(c)) }}
    }}
  }}
}}
console.log(JSON.stringify({{ fout, getest }}))
""")
    subprocess.run([str(ESBUILD), str(tmp_path / "entry.ts"), "--bundle", "--format=esm", "--platform=node",
                    f"--outfile={tmp_path / 'e.mjs'}"], check=True, capture_output=True)
    kaart = json.loads((DATA / "kaart.json").read_text())
    nrs = random.Random(5).sample(range(len(kaart)), min(300, len(kaart)))
    r = subprocess.run(["node", str(tmp_path / "e.mjs"), str(DATA / "kaart.json"), str(DATA / "sport" / "score_alle.json"),
                        str(DATA), json.dumps(nrs)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-3000:]
    uit = json.loads(r.stdout)
    assert uit["getest"] > 1000
    assert uit["fout"] == 0, r.stderr[-3000:]
