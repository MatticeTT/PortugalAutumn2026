"""M0-acceptatie: elk antwoord staat als testbestand, of de bron staat in OPEN.md."""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures" / "probe"
MANIFEST = json.loads((FIX / "manifest.json").read_text())
OPEN_MD = (ROOT / "OPEN.md").read_text()

# Bron -> aanvaarde fixturenamen (live via probe.py, of via Firecrawl).
BRONNEN = {
    "Open-Meteo GFS wind": ["openmeteo_gfs_wind", "firecrawl_openmeteo_wind_3modellen"],
    "Open-Meteo ECMWF wind": ["openmeteo_ecmwf_wind", "firecrawl_openmeteo_wind_3modellen"],
    "Open-Meteo GFS-Wave": ["openmeteo_gfswave", "firecrawl_openmeteo_gfswave"],
    "Copernicus IBI": ["copernicus_ibi"],
    "Neaps": ["neaps"],
    "EMODnet boei": ["emodnet_buoy"],
    "IPMA stations": ["ipma_observations"],
    "IPMA waarschuwingen": ["ipma_warnings", "firecrawl_ipma_warnings"],
}


def ok(name):
    return MANIFEST.get(name, {}).get("status") == "ok"


def load(name):
    return json.loads((FIX / f"{name}.json").read_text())


@pytest.mark.parametrize("bron", BRONNEN)
def test_bron_beproefd_of_open(bron):
    namen = BRONNEN[bron]
    if any(ok(n) for n in namen):
        return
    assert f"`{namen[0]}`" in OPEN_MD, f"{bron}: geen fixture en niet in OPEN.md"


def test_manifest_verwijst_naar_bestaande_bestanden():
    for name, meta in MANIFEST.items():
        if meta["status"] == "ok" and name != "neaps":
            assert (FIX / f"{name}.json").exists(), name


# --- inhoud ------------------------------------------------------------------


def wind_fixtures():
    out = []
    if ok("firecrawl_openmeteo_wind_3modellen"):
        for m in ("gfs_seamless", "ecmwf_ifs"):
            out.append(("firecrawl_openmeteo_wind_3modellen", f"_{m}"))
    for n in ("openmeteo_gfs_wind", "openmeteo_ecmwf_wind"):
        if ok(n):
            out.append((n, ""))
    return out


@pytest.mark.parametrize("name,suffix", wind_fixtures())
def test_openmeteo_wind_velden(name, suffix):
    d = load(name)
    h, u = d["hourly"], d["hourly_units"]
    n = len(h["time"])
    assert n >= 24
    for v in ("wind_speed_10m", "wind_gusts_10m", "wind_direction_10m"):
        assert len(h[v + suffix]) == n
    assert u["wind_speed_10m" + suffix] == "kn"
    assert all(0 <= x <= 360 for x in h["wind_direction_10m" + suffix] if x is not None)


@pytest.mark.parametrize("name", [n for n in ("openmeteo_gfswave", "firecrawl_openmeteo_gfswave") if ok(n)])
def test_gfswave_deelgolven(name):
    h = load(name)["hourly"]
    for deel in ("swell_wave", "secondary_swell_wave", "wind_wave"):
        for v in ("height", "period", "direction"):
            assert f"{deel}_{v}" in h
    # Bevinding M0: GFS-Wave geeft geen piekperiode voor de eerste deining.
    assert all(x is None for x in h["swell_wave_peak_period"])
    # Totale hoogte ~ wortel van de som van de kwadraten van de deelgolven (BoM).
    for i in range(len(h["time"])):
        som = sum(h[f"{d}_height"][i] ** 2 for d in ("swell_wave", "secondary_swell_wave", "wind_wave")) ** 0.5
        assert abs(som - h["wave_height"][i]) < 0.1


@pytest.mark.parametrize("name", [n for n in ("ipma_warnings", "firecrawl_ipma_warnings") if ok(n)])
def test_ipma_waarschuwingen(name):
    d = load(name)
    recs = d["records"] if isinstance(d, dict) else d
    for r in recs:
        assert {"awarenessTypeName", "awarenessLevelID", "idAreaAviso", "startTime", "endTime"} <= set(r)
        assert r["awarenessLevelID"] in {"green", "yellow", "orange", "red"}
    assert any(r["awarenessTypeName"] == "Agitação Marítima" for r in recs)
    assert any(r["idAreaAviso"] == "FAR" for r in recs)


def test_neaps_stations():
    st = load("neaps_stations")
    namen = {s["naam"] for s in st}
    assert namen == {"Viana Do Castelo", "Leixoes", "Nazare", "Peniche", "Cascais", "Sines", "Lagos Algarve"}
    vrij = {s["naam"] for s in st if s["licentie"] == "cc-by-4.0"}
    assert vrij == {"Cascais", "Lagos Algarve"}


def test_neaps_cascais_getij():
    ex = load("neaps_cascais")["extremes"]
    assert len(ex) >= 7
    for a, b in zip(ex, ex[1:]):
        assert a["high"] != b["high"]  # hoog en laag wisselen af
    for a, b in zip(ex, ex[2:]):  # twee keer per dag hoogwater, ~12 u 25 min
        from datetime import datetime
        dt = (datetime.fromisoformat(b["time"]) - datetime.fromisoformat(a["time"])).total_seconds() / 3600
        assert 11.5 < dt < 13.5
