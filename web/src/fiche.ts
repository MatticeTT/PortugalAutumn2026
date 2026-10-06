import { KLEUR, tekstKleur } from './kleuren'
import { extremen, hoogte, vensters, zon, type Extreem } from './getij'
import { kiesSport, kiesUur, lisDag, lisUur, sportNaam, staat, toonDag, toonTijd, utc, vliegNaar } from './main'
import type { Detail } from './types'

const cache = new Map<string, Promise<Detail>>()
let huidig: Detail | null = null
const VENSTER_BREEDTE = () => {
  try { return Number(localStorage.getItem('vensterbreedte')) || 0.5 } catch { return 0.5 }
}

const el = () => document.getElementById('fiche')!
const fmt = (x: number | null | undefined, nd = 1) => (x == null ? '–' : x.toFixed(nd).replace('.', ','))
const kompas = (d: number) => ['N', 'NNO', 'NO', 'ONO', 'O', 'OZO', 'ZO', 'ZZO', 'Z', 'ZZW', 'ZW', 'WZW', 'W', 'WNW', 'NW', 'NNW'][Math.round(d / 22.5) % 16]
const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]!)
const TIJ = ['laag', 'opkomend', 'hoog', 'afgaand']
const TIJ_KORT = ['laag', 'op', 'hoog', 'af']
const IPMA: Record<string, string> = { yellow: 'geel', orange: 'oranje', red: 'rood' }

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

const cel = (n: number, extra = '') =>
  `<td class="cijfer ${extra}" style="background:${n ? KLEUR[n - 1] : 'transparent'};color:${n ? tekstKleur(n) : 'inherit'}">${n || '–'}</td>`

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
    <p class="klein">Surfvenster (midden tussen eb en vloed, bij daglicht): ${vtxt}. Hoogtes tegenover het Zero Hidrográfico.
      Het getij telt mee bij kiten op land (hoog water: geen strand), bij stranden die droogvallen en bij golfsporten als het beste getij van het strand gekend is.</p>${nauw}</div>`
}

function dagstrook(d: Detail, idx: number[]) {
  const c = d.cijfers[staat.sport] ?? ''
  return `<div class="tabel"><table>
    <tr><th>uur</th>${idx.map((i) => `<th class="${i === staat.i ? 'nu' : ''}"><a href="#" data-i="${i}">${lisUur(utc(staat.index.tijd[i]))}</a></th>`).join('')}</tr>
    <tr><td>${esc(sportNaam(staat.sport))}</td>${idx.map((i) => cel(Number(c[i] ?? 0), i === staat.i ? 'nu' : '')).join('')}</tr></table></div>`
}

function alleSporten(d: Detail, i: number) {
  const I = staat.index
  return Object.entries(I.groepen).map(([g, naam]) => `<div class="groep"><span class="klein">${esc(naam)}</span><div class="chips">
    ${I.sporten.filter((s) => s.groep === g).map((s) => {
      const n = Number(d.cijfers[s.id]?.[i] ?? 0)
      return `<button class="chip ${s.id === staat.sport ? 'gekozen' : ''}" data-sport="${s.id}"
        style="--c:${n ? KLEUR[n - 1] : 'transparent'};--t:${n ? tekstKleur(n) : 'inherit'}"><b>${n || '–'}</b> ${esc(s.naam)}</button>`
    }).join('')}</div></div>`).join('')
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
  return `<div class="tabel"><table>
    <tr><th>uur</th>${idx.map((i) => `<th class="${i === staat.i ? 'nu' : ''}">${lisUur(utc(staat.index.tijd[i]))}</th>`).join('')}</tr>
    ${rij('Wind (kn)', n('wind', 0))}${rij('Vlagen (kn)', n('vlagen', 0))}${rij('Windrichting', p('windrichting'))}
    ${rij('Golf (m)', n('wave_height'))}${rij('Piekperiode (s)', n('piekperiode', 0))}${rij('Golfrichting', p('wave_direction'))}
    ${rij('Deining 1 (m)', n('swell_wave_height'))}${rij('· periode (s)', n('swell_wave_period', 0))}${rij('· richting', p('swell_wave_direction'))}
    ${rij('Deining 2 (m)', n('secondary_swell_wave_height'))}${rij('· periode (s)', n('secondary_swell_wave_period', 0))}${rij('· richting', p('secondary_swell_wave_direction'))}
    ${rij('Windgolf (m)', n('wind_wave_height'))}${rij('· periode (s)', n('wind_wave_period', 0))}${rij('· richting', p('wind_wave_direction'))}
    ${rij('Surfgolf GOLF (m)', n('GOLF'))}${rij('Ruwheid RUW (m)', n('RUW'))}
    ${rij('Getij', (i) => (d.tij[i] == null ? '–' : TIJ_KORT[d.tij[i]!]))}
  </table></div>`
}

function strandGegevens(d: Detail) {
  const delen = [`strandfactor K ${fmt(d.K)} (${esc(d.K_bron)})`]
  if (d.BESTTIJ) delen.push(`beste getij: ${esc(d.BESTTIJ)}`)
  if (d.DROOG) delen.push('valt droog bij laag water')
  if (d.LUWTE) delen.push(`luwte bij wind uit ${d.LUWTE[0]}° tot ${d.LUWTE[1]}°`)
  const onzeker = d.onzeker ? ` Kijkrichting onzeker: ${esc(d.redenen_onzeker.join('; '))}.` : ''
  return `<p class="klein">Dit strand: kijkt naar ${kompas(d.kijkrichting)} (${d.kijkrichting}°), ${delen.join(', ')}.${onzeker}</p>`
}

function render() {
  const d = huidig!
  const I = staat.index
  const i = staat.i
  const ms = utc(I.tijd[i])
  const dagKey = lisDag(ms)
  const idx = I.tijd.map((_, k) => k).filter((k) => lisDag(utc(I.tijd[k])) === dagKey)
  const dagStart = utc(I.tijd[idx[0]]) - lisUur(utc(I.tijd[idx[0]])) * 3600e3
  const n = Number(d.cijfers[staat.sport]?.[i] ?? 0)
  const r = d.redenen[staat.sport]?.[i] ?? '0'
  const reden = r !== '0' ? I.redenen[r] : ''
  const warn = d.ipma[i] && d.ipma[i] !== 'green' ? `<div class="waarschuwing">⚠ IPMA: waarschuwing zeegang (${IPMA[d.ipma[i]] ?? d.ipma[i]})</div>` : ''
  const groot = n
    ? `<div class="score" style="background:${KLEUR[n - 1]};color:${tekstKleur(n)}">
        <b>${n}</b><span><strong>${esc(I.schaal[n - 1])}</strong>${reden ? `<small>${esc(reden)}</small>` : ''}</span></div>`
    : `<p>Voor dit uur is er geen cijfer: de voorspelling ontbreekt.</p>`
  el().innerHTML = `<button class="sluit" aria-label="Sluiten">×</button>
    <h2>${esc(d.naam)}</h2>
    <div class="sub">${esc(d.district)} · ${esc(sportNaam(staat.sport))} · ${toonDag(ms)} ${toonTijd(ms)}${d.tij[i] != null ? ` · getij ${TIJ[d.tij[i]!]}` : ''}</div>
    ${warn}${groot}
    <div class="blok"><h3>Deze dag</h3>${dagstrook(d, idx)}</div>
    <div class="blok"><h3>Alle sporten om ${toonTijd(ms)}</h3>${alleSporten(d, i)}</div>
    ${getijBlok(d, dagStart, dagStart + 24 * 3600e3, ms / 60000)}
    <div class="blok"><h3>Voorspelling</h3>${ruweTabel(d, idx)}
      <p class="klein">${esc(I.bron)}.</p>${strandGegevens(d)}</div>
    <div class="blok klein">Surf, kite en windsurf zijn verboden in zones voor baders (nationaal strandedict).
      Havenkapiteins leggen in het badseizoen afstanden op (Cascais: 300 m van badstranden).
      Niet in het cijfer: stroming, rotsen, watertemperatuur, drukte en of er redders zijn.
      De cijfers zijn geen veiligheidsadvies.</div>`
  bind()
}

function bind() {
  el().querySelector('.sluit')?.addEventListener('click', sluitFiche)
  el().querySelectorAll<HTMLAnchorElement>('a[data-i]').forEach((a) =>
    a.addEventListener('click', (e) => { e.preventDefault(); kiesUur(Number(a.dataset.i)) }))
  el().querySelectorAll<HTMLButtonElement>('button[data-sport]').forEach((b) =>
    b.addEventListener('click', () => kiesSport(b.dataset.sport!)))
}
