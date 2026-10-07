// De fiche van een strand: in één oogopslag.
// 1. Bovenaan, met foto: wat je vandaag kan, met de uren; eronder de andere uitkomsten van de dag.
// 2. Per uur: de uitkomst (kleur), WAVE, WIND en het getij.
// 3. WAVE en WIND op het gekozen uur.
// Alles wordt in de pipeline berekend (pipeline/rules/uitkomst.py); hier wordt alleen getoond.
import { BLAUW, CYAAN, LICHT } from './kleuren'
import { extremen, hoogte } from './getij'
import { kiesUur, lisDag, lisUur, staat, toonDag, toonTijd, utc, vliegNaar } from './main'
import type { Detail } from './types'

const cache = new Map<string, Promise<Detail>>()
let huidig: Detail | null = null

const el = () => document.getElementById('fiche')!
const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]!)

// De vijf uitkomsten, elk met een foto en een kleur (letters zoals in strand/<id>.json).
interface Soort { letter: string; zin: string; kort: string; foto: string; kleur: string }
const SOORTEN: Soort[] = [
  { letter: 'G', zin: 'Vandaag kan je golfsurfen', kort: 'Golfsurfen', foto: 'golfsurfen', kleur: '#2a78d6' },
  { letter: 'O', zin: 'Vandaag kan je windsurfen op golven', kort: 'Windsurfen op golven', foto: 'golven-en-wind', kleur: '#0a9396' },
  { letter: 'S', zin: 'Vandaag kan je windsurfen', kort: 'Windsurfen', foto: 'windsurfen', kleur: '#e8590c' },
  { letter: 'R', zin: 'Vandaag is het water stil', kort: 'Stille waters', foto: 'plat-water', kleur: '#2f9e44' },
  { letter: 'W', zin: 'Vandaag is het te wild', kort: 'Te wild', foto: 'af-te-raden', kleur: '#c92a2a' },
]
const soort = (l: string) => SOORTEN.find((s) => s.letter === l)
const SPORT = ['G', 'O', 'S']

// Strafpunten van de uitkomst: 0 ideaal, 1 goed. Bij 2 of meer toont de app geen uitkomst ("."),
// behalve "te wild" (pipeline/rules/uitkomst.py, getoond()).
const KWALITEIT = ['ideaal', 'goed']
const kwaliteit = (straf: string) => Math.min(1, Number(straf || 0))
const kompas = (d: number) => ['N', 'NNO', 'NO', 'ONO', 'O', 'OZO', 'ZO', 'ZZO', 'Z', 'ZZW', 'ZW', 'WZW', 'W', 'WNW', 'NW', 'NNW'][Math.round(d / 22.5) % 16]
const hoek = (a: number, b: number) => { const x = Math.abs(a - b) % 360; return x > 180 ? 360 - x : x }
// Windrichting tegenover het strand, met dezelfde grenzen als de berekening.
const tovStrand = (wind: number, kust: number) => {
  const p = hoek(wind, kust)
  return p < 22.5 ? 'recht aanlandig' : p <= 67.5 ? 'schuin aanlandig' : p <= 112.5 ? 'zijwind'
    : p <= 157.5 ? 'schuin aflandig' : 'recht aflandig'
}
const getal = (x: number | null | undefined, nd = 0) => (x == null ? '–' : x.toFixed(nd).replace('.', ','))

const WAVE_NAAM = ['', 'niets', 'beginnergolven', 'sterke golven', 'te sterk']
const WIND_NAAM = ['', 'niets', 'beginnerwind', 'sterke wind', 'te sterk']

function laad(id: string): Promise<Detail> {
  if (!cache.has(id)) cache.set(id, fetch(`data/strand/${id.replace(/[^A-Za-z0-9_.-]/g, '_')}.json`).then((r) => r.json()))
  return cache.get(id)!
}

export async function openFiche(id: string) {
  staat.open = id
  const f = el()
  f.hidden = false
  f.innerHTML = '<p class="klein">Laden…</p>'
  huidig = await laad(id)
  if (staat.open !== id) return
  history.replaceState(null, '', `#${encodeURIComponent(id)}`)
  vliegNaar(huidig.lon, huidig.lat)
  render()
}

export function sluitFiche() {
  staat.open = null
  huidig = null
  el().hidden = true
  history.replaceState(null, '', location.pathname)
}

export function toonUur() {
  if (huidig && staat.open === huidig.id) render()
}

// ---- 1. Wat kan je vandaag? ----

// Uren na elkaar met dezelfde uitkomst en kwaliteit, dag en nacht: [eerste, laatste, kwaliteit].
function vensters(d: Detail, idx: number[], letter: string): [number, number, number][] {
  const out: [number, number, number][] = []
  for (const i of idx) {
    if (d.uitkomst[i] !== letter) continue
    const k = kwaliteit(d.straf[i])
    const laatste = out[out.length - 1]
    if (laatste && laatste[1] === i - 1 && (letter === 'W' || laatste[2] === k)) laatste[1] = i
    else out.push([i, i, k])
  }
  return out
}

function overzicht(d: Detail, idx: number[]) {
  const uur = (i: number) => lisUur(utc(staat.index.tijd[i]))
  // Ideaal / goed / kan geldt voor de vier activiteiten, niet voor "te wild".
  const uren = (v: [number, number, number][], letter: string) => v.map(([a, b, k]) =>
    `<span class="venster k${letter === 'W' ? 0 : k}">${uur(a)}–${uur(b) + 1}u${letter === 'W' ? '' : ` <small>${KWALITEIT[k]}</small>`}</span>`).join('')
  const lijst = SOORTEN.map((s) => ({ s, v: vensters(d, idx, s.letter) }))
  const telUren = (v: [number, number, number][]) => v.reduce((n, [a, b]) => n + b - a + 1, 0)
  // Bovenaan: de sport met de meeste uren; geen sport, dan stille waters; anders te wild.
  const sporten = lijst.filter((x) => SPORT.includes(x.s.letter) && x.v.length)
  const hoofd = sporten.sort((a, b) => telUren(b.v) - telUren(a.v))[0]
    ?? lijst.find((x) => x.s.letter === 'R' && x.v.length) ?? lijst.find((x) => x.s.letter === 'W' && x.v.length)
  const held = hoofd
    ? `<figure class="held" style="--kleur:${hoofd.s.kleur}"><img src="foto/${hoofd.s.foto}.webp" alt="">
        <figcaption><span class="zin">${hoofd.s.zin}</span><span class="uren">${uren(hoofd.v, hoofd.s.letter)}</span></figcaption></figure>`
    : '<div class="held leeg"><span class="zin">Geen voorspelling voor vandaag</span></div>'
  const rest = lijst.filter((x) => x !== hoofd).map((x) => `
    <li class="${x.v.length ? '' : 'niet'}" style="--kleur:${x.s.kleur}">
      <img src="foto/${x.s.foto}.webp" alt=""><span class="kort">${x.s.kort}</span>
      <span class="uren">${x.v.length ? uren(x.v, x.s.letter) : 'niet vandaag'}</span></li>`).join('')
  return `${held}<ul class="rest">${rest}</ul>`
}

// ---- 2. Per uur ----

function dag(d: Detail, idx: number[]) {
  const T = staat.index.tijd
  const ex = d.getij ? extremen(staat.getij, d.getij.a, d.getij.b, d.getij.w) : []
  const kol = (i: number) => (i === staat.i ? 'nu' : '')
  const wat = (i: number) => {
    const s = soort(d.uitkomst[i])
    const k = s?.letter === 'W' ? 0 : kwaliteit(d.straf[i])
    return `<td class="${kol(i)}"><span class="wat" style="${s ? `background:${s.kleur};opacity:${[1, 0.6][k]}` : ''}"
      title="${s ? (s.letter === 'W' ? s.kort : `${s.kort}, ${KWALITEIT[k]}`) : ''}"></span></td>`
  }
  const level = (i: number, reeks: string, pal: string[]) => {
    const n = Number(reeks[i] ?? 0)
    return `<td class="${kol(i)}" style="${n ? `background:${pal[n - 1]};color:${LICHT(n) ? '#0d2530' : '#fff'}` : ''}"><b>${n || '–'}</b></td>`
  }
  const getij = (i: number) => {
    const t = utc(T[i]) / 60000
    const h = ex.length ? hoogte(ex, t) : null
    const e = ex.find((x) => x.t >= t - 30 && x.t < t + 30)
    const pct = h == null ? 0 : Math.max(4, Math.min(100, (h / 4) * 100))
    return `<td class="${kol(i)}">${h == null ? '–' : `<span class="peil"><i style="height:${pct}%"></i></span>`}<small>${e ? (e.hoog ? 'hoog' : 'laag') : ''}</small></td>`
  }
  return `<div class="dag"><table>
    <tr><th></th>${idx.map((i) => `<td class="${kol(i)}"><a href="#" data-i="${i}">${lisUur(utc(T[i]))}</a></td>`).join('')}</tr>
    <tr class="r-wat"><th></th>${idx.map(wat).join('')}</tr>
    <tr class="r-cijfer"><th>WAVE</th>${idx.map((i) => level(i, d.WAVE, BLAUW)).join('')}</tr>
    <tr class="r-cijfer"><th>WIND</th>${idx.map((i) => level(i, d.WIND, CYAAN)).join('')}</tr>
    <tr class="r-getij"><th>getij</th>${idx.map(getij).join('')}</tr>
  </table></div>`
}

// ---- 3. WAVE en WIND op het gekozen uur ----

function tegel(soortNaam: 'WAVE' | 'WIND', n: number, gegevens: string) {
  const kleur = (soortNaam === 'WIND' ? CYAAN : BLAUW)[n - 1] ?? '#ccc'
  const naam = (soortNaam === 'WIND' ? WIND_NAAM : WAVE_NAAM)[n]
  return `<div class="tegel ${LICHT(n) ? 'licht' : ''} ${n === 4 ? 'gevaar' : ''}" style="background:${kleur}">
    <span class="soort">${soortNaam}</span><b>${n}</b><span class="betekenis">${naam}</span>
    <span class="gegevens">${gegevens}</span></div>`
}

function waveGegevens(d: Detail, i: number) {
  const r = d.wave_direction?.[i]
  return `${getal(d.wave_height?.[i], 1)} m · ${getal(d.wave_period?.[i])} s${r == null ? '' : ` · uit ${kompas(r)}`}`
}

function windGegevens(d: Detail, i: number) {
  const r = d.windrichting[i]
  return `${getal(d.wind[i])} kn · vlagen ${getal(d.vlagen[i])} kn${r == null ? '' : `<br>uit ${kompas(r)} · ${tovStrand(r, d.kust)}`}`
}

function render() {
  const d = huidig!
  const I = staat.index
  const i = staat.i
  const ms = utc(I.tijd[i])
  const idx = I.tijd.map((_, k) => k).filter((k) => lisDag(utc(I.tijd[k])) === lisDag(ms))
  const nu = soort(d.uitkomst[i])
  const wave = Number(d.WAVE[i] ?? 0), wind = Number(d.WIND[i] ?? 0)
  el().innerHTML = `<button class="sluit" aria-label="Sluiten">×</button>
    <h2>${esc(d.naam)}</h2>
    <div class="sub">${toonDag(ms)}</div>
    ${overzicht(d, idx)}
    <h3 class="kop">Per uur</h3>
    ${dag(d, idx)}
    ${wave && wind ? `<h3 class="kop">Om ${toonTijd(ms)}${nu ? `: ${nu.kort.toLowerCase()}${nu.letter === 'W' ? '' : `, ${KWALITEIT[kwaliteit(d.straf[i])]}`}` : ''}</h3>
      <div class="tegels">${tegel('WAVE', wave, waveGegevens(d, i))}${tegel('WIND', wind, windGegevens(d, i))}</div>` : ''}
    <p class="klein"><a href="rekenen.html">Hoe berekend?</a> · Geen veiligheidsadvies: volg de redders en de vlaggen.</p>`
  bind()
}

function bind() {
  el().querySelector('.sluit')?.addEventListener('click', sluitFiche)
  el().querySelectorAll<HTMLAnchorElement>('a[data-i]').forEach((a) =>
    a.addEventListener('click', (e) => { e.preventDefault(); kiesUur(Number(a.dataset.i)) }))
  // De uren naar het gekozen uur schuiven.
  const v = el().querySelector<HTMLElement>('.dag')
  const nu = v?.querySelector<HTMLElement>('td.nu')
  if (v && nu) v.scrollLeft = Math.max(0, nu.offsetLeft - v.clientWidth / 2)
}
