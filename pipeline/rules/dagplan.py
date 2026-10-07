"""Dagplan: per strand en per uur wat je kan doen, uit WIND, WAVE, getij en daglicht.

Vier activiteiten (de sportkeuze op de kaart):
- surf      Surfweer:     WAVE 3 of 4 en WIND 1 of 2 (eigenaar). Getij: beste tussen 35 en 75% van
                          laag naar hoog water, mogelijk tussen 15 en 90%; rond het laagste water sluiten
                          de golven, rond het hoogste breken ze op de kant (breakfinder.surf, surfertoday.com).
- wind      Windweer:     WIND 3 of 4 en WAVE 1 of 2: kiten en windsurfen.
- windgolf  Wind-golven:  WIND 3 of 4 en WAVE 3 of 4: windsurfen en kiten op golven.
                          Voor beide wind-activiteiten: rond het hoogste water (boven 90%) minder strand
                          en meer shorebreak, dus "mogelijk" in plaats van "goed" (rideevolve.eu, windsurf.co.uk).
- plat      Stille waters: WAVE 1 of 2, wind tot 10 kn (stil.sup_goed_tot_kn) en geen aflandige wind
                          vanaf 5 kn (die drijft je van de kant). Getij: beste rond hoog- en laagwater
                          (onder 25% of boven 75%), want midden tussen eb en vloed stroomt het het sterkst
                          (nrc.govt.nz, Paddleboarding safety guidelines).

Per uur een cijfer: 0 niet, 1 mogelijk, 2 goed. Alleen bij daglicht. WIND 5 of WAVE 5: overal 0.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime

from pipeline.rules.score import rules

ACTIVITEITEN = {"surf": "Surfweer", "wind": "Windweer", "windgolf": "Wind-golven", "plat": "Stille waters"}
AFLANDIG = ("schuin_af", "af")
PLAT_AFLANDIG_VANAF_KN = 5


def getij_fractie(extremen: list[list], t_min: float) -> float | None:
    """Waterpeil tussen laag (0) en hoog (1) water, met de halve cosinus tussen twee extremen."""
    for e0, e1 in zip(extremen, extremen[1:], strict=False):
        if e0[0] <= t_min < e1[0]:
            f = (t_min - e0[0]) / (e1[0] - e0[0])
            x = (1 - math.cos(math.pi * f)) / 2
            return x if e1[2] else 1 - x  # naar hoog water: stijgt
    return None


def zon(lat: float, lon: float, dag: datetime) -> tuple[float, float] | None:
    """Zonsopgang en -ondergang in minuten sinds 1970 UTC (NOAA, vereenvoudigd; zelfde als web/src/getij.ts)."""
    rad = math.pi / 180
    n = dag.timetuple().tm_yday
    g = (2 * math.pi / 365) * (n - 1)
    eq = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g) - 0.014615 * math.cos(2 * g)
                   - 0.040849 * math.sin(2 * g))
    decl = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g) - 0.006758 * math.cos(2 * g)
            + 0.000907 * math.sin(2 * g))
    cos_h = (math.cos(90.833 * rad) - math.sin(lat * rad) * math.sin(decl)) / (math.cos(lat * rad) * math.cos(decl))
    if abs(cos_h) > 1:
        return None
    h = math.acos(cos_h) / rad
    base = datetime(dag.year, dag.month, dag.day, tzinfo=UTC).timestamp() / 60
    mid = 720 - 4 * lon - eq
    return base + mid - 4 * h, base + mid + 4 * h


def daglicht(lat: float, lon: float, t_min: float) -> bool:
    """Het uur [t, t+60) ligt grotendeels bij daglicht."""
    z = zon(lat, lon, datetime.fromtimestamp(t_min * 60, UTC))
    return z is not None and z[0] - 30 <= t_min <= z[1] - 30


def uur(wind: int, wave: int, wind_kn: float, windklasse: str | None, p: float | None, licht: bool) -> dict[str, int]:
    """Per activiteit 0 niet, 1 mogelijk, 2 goed, voor één uur."""
    uit = dict.fromkeys(ACTIVITEITEN, 0)
    if not licht or wind == 5 or wave == 5:
        return uit
    if wave in (3, 4) and wind in (1, 2):
        uit["surf"] = 1 if p is None else 2 if 0.35 <= p <= 0.75 else 1 if 0.15 <= p <= 0.90 else 0
    if wind in (3, 4):
        k = "windgolf" if wave in (3, 4) else "wind"
        uit[k] = 1 if p is not None and p > 0.90 else 2
    aflandig = windklasse in AFLANDIG and wind_kn >= PLAT_AFLANDIG_VANAF_KN
    if wave in (1, 2) and wind_kn <= rules()["stil"]["sup_goed_tot_kn"] and not aflandig:
        uit["plat"] = 1 if p is None else 2 if p <= 0.25 or p >= 0.75 else 1
    return uit
