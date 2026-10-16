"""Met de hand nagerekende voorbeelden voor de foutberekening van de proef."""

import math

import numpy as np
import pandas as pd
import pytest

from proef.fouten import afstand_km, foutmaten, hoekverschil, naar_10m, uurgemiddelde, uurmaximum_vorig_uur
from proef.logboek import Logboek
from proef.metingen import lees_ndbc

T = pd.date_range("2026-09-01", periods=5, freq="h", tz="UTC")


def test_vijf_uur_windsnelheid():
    # F − O = 2, −1, 0, 3, −4
    f = pd.Series([12, 9, 20, 28, 6], index=T, dtype=float)
    o = pd.Series([10, 10, 20, 25, 10], index=T, dtype=float)
    m = foutmaten(f, o, "wind_kn", totaal_uren=5)
    assert m["n"] == 5 and m["dekking_pct"] == 100.0
    assert m["bias"] == pytest.approx(0.0)  # (2 − 1 + 0 + 3 − 4) / 5
    assert m["mae"] == pytest.approx(2.0)  # (2 + 1 + 0 + 3 + 4) / 5
    assert m["rmse"] == pytest.approx(math.sqrt(6.0))  # (4 + 1 + 0 + 9 + 16) / 5 = 6
    # klassen <12, 12–25, >25: F = 1,0,1,2,0; O = 0,0,1,2,0 → 4 van 5
    assert m["trefkans_pct"] == pytest.approx(80.0)
    assert m["r"] == pytest.approx(np.corrcoef(f, o)[0, 1])


def test_vijf_uur_richting_en_ontbrekend():
    f = pd.Series([350, 10, 180, 90, np.nan], index=T, dtype=float)
    o = pd.Series([10, 350, 170, 100, 50], index=T, dtype=float)
    m = foutmaten(f, o, "windrichting", totaal_uren=5)
    # kortste verschillen: −20, 20, 10, −10 (vijfde uur ontbreekt)
    assert m["n"] == 4 and m["dekking_pct"] == 80.0
    assert m["bias"] == pytest.approx(0.0)
    assert m["mae"] == pytest.approx(15.0)
    assert m["rmse"] == pytest.approx(math.sqrt(250.0))
    assert m["r"] is None and m["trefkans_pct"] is None


def test_hoekverschil_rand():
    assert list(hoekverschil([0, 359, 180], [180, 1, 0])) == [-180, -2, -180]


def test_uurgemiddelde_venster():
    t = pd.to_datetime(["2026-09-01 00:29", "2026-09-01 00:30", "2026-09-01 01:20", "2026-09-01 00:50"], utc=True)
    s = pd.Series([1.0, 3.0, 5.0, 7.0], index=t)
    u = uurgemiddelde(s)
    assert u[pd.Timestamp("2026-09-01 00:00", tz="UTC")] == 1.0  # [23:30, 00:30)
    assert u[pd.Timestamp("2026-09-01 01:00", tz="UTC")] == pytest.approx(5.0)  # 00:30, 00:50, 01:20


def test_uurgemiddelde_richting_over_noord():
    t = pd.to_datetime(["2026-09-01 00:00", "2026-09-01 00:10"], utc=True)
    u = uurgemiddelde(pd.Series([350.0, 10.0], index=t), richting=True)
    assert min(u.iloc[0], 360 - u.iloc[0]) == pytest.approx(0.0, abs=1e-9)


def test_vlaag_vorig_uur():
    t = pd.to_datetime(["2026-09-01 00:00", "2026-09-01 00:10", "2026-09-01 00:50", "2026-09-01 01:00"], utc=True)
    v = uurmaximum_vorig_uur(pd.Series([30.0, 10.0, 12.0, 11.0], index=t))
    assert v[pd.Timestamp("2026-09-01 00:00", tz="UTC")] == 30.0
    assert v[pd.Timestamp("2026-09-01 01:00", tz="UTC")] == 12.0  # (00:00, 01:00]


def test_windprofiel():
    # 10 m blijft gelijk; 4 m naar 10 m: ln(10/0,0002)/ln(4/0,0002) = 1,0925
    assert naar_10m(10.0, 10.0) == pytest.approx(10.0)
    assert naar_10m(1.0, 4.0) == pytest.approx(math.log(50000) / math.log(20000))


def test_afstand():
    # één breedtegraad = 6371·π/180 km
    assert float(afstand_km(0, 0, 1, 0)) == pytest.approx(111.195, abs=0.01)


def test_ndbc_ontbrekende_codes():
    tekst = """#YY  MM DD hh mm WDIR WSPD GST  WVHT   DPD   APD MWD   PRES  ATMP  WTMP  DEWP  VIS PTDY  TIDE
#yr  mo dy hr mn degT m/s  m/s     m   sec   sec degT   hPa  degC  degC  degC  nmi  hPa    ft
2026 09 01 00 00  99  5.0  6.0  1.20  12.0   7.0  99 1015.0  15.0  14.0  10.0   MM   MM    MM
2026 09 01 00 10 999 99.0 99.0 99.00 99.00 99.00 999 9999.0 999.0 999.0 999.0   MM   MM    MM
2026 09 01 00 20  MM   MM   MM    MM    MM    MM  MM     MM    MM    MM    MM   MM   MM    MM
"""
    df = lees_ndbc(tekst, Logboek(), "test")
    assert len(df) == 3
    eerste = df.iloc[0]
    assert eerste.WDIR == 99 and eerste.MWD == 99  # 99° is een geldige richting
    assert eerste.WSPD == 5.0 and eerste.WVHT == 1.2 and eerste.WTMP == 14.0
    assert df.iloc[1].isna().all() and df.iloc[2].isna().all()
