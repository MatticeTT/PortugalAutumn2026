// Getijverschil bij springtij per getijstation: MHWS - MLWS uit de datums van TICON-4 (via Neaps).
// Dat is het gemiddelde verschil tussen hoog- en laagwater bij springtij.
// Leest de stations van Portugal (stations.json) en van de andere landen (stations_landen.json).
// Schrijft data/beaches/bodem/getij_stations.json: {station_id: {mhws, mlws, verschil_m, bron}}.
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { stationsNear } from 'neaps'

const tides = new URL('../../data/tides/', import.meta.url)
const lijst = ['stations.json', 'stations_landen.json']
  .flatMap((f) => JSON.parse(readFileSync(new URL(f, tides))).stations)
const uit = {}
for (const s of lijst) {
  const st = stationsNear({ latitude: s.lat, longitude: s.lon, maxDistance: 5_000, limit: 20 })
    .find((x) => x.id === s.neaps_id)
  const d = st?.datums ?? {}
  if (d.MHWS != null && d.MLWS != null) {
    uit[s.id] = { mhws: d.MHWS, mlws: d.MLWS, verschil_m: Math.round((d.MHWS - d.MLWS) * 100) / 100, bron: 'datums' }
  } else if (st) {
    // Geen datums: 2 x (M2 + S2), de klassieke benadering van het springverval.
    const a = Object.fromEntries(st.harmonic_constituents.map((c) => [c.name, c.amplitude]))
    if (a.M2 != null && a.S2 != null) uit[s.id] = { verschil_m: Math.round(2 * (a.M2 + a.S2) * 100) / 100, bron: '2(M2+S2)' }
  }
  if (!uit[s.id]) console.log('geen getijverschil voor', s.id)
}
const dir = new URL('../../data/beaches/bodem/', import.meta.url)
mkdirSync(dir, { recursive: true })
writeFileSync(new URL('getij_stations.json', dir), JSON.stringify(uit, null, 1) + '\n')
console.log(Object.keys(uit).length, 'stations van', lijst.length)
