// Mijlpaal 0: één echte aanroep van Neaps, met de TICON-4-constanten uit
// @neaps/tide-database. Schrijft tests/fixtures/probe/neaps_stations.json en
// neaps_cascais.json en werkt manifest.json bij.
import { readFileSync, writeFileSync, existsSync } from 'node:fs'
import { stationsNear, findStation } from 'neaps'

const OUT = new URL('../../tests/fixtures/probe/', import.meta.url)

// Alle stations langs het vasteland (straal 450 km rond het midden).
const stations = stationsNear({ latitude: 39.4, longitude: -8.8, maxDistance: 450_000, limit: 100 })
  .map((s) => ({
    id: s.id, naam: s.name, land: s.country, lat: s.latitude, lon: s.longitude,
    bron: s.source?.name, licentie: s.license?.type, commercieel: s.license?.commercial_use,
    datums: s.datums, chart_datum: s.chart_datum, type: s.type,
  }))
  .filter((s) => s.land === 'Portugal')
writeFileSync(new URL('neaps_stations.json', OUT), JSON.stringify(stations, null, 1) + '\n')

// Hoog- en laagwater voor Cascais over twee dagen, in UTC, tegenover MSL.
const cascais = findStation('ticon/cascais-209-prt-uhslc_fd')
const p = cascais.getExtremesPrediction({
  start: new Date('2026-10-05T00:00:00Z'), end: new Date('2026-10-07T00:00:00Z'), datum: 'MSL',
})
const fixture = {
  station: p.station.id, datum: p.datum, units: p.units,
  extremes: p.extremes.map((e) => ({ time: new Date(e.time).toISOString(), level: Math.round(e.level * 1000) / 1000, high: e.high, label: e.label })),
}
writeFileSync(new URL('neaps_cascais.json', OUT), JSON.stringify(fixture, null, 1) + '\n')

const mpath = new URL('manifest.json', OUT)
const manifest = existsSync(mpath) ? JSON.parse(readFileSync(mpath, 'utf8')) : {}
const op = new Date().toISOString().slice(0, 16) + 'Z'
manifest.neaps = { status: 'ok', op, via: process.env.PROBE_VIA ?? 'lokaal' }
writeFileSync(mpath, JSON.stringify(Object.fromEntries(Object.entries(manifest).sort()), null, 1) + '\n')
console.log(`OK    neaps: ${stations.length} stations, ${fixture.extremes.length} extremen in Cascais`)
