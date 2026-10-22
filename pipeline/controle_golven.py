"""Controle na elke kaartrun: tonen de beelden dezelfde golven als Copernicus zelf?

Leest op vaste punten op open zee de ruwe waarde van Copernicus (dichtstbijzijnde cel van 1/12 graad) en de
waarde die de browser uit de fijne kaarttegel terugleest (zelfde decodering als web/src/field.ts). Verschillen
komen van het 3 x 3-gemiddelde naar 0,25 graad en van de codering in 8 bit. Schrijft controle_golven.json naast
de kaartdata en stopt met een fout als een verschil boven de grens ligt.

Gebruik: python -m pipeline.controle_golven --data web/public/data
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from pipeline import golven
from pipeline.build import H_MAX, T_MAX, TILE_DEG

# Open zee in alle oceanen; weinig verloop over 25 km, zodat het gemiddelde naar 0,25 graad weinig uitmaakt.
PUNTEN = {
    "Golf van Biskaje": (45.0, -8.0), "Noord-Atlantisch": (50.0, -30.0), "Midden-Atlantisch": (30.0, -40.0),
    "Zuid-Atlantisch": (-35.0, -20.0), "Indische Oceaan": (-30.0, 80.0), "Grote Oceaan noord": (35.0, -150.0),
    "Grote Oceaan zuid": (-40.0, -120.0), "Tasmanzee": (-38.0, 160.0),
}
UREN = (0, 24, 96)
GRENS = {"hoogte_m": lambda ref: 0.15 + 0.05 * ref, "periode_s": lambda ref: 0.6, "richting_graden": lambda ref: 10.0}


def lees_tegel(data: Path, uur: int, systeem: str, lat: float, lon: float):
    """Waarde van de kaarttegel op dit punt, zoals de browser ze decodeert (dichtstbijzijnde pixel)."""
    l = lon % 360
    c, r = int(l // TILE_DEG), int((90 - lat) // TILE_DEG)
    pad = data / f"{uur:03d}" / systeem / f"{r}_{c}.webp"
    if not pad.exists():
        return None
    px = np.asarray(Image.open(pad).convert("RGB"), dtype=float)
    j, i = round((90 - r * TILE_DEG - lat) * 4), round((l - c * TILE_DEG) * 4)
    rr, gg, bb = px[j, i]
    if bb == 0:
        return {"land": True}
    x, y = rr / 127.5 - 1, gg / 127.5 - 1
    lengte = float(np.hypot(x, y))
    naar = float(np.degrees(np.arctan2(x, y)) % 360)
    return {"hoogte_m": ((bb - 1) / 254) ** 2 * H_MAX, "periode_s": max(0.0, (lengte - 0.3) / 0.7 * T_MAX),
            "richting_graden": (naar + 180) % 360}


def ruw(bron: golven.Bron, t: dt.datetime, systeem: str, lat: float, lon: float) -> dict:
    tt = np.datetime64(t.replace(tzinfo=None), "ns")
    h, d, tm = (float(bron.ds[v].sel(time=tt, latitude=lat, longitude=((lon + 180) % 360) - 180, method="nearest"))
                for v in golven.SYSTEMEN[systeem])
    return {"hoogte_m": h, "periode_s": tm / golven.TM01_GEDEELD_DOOR_TP, "richting_graden": d}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--data", type=Path, default=Path("web/public/data"))
    a = p.parse_args(argv)
    m = json.loads((a.data / "manifest.json").read_text())
    run = dt.datetime.strptime(m["run"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=dt.UTC)
    bron = golven.Bron()
    rijen, fouten = [], []
    for uur in UREN:
        t = run + dt.timedelta(hours=uur)
        for naam, (lat, lon) in PUNTEN.items():
            r, k = ruw(bron, t, "swell", lat, lon), lees_tegel(a.data, uur, "swell", lat, lon)
            rij = {"uur": uur, "punt": naam, "lat": lat, "lon": lon, "copernicus": r, "kaart": k}
            if k is None or k.get("land") or not np.isfinite(r["hoogte_m"]):
                rij["status"] = "niet vergeleken"
            else:
                for v, grens in GRENS.items():
                    d = k[v] - r[v]
                    if v == "richting_graden":
                        d = (d + 180) % 360 - 180
                    if r["hoogte_m"] < 0.2 and v != "hoogte_m":
                        continue  # nauwelijks deining: richting en periode zeggen weinig
                    if abs(d) > grens(r[v]):
                        fouten.append(f"{naam} +{uur} u {v}: kaart {k[v]:.2f}, Copernicus {r[v]:.2f}")
                rij["status"] = "ok"
            rijen.append(rij)
    uit = {"run": m["run"], "systeem": "deining", "grenzen": "hoogte 0,15 m + 5 %, periode 0,6 s, richting 10 graden",
           "fouten": fouten, "punten": rijen}
    (a.data / "controle_golven.json").write_text(json.dumps(uit, indent=1, ensure_ascii=False))
    vergeleken = sum(r["status"] == "ok" for r in rijen)
    print(f"{vergeleken} punten vergeleken, {len(fouten)} buiten de grens", flush=True)
    for f in fouten:
        print("  ", f)
    if vergeleken < len(rijen) // 2:
        print("Te weinig punten vergeleken")
        return 1
    return 1 if fouten else 0


if __name__ == "__main__":
    sys.exit(main())
