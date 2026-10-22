# Logboek proef

Gestart 2026-10-22 12:24 UTC, klaar 2026-10-22 12:32 UTC (8.0 min).

## Bronnen

- Open-Meteo Previous Runs API (wind, `_previous_day1/3/5`) en Marine API (golven, watertemperatuur), CC BY 4.0, niet-commercieel
- NDBC (NOAA): maandarchief `data/stdmet/Sep/<id>.txt`, aangevuld uit `data/realtime2/<id>.txt`; stationspagina voor positie en anemometerhoogte
- METAR via Iowa Environmental Mesonet: `cgi-bin/request/asos.py`; stationslijsten `geojson/network/<netwerk>.geojson`
- Copernicus Marine In Situ: `cmems_obs-ins_glo_phybgcwav_mynrt_na_irr`, `index_monthly.txt`, map `monthly/<soort>/202609/`

## Aanvragen

- marine-api.open-meteo.com: 141
- mesonet.agron.iastate.edu: 27
- previous-runs-api.open-meteo.com: 87
- www.ndbc.noaa.gov: 12
- Open-Meteo, geschat gewicht (meer dan 10 variabelen of 2 weken telt meervoudig): 489

## Weggefilterde waarden

| Bron | Reden | Aantal |
|---|---|---:|
| Copernicus GL_TS_MO_EXAU061_202609.nc | VTPK: kwaliteitsvlag niet 'good_data' | 5 |
| Copernicus IR_TS_MO_Donostia-buoy_202609.nc | TEMP: kwaliteitsvlag niet 'good_data' | 76 |
| Copernicus IR_TS_MO_Tarifa-coast-buoy_202609.nc | VHM0: kwaliteitsvlag niet 'good_data' | 2 |
| Copernicus IR_TS_MO_Tarifa-coast-buoy_202609.nc | VMDR: kwaliteitsvlag niet 'good_data' | 2 |
| Copernicus IR_TS_MO_Tarifa-coast-buoy_202609.nc | VTM02: kwaliteitsvlag niet 'good_data' | 2 |
| Copernicus IR_TS_MO_Tarifa-coast-buoy_202609.nc | VTPK: kwaliteitsvlag niet 'good_data' | 22 |
| Copernicus NO_TS_MO_HoekVanHollandNAP_202609.nc | TEMP: kwaliteitsvlag niet 'good_data' | 1648 |
| Copernicus NO_TS_MO_MaeslantkeringZeezijdeNoordMeetpaal_202609.nc | VTPK: kwaliteitsvlag niet 'good_data' | 37 |
| Copernicus NO_TS_MO_OstendEasternPalisadeBuoy_202609.nc | TEMP: kwaliteitsvlag niet 'good_data' | 94 |
| METAR PHOG | windsnelheid ontbreekt in bericht | 3 |
| NDBC 41009 maandarchief | APD: ontbrekend (code 99) | 2851 |
| NDBC 41009 maandarchief | DPD: ontbrekend (code 99) | 2854 |
| NDBC 41009 maandarchief | MWD: ontbrekend (code 999) | 2854 |
| NDBC 41009 maandarchief | WTMP: ontbrekend (code 999) | 4252 |
| NDBC 41009 maandarchief | WVHT: ontbrekend (code 99) | 2851 |
| NDBC 41009 realtime2 | APD: ontbrekend (MM) | 3458 |
| NDBC 41009 realtime2 | DPD: ontbrekend (MM) | 4309 |
| NDBC 41009 realtime2 | GST: ontbrekend (MM) | 43 |
| NDBC 41009 realtime2 | MWD: ontbrekend (MM) | 3458 |
| NDBC 41009 realtime2 | WDIR: ontbrekend (MM) | 103 |
| NDBC 41009 realtime2 | WSPD: ontbrekend (MM) | 43 |
| NDBC 41009 realtime2 | WTMP: ontbrekend (MM) | 6430 |
| NDBC 41009 realtime2 | WVHT: ontbrekend (MM) | 3454 |
| NDBC 41025 maandarchief | APD: ontbrekend (code 99) | 2865 |
| NDBC 41025 maandarchief | DPD: ontbrekend (code 99) | 2865 |
| NDBC 41025 maandarchief | GST: ontbrekend (code 99) | 23 |
| NDBC 41025 maandarchief | MWD: ontbrekend (code 999) | 2865 |
| NDBC 41025 maandarchief | WDIR: ontbrekend (code 999) | 23 |
| NDBC 41025 maandarchief | WSPD: ontbrekend (code 99) | 23 |
| NDBC 41025 maandarchief | WTMP: ontbrekend (code 999) | 47 |
| NDBC 41025 maandarchief | WVHT: ontbrekend (code 99) | 2865 |
| NDBC 41025 realtime2 | APD: ontbrekend (MM) | 3381 |
| NDBC 41025 realtime2 | DPD: ontbrekend (MM) | 4344 |
| NDBC 41025 realtime2 | GST: ontbrekend (MM) | 138 |
| NDBC 41025 realtime2 | MWD: ontbrekend (MM) | 3381 |
| NDBC 41025 realtime2 | WDIR: ontbrekend (MM) | 153 |
| NDBC 41025 realtime2 | WSPD: ontbrekend (MM) | 138 |
| NDBC 41025 realtime2 | WTMP: ontbrekend (MM) | 232 |
| NDBC 41025 realtime2 | WVHT: ontbrekend (MM) | 3377 |
| NDBC 46026 maandarchief | APD: ontbrekend (code 99) | 2855 |
| NDBC 46026 maandarchief | DPD: ontbrekend (code 99) | 2855 |
| NDBC 46026 maandarchief | GST: ontbrekend (code 99) | 20 |
| NDBC 46026 maandarchief | MWD: ontbrekend (code 999) | 2855 |
| NDBC 46026 maandarchief | WDIR: ontbrekend (code 999) | 20 |
| NDBC 46026 maandarchief | WSPD: ontbrekend (code 99) | 20 |
| NDBC 46026 maandarchief | WTMP: ontbrekend (code 999) | 30 |
| NDBC 46026 maandarchief | WVHT: ontbrekend (code 99) | 2855 |
| NDBC 46026 realtime2 | APD: ontbrekend (MM) | 2665 |
| NDBC 46026 realtime2 | DPD: ontbrekend (MM) | 4709 |
| NDBC 46026 realtime2 | GST: ontbrekend (MM) | 171 |
| NDBC 46026 realtime2 | MWD: ontbrekend (MM) | 2665 |
| NDBC 46026 realtime2 | WDIR: ontbrekend (MM) | 219 |
| NDBC 46026 realtime2 | WSPD: ontbrekend (MM) | 171 |
| NDBC 46026 realtime2 | WTMP: ontbrekend (MM) | 938 |
| NDBC 46026 realtime2 | WVHT: ontbrekend (MM) | 2660 |
| NDBC 51205 maandarchief | GST: ontbrekend (code 99) | 1440 |
| NDBC 51205 maandarchief | WDIR: ontbrekend (code 999) | 1440 |
| NDBC 51205 maandarchief | WSPD: ontbrekend (code 99) | 1440 |
| NDBC 51205 realtime2 | APD: ontbrekend (MM) | 2 |
| NDBC 51205 realtime2 | GST: ontbrekend (MM) | 2179 |
| NDBC 51205 realtime2 | MWD: ontbrekend (MM) | 2 |
| NDBC 51205 realtime2 | WDIR: ontbrekend (MM) | 2179 |
| NDBC 51205 realtime2 | WSPD: ontbrekend (MM) | 2179 |

## Open punten uit de specificatie (NA TE GAAN)

| Punt | Status | Antwoord |
|---|---|---|
| Modelnamen wind (best_match, ecmwf_ifs025, gfs_seamless) | opgelost | alle drie aanvaard door de Previous Runs API |
| Vlagen met _previous_dayN | opgelost | best_match: ja, ecmwf_ifs025: nee, gfs_seamless: ja |
| Modelnamen golven (best_match, ecmwf_wam025, meteofrance_wave, ncep_gfswave025) | opgelost | alle vier aanvaard door de Marine API |
| wave_peak_period en wave_period per golfmodel | opgelost | best_match: piek nee, gemiddeld ja; ecmwf_wam025: piek ja, gemiddeld ja; meteofrance_wave: piek nee, gemiddeld ja; ncep_gfswave025: piek nee, gemiddeld ja |
| Langere horizonten voor golven | NIET OPGELOST | Marine API met _previous_day1: werkt. De Single Runs API (single-runs-api.open-meteo.com/v1/forecast) noemt in haar documentatie enkel weermodellen, geen golfmodellen. Golven worden in deze proef daarom enkel op korte horizon beoordeeld. |
| Copernicus: namen van de omgevingsvariabelen voor de Toolbox | opgelost | COPERNICUSMARINE_SERVICE_USERNAME en COPERNICUSMARINE_SERVICE_PASSWORD; aanwezig in deze run |
| METAR-station Ho'okipa, Maui (VS) | opgelost | specificatie noemde PHOG; gekozen: PHOG (Kahului, 9.5 km, 99.7% dekking); geprobeerd: PHOG 99.7% |
| METAR-station Oostende, Mariakerke (BE) | opgelost | specificatie noemde EBOS; gekozen: EBOS (Ostend, 4.6 km, 100.0% dekking); geprobeerd: EBOS 100.0% |
| Golfboei Copernicus Oostende, Mariakerke (BE) | opgelost | NO_TS_MO_OstendEasternPalisadeBuoy_202609, 2.5 km, 100.0% dekking; geprobeerd: 1 |
| METAR-station Scheveningen (NL) | opgelost | specificatie noemde EHRD; gekozen: EHRD (Rotterdam, 21.0 km, 100.0% dekking); geprobeerd: EHRD 100.0% |
| Golfboei Copernicus Scheveningen (NL) | opgelost | NO_TS_MO_MaeslantkeringZeezijdeNoordMeetpaal_202609, 18.0 km, 99.9% dekking; geprobeerd: 1 |
| METAR-station Hossegor, La Gravière (FR) | opgelost | specificatie noemde LFBZ; gekozen: LFBZ (Biarritz-bayonne, 23.6 km, 100.0% dekking); geprobeerd: LFBZ 100.0% |
| Golfboei Copernicus Hossegor, La Gravière (FR) | opgelost | IR_TS_MO_Donostia-buoy_202609, 47.1 km, 98.2% dekking; geprobeerd: 1 |
| METAR-station Nazaré, Praia do Norte (PT) | opgelost | specificatie noemde (geen station genoemd); gekozen: LPMR (Monte Real, 30.0 km, 92.6% dekking); geprobeerd: LPMR 92.6% |
| Golfboei Copernicus Nazaré, Praia do Norte (PT) | opgelost | IR_TS_MO_6200199_202609, 12.0 km, 100.0% dekking; geprobeerd: 1 |
| METAR-station Tarifa, Los Lances (ES) | opgelost | specificatie noemde LXGB; gekozen: LEAG (Algeciras, 20.5 km, 100.0% dekking); geprobeerd: LEAG 100.0% |
| Golfboei Copernicus Tarifa, Los Lances (ES) | opgelost | IR_TS_MO_Tarifa-coast-buoy_202609, 3.5 km, 99.3% dekking; geprobeerd: 1 |
| METAR-station Pozo Izquierdo, Gran Canaria (ES) | opgelost | specificatie noemde GCLP; gekozen: GCLP (Gran Canaria, 11.9 km, 100.0% dekking); geprobeerd: GCLP 100.0% |
| Golfboei Copernicus Pozo Izquierdo, Gran Canaria (ES) | opgelost | IR_TS_MO_LasPalmas-coast-buoy_202609, 25.7 km, 99.2% dekking; geprobeerd: 1 |
| METAR-station Big Bay, Kaapstad (ZA) | opgelost | specificatie noemde FACT; gekozen: FACT (Cape Town, 23.5 km, 99.3% dekking); geprobeerd: FACT 99.3% |
| Golfboei Copernicus Big Bay, Kaapstad (ZA) | NIET OPGELOST | geen platform met VHM0 binnen 100 km met ≥70% dekking → 'geen golfmeting'; geprobeerd: 0 |
| METAR-station Manly, Sydney (AU) | opgelost | specificatie noemde YSSY; gekozen: YSSY (Sydney, 19.8 km, 99.3% dekking); geprobeerd: YSSY 99.3% |
| Golfboei Copernicus Manly, Sydney (AU) | opgelost | GL_TS_MO_EXAU061_202609, 8.0 km, 99.9% dekking; geprobeerd: 1 |
| METAR-station Joaquina, Florianópolis (BR) | opgelost | specificatie noemde SBFL; gekozen: SBFL (Florianopolis, 10.8 km, 100.0% dekking); geprobeerd: SBFL 100.0% |
| Golfboei Copernicus Joaquina, Florianópolis (BR) | NIET OPGELOST | geen platform met VHM0 binnen 100 km met ≥70% dekking → 'geen golfmeting'; geprobeerd: 0 |
| METAR-station Uluwatu, Bali (ID) | opgelost | specificatie noemde WADD; gekozen: WADD (Denpasar, 11.5 km, 100.0% dekking); geprobeerd: WADD 100.0% |
| Golfboei Copernicus Uluwatu, Bali (ID) | NIET OPGELOST | geen platform met VHM0 binnen 100 km met ≥70% dekking → 'geen golfmeting'; geprobeerd: 0 |
| NDBC maandarchieven voor september | opgelost | https://www.ndbc.noaa.gov/data/stdmet/Sep/<id>.txt; gaten aangevuld uit realtime2 (zie regels hierboven) |
| Meethoogte anemometer per NDBC-boei | opgelost | 46026: 4.1 m, 51205: niet gevonden, 41025: 4.1 m, 41009: 3.8 m (stationspagina NDBC) |
| Copernicus: welke vlagwaarde betekent 'goed' | opgelost | gelezen uit flag_meanings in de bestanden: VHM0_QC good_data = 1, TEMP_QC good_data = 1, VTPK_QC good_data = 1, VTM02_QC good_data = 1, VMDR_QC good_data = 1 |
| Windvlagen in Copernicus In Situ | NIET OPGELOST | niet nodig: wind buiten de VS komt in deze proef van METAR, niet van Copernicus |
| Ruwheidslengte z0 voor de windhoogtecorrectie | opgelost | z0 = 0.0002 m (open zee); u10 = uz · ln(10/z0) / ln(z/z0); enkel op NDBC-wind en -vlagen, METAR meet al op 10 m |
| IEM-parameters | opgelost | station, data=sknt,drct,gust, sts, ets, tz=Etc/UTC, format=onlycomma, latlon, missing, report_type=3,4 (routine en speciale METAR), volgens /cgi-bin/request/asos.py?help; 1 s wachttijd per aanvraag |
| Licentie METAR-downloads via IEM | NIET OPGELOST | niet vermeld op de helppagina; nog na te vragen |
| Klassen per sport uit stap 1 | NIET OPGELOST | nog niet beschikbaar; voorlopige klassen uit de specificatie gebruikt |
| Looptijd binnen een uur | opgelost | 8.0 minuten |

## Verloop

- 12:24:12 Stap 0: controle van de bronnen bij Open-Meteo
- 12:24:12 Previous Runs, best_match: ok
- 12:24:13 Previous Runs, ecmwf_ifs025: alle waarden leeg: wind_gusts_10m_previous_day1
- 12:24:14 Previous Runs, gfs_seamless: ok
- 12:24:14 NA TE GAAN · Modelnamen wind (best_match, ecmwf_ifs025, gfs_seamless): alle drie aanvaard door de Previous Runs API
- 12:24:14 NA TE GAAN · Vlagen met _previous_dayN: best_match: ja, ecmwf_ifs025: nee, gfs_seamless: ja
- 12:24:14 Marine, best_match: bruikbaar ['wave_height', 'wave_period', 'wave_direction', 'sea_surface_temperature']; alle waarden leeg: wave_peak_period
- 12:24:15 Marine, ecmwf_wam025: bruikbaar ['wave_height', 'wave_period', 'wave_peak_period', 'wave_direction']; alle waarden leeg: sea_surface_temperature
- 12:24:16 Marine, meteofrance_wave: bruikbaar ['wave_height', 'wave_period', 'wave_direction']; alle waarden leeg: wave_peak_period, sea_surface_temperature
- 12:24:17 Marine, ncep_gfswave025: bruikbaar ['wave_height', 'wave_period', 'wave_direction']; alle waarden leeg: wave_peak_period, sea_surface_temperature
- 12:24:17 NA TE GAAN · Modelnamen golven (best_match, ecmwf_wam025, meteofrance_wave, ncep_gfswave025): alle vier aanvaard door de Marine API
- 12:24:17 NA TE GAAN · wave_peak_period en wave_period per golfmodel: best_match: piek nee, gemiddeld ja; ecmwf_wam025: piek ja, gemiddeld ja; meteofrance_wave: piek nee, gemiddeld ja; ncep_gfswave025: piek nee, gemiddeld ja
- 12:24:18 NA TE GAAN · Langere horizonten voor golven: Marine API met _previous_day1: werkt. De Single Runs API (single-runs-api.open-meteo.com/v1/forecast) noemt in haar documentatie enkel weermodellen, geen golfmodellen. Golven worden in deze proef daarom enkel op korte horizon beoordeeld.
- 12:24:18 Stap 0 en 1: meetpunten kiezen en metingen ophalen
- 12:24:18 NA TE GAAN · Copernicus: namen van de omgevingsvariabelen voor de Toolbox: COPERNICUSMARINE_SERVICE_USERNAME en COPERNICUSMARINE_SERVICE_PASSWORD; aanwezig in deze run
- 12:24:41 Copernicus-index: 9548 bestanden voor 202609; soorten: {'PF': 4362, 'DB': 1643, 'TS': 1234, 'MO': 1179, 'TG': 596, 'RF': 120, 'ML': 106, 'HF': 72, 'CT': 66, 'GL': 65, 'FB': 36, 'SD': 28, 'SM': 16, 'XB': 16, 'AD': 7, 'TX': 2}
- 12:24:42 NDBC 46026: maandarchief 4260 regels in september
- 12:24:43 NDBC 46026: realtime2 3361 regels in september
- 12:24:43 NDBC 46026: realtime2 vult 4251 ontbrekende waarden van het maandarchief aan
- 12:24:45 NDBC 51205: maandarchief 1440 regels in september
- 12:24:46 NDBC 51205: realtime2 1432 regels in september
- 12:24:46 NDBC 51205: realtime2 vult 5 ontbrekende waarden van het maandarchief aan
- 12:24:47 NA TE GAAN · METAR-station Ho'okipa, Maui (VS): specificatie noemde PHOG; gekozen: PHOG (Kahului, 9.5 km, 99.7% dekking); geprobeerd: PHOG 99.7%
- 12:24:48 NDBC 41025: maandarchief 4265 regels in september
- 12:24:49 NDBC 41025: realtime2 3370 regels in september
- 12:24:49 NDBC 41025: realtime2 vult 4402 ontbrekende waarden van het maandarchief aan
- 12:24:51 NDBC 41009: maandarchief 4252 regels in september
- 12:24:52 NDBC 41009: realtime2 3362 regels in september
- 12:24:52 NDBC 41009: realtime2 vult 4415 ontbrekende waarden van het maandarchief aan
- 12:24:55 NA TE GAAN · METAR-station Oostende, Mariakerke (BE): specificatie noemde EBOS; gekozen: EBOS (Ostend, 4.6 km, 100.0% dekking); geprobeerd: EBOS 100.0%
- 12:25:11 NA TE GAAN · Golfboei Copernicus Oostende, Mariakerke (BE): NO_TS_MO_OstendEasternPalisadeBuoy_202609, 2.5 km, 100.0% dekking; geprobeerd: 1
- 12:25:26 NA TE GAAN · METAR-station Scheveningen (NL): specificatie noemde EHRD; gekozen: EHRD (Rotterdam, 21.0 km, 100.0% dekking); geprobeerd: EHRD 100.0%
- 12:25:41 NA TE GAAN · Golfboei Copernicus Scheveningen (NL): NO_TS_MO_MaeslantkeringZeezijdeNoordMeetpaal_202609, 18.0 km, 99.9% dekking; geprobeerd: 1
- 12:25:58 NA TE GAAN · METAR-station Hossegor, La Gravière (FR): specificatie noemde LFBZ; gekozen: LFBZ (Biarritz-bayonne, 23.6 km, 100.0% dekking); geprobeerd: LFBZ 100.0%
- 12:26:13 NA TE GAAN · Golfboei Copernicus Hossegor, La Gravière (FR): IR_TS_MO_Donostia-buoy_202609, 47.1 km, 98.2% dekking; geprobeerd: 1
- 12:26:57 NA TE GAAN · METAR-station Nazaré, Praia do Norte (PT): specificatie noemde (geen station genoemd); gekozen: LPMR (Monte Real, 30.0 km, 92.6% dekking); geprobeerd: LPMR 92.6%
- 12:27:11 NA TE GAAN · Golfboei Copernicus Nazaré, Praia do Norte (PT): IR_TS_MO_6200199_202609, 12.0 km, 100.0% dekking; geprobeerd: 1
- 12:27:27 NA TE GAAN · METAR-station Tarifa, Los Lances (ES): specificatie noemde LXGB; gekozen: LEAG (Algeciras, 20.5 km, 100.0% dekking); geprobeerd: LEAG 100.0%
- 12:27:41 NA TE GAAN · Golfboei Copernicus Tarifa, Los Lances (ES): IR_TS_MO_Tarifa-coast-buoy_202609, 3.5 km, 99.3% dekking; geprobeerd: 1
- 12:27:55 NA TE GAAN · METAR-station Pozo Izquierdo, Gran Canaria (ES): specificatie noemde GCLP; gekozen: GCLP (Gran Canaria, 11.9 km, 100.0% dekking); geprobeerd: GCLP 100.0%
- 12:28:09 NA TE GAAN · Golfboei Copernicus Pozo Izquierdo, Gran Canaria (ES): IR_TS_MO_LasPalmas-coast-buoy_202609, 25.7 km, 99.2% dekking; geprobeerd: 1
- 12:28:38 NA TE GAAN · METAR-station Big Bay, Kaapstad (ZA): specificatie noemde FACT; gekozen: FACT (Cape Town, 23.5 km, 99.3% dekking); geprobeerd: FACT 99.3%
- 12:28:38 NA TE GAAN · Golfboei Copernicus Big Bay, Kaapstad (ZA): geen platform met VHM0 binnen 100 km met ≥70% dekking → 'geen golfmeting'; geprobeerd: 0
- 12:28:53 NA TE GAAN · METAR-station Manly, Sydney (AU): specificatie noemde YSSY; gekozen: YSSY (Sydney, 19.8 km, 99.3% dekking); geprobeerd: YSSY 99.3%
- 12:29:07 NA TE GAAN · Golfboei Copernicus Manly, Sydney (AU): GL_TS_MO_EXAU061_202609, 8.0 km, 99.9% dekking; geprobeerd: 1
- 12:29:09 NA TE GAAN · METAR-station Joaquina, Florianópolis (BR): specificatie noemde SBFL; gekozen: SBFL (Florianopolis, 10.8 km, 100.0% dekking); geprobeerd: SBFL 100.0%
- 12:29:09 NA TE GAAN · Golfboei Copernicus Joaquina, Florianópolis (BR): geen platform met VHM0 binnen 100 km met ≥70% dekking → 'geen golfmeting'; geprobeerd: 0
- 12:29:11 NA TE GAAN · METAR-station Uluwatu, Bali (ID): specificatie noemde WADD; gekozen: WADD (Denpasar, 11.5 km, 100.0% dekking); geprobeerd: WADD 100.0%
- 12:29:11 NA TE GAAN · Golfboei Copernicus Uluwatu, Bali (ID): geen platform met VHM0 binnen 100 km met ≥70% dekking → 'geen golfmeting'; geprobeerd: 0
- 12:29:11 NA TE GAAN · NDBC maandarchieven voor september: https://www.ndbc.noaa.gov/data/stdmet/Sep/<id>.txt; gaten aangevuld uit realtime2 (zie regels hierboven)
- 12:29:11 NA TE GAAN · Meethoogte anemometer per NDBC-boei: 46026: 4.1 m, 51205: niet gevonden, 41025: 4.1 m, 41009: 3.8 m (stationspagina NDBC)
- 12:29:11 NA TE GAAN · Copernicus: welke vlagwaarde betekent 'goed': gelezen uit flag_meanings in de bestanden: VHM0_QC good_data = 1, TEMP_QC good_data = 1, VTPK_QC good_data = 1, VTM02_QC good_data = 1, VMDR_QC good_data = 1
- 12:29:11 NA TE GAAN · Windvlagen in Copernicus In Situ: niet nodig: wind buiten de VS komt in deze proef van METAR, niet van Copernicus
- 12:29:11 NA TE GAAN · Ruwheidslengte z0 voor de windhoogtecorrectie: z0 = 0.0002 m (open zee); u10 = uz · ln(10/z0) / ln(z/z0); enkel op NDBC-wind en -vlagen, METAR meet al op 10 m
- 12:29:11 NA TE GAAN · IEM-parameters: station, data=sknt,drct,gust, sts, ets, tz=Etc/UTC, format=onlycomma, latlon, missing, report_type=3,4 (routine en speciale METAR), volgens /cgi-bin/request/asos.py?help; 1 s wachttijd per aanvraag
- 12:29:11 NA TE GAAN · Licentie METAR-downloads via IEM: niet vermeld op de helppagina; nog na te vragen
- 12:29:11 NA TE GAAN · Klassen per sport uit stap 1: nog niet beschikbaar; voorlopige klassen uit de specificatie gebruikt
- 12:29:11 Stap 2: voorspellingen ophalen
- 12:29:25 Ocean Beach, San Francisco (VS): 38 foutregels
- 12:29:40 Ho'okipa, Maui (VS): 38 foutregels
- 12:29:55 Cape Hatteras, Buxton (VS): 38 foutregels
- 12:30:06 Cocoa Beach, Florida (VS): 37 foutregels
- 12:30:21 Oostende, Mariakerke (BE): 29 foutregels
- 12:30:35 Scheveningen (NL): 34 foutregels
- 12:30:51 Hossegor, La Gravière (FR): 38 foutregels
- 12:31:05 Nazaré, Praia do Norte (PT): 34 foutregels
- 12:31:21 Tarifa, Los Lances (ES): 38 foutregels
- 12:31:36 Pozo Izquierdo, Gran Canaria (ES): 38 foutregels
- 12:31:44 Big Bay, Kaapstad (ZA): 24 foutregels
- 12:31:55 Manly, Sydney (AU): 33 foutregels
- 12:32:03 Joaquina, Florianópolis (BR): 24 foutregels
- 12:32:12 Uluwatu, Bali (ID): 24 foutregels
- 12:32:13 NA TE GAAN · Looptijd binnen een uur: 8.0 minuten
