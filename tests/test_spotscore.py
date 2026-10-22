import datetime as dt
import json
import math
from pathlib import Path

from pipeline import spotscore as S


def _iso(t):
    return t.strftime("%Y-%m-%dT%H:%MZ")


def test_zonhoogte_middag_en_nacht():
    # Lissabon, 21 juni: middag hoog, middernacht onder de horizon
    assert S.zonhoogte(dt.datetime(2026, 6, 21, 12, 30, tzinfo=dt.UTC), 38.7, -9.1) > 65
    assert S.zonhoogte(dt.datetime(2026, 6, 21, 0, 30, tzinfo=dt.UTC), 38.7, -9.1) < -6


def test_helling_uit_profiel():
    # waterlijn op 50 m, 2 m diep op 150 m: helling 0,02
    assert S.helling_uit_profiel([-1, -0.5, 0, 0.5, 1.0, 1.5, 2.0, 3.0]) == 0.02


def test_reken_spot_supertubos_kunstmatig():
    spots = json.loads(Path("spots/spots.json").read_text())["spots"]
    spot = next(s for s in spots if s["naam"] == "Supertubos")
    t0 = dt.datetime(2026, 10, 24, 0, tzinfo=dt.UTC)
    uren = [t0 + dt.timedelta(hours=h) for h in range(0, 25)]
    # deining 1,5 m 12 s uit het westzuidwesten, lichte oostenwind (offshore), getij 3 m met periode 12u25
    golven = {"bron": "test", "cel": [39.34, -9.37], "tijden": [_iso(t) for t in uren],
              "deining1": [[1.5, 255, 12.0]] * 25, "deining2": [None] * 25, "windzee": [[0.2, 90, 3.0]] * 25}
    wind = {"tijden": [_iso(t) for t in uren[::3]], "u": [-2.0] * 9, "v": [0.0] * 9, "stoot": [3.0] * 9}
    n = 25 * 6 + 1
    h = [1.5 * math.cos(2 * math.pi * k * 600 / 44700) for k in range(n)]
    ext = []
    for k in range(1, n - 1):
        if (h[k] > h[k - 1] and h[k] >= h[k + 1]) or (h[k] < h[k - 1] and h[k] <= h[k + 1]):
            ext.append([_iso(t0 + dt.timedelta(minutes=10 * k)), "hoog" if h[k] > 0 else "laag", h[k]])
    ext.insert(0, [_iso(t0), "hoog", 1.5])
    getij = {"start": _iso(t0), "stap_min": 10, "h": h, "uitersten": ext}
    r = S.reken_spot(spot, {"golven": golven, "wind": wind, "getij": getij}, S.bodem_index(), t0, t0 + dt.timedelta(hours=23))
    assert r is not None
    assert len(r["scores"]["SB"]) == 93
    # 's nachts donker: score 1
    assert r["scores"]["SB"][0] == 1.0
    # overdag met deze golf een duidelijke score voor de shortboard
    middag = r["scores"]["SB"][4 * 13]
    assert middag > 2.0, r["uur"][13]
