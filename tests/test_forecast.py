"""M3: elk strand krijgt een wind- en een golfpunt, golven in zee."""

import pytest

pytest.importorskip("shapely")
from pipeline.forecast import fetch  # noqa: E402


def test_elk_strand_heeft_punten():
    per_beach, wind, wave = fetch.points()
    assert len(per_beach) > 500
    assert all(v["wind"] in wind and v["golf"] in wave for v in per_beach.values())
    # Minder punten dan stranden: dat houdt Open-Meteo binnen 10.000 aanroepen per dag.
    assert (2 * len(wind) + len(wave)) * 4 < 10_000


def test_raster():
    assert fetch.snap(-8.5321, 37.1179) == (-8.55, 37.1)
