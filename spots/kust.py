"""Kustlijn: strandrichting en swellvenster per spot.

Werkt met de OSM-kustlijn. Afspraak in OSM: het land ligt links van de lijnrichting, de zee rechts.
Zo volgt de zeekant rechtstreeks uit de lijn, zonder land/zee-masker.

Alle meetkunde gebeurt per spot in een eigen vlakke projectie (azimutaal, afstandsgetrouw, in meter),
met het noorden boven: x = oost, y = noord. Richtingen zijn kompasgraden (0 = noord, 90 = oost).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pyproj
import shapely
from shapely import STRtree


def kompas(dx, dy):
    return (np.degrees(np.arctan2(dx, dy)) + 360.0) % 360.0


def hoekverschil(a, b):
    """Kleinste verschil tussen twee kompasrichtingen, 0..180."""
    return np.abs((np.asarray(a) - np.asarray(b) + 180.0) % 360.0 - 180.0)


class Kustlijn:
    """Alle kuststukken (lon/lat) met een ruimtelijke index."""

    def __init__(self, lijnen):
        self.lijnen = np.asarray(lijnen, dtype=object)
        self.boom = STRtree(self.lijnen)

    @classmethod
    def uit_bestand(cls, pad, bbox=None):
        import pyogrio

        df = pyogrio.read_dataframe(pad, bbox=bbox, columns=[]) if bbox else pyogrio.read_dataframe(pad, columns=[])
        return cls(naar_kustlijnen(df.geometry.values))

    def in_doos(self, lon0, lat0, straal_m):
        """Kuststukken binnen een doos rond (lon0, lat0); werkt ook over de datumgrens."""
        dlat = straal_m / 111_000.0
        dlon = straal_m / (111_000.0 * max(np.cos(np.radians(lat0)), 0.02))
        dlon = min(dlon, 180.0)
        s, n = max(lat0 - dlat, -90.0), min(lat0 + dlat, 90.0)
        dozen = []
        w, e = lon0 - dlon, lon0 + dlon
        if w < -180:
            dozen += [(w + 360, s, 180, n), (-180, s, e, n)]
        elif e > 180:
            dozen += [(w, s, 180, n), (-180, s, e - 360, n)]
        else:
            dozen.append((w, s, e, n))
        idx = np.unique(np.concatenate([self.boom.query(shapely.box(*d)) for d in dozen]))
        return self.lijnen[idx]


def naar_kustlijnen(geoms, stuk=500):
    """Lijnen met het land links. Landvlakken (bv. GSHHG) worden kustlijnen in die richting.

    Lange lijnen worden in stukken van hoogstens 'stuk' punten geknipt, zodat de index snel blijft.
    """
    uit = []
    for g in geoms:
        if g is None or g.is_empty:
            continue
        if g.geom_type in ("Polygon", "MultiPolygon"):
            ringen = []
            for p in getattr(g, "geoms", [g]):
                p = shapely.orient_polygons(p) if hasattr(shapely, "orient_polygons") else shapely.geometry.polygon.orient(p, 1.0)
                # buitenrand tegen de klok in: land links. Gaten (meren) zijn geen zeekust.
                ringen.append(p.exterior)
            lijnen = ringen
        else:
            lijnen = list(getattr(g, "geoms", [g]))
        for l in lijnen:
            c = shapely.get_coordinates(l)
            for i in range(0, max(len(c) - 1, 1), stuk):
                deel = c[i:i + stuk + 1]
                if len(deel) >= 2:
                    uit.append(shapely.LineString(deel))
    return uit


@dataclass
class Resultaat:
    kustpunt_lonlat: tuple[float, float] | None = None
    afstand_kust_m: float | None = None
    spot_kant: str | None = None  # "zee" of "land"
    strandrichting: float | None = None
    eenheid: float | None = None
    venster_van: float | None = None
    venster_tot: float | None = None
    venster_breedte: float | None = None
    rekenpunt_lonlat: tuple[float, float] | None = None
    twijfel: list[str] = field(default_factory=list)


def _segmenten(lijnen_xy):
    """Alle lijnstukjes als arrays (x0, y0, x1, y1)."""
    delen = []
    for g in lijnen_xy:
        for part in getattr(g, "geoms", [g]):
            c = shapely.get_coordinates(part)
            if len(c) >= 2:
                delen.append(np.hstack([c[:-1], c[1:]]))
    if not delen:
        return np.zeros((0, 4))
    return np.vstack(delen)


def _normaal(seg):
    """Zeewaartse normaal (rechts van de lijnrichting) en lengte per stukje."""
    dx = seg[:, 2] - seg[:, 0]
    dy = seg[:, 3] - seg[:, 1]
    lengte = np.hypot(dx, dy)
    ok = lengte > 0
    nx = np.where(ok, dy / np.where(ok, lengte, 1), 0)
    ny = np.where(ok, -dx / np.where(ok, lengte, 1), 0)
    return nx, ny, lengte


def _afstand_punt_seg(px, py, seg):
    x0, y0, x1, y1 = seg.T
    dx, dy = x1 - x0, y1 - y0
    l2 = dx * dx + dy * dy
    t = np.clip(((px - x0) * dx + (py - y0) * dy) / np.where(l2 > 0, l2, 1), 0, 1)
    qx, qy = x0 + t * dx, y0 + t * dy
    return np.hypot(px - qx, py - qy), qx, qy


def _vensterboog(open_, stap, richting, gat_max):
    """Aaneengesloten boog van open richtingen rond de strandrichting.

    open_[i] gaat over richting i*stap. Kleine dichte stukken (<= gat_max graden) tellen als open.
    Geeft (van, tot, breedte) met van -> tot met de klok mee, of None.
    """
    n = len(open_)
    o = open_.copy()
    if not o.any():
        return None
    if o.all():
        return 0.0, 360.0, 360.0
    # dichte stukken, rondlopend, opvullen als ze smal zijn
    start = int(np.argmax(o))  # begin op een open richting
    rol = np.roll(o, -start)
    i = 0
    while i < n:
        if not rol[i]:
            j = i
            while j < n and not rol[j]:
                j += 1
            if (j - i) * stap <= gat_max:
                rol[i:j] = True
            i = j
        else:
            i += 1
    o = np.roll(rol, start)
    if o.all():
        return 0.0, 360.0, 360.0
    k = int(round(richting / stap)) % n
    if not o[k]:
        return None
    a = k
    while o[(a - 1) % n]:
        a = (a - 1) % n
    b = k
    while o[(b + 1) % n]:
        b = (b + 1) % n
    breedte = ((b - a) % n + 1) * stap
    return (a * stap) % 360.0, (b * stap) % 360.0, float(breedte)


def bereken(kust: Kustlijn, lon: float, lat: float, r: dict) -> Resultaat:
    """Strandrichting, swellvenster en rekenpunt voor één spot. r = regels/spots.yaml."""
    res = Resultaat()
    max_kust = r["positie"]["max_afstand_kust_m"]["waarde"]
    straal = r["strandrichting"]["straal_m"]["waarde"]
    min_eenheid = r["strandrichting"]["min_eenheid"]["waarde"]
    marge = r["strandrichting"]["andere_kust_marge_m"]["waarde"]
    sv = r["swellvenster"]
    vertrek = sv["vertrek_in_zee_m"]["waarde"]
    stap = sv["stap_graden"]["waarde"]
    bereik = sv["bereik_km"]["waarde"] * 1000.0
    gat = sv["gat_negeren_graden"]["waarde"]
    min_breedte = sv["min_breedte_graden"]["waarde"]

    proj = pyproj.Transformer.from_crs(
        "EPSG:4326", f"+proj=aeqd +lat_0={lat} +lon_0={lon} +datum=WGS84 +units=m", always_xy=True
    )
    terug = pyproj.Transformer.from_crs(
        f"+proj=aeqd +lat_0={lat} +lon_0={lon} +datum=WGS84 +units=m", "EPSG:4326", always_xy=True
    )

    def naar_xy(c):
        x, y = proj.transform(c[:, 0], c[:, 1])
        return np.column_stack([x, y])

    lijnen = kust.in_doos(lon, lat, bereik * 1.1)
    if len(lijnen) == 0:
        res.twijfel.append(f"geen kustlijn binnen {bereik/1000:.0f} km")
        return res
    lijnen_xy = shapely.transform(lijnen, naar_xy)
    seg = _segmenten(lijnen_xy)
    nx, ny, lengte = _normaal(seg)

    # 1. dichtste kustpunt
    d, qx, qy = _afstand_punt_seg(0.0, 0.0, seg)
    i = int(np.argmin(d))
    res.afstand_kust_m = float(d[i])
    kx, ky = float(qx[i]), float(qy[i])
    klon, klat = terug.transform(kx, ky)
    res.kustpunt_lonlat = (float(klon), float(klat))
    if res.afstand_kust_m > max_kust:
        res.twijfel.append(f"positie: {res.afstand_kust_m:.0f} m van de kust (max {max_kust} m)")
        return res
    # spot rechts (zee) of links (land) van het dichtste stukje
    x0, y0, x1, y1 = seg[i]
    kruis = (x1 - x0) * (0 - y0) - (y1 - y0) * (0 - x0)
    res.spot_kant = "land" if kruis > 0 else "zee"

    # 2. strandrichting: lengtegewogen gemiddelde normaal binnen 'straal' rond het kustpunt
    dk, _, _ = _afstand_punt_seg(kx, ky, seg)
    bij = (dk <= straal) & (lengte > 0)
    vx = float(np.sum(nx[bij] * lengte[bij]))
    vy = float(np.sum(ny[bij] * lengte[bij]))
    tot = float(np.sum(lengte[bij]))
    eenheid = float(np.hypot(vx, vy) / tot) if tot > 0 else 0.0
    res.eenheid = round(eenheid, 3)
    richting = float(kompas(vx, vy))
    if eenheid < min_eenheid:
        res.twijfel.append(f"strandrichting: kust kronkelt binnen {straal} m (eenheid {eenheid:.2f} < {min_eenheid})")
    else:
        res.strandrichting = round(richting, 1)

    # kust die de andere kant op kijkt, vlak bij de spot (landtong, pier, eilandje)
    dichtbij = (d <= res.afstand_kust_m + marge) & (lengte > 0)
    if dichtbij.any():
        r_seg = kompas(nx[dichtbij], ny[dichtbij])
        if np.any(hoekverschil(r_seg, richting) > 120):
            res.twijfel.append("kant onzeker: binnen bereik ligt ook kust die de andere kant op kijkt")

    # 3. rekenpunt in zee en swellvenster
    hx, hy = np.sin(np.radians(richting)), np.cos(np.radians(richting))
    ox, oy = kx + vertrek * hx, ky + vertrek * hy
    d_o, _, _ = _afstand_punt_seg(ox, oy, seg)
    if float(d_o.min()) < vertrek * 0.5:
        res.twijfel.append("vertrekpunt in zee ligt te dicht bij andere kust (smalle geul of haven)")
        return res
    olon, olat = terug.transform(ox, oy)
    res.rekenpunt_lonlat = (float(olon), float(olat))

    hoeken = np.arange(0, 360, stap, dtype=float)
    ex = ox + bereik * np.sin(np.radians(hoeken))
    ey = oy + bereik * np.cos(np.radians(hoeken))
    stralen = shapely.linestrings(np.stack([np.column_stack([np.full_like(ex, ox), np.full_like(ey, oy)]),
                                            np.column_stack([ex, ey])], axis=1))
    stukken = shapely.linestrings(seg.reshape(-1, 2, 2))
    boom = STRtree(stukken)
    paren = boom.query(stralen, predicate="intersects")
    geraakt = np.zeros(len(hoeken), bool)
    geraakt[np.unique(paren[0])] = True
    boog = _vensterboog(~geraakt, stap, richting, gat)
    if boog is None:
        res.twijfel.append(f"swellvenster: recht voor het strand ligt land binnen {bereik/1000:.0f} km")
    else:
        res.venster_van, res.venster_tot, res.venster_breedte = boog
        if res.venster_breedte < min_breedte:
            res.twijfel.append(f"swellvenster smal: {res.venster_breedte:.0f} graden")
    return res
