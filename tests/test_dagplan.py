"""Dagplan: welke activiteit kan op welk uur (pipeline/rules/dagplan.py)."""

from datetime import UTC, datetime

import pytest

from pipeline.rules.dagplan import daglicht, getij_fractie, uur, zon

EX = [[0, 50, 0], [360, 350, 1], [720, 60, 0]]  # laag 0', hoog 6u, laag 12u


def test_getij_fractie():
    assert getij_fractie(EX, 0) == pytest.approx(0)
    assert getij_fractie(EX, 180) == pytest.approx(0.5)
    assert getij_fractie(EX, 360) == pytest.approx(1)
    assert getij_fractie(EX, 540) == pytest.approx(0.5)
    assert getij_fractie(EX, 800) is None


def test_zon_lissabon_oktober():
    # 7 oktober 2026, Lissabon: zon op rond 7:30 lokale tijd (6:30 UTC), onder rond 19:10 (18:10 UTC).
    op, onder = zon(38.7, -9.14, datetime(2026, 10, 7, tzinfo=UTC))
    t0 = datetime(2026, 10, 7, tzinfo=UTC).timestamp() / 60
    assert 6 * 60 + 15 < op - t0 < 6 * 60 + 45
    assert 18 * 60 < onder - t0 < 18 * 60 + 25
    assert daglicht(38.7, -9.14, t0 + 12 * 60) and not daglicht(38.7, -9.14, t0 + 2 * 60)


@pytest.mark.parametrize("p,s", [(0.5, 2), (0.35, 2), (0.75, 2), (0.2, 1), (0.85, 1), (0.1, 0), (0.95, 0), (None, 1)])
def test_surf_volgens_getij(p, s):
    assert uur(wind=2, wave=3, wind_kn=9, windklasse="af", p=p, licht=True)["surf"] == s


def test_surf_vraagt_wave_3_of_4_en_wind_1_of_2():
    assert uur(1, 4, 5, "zij", 0.5, True)["surf"] == 2
    assert uur(3, 3, 14, "zij", 0.5, True)["surf"] == 0
    assert uur(1, 2, 5, "zij", 0.5, True)["surf"] == 0
    assert uur(1, 3, 5, "zij", 0.5, False)["surf"] == 0  # nacht


def test_wind_en_windgolf():
    assert uur(3, 1, 14, "zij", 0.5, True)["wind"] == 2
    assert uur(4, 4, 20, "zij", 0.5, True)["windgolf"] == 2
    assert uur(3, 3, 14, "zij", 0.95, True)["windgolf"] == 1  # hoog water: minder strand
    assert uur(3, 3, 14, "zij", 0.5, True)["wind"] == 0


def test_plat():
    assert uur(1, 1, 4, "aanlandig", 0.9, True)["plat"] == 2
    assert uur(1, 1, 4, "aanlandig", 0.5, True)["plat"] == 1  # sterkste stroming midden tussen eb en vloed
    assert uur(2, 1, 9, "af", 0.9, True)["plat"] == 0         # aflandig drijft je weg
    assert uur(2, 2, 11, "zij", 0.9, True)["plat"] == 0       # boven 10 kn


def test_vijf_is_overal_niet():
    assert set(uur(5, 3, 30, "zij", 0.5, True).values()) == {0}
    assert set(uur(1, 5, 3, "zij", 0.5, True).values()) == {0}
