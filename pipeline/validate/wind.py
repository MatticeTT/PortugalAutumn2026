"""M6: windmodellen naast de IPMA-kuststations, per vooruitzicht (0 tot 4 dagen).

Leest het archief (tak `archief`, zie archive.py): per run de voorspelling van GFS en ECMWF
op het windpunt bij elk kuststation, en de metingen van de laatste 24 uur. Metingen van
verschillende runs worden samengevoegd. Schrijft data/validate/wind.json.
"""

from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "validate" / "wind.json"
KMH_PER_KN = 1.852
MIN_PAREN = 100


def stats(pairs):
    n = len(pairs)
    if n < MIN_PAREN:
        return {"n": n, "te_weinig": True}
    mo = sum(o for o, _ in pairs) / n
    bias = sum(m - o for o, m in pairs) / n
    rmse = math.sqrt(sum((m - o) ** 2 for o, m in pairs) / n)
    within2 = sum(abs(m - o) <= 2 for o, m in pairs) / n
    return {"n": n, "gemiddeld_gemeten_kn": round(mo, 2), "afwijking_kn": round(bias, 2), "rmse_kn": round(rmse, 2),
            "binnen_2_kn_pct": round(100 * within2, 1)}


def main(archive: Path):
    files = sorted(archive.glob("*/*Z.json"))
    obs: dict[tuple[str, str], float] = {}
    runs = []
    for f in files:
        rec = json.loads(f.read_text())
        runs.append(rec)
        for sid, st in rec.get("ipma_stations", {}).items():
            for t, v in st.get("metingen", {}).items():
                kmh = (v or {}).get("intensidadeVentoKM")
                if kmh is not None and kmh >= 0:
                    obs[(sid, t[:13])] = kmh / KMH_PER_KN
    pairs = defaultdict(list)  # (model, vooruitzicht in dagen) -> [(gemeten, voorspeld)]
    for rec in runs:
        made = datetime.fromisoformat(rec["gemaakt"].replace("Z", "+00:00"))
        for sid, st in rec.get("ipma_stations", {}).items():
            for model, fc in st.get("voorspelling", {}).items():
                times = rec["tijd"][model]
                for t, v in zip(times, fc.get("wind_speed_10m", []), strict=False):
                    o = obs.get((sid, t[:13]))
                    if v is None or o is None:
                        continue
                    lead = (datetime.fromisoformat(t).replace(tzinfo=UTC) - made).total_seconds() / 86400
                    if lead < 0:
                        continue
                    pairs[(model, int(lead))].append((o, v))
    res = {"gemaakt": datetime.now(UTC).strftime("%Y-%m-%dT%H:%MZ"), "runs": len(runs), "metingen": len(obs),
           "per_model": {}}
    for (model, lead), p in sorted(pairs.items()):
        res["per_model"].setdefault(model, {})[f"dag_{lead}"] = stats(p)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps(res, ensure_ascii=False)[:1500])


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "archief")
