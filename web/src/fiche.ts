// De fiche van een strand, met de score van de rekenchat (versie 2.1, web/src/score.ts).
//   bovenaan  de dag: per groep (golfsporten, windsporten, stille waters) de uren met 3 of 4
//   per uur   de cirkels WIND en WAVE en stille waters
//   gekozen uur  per groep het cijfer, de rand en de scores van de categorieën (uitklapbaar: de deelscores)
//   gegevens  wind, golven op zee en op het strand, stroming, getij
// De fiche rekent zelf na met de invoer per uur (zelfde als de kaart), maar met jouw niveau en gewicht.
import { extremen, hoogte } from './getij'
import { uitpakken } from './inpakken'
import { conditiesUur } from './invoer'
import { BETEKENIS, BLAUW5, CYAAN5, RANDKLEUR, RANDUITLEG, STIL5, donkerCijfer } from './scorekaart'
import { CATEGORIES, GOLF, WIND, isStorm, score, strandUur, waarschuwingen, type Cond, type Groep, type StrandUur } from './score'
import { gewicht, niveau } from './surf'
import { waarschuwingBalk } from './waarschuwing'
import { data, kiesUur, lisDag, lisUur, staat, toonDag, toonTijd, utc, vliegNaar } from './main'
import type { Detail } from './types'

const cache = new Map<string, Promise<Detail>>()
let huidig: Detail | null = null

const el = () => document.getElementById('fiche')!
const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]!)
const kompas = (d: number) => ['N', 'NNO', 'NO', 'ONO', 'O', 'OZO', 'ZO', 'ZZO', 'Z', 'ZZW', 'ZW', 'WZW', 'W', 'WNW', 'NW', 'NNW'][Math.round(d / 22.5) % 16]
const windNaam = (phi: number) => phi < 22.5 ? 'recht aanlandig' : phi < 67.5 ? 'schuin aanlandig' : phi < 112.5 ? 'zijwind'
  : phi < 157.5 ? 'schuin aflandig' : 'recht aflandig'
const getal = (x: number | null | undefined, nd = 0) => (x == null ? '–' : x.toFixed(nd).replace('.', ','))

function laad(id: string): Promise<Detail> {
  if (!cache.has(id)) cache.set(id, data(`strand/${id.replace(/[^A-Za-z0-9_.-]/g, '_')}.json`).then(uitpakken))
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

// ---- Namen ----
const SPORTNAAM: Record<string, string> = {
  golfsurfen: 'Golfsurfen', longboard: 'Longboard', shortboard: 'Shortboard', windsurfen: 'Windsurfen',
  kitesurfen: 'Kitesurfen',
}
export function categorieNaam(k: string): string {
  const delen = k.split('_')
  const nv = delen[delen.length - 1]
  const golven = delen.includes('golven') ? ' op golven' : ''
  return `${SPORTNAAM[delen[0]] ?? delen[0]}${golven} · ${nv}`
}
const DEEL: Record<string, string> = {
  golf: 'golfhoogte', wind: 'wind', periode: 'periode', windrichting: 'windrichting', vlagen: 'vlagen',
  water: 'water aan het strand', golfrichting: 'golfrichting', zuiverheid: 'zuivere deining', stroming: 'stroming',
  getij: 'getij', neerslag: 'neerslag',
}

// ---- Rekenen per uur (met niveau en gewicht van de gebruiker) ----
function cond(d: Detail, i: number): Cond | null {
  const c = conditiesUur(d, i)
  if (!c) return null
  const g = gewicht()
  return g ? { ...c, gewicht: g } : c
}
function uurScore(d: Detail, i: number): StrandUur | null {
  const c = cond(d, i)
  return c ? strandUur(c, niveau()) : null
}

// ---- De dag: per groep de uren met 3 of 4 ----
type Venster = [number, number]
function vensters(idx: number[], goed: (i: number) => boolean): Venster[] {
  const out: Venster[] = []
  for (const i of idx) {
    if (!goed(i)) continue
    const laatste = out[out.length - 1]
    if (laatste && laatste[1] === i - 1) laatste[1] = i
    else out.push([i, i])
  }
  return out
}
const urenTekst = (v: Venster[]) => v.map(([a, b]) => `<span class="venster">${uurNr(a)}–${uurNr(b) + 1}u</span>`).join('')

function overzicht(per: Map<number, StrandUur>, idx: number[]) {
  const groepen = [
    { naam: 'Golfsporten', kleur: BLAUW5[3], foto: 'golfsurfen', cijfer: (u: StrandUur) => u.golf.cijfer },
    { naam: 'Windsporten', kleur: CYAAN5[3], foto: 'windsurfen', cijfer: (u: StrandUur) => u.wind.cijfer },
    { naam: 'Stille waters', kleur: STIL5[3], foto: 'plat-water', cijfer: (u: StrandUur) => u.stille_waters.cijfer },
  ]
  const rij = groepen.map((g) => {
    const v = vensters(idx, (i) => { const u = per.get(i); return !!u && g.cijfer(u) >= 3 })
    const max = Math.max(-1, ...idx.map((i) => { const u = per.get(i); return u ? g.cijfer(u) : -1 }))
    return { ...g, v, max }
  })
  const hoofd = rij.filter((r) => r.v.length).sort((a, b) => b.max - a.max)[0]
  const held = hoofd
    ? `<figure class="held" style="--kleur:${hoofd.kleur}"><img src="foto/${hoofd.foto}.webp" alt="">
        <figcaption><span class="zin">${hoofd.naam}: ${hoofd.max} ${BETEKENIS[hoofd.max]}</span><span class="uren">${urenTekst(hoofd.v)}</span></figcaption></figure>`
    : '<div class="held leeg"><span class="zin">Vandaag nergens 3 of 4</span></div>'
  const rest = rij.filter((r) => r !== hoofd).map((r) => `
    <li class="${r.v.length ? '' : 'niet'}" style="--kleur:${r.kleur};--uren:${r.kleur}">
      <img src="foto/${r.foto}.webp" alt=""><span class="kort">${r.naam}${r.max >= 0 ? ` <small>hoogste ${r.max}</small>` : ''}</span>
      <span class="uren">${r.v.length ? urenTekst(r.v) : 'geen 3 of 4'}</span></li>`).join('')
  return `${held}<ul class="rest">${rest}</ul>`
}

// ---- Per uur ----
function cel(g: Groep | null, pal: string[], kol: string) {
  if (!g) return `<td class="${kol}">–</td>`
  const kleur = g.te_veel ? '#111' : pal[g.cijfer]
  const tekst = g.te_veel ? '#fff' : donkerCijfer(g.cijfer) ? '#0d2530' : '#fff'
  const rand = g.rand ? `box-shadow:inset 0 0 0 3px ${RANDKLEUR[g.rand]};` : ''
  return `<td class="${kol}" style="background:${kleur};color:${tekst};${rand}" title="${g.te_veel ? 'te veel' : BETEKENIS[g.cijfer]}${g.rand ? ', ' + RANDUITLEG[g.rand] : ''}"><b>${g.cijfer}</b></td>`
}

function dag(d: Detail, idx: number[], per: Map<number, StrandUur>) {
  const T = staat.index.tijd
  const ex = d.getij ? extremen(staat.getij, d.getij.a, d.getij.b, d.getij.w) : []
  const kol = (i: number) => [i === staat.i ? 'nu' : '', d.licht[i] === '0' ? 'nacht' : ''].join(' ')
  const stil = (i: number) => {
    const u = per.get(i)
    if (!u) return `<td class="${kol(i)}">–</td>`
    const n = u.stille_waters.cijfer
    return `<td class="${kol(i)}" style="background:${STIL5[n]};color:${n <= 2 ? '#0d2530' : '#fff'}"><b>${n}</b></td>`
  }
  const storm = (i: number) => `<td class="${kol(i)}">${per.get(i)?.storm ? '<b class="storm">storm</b>' : ''}</td>`
  const getij = (i: number) => {
    const t = utc(T[i]) / 60000
    const h = ex.length ? hoogte(ex, t) : null
    const e = ex.find((x) => x.t >= t - 30 && x.t < t + 30)
    const pct = h == null ? 0 : Math.max(4, Math.min(100, (h / 4) * 100))
    return `<td class="${kol(i)}">${h == null ? '–' : `<span class="peil"><i style="height:${pct}%"></i></span>`}<small>${e ? (e.hoog ? 'hoog' : 'laag') : ''}</small></td>`
  }
  const heeftStorm = idx.some((i) => per.get(i)?.storm)
  return `<div class="dag"><table>
    <tr><th></th>${idx.map((i) => `<td class="${kol(i)}"><a href="#" data-i="${i}">${lisUur(utc(T[i]))}</a></td>`).join('')}</tr>
    <tr class="r-cijfer"><th>WIND</th>${idx.map((i) => cel(per.get(i)?.wind ?? null, CYAAN5, kol(i))).join('')}</tr>
    <tr class="r-cijfer"><th>WAVE</th>${idx.map((i) => cel(per.get(i)?.golf ?? null, BLAUW5, kol(i))).join('')}</tr>
    <tr class="r-cijfer"><th title="stille waters">stil</th>${idx.map(stil).join('')}</tr>
    ${heeftStorm ? `<tr><th></th>${idx.map(storm).join('')}</tr>` : ''}
    <tr class="r-getij"><th>getij</th>${idx.map(getij).join('')}</tr>
  </table></div>`
}

// ---- Het gekozen uur: per groep het cijfer en de categorieën ----
const pct = (x: number | null | undefined) => (x == null ? '–' : `${Math.round(x * 100)}%`)

function categorieLijst(c: Cond, g: Groep) {
  const namen = Object.keys(g.scores).sort((a, b) => g.scores[b] - g.scores[a])
  return `<ul class="categorieen">${namen.map((k) => {
    const r = score(k, c)
    const w = waarschuwingen(k, c)
    const deel = (o: Record<string, number | null>) => Object.entries(o).filter(([, v]) => v != null)
      .map(([n, v]) => `<li><span>${DEEL[n] ?? n}</span><b>${pct(v)}</b></li>`).join('')
    return `<li><details><summary><span class="cat">${categorieNaam(k)}${r.profiel ? ` <small>${esc(r.profiel)}</small>` : ''}</span>
        <span class="balk"><i style="width:${r.score}%"></i><em style="left:60%"></em></span><b>${Math.round(r.score)}</b></summary>
      ${r.veto ? `<p class="klein">0 door ${r.veto}</p>` : `<div class="deel"><h4>Essentieel</h4><ul>${deel(r.essentieel)}</ul>
        <h4>Bijkomend</h4><ul>${deel(r.bijkomend) || '<li><span>geen gegevens</span></li>'}</ul></div>`}
      ${w.length ? `<ul class="let-op">${w.map((x) => `<li>${esc(x)}</li>`).join('')}</ul>` : ''}
    </details></li>`
  }).join('')}</ul>`
}

function groepKaart(naam: string, g: Groep, pal: string[], c: Cond) {
  const kleur = g.te_veel ? '#111' : pal[g.cijfer]
  const tekst = g.te_veel || !donkerCijfer(g.cijfer) ? '#fff' : '#0d2530'
  const rand = g.rand ? `outline:4px solid ${RANDKLEUR[g.rand]};outline-offset:-4px;` : ''
  const zin = g.te_veel ? 'te veel: te gevaarlijk' : BETEKENIS[g.cijfer]
  return `<div class="groep">
    <div class="tegel" style="background:${kleur};color:${tekst};${rand}">
      <span class="soort">${naam}</span><b>${g.cijfer}</b><span class="betekenis">${zin}</span>
      ${g.rand ? `<span class="gegevens">${RANDUITLEG[g.rand]}</span>` : ''}
      ${g.cijfer >= 1 ? `<span class="gegevens">beste: ${categorieNaam(g.beste)}</span>` : ''}</div>
    ${categorieLijst(c, g)}</div>`
}

function gekozenUur(d: Detail, i: number) {
  if (d.onzeker?.length) {
    return `<div class="held leeg"><span class="zin">Geen score voor dit strand</span><small>${esc(d.onzeker.join('; '))}</small></div>`
  }
  const c = cond(d, i)
  if (!c) return '<p class="klein">Geen voorspelling voor dit uur.</p>'
  const u = strandUur(c, niveau())
  const st = u.stille_waters
  const melding = [u.storm ? '<p class="melding storm">Storm: wind vanaf 41 knopen of vlagen vanaf 48 knopen.</p>' : '',
    c.onweer ? '<p class="melding">Onweer: elke categorie 0.</p>' : '',
    c.donker ? '<p class="melding">Donker: elke categorie 0.</p>' : ''].join('')
  const stDeel = Object.entries({ ...st.essentieel, ...st.bijkomend }).filter(([, v]) => v != null)
    .map(([n, v]) => `<li><span>${DEEL[n] ?? n}</span><b>${pct(v as number)}</b></li>`).join('')
  return `${melding}<div class="groepen">
    ${groepKaart('WIND', u.wind, CYAAN5, c)}
    ${groepKaart('WAVE', u.golf, BLAUW5, c)}
    <div class="groep"><div class="tegel" style="background:${STIL5[st.cijfer]};color:${st.cijfer <= 2 ? '#0d2530' : '#fff'}">
      <span class="soort">Stille waters</span><b>${st.cijfer}</b><span class="betekenis">${BETEKENIS[st.cijfer]} · ${Math.round(st.score)}/100</span>
      <span class="gegevens">zwemmen, snorkelen, duiken, sup, e-foil</span></div>
      ${st.veto ? '' : `<details class="stil"><summary>deelscores</summary><div class="deel"><ul>${stDeel}</ul></div></details>`}</div>
  </div>
  ${niveau() || gewicht() ? `<p class="klein">Gerekend ${niveau() ? `voor niveau ${niveau()}` : ''}${niveau() && gewicht() ? ' en ' : ''}${gewicht() ? `met ${gewicht()} kg` : ''} (knop Surfen).</p>` : ''}`
}

// ---- Gegevens van het gekozen uur ----
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

function waveGegevens(d: Detail, i: number) {
  const r = d.zee_r?.[i]
  return `<span class="rijtjes">
    ${rijtje(ICOON.golf, `${getal(d.zee_h?.[i], 1)} m`, 'hoogte')}
    ${rijtje(ICOON.periode, `${getal(d.zee_t?.[i], 1)} s`, 'periode')}
    ${r == null ? '' : rijtje(pijl(r), kompas(r), 'richting')}</span>
    ${r == null ? '' : `<span class="tovstrand">${richtingTekening('golf', r, d.kust, d.venster)}
      <small>golf uit ${kompas(r)}</small></span>`}`
}


// Stroming (rekenchat): snelheid, richting waarheen, en hoeveel hoger of lager de golf daardoor wordt.
function stroming(d: Detail, i: number) {
  const kn = d.stroom?.[i], naar = d.stroom_naar?.[i], pct = d.stroom_pct?.[i]
  if (kn == null || naar == null || !(kn > 0)) return ''
  const golf = pct == null ? '' : pct === 0 ? ', golf even hoog' : `, golf ${Math.abs(pct)}% ${pct > 0 ? 'hoger' : 'lager'}`
  return `<p class="opstrand stroming">Stroming: <b>${getal(kn, 1)} kn</b> naar ${kompas(naar)}${golf}</p>`
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

function opStrand(d: Detail, i: number) {
  if (d.gh?.[i] == null) return ''
  const stroom = d.st?.[i] && 'tmd'.includes(d.st[i]) ? { t: 'tegen de wind in', m: 'mee met de wind', d: 'dwars op de wind' }[d.st[i] as 't' | 'm' | 'd'] : null
  return `<h3 class="kop">Op dit strand</h3><ul class="extras opstrand-lijst">
    <li><span>hoofdgolf</span><b>${getal(d.gh[i], 2)} m · ${getal(d.gt?.[i], 1)} s</b><small>golfhoek ${getal(d.gk?.[i])}°</small></li>
    <li><span>alle golven samen</span><b>${getal(d.gs?.[i], 2)} m</b><small>${d.ga?.[i] == null ? '' : `hoofdgolf ${pct(d.ga[i])} van de energie`}</small></li>
    <li><span>windhoek</span><b>${getal(d.wh?.[i])}°</b><small>${d.wh?.[i] == null ? '' : windNaam(d.wh[i]!)}</small></li>
    ${stroom ? `<li><span>stroming</span><b>${getal(d.stroom?.[i], 1)} kn</b><small>${stroom}</small></li>` : ''}
    ${d.ns?.[i] != null ? `<li><span>neerslag</span><b>${getal(d.ns[i], 1)} mm</b><small>per uur</small></li>` : ''}
  </ul>${stroming(d, i)}`
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
      · verval ${getal(d.verval[i], 1)} m
      <small>${k > 0 ? `${ex[k].hoog ? 'hoog' : 'laag'} om ${toonTijd(ex[k].t * 60000)}` : ''}</small></span></li></ul>`
}

function render() {
  const d = huidig!
  const I = staat.index
  const i = staat.i
  const ms = utc(I.tijd[i])
  const idx = I.tijd.map((_, k) => k).filter((k) => lisDag(utc(I.tijd[k])) === lisDag(ms))
  const per = new Map<number, StrandUur>()
  if (!d.onzeker?.length) for (const k of idx) { const u = uurScore(d, k); if (u) per.set(k, u) }
  const wind = d.wind[i] != null
  el().innerHTML = `<button class="sluit" aria-label="Sluiten">×</button>
    <h2>${esc(d.naam)}</h2>
    <div class="sub">${toonDag(ms)}</div>
    ${d.nota ? `<p class="vastenota">${esc(d.nota)}</p>` : ''}
    ${waarschuwingBalk(d.waarschuwing?.[i], d.waarschuwingen, I.tijd[i])}
    ${d.onzeker?.length ? '' : overzicht(per, idx)}
    <h3 class="kop">Per uur</h3>
    ${dag(d, idx, per)}
    <h3 class="kop">Om ${toonTijd(ms)}${d.licht[i] === '0' ? ' <small>(donker)</small>' : ''}</h3>
    ${gekozenUur(d, i)}
    ${wind ? `<h3 class="kop">Wind en golven op zee</h3><div class="tegels gegevens-tegels">
      <div class="tegel licht"><span class="soort">golven op zee</span>${waveGegevens(d, i)}</div>
      <div class="tegel licht"><span class="soort">wind</span>${windGegevens(d, i)}</div></div>` : ''}
    ${opStrand(d, i)}
    ${extras(d, i)}
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

// voor tests en de planning
export { CATEGORIES, GOLF, WIND, isStorm }
