"""Controle na elke kaartrun: tonen de beelden dezelfde golven als Copernicus zelf?

Leest op vaste punten op open zee de ruwe waarden van Copernicus (de 3 x 3 cellen van 1/12 graad die samen één
kaartcel van 0,25 graad vormen) en de waarde die de browser uit de fijne kaarttegel terugleest (zelfde
decodering als web/src/field.ts). De kaartwaarde moet binnen het bereik van die 3 x 3 cellen liggen, met een
marge voor de codering in 8 bit. Het verschil met de dichtstbijzijnde cel staat ter info in het verslag.
Schrijft controle_golven.json naast de kaartdata en stopt met een fout als een waarde buiten het bereik valt.

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
# Marge bovenop het bereik van de 3 x 3 cellen: afronding van de codering in 8 bit.
MARGE = {"hoogte_m": lambda ref: 0.05 + 0.03 * ref, "periode_s": lambda ref: 0.3, "richting_graden": lambda ref: 3.0}


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
    """Dichtstbijzijnde cel en het bereik (min, max) over de 3 x 3 cellen eromheen."""
    tt = np.datetime64(t.replace(tzinfo=None), "ns")
    lo = ((lon + 180) % 360) - 180
    uit = {}
    for naam, v in zip(("hoogte_m", "richting_graden", "periode_s"), golven.SYSTEMEN[systeem]):
        da = bron.ds[v].sel(time=tt)
        j = int(np.abs(da["latitude"].values - lat).argmin())
        i = int(np.abs(da["longitude"].values - lo).argmin())
        blok = np.asarray(da.isel(latitude=slice(j - 1, j + 2), longitude=slice(i - 1, i + 2)).values, dtype=float)
        if naam == "periode_s":
            blok = blok / golven.TM01_GEDEELD_DOOR_TP
        uit[naam] = float(blok[1, 1])
        uit[naam + "_bereik"] = blok.ravel().tolist()
    return uit


def binnen_bereik(waarde: float, cellen: list[float], naam: str, marge: float) -> bool:
    c = np.array([x for x in cellen if np.isfinite(x)])
    if not len(c):
        return False
    if naam == "richting_graden":
        # Afwijking van de waarde tegenover elke cel; binnen bereik als ze tussen de uiterste afwijkingen ligt.
        d = (c - waarde + 180) % 360 - 180
        return d.min() - marge <= 0 <= d.max() + marge
    return c.min() - marge <= waarde <= c.max() + marge


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
                for v, marge in MARGE.items():
                    if r["hoogte_m"] < 0.2 and v != "hoogte_m":
                        continue  # nauwelijks deining: richting en periode zeggen weinig
                    if not binnen_bereik(k[v], r[v + "_bereik"], v, marge(r[v])):
                        fouten.append(f"{naam} +{uur} u {v}: kaart {k[v]:.2f}, Copernicus {r[v]:.2f}, "
                                      f"3 x 3 cellen {[round(x, 2) for x in r[v + '_bereik']]}")
                rij["status"] = "ok"
            rijen.append(rij)
    uit = {"run": m["run"], "systeem": "deining", "regel": "kaartwaarde binnen het bereik van de 3 x 3 Copernicus-cellen, marge 0,05 m + 3 %, 0,3 s, 3 graden",
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
