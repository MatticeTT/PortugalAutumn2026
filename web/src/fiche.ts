// De fiche van een strand: in één oogopslag.
// 1. WAVE en WIND op het gekozen uur.
// 2. De dag per uur: WAVE, WIND en het getij.
// 3. Wat je vandaag kan doen, met een foto en de uren (bovenaan).
// De berekening zit in de pipeline (pipeline/rules/score.py en dagplan.py); hier wordt alleen getoond.
import { BLAUW, CYAAN, LICHT } from './kleuren'
import { extremen, hoogte, zon } from './getij'
import { kiesUur, lisDag, lisUur, staat, toonDag, toonTijd, utc, vliegNaar } from './main'
import type { Detail, ScoreRij } from './types'

const cache = new Map<string, Promise<Detail>>()
let huidig: Detail | null = null

const el = () => document.getElementById('fiche')!
const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]!)

// Wat het cijfer betekent, in een paar woorden.
const BETEKENIS = ['', 'niets', 'weinig', 'goed voor beginners', 'sterk, voor gevorderden', 'gevaarlijk']

// De vijf toestanden van een dag, elk met een foto en een kleur. `plan` is de sleutel in strand/<id>.json
// (pipeline/rules/dagplan.py); "af te raden" komt uit WIND of WAVE 5.
interface Toestand { id: string; plan?: string; zin: string; kort: string; foto: string; kleur: string }
const TOESTANDEN: Toestand[] = [
  { id: 'surf', plan: 'surf', zin: 'Vandaag kan je golfsurfen', kort: 'Golfsurfen', foto: 'golfsurfen', kleur: '#2a78d6' },
  { id: 'windgolf', plan: 'windgolf', zin: 'Vandaag zijn er golven en wind', kort: 'Golven en wind', foto: 'golven-en-wind', kleur: '#0a9396' },
  { id: 'wind', plan: 'wind', zin: 'Vandaag kan je windsurfen', kort: 'Windsurfen', foto: 'windsurfen', kleur: '#e8590c' },
  { id: 'plat', plan: 'plat', zin: 'Vandaag is het plat water', kort: 'Plat water', foto: 'plat-water', kleur: '#2f9e44' },
  { id: 'gevaar', zin: 'Vandaag is het af te raden', kort: 'Af te raden', foto: 'af-te-raden', kleur: '#c92a2a' },
]
const MIN_UREN = 2 // een sessie: minstens 2 uur na elkaar (zie "Hoe rekenen we")

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

// ---- 1. WAVE en WIND ----

function tegel(soort: 'WAVE' | 'WIND', n: number, letOp: boolean) {
  const kleur = (soort === 'WIND' ? CYAAN : BLAUW)[n - 1] ?? '#ccc'
  const uitleg = letOp ? 'wind van land: te licht om te kiten' : BETEKENIS[n]
  return `<div class="tegel ${LICHT(n) ? 'licht' : ''} ${n === 5 ? 'gevaar' : ''}" style="background:${kleur}">
    <span class="soort">${soort}</span><b>${n}${letOp ? '<i class="letop">!</i>' : ''}</b><span class="betekenis">${uitleg}</span></div>`
}

// ---- 2. De dag per uur ----

function dag(d: Detail, idx: number[], dagStart: number) {
  const T = staat.index.tijd
  const rows: (ScoreRij | null)[] = d.score ?? []
  const licht = zon(d.lat, d.lon, dagStart / 60000 + 720)
  const ex = d.getij ? extremen(staat.getij, d.getij.a, d.getij.b, d.getij.w) : []
  const kol = (i: number) => {
    const t = utc(T[i]) / 60000
    const nacht = licht && (t + 30 < licht[0] || t - 30 > licht[1])
    return `${nacht ? 'nacht' : ''} ${i === staat.i ? 'nu' : ''}`
  }
  const cijfer = (i: number, k: 0 | 1) => {
    const n = rows[i]?.[k] ?? 0
    const pal = k === 0 ? CYAAN : BLAUW
    const l = k === 0 && rows[i]?.[10] ? '<i class="letop">!</i>' : ''
    return `<td class="${kol(i)}" style="${n ? `background:${pal[n - 1]};color:${LICHT(n) ? '#0d2530' : '#fff'}` : ''}"><b>${n || '–'}</b>${l}</td>`
  }
  const getij = (i: number) => {
    const t = utc(T[i]) / 60000
    const h = ex.length ? hoogte(ex, t) : null
    const e = ex.find((x) => x.t >= t - 30 && x.t < t + 30)
    const pct = h == null ? 0 : Math.max(4, Math.min(100, (h / 4) * 100))
    return `<td class="${kol(i)}">${h == null ? '–' : `<span class="peil"><i style="height:${pct}%"></i></span>`}<small>${e ? (e.hoog ? 'hoog' : 'laag') : ''}</small></td>`
  }
  const wat = (i: number) => {
    const t = toestandOpUur(d, i)
    return `<td class="${kol(i)}"><span class="wat" style="${t ? `background:${t.kleur}` : ''}" title="${t ? t.kort : 'niets'}"></span></td>`
  }
  return `<div class="dag"><table>
    <tr><th></th>${idx.map((i) => `<td class="${kol(i)}"><a href="#" data-i="${i}">${lisUur(utc(T[i]))}</a></td>`).join('')}</tr>
    <tr class="r-wat"><th></th>${idx.map(wat).join('')}</tr>
    <tr class="r-cijfer"><th>WAVE</th>${idx.map((i) => cijfer(i, 1)).join('')}</tr>
    <tr class="r-cijfer"><th>WIND</th>${idx.map((i) => cijfer(i, 0)).join('')}</tr>
    <tr class="r-getij"><th>getij</th>${idx.map(getij).join('')}</tr>
  </table></div>`
}

// ---- 3. Wanneer kan je gaan? ----

// Uren na elkaar met minstens `min` (1 mogelijk, 2 goed), als [eerste uur, laatste uur].
function vensters(code: string, idx: number[], min: number): [number, number][] {
  const out: [number, number][] = []
  let start = -1
  idx.forEach((i, k) => {
    const ok = Number(code[i] ?? 0) >= min
    if (ok && start < 0) start = k
    const laatste = k === idx.length - 1
    if (start >= 0 && (!ok || laatste)) {
      const eind = ok ? k : k - 1
      if (eind - start + 1 >= MIN_UREN) out.push([idx[start], idx[eind]])
      start = -1
    }
  })
  return out
}

// Per toestand de uren van de dag: [eerste uur, laatste uur] met "goed" (2), anders met "mogelijk" (1).
function urenVan(d: Detail, t: Toestand, idx: number[]): { v: [number, number][]; goed: boolean } {
  let code: string
  if (t.plan) code = d.plan?.[t.plan] ?? ''
  else {
    // Af te raden: WIND of WAVE 5, overdag.
    const rows = d.score ?? []
    code = staat.index.tijd.map((_, i) => (rows[i] && (rows[i]![0] === 5 || rows[i]![1] === 5) ? '2' : '0')).join('')
  }
  const goed = vensters(code, idx, 2)
  if (goed.length) return { v: goed, goed: true }
  return { v: vensters(code, idx, 1), goed: false }
}

// Welke toestand heeft een uur (voor de kleur in de dagstrook): de eerste die op dat uur geldt.
function toestandOpUur(d: Detail, i: number): Toestand | null {
  const rows = d.score ?? []
  if (rows[i] && (rows[i]![0] === 5 || rows[i]![1] === 5)) return TOESTANDEN[4]
  return TOESTANDEN.find((t) => t.plan && Number(d.plan?.[t.plan]?.[i] ?? 0) >= 1) ?? null
}

function overzicht(d: Detail, idx: number[]) {
  const uur = (i: number) => lisUur(utc(staat.index.tijd[i]))
  const tekst = (v: [number, number][]) => v.map(([a, b]) => `${uur(a)}–${uur(b) + 1}u`).join(' en ')
  const lijst = TOESTANDEN.map((t) => ({ t, ...urenVan(d, t, idx) }))
  // Bovenaan: de eerste toestand met goede uren; anders de eerste met mogelijke uren.
  const hoofd = lijst.find((x) => x.v.length && x.goed) ?? lijst.find((x) => x.v.length)
  const held = hoofd
    ? `<figure class="held" style="--kleur:${hoofd.t.kleur}"><img src="foto/${hoofd.t.foto}.webp" alt="">
        <figcaption><span class="zin">${hoofd.t.zin}</span><span class="uren">${tekst(hoofd.v)}${hoofd.goed ? '' : ' <small>(niet ideaal)</small>'}</span></figcaption></figure>`
    : `<div class="held leeg"><span class="zin">Vandaag geen goede uren</span></div>`
  const rest = lijst.filter((x) => x !== hoofd && (x.t.plan || x.v.length)).map((x) => `
    <li class="${x.v.length ? '' : 'niet'}" style="--kleur:${x.t.kleur}">
      <img src="foto/${x.t.foto}.webp" alt=""><span class="kort">${x.t.kort}</span>
      <span class="uren">${x.v.length ? tekst(x.v) + (x.goed ? '' : ' <small>(niet ideaal)</small>') : 'niet vandaag'}</span></li>`).join('')
  return `${held}<ul class="rest">${rest}</ul>`
}

function render() {
  const d = huidig!
  const I = staat.index
  const i = staat.i
  const ms = utc(I.tijd[i])
  const idx = I.tijd.map((_, k) => k).filter((k) => lisDag(utc(I.tijd[k])) === lisDag(ms))
  const dagStart = utc(I.tijd[idx[0]]) - lisUur(utc(I.tijd[idx[0]])) * 3600e3
  const row = d.score?.[i]
  const ipma = d.ipma[i] && d.ipma[i] !== 'green' ? '<p class="waarschuwing">⚠ IPMA-waarschuwing voor zeegang</p>' : ''
  el().innerHTML = `<button class="sluit" aria-label="Sluiten">×</button>
    <h2>${esc(d.naam)}</h2>
    <div class="sub">${toonDag(ms)}</div>${ipma}
    ${overzicht(d, idx)}
    <h3 class="kop">Per uur</h3>
    ${dag(d, idx, dagStart)}
    ${row ? `<h3 class="kop">Om ${toonTijd(ms)}</h3><div class="tegels">${tegel('WAVE', row[1], false)}${tegel('WIND', row[0], !!row[10])}</div>` : ''}
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
