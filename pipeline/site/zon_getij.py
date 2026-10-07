"""Hulp voor de site: waterpeil tussen laag- en hoogwater, en daglicht. Geen rekenregels."""

from __future__ import annotations

import math
from datetime import UTC, datetime


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
