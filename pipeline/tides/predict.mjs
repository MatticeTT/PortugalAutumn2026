// M2: hoog- en laagwater voor de zeven Portugese peilstations, 2026 en 2027.
// Harmonische voorspelling met Neaps en de TICON-4-constanten (PLAN.md 3.2).
//
// Hoogtes tegenover het Zero Hidrográfico: MSL + 2,00 m (OPEN.md punt 8).
// Tijden in UTC. Schrijft data/tides/stations.json:
//   { stations: [{ id, naam, lat, lon, licentie, extremen: [[minuten sinds 1970 UTC, hoogte in cm, 1 = hoog / 0 = laag], ...] }] }
import { mkdirSync, writeFileSync } from 'node:fs'
import { findStation } from 'neaps'

export const STATIONS = [
  ['viana', 'ticon/vianadocastelotg-via-prt-cmems', 'Viana do Castelo'],
  ['leixoes', 'ticon/leixoestg-lei-prt-cmems', 'Leixões'],
  ['nazare', 'ticon/nazaretg-naz-prt-cmems', 'Nazaré'],
  ['peniche', 'ticon/penichetg-pen-prt-cmems', 'Peniche'],
  ['cascais', 'ticon/cascais-209-prt-uhslc_fd', 'Cascais'],
  ['sines', 'ticon/sinestg-sin-prt-cmems', 'Sines'],
  ['lagos', 'ticon/lagos_algarve-723a-prt-uhslc_rq', 'Lagos'],
]
const ZH_ONDER_MSL = 2.0
const START = new Date('2026-01-01T00:00:00Z')
const END = new Date('2028-01-01T00:00:00Z')

const out = { bron: 'Neaps + TICON-4 (DOI 10.17882/109129)', datum: 'Zero Hidrográfico = MSL - 2,00 m',
  tijd: 'UTC', van: START.toISOString(), tot: END.toISOString(), stations: [] }
for (const [key, id, naam] of STATIONS) {
  const s = findStation(id)
  const { extremes } = s.getExtremesPrediction({ start: START, end: END, datum: 'MSL' })
  out.stations.push({
    id: key, neaps_id: id, naam, lat: s.latitude, lon: s.longitude, licentie: s.license.type,
    extremen: extremes.map((e) => [Math.round(new Date(e.time).getTime() / 60000),
      Math.round((e.level + ZH_ONDER_MSL) * 100), e.high ? 1 : 0]),
  })
}
const dir = new URL('../../data/tides/', import.meta.url)
mkdirSync(dir, { recursive: true })
writeFileSync(new URL('stations.json', dir), JSON.stringify(out) + '\n')
console.log(out.stations.map((s) => `${s.naam}: ${s.extremen.length}`).join(', '))
