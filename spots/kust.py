"""Strandrichting en swellvenster per spot uit de fijne kustlijn GSHHG (volle resolutie, orde 100 m).

GSHHG (Wessel & Smith, LGPL) komt uit het pakket basemap-data-hires: gshhs_f.dat met de punten (lengte, breedte
als float32) en gshhsmeta_f.dat met per veelhoek het niveau (1 land, 2 meer, 3 eiland in een meer, 5 Antarctica),
de begin- en eindbyte. Zie pipeline/README of spots/README voor het ophalen.

Per spot:
  kustpunt      het dichtste punt op de kustlijn
  richting      richting waarin het strand naar zee kijkt (graden, 270 = west): loodrecht op de kustlijn binnen
                500 m, 1 km en 2 km van het kustpunt (hoofdas van de kustpunten), aan de kant waar water is. De
                regels (overdracht plankscore) meten de kustlijn over ongeveer 1 km: dat is de strandrichting.
  open_km       per 5 graden: afstand tot het eerste land vanaf een punt net voor de kust, tot 300 km
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import nearest_points

STRAAL_MAX_KM = 300.0
STAP_GRADEN = 5
DEEL = 200  # punten per stuk kustlijn in de zoekboom


def km_per_graad(lat: float) -> tuple[float, float]:
    return 111.32 * math.cos(math.radians(lat)), 110.57


def verplaats(lon: float, lat: float, richting: float, km: float) -> tuple[float, float]:
    kx, ky = km_per_graad(lat)
    return lon + math.sin(math.radians(richting)) * km / kx, lat + math.cos(math.radians(richting)) * km / ky


@dataclass
class Resultaat:
    kust_km: float
    kustpunt: tuple[float, float]
    richting_500m: float | None
    richting_1km: float | None
    richting_2km: float | None
    startpunt: tuple[float, float] | None
    open_km: list[float] | None


class Kust:
    def __init__(self, map_: Path):
        meta = [r.split() for r in (map_ / "gshhsmeta_f.dat").read_text().splitlines() if r.strip()]
        raw = np.fromfile(map_ / "gshhs_f.dat", dtype="<f4")
        polys, niveaus, delen = [], [], []
        for m in meta:
            niveau, start, n = int(m[0]), int(m[5]), int(m[6])
            a = raw[start // 4:(start + n) // 4].reshape(-1, 2).astype(np.float64)
            if len(a) < 4:
                continue
            polys.append(Polygon(a))
            niveaus.append(1 if niveau == 5 else niveau)
            for i in range(0, len(a) - 1, DEEL):
                stuk = a[i:i + DEEL + 1]
                if len(stuk) >= 2:
                    delen.append(LineString(stuk))
        self.polys = np.array(polys, dtype=object)
        self.niveaus = np.array(niveaus)
        shapely.prepare(self.polys)
        self.poly_boom = shapely.STRtree(self.polys)
        self.delen = np.array(delen, dtype=object)
        self.lijn_boom = shapely.STRtree(self.delen)

    def is_land(self, lon: float, lat: float) -> bool:
        """Land als het diepste niveau dat het punt bevat oneven is (land of eiland in een meer)."""
        p = Point(lon, lat)
        kand = self.poly_boom.query(p, predicate="intersects")
        if not len(kand):
            return False
        return int(self.niveaus[kand].max()) % 2 == 1

    def kustlijn_bij(self, lon: float, lat: float, km: float) -> list[np.ndarray]:
        kx, ky = km_per_graad(lat)
        doos = shapely.box(lon - km / kx, lat - km / ky, lon + km / kx, lat + km / ky)
        uit = []
        for i in self.lijn_boom.query(doos):
            g = shapely.intersection(self.delen[i], doos)
            for d in getattr(g, "geoms", [g]):
                if not d.is_empty and d.geom_type == "LineString":
                    uit.append(np.asarray(d.coords))
        return uit

    def dichtste_kustpunt(self, lon: float, lat: float, km: float = 5.0):
        stukken = self.kustlijn_bij(lon, lat, km)
        if not stukken:
            return None, None
        kx, ky = km_per_graad(lat)
        beste, best_d = None, 1e9
        p = Point(lon, lat)
        for s in stukken:
            q = nearest_points(p, LineString(s))[1] if len(s) >= 2 else Point(s[0])
            d = math.hypot((q.x - lon) * kx, (q.y - lat) * ky)
            if d < best_d:
                beste, best_d = (q.x, q.y), d
        return beste, best_d

    def richting(self, q: tuple[float, float], straal_km: float) -> float | None:
        """Loodrecht op de hoofdas van de kustpunten binnen de straal, naar de kant met water."""
        kx, ky = km_per_graad(q[1])
        pts = []
        for s in self.kustlijn_bij(q[0], q[1], straal_km):
            for x, y in s:
                dx, dy = (x - q[0]) * kx, (y - q[1]) * ky
                if dx * dx + dy * dy <= straal_km * straal_km:
                    pts.append((dx, dy))
        if len(pts) < 3:
            return None
        a = np.array(pts)
        a -= a.mean(axis=0)
        sxx, syy, sxy = (a[:, 0] ** 2).sum(), (a[:, 1] ** 2).sum(), (a[:, 0] * a[:, 1]).sum()
        hoek = 0.5 * math.atan2(2 * sxy, sxx - syy)  # hoofdas t.o.v. oost
        langs = (90 - math.degrees(hoek)) % 180
        kandidaten = []
        for n in ((langs + 90) % 360, (langs - 90) % 360):
            nat = sum(not self.is_land(*verplaats(q[0], q[1], n, d)) for d in (0.2, 0.4, 0.7, 1.0))
            kandidaten.append((nat, n))
        kandidaten.sort(reverse=True)
        if kandidaten[0][0] == 0 or kandidaten[0][0] == kandidaten[1][0]:
            return None  # geen of aan beide kanten evenveel water: geen duidelijke kust
        return round(kandidaten[0][1]) % 360

    def straal(self, lon: float, lat: float, richting: float, max_km: float = STRAAL_MAX_KM) -> float:
        ex, ey = verplaats(lon, lat, richting, max_km)
        lijn = LineString([(lon, lat), (ex, ey)])
        kx, ky = km_per_graad(lat)
        best = max_km
        for i in self.lijn_boom.query(lijn):
            g = shapely.intersection(self.delen[i], lijn)
            if g.is_empty:
                continue
            for x, y in shapely.get_coordinates(g):
                best = min(best, math.hypot((x - lon) * kx, (y - lat) * ky))
        return round(best, 1)

    def analyse(self, lon: float, lat: float) -> Resultaat | None:
        q, d = self.dichtste_kustpunt(lon, lat)
        if q is None:
            return None
        r500, r1k, r2k = self.richting(q, 0.5), self.richting(q, 1.0), self.richting(q, 2.0)
        f = r1k if r1k is not None else (r2k if r2k is not None else r500)
        start = None
        if f is not None:
            for afst in (0.15, 0.3, 0.5, 0.8, 1.2, 2.0, 3.0):
                x, y = verplaats(q[0], q[1], f, afst)
                if not self.is_land(x, y) and self.straal(x, y, f, 5) > 1:
                    start = (x, y)
                    break
        open_km = None
        if start is not None:
            open_km = [self.straal(start[0], start[1], b) for b in range(0, 360, STAP_GRADEN)]
        return Resultaat(round(d, 3), (round(q[0], 5), round(q[1], 5)), r500, r1k, r2k,
                         None if start is None else (round(start[0], 5), round(start[1], 5)), open_km)
