// Pagina "Hoe berekend": de grenswaarden rechtstreeks uit score_parameters.json, zodat ze altijd kloppen.
import './style.css'
import P from './score_parameters.json'
import { categorieNaam } from './scorekaart'

const zet = (id: string, t: string | number) => { const e = document.getElementById(id); if (e) e.textContent = String(t) }
zet('versie', P.versie)
zet('stormwind', P.storm.wind_vanaf_knopen)
zet('stormvlaag', P.storm.vlaag_vanaf_knopen)
zet('aftrek', Math.round(P.bijkomend_max_aftrek * 100))
zet('onderkant', Math.round(P.brekende_golf_onderkant_factor * 100))

const g = (x: number | null) => (x == null ? '–' : String(x).replace('.', ','))
const trap = (t: (number | null)[]) => t.map(g).join(' · ')
const hoek = (pts: number[][]) => pts.map(([a, s]) => `${a}°→${g(s)}`).join(', ')
const rij = (cellen: string[]) => `<tr>${cellen.map((c) => `<td>${c}</td>`).join('')}</tr>`

const surf = Object.entries(P.golfsurfen).map(([k, p]) => rij([categorieNaam(k), trap(p.hb), trap(p.t),
  Object.entries(p.wind).map(([a, [i, n]]) => `${a}°: ${i}/${n}`).join(' · '), trap(p.cur)]))
const vlak = Object.entries(P.vlak_water).flatMap(([k, v]) => Object.entries(v.profielen).map(([n, p]) =>
  rij([`${categorieNaam(k)} <small>${n}</small>`, trap(p.wind), hoek(p.angle), trap(p.gust), trap(p.water)])))
const golven = Object.entries(P.op_golven).map(([k, p]) => rij([categorieNaam(k), trap(p.wind), hoek(p.angle),
  trap(p.gust), trap(p.hb), trap(p.t)]))
document.getElementById('grenzen')!.innerHTML = `
  <p class="klein">Trapezium: onbruikbaar onder · ideaal van · ideaal tot · onbruikbaar boven. Wind in knopen, golf in meter (brekend), periode in seconden.</p>
  <h3>Golfsporten</h3><div class="tabel"><table><tr><th>Categorie</th><th>Brekende golf</th><th>Periode</th><th>Wind per windhoek (ideaal tot / 0 vanaf)</th><th>Stroming</th></tr>${surf.join('')}</table></div>
  <h3>Windsporten op vlak water</h3><div class="tabel"><table><tr><th>Categorie</th><th>Wind</th><th>Windhoek → deelscore</th><th>Vlaag boven gemiddelde</th><th>Golf aan het strand</th></tr>${vlak.join('')}</table></div>
  <h3>Windsporten op golven</h3><div class="tabel"><table><tr><th>Categorie</th><th>Wind</th><th>Windhoek → deelscore</th><th>Vlaag</th><th>Brekende golf</th><th>Periode</th></tr>${golven.join('')}</table></div>
  <h3>Stille waters</h3><div class="tabel"><table><tr><th>Wind</th><th>Water</th><th>Stroming</th><th>Wind van land</th></tr>
    ${rij([trap(P.stille_waters.wind), trap(P.stille_waters.water), trap(P.stille_waters.cur), trap(P.stille_waters.off_wind)])}</table></div>`
