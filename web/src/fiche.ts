// De fiche van een strand: in één oogopslag.
// 1. WAVE en WIND op het gekozen uur.
// 2. De dag per uur: WAVE, WIND en het getij.
// 3. Golfsurfen, windsurfen, wind-golven en stille waters: wanneer, of vandaag niet.
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

const ACTIVITEIT: [string, string][] = [
  ['surf', 'Golfsurfen'], ['wind', 'Windsurfen'], ['windgolf', 'Wind-golven'], ['plat', 'Stille waters'],
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
  return `<div class="dag"><table>
    <tr><th></th>${idx.map((i) => `<td class="${kol(i)}"><a href="#" data-i="${i}">${lisUur(utc(T[i]))}</a></td>`).join('')}</tr>
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

function wanneer(d: Detail, idx: number[]) {
  const uur = (i: number) => lisUur(utc(staat.index.tijd[i]))
  const tekst = (v: [number, number][]) => v.map(([a, b]) => `${uur(a)}–${uur(b) + 1}u`).join(', ')
  return `<ul class="wanneer">${ACTIVITEIT.map(([a, naam]) => {
    const code = d.plan?.[a] ?? ''
    const goed = vensters(code, idx, 2)
    const kan = goed.length ? [] : vensters(code, idx, 1)
    const stand = goed.length ? 'goed' : kan.length ? 'kan' : 'niet'
    const zin = goed.length ? tekst(goed) : kan.length ? `${tekst(kan)} <small>(niet ideaal)</small>` : 'vandaag niet'
    return `<li class="${stand}"><span class="naam">${naam}</span><span class="uren">${zin}</span></li>`
  }).join('')}</ul>`
}

function render() {
  const d = huidig!
  const I = staat.index
  const i = staat.i
  const ms = utc(I.tijd[i])
  const idx = I.tijd.map((_, k) => k).filter((k) => lisDag(utc(I.tijd[k])) === lisDag(ms))
  const dagStart = utc(I.tijd[idx[0]]) - lisUur(utc(I.tijd[idx[0]])) * 3600e3
  const row = d.score?.[i]
  const gevaar = d.ipma[i] && d.ipma[i] !== 'green' ? '<p class="waarschuwing">⚠ IPMA-waarschuwing voor zeegang</p>' : ''
  el().innerHTML = `<button class="sluit" aria-label="Sluiten">×</button>
    <h2>${esc(d.naam)}</h2>
    <div class="sub">${toonDag(ms)} om ${toonTijd(ms)}</div>${gevaar}
    ${row ? `<div class="tegels">${tegel('WAVE', row[1], false)}${tegel('WIND', row[0], !!row[10])}</div>` : '<p>Geen voorspelling voor dit uur.</p>'}
    ${dag(d, idx, dagStart)}
    ${wanneer(d, idx)}
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
