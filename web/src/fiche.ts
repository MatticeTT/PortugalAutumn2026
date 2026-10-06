import { BLAUW, CYAAN, LICHT } from './kleuren'
import { extremen, hoogte, vensters, zon, type Extreem } from './getij'
import { kiesUur, lisDag, lisUur, staat, toonDag, toonTijd, utc, vliegNaar } from './main'
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

// Windpijl: wijst waar de wind naartoe waait.
function windpijl(dir: number | null, kn: number | null) {
  if (dir == null) return ''
  return `<svg width="58" height="58" viewBox="-29 -29 58 58" role="img" aria-label="wind uit ${kompas(dir)}">
    <circle r="27" fill="none" stroke="var(--lijn)"/>
    <g transform="rotate(${dir + 180})"><path d="M0 -22 L9 6 L0 0 L-9 6 Z" fill="var(--wind)"/></g>
    <text y="24" text-anchor="middle" font-size="9" fill="var(--zacht)">${Math.round(kn ?? 0)} kn</text></svg>`
}

// Golfje: groter en feller naarmate de golven groter zijn (zoals in het prototype).
function golfje(hb: number, wave: number) {
  const s = Math.min(1, 0.25 + hb / 3)
  const kleur = BLAUW[Math.max(0, wave - 1)]
  const h = 10 + 34 * s
  return `<svg width="84" height="58" viewBox="0 0 84 58" role="img" aria-label="golf ${fmt(hb)} m">
    <path d="M2 56 C 20 56, 26 ${56 - h}, 46 ${56 - h} C 60 ${56 - h}, 66 ${56 - h * 0.55}, 58 ${56 - h * 0.35}
      C 70 ${56 - h * 0.5}, 76 52, 82 56 Z" fill="${kleur}" stroke="var(--golf)" stroke-width="1.2"/></svg>`
}

function scoreBlok(soort: 'WIND' | 'WAVE', n: number, reden: string) {
  const kleur = (soort === 'WIND' ? CYAAN : BLAUW)[n - 1] ?? '#ccc'
  return `<div class="score ${LICHT(n) ? 'licht' : ''} ${n === 5 ? 'gevaar' : ''}" style="background:${kleur}">
    <b>${soort} ${n}</b><small>${esc(reden.replace(/^(WIND|WAVE) \d: /, ''))}</small></div>`
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
  return `<div class="blok getij"><h3>Getij</h3>
    <svg viewBox="0 0 ${W} ${H}" role="img" aria-label="getijcurve">${nacht}${vensterRect}
      <polyline points="${pts.join(' ')}" fill="none" stroke="var(--golf)" stroke-width="2"/>${labels}${nuLijn}${uren}</svg>
    <div class="tijden">${tijden}</div>
    <p class="klein">Surfvenster (midden tussen eb en vloed, bij daglicht): ${vtxt}. Hoogtes tegenover het Zero Hidrográfico. Het getij verandert de scores niet.</p>${nauw}</div>`
}

function dagstrook(rows: (ScoreRij | null)[], idx: number[]) {
  const cel = (n: number, pal: string[]) => `<td style="background:${pal[n - 1] ?? 'transparent'};color:${LICHT(n) ? '#0d2530' : '#fff'}">${n || '–'}</td>`
  return `<div class="tabel"><table><tr><th>uur</th>${idx.map((i) => `<th class="${i === staat.i ? 'nu' : ''}"><a href="#" data-i="${i}">${lisUur(utc(staat.index.tijd[i]))}</a></th>`).join('')}</tr>
    <tr><td>WIND</td>${idx.map((i) => cel(rows[i]?.[0] ?? 0, CYAAN)).join('')}</tr>
    <tr><td>WAVE</td>${idx.map((i) => cel(rows[i]?.[1] ?? 0, BLAUW)).join('')}</tr></table></div>`
}

function ruweTabel(s: any, idx: number[]) {
  const pijl = (d: number | null) => (d == null ? '–' : `<span class="pijl" style="transform:rotate(${d + 180}deg)" title="${kompas(d)}">↑</span>`)
  const rij = (naam: string, f: (i: number) => string) => `<tr><td>${naam}</td>${idx.map((i) => `<td class="${i === staat.i ? 'nu' : ''}">${f(i)}</td>`).join('')}</tr>`
  // Een deelgolf van 0 m heeft geen periode of richting: dan een streepje.
  const leeg = (k: string, i: number) => {
    const h = k.replace(/_(period|direction)$/, '_height')
    return h !== k && !s[h]?.[i]
  }
  const n = (k: string, nd = 1) => (i: number) => (leeg(k, i) ? '–' : fmt(s[k]?.[i], nd))
  const p = (k: string) => (i: number) => (leeg(k, i) ? '–' : pijl(s[k]?.[i]))
  return `<div class="tabel"><table>
    <tr><th>uur</th>${idx.map((i) => `<th class="${i === staat.i ? 'nu' : ''}">${lisUur(utc(staat.index.tijd[i]))}</th>`).join('')}</tr>
    ${rij('Wind (kn)', n('wind', 0))}${rij('Vlagen (kn)', n('vlagen', 0))}${rij('Windrichting', p('windrichting'))}
    ${rij('Golf (m)', n('wave_height'))}${rij('Periode (s)', n('wave_period', 0))}${rij('Golfrichting', p('wave_direction'))}
    ${rij('Deining 1 (m)', n('swell_wave_height'))}${rij('· periode (s)', n('swell_wave_period', 0))}${rij('· richting', p('swell_wave_direction'))}
    ${rij('Deining 2 (m)', n('secondary_swell_wave_height'))}${rij('· periode (s)', n('secondary_swell_wave_period', 0))}${rij('· richting', p('secondary_swell_wave_direction'))}
    ${rij('Windgolf (m)', n('wind_wave_height'))}${rij('· periode (s)', n('wind_wave_period', 0))}${rij('· richting', p('wind_wave_direction'))}
    ${rij('Op het strand (m)', (i) => fmt(s.score[i]?.[5]))}
  </table></div>`
}

function render() {
  const d = huidig!
  const I = staat.index
  const s = d.standen[staat.stand]
  const i = staat.i
  const row = s?.score[i]
  const ms = utc(I.tijd[i])
  const dagKey = lisDag(ms)
  const idx = I.tijd.map((_, k) => k).filter((k) => lisDag(utc(I.tijd[k])) === dagKey)
  const dagStart = utc(I.tijd[idx[0]]) - lisUur(utc(I.tijd[idx[0]])) * 3600e3
  const kop = `<button class="sluit" aria-label="Sluiten">×</button>
    <h2>${esc(d.naam)}</h2><div class="sub">${esc(d.district)} · kijkt naar ${kompas(d.kijkrichting)} (${d.kijkrichting}°) · ${toonDag(ms)} ${toonTijd(ms)}</div>`
  if (!row) {
    el().innerHTML = `${kop}<p>Voor dit uur is er geen voorspelling van ${esc(I.standen[staat.stand].naam)}.</p>`
    bind()
    return
  }
  const [wind, wave, li, notas, red, hb, bereik, ws, warn] = row
  const notaTxt = notas.map((n) => I.notas[n])
  const onzeker = d.onzeker ? `<p class="klein">Kijkrichting onzeker: ${esc(d.redenen_onzeker.join('; '))}.</p>` : ''
  el().innerHTML = `${kop}
    <div class="label">${esc(I.labels[li])}</div>
    ${warn != null ? `<div class="waarschuwing">⚠ ${esc(I.teksten[warn])}</div>` : ''}
    <div class="scores">${scoreBlok('WIND', wind, I.teksten[red[0]])}${scoreBlok('WAVE', wave, I.teksten[red[1]])}</div>
    <div class="beeld">
      <figure>${golfje(hb, wave)}<figcaption>op het strand<br>${fmt(bereik[0])}–${fmt(bereik[1])} m</figcaption></figure>
      <figure>${windpijl(s.windrichting[i], s.wind[i])}<figcaption>wind ${s.windrichting[i] != null ? 'uit ' + kompas(s.windrichting[i]!) : ''}</figcaption></figure>
    </div>
    ${ws != null ? `<p>${esc(I.teksten[ws])}</p>` : ''}
    ${notaTxt.length ? `<ul class="notas">${notaTxt.map((t) => `<li>${esc(t)}</li>`).join('')}</ul>` : ''}
    ${onzeker}
    <div class="blok"><h3>Deze dag</h3>${dagstrook(s.score, idx)}</div>
    ${getijBlok(d, dagStart, dagStart + 24 * 3600e3, ms / 60000)}
    <div class="blok"><h3>Voorspelling (${esc(s.bron)})</h3>${ruweTabel(s, idx)}</div>
    <div class="blok klein">Surf, kite en windsurf zijn verboden in zones voor baders (nationaal strandedict).
      Havenkapiteins leggen in het badseizoen afstanden op (Cascais: 300 m van badstranden).
      De scores zijn geen veiligheidsadvies.</div>`
  bind()
}

function bind() {
  el().querySelector('.sluit')?.addEventListener('click', sluitFiche)
  el().querySelectorAll<HTMLAnchorElement>('a[data-i]').forEach((a) =>
    a.addEventListener('click', (e) => { e.preventDefault(); kiesUur(Number(a.dataset.i)) }))
}
