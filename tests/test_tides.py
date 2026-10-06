"""M2: lezer van de getijtabel en interpolatie langs de kust."""

from pathlib import Path

import pytest

pytest.importorskip("shapely")
from pipeline.tides import interp, table  # noqa: E402

FIX = Path(__file__).parent / "fixtures" / "tides" / "tabel_voorbeeld.txt"


def test_lezer_tabelpagina():
    p = table.parse(FIX.read_text())["CASCAIS"]
    assert p.nivel_medio == 2.08
    assert p.lat == pytest.approx(38.693, abs=0.001) and p.lon == pytest.approx(-9.415, abs=0.001)
    assert len(p.events) == 48  # 12 dagen x 4
    days = {t.strftime("%m-%d") for t, _ in p.events}
    assert days == {f"{m:02d}-{d:02d}" for m in (1, 2, 3) for d in (1, 2, 17, 18)}
    kinds = [hi for _, _, hi in table.classify(p)]
    assert all(a != b for a, b in zip(kinds, kinds[1:], strict=False))  # hoog en laag wisselen af


def test_interpolatie_halverwege():
    a = [[0, 300, 1], [372, 100, 0]]
    b = [[20, 340, 1], [392, 80, 0]]
    assert interp.interpolate(a, b, 0.5) == [[10, 320, 1], [382, 90, 0]]
    assert interp.interpolate(a, b, 0.0) == a


def test_kustvolgorde_stations():
    sts = interp.load_stations()
    assert [s["id"] for s in sts] == ["viana", "leixoes", "nazare", "peniche", "cascais", "sines", "lagos", "huelva"]
    a, b, w, _ = interp.weights(-9.17, 38.65, sts)  # Costa da Caparica
    assert (a, b) == ("cascais", "sines") and 0 < w < 0.3
    a, b, w, _ = interp.weights(-7.92, 36.98, sts)  # Faro: tussen Lagos en Huelva
    assert (a, b) == ("lagos", "huelva") and 0.3 < w < 0.6


def test_elk_strand_heeft_getijstations():
    import json

    root = Path(__file__).resolve().parents[1]
    fc = json.loads((root / "data" / "beaches" / "stranden.geojson").read_text())
    tg = json.loads((root / "data" / "tides" / "stranden_getij.json").read_text())
    ids = {f["properties"]["id"] for f in fc["features"]}
    assert ids == set(tg)
    assert all(v["nauwkeurigheid"] in {"±5 min", "±15 min", "onzeker"} for v in tg.values())
