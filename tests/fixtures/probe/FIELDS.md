# Veldnamen per bron

Gegenereerd door `pipeline/probe/probe.py`. Niet met de hand bewerken.

## copernicus_ibi

Status: overgeslagen (2026-10-05T14:40Z, via ?)

Reden: geen Copernicus-account in de omgeving (COPERNICUSMARINE_SERVICE_USERNAME/PASSWORD)

## emodnet_buoy

Status: fout (2026-10-05T14:40Z, via ?)

Reden: RuntimeError: geen bruikbare dataset; geprobeerd: ERD_EP_TS_VMDR_NRT_METADATA: geen golfvariabelen (PLATFORMCODE, call_name, latitude, longitude, DataFeatureType, firstDateObservation, lastDateObservation, parameters_group_longname, parameters_group_P02, parameters, parameters_P01, WMO) | ERD_EP_TS_SINC_NRT_METADATA: geen golfvariabelen (PLATFORMCODE, call_name, latitude, longitude, DataFeatureType, firstDateObservation, lastDateObservation, parameters_group_longname, parameters_group_P02, param

## emodnet_search

Status: ok (2026-10-05T14:40Z, via github-actions)

```
table: dict
table.columnNames: list
table.columnTypes: list
table.rows: list
```

## firecrawl_ipma_warnings

Status: ok (2026-10-05T14:31Z, via firecrawl (sandbox blokkeert de host))

```
_ingekort: str
records: list
records.[].text: str
records.[].awarenessTypeName: str
records.[].idAreaAviso: str
records.[].startTime: str
records.[].awarenessLevelID: str
records.[].endTime: str
```

## firecrawl_openmeteo_gfswave

Status: ok (2026-10-05T14:31Z, via firecrawl (sandbox blokkeert de host))

```
latitude: float
longitude: float
generationtime_ms: float
utc_offset_seconds: int
timezone: str
timezone_abbreviation: str
elevation: float
_aanvraag: str
hourly_units: dict
hourly_units.time: str
hourly_units.wave_height: str
hourly_units.wave_period: str
hourly_units.wave_direction: str
hourly_units.swell_wave_height: str
hourly_units.swell_wave_period: str
hourly_units.swell_wave_peak_period: str
hourly_units.swell_wave_direction: str
hourly_units.secondary_swell_wave_height: str
hourly_units.secondary_swell_wave_period: str
hourly_units.secondary_swell_wave_direction: str
hourly_units.wind_wave_height: str
hourly_units.wind_wave_period: str
hourly_units.wind_wave_direction: str
hourly: dict
hourly.time: list
hourly.wave_height: list
hourly.wave_period: list
hourly.wave_direction: list
hourly.swell_wave_height: list
hourly.swell_wave_period: list
hourly.swell_wave_peak_period: list
hourly.swell_wave_direction: list
hourly.secondary_swell_wave_height: list
hourly.secondary_swell_wave_period: list
hourly.secondary_swell_wave_direction: list
hourly.wind_wave_height: list
hourly.wind_wave_period: list
hourly.wind_wave_direction: list
```

## firecrawl_openmeteo_wind_3modellen

Status: ok (2026-10-05T14:31Z, via firecrawl (sandbox blokkeert de host))

```
latitude: float
longitude: float
generationtime_ms: float
utc_offset_seconds: int
timezone: str
timezone_abbreviation: str
elevation: float
_aanvraag: str
hourly_units: dict
hourly_units.time: str
hourly_units.wind_speed_10m_gfs_seamless: str
hourly_units.wind_gusts_10m_gfs_seamless: str
hourly_units.wind_direction_10m_gfs_seamless: str
hourly_units.wind_speed_10m_ecmwf_ifs: str
hourly_units.wind_gusts_10m_ecmwf_ifs: str
hourly_units.wind_direction_10m_ecmwf_ifs: str
hourly_units.wind_speed_10m_ecmwf_ifs025: str
hourly_units.wind_gusts_10m_ecmwf_ifs025: str
hourly_units.wind_direction_10m_ecmwf_ifs025: str
hourly: dict
hourly.time: list
hourly.wind_speed_10m_gfs_seamless: list
hourly.wind_gusts_10m_gfs_seamless: list
hourly.wind_direction_10m_gfs_seamless: list
hourly.wind_speed_10m_ecmwf_ifs: list
hourly.wind_gusts_10m_ecmwf_ifs: list
hourly.wind_direction_10m_ecmwf_ifs: list
hourly.wind_speed_10m_ecmwf_ifs025: list
hourly.wind_gusts_10m_ecmwf_ifs025: list
hourly.wind_direction_10m_ecmwf_ifs025: list
```

## hidrografico_collections

Status: fout (2026-10-05T14:40Z, via ?)

Reden: URLError: <urlopen error [Errno -2] Name or service not known>

## ipma_observations

Status: ok (2026-10-05T14:40Z, via github-actions)

```
_ingekort: str
2026-10-05T14:00: dict
2026-10-05T14:00.{<227 sleutels, bv. 1210881>}
2026-10-05T14:00.{*}.intensidadeVentoKM: float
2026-10-05T14:00.{*}.temperatura: float
2026-10-05T14:00.{*}.radiacao: float
2026-10-05T14:00.{*}.idDireccVento: int
2026-10-05T14:00.{*}.precAcumulada: float
2026-10-05T14:00.{*}.intensidadeVento: float
2026-10-05T14:00.{*}.humidade: float
2026-10-05T14:00.{*}.pressao: float
```

## ipma_stations

Status: ok (2026-10-05T14:40Z, via github-actions)

```
[].geometry: dict
[].geometry.type: str
[].geometry.coordinates: list
[].type: str
[].properties: dict
[].properties.idEstacao: int
[].properties.localEstacao: str
```

## ipma_warnings

Status: ok (2026-10-05T14:40Z, via github-actions)

```
[].text: str
[].awarenessTypeName: str
[].idAreaAviso: str
[].startTime: str
[].awarenessLevelID: str
[].endTime: str
```

## neaps

Status: ok (2026-10-05T14:35Z, via lokaal)

## openfreemap_style

Status: ok (2026-10-05T14:40Z, via github-actions)

```
version: int
sources: dict
sources.ne2_shaded: dict
sources.ne2_shaded.maxzoom: int
sources.ne2_shaded.tileSize: int
sources.ne2_shaded.tiles: list
sources.ne2_shaded.type: str
sources.openmaptiles: dict
sources.openmaptiles.type: str
sources.openmaptiles.url: str
glyphs: str
sprite: str
_layers: int
```

## openmeteo_ecmwf_wind

Status: ok (2026-10-05T14:40Z, via github-actions)

```
latitude: float
longitude: float
generationtime_ms: float
utc_offset_seconds: int
timezone: str
timezone_abbreviation: str
elevation: float
hourly_units: dict
hourly_units.time: str
hourly_units.wind_speed_10m: str
hourly_units.wind_gusts_10m: str
hourly_units.wind_direction_10m: str
hourly: dict
hourly.time: list
hourly.wind_speed_10m: list
hourly.wind_gusts_10m: list
hourly.wind_direction_10m: list
```

## openmeteo_gfs_wind

Status: ok (2026-10-05T14:40Z, via github-actions)

```
latitude: float
longitude: float
generationtime_ms: float
utc_offset_seconds: int
timezone: str
timezone_abbreviation: str
elevation: float
hourly_units: dict
hourly_units.time: str
hourly_units.wind_speed_10m: str
hourly_units.wind_gusts_10m: str
hourly_units.wind_direction_10m: str
hourly: dict
hourly.time: list
hourly.wind_speed_10m: list
hourly.wind_gusts_10m: list
hourly.wind_direction_10m: list
```

## openmeteo_gfswave

Status: ok (2026-10-05T14:40Z, via github-actions)

```
latitude: float
longitude: float
generationtime_ms: float
utc_offset_seconds: int
timezone: str
timezone_abbreviation: str
elevation: float
hourly_units: dict
hourly_units.time: str
hourly_units.wave_height: str
hourly_units.wave_period: str
hourly_units.wave_peak_period: str
hourly_units.wave_direction: str
hourly_units.swell_wave_height: str
hourly_units.swell_wave_period: str
hourly_units.swell_wave_peak_period: str
hourly_units.swell_wave_direction: str
hourly_units.secondary_swell_wave_height: str
hourly_units.secondary_swell_wave_period: str
hourly_units.secondary_swell_wave_direction: str
hourly_units.wind_wave_height: str
hourly_units.wind_wave_period: str
hourly_units.wind_wave_peak_period: str
hourly_units.wind_wave_direction: str
hourly: dict
hourly.time: list
hourly.wave_height: list
hourly.wave_period: list
hourly.wave_peak_period: list
hourly.wave_direction: list
hourly.swell_wave_height: list
hourly.swell_wave_period: list
hourly.swell_wave_peak_period: list
hourly.swell_wave_direction: list
hourly.secondary_swell_wave_height: list
hourly.secondary_swell_wave_period: list
hourly.secondary_swell_wave_direction: list
hourly.wind_wave_height: list
hourly.wind_wave_period: list
hourly.wind_wave_peak_period: list
hourly.wind_wave_direction: list
```
