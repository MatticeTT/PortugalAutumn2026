import { BLAUW, CYAAN, LICHT, PLAN_KLEUR } from './kleuren'
import { extremen, hoogte, vensters, zon, type Extreem } from './getij'
import { kiesUur, lisDag, lisUur, sportNaam, staat, toonDag, toonTijd, utc, vliegNaar, WW } from './main'
import { bereken, k2, kant, type Tij } from './sportscore'
import type { Detail, ScoreRij } from './types'

const cache = new Map<string, Promise<Detail>>()
let huidig: Detail | null = null
const VENSTER_BREEDTE = () => {
  try { return Number(localStorage.getItem('vensterbreedte')) || 0.5 } catch { return 0.5 }
}

const el = () => document.getElementById('fiche')!
const fmt = (x: number | null | undefined, nd = 1) => (x == null ? '–' : x.toFixed(nd).replace('.', ','))
const kompas = (d: number) => ['N', 'NNO', 'NO', 'ONO', 'O', 'OZO', 'ZO', 'ZZO', 'Z', 'ZZW', 'ZW', 'WZW', 'W', 'WNW', 'NW', 'NNW'][Math.round(d / 22.5) % 16]
const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]!)
const TIJ: Tij[] = ['laag', 'op', 'hoog', 'af'] // codes 0..3 uit strand/<id>.json
const IPMA: Record<string, string> = { yellow: 'geel', orange: 'oranje', red: 'rood' }

// Tekeningen zoals in de Watersportwijzer: strand onderaan, zee bovenaan.
function svgDir(pad: string) {
  return `<svg viewBox="0 0 44 30" aria-hidden="true"><rect width="44" height="19" fill="var(--sea)"/><rect y="19" width="44" height="11" fill="var(--sand)"/>
    <path d="${pad}" fill="none" stroke="var(--tekst)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`
}
// De pijl wijst waar de wind naartoe blaast.
const RICHTINGEN = [
  { naam: 'aanlandig', svg: svgDir('M22 4v13M17 12l5 6 5-6') },
  { naam: 'schuin aanlandig', svg: svgDir('M13 5l15 11M21 16l8 1-2-8') },
  { naam: 'zijwind', svg: svgDir('M9 11h24M27 6l6 5-6 5') },
  { naam: 'schuin aflandig', svg: svgDir('M13 24l15-11M21 13l8-1-2 8') },
  { naam: 'aflandig', svg: svgDir('M22 26V8M17 13l5-6 5 6') },
]
const sector = (a: number) => (a < 22.5 ? 0 : a < 67.5 ? 1 : a <= 112.5 ? 2 : a < 157.5 ? 3 : 4)

function svgTij(h: number, pijl?: 'op' | 'af') {
  const y = 30 - h
  let p = ''
  if (pijl === 'op') p = `<path d="M34 ${y - 2}V6M30 10l4-5 4 5" fill="none" stroke="var(--tekst)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>`
  if (pijl === 'af') p = `<path d="M34 4v${y - 7}M30 ${y - 8}l4 5 4-5" fill="none" stroke="var(--tekst)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>`
  return `<svg viewBox="0 0 44 30" aria-hidden="true"><path d="M0 30L44 8v22z" fill="var(--sand)"/><rect y="${y}" width="44" height="${h}" fill="var(--sea)" opacity=".85"/>
    <path d="M0 ${y}h44" stroke="var(--tekst)" stroke-width="1.5" fill="none"/>${p}</svg>`
}
const GETIJ = [
  { naam: 'laag water', svg: svgTij(6) }, { naam: 'opkomend', svg: svgTij(13, 'op') },
  { naam: 'hoog water', svg: svgTij(22) }, { naam: 'afgaand', svg: svgTij(13, 'af') },
]

// Golfkammen, gedraaid naar de hoek waaronder ze binnenkomen.
function svgGolf(a: number, i: number) {
  const lijnen = [-2, 5, 12, 19].map((y) => `<path d="M-10 ${y}h64"/>`).join('')
  return `<svg viewBox="0 0 44 30" aria-hidden="true"><defs><clipPath id="gk${i}"><rect width="44" height="19"/></clipPath></defs>
    <rect width="44" height="19" fill="var(--sea)"/><rect y="19" width="44" height="11" fill="var(--sand)"/>
    <g clip-path="url(#gk${i})"><g transform="rotate(${a} 22 9.5)" fill="none" stroke="var(--tekst)" stroke-width="1.6" stroke-linecap="round">${lijnen}</g></g></svg>`
}
const GOLVEN = [{ a: 0, naam: 'recht binnen' }, { a: 45, naam: 'schuin' }, { a: 70, naam: 'erg schuin' }, { a: 100, naam: 'langs het strand' }]
const golfSoort = (theta: number) => (theta < 22.5 ? 0 : theta < 57.5 ? 1 : theta < 85 ? 2 : 3)

const KLASSEN: [number, string][] = [[1, 'open strand'], [0.6, 'half beschut'], [0.3, 'beschut'], [0.1, 'sterk beschut'], [0, 'lagune']]
const kNaam = (k: number) => KLASSEN.find(([v]) => k >= v)?.[1] ?? 'lagune'

function rij(items: { naam: string; svg: string }[], aan: number | null) {
  return `<div class="picts">${items.map((it, k) => `<div class="pict" ${k === aan ? 'aria-current="true"' : ''}>${it.svg}<span>${it.naam}</span></div>`).join('')}</div>`
}

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

function rekenUur(d: Detail, i: number) {
  return bereken(staat.index.sporten, {
    N: d.kijkrichting, K: d.K, BESTTIJ: d.BESTTIJ, DROOG: d.DROOG, LUWTE: d.LUWTE,
    H: d.wave_height?.[i] ?? null, T: d.piekperiode[i], GR: d.wave_direction?.[i] ?? null,
    V: d.wind[i], G: d.vlagen[i], WR: d.windrichting[i], TIJ: d.tij[i] == null ? null : TIJ[d.tij[i]!],
  })
}

// ---- WIND en WAVE (M5) ----

// Windpijl: wijst waar de wind naartoe waait.
function windpijl(dir: number | null, kn: number | null) {
  if (dir == null) return ''
  return `<svg width="58" height="58" viewBox="-29 -29 58 58" role="img" aria-label="wind uit ${kompas(dir)}">
    <circle r="27" fill="none" stroke="var(--lijn)"/>
    <g transform="rotate(${dir + 180})"><path d="M0 -22 L9 6 L0 0 L-9 6 Z" fill="var(--wind)"/></g>
    <text y="24" text-anchor="middle" font-size="9" fill="var(--zacht)">${Math.round(kn ?? 0)} kn</text></svg>`
}

// Golfje: groter en feller naarmate de golven groter zijn.
function golfje(hb: number, wave: number) {
  const s = Math.min(1, 0.25 + hb / 3)
  const kleur = BLAUW[Math.max(0, wave - 1)]
  const h = 10 + 34 * s
  return `<svg width="84" height="58" viewBox="0 0 84 58" role="img" aria-label="golf ${fmt(hb)} m">
    <path d="M2 56 C 20 56, 26 ${56 - h}, 46 ${56 - h} C 60 ${56 - h}, 66 ${56 - h * 0.55}, 58 ${56 - h * 0.35}
      C 70 ${56 - h * 0.5}, 76 52, 82 56 Z" fill="${kleur}" stroke="var(--golf)" stroke-width="1.2"/></svg>`
}

// Zelfde betekenis als in de legende.
const WW_SCHAAL = ['', 'de moeite niet', 'je kan proberen', 'ideaal voor beginners', 'sterk: voor gevorderden', 'gevaarlijk']

function wwScore(soort: 'WIND' | 'WAVE', n: number, reden: string, letOp = false) {
  const kleur = (soort === 'WIND' ? CYAAN : BLAUW)[n - 1] ?? '#ccc'
  return `<div class="ww-score ${LICHT(n) ? 'licht' : ''} ${n === 5 ? 'gevaar' : ''}" style="background:${kleur}">
    <span class="soort">${soort}</span><b>${n}${letOp ? '<i class="letop" title="wind van land">!</i>' : ''}</b><strong>${letOp ? 'te licht om te kiten, goed voor surf' : WW_SCHAAL[n]}</strong>
    <small>${esc(reden.replace(/^(WIND|WAVE) \d: /, ''))}</small></div>`
}

function wwBlok(d: Detail, i: number) {
  const row = d.score?.[i]
  if (!row) return ''
  const I = staat.index
  const [wind, wave, li, notas, red, hb, bereik, ws, warn] = row
  return `<div class="ww">
    <div class="label">${esc(I.labels[li])}</div>
    ${warn != null ? `<div class="waarschuwing">⚠ ${esc(I.teksten[warn])}</div>` : ''}
    <div class="ww-scores">${wwScore('WIND', wind, I.teksten[red[0]], !!row[10])}${wwScore('WAVE', wave, I.teksten[red[1]])}</div>
    <div class="beeld">
      <figure>${golfje(hb, wave)}<figcaption>op het strand<br>${fmt(bereik[0])}–${fmt(bereik[1])} m</figcaption></figure>
      <figure>${windpijl(d.windrichting[i], d.wind[i])}<figcaption>wind ${d.windrichting[i] != null ? 'uit ' + kompas(d.windrichting[i]!) : ''}</figcaption></figure>
    </div>
    ${ws != null ? `<p>${esc(I.teksten[ws])}</p>` : ''}
    ${notas.length ? `<ul class="notas">${notas.map((n) => `<li>${esc(I.notas[n])}</li>`).join('')}</ul>` : ''}</div>`
}



function omstandigheden(d: Detail, i: number, r: NonNullable<ReturnType<typeof rekenUur>>) {
  const x = r.x
  const wd = d.windrichting[i]
  const tij = d.tij[i]
  return `<div class="deel"><h4>Golven</h4>
      <p class="waarde">${fmt(d.wave_height?.[i])} m · ${fmt(d.piekperiode[i], 0)} s${d.wave_direction?.[i] != null ? ` · uit ${kompas(d.wave_direction[i])}` : ''}
        <span class="klein">aan het strand ${k2(x.GOLF)} m</span></p>
      ${x.K === 0 ? '<p class="klein">Lagune: hier breken geen golven.</p>' : rij(GOLVEN.map((g, k) => ({ naam: g.naam, svg: svgGolf(g.a, k) })), golfSoort(x.theta))}
    </div>
    <div class="deel"><h4>Wind</h4>
      <p class="waarde">${fmt(d.wind[i], 0)} kn · stoten ${fmt(d.vlagen[i], 0)} kn${wd != null ? ` · uit ${kompas(wd)} (${Math.round(wd)}°)` : ''}
        <span class="klein">${kant(x.a)}${x.luw ? ', in de luwte telt de helft' : ''}</span></p>
      ${rij(RICHTINGEN, sector(x.a))}
    </div>
    <div class="deel"><h4>Getij</h4>
      ${tij == null ? '<p class="klein">Geen getij voor dit uur.</p>' : rij(GETIJ, tij)}
    </div>`
}

function overStrand(d: Detail) {
  const delen = [
    `<li>Kijkt naar ${kompas(d.kijkrichting)} (${d.kijkrichting}°)${d.onzeker ? ', onzeker' : ''}.</li>`,
    `<li>${kNaam(d.K)} (strandfactor ${fmt(d.K)}, ${esc(d.K_bron)}).</li>`,
    `<li>Golfsurf werkt hier het best bij: ${d.BESTTIJ ? `${esc(d.BESTTIJ)} water` : 'niet gekend'}.</li>`,
    `<li>Bij laag water: ${d.DROOG ? 'valt het droog' : 'blijft er water'}.</li>`,
    d.LUWTE ? `<li>In de luwte bij wind uit ${d.LUWTE[0]}° tot ${d.LUWTE[1]}°.</li>` : '',
  ]
  const onzeker = d.onzeker ? `<p class="klein">Waarom onzeker: ${esc(d.redenen_onzeker.join('; '))}.</p>` : ''
  return `<details class="blok meer"><summary>Over dit strand</summary><ul class="uitleg">${delen.join('')}</ul>${onzeker}</details>`
}


function getijBlok(d: Detail, dagStart: number, dagEind: number, nu: number) {
  if (!d.getij) return ''
  const ex = extremen(staat.getij, d.getij.a, d.getij.b, d.getij.w)
  const van = dagStart / 60000, tot = dagEind / 60000
  const licht = zon(d.lat, d.lon, van + 720)
  const ven = vensters(ex, van, tot, VENSTER_BREEDTE(), licht)
  const W = 400, H = 110
  const x = (t: number) => ((t - van) / (tot - van)) * W
  const pts: string[] = []
  let lo = 9, hi = -9
  for (let t = van; t <= tot; t += 10) {
    const h = hoogte(ex, t)
    if (h == null) continue
    lo = Math.min(lo, h); hi = Math.max(hi, h)
  }
  lo = Math.min(lo, 0.3); hi = Math.max(hi, 3.8)
  const y = (h: number) => H - 14 - ((h - lo) / (hi - lo)) * (H - 30)
  for (let t = van; t <= tot; t += 10) {
    const h = hoogte(ex, t)
    if (h != null) pts.push(`${x(t).toFixed(1)},${y(h).toFixed(1)}`)
  }
  const dag = ex.filter((e) => e.t >= van && e.t <= tot)
  const nacht = licht ? `<rect x="0" y="0" width="${x(licht[0])}" height="${H}" fill="var(--lijn)" opacity=".45"/>
    <rect x="${x(licht[1])}" y="0" width="${W - x(licht[1])}" height="${H}" fill="var(--lijn)" opacity=".45"/>` : ''
  const vensterRect = ven.map(([a, b]) => `<rect x="${x(a)}" y="0" width="${x(b) - x(a)}" height="${H}" fill="var(--wind)" opacity=".18"/>`).join('')
  const labels = dag.map((e: Extreem) => `<text x="${x(e.t)}" y="${e.hoog ? y(e.h) - 5 : y(e.h) + 12}" text-anchor="middle"
      font-size="10" fill="var(--tekst)">${e.hoog ? 'HW' : 'LW'} ${toonTijd(e.t * 60000)}</text>`).join('')
  const nuLijn = nu >= van && nu <= tot ? `<line x1="${x(nu)}" x2="${x(nu)}" y1="0" y2="${H}" stroke="var(--accent)" stroke-dasharray="3 3"/>` : ''
  const uren = [6, 12, 18].map((u) => {
    const t = van + u * 60
    return `<text x="${x(t)}" y="${H - 2}" text-anchor="middle" font-size="9" fill="var(--zacht)">${String(u).padStart(2, '0')}u</text>`
  }).join('')
  const tijden = dag.map((e) => `<span>${e.hoog ? 'Hoogwater' : 'Laagwater'} ${toonTijd(e.t * 60000)} · ${fmt(e.h)} m</span>`).join('')
  const vtxt = ven.length ? ven.map(([a, b]) => `${toonTijd(a * 60000)}–${toonTijd(b * 60000)}`).join(', ') : 'geen bij daglicht'
  const nauw = d.getij.nauwkeurigheid !== '±5 min' ? `<p class="klein">Getijtijden ${esc(d.getij.nauwkeurigheid)}${d.getij.nota ? ': ' + esc(d.getij.nota) : ''}.</p>` : ''
  return `<div class="getij">
    <svg viewBox="0 0 ${W} ${H}" role="img" aria-label="getijcurve">${nacht}${vensterRect}
      <polyline points="${pts.join(' ')}" fill="none" stroke="var(--golf)" stroke-width="2"/>${labels}${nuLijn}${uren}</svg>
    <div class="tijden">${tijden}</div>
    <p class="klein">Surfvenster (midden tussen eb en vloed, bij daglicht): ${vtxt}. Hoogtes tegenover het Zero Hidrográfico.</p>${nauw}</div>`
}

// ---- Dagplan: wanneer kan je vandaag gaan? (pipeline/rules/dagplan.py) ----

const ACT_TEKST: Record<string, string> = {
  surf: 'Golfsurfen', wind: 'Kiten en windsurfen', windgolf: 'Windsurfen op golven', plat: 'Plat water: SUP, kajak, zwemmen',
}
const MIN_UREN = 2 // een sessie: minstens 2 uur na elkaar

// Uren na elkaar met minstens `min` (1 mogelijk, 2 goed), als [eerste uur, uur na het laatste].
function vensters2(code: string, idx: number[], min: number): [number, number][] {
  const out: [number, number][] = []
  let start = -1
  idx.forEach((i, k) => {
    const ok = Number(code[i] ?? 0) >= min
    if (ok && start < 0) start = k
    if ((!ok || k === idx.length - 1) && start >= 0) {
      const eind = ok ? k : k - 1
      if (eind - start + 1 >= MIN_UREN) out.push([idx[start], idx[eind]])
      start = -1
    }
  })
  return out
}

function dagplanBlok(d: Detail, idx: number[]) {
  const T = staat.index.tijd
  const uur = (i: number) => lisUur(utc(T[i]))
  // Binnen een "mogelijk"-venster: de losse uren die wel goed zijn (te kort voor een eigen venster).
  const beste = (code: string, v: [number, number][]) => {
    const u = v.flatMap(([a, b]) => idx.filter((i) => i >= a && i <= b && code[i] === '2')).map(uur)
    return u.length ? `beste om ${u.join(' en ')}u` : 'getij niet ideaal'
  }
  const tekst = (v: [number, number][]) => v.map(([a, b]) => `${uur(a)}–${uur(b) + 1}u`).join(' en ')
  const rijen = Object.keys(staat.index.activiteiten).map((a) => {
    const code = d.plan?.[a] ?? ''
    const goed = vensters2(code, idx, 2)
    const kan = vensters2(code, idx, 1).filter(([x, y]) => !goed.some(([g0, g1]) => g0 >= x && g1 <= y))
    const n = goed.length ? 2 : kan.length ? 1 : 0
    const zin = goed.length ? `<b>${tekst(goed)}</b>${kan.length ? ` <span class="klein">· ook mogelijk ${tekst(kan)}</span>` : ''}`
      : kan.length ? `mogelijk ${tekst(kan)} <span class="klein">(${beste(code, kan)})</span>` : '<span class="klein">vandaag niet</span>'
    return `<li class="${n ? '' : 'niet'}"><i class="stip" style="background:${PLAN_KLEUR[n]}">${n === 2 ? '✓' : n === 1 ? '~' : ''}</i>
      <span class="act">${ACT_TEKST[a]}</span><span class="uren">${zin}</span></li>`
  })
  const rows = d.score ?? []
  const gevaar = idx.filter((i) => rows[i] && (rows[i]![0] === 5 || rows[i]![1] === 5))
  const g = gevaar.length ? `<p class="waarschuwing">⚠ Gevaarlijk om ${gevaar.map(uur).join(', ')}u (WIND of WAVE 5).</p>` : ''
  return `<section class="dagplan"><h3>${esc(toonDag(utc(T[idx[0]])))} aan dit strand</h3><ul>${rijen.join('')}</ul>${g}
    <p class="klein">Alleen bij daglicht, minstens ${MIN_UREN} uur na elkaar. Surfen: WAVE 3 of 4, WIND 1 of 2 en het getij halverwege.
      <a href="rekenen.html#dagplan">Hoe bepaald?</a></p></section>`
}

// De dag in één oogopslag: per uur WIND, wind, WAVE, golf en het waterpeil, op één tijdlijn.
// De nacht is gedimd; het gekozen uur is omkaderd. Tik op een uur om het te kiezen.
function dagverloop(d: Detail, idx: number[], dagStart: number) {
  const T = staat.index.tijd
  const rows: (ScoreRij | null)[] = d.score ?? []
  const licht = zon(d.lat, d.lon, dagStart / 60000 + 720)
  const ex = d.getij ? extremen(staat.getij, d.getij.a, d.getij.b, d.getij.w) : []
  const peil = (i: number) => (ex.length ? hoogte(ex, utc(T[i]) / 60000) : null)
  const piek = (i: number) => {
    const t = utc(T[i]) / 60000
    const e = ex.find((x) => x.t >= t - 30 && x.t < t + 30)
    return e ? (e.hoog ? 'HW' : 'LW') : ''
  }
  const kol = (i: number) => {
    const t = utc(T[i]) / 60000
    const nacht = licht && (t + 30 < licht[0] || t - 30 > licht[1])
    return `${nacht ? 'nacht' : ''} ${i === staat.i ? 'nu' : ''}`
  }
  const cel = (i: number, html: string, stijl = '') => `<td class="${kol(i)}" style="${stijl}">${html}</td>`
  const ww = (i: number, k: 0 | 1) => {
    const n = rows[i]?.[k] ?? 0
    const pal = k === 0 ? CYAAN : BLAUW
    const l = k === 0 && rows[i]?.[10] ? '<i class="letop">!</i>' : ''
    return cel(i, `<b>${n || '–'}</b>${l}`, n ? `background:${pal[n - 1]};color:${LICHT(n) ? '#0d2530' : '#fff'}` : '')
  }
  const pijl = (i: number) => {
    const r = d.windrichting[i]
    return r == null ? '–' : `<span class="pijl" style="transform:rotate(${r + 180}deg)" title="uit ${kompas(r)}">↑</span>`
  }
  const balk = (i: number) => {
    const h = peil(i)
    if (h == null) return '–'
    const pct = Math.max(4, Math.min(100, (h / 4) * 100))
    return `<span class="peil" title="${fmt(h)} m"><i style="height:${pct}%"></i></span><small>${piek(i)}</small>`
  }
  const sport = staat.sport === WW ? '' : `<tr class="r-cijfer"><th>${esc(sportNaam(staat.sport))}</th>${idx.map((i) => {
    const n = Number(d.plan?.[staat.sport]?.[i] ?? 0)
    return cel(i, `<b>${n === 2 ? '✓' : n === 1 ? '~' : ''}</b>`, n ? `background:${PLAN_KLEUR[n]};color:${n === 2 ? '#fff' : '#2b1d00'}` : '')
  }).join('')}</tr>`
  return `<div class="tabel verloop"><table>
    <tr><th></th>${idx.map((i) => `<td class="${kol(i)}"><a href="#" data-i="${i}">${lisUur(utc(T[i]))}u</a></td>`).join('')}</tr>
    ${sport}
    <tr class="r-cijfer"><th>WIND</th>${idx.map((i) => ww(i, 0)).join('')}</tr>
    <tr><th>wind <small>kn</small></th>${idx.map((i) => cel(i, `${pijl(i)}<span>${fmt(d.wind[i], 0)}</span>`)).join('')}</tr>
    <tr class="r-cijfer"><th>WAVE</th>${idx.map((i) => ww(i, 1)).join('')}</tr>
    <tr><th>golf <small>m</small></th>${idx.map((i) => cel(i, `<span>${fmt(d.wave_height?.[i])}</span><small>${fmt(d.piekperiode[i], 0)} s</small>`)).join('')}</tr>
    <tr class="r-getij"><th>getij</th>${idx.map((i) => cel(i, balk(i))).join('')}</tr>
  </table></div>`
}

function ruweTabel(d: Detail, idx: number[]) {
  const pijl = (x: number | null) => (x == null ? '–' : `<span class="pijl" style="transform:rotate(${x + 180}deg)" title="${kompas(x)}">↑</span>`)
  const rij = (naam: string, f: (i: number) => string) => `<tr><td>${naam}</td>${idx.map((i) => `<td class="${i === staat.i ? 'nu' : ''}">${f(i)}</td>`).join('')}</tr>`
  // Een deelgolf van 0 m heeft geen periode of richting: dan een streepje.
  const leeg = (k: string, i: number) => {
    const h = k.replace(/_(period|direction)$/, '_height')
    return h !== k && !d[h]?.[i]
  }
  const n = (k: string, nd = 1) => (i: number) => (leeg(k, i) ? '–' : fmt(d[k]?.[i], nd))
  const p = (k: string) => (i: number) => (leeg(k, i) ? '–' : pijl(d[k]?.[i]))
  const tij = ['laag', 'op', 'hoog', 'af']
  return `<div class="tabel"><table>
    <tr><th>uur</th>${idx.map((i) => `<th class="${i === staat.i ? 'nu' : ''}">${lisUur(utc(staat.index.tijd[i]))}</th>`).join('')}</tr>
    ${rij('Wind (kn)', n('wind', 0))}${rij('Vlagen (kn)', n('vlagen', 0))}${rij('Windrichting', p('windrichting'))}
    ${rij('Golf (m)', n('wave_height'))}${rij('Piekperiode (s)', n('piekperiode', 0))}${rij('Golfrichting', p('wave_direction'))}
    ${rij('Deining 1 (m)', n('swell_wave_height'))}${rij('· periode (s)', n('swell_wave_period', 0))}${rij('· richting', p('swell_wave_direction'))}
    ${rij('Deining 2 (m)', n('secondary_swell_wave_height'))}${rij('· periode (s)', n('secondary_swell_wave_period', 0))}${rij('· richting', p('secondary_swell_wave_direction'))}
    ${rij('Windgolf (m)', n('wind_wave_height'))}${rij('· periode (s)', n('wind_wave_period', 0))}${rij('· richting', p('wind_wave_direction'))}
    ${rij('Op het strand, WAVE (m)', (i) => fmt(d.score?.[i]?.[5]))}
    ${rij('Golf aan het strand, sport (m)', n('GOLF'))}${rij('Ruwheid (m)', n('RUW'))}
    ${rij('Getij', (i) => (d.tij[i] == null ? '–' : tij[d.tij[i]!]))}
  </table></div>`
}

function render() {
  const d = huidig!
  const I = staat.index
  const i = staat.i
  const ms = utc(I.tijd[i])
  const dagKey = lisDag(ms)
  const idx = I.tijd.map((_, k) => k).filter((k) => lisDag(utc(I.tijd[k])) === dagKey)
  const dagStart = utc(I.tijd[idx[0]]) - lisUur(utc(I.tijd[idx[0]])) * 3600e3
  const r = rekenUur(d, i)
  const warn = d.ipma[i] && d.ipma[i] !== 'green' ? `<div class="waarschuwing">⚠ IPMA: waarschuwing zeegang (${IPMA[d.ipma[i]] ?? d.ipma[i]})</div>` : ''
  const kop = `<button class="sluit" aria-label="Sluiten">×</button>
    <h2>${esc(d.naam)}</h2>
    <div class="sub">${esc(d.district)} · ${toonDag(ms)} om ${toonTijd(ms)}</div>${warn}`
  if (!r) {
    el().innerHTML = `${kop}<p>Voor dit uur is er geen voorspelling.</p>`
    bind()
    return
  }
  el().innerHTML = `${kop}
    ${dagplanBlok(d, idx)}
    <section class="blok"><h3>Om ${toonTijd(ms)}</h3>${wwBlok(d, i)}</section>
    <section class="blok"><h3>${esc(toonDag(ms))} per uur</h3>${dagverloop(d, idx, dagStart)}
      <p class="klein">Tik op een uur. De nacht is grijs. Getij: het waterpeil, HW hoog water, LW laag water.</p></section>
    <details class="blok meer"><summary>Golven, wind en getij om ${toonTijd(ms)}</summary>${omstandigheden(d, i, r)}</details>
    <details class="blok meer"><summary>Getij in detail</summary>${getijBlok(d, dagStart, dagStart + 24 * 3600e3, ms / 60000)}</details>
    <details class="blok meer"><summary>Volledige voorspelling</summary>${ruweTabel(d, idx)}<p class="klein">${esc(I.bron)}.</p></details>
    ${overStrand(d)}
    <p class="blok klein">De cijfers zeggen of wind en golven passen. Ze kennen het strand zelf niet:
      stroming, rotsen, watertemperatuur, drukte en plaatselijke regels zitten er niet in. Volg altijd de redders en de vlaggen.
      Surf, kite en windsurf zijn verboden in zones voor baders.</p>`
  bind()
}

function bind() {
  el().querySelector('.sluit')?.addEventListener('click', sluitFiche)
  // De uurtabel naar het gekozen uur schuiven.
  const v = el().querySelector<HTMLElement>('.verloop')
  const nu = v?.querySelector<HTMLElement>('td.nu')
  if (v && nu) v.scrollLeft = Math.max(0, nu.offsetLeft - v.clientWidth / 2)
  el().querySelectorAll<HTMLAnchorElement>('a[data-i]').forEach((a) =>
    a.addEventListener('click', (e) => { e.preventDefault(); kiesUur(Number(a.dataset.i)) }))
}
