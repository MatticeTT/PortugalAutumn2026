"""Stap 1: meetkunde van strandrichting en swellvenster op verzonnen kustlijnen (geen echte data)."""

import numpy as np
import shapely
import yaml
from pathlib import Path

from spots import kust as K
from spots.bouw import kies

R = yaml.safe_load((Path(__file__).resolve().parents[1] / "regels" / "spots.yaml").read_text())


def km(lat):  # graden lengte per km
    return 1 / (111.32 * np.cos(np.radians(lat)))


def westkust():
    # zee in het westen: lijn van noord naar zuid (land links = oost)
    return shapely.LineString([(-9.0, 41.0), (-9.0, 39.0)])


def test_rechte_westkust():
    k = K.Kustlijn([westkust()])
    res = K.bereken(k, -9.0 - 0.2 * km(40), 40.0, R)
    assert res.twijfel == []
    assert abs(res.afstand_kust_m - 200) < 5
    assert res.spot_kant == "zee"
    assert abs(res.strandrichting - 270) < 0.5
    assert res.venster_breedte >= 179 and K.hoekverschil(res.venster_van, 180) <= 1 and K.hoekverschil(res.venster_tot, 0) <= 1
    assert res.rekenpunt_lonlat[0] < -9.0


def test_spot_op_land_binnen_300m():
    k = K.Kustlijn([westkust()])
    res = K.bereken(k, -9.0 + 0.1 * km(40), 40.0, R)
    assert res.spot_kant == "land" and abs(res.strandrichting - 270) < 0.5


def test_te_ver_van_kust():
    k = K.Kustlijn([westkust()])
    res = K.bereken(k, -9.0 - 2 * km(40), 40.0, R)
    assert res.strandrichting is None and res.twijfel[0].startswith("positie")


def test_eiland_voor_de_kust_schermt_af():
    # groot eiland 10 km uit de kust, 20 km breed: dicht stuk rond 270 graden
    lat = 40.0
    x0, x1 = -9.0 - 10 * km(lat), -9.0 - 15 * km(lat)
    eiland = shapely.LineString([(x0, 40.09), (x0, 39.91), (x1, 39.91), (x1, 40.09), (x0, 40.09)])  # tegen de klok in: zee rechts
    eiland = shapely.LineString(list(eiland.coords)[::-1]) if shapely.is_ccw(eiland) else eiland
    k = K.Kustlijn([westkust(), eiland])
    res = K.bereken(k, -9.0 - 0.1 * km(lat), lat, R)
    assert any(t.startswith("swellvenster: recht voor") for t in res.twijfel)


def test_klein_eilandje_wordt_genegeerd():
    lat = 40.0
    x = -9.0 - 20 * km(lat)
    # 300 m breed op 20 km: minder dan 1 graad schaduw
    eilandje = shapely.LineString([(x, 40.0015), (x - 0.003, 40.0015), (x - 0.003, 39.9985), (x, 39.9985), (x, 40.0015)])
    k = K.Kustlijn([westkust(), eilandje])
    res = K.bereken(k, -9.0 - 0.1 * km(lat), lat, R)
    assert res.venster_breedte >= 179


def test_baai_kronkelt():
    # zaagtand-kust: richting wisselt elke 100 m
    pts = [(-9.0 + (0.0012 if i % 2 else 0), 40.0 + 0.003 - i * 0.0009) for i in range(8)]
    k = K.Kustlijn([shapely.LineString(pts)])
    res = K.bereken(k, -9.0005, 40.0, R)
    assert any("kronkelt" in t for t in res.twijfel) or res.eenheid < 1


def test_datumgrens():
    # oostkust die naar het oosten kijkt op lengte 179.999, spot over de grens
    kust = shapely.LineString([(179.999, -17.0), (179.999, -18.0)][::-1])  # zuid->noord: zee rechts = oost
    k = K.Kustlijn([kust])
    res = K.bereken(k, -179.999, -17.5, R)
    assert res.afstand_kust_m < 300 and abs(res.strandrichting - 90) < 1


def test_vensterboog():
    o = np.ones(360, bool)
    o[0:90] = False  # dicht van 0 tot 89
    o[200:203] = False  # klein gat, wordt genegeerd
    assert K._vensterboog(o, 1, 180, 5) == (90.0, 359.0, 270.0)
    assert K._vensterboog(o, 1, 45, 5) is None


def test_bodemtags():
    t = R["bodem"]["buurt_naar_bodem"]
    assert kies({"natural": "beach"}, t) == "zand"
    assert kies({"natural": "beach", "surface": "pebblestone"}, t) == "keien"
    assert kies({"natural": "reef"}, t) == "rif"
