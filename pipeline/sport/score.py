"""Sportscore 1 tot 5 per sport, voor één strand en één uur.

Volgt het document van de eigenaar "Sportscore 1 tot 5: rekenregels per sport" stap voor stap
(STAP 0 tot 4, de groepen A tot D, droogvallen en de redenen). De grenzen staan in sporten.yaml.
Een pure functie: geen netwerk, geen bestanden behalve sporten.yaml.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import yaml

SPORTEN_FILE = Path(__file__).with_name("sporten.yaml")
TIJ = ("laag", "opkomend", "hoog", "afgaand")


@cache
def sporten(path: Path = SPORTEN_FILE) -> dict:
    return yaml.safe_load(path.read_text())


@dataclass
class Invoer:
    N: float | None                        # kijkrichting van het strand
    H: float | None                        # golfhoogte (m)
    T: float | None                        # piekperiode (s)
    GR: float | None                       # golfrichting, waar de golven vandaan komen
    V: float | None                        # gemiddelde wind (kn)
    G: float | None                        # windstoot (kn)
    WR: float | None                       # windrichting, waar de wind vandaan komt
    TIJ: str | None = None                 # laag, opkomend, hoog of afgaand
    K: float | None = 1.0                  # strandfactor
    BESTTIJ: str | None = None             # laag of hoog
    DROOG: bool = False
    LUWTE: tuple[float, float] | None = None


@dataclass
class Uitkomst:
    cijfers: dict[str, int]                # sport -> 1..5
    redenen: dict[str, int]                # sport -> 0 (geen of niets verschoven) of 1..9
    GOLF: float
    RUW: float
    W: float
    a: float


def verschil(x: float, n: float) -> float:
    d = abs((x - n) % 360)
    return min(d, 360 - d)


def trap(x: float, g1: float, g2: float) -> int:
    return 2 if x >= g2 else 1 if x >= g1 else 0


def omhoog(c: int, u: int) -> int:
    if u == 2 and c >= 2:
        return 5
    if u == 1 and c == 3:
        return 4
    return c


def omlaag(c: int, d: int) -> int:
    if c <= 3:
        return max(1, c - 1) if d == 1 else 1 if d == 2 else c
    if c == 4:
        return 5 if d == 2 else 4
    return c


def schuif(a: float, zee: float, opzij: float, land: float) -> float:
    if a <= 45:
        return zee
    if a <= 90:
        return zee + (opzij - zee) * (a - 45) / 45
    if a < 135:
        return opzij + (land - opzij) * (a - 90) / 45
    return land


def vlaag(V: float, G: float) -> int:
    if G >= 2 * V and G >= 25:
        return 2
    if G - V >= 10 and G >= 1.5 * V:
        return 1
    return 0


def wind_basis(V: float, W: float, w: list[float]) -> int:
    w1, w2, w3, w4 = w
    if W >= w4:
        return 5
    if W >= w3:
        return 4
    if V >= w2:
        return 3
    if V >= w1:
        return 2
    return 1


def _getal(x) -> float | None:
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def bereken(inv: Invoer) -> Uitkomst | None:
    """Alle sporten voor één uur; None als het document zegt: toon geen cijfer."""
    cfg = sporten()
    # STAP 0
    K = _getal(inv.K)
    K = 1.0 if K is None else min(1.5, max(0.0, K))
    N, H, T, GR, V, G, WR = (_getal(x) for x in (inv.N, inv.H, inv.T, inv.GR, inv.V, inv.G, inv.WR))
    if K == 0:
        H, T = 0.0, 10.0
    if None in (H, T, V, WR, N) or H < 0 or V < 0 or T <= 0:
        return None
    if G is None or G < V:
        G = V
    N %= 360
    WR %= 360
    if GR is not None:
        GR %= 360
    # STAP 1
    if inv.LUWTE is not None:
        lv, lt = inv.LUWTE[0] % 360, inv.LUWTE[1] % 360
        if (lv <= WR <= lt) if lv <= lt else (WR >= lv or WR <= lt):
            V, G = V * 0.5, G * 0.5
    # STAP 2
    theta = verschil(GR, N) if GR is not None else 0.0
    a = verschil(WR, N)
    # STAP 3
    Tr = min(T, 20)
    golf0 = 0.33 * H ** 0.8 * Tr ** 0.4 * max(1, Tr / 10) ** 0.85
    if theta <= 80:
        R = math.cos(math.radians(theta)) ** 0.4
    elif theta < 135:
        R = 0.496 * (135 - theta) / 55
    else:
        R = 0.0
    GOLF = K * R * golf0
    RUW = K * max(R, 0.1) * max(golf0, H)
    # STAP 4
    W = max(V, G / 1.3)

    tij = inv.TIJ
    vl = vlaag(V, G)
    cijfers: dict[str, int] = {}
    redenen: dict[str, int] = {}
    for s, c in cfg["sporten"].items():
        r: set[int] = set()
        grp = c["groep"]
        if grp == "A":
            g1, g2, g3, g4 = c["golf"]
            b = 1 if GOLF < g1 else 2 if GOLF < g2 else 3 if GOLF < g3 else 4 if GOLF < g4 else 5
            basis = b
            if c["periode"] and b == 3 and T < 6:
                b = 2
                r.add(8)
            P = trap(W, schuif(a, *c["wind1"]), schuif(a, *c["wind2"]))
            ts = 1 if (inv.BESTTIJ == "laag" and tij == "hoog") or (inv.BESTTIJ == "hoog" and tij == "laag") else 0
            straf = "omhoog" if c["straf"] == "omlaag" and a > 112.5 else c["straf"]
            if straf == "omhoog":
                cijfer = omlaag(omhoog(b, P), ts)
            else:
                cijfer = omlaag(b, min(2, P + ts))
            if P > 0 and a > 112.5:
                r.add(3)
            if P > 0 and s in ("leren", "supsurf"):
                r.add(6)
            if P > 0 and straf == "omlaag":
                r.add(7)
            if ts:
                r.add(9)
        elif grp == "B":
            b = basis = wind_basis(V, W, c["wind"])
            ruw = trap(RUW, *c["ruw"]) if c["ruw"] else 0
            if c["richting"] == "kite":
                ri = 0 if a <= 90 else 1 if a <= 112.5 else 2
            elif c["richting"] == "zeil":
                ri = 1 if a > 112.5 and W >= 10 else 0
            else:
                ri = 1 if a > 112.5 else 0
            if K == 0 and c["richting"] != "land":
                ri = 0
            cijfer = omhoog(b, max(ruw, ri, vl))
            if c["richting"] == "land" and tij == "hoog":
                cijfer = 1
                r.add(2)
            if ri:
                r.add(3)
            if vl:
                r.add(4)
            if ruw:
                r.add(5)
        elif grp == "C":
            wc = wind_basis(V, W, c["wind"])
            gc = 5 if RUW >= 3.0 else 4 if RUW >= 2.0 else 3 if GOLF >= 0.8 else 2 if GOLF >= 0.5 else 1
            if wc == 1:
                b = 1
            elif wc == 5 or gc == 5:
                b = 5
            elif gc == 1:
                b = 1
            elif wc == 2:
                b = 5 if gc == 4 else 2
            elif wc == 4 or gc == 4:
                b = 4
            else:
                b = min(wc, gc)
            basis = b
            ri = 0 if a <= 112.5 else 1 if a <= 157.5 else 2
            if c["zeekant"] and a < 22.5:
                ri = max(ri, 1)
            cijfer = omhoog(b, max(ri, vl))
            if ri:
                r.add(3)
            if vl:
                r.add(4)
        else:  # D
            ruw = trap(RUW, *c["ruw"])
            gewoon = trap(W, *c["wind"])
            wt = trap(W, *c["land"]) if a > 112.5 and K > 0 else gewoon
            basis = 3
            cijfer = 3 + max(ruw, wt)
            if cijfer > 3 + max(ruw, gewoon):
                r.add(3)
            if ruw:
                r.add(5)
            if wt:
                r.add(6)
        if inv.DROOG and tij == "laag" and s != "landkite":
            cijfer = 1
            r.add(1)
        cijfers[s] = cijfer
        # Een reden alleen als een regel het cijfer heeft verschoven (deel 1 van het document):
        # bij een kitesurf-1 door te weinig wind hoort geen "ongunstige windrichting".
        redenen[s] = min(r) if r and cijfer != basis else 0
    return Uitkomst(cijfers, redenen, GOLF, RUW, W, a)


def tij_op(extremen: list[list], t_min: float) -> str | None:
    """TIJ voor een tijdstip (minuten sinds 1970 UTC) uit hoog- en laagwaters [[minuten, cm, hoog], ...].

    Laag of hoog: hoogstens 1 uur van dat extreem. Daartussen opkomend of afgaand.
    """
    if not extremen or t_min < extremen[0][0] - 60 or t_min > extremen[-1][0] + 60:
        return None
    dichtst = min(extremen, key=lambda e: abs(e[0] - t_min))
    if abs(dichtst[0] - t_min) <= 60:
        return "hoog" if dichtst[2] else "laag"
    volgend = next((e for e in extremen if e[0] > t_min), None)
    if volgend is None:
        return None
    return "opkomend" if volgend[2] else "afgaand"


# Strandfactor K uit de blootstelling van het strand (M1): de grootste factor f over alle
# richtingen, omgezet naar de klassen van het document (1 open, 0,6 half beschut, 0,3 beschut,
# 0,1 sterk beschut, 0 lagune). Een open strand haalt f 0,8 tot 0,9.
K_KLASSEN = [(0.8, 1.0), (0.6, 0.6), (0.35, 0.3), (0.1, 0.1)]


def strandfactor(blootstelling: list[float], redenen: list[str]) -> tuple[float, str]:
    """K en waar die vandaan komt."""
    f = max(blootstelling) if blootstelling else 0.0
    if f < 0.1 and any("ligt op land" in r for r in redenen):
        # De blootstelling is hier niet te vertrouwen: het punt voor de kust viel op land.
        return 1.0, "standaard: ligging van het strand onzeker"
    for grens, k in K_KLASSEN:
        if f >= grens:
            return k, f"uit de blootstelling ({f:.2f})"
    return 0.0, f"uit de blootstelling ({f:.2f})"
