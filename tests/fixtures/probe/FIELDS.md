# Veldnamen per bron

Gegenereerd door `pipeline/probe/probe.py`. Niet met de hand bewerken.

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

## neaps

Status: ok (2026-10-05T14:35Z, via lokaal)

## openmeteo_gfs_wind

Status: fout (2026-10-05T14:38Z, via ?)

Reden: URLError: <urlopen error Tunnel connection failed: 403 Forbidden>

## openmeteo_ecmwf_wind

Status: fout (2026-10-05T14:38Z, via ?)

Reden: URLError: <urlopen error Tunnel connection failed: 403 Forbidden>

## openmeteo_gfswave

Status: fout (2026-10-05T14:38Z, via ?)

Reden: URLError: <urlopen error Tunnel connection failed: 403 Forbidden>

## copernicus_ibi

Status: overgeslagen (2026-10-05T14:38Z, via ?)

Reden: geen Copernicus-account in de omgeving (COPERNICUSMARINE_SERVICE_USERNAME/PASSWORD)

## emodnet_search

Status: fout (2026-10-05T14:38Z, via ?)

Reden: URLError: <urlopen error Tunnel connection failed: 403 Forbidden>

## emodnet_buoy

Status: fout (2026-10-05T14:38Z, via ?)

Reden: URLError: <urlopen error Tunnel connection failed: 403 Forbidden>

## ipma_warnings

Status: fout (2026-10-05T14:38Z, via ?)

Reden: URLError: <urlopen error Tunnel connection failed: 403 Forbidden>

## ipma_stations

Status: fout (2026-10-05T14:38Z, via ?)

Reden: URLError: <urlopen error Tunnel connection failed: 403 Forbidden>

## ipma_observations

Status: fout (2026-10-05T14:38Z, via ?)

Reden: URLError: <urlopen error Tunnel connection failed: 403 Forbidden>

## hidrografico_collections

Status: fout (2026-10-05T14:38Z, via ?)

Reden: URLError: <urlopen error Tunnel connection failed: 403 Forbidden>

## openfreemap_style

Status: fout (2026-10-05T14:38Z, via ?)

Reden: URLError: <urlopen error Tunnel connection failed: 403 Forbidden>
