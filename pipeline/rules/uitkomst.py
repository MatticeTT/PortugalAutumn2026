"""Per strand en per uur precies één uitkomst: te wild, golfsurfen, windsurfen op golven, windsurfen
of stille waters. Plus WAVE en WIND als level 1 tot 4.

Regels van de rekenchat van de eigenaar (7 oktober 2026), exact overgenomen; niets eigens toegevoegd.
De testgevallen van die chat staan in tests/test_uitkomst.py.

Invoer per uur (zoals Windguru): gemiddelde wind en vlagen (kn), windrichting, en per deining
(deining 1, deining 2, windgolf) hoogte (m), periode (s) en richting. Per strand: de kustrichting
(kijkrichting naar zee) en het swell-venster (de richtingen waaruit deining het strand kan bereiken).
Getij: tij% (0 = laagwater, 100 = hoogwater) en het verval (m) van die getijslag.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# Uitkomsten, met een letter voor de databestanden.
TE_WILD, GOLFSURF, WINDGOLF, WINDSURF, STIL = "W", "G", "O", "S", "R"
UITKOMSTEN = {
    GOLFSURF: "Golfsurfen", WINDGOLF: "Windsurfen op golven", WINDSURF: "Windsurfen",
    STIL: "Stille waters", TE_WILD: "Te wild",
}
VOLGORDE = [GOLFSURF, WINDGOLF, WINDSURF, STIL]  # bij gelijke strafpunten


def hoek(a: float, b: float) -> float:
    """Hoek tussen twee kompasrichtingen, 0 tot 180."""
    d = abs(a - b) % 360
    return 360 - d if d > 180 else d


def in_venster(richting: float, venster: list[list[float]]) -> bool:
    r = richting % 360
    for van, tot in venster:
        van, tot = van % 360, tot % 360
        if (van <= r <= tot) if van <= tot else (r >= van or r <= tot):
            return True
    return False


@dataclass
class Deining:
    h: float  # m
    t: float  # s
    richting: float  # graden, waar de deining vandaan komt


@dataclass
class Uur:
    wind: float          # kn, gemiddeld
    vlaag: float         # kn
    windrichting: float  # graden, waar de wind vandaan komt
    deiningen: list[Deining]
    tij: float | None = None     # tij%, 0 tot 100
    verval: float | None = None  # m


@dataclass
class Strand:
    kust: float                  # kustrichting: richting waarin het strand naar zee kijkt
    venster: list[list[float]]   # swell-venster: [[van, tot], ...] in graden


@dataclass
class Uitkomst:
    uitkomst: str        # W, G, O, S of R
    strafpunten: int     # van de winnaar (0 bij te wild)
    wave: int            # 1 tot 4
    wind: int            # 1 tot 4
    E: float             # kJ, de grootste deining
    H_strand: float      # m
    punten: dict[str, int | None]  # per sport de strafpunten, None = valt af


def energie(d: Deining, s: Strand) -> float:
    """E = 1,96 × H² × T² × cos θ (kJ); 0 buiten het venster of bij θ ≥ 90."""
    th = hoek(d.richting, s.kust)
    if th >= 90 or not in_venster(d.richting, s.venster):
        return 0.0
    return 1.96 * d.h ** 2 * d.t ** 2 * math.cos(math.radians(th))


def h_strand(deiningen: list[Deining], s: Strand) -> float:
    """√(som van H² × cos θ over de deiningen binnen het venster)."""
    som = 0.0
    for d in deiningen:
        th = hoek(d.richting, s.kust)
        if th < 90 and in_venster(d.richting, s.venster):
            som += d.h ** 2 * math.cos(math.radians(th))
    return math.sqrt(som)


def wave_level(E: float) -> int:
    return 1 if E < 100 else 2 if E < 300 else 3 if E < 1000 else 4


def wind_level(wind: float, vlaag: float) -> int:
    if wind > 25 or vlaag > 35:
        return 4
    return 1 if wind < 5 else 2 if wind < 12 else 3


def bereken(u: Uur, s: Strand) -> Uitkomst:
    # Hulpgetallen
    Es = [(energie(d, s), d) for d in u.deiningen if d.h > 0 and d.t > 0]
    E, groot = max(Es, key=lambda x: x[0], default=(0.0, None))
    T = groot.t if groot is not None and E > 0 else 0.0
    H = h_strand([d for d in u.deiningen if d.h > 0], s)
    phi = hoek(u.windrichting, s.kust)
    recht_aan = phi < 22.5
    zee_of_opzij = phi <= 112.5
    schuin_af = 112.5 < phi <= 157.5
    recht_af = phi > 157.5
    vlagerig = u.vlaag - u.wind > 10
    getij_telt = u.tij is not None and u.verval is not None and u.verval > H / 0.78
    tij_extreem = getij_telt and (u.tij <= 15 or u.tij >= 90)
    w = u.wind

    lvl_wave, lvl_wind = wave_level(E), wind_level(w, u.vlaag)
    # Te wild
    if w > 25 or u.vlaag > 35 or E >= 1000:
        return Uitkomst(TE_WILD, 0, lvl_wave, lvl_wind, E, H, {})

    punten: dict[str, int | None] = {}

    # Ideaal golfsurfen
    if E < 100 or (zee_of_opzij and w >= 15):
        punten[GOLFSURF] = None
    else:
        p = 0
        p += 1 if E < 200 else 0
        p += 1 if T < 9 else 0
        if zee_of_opzij:
            p += 1 if 5 <= w < 15 else 0
        else:
            p += 1 if 15 < w <= 25 else 0
        p += 1 if tij_extreem else 0
        punten[GOLFSURF] = p

    # Windsurfen op golven
    if E < 100 or w < 12 or recht_af:
        punten[WINDGOLF] = None
    else:
        p = 0
        p += 1 if w < 15 else 0
        p += 1 if vlagerig else 0
        p += 1 if recht_aan or schuin_af else 0
        p += 1 if E < 200 else 0
        p += 1 if tij_extreem else 0
        punten[WINDGOLF] = p

    # Ideaal windsurfen
    if w < 5 or E >= 300 or (E >= 100 and w < 12) or recht_af or (schuin_af and w < 12):
        punten[WINDSURF] = None
    else:
        p = 0
        p += 1 if w < 12 else 0
        p += 1 if vlagerig else 0
        p += 1 if schuin_af else 0
        p += 1 if recht_aan and H >= 0.5 else 0
        p += 1 if 100 <= E < 300 else 0
        p += 1 if getij_telt and u.tij >= 90 and H >= 0.5 else 0
        punten[WINDSURF] = p

    # Stille waters
    if w >= 12 or E >= 200:
        punten[STIL] = None
    else:
        p = 0
        p += 1 if 5 <= w < 12 else 0
        p += 1 if vlagerig else 0
        p += 1 if not zee_of_opzij and w >= 5 else 0  # wind van land
        p += 1 if H >= 0.5 else 0
        p += 1 if getij_telt and u.tij <= 15 and H >= 0.5 else 0
        punten[STIL] = p

    kandidaten = [(punten[k], VOLGORDE.index(k), k) for k in VOLGORDE if punten[k] is not None]
    if not kandidaten:
        return Uitkomst(TE_WILD, 0, lvl_wave, lvl_wind, E, H, punten)
    p, _, k = min(kandidaten)
    return Uitkomst(k, p, lvl_wave, lvl_wind, E, H, punten)


def getoond(r: Uitkomst) -> str | None:
    """Wat de app toont: te wild altijd; een andere uitkomst alleen bij 0 of 1 strafpunt (eigenaar)."""
    if r.uitkomst == TE_WILD or r.strafpunten <= 1:
        return r.uitkomst
    return None
