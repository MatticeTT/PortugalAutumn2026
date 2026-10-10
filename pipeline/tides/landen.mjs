// Getij voor Spanje, Frankrijk, België en Nederland: hoog- en laagwater voor elk TICON-4-station langs die kusten,
// 2026 en 2027, met Neaps (zelfde bron en methode als predict.mjs voor Portugal).
// Hoogtes in cm boven het laagste laagwater van 2026-2027 van dat station (zoals een kaartnul, ongeveer LAT):
// het rekenmodel gebruikt alleen het verval en de stand tussen laag- en hoogwater, dus het nulpunt verandert
// niets aan de berekening; de fiche tekent er het peil mee.
// Schrijft data/tides/stations_landen.json (zelfde vorm als stations.json).
import { mkdirSync, writeFileSync } from 'node:fs'
import { stationsNear } from 'neaps'

const LANDEN = { Spain: 'es', France: 'fr', Belgium: 'be', Netherlands: 'nl' }
// Punten langs de kusten; met een straal van 400 km vallen alle stations van die landen erbinnen.
const ZOEK = [[43.5, -3], [41.5, 2.5], [37, -1], [36.5, -5], [42.5, -8.9], [47.5, -3.5], [49.5, 0], [43.3, 5],
  [45.5, -1.2], [51.2, 2.9], [50.8, 1.6], [43.4, 3.6], [52.3, 4.5], [53.2, 5.5], [53.4, 6.6]]
const START = new Date('2026-01-01T00:00:00Z')
const END = new Date('2028-01-01T00:00:00Z')

const gevonden = new Map()
for (const [la, lo] of ZOEK) {
  for (const s of stationsNear({ latitude: la, longitude: lo, maxDistance: 400_000, limit: 400 })) {
    if (LANDEN[s.country] && s.type === 'reference') gevonden.set(s.id, s)
  }
}
const out = { bron: 'Neaps + TICON-4 (DOI 10.17882/109129)', datum: 'laagste laagwater 2026-2027 per station', tijd: 'UTC',
  van: START.toISOString(), tot: END.toISOString(), stations: [] }
for (const s of [...gevonden.values()].sort((a, b) => a.id.localeCompare(b.id))) {
  let extremes
  try {
    ({ extremes } = s.getExtremesPrediction({ start: START, end: END, datum: 'MSL' }))
  } catch (e) {
    console.log(`overgeslagen ${s.id}: ${e.message}`)
    continue
  }
  if (!extremes?.length) continue
  const nul = Math.min(...extremes.map((e) => e.level))
  out.stations.push({
    id: s.id.replace(/^ticon\//, ''), neaps_id: s.id, naam: s.name, land: LANDEN[s.country],
    lat: s.latitude, lon: s.longitude, licentie: s.license.type,
    extremen: extremes.map((e) => [Math.round(new Date(e.time).getTime() / 60000), Math.round((e.level - nul) * 100), e.high ? 1 : 0]),
  })
}
const dir = new URL('../../data/tides/', import.meta.url)
mkdirSync(dir, { recursive: true })
writeFileSync(new URL('stations_landen.json', dir), JSON.stringify(out) + '\n')
const per = {}
for (const s of out.stations) per[s.land] = (per[s.land] ?? 0) + 1
console.log(per, out.stations.length, 'stations')
