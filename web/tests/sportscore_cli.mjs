// Rekent invoer met web/src/sportscore.ts, voor tests/test_sport.py (zelfde cijfers als Python?).
// stdin: {"sporten": [...], "invoer": [{N, K, H, T, GR, V, G, WR, TIJ, BESTTIJ, DROOG, LUWTE}, ...]}
// stdout: per invoer {sport: cijfer} of null.
import { bereken } from '../src/sportscore.ts'

let tekst = ''
for await (const deel of process.stdin) tekst += deel
const { sporten, invoer } = JSON.parse(tekst)
const uit = invoer.map((inv) => {
  const r = bereken(sporten, inv)
  return r && Object.fromEntries(Object.entries(r.d).map(([k, v]) => [k, v.s]))
})
process.stdout.write(JSON.stringify(uit))
