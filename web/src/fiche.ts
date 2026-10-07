// De fiche van een strand, met het rekenmodel v2 (pipeline/rules/model.py). De vier lagen staan apart:
//   bovenaan  de dag: per conclusie de uren, en per uur de conclusie, WAVE, WIND, op het strand en het getij
//   laag 4    de conclusie van het gekozen uur, met de vijf scores
//   laag 1-2  de vlakken WAVE (zee: hoogte en periode) en WIND (wind en vlaag)
//   laag 3    wat dit strand met die zee en die wind doet: golfrichting, windrichting, getij
// Alles wordt in de pipeline berekend; hier wordt alleen getoond.
import { BLAUW, CYAAN, LICHT } from './kleuren'
import { extremen, hoogte } from './getij'
import { data, kiesUur, lisDag, lisUur, staat, toonDag, toonTijd, utc, vliegNaar } from './main'
import type { Detail } from './types'

const cache = new Map<string, Promise<Detail>>()
let huidig: Detail | null = null

const el = () => document.getElementById('fiche')!
const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]!)

// Per conclusie een letter (zie build_data.py): hoofdletter = ideaal, kleine letter = andere (de beste
// activiteit, niet ideaal), W = te wild. Kleuren (eigenaar): golfsurf blauw, windsurf op golven geel,
// windsurf cyaan, stille waters grijs, te wild rood. `tekst` = dezelfde kleur, leesbaar als tekst.
interface Soort { letter: string; naam: string; zin: string; foto: string; kleur: string; tekst: string }
const SOORTEN: Soort[] = [
  { letter: 'G', naam: 'golfsurfen', zin: 'Ideaal golfsurfen', foto: 'golfsurfen', kleur: '#2a6fdb', tekst: '#2a6fdb' },
  { letter: 'O', naam: 'windsurfen op golven', zin: 'Ideaal windsurfen op golven', foto: 'golven-en-wind', kleur: '#f5c400', tekst: '#b38f00' },
  { letter: 'S', naam: 'windsurfen', zin: 'Ideaal windsurfen', foto: 'windsurfen', kleur: '#14b8d4', tekst: '#0e8fa6' },
  { letter: 'R', naam: 'stille waters', zin: 'Ideaal stille waters', foto: 'plat-water', kleur: '#8a949c', tekst: '#6b757d' },
  { letter: 'W', naam: 'te wild', zin: 'Te wild', foto: 'af-te-raden', kleur: '#d0312d', tekst: '#d0312d' },
]
const soort = (l: string) => SOORTEN.find((s) => s.letter === l.toUpperCase())
const SCORES = ['golfsurfen', 'windsurfen op golven', 'windsurfen', 'stille waters', 'te wild']
const SCORE_LETTER = ['G', 'O', 'S', 'R', 'W']

const LEVEL = ['', 'niets', 'beginner', 'sterk', 'te sterk']
const kompas = (d: number) => ['N', 'NNO', 'NO', 'ONO', 'O', 'OZO', 'ZO', 'ZZO', 'Z', 'ZZW', 'ZW', 'WZW', 'W', 'WNW', 'NW', 'NNW'][Math.round(d / 22.5) % 16]
// Naam van de windhoek φ (tabel in laag 3 van het document).
const windNaam = (phi: number) => phi < 22.5 ? 'recht aanlandig' : phi < 67.5 ? 'schuin aanlandig' : phi < 112.5 ? 'zijwind'
  : phi < 157.5 ? 'schuin aflandig' : 'recht aflandig'
const getal = (x: number | null | undefined, nd = 0) => (x == null ? '–' : x.toFixed(nd).replace('.', ','))

function laad(id: string): Promise<Detail> {
  if (!cache.has(id)) cache.set(id, data(`strand/${id.replace(/[^A-Za-z0-9_.-]/g, '_')}.json`))
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

const uurNr = (i: number) => lisUur(utc(staat.index.tijd[i]))

// ---- De dag: per conclusie de uren ----

// Uren na elkaar met dezelfde conclusie (letter), dag en nacht: [eerste, laatste].
function vensters(d: Detail, idx: number[], past: (l: string) => boolean): [number, number][] {
  const out: [number, number][] = []
  for (const i of idx) {
    if (!past(d.letter[i])) continue
    const laatste = out[out.length - 1]
    if (laatste && laatste[1] === i - 1) laatste[1] = i
    else out.push([i, i])
  }
  return out
}
const urenTekst = (v: [number, number][]) => v.map(([a, b]) => `<span class="venster">${uurNr(a)}–${uurNr(b) + 1}u</span>`).join('')
const telUren = (v: [number, number][]) => v.reduce((n, [a, b]) => n + b - a + 1, 0)

function overzicht(d: Detail, idx: number[]) {
  if (d.controle?.blokkerend?.length) {
    return `<div class="held leeg"><span class="zin">Voor dit strand rekent het model nog niet</span>
      <small>${esc(d.controle.blokkerend.join(', '))}</small></div>`
  }
  const ideaal = SOORTEN.filter((s) => s.letter !== 'W').map((s) => ({ s, v: vensters(d, idx, (l) => l === s.letter) }))
  const wild = { s: soort('W')!, v: vensters(d, idx, (l) => l === 'W') }
  const andere = vensters(d, idx, (l) => /[gosr]/.test(l))
  // Bovenaan met foto: de ideale activiteit met de meeste uren; geen ideaal uur, dan te wild.
  const hoofd = ideaal.filter((x) => x.v.length).sort((a, b) => telUren(b.v) - telUren(a.v))[0] ?? (wild.v.length ? wild : null)
  const held = hoofd
    ? `<figure class="held" style="--kleur:${hoofd.s.kleur}"><img src="foto/${hoofd.s.foto}.webp" alt="">
        <figcaption><span class="zin">${hoofd.s.zin}</span><span class="uren">${urenTekst(hoofd.v)}</span></figcaption></figure>`
    : '<div class="held leeg"><span class="zin">Vandaag geen ideaal uur</span></div>'
  const rij = (s: Soort, v: [number, number][]) => `
    <li class="${v.length ? '' : 'niet'}" style="--kleur:${s.kleur};--uren:${s.tekst}">
      <img src="foto/${s.foto}.webp" alt=""><span class="kort">${s.zin}</span>
      <span class="uren">${v.length ? urenTekst(v) : 'niet vandaag'}</span></li>`
  const rest = [...ideaal, wild].filter((x) => x !== hoofd).map((x) => rij(x.s, x.v)).join('')
  const ander = `<li class="${andere.length ? '' : 'niet'} andere" style="--kleur:var(--lijn)">
      <span class="stip-andere"></span><span class="kort">Andere <small>niet ideaal</small></span>
      <span class="uren">${andere.length ? urenTekst(andere) : 'niet vandaag'}</span></li>`
  return `${held}<ul class="rest">${rest}${ander}</ul>`
}

// ---- Per uur ----

function dag(d: Detail, idx: number[]) {
  const T = staat.index.tijd
  const ex = d.getij ? extremen(staat.getij, d.getij.a, d.getij.b, d.getij.w) : []
  const kol = (i: number) => [i === staat.i ? 'nu' : '', d.licht[i] === '0' ? 'nacht' : ''].join(' ')
  const wat = (i: number) => {
    const l = d.letter[i] ?? '.'
    const s = soort(l)
    const ideaal = s && (l === 'W' || l === l.toUpperCase())
    const titel = d.conclusie?.[i] ?? ''
    return `<td class="${kol(i)}"><span class="wat ${s && !ideaal ? 'andere' : ''}" style="${s ? `--kleur:${s.kleur}` : ''}"
      title="${esc(titel)}"></span></td>`
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
    <tr class="r-cijfer"><th title="WAVE op het strand">strand</th>${idx.map((i) => level(i, d.WAVE_strand, BLAUW)).join('')}</tr>
    <tr class="r-getij"><th>getij</th>${idx.map(getij).join('')}</tr>
  </table></div>`
}

// ---- Laag 4: de conclusie en de vijf scores ----

function conclusie(d: Detail, i: number) {
  const tekst = d.conclusie?.[i]
  const scores = d.scores?.[i]
  if (!tekst || !scores) return ''
  const s = soort(d.letter[i])
  const ideaal = d.letter[i] === 'W' || d.letter[i] === d.letter[i].toUpperCase()
  const balk = (k: number) => {
    const ks = soort(SCORE_LETTER[k])!
    return `<li><span>${SCORES[k]}</span><span class="balk"><i style="width:${scores[k]}%;background:${ks.kleur}"></i>
      <em style="left:${k === 4 ? 50 : 75}%"></em></span><b>${scores[k]}</b></li>`
  }
  return `<div class="conclusie ${ideaal ? '' : 'andere'}" style="--kleur:${s?.kleur ?? 'var(--lijn)'}">
      <span class="laag">Conclusie</span><p>${esc(tekst)}</p>
      <ul class="scores">${[0, 1, 2, 3, 4].map(balk).join('')}</ul>
      <small>Ideaal vanaf 75 · te wild vanaf 50</small></div>`
}

// ---- Laag 1 en 2: de vlakken WAVE en WIND ----

// rood: het vlak staat rood omkaderd als de richting verkeerd is (wind van land; golf die op zee staat maar
// op het strand te weinig aankomt). Zie build_data.py.
function tegel(naam: 'WAVE' | 'WIND', n: number, gegevens: string, rood = false) {
  const kleur = (naam === 'WIND' ? CYAAN : BLAUW)[n - 1] ?? '#ccc'
  return `<div class="tegel ${LICHT(n) ? 'licht' : ''} ${n === 4 ? 'gevaar' : ''} ${rood ? 'verkeerd' : ''}" style="background:${kleur}">
    <span class="soort">${naam}</span><b>${n}</b><span class="betekenis">${LEVEL[n]}</span>
    <span class="gegevens">${gegevens}</span></div>`
}

// ---- Icoontjes voor de WAVE- en WIND-vakken (lijnen in de tekstkleur) ----

const svg = (inhoud: string) =>
  `<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"
    stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${inhoud}</svg>`
const ICOON = {
  golf: svg('<path d="M2 15c2 0 2-2 4-2s2 2 4 2 2-2 4-2 2 2 4 2 2-2 4-2"/><path d="M2 20c2 0 2-2 4-2s2 2 4 2 2-2 4-2 2 2 4 2 2-2 4-2"/><path d="M4 9c2-4 7-5 10-2"/>'),
  periode: svg('<circle cx="12" cy="13" r="8"/><path d="M12 9v4l3 2"/><path d="M9 3h6"/>'),
  wind: svg('<path d="M3 8h11a3 3 0 1 0-3-3"/><path d="M3 12h16a3 3 0 1 1-3 3"/><path d="M3 16h7"/>'),
  vlaag: svg('<path d="M3 9h9a3 3 0 1 0-3-3"/><path d="M3 14h13a3 3 0 1 1-3 3"/><path d="M18 3l-2 4h3l-2 4"/>'),
}
// Pijl die wijst waar wind of golven naartoe gaan (ze komen "uit" de richting r).
const pijl = (r: number) => `<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
  <g transform="rotate(${r + 180} 12 12)"><path d="M12 3 L18 15 L12 12 L6 15 Z" fill="currentColor"/></g></svg>`

// Tekening van een richting tegenover het strand: zee boven, strand onder, alsof je op het strand
// staat en naar zee kijkt (rechts = met de klok mee vanaf de kustrichting). De pijl komt uit de richting
// waar golf of wind vandaan komt en wijst naar het strand. Bij golven toont een lichte waaier het
// swell-venster: de richtingen waaruit deining dit strand kan bereiken. Rechtsboven wijst N naar het noorden.
const rel = (richting: number, kust: number) => ((richting - kust) % 360 + 540) % 360 - 180 // 0 = recht van zee
const op = (a: number, r: number, cx = 60, cy = 50) => {
  const t = (a * Math.PI) / 180
  return [cx + r * Math.sin(t), cy - r * Math.cos(t)].map((x) => x.toFixed(1))
}
let tekeningNr = 0
function richtingTekening(soort: 'golf' | 'wind', richting: number, kust: number, vensters?: number[][] | null) {
  const clip = `zee${++tekeningNr}`
  const a = rel(richting, kust)
  // Van land: de pijl begint in het strand (onder de kustlijn is maar 22 hoog), dus korter.
  const c = Math.cos((a * Math.PI) / 180)
  const [x0, y0] = op(a, c < 0 ? Math.min(44, 16 / -c) : 44)
  const [x1, y1] = op(a, 10)
  const hoek = Math.atan2(Number(y1) - Number(y0), Number(x1) - Number(x0)) * 180 / Math.PI
  // Elk swell-venster als een lichte waaier.
  const waaier = (vensters ?? []).map((v) => {
    const v0 = rel(v[0], kust)
    let v1 = rel(v[1], kust)
    if (v1 <= v0) v1 += 360
    const [ax, ay] = op(v0, 60), [bx, by] = op(v1, 60)
    return `<path d="M60 50 L${ax} ${ay} A60 60 0 ${v1 - v0 > 180 ? 1 : 0} 1 ${bx} ${by} Z" fill="currentColor" opacity=".16" clip-path="url(#${clip})"/>`
  }).join('')
  // Golven: twee kammen dwars op de pijl; wind: drie streepjes langs de pijl.
  const teken = soort === 'golf'
    ? `<g transform="translate(${x0} ${y0}) rotate(${hoek})"><path d="M4 -9 Q8 0 4 9 M11 -7 Q15 0 11 7" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></g>`
    : `<g transform="translate(${x0} ${y0}) rotate(${hoek})" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M-2 -6 H8 M-6 0 H6 M-2 6 H8"/></g>`
  const [nx, ny] = op(rel(0, kust), 9, 108, 12)
  return `<svg class="richting" viewBox="0 0 120 72" aria-hidden="true">
    <defs><clipPath id="${clip}"><rect width="120" height="50"/></clipPath></defs>
    <rect width="120" height="50" rx="6" fill="#4f9fd0" opacity=".28"/>
    <path d="M0 50 H120 V66 a6 6 0 0 1 -6 6 H6 a6 6 0 0 1 -6 -6 Z" fill="#e8d9b0"/>
    <path d="M0 50 H120" stroke="#c9b27a" stroke-width="1.5"/>
    ${waaier}
    ${teken}
    <path d="M${x0} ${y0} L${x1} ${y1}" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
    <g transform="translate(${x1} ${y1}) rotate(${hoek})"><path d="M2 0 L-8 -6 L-8 6 Z" fill="currentColor"/></g>
    <circle cx="60" cy="50" r="2.5" fill="currentColor"/>
    <g font-size="8" font-weight="700" fill="currentColor" opacity=".75">
      <text x="${nx}" y="${ny}" text-anchor="middle" dominant-baseline="middle">N</text>
      <text x="6" y="64">strand</text><text x="6" y="11">zee</text></g></svg>`
}

// Getij: strand dat schuin oploopt, het water op de juiste hoogte, en een pijl omhoog of omlaag.
function getijTekening(p: number, stijgt: boolean) {
  const y = 28 - p * 20 // waterlijn: 28 bij laagwater, 8 bij hoogwater
  const pijl = stijgt ? 'M38 22 V8 M33 13 L38 7 L43 13' : 'M38 8 V22 M33 17 L38 23 L43 17'
  return `<svg class="strand" viewBox="0 0 48 32" width="48" height="32" aria-hidden="true">
    <rect y="${y}" width="48" height="${32 - y}" rx="2" fill="#4f9fd0" opacity=".55"/>
    <path d="M0 32 L48 6 V32 Z" fill="#e8d9b0" opacity=".9"/>
    <path d="M0 ${y} H48" stroke="currentColor" stroke-width="1.6"/>
    <path d="${pijl}" stroke="currentColor" stroke-width="2.4" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>`
}

const rijtje = (icoon: string, waarde: string, woord: string) =>
  `<span class="rijtje">${icoon}<b>${waarde}</b><small>${woord}</small></span>`

// WAVE: het level komt alleen uit E_zee = 1,96 × hoogte² × periode² van de krachtigste deining, zonder
// richting. Het vlak toont precies die deining: hoogte, periode, richting (evenveel regels als WIND). Wat het strand
// ervan krijgt (bereikt, WAVE_strand), staat in de regel onder de vlakken.
function waveGegevens(d: Detail, i: number) {
  const r = d.zee_r?.[i]
  return `<span class="rijtjes">
    ${rijtje(ICOON.golf, `${getal(d.zee_h?.[i], 1)} m`, 'hoogte')}
    ${rijtje(ICOON.periode, `${getal(d.zee_t?.[i], 1)} s`, 'periode')}
    ${r == null ? '' : rijtje(pijl(r), kompas(r), 'richting')}</span>
    ${r == null ? '' : `<span class="tovstrand">${richtingTekening('golf', r, d.kust, d.venster)}
      <small>golf uit ${kompas(r)}</small></span>`}`
}

// De regel onder de vlakken: wat dit strand van de zee krijgt.
function opStrand(d: Detail, i: number) {
  if (d.bereikt?.[i] == null) return ''
  const n = Number(d.WAVE_strand[i])
  return `<p class="opstrand">Op dit strand komt <b>${d.bereikt[i]}%</b> van de golfkracht aan
    (E ${d.E[i]} kJ): <span class="lvl" style="background:${BLAUW[n - 1]};color:${LICHT(n) ? '#0d2530' : '#fff'}">WAVE_strand ${n}</span> ${LEVEL[n]}</p>`
}

// WIND: wind en vlaag, en de windrichting tegenover het strand.
function windGegevens(d: Detail, i: number) {
  const r = d.windrichting[i]
  const phi = d.windhoek?.[i]
  return `<span class="rijtjes">
    ${rijtje(ICOON.wind, `${getal(d.wind[i])} kn`, 'wind')}
    ${rijtje(ICOON.vlaag, `${getal(d.vlagen[i])} kn`, 'vlaag')}
    ${r == null ? '' : rijtje(pijl(r), kompas(r), 'richting')}</span>
    ${r == null ? '' : `<span class="tovstrand">${richtingTekening('wind', r, d.kust)}
      <small>wind uit ${kompas(r)}${phi == null ? '' : `<span>${windNaam(phi)}</span>`}</small></span>`}`
}

// ---- Laag 3: de extra's per strand ----

function extras(d: Detail, i: number) {
  if (!d.getij || d.tij?.[i] == null) return ''
  const ex = extremen(staat.getij, d.getij.a, d.getij.b, d.getij.w)
  const t = utc(staat.index.tijd[i]) / 60000
  const k = ex.findIndex((e) => e.t > t)
  const stijgt = k > 0 ? ex[k].hoog : null
  return `<h3 class="kop">Getij op dit strand</h3><ul class="extras">
    <li>${stijgt == null ? '' : getijTekening(d.tij[i]! / 100, stijgt)}<span><b>${d.tij[i]}%</b>${stijgt == null ? '' : `, ${stijgt ? 'opkomend' : 'afgaand'}`}
      · verval ${getal(d.verval[i], 1)} m · tijgewicht ${getal(d.tijgewicht[i], 2)}
      <small>${k > 0 ? `${ex[k].hoog ? 'hoog' : 'laag'} om ${toonTijd(ex[k].t * 60000)} · ` : ''}E ${d.E[i]} kJ · H op het strand ${getal(d.H[i], 2)} m · periode ${getal(d.periode[i], 1)} s</small></span></li></ul>`
}

function render() {
  const d = huidig!
  const I = staat.index
  const i = staat.i
  const ms = utc(I.tijd[i])
  const idx = I.tijd.map((_, k) => k).filter((k) => lisDag(utc(I.tijd[k])) === lisDag(ms))
  const wave = Number(d.WAVE[i] ?? 0), wind = Number(d.WIND[i] ?? 0)
  const nakijken = d.controle?.nakijken?.length
    ? `<p class="klein nakijken">Stranddata nakijken: ${esc(d.controle.nakijken.join('; '))}</p>` : ''
  el().innerHTML = `<button class="sluit" aria-label="Sluiten">×</button>
    <h2>${esc(d.naam)}</h2>
    <div class="sub">${toonDag(ms)}</div>
    ${overzicht(d, idx)}
    <h3 class="kop">Per uur</h3>
    ${dag(d, idx)}
    <h3 class="kop">Om ${toonTijd(ms)}${d.licht[i] === '0' ? ' <small>(donker)</small>' : ''}</h3>
    ${conclusie(d, i)}
    ${wave && wind ? `<div class="tegels">${tegel('WAVE', wave, waveGegevens(d, i), (Number(d.rood?.[i] ?? 0) & 2) > 0)}${tegel('WIND', wind, windGegevens(d, i), (Number(d.rood?.[i] ?? 0) & 1) > 0)}</div>${opStrand(d, i)}` : ''}
    ${extras(d, i)}
    ${nakijken}
    <p class="klein"><a href="rekenen.html">Hoe berekend?</a> · <a href="controle.html#${encodeURIComponent(d.id)}">Stranddata</a>
      · Geen veiligheidsadvies: volg de redders en de vlaggen.</p>`
  bind()
}

function bind() {
  el().querySelector('.sluit')?.addEventListener('click', sluitFiche)
  el().querySelectorAll<HTMLAnchorElement>('a[data-i]').forEach((a) =>
    a.addEventListener('click', (e) => { e.preventDefault(); kiesUur(Number(a.dataset.i)) }))
  const v = el().querySelector<HTMLElement>('.dag')
  const nu = v?.querySelector<HTMLElement>('td.nu')
  if (v && nu) v.scrollLeft = Math.max(0, nu.offsetLeft - v.clientWidth / 2)
}
