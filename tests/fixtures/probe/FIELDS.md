# Veldnamen per bron

Gegenereerd door `pipeline/probe/probe.py`. Niet met de hand bewerken.

## copernicus_ibi

Status: ok (2026-10-06T07:58Z, via github-actions)

```
dataset_id: str
punt: dict
punt.latitude: float
punt.longitude: float
variabelen: dict
variabelen.VCMX: dict
variabelen.VCMX.long_name: str
variabelen.VCMX.units: str
variabelen.VHM0: dict
variabelen.VHM0.long_name: str
variabelen.VHM0.units: str
variabelen.VHM0_SW1: dict
variabelen.VHM0_SW1.long_name: str
variabelen.VHM0_SW1.units: str
variabelen.VHM0_SW2: dict
variabelen.VHM0_SW2.long_name: str
variabelen.VHM0_SW2.units: str
variabelen.VHM0_WW: dict
variabelen.VHM0_WW.long_name: str
variabelen.VHM0_WW.units: str
variabelen.VMDR: dict
variabelen.VMDR.long_name: str
variabelen.VMDR.units: str
variabelen.VMDR_SW1: dict
variabelen.VMDR_SW1.long_name: str
variabelen.VMDR_SW1.units: str
variabelen.VMDR_SW2: dict
variabelen.VMDR_SW2.long_name: str
variabelen.VMDR_SW2.units: str
variabelen.VMDR_WW: dict
variabelen.VMDR_WW.long_name: str
variabelen.VMDR_WW.units: str
variabelen.VMXL: dict
variabelen.VMXL.long_name: str
variabelen.VMXL.units: str
variabelen.VPED: dict
variabelen.VPED.long_name: str
variabelen.VPED.units: str
variabelen.VSDX: dict
variabelen.VSDX.long_name: str
variabelen.VSDX.units: str
variabelen.VSDY: dict
variabelen.VSDY.long_name: str
variabelen.VSDY.units: str
variabelen.VTM01_SW1: dict
variabelen.VTM01_SW1.long_name: str
variabelen.VTM01_SW1.units: str
variabelen.VTM01_SW2: dict
variabelen.VTM01_SW2.long_name: str
variabelen.VTM01_SW2.units: str
variabelen.VTM01_WW: dict
variabelen.VTM01_WW.long_name: str
variabelen.VTM01_WW.units: str
variabelen.VTM02: dict
variabelen.VTM02.long_name: str
variabelen.VTM02.units: str
variabelen.VTM10: dict
variabelen.VTM10.long_name: str
variabelen.VTM10.units: str
variabelen.VTPK: dict
variabelen.VTPK.long_name: str
variabelen.VTPK.units: str
time: list
VCMX: list
VHM0: list
VHM0_SW1: list
VHM0_SW2: list
VHM0_WW: list
VMDR: list
VMDR_SW1: list
VMDR_SW2: list
VMDR_WW: list
VMXL: list
VPED: list
VSDX: list
VSDY: list
VTM01_SW1: list
VTM01_SW2: list
VTM01_WW: list
VTM02: list
VTM10: list
VTPK: list
```

## emodnet_buoy

Status: fout (2026-10-06T07:58Z, via ?)

Reden: RuntimeError: {"catalogus": "ERD_EP_WAVES_INSITU_METADATA", "platformen": [{"PLATFORMCODE": "6200199", "call_name": "Monican02", "latitude": 39.560001373291016, "longitude": -9.210000038146973, "lastDateObservation": "2025-05-22T11:00:00Z"}, {"PLATFORMCODE": "6200084", "call_name": "Cabo Silleiro buoy", "latitude": 42.119998931884766, "longitude": -9.430000305175781, "lastDateObservation": "2025-10-20T10:00:00Z"}, {"PLATFORMCODE": "6201081", "call_name": "Sines", "latitude": 37.67499923706055, "longitude": -9.725000381469727, "lastDateObservation": "2025-10-20T10:00:00Z"}, {"PLATFORMCODE": "6200192", "call_name": "Monican01", "latitude": 39.5099983215332, "longitude": -9.640000343322754, "lastDateObservation": "2025-10-01T14:00:00Z"}, {"PLATFORMCODE": "6200191", "call_name": "Raia01", "latitude": 41.150001525878906, "longitude": -9.579999923706055, "lastDateObservation": "2025-02-12T15:00:00Z"}, {"PLATFORMCODE": "Sines-coast-buoy", "call_name": "Sines coastal buoy", "latitude": 37.921112060546875, "longitude": -8.928889274597168, "lastDateObservation": "2025-10-20T08:26:44Z"}, {"PLATFORMCODE": "Leixoes-coast-buoy", "call_name": "Leixoes coastal buoy", "latitude": 41.31666564941406, "longitude": -8.983333587646484, "lastDateObservation": "2025-10-20T07:02:13Z"}, {"PLATFORMCODE": "Faro-coast-buoy", "call_name": "Faro coastal buoy", "latitude": 36.90472412109375, "longitude": -7.898333549499512, "lastDateObservation": "2025-10-20T04:55:24Z"}, {"PLATFORMCODE": "6201079", "call_name": "Datawell", "latitude": 36.904361724853516, "longitude": -7.899449825286865, "lastDateObservation": "2025-10-20T04:25:00Z"}, {"PLATFORMCODE": "6201077", "call_name": "Datawell", "latitude": 41.31631088256836, "longitude": -8.983099937438965, "lastDateObservation": "2025-10-19T23:32:00Z"}], "datasets_per_platform": {"6201081": ["ERD_EP_TS_RELH_NRT_METADATA"]}, "geprobeerd": ["ERD_EP_TS_VHM0_NRT_METADATA: Remote end closed connection without response", "zoek 6200199: HTTP Error 404: ", "zoek 6200084: HTTP Error 404: ", "zoek 6200192: HTTP Error 404: ", "zoek 6200191: HTTP Error 404: ", "zoek Sines-coast-buoy: HTTP Error 404: ", "zoek Leixoes-coast-buoy: HTTP Error 404: ", "zoek Faro-coast-buoy: HTTP Error 404: ", "zoek 6201079: HTTP Error 404: ", "zoek 6201077: HTTP Error 404: "]}

## emodnet_platforms

Status: ok (2026-10-06T07:58Z, via github-actions)

```
[].PLATFORMCODE: str
[].call_name: str
[].latitude: float
[].longitude: float
[].DataFeatureType: str
[].firstDateObservation: str
[].lastDateObservation: str
[].parameters_group_longname: str
[].parameters_group_P02: str
[].parameters: str
[].parameters_P01: str
[].WMO: int
[].BEST_PRACTICES_DOI: str
[].DATA_DOI: str
[].data_owner_longname: str
[].data_owner_country_code: str
[].data_owner_country_longname: str
[].data_owner_EDMO: NoneType
[].data_assembly_center_longname: str
[].platform_type_longname: str
[].platform_type_SDNL06: str
[].platformpage_link: str
[].integrator_id: str
```

## emodnet_search

Status: ok (2026-10-06T07:58Z, via github-actions)

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

Status: fout (2026-10-06T07:58Z, via ?)

Reden: URLError: <urlopen error [Errno -2] Name or service not known>

## ipma_observations

Status: ok (2026-10-06T07:58Z, via github-actions)

```
_ingekort: str
2026-10-06T07:00: dict
2026-10-06T07:00.{<227 sleutels, bv. 1210881>}
2026-10-06T07:00.{*}.intensidadeVentoKM: float
2026-10-06T07:00.{*}.temperatura: float
2026-10-06T07:00.{*}.radiacao: float
2026-10-06T07:00.{*}.idDireccVento: int
2026-10-06T07:00.{*}.precAcumulada: float
2026-10-06T07:00.{*}.intensidadeVento: float
2026-10-06T07:00.{*}.humidade: float
2026-10-06T07:00.{*}.pressao: float
```

## ipma_stations

Status: ok (2026-10-06T07:58Z, via github-actions)

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

Status: ok (2026-10-06T07:58Z, via github-actions)

```
[].text: str
[].awarenessTypeName: str
[].idAreaAviso: str
[].startTime: str
[].awarenessLevelID: str
[].endTime: str
```

## neaps

Status: ok (2026-10-06T07:15Z, via github-actions)

## openfreemap_style

Status: ok (2026-10-06T07:58Z, via github-actions)

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

Status: ok (2026-10-06T07:58Z, via github-actions)

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

Status: ok (2026-10-06T07:58Z, via github-actions)

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

Status: ok (2026-10-06T07:58Z, via github-actions)

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
