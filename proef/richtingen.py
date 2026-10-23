"""Controle: wijzen de animatie (kaartbeelden) en het kompas (spotdetails) dezelfde kant op?

Leest een gebouwde site (map met data/manifest.json, de beelden en data/spots) en vergelijkt per spot en per tijdstip
overdag de wind en de deining zoals de browser ze bemonstert (bilineair, regio rond Portugal eerst) met de waarden in
het kompas. Deining wordt alleen vergeleken waar ze er toe doet (kompas minstens 0,3 m).

Gebruik: python proef/richtingen.py <site-map>
"""

import glob
import json
import math
import sys
from datetime import datetime, timezone

import numpy as np
from PIL import Image

NAMEN = ["Praia da Rocha", "Meia Praia", "Arrifana", "Praia do Castelejo", "Supertubos", "Ribeira d'Ilhas", "Carcavelos",
         "Nazaré Praia do Norte", "Matosinhos", "Costa da Caparica São João", "Praia da Falésia Açoteias", "Praia do Amado",
         "Praia de Monte Gordo", "Praia de Odeceixe-Mar", "Praia de Espinho", "Guincho"]


def main(site):
    data = f"{site}/data"
    m = json.load(open(f"{data}/manifest.json"))
    idx = json.load(open(f"{data}/spots/index.json"))
    det = {}
    for f in glob.glob(f"{data}/spots/d*.json"):
        det.update(json.load(open(f)))
    cache = {}

    def beeld(pad):
        if pad not in cache:
            cache[pad] = np.asarray(Image.open(pad).convert("RGB")).astype(float)
        return cache[pad]

    def bilin(a, fy, fx):
        y0, x0 = int(fy), int(fx)
        ty, tx = fy - y0, fx - x0
        return (a[y0, x0] * (1 - tx) * (1 - ty) + a[y0, x0 + 1] * tx * (1 - ty) + a[y0 + 1, x0] * (1 - tx) * ty
                + a[y0 + 1, x0 + 1] * tx * ty)

    def tegel(t, soort, lat, lon):
        f = m["fine"]
        j, i = (90 - lat) / f["deg"], (lon % 360) / f["deg"]
        r, c = int(j // (f["tilePx"] - 1)), int(i // (f["tilePx"] - 1))
        a = beeld(f"{data}/{t['h']:03d}/{soort}/{r}_{c}.webp")
        return bilin(a, j - r * (f["tilePx"] - 1), i - c * (f["tilePx"] - 1))

    def golf(t, lat, lon):
        g = m.get("regio")
        if g and t.get("wavesRegio"):
            fy, fx = (g["lat0"] - lat) / g["deg"], (lon - g["lon0"]) / g["deg"]
            if 0 <= fy < g["h"] - 1 and 0 <= fx < g["w"] - 1:
                return bilin(beeld(f"{data}/{t['h']:03d}/swell-regio.webp"), fy, fx), "IBI"
        return tegel(t, "swell", lat, lon), "0,25°"

    hk = lambda a, b: abs((a - b + 180) % 360 - 180)
    dw, dg = [], []
    for t in m["times"]:
        tijd = datetime.fromisoformat(t["time"].replace("Z", "+00:00"))
        if not (t["fine"] and t["waves"] and tijd.hour in (12,) and len(dw) < 400):
            continue
        print(f"--- {t['time']}")
        for n in NAMEN:
            s = next((x for x in idx["spots"] if x["naam"] == n), None)
            if not s:
                continue
            d = det[str(s["id"])]
            i = round((tijd.timestamp() - datetime.fromisoformat(d["start"].replace("Z", "+00:00")).timestamp()) / 3600)
            if not (0 <= i < d["uren"]) or not d["wind"][i]:
                continue
            w, sw = d["wind"][i], d["deining"][i]
            rgb = tegel(t, "wind", s["lat"], s["lon"])
            comp = lambda b: math.copysign((b / 127.5 - 1) ** 2, b / 127.5 - 1) * m["encoding"]["windMax"]
            u, v = comp(rgb[0]), comp(rgb[1])
            vd = math.degrees(math.atan2(-u, -v)) % 360
            rij = f"{n[:24]:24} wind {w[3]:3.0f}°/{vd:3.0f}°"
            if w[0] >= 5:
                dw.append(hk(vd, w[3]))
            g, bron = golf(t, s["lat"], s["lon"])
            if g[2] > 0 and sw:
                sv = (math.degrees(math.atan2(g[0] / 127.5 - 1, g[1] / 127.5 - 1)) + 180) % 360
                hs = m["encoding"]["waveHMax"] * ((g[2] - 1) / 254) ** 2
                rij += f" | deining kompas {sw[1]:3.0f}° {sw[0]:.1f} m, animatie ({bron}) {sv:3.0f}° {hs:.1f} m"
                if sw[0] >= 0.3:
                    dg.append(hk(sv, sw[1]))
            print(rij)
    print(f"\nwind (≥ 5 kn): mediaan {np.median(dw):.0f}°, 90% onder {np.percentile(dw, 90):.0f}°  ({len(dw)} metingen)")
    print(f"deining (≥ 0,3 m): mediaan {np.median(dg):.0f}°, 90% onder {np.percentile(dg, 90):.0f}°, max {max(dg):.0f}°  ({len(dg)} metingen)")


if __name__ == "__main__":
    main(sys.argv[1])
