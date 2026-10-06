"""M1: de meetkunde van de strandentabel, en de acceptatie op de gebouwde tabel."""

import json
from pathlib import Path

import pytest

pytest.importorskip("shapely")
from shapely.geometry import LineString, Point  # noqa: E402

from pipeline.beaches import build  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "beaches"
COASTAL = {"Viana do Castelo", "Braga", "Porto", "Aveiro", "Coimbra", "Leiria", "Lisboa", "Setúbal", "Beja", "Faro"}


def coast_ns():
    """Rechte kust van noord naar zuid getekend: land links (oost), zee rechts (west)."""
    line = LineString([(0, 50_000), (0, -50_000)])
    return build.Coast(list(build.chunks(line, 2)), [])


def test_kijkrichting_rechte_kust():
    c = coast_ns()
    facing, conf = c.orientation(Point(0, 0))
    assert abs(build.angdiff(facing, 270)) < 1
    assert conf > 0.99


def test_stralen_land_en_zee():
    c = coast_ns()
    origin = Point(-150, 0)
    assert c.ray_distance(origin, 90) == pytest.approx(150, abs=1)  # naar het land
    assert c.ray_distance(origin, 270) == build.PARAMS["straal_lengte_km"] * 1000  # open zee


def test_blootstelling_recht_en_schuin():
    dist = {d: (300.0 if 180 < d < 360 else 0.0) for d in range(0, 360, 5)}  # zee in het westen
    f = build.exposure(dist, 270)
    assert f[27] > 0.9                # recht uit zee
    assert f[9] < 0.05                # golven uit het oosten komen van over land
    assert f[18] < f[22] < f[27]      # schuiner invallend: minder energie


def test_beschut_strand_krijgt_deining_om_de_kaap():
    # Open tussen 205 en 300 graden, kijkt naar 251 (zoals Arrifana); deining uit 323.
    dist = {d: (300.0 if 205 <= d <= 300 else 1.0) for d in range(0, 360, 5)}
    f = build.exposure(dist, 251)
    assert 0.2 < f[32] < 0.6  # niet 0: door de spreiding komt er deining om de kaap


def test_venster():
    dist = {d: (300.0 if 200 <= d <= 340 else 1.0) for d in range(0, 360, 5)}
    assert build.window(dist) == [[200, 345]]
    assert build.window({d: 300.0 for d in range(0, 360, 5)}) == [[0, 360]]
    assert build.window({d: 0.0 for d in range(0, 360, 5)}) == []


def test_kompas():
    assert build.compass(270) == "W"
    assert build.compass(225) == "ZW"


# --- acceptatie M1 -----------------------------------------------------------

needs_data = pytest.mark.skipif(not (OUT / "stranden.geojson").exists(), reason="strandentabel nog niet gebouwd")


@needs_data
def test_elk_officieel_zwemwater_teruggevonden():
    v = json.loads((OUT / "verslag.json").read_text())
    assert v["eea_kustzwemwateren"] >= 300
    assert v["eea_niet_teruggevonden"] == []


@needs_data
def test_strandentabel_velden_en_licentie():
    fc = json.loads((OUT / "stranden.geojson").read_text())
    assert "ODbL" in fc["licentie"]
    assert len(fc["features"]) > 500
    for f in fc["features"]:
        p = f["properties"]
        lon, lat = f["geometry"]["coordinates"]
        assert -10 < lon < -6 and 36.8 < lat < 42.2
        assert 0 <= p["kijkrichting"] < 360
        assert len(p["blootstelling"]) == 36 and all(0 <= x <= 1 for x in p["blootstelling"])
        assert p["besloten_water"] is False
        assert p["district"] in COASTAL, (p["naam"], p["district"])
        assert p["onzeker"] == bool(p["redenen"])


@needs_data
def test_onzekere_lijst_beschikbaar():
    rows = (OUT / "onzeker.csv").read_text().splitlines()
    fc = json.loads((OUT / "stranden.geojson").read_text())
    assert len(rows) - 1 == sum(f["properties"]["onzeker"] for f in fc["features"])
