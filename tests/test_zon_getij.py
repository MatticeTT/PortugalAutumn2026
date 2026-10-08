"""Waterpeil en daglicht (pipeline/site/zon_getij.py)."""

from datetime import UTC, datetime

import pytest

from pipeline.site.zon_getij import daglicht, getij_fractie, zon

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


def test_planning_blokken():
    from datetime import UTC, datetime, timedelta

    from pipeline.site.planning import blokken, km
    t0 = datetime(2026, 10, 8, 7, tzinfo=UTC)
    uren = [t0 + timedelta(hours=i) for i in range(12)]
    ok = [True, True, False, True, True, True, False, True, True, True, True, False]
    assert blokken(uren, ok, 3) == [(3, 5), (7, 10)]      # twee blokken op één dag; 2 uur is geen blok
    assert blokken(uren, ok, 4) == [(7, 10)]
    assert km(37.1238, -8.5195) == 0
