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
| `wave_peak_period`, `swell_wave_peak_period`, `wind_wave_peak_period` | — | **Leeg bij GFS-Wave** (`null`, eenheid `"undefined"`) |

- Golfrichting: waar de golven vandaan komen.
- Een ontbrekende deelgolf staat op `0`, niet op `null`.
- De drie deelgolven samen liggen tot 12 procent onder `wave_height` (`OPEN.md` punt 10).

## Copernicus Marine IBI

Dataset `cmems_mod_ibi_wav_anfc_0.027deg_PT1H-i`, via de Python-toolbox `copernicusmarine` (`open_dataset`, uitsnede rond één punt). Bevestigd op 6 oktober 2026: uurwaarden, raster van ongeveer 3 km.

| Variabele | Eenheid | Betekenis |
|---|---|---|
| `VHM0` | m | Significante golfhoogte, totale zee |
| `VTPK` | s | Piekperiode, totale zee |
| `VTM02`, `VTM10` | s | Gemiddelde periodes |
| `VMDR`, `VPED` | ° | Gemiddelde richting en richting bij de piek (waar de golven vandaan komen) |
| `VHM0_SW1`, `VTM01_SW1`, `VMDR_SW1` | m, s, ° | Eerste deining |
| `VHM0_SW2`, `VTM01_SW2`, `VMDR_SW2` | m, s, ° | Tweede deining |
| `VHM0_WW`, `VTM01_WW`, `VMDR_WW` | m, s, ° | Windgolf |
| `VCMX`, `VMXL` | m | Hoogste golf en hoogste top |
| `VSDX`, `VSDY` | m/s | Stokesdrift |

Ook hier zijn de periodes per deelgolf gemiddelde periodes (`VTM01`), geen piekperiodes.

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
- `stations.json`: GeoJSON-lijst; `properties.idEstacao` (getal), `properties.localEstacao` (naam), `geometry.coordinates` [lon, lat]. 227 stations.
- `observations.json`: `{tijdstip: {idEstacao: waarneming of null}}`, 24 uurlijkse tijdstippen in UTC zonder zone.
- Velden per waarneming: `intensidadeVento` (m/s), `intensidadeVentoKM` (km/u), `idDireccVento` (sector 0 tot 9, zie `OPEN.md` punt 11), `temperatura`, `humidade`, `pressao`, `precAcumulada`, `radiacao`. `-99` = ontbrekend.

## EMODnet Physics ERDDAP

`https://data-erddap.emodnet-physics.eu/erddap/`. De proef zoekt via `search/advanced.json` en leest metingen via `tabledap/{datasetID}.json`. Dataset-ID nog onbekend: `OPEN.md` punt 3.

## Instituto Hidrográfico, OGC API

`api-features.hidrografico.pt` bestaat niet in DNS (`OPEN.md` punt 4).

## OpenFreeMap

Stijl `https://tiles.openfreemap.org/styles/liberty`: MapLibre-stijl versie 8, vectorbron `openmaptiles` (`https://tiles.openfreemap.org/planet`), 111 lagen. Rechtstreeks bruikbaar in MapLibre GL JS, zonder sleutel.
