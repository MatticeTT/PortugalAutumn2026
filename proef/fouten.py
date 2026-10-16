"""Uitlijnen van metingen op het uur, windhoogtecorrectie en foutmaten (zuivere functies, getest)."""

import math

import numpy as np
import pandas as pd

KN_PER_MS = 1.943844  # 1 m/s = 3600/1852 kn
Z0_ZEE = 0.0002  # ruwheidslengte boven open zee (m)

UREN = pd.date_range("2026-09-01 00:00", "2026-09-30 23:00", freq="h", tz="UTC")

# Voorlopige klassen uit de specificatie (grenzen: onder, tussen, boven).
KLASSEN = {
    "wind_kn": [12, 25],
    "vlaag_kn": [12, 25],
    "hs_m": [0.5, 1.5, 3],
}

RICHTINGEN = {"windrichting", "golfrichting"}


def uurgemiddelde(reeks: pd.Series, richting: bool = False) -> pd.Series:
    """Gemiddelde per heel uur over het venster [uur - 30 min, uur + 30 min)."""
    reeks = reeks.dropna()
    if reeks.empty:
        return pd.Series(dtype=float)
    uur = (reeks.index + pd.Timedelta(minutes=30)).floor("h")
    if not richting:
        return reeks.groupby(uur).mean()
    rad = np.deg2rad(reeks.to_numpy())
    s = pd.Series(np.sin(rad), index=reeks.index).groupby(uur).mean()
    c = pd.Series(np.cos(rad), index=reeks.index).groupby(uur).mean()
    return (np.round(np.rad2deg(np.arctan2(s, c)), 6) % 360).astype(float)


def uurmaximum_vorig_uur(reeks: pd.Series) -> pd.Series:
    """Maximum over het voorgaande uur (uur - 60 min, uur], zoals Open-Meteo vlagen definieert."""
    reeks = reeks.dropna()
    if reeks.empty:
        return pd.Series(dtype=float)
    return reeks.groupby(reeks.index.ceil("h")).max()


def naar_10m(snelheid, hoogte_m: float, z0: float = Z0_ZEE):
    """Logaritmisch windprofiel: u10 = uz · ln(10/z0) / ln(z/z0)."""
    return snelheid * math.log(10 / z0) / math.log(hoogte_m / z0)


def hoekverschil(f, o):
    """Kortste hoekverschil F − O in graden, tussen −180 en 180."""
    return (np.asarray(f, float) - np.asarray(o, float) + 180) % 360 - 180


def klasse(x, grenzen):
    return np.digitize(np.asarray(x, float), grenzen)


def foutmaten(f: pd.Series, o: pd.Series, variabele: str, totaal_uren: int = len(UREN)) -> dict:
    """Bias, MAE, RMSE, r en trefkans over de uren waar F en O allebei geldig zijn."""
    paar = pd.concat([f.rename("f"), o.rename("o")], axis=1).dropna()
    n = len(paar)
    uit = {"n": n, "dekking_pct": round(100 * n / totaal_uren, 1),
           "bias": None, "mae": None, "rmse": None, "r": None, "trefkans_pct": None}
    if n == 0:
        return uit
    if variabele in RICHTINGEN:
        d = hoekverschil(paar.f, paar.o)
    else:
        d = (paar.f - paar.o).to_numpy()
        if n >= 3 and paar.f.std() > 0 and paar.o.std() > 0:
            uit["r"] = float(np.corrcoef(paar.f, paar.o)[0, 1])
        if variabele in KLASSEN:
            g = KLASSEN[variabele]
            uit["trefkans_pct"] = float(100 * np.mean(klasse(paar.f, g) == klasse(paar.o, g)))
    uit["bias"] = float(np.mean(d))
    uit["mae"] = float(np.mean(np.abs(d)))
    uit["rmse"] = float(np.sqrt(np.mean(d ** 2)))
    return uit


def afstand_km(lat1, lon1, lat2, lon2):
    """Grootcirkelafstand (haversine, aardstraal 6371 km)."""
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp = p2 - p1
    dl = np.radians(np.asarray(lon2) - np.asarray(lon1))
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 6371.0 * 2 * np.arcsin(np.sqrt(a))
