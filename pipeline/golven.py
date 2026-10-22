"""Golven van Copernicus Marine, opgesplitst in deining en windzee, voor de kaart.

Bron: GLOBAL_ANALYSISFORECAST_WAV_001_027 (Météo-France MFWAM), dataset cmems_mod_glo_wav_anfc_0.083deg_PT3H-i:
wereldwijd 1/12 graad (80 zuid .. 90 noord, lengte -180 .. 179,92), om de 3 uur, tot 10 dagen vooruit.
  deining  VHM0_SW1, VMDR_SW1, VTM01_SW1   primaire deining: hoogte (m), richting waar ze vandaan komt (graden),
                                           gemiddelde periode Tm01 (s)
  windzee  VHM0_WW,  VMDR_WW,  VTM01_WW    golven van de wind ter plaatse
Gebruik: gratis, ook commercieel, met de vermelding "Generated using E.U. Copernicus Marine Service Information".

De kaart toont de piekperiode, zoals surfers en de plankscore die gebruiken: Tp = Tm01 / 0,835
(JONSWAP-spectrum met piekfactor 3,3, DNV-RP-C205; zie de overdracht van de plankscore).

Het rooster van 1/12 graad wordt teruggebracht naar het rooster van de kaart (0,25 graad, lengte 0 .. 359,75,
breedte 90 noord .. 90 zuid): elke cel van 0,25 graad is het gemiddelde van de 3 x 3 cellen van 1/12 graad
eromheen (richting gewogen naar golfhoogte). Zuidelijker dan 80 graden zuid is er geen golfmodel.
"""

from __future__ import annotations

import datetime as dt
import os

import numpy as np

DATASET = "cmems_mod_glo_wav_anfc_0.083deg_PT3H-i"
SYSTEMEN = {
    "swell": ("VHM0_SW1", "VMDR_SW1", "VTM01_SW1"),
    "windsea": ("VHM0_WW", "VMDR_WW", "VTM01_WW"),
}
TM01_GEDEELD_DOOR_TP = 0.835
STAP = 3  # 0,25 graad = 3 cellen van 1/12 graad
NI, NJ = 1440, 721


def beschikbaar() -> bool:
    return bool(os.environ.get("COPERNICUSMARINE_SERVICE_USERNAME") and os.environ.get("COPERNICUSMARINE_SERVICE_PASSWORD"))


class Bron:
    """Opent de dataset één keer (alleen de metadata); velden komen per tijdstip binnen."""

    def __init__(self):
        import copernicusmarine

        vars_ = [v for s in SYSTEMEN.values() for v in s]
        self.ds = copernicusmarine.open_dataset(dataset_id=DATASET, variables=vars_)
        lat = self.ds["latitude"].values
        lon = self.ds["longitude"].values
        self.lat0, self.dlat = float(lat[0]), float(lat[1] - lat[0])
        self.lon0, self.dlon = float(lon[0]), float(lon[1] - lon[0])
        if abs(self.dlat - 1 / 12) > 1e-6 or abs(self.dlon - 1 / 12) > 1e-6:
            raise RuntimeError(f"Onverwacht Copernicus-rooster {self.dlat} x {self.dlon}")
        self.tijden = {np.datetime64(t, "s").astype(dt.datetime).replace(tzinfo=dt.UTC) for t in self.ds["time"].values}
        self.laatste = max(self.tijden)

    def heeft(self, t: dt.datetime) -> bool:
        return t in self.tijden

    def velden(self, t: dt.datetime, systeem: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Hoogte, richting (vandaan) en piekperiode op het kaartrooster van 0,25 graad; NaN op land."""
        tt = np.datetime64(t.replace(tzinfo=None), "ns")
        h, d, tm = (np.asarray(self.ds[v].sel(time=tt).values, dtype=np.float32) for v in SYSTEMEN[systeem])
        return naar_kaartrooster(h, d, tm / TM01_GEDEELD_DOOR_TP, self.lat0, self.lon0)


def _som3(x: np.ndarray) -> np.ndarray:
    """Som over de 3 x 3 buren; lengte loopt rond, breedte niet."""
    p = np.pad(x, ((1, 1), (0, 0)))
    s = p[:-2] + p[1:-1] + p[2:]
    return s + np.roll(s, 1, axis=1) + np.roll(s, -1, axis=1)


def naar_kaartrooster(h: np.ndarray, d: np.ndarray, tp: np.ndarray, lat0: float, lon0: float):
    """Fijn rooster (breedte oplopend vanaf lat0, lengte vanaf lon0, stap 1/12) naar 0,25 graad.

    Golfhoogte en periode: gewoon gemiddelde van de zeecellen in het 3 x 3-blok. Richting: gemiddelde van de
    eenheidsvectoren, gewogen naar golfhoogte. Een cel is zee als de middelste fijne cel zee is, zodat de kustlijn
    niet opschuift.
    """
    zee = np.isfinite(h) & np.isfinite(d) & np.isfinite(tp)
    w = zee.astype(np.float32)
    hz = np.where(zee, h, 0).astype(np.float32)
    n = _som3(w)
    hm = _som3(hz)
    tm = _som3(np.where(zee, tp, 0).astype(np.float32))
    r = np.radians(np.where(zee, d, 0))
    wh = hz + 1e-3 * w
    sx, cy = _som3(np.sin(r) * wh), _som3(np.cos(r) * wh)
    with np.errstate(invalid="ignore", divide="ignore"):
        hm, tm = hm / n, tm / n
    dm = np.degrees(np.arctan2(sx, cy)) % 360

    # Fijne index van elk punt van het kaartrooster.
    lats = 90 - 0.25 * np.arange(NJ)
    lons = 0.25 * np.arange(NI)
    jj = np.rint((lats - lat0) * 12).astype(int)
    ii = np.rint((((lons + 180) % 360 - 180) - lon0) * 12).astype(int) % h.shape[1]
    binnen = (jj >= 0) & (jj < h.shape[0])
    jc = np.clip(jj, 0, h.shape[0] - 1)
    uit = []
    for f in (hm, dm, tm):
        g = f[jc][:, ii]
        g[~zee[jc][:, ii] | ~binnen[:, None]] = np.nan
        uit.append(g.astype(np.float32))
    return tuple(uit)
