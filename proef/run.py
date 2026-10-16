"""Proef: voorspelling tegen meting op 14 spots, september 2026.

Gebruik: python -m proef.run --out proef/results
Stappen volgen de specificatie: 0 controle en meetpunten, 1 metingen, 2 voorspellingen,
3 opschonen en uitlijnen (in metingen.py), 4 windhoogte, 5 fouten, 6 rapport.
"""

import argparse
import sys
import tempfile
import time
from pathlib import Path

import pandas as pd

from . import metingen as M
from . import rapport
from . import voorspellingen as V
from .fouten import UREN, Z0_ZEE, afstand_km, foutmaten
from .logboek import Logboek
from .spots import SPOTS

MIN_DEKKING = 70.0
MAX_KM = 100.0
WINDVARS = ["wind_kn", "windrichting", "vlaag_kn"]
GOLFVARS = ["hs_m", "tp_s", "tm_s", "golfrichting"]


def dekking(df: pd.DataFrame, kol: str) -> float:
    if kol not in df:
        return 0.0
    return round(100 * df[kol].reindex(UREN).notna().sum() / len(UREN), 1)


# ---------------------------------------------------------------- stap 0: Open-Meteo

def controle_open_meteo(log: Logboek) -> tuple[dict, dict]:
    """Bestaan de modelnamen en variabelen? Stopt bij een onbekende modelnaam."""
    vlagen = {}
    for model in V.WINDMODELLEN:
        ok, msg = V.probe(log, V.PREVIOUS_RUNS, {"latitude": 51.23, "longitude": 2.905, "models": model,
                                                  "wind_speed_unit": "kn",
                                                  "hourly": "wind_speed_10m_previous_day1,wind_gusts_10m_previous_day1"})
        if ok:
            vlagen[model] = "wind_gusts_10m" not in msg
            log.info(f"Previous Runs, {model}: {msg}")
            continue
        ok2, msg2 = V.probe(log, V.PREVIOUS_RUNS, {"latitude": 51.23, "longitude": 2.905, "models": model,
                                                    "hourly": "wind_speed_10m_previous_day1"})
        if not ok2:
            sys.exit(f"STOP stap 0: windmodel '{model}' bestaat niet bij de Previous Runs API: {msg2}")
        vlagen[model] = False
        log.info(f"Previous Runs, {model}: vlagen niet beschikbaar ({msg})")
    log.antwoord("Modelnamen wind (best_match, ecmwf_ifs025, gfs_seamless)", True, "alle drie aanvaard door de Previous Runs API")
    log.antwoord("Vlagen met _previous_dayN", True,
                 ", ".join(f"{m}: {'ja' if v else 'nee'}" for m, v in vlagen.items()))

    golfvars = {}
    oceaan = {"latitude": 40.0, "longitude": -30.0, "cell_selection": "sea"}
    for model in V.GOLFMODELLEN:
        vars_ = list(V.GOLFVARS)
        ok, msg = V.probe(log, V.MARINE, {**oceaan, "models": model, "hourly": ",".join(vars_)})
        if not ok and "wave_peak_period" in msg:
            vars_.remove("wave_peak_period")
            ok, msg = V.probe(log, V.MARINE, {**oceaan, "models": model, "hourly": ",".join(vars_)})
        if not ok:
            ok_hs, msg_hs = V.probe(log, V.MARINE, {**oceaan, "models": model, "hourly": "wave_height"})
            if not ok_hs:
                sys.exit(f"STOP stap 0: golfmodel '{model}' bestaat niet bij de Marine API: {msg_hs}")
            sys.exit(f"STOP stap 0: Marine API weigert variabelen voor '{model}': {msg}")
        leeg = msg.split(": ", 1)[1].split(", ") if msg.startswith("alle waarden leeg") else []
        golfvars[model] = [v for v in vars_ if v not in leeg]
        log.info(f"Marine, {model}: bruikbaar {golfvars[model]}; {msg}")
    log.antwoord("Modelnamen golven (best_match, ecmwf_wam025, meteofrance_wave, ncep_gfswave025)", True,
                 "alle vier aanvaard door de Marine API")
    log.antwoord("wave_peak_period en wave_period per golfmodel", True,
                 "; ".join(f"{m}: piek {'ja' if 'wave_peak_period' in v else 'nee'}, gemiddeld {'ja' if 'wave_period' in v else 'nee'}"
                           for m, v in golfvars.items()))

    ok, msg = V.probe(log, V.MARINE, {**oceaan, "hourly": "wave_height_previous_day1"})
    log.antwoord("Langere horizonten voor golven", False,
                 f"Marine API met _previous_day1: {'werkt' if ok and msg == 'ok' else 'werkt niet (' + msg + ')'}. "
                 "De Single Runs API (single-runs-api.open-meteo.com/v1/forecast) noemt in haar documentatie enkel weermodellen, "
                 "geen golfmodellen. Golven worden in deze proef daarom enkel op korte horizon beoordeeld.")
    return vlagen, golfvars


# ---------------------------------------------------------------- stap 0+1: meetpunten en metingen

def kies_metar(log: Logboek, spot) -> tuple[dict | None, pd.DataFrame | None, list[dict]]:
    kand = M.metar_kandidaten(log, spot.metar_netwerken, spot.lat, spot.lon, MAX_KM)
    geprobeerd = []
    for k in kand[:6]:
        df = M.metar(log, k["id"])
        d = dekking(df, "wind_kn")
        geprobeerd.append({**k, "dekking_pct": d})
        if d >= MIN_DEKKING:
            return {**k, "dekking_pct": d}, df, geprobeerd
    return None, None, geprobeerd


def kies_copernicus(log: Logboek, index, spot, variabele: str, kol: str, werk: Path, vlaglog: dict):
    kand = M.copernicus_kandidaten(index, variabele, spot.lat, spot.lon, MAX_KM)
    geprobeerd = []
    for _, k in kand.head(5).iterrows():
        try:
            pad = M.copernicus_download(k.file_name, werk / "cmems")
            df = M.copernicus_lees(pad, log, vlaglog)
        except Exception as e:  # noqa: BLE001 - elk falend bestand loggen en verder
            log.info(f"Copernicus {k.file_name}: niet leesbaar ({e})")
            continue
        d = dekking(df, kol)
        naam = k.file_name.rsplit("/", 1)[-1]
        info = {"id": naam.removesuffix(".nc"), "lat": float(k.lat), "lon": float(k.lon),
                "afstand_km": float(k.afstand_km), "dekking_pct": d, "soort_bestand": k.soort}
        geprobeerd.append(info)
        if d >= MIN_DEKKING:
            return info, df, geprobeerd
    return None, None, geprobeerd


def meetpunten(log: Logboek, werk: Path):
    """Per spot: meetpunten voor golven, wind en watertemperatuur, met de metingen zelf."""
    res = {}
    rijen = []
    copernicus = M.copernicus_inloggen(log)
    index = None
    vlaglog: dict = {}
    if copernicus:
        try:
            index = M.copernicus_index(log, werk / "cmems_index")
        except Exception as e:  # noqa: BLE001
            log.info(f"Copernicus-index niet op te halen: {e}")
    ndbc_hoogtes = {}

    for s in SPOTS:
        r = {"golf": None, "wind": None, "sst": None}
        data = {}

        # Boeien in de VS
        if s.ndbc_golf:
            df, info = M.ndbc(log, s.ndbc_golf)
            ndbc_hoogtes[s.ndbc_golf] = info.get("anemometer_m")
            afst = float(afstand_km(s.lat, s.lon, info["lat"], info["lon"])) if info["lat"] is not None else None
            basis = {"id": f"NDBC {s.ndbc_golf}", "lat": info["lat"], "lon": info["lon"], "afstand_km": afst, "soort": "boei"}
            for groep, kol in (("golf", "hs_m"), ("sst", "sst_c")):
                d = dekking(df, kol)
                if d >= MIN_DEKKING and (afst is None or afst <= MAX_KM):
                    r[groep] = {**basis, "dekking_pct": d}
                    data[groep] = df
                rijen.append(rapport.station_rij(s, groep, {**basis, "dekking_pct": d},
                                                 "gekozen" if r[groep] else "afgewezen (dekking of afstand)"))
            if s.ndbc_wind == s.ndbc_golf:
                d = dekking(df, "wind_kn")
                ok = d >= MIN_DEKKING and (afst is None or afst <= MAX_KM)
                hoogte = info.get("anemometer_m")
                opm = f"anemometer {hoogte} m, omgerekend naar 10 m" if hoogte else "anemometerhoogte onbekend: NIET omgerekend"
                rijen.append(rapport.station_rij(s, "wind", {**basis, "dekking_pct": d},
                                                 ("gekozen; " if ok else "afgewezen (dekking of afstand); ") + opm))
                if ok:
                    r["wind"] = {**basis, "dekking_pct": d, "opmerking": opm}
                    data["wind"] = df

        # Wind van een luchthaven als er geen bruikbare boei is
        if r["wind"] is None and s.metar_netwerken:
            keuze, df, geprobeerd = kies_metar(log, s)
            for k in geprobeerd:
                rijen.append(rapport.station_rij(s, "wind", {**k, "id": f"METAR {k['id']}", "soort": "luchthaven"},
                                                 "gekozen" if keuze and k["id"] == keuze["id"] else "afgewezen (dekking)"))
            if keuze:
                r["wind"] = {**keuze, "id": f"METAR {keuze['id']}", "soort": "luchthaven"}
                data["wind"] = df
            spec = s.metar_spec or "(geen station genoemd)"
            log.antwoord(f"METAR-station {s.naam}", keuze is not None,
                         f"specificatie noemde {spec}; gekozen: "
                         + (f"{keuze['id']} ({keuze['naam']}, {keuze['afstand_km']:.1f} km, {keuze['dekking_pct']}% dekking)" if keuze
                            else "geen station binnen 100 km met ≥70% dekking → 'geen meting'")
                         + f"; geprobeerd: {', '.join(k['id'] + ' ' + str(k['dekking_pct']) + '%' for k in geprobeerd) or 'geen kandidaten'}")

        # Golven en watertemperatuur buiten de VS: Copernicus In Situ
        if not s.ndbc_golf:
            for groep, var, kol in (("golf", "VHM0", "hs_m"), ("sst", "TEMP", "sst_c")):
                if index is None:
                    rijen.append(rapport.station_rij(s, groep, None, "geen meting (Copernicus niet beschikbaar in deze run)"))
                    continue
                keuze, df, geprobeerd = kies_copernicus(log, index, s, var, kol, werk, vlaglog)
                for k in geprobeerd:
                    rijen.append(rapport.station_rij(s, groep, {**k, "soort": "boei" if groep == "golf" else "meetpaal/boei"},
                                                     "gekozen" if keuze and k["id"] == keuze["id"] else "afgewezen (dekking)"))
                if keuze:
                    r[groep] = {**keuze, "soort": "boei" if groep == "golf" else "meetpaal/boei"}
                    data[groep] = df
                if groep == "golf":
                    log.antwoord(f"Golfboei Copernicus {s.naam}", keuze is not None,
                                 (f"{keuze['id']}, {keuze['afstand_km']:.1f} km, {keuze['dekking_pct']}% dekking" if keuze
                                  else "geen platform met VHM0 binnen 100 km met ≥70% dekking → 'geen golfmeting'")
                                 + f"; geprobeerd: {len(geprobeerd)}")

        for groep in ("golf", "wind", "sst"):
            if r[groep] is None and not any(x["spot"] == s.naam and x["groep"] == groep and x["status"].startswith("gekozen") for x in rijen):
                rijen.append(rapport.station_rij(s, groep, None, "geen meting"))
        res[s.slug] = (r, data)

    # Antwoorden op de open punten rond metingen
    log.antwoord("NDBC maandarchieven voor september", True,
                 "https://www.ndbc.noaa.gov/data/stdmet/Sep/<id>.txt; gaten aangevuld uit realtime2 (zie regels hierboven)")
    log.antwoord("Meethoogte anemometer per NDBC-boei", all(v for k, v in ndbc_hoogtes.items() if k in {s.ndbc_wind for s in SPOTS}),
                 ", ".join(f"{k}: {v} m" if v else f"{k}: niet gevonden" for k, v in ndbc_hoogtes.items())
                 + " (stationspagina NDBC)")
    log.antwoord("Copernicus: welke vlagwaarde betekent 'goed'", bool(vlaglog) and all(v is not None for v in vlaglog.values()),
                 ("gelezen uit flag_meanings in de bestanden: " + ", ".join(f"{k}_QC good_data = {v}" for k, v in vlaglog.items()))
                 if vlaglog else "geen Copernicus-bestand gelezen in deze run")
    log.antwoord("Windvlagen in Copernicus In Situ", False,
                 "niet nodig: wind buiten de VS komt in deze proef van METAR, niet van Copernicus")
    log.antwoord("Ruwheidslengte z0 voor de windhoogtecorrectie", True,
                 f"z0 = {Z0_ZEE} m (open zee); u10 = uz · ln(10/z0) / ln(z/z0); enkel op NDBC-wind en -vlagen, METAR meet al op 10 m")
    log.antwoord("IEM-parameters", True,
                 "station, data=sknt,drct,gust, sts, ets, tz=Etc/UTC, format=onlycomma, latlon, missing, report_type=3,4 "
                 "(routine en speciale METAR), volgens /cgi-bin/request/asos.py?help; 1 s wachttijd per aanvraag")
    log.antwoord("Licentie METAR-downloads via IEM", False, "niet vermeld op de helppagina; nog na te vragen")
    log.antwoord("Klassen per sport uit stap 1", False, "nog niet beschikbaar; voorlopige klassen uit de specificatie gebruikt")
    return res, rijen


# ---------------------------------------------------------------- stap 2: voorspellingen

def voorspellingen(log: Logboek, s, r: dict, vlagen: dict, golfvars: dict):
    """Per positie (meetpunt en strand) de voorspellingen per model; kolommen <var>|<model>|<horizon>."""
    def wind_op(lat, lon):
        delen, cellen = [], {}
        for m in V.WINDMODELLEN:
            try:
                df, cel = V.wind(log, lat, lon, m, vlagen.get(m, False))
            except V.OpenMeteoFout as e:
                log.info(f"{s.naam}: wind {m} mislukt ({e})")
                continue
            cellen[m] = cel
            for k in df:
                var, d = k.rsplit("_d", 1)
                delen.append(df[k].rename(f"{var}|{m}|{V.HORIZONNEN[int(d)]}"))
        return delen, cellen

    def golf_op(lat, lon):
        delen, cellen = [], {}
        for m in V.GOLFMODELLEN:
            try:
                df, cel = V.marine(log, lat, lon, m, golfvars[m])
            except V.OpenMeteoFout as e:
                log.info(f"{s.naam}: marine {m} mislukt ({e})")
                continue
            cellen[m] = cel
            for k in df:
                delen.append(df[k].rename(f"{k}|{m}|kort"))
        return delen, cellen

    meetpunt, strand = {}, {}
    cellen = {}
    if r["wind"]:
        d, c = wind_op(r["wind"]["lat"], r["wind"]["lon"])
        meetpunt["wind"] = pd.concat(d, axis=1) if d else pd.DataFrame(index=UREN)
        cellen["wind"] = c
    for groep in ("golf", "sst"):
        if r[groep]:
            d, c = golf_op(r[groep]["lat"], r[groep]["lon"])
            meetpunt[groep] = pd.concat(d, axis=1) if d else pd.DataFrame(index=UREN)
            cellen[groep] = c
    dw, cw = wind_op(s.lat, s.lon)
    dg, cg = golf_op(s.lat, s.lon)
    strand = pd.concat(dw + dg, axis=1) if dw or dg else pd.DataFrame(index=UREN)
    cellen["strand"] = {**{f"wind {k}": v for k, v in cw.items()}, **{f"golf {k}": v for k, v in cg.items()}}
    return meetpunt, strand, cellen


# ---------------------------------------------------------------- stap 5: fouten

def fouten_spot(s, r: dict, data: dict, meetpunt: dict) -> list[dict]:
    rijen = []
    groepen = [("wind", WINDVARS), ("golf", GOLFVARS), ("sst", ["sst_c"])]
    for groep, vars_ in groepen:
        if groep not in meetpunt or groep not in data:
            continue
        obs, fc = data[groep], meetpunt[groep]
        for var in vars_:
            if var not in obs:
                continue
            o = obs[var]
            if var == "windrichting":
                o = o.where(obs["wind_kn"] >= 5)  # richting enkel bij minstens 5 kn gemeten wind
            for kol in fc:
                v, model, horizon = kol.split("|")
                if v != var:
                    continue
                m = foutmaten(fc[kol], o, var)
                rijen.append({"spot": s.naam, "slug": s.slug, "variabele": var, "model": model, "horizon": horizon, **m})
    return rijen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="proef/results")
    args = ap.parse_args()
    out = Path(args.out)
    (out / "ruw").mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    log = Logboek()
    werk = Path(tempfile.mkdtemp(prefix="proef_"))

    log.info("Stap 0: controle van de bronnen bij Open-Meteo")
    vlagen, golfvars = controle_open_meteo(log)

    log.info("Stap 0 en 1: meetpunten kiezen en metingen ophalen")
    res, stations = meetpunten(log, werk)
    rapport.schrijf_stations(out, stations)

    log.info("Stap 2: voorspellingen ophalen")
    alle_fouten, kop = [], {}
    for s in SPOTS:
        r, data = res[s.slug]
        meetpunt, strand, cellen = voorspellingen(log, s, r, vlagen, golfvars)
        fouten = fouten_spot(s, r, data, meetpunt)
        alle_fouten += fouten
        kop[s.slug] = rapport.spotkop(s, r, cellen)
        rapport.schrijf_ruw(out / "ruw", s.slug, data, meetpunt, strand)
        rapport.schrijf_spot(out, s, kop[s.slug], fouten)
        log.info(f"{s.naam}: {len(fouten)} foutregels")

    rapport.schrijf_overzicht(out, alle_fouten, res)
    rapport.schrijf_grafiek(out, alle_fouten)
    duur = (time.monotonic() - t0) / 60
    log.antwoord("Looptijd binnen een uur", duur < 60, f"{duur:.1f} minuten")
    rapport.schrijf_logboek(out, log, duur)
    log.info(f"Klaar in {duur:.1f} min")


if __name__ == "__main__":
    main()
