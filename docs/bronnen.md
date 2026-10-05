# Bronnen: aanroepen en veldnamen (M0)

De volledige lijst van sleutels per antwoord staat in `tests/fixtures/probe/FIELDS.md` (gegenereerd). Hier staat wat de velden betekenen en wat de proef heeft vastgesteld.

## Open-Meteo, wind

`GET https://api.open-meteo.com/v1/forecast`

| Parameter | Waarde |
|---|---|
| `hourly` | `wind_speed_10m,wind_gusts_10m,wind_direction_10m` |
| `models` | `gfs_seamless` (Windguru-stand), `ecmwf_ifs` (9 km) |
| `wind_speed_unit` | `kn` |
| `timezone` | `UTC` |

- Met één model heten de velden `hourly.wind_speed_10m` enz. Met meer modellen tegelijk krijgt elk veld het model als achtervoegsel: `wind_speed_10m_gfs_seamless`, `wind_speed_10m_ecmwf_ifs`.
- `hourly.time`: ISO-tijd zonder zone, in de gevraagde `timezone`.
- `wind_direction_10m`: graden, waar de wind **vandaan** komt.
- **Bevestigd op 5 oktober 2026:** `ecmwf_ifs` is een geldige model-id en geeft uurwaarden. `ecmwf_ifs025` (25 km) bestaat ook.
- De teruggegeven `latitude`/`longitude` is het rasterpunt van het model, niet het gevraagde punt.

## Open-Meteo Marine, golven

`GET https://marine-api.open-meteo.com/v1/marine` met `models=ncep_gfswave016`.

| Veld | Eenheid | Betekenis |
|---|---|---|
| `wave_height`, `wave_period`, `wave_direction` | m, s, ° | Totale zee |
| `swell_wave_height`, `_period`, `_direction` | m, s, ° | Eerste deining |
| `secondary_swell_wave_height`, `_period`, `_direction` | m, s, ° | Tweede deining |
| `wind_wave_height`, `_period`, `_direction` | m, s, ° | Windgolf |
| `swell_wave_peak_period` | — | **Leeg bij GFS-Wave** (`null`, eenheid `"undefined"`) |

- Golfrichting: waar de golven vandaan komen.
- Getoetst: `wave_height` is binnen 0,1 m gelijk aan de wortel van de som van de kwadraten van de drie deelgolven.

## Copernicus Marine IBI

Dataset `cmems_mod_ibi_wav_anfc_0.027deg_PT1H-i`, via de Python-toolbox `copernicusmarine` (`open_dataset`, uitsnede rond één punt). Variabelen volgens de productbeschrijving, te bevestigen bij de eerste run: `VHM0`, `VTPK`, `VTM02`, `VMDR`, `VHM0_SW1`, `VTM01_SW1`, `VMDR_SW1`, `VHM0_SW2`, `VTM01_SW2`, `VMDR_SW2`, `VHM0_WW`, `VTM01_WW`, `VMDR_WW`. Nog niet aangeroepen: zie `OPEN.md` punt 2.

## Neaps (getij)

npm-pakket `neaps` met `@neaps/tide-database` (TICON-4). Rekent offline.

- `findStation(id)` → station; `station.getExtremesPrediction({start, end, datum})` → `{datum, units, station, distance, extremes[]}`.
- `extremes[]`: `time` (Date, UTC), `level` (m tegenover `datum`), `high`/`low` (bool), `label`.
- Station-ID's op het vasteland:

| Station | ID | Licentie |
|---|---|---|
| Viana do Castelo | `ticon/vianadocastelotg-via-prt-cmems` | CC BY-NC 4.0 |
| Leixões | `ticon/leixoestg-lei-prt-cmems` | CC BY-NC 4.0 |
| Nazaré | `ticon/nazaretg-naz-prt-cmems` | CC BY-NC 4.0 |
| Peniche | `ticon/penichetg-pen-prt-cmems` | CC BY-NC 4.0 |
| Cascais | `ticon/cascais-209-prt-uhslc_fd` | CC BY 4.0 |
| Sines | `ticon/sinestg-sin-prt-cmems` | CC BY-NC 4.0 |
| Lagos | `ticon/lagos_algarve-723a-prt-uhslc_rq` | CC BY 4.0 |

- Beschikbare datums per station: HAT, MHHW, MHW, MSL, MTL, MLW, MLLW, LAT, MHWS, MLWS. Gebruik `MSL` en tel 2,00 m op voor het Zero Hidrográfico (`OPEN.md` punt 8).

## IPMA, waarschuwingen

`GET https://api.ipma.pt/open-data/forecast/warnings/warnings_www.json` → lijst van records.

| Veld | Voorbeeld | Betekenis |
|---|---|---|
| `idAreaAviso` | `FAR` | District (drie letters), zie `OPEN.md` punt 6 |
| `awarenessTypeName` | `Agitação Marítima`, `Vento`, `Trovoada`, … | Soort waarschuwing; acht soorten per district |
| `awarenessLevelID` | `green`, `yellow`, `orange`, `red` | Niveau |
| `startTime`, `endTime` | `2026-10-05T10:48:00` | Lokale tijd zonder zone **[onbevestigd]** |
| `text` | | Toelichting, leeg bij groen |

## IPMA, stations

- `observation/meteorology/stations/stations.json`: lijst van stations (GeoJSON).
- `observation/meteorology/stations/observations.json`: `{tijdstip: {stationId: {...}}}`. Velden volgen na de eerste run.

## EMODnet Physics ERDDAP

`https://data-erddap.emodnet-physics.eu/erddap/`. De proef zoekt via `search/advanced.json` en leest metingen via `tabledap/{datasetID}.json`. Dataset-ID nog onbekend: `OPEN.md` punt 3.

## Instituto Hidrográfico, OGC API

`GET https://api-features.hidrografico.pt/collections?f=json`. Lijst van collecties volgt na de eerste run.

## OpenFreeMap

Stijl `https://tiles.openfreemap.org/styles/liberty`, rechtstreeks bruikbaar in MapLibre GL JS.
