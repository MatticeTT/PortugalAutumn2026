"""M2: onze voorspelling naast de officiële getijtafel 2026 leggen.

Klaar als (PLAN.md M2): per hoofdhaven valt de helft van de tijdsverschillen binnen
3 minuten en 95 procent binnen 10 minuten, met hoogtes binnen 0,1 m.

Hoogtes: onze voorspelling is MSL + 2,00 m. De tabel noemt per haven het gemiddelde
niveau boven het Zero Hidrográfico ("Nível médio"); we vergelijken met beide.
Schrijft alleen de verschillen naar data/tides/controle.json, nooit de tabel zelf.
"""

from __future__ import annotations

import json
import statistics
from bisect import bisect_left
from datetime import UTC, datetime
from pathlib import Path

from pipeline.tides import interp, table

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "tides" / "controle.json"
ZH = 2.00


def pct(xs, lim):
    return round(100 * sum(abs(x) <= lim for x in xs) / len(xs), 1) if xs else None


def compare(port: table.Port, stations) -> dict:
    official = table.classify(port)
    a, b, w, km = interp.weights(port.lon, port.lat, stations)
    pred = interp.predict_at(port.lon, port.lat, stations)
    pt = [e[0] for e in pred]
    dts, dhs, dhs_nm = [], [], []
    signed = []
    unmatched = 0
    for t, h, hi in official:
        m = int(t.timestamp() // 60)
        i = bisect_left(pt, m)
        cands = [pred[j] for j in (i - 1, i) if 0 <= j < len(pred) and bool(pred[j][2]) == hi]
        if not cands:
            unmatched += 1
            continue
        e = min(cands, key=lambda e: abs(e[0] - m))
        if abs(e[0] - m) > 120:
            unmatched += 1
            continue
        dt = e[0] - m
        dts.append(abs(dt))
        signed.append(dt)
        ours = e[1] / 100  # MSL + 2,00
        dhs.append(ours - h)
        if port.nivel_medio is not None:
            dhs_nm.append(ours - ZH + port.nivel_medio - h)
    res = {
        "haven": port.name,
        "stations": [a, b] if a != b else [a],
        "gewicht": round(w, 2),
        "km_langs_kust": round(km),
        "extremen_tabel": len(official),
        "niet_gekoppeld": unmatched,
        "tijd_mediaan_abs_min": statistics.median(dts) if dts else None,
        "tijd_gemiddeld_min": round(statistics.mean(signed), 1) if signed else None,
        "tijd_binnen_3_min_pct": pct(dts, 3),
        "tijd_binnen_10_min_pct": pct(dts, 10),
        "hoogte_gemiddeld_m_zh200": round(statistics.mean(dhs), 3) if dhs else None,
        "hoogte_binnen_10cm_pct_zh200": pct(dhs, 0.1),
        "nivel_medio_tabel": port.nivel_medio,
        "hoogte_gemiddeld_m_nm": round(statistics.mean(dhs_nm), 3) if dhs_nm else None,
        "hoogte_binnen_10cm_pct_nm": pct(dhs_nm, 0.1),
    }
    res["haalt_norm"] = bool(
        dts and pct(dts, 3) >= 50 and pct(dts, 10) >= 95 and (res["hoogte_binnen_10cm_pct_nm"] or 0) >= 95
    )
    return res


def main():
    ports = table.load()
    stations = interp.load_stations()
    results = []
    for name in table.PORTS:
        p = ports.get(name)
        if p is None or not p.events or p.lat is None:
            results.append({"haven": name, "fout": "niet gevonden in de tabel"})
            continue
        results.append(compare(p, stations))
    out = {"gemaakt": datetime.now(UTC).strftime("%Y-%m-%dT%H:%MZ"), "jaar": table.YEAR, "havens": results}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    for r in results:
        print(json.dumps(r, ensure_ascii=False))


if __name__ == "__main__":
    main()
