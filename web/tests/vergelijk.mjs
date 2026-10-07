// Rekent de fiche (src/sportscore.ts) na op alle gebouwde stranden, uren en sporten:
// het cijfer moet gelijk zijn aan dat van de kaart (pipeline/site/build_data.py).
// Gebruik (in web/): node tests/vergelijk.mjs [map met data, standaard public/data]
import { readFileSync, readdirSync } from 'node:fs'
import { bereken } from '../src/sportscore.ts'

const dir = process.argv[2] ?? 'public/data'
const ix = JSON.parse(readFileSync(`${dir}/index.json`, 'utf8'))
const TIJ = ['laag', 'op', 'hoog', 'af']
let n = 0, fout = 0
for (const f of readdirSync(`${dir}/strand`)) {
  const d = JSON.parse(readFileSync(`${dir}/strand/${f}`, 'utf8'))
  for (let i = 0; i < ix.tijd.length; i++) {
    const r = bereken(ix.sporten, {
      N: d.kijkrichting, K: d.K, BESTTIJ: d.BESTTIJ, DROOG: d.DROOG, LUWTE: d.LUWTE,
      H: d.wave_height[i], T: d.piekperiode[i], GR: d.wave_direction[i], V: d.wind[i], G: d.vlagen[i],
      WR: d.windrichting[i], TIJ: d.tij[i] == null ? null : TIJ[d.tij[i]],
    })
    for (const s of ix.sporten) {
      n++
      const kaart = Number(d.cijfers[s.id][i])
      const fiche = r ? r.d[s.id].s : 0
      if (kaart !== fiche && fout++ < 5) console.log(`verschil: ${d.naam}, uur ${i}, ${s.id}: kaart ${kaart}, fiche ${fiche}`)
    }
  }
}
console.log(`${n} cijfers nagerekend, ${fout} verschillen`)
process.exit(fout ? 1 : 0)
