// Laag "Klimmen": rotsklim- en boulderplekken op het vasteland van Portugal. Los van de surfberekening.
// Elk punt komt uit een bron (OpenStreetMap, Camptocamp of eigen invoer); niets wordt verzonnen.
// - aparte iconen: boulder (lichtbruin, afgerond vierkant) en sport/trad/onbekend (donkerbruin, pil)
// - filter op discipline en op graadbereik; clusters bij uitzoomen
// - rode rand: het regent dat uur (pipeline/klim/weer.py)
// - eigen invoer (import CSV/GeoJSON of formulier) wordt in deze browser bewaard en gaat altijd voor
import type { GeoJSONSource, Map as Kaart } from 'maplibre-gl'
import { data, staat, toonDag, toonTijd, utc, vliegNaar } from './main'

interface Graad { min: string | null; max: string | null; soort: 'eigen' | 'bereik' | 'omgerekend'; gemiddeld?: string; romeins?: boolean; toelichting?: string }
interface Bron { bron: string; id: string; link: string | null; datum: string | null }
export interface KlimPlek {
  id: string; naam: string | null; lat: number; lon: number; soort: string; disciplines: string[]
  routes: number | string | null; schaal: 'frans' | 'font'; graad: Graad | null; frans: Graad | null; font: Graad | null
  rots: string | null; richting: string | null; bronnen: Bron[]; w?: string | null; eigen?: boolean; lokaal?: boolean
}
interface Weer {
  neerslag: (number | null)[]; vocht: (number | null)[]; temp: (number | null)[]; wind: (number | null)[]
  sinds: (number | null)[]; regen24: (number | null)[]; terug: number
}
interface Status { [bron: string]: { ok: boolean; opgehaald?: string | null; fout?: string; geprobeerd?: string } }

const BRUIN = '#6B4226', LICHTBRUIN = '#B5803A', ROOD = '#e0242f'
const SOORT: Record<string, string> = { gebied: 'gebied', boulder: 'boulder', route: 'route', onbekend: 'onbekend' }
const DISC: Record<string, string> = { sport: 'sportklimmen', boulder: 'boulderen', trad: 'trad', onbekend: 'onbekend' }
const EIGEN_SLEUTEL = 'klim-eigen-v1'

let server: KlimPlek[] = []
let plekken: KlimPlek[] = []
let rood = new Map<string, string>()
let status: Status = {}
let kaart: Kaart
let open: KlimPlek | null = null
const weerCache = new Map<string, Promise<Weer>>()
const filter = { aan: true, sport: true, boulder: true, trad: true, onbekend: true, van: 0, tot: 99, zonderGraad: true }

const el = () => document.getElementById('fiche')!
const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]!)
const plat = (s: string | null) => (s ?? '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9 ]/g, ' ').split(/\s+/).filter(Boolean).join(' ')

// ---- graden (zelfde regels als pipeline/klim/graden.py) ----
const FRANS = /^[1-9][abc]?\+?$/, FONT = /^[1-9][ABC]?\+?$/
const ROMEINS = /^(XII|XI|X|IX|VIII|VII|VI|V|IV|III|II|I)[+-]?$/
// Volgorde van een graad, voor het filter. Romeinse cijfers (zoals in de bron) hebben geen zekere plaats: null.
function rangVan(g: string): number | null {
  if (ROMEINS.test(g)) return null
  const s = g.toLowerCase()
  const letter = 'abc'.indexOf(s[1] ?? '')
  return Number(s[0]) * 6 + (letter < 0 ? 0 : letter * 2) + (s.endsWith('+') ? 1 : 0)
}
const graadTekst = (g: Graad | null) => !g ? 'graad onbekend'
  : g.min && g.max ? (g.min === g.max ? g.min : `${g.min} – ${g.max}`) : g.min || g.max || 'graad onbekend'
const kort = (g: Graad | null) => !g ? '?' : g.min && g.max ? (g.min === g.max ? g.min : `${g.min}–${g.max}`) : g.min || g.max || '?'
const isBoulder = (p: KlimPlek) => p.disciplines.includes('boulder') && !p.disciplines.includes('sport') && !p.disciplines.includes('trad')

// ---- eigen invoer (deze browser) ----
function leesEigen(): KlimPlek[] {
  try { return JSON.parse(localStorage.getItem(EIGEN_SLEUTEL) ?? '[]') } catch { return [] }
}
function bewaarEigen(lijst: KlimPlek[]) {
  try { localStorage.setItem(EIGEN_SLEUTEL, JSON.stringify(lijst)) } catch { /* niet bewaard */ }
}
function eigenPlek(r: Record<string, string>, nr: number): KlimPlek | null {
  const lat = Number(String(r.lat ?? '').replace(',', '.')), lon = Number(String(r.lon ?? '').replace(',', '.'))
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return null
  let disc = (r.discipline ?? '').toLowerCase().split(/[;,/ ]+/).filter((d) => ['sport', 'boulder', 'trad'].includes(d))
  if (!disc.length) disc = ['onbekend']
  // Schaal uit de kolom "schaal" (Frans/Font), anders: Font als het alleen boulderen is.
  const schaal = (r.schaal ?? '').trim().toLowerCase()
  const boulder = schaal === 'font' || (!schaal && disc.length === 1 && disc[0] === 'boulder')
  const lees = (v?: string) => {
    const x = (v ?? '').trim().replace(/\s/g, '')
    if (!x) return null
    return boulder ? (FONT.test(x.toUpperCase()) ? x.toUpperCase() : null) : (FRANS.test(x.toLowerCase()) ? x.toLowerCase() : null)
  }
  const lo = lees(r.graad_min), hi = lees(r.graad_max)
  const om = (r.omgerekend ?? '').trim().toLowerCase().startsWith('ja')
  const g: Graad | null = lo || hi ? { min: lo, max: hi, soort: om ? 'omgerekend' : 'eigen', ...(om ? { toelichting: r.omgerekend.trim() } : {}) } : null
  const routes = (r.aantal_routes ?? '').trim()
  return {
    id: `eigen/${Date.now()}-${nr}`, naam: (r.naam ?? '').trim() || null, lat, lon, soort: 'onbekend', disciplines: disc,
    routes: routes ? (/^\d+$/.test(routes) ? Number(routes) : routes) : null,
    schaal: boulder ? 'font' : 'frans', graad: g, frans: boulder ? null : g, font: boulder ? g : null,
    rots: null, richting: null, eigen: true, lokaal: true,
    bronnen: [{ bron: `eigen invoer${r.bron ? ` (${r.bron})` : ''}`, id: 'eigen', link: (r.bron_url ?? '').trim() || null,
      datum: new Date().toISOString().slice(0, 10) }],
  }
}
function afstand(a: { lat: number; lon: number }, b: { lat: number; lon: number }) {
  const r = 6371000, t = Math.PI / 180
  const dp = (b.lat - a.lat) * t, dl = (b.lon - a.lon) * t
  const h = Math.sin(dp / 2) ** 2 + Math.cos(a.lat * t) * Math.cos(b.lat * t) * Math.sin(dl / 2) ** 2
  return 2 * r * Math.asin(Math.sqrt(h))
}
function gelijkeNaam(a: string | null, b: string | null) {
  const x = plat(a), y = plat(b)
  if (!x || !y) return false
  if (x === y || x.includes(y) || y.includes(x)) return true
  // gelijkenis zoals difflib (ratio ≥ 0,85), benaderd met de langste gemeenschappelijke deelreeks
  const m = Array.from({ length: x.length + 1 }, () => new Array(y.length + 1).fill(0))
  for (let i = 1; i <= x.length; i++) for (let j = 1; j <= y.length; j++)
    m[i][j] = x[i - 1] === y[j - 1] ? m[i - 1][j - 1] + 1 : Math.max(m[i - 1][j], m[i][j - 1])
  return (2 * m[x.length][y.length]) / (x.length + y.length) >= 0.85
}
// Eigen invoer gaat voor: een overeenkomende plek (150 m en gelijke naam) krijgt de eigen gegevens.
function samen() {
  plekken = server.map((p) => ({ ...p, bronnen: [...p.bronnen] }))
  const vrij = [...plekken] // eigen plekken worden niet met elkaar samengevoegd; één eigen rij per plek
  for (const e of leesEigen()) {
    const q = vrij.find((q) => afstand(e, q) <= 150 && gelijkeNaam(e.naam, q.naam))
    if (!q) { plekken.push({ ...e }); continue }
    q.lokaal = !q.w
    vrij.splice(vrij.indexOf(q), 1)
    for (const k of ['naam', 'lat', 'lon', 'disciplines', 'schaal', 'graad', 'frans', 'font', 'routes'] as const)
      if (e[k] != null && !(k === 'disciplines' && e.disciplines[0] === 'onbekend')) (q as any)[k] = e[k]
    q.bronnen = [...e.bronnen, ...q.bronnen]
    q.eigen = true
  }
}

// ---- kaart ----
function icoon(boulder: boolean, randRood: boolean, tekst: string) {
  const ratio = 2, h = 24
  const c = document.createElement('canvas'), g = c.getContext('2d')!
  const font = '700 12px system-ui, sans-serif'
  g.font = font
  const w = Math.max(h, Math.ceil(g.measureText(tekst).width) + 16)
  c.width = w * ratio; c.height = h * ratio
  g.scale(ratio, ratio)
  const r = boulder ? 5 : h / 2 // boulder: afgerond vierkant; sport en de rest: pil
  const vorm = (i: number) => { g.beginPath(); g.roundRect(i, i, w - 2 * i, h - 2 * i, Math.max(1, r - i)) }
  vorm(0); g.fillStyle = randRood ? ROOD : 'rgba(20,32,43,0.55)'; g.fill()
  vorm(randRood ? 3 : 1.5); g.fillStyle = boulder ? LICHTBRUIN : BRUIN; g.fill()
  g.font = font; g.fillStyle = '#fff'; g.textAlign = 'center'; g.textBaseline = 'middle'
  g.fillText(tekst, w / 2, h / 2 + 1)
  return { width: c.width, height: c.height, data: new Uint8Array(g.getImageData(0, 0, c.width, c.height).data.buffer) }
}
// Bolletje met het aantal plekken bij uitzoomen: wit, met rand en cijfer in de kleur van de laag.
export function groepIcoon(n: number, kleur: string) {
  const ratio = 2, s = n < 10 ? 28 : n < 100 ? 32 : 38
  const c = document.createElement('canvas'), g = c.getContext('2d')!
  c.width = c.height = s * ratio; g.scale(ratio, ratio)
  g.beginPath(); g.arc(s / 2, s / 2, s / 2 - 2, 0, Math.PI * 2)
  g.fillStyle = '#fff'; g.fill(); g.lineWidth = 3; g.strokeStyle = kleur; g.stroke()
  g.font = '800 13px system-ui, sans-serif'; g.fillStyle = kleur; g.textAlign = 'center'; g.textBaseline = 'middle'
  g.fillText(String(n), s / 2, s / 2 + 1)
  return { width: c.width, height: c.height, data: new Uint8Array(g.getImageData(0, 0, c.width, c.height).data.buffer) }
}

const graadRang = (p: KlimPlek) => {
  const g = p.graad
  const lo = g?.min ? rangVan(g.min) : null, hi = g?.max ? rangVan(g.max) : null
  if (lo == null && hi == null) return null
  return [lo ?? hi!, hi ?? lo!]
}
function zichtbaar(p: KlimPlek) {
  if (!p.disciplines.some((d) => (filter as any)[d])) return false
  const r = graadRang(p)
  if (!r) return filter.zonderGraad
  return r[1] >= filter.van && r[0] <= filter.tot // bereik overlapt het filter
}
function features() {
  const i = staat.i
  return {
    type: 'FeatureCollection' as const,
    features: filter.aan ? plekken.filter(zichtbaar).map((p) => ({
      type: 'Feature' as const, geometry: { type: 'Point' as const, coordinates: [p.lon, p.lat] },
      properties: { id: p.id, b: isBoulder(p) ? 1 : 0, g: kort(p.graad), r: /[12]/.test(rood.get(p.id)?.[i] ?? '') ? 1 : 0 },
    })) : [],
  }
}

export async function laadKlim(k: Kaart) {
  kaart = k
  try {
    ;[server, status] = await Promise.all([data('klim/kaart.json'), data('klim/status.json').catch(() => ({}))])
    const r: Record<string, string> = await data('klim/rood.json').catch(() => ({}))
    rood = new Map(Object.entries(r))
  } catch { server = [] }
  samen()
  kaart.on('styleimagemissing', (e) => {
    if (kaart.hasImage(e.id)) return
    const m = /^k\|([01])\|([01])\|(.*)$/.exec(e.id)
    if (m) kaart.addImage(e.id, icoon(m[1] === '1', m[2] === '1', m[3]), { pixelRatio: 2 })
    const n = /^kg\|(\d+)$/.exec(e.id)
    if (n) kaart.addImage(e.id, groepIcoon(Number(n[1]), BRUIN), { pixelRatio: 2 })
  })
  kaart.addSource('klim', { type: 'geojson', data: features(), cluster: true, clusterRadius: 40, clusterMaxZoom: 10,
    attribution: '© OpenStreetMap contributors (ODbL) · Camptocamp.org (CC BY-SA 3.0)' })
  kaart.addLayer({ id: 'klimgroepen', type: 'symbol', source: 'klim', filter: ['has', 'point_count'],
    layout: { 'icon-image': ['concat', 'kg|', ['to-string', ['get', 'point_count']]] as any, 'icon-allow-overlap': true } })
  kaart.addLayer({ id: 'klim', type: 'symbol', source: 'klim', filter: ['!', ['has', 'point_count']],
    layout: { 'icon-image': ['concat', 'k|', ['to-string', ['get', 'b']], '|', ['to-string', ['get', 'r']], '|', ['get', 'g']] as any,
      'icon-allow-overlap': true, 'symbol-sort-key': ['get', 'r'] } })
  kaart.on('click', 'klim', (e) => { const id = e.features?.[0]?.properties?.id; if (id) openKlim(id) })
  kaart.on('click', 'klimgroepen', async (e) => {
    const f = e.features![0]
    const z = await (kaart.getSource('klim') as GeoJSONSource).getClusterExpansionZoom(f.properties!.cluster_id)
    kaart.easeTo({ center: (f.geometry as any).coordinates, zoom: z })
  })
  for (const l of ['klim', 'klimgroepen']) {
    kaart.on('mouseenter', l, () => (kaart.getCanvas().style.cursor = 'pointer'))
    kaart.on('mouseleave', l, () => (kaart.getCanvas().style.cursor = ''))
  }
  paneel()
  const hash = decodeURIComponent(location.hash.slice(1))
  if (hash.startsWith('klim:')) openKlim(hash.slice(5))
}

export function ververs() {
  (kaart?.getSource('klim') as GeoJSONSource | undefined)?.setData(features())
  if (open && staat.open === `klim:${open.id}`) render()
}

// ---- paneel: aan/uit, filter, telling, meldingen, eigen invoer ----
const FRANSE = ['3', '4a', '4b', '4c', '5a', '5b', '5c', '6a', '6a+', '6b', '6b+', '6c', '6c+', '7a', '7a+', '7b', '7b+', '7c', '7c+', '8a', '8a+', '8b', '8b+', '8c', '8c+', '9a']

function telling() {
  const per = (f: (p: KlimPlek) => boolean) => plekken.filter(f).length
  const bronnen = new Map<string, number>()
  for (const p of plekken) for (const b of new Set(p.bronnen.map((b) => b.bron.startsWith('eigen') ? 'eigen invoer' : b.bron)))
    bronnen.set(b, (bronnen.get(b) ?? 0) + 1)
  const disc = ['sport', 'boulder', 'trad', 'onbekend'].map((d) => `${DISC[d]} ${per((p) => p.disciplines.includes(d))}`)
  return `<p class="klein"><b>${plekken.length} plekken</b>, ${per((p) => !!p.graad)} met een graad.<br>
    Per bron: ${[...bronnen].map(([b, n]) => `${esc(b)} ${n}`).join(' · ') || '–'}<br>
    Per discipline: ${disc.join(' · ')}</p>`
}
function meldingen() {
  const fout = Object.entries(status).filter(([, s]) => !s.ok)
  return fout.map(([b, s]) => `<p class="klimmelding">${b === 'osm' ? 'OpenStreetMap' : b === 'c2c' ? 'Camptocamp' : b}
    kon niet worden opgehaald; de laatst bewaarde gegevens${s.opgehaald ? ` (${s.opgehaald.slice(0, 10)})` : ''} worden getoond.</p>`).join('')
}

function paneel() {
  const knop = document.createElement('button')
  knop.className = 'klimknop'
  knop.textContent = 'Klimmen'
  knop.setAttribute('aria-expanded', 'false')
  const p = document.createElement('div')
  p.className = 'klimpaneel'
  p.hidden = true
  document.getElementById('kaart')!.append(knop, p)
  knop.onclick = () => { p.hidden = !p.hidden; knop.setAttribute('aria-expanded', String(!p.hidden)); if (!p.hidden) vul() }
  const vul = () => {
    const opties = (sel: number) => FRANSE.map((g) => `<option value="${rangVan(g)}" ${rangVan(g) === sel ? 'selected' : ''}>${g}</option>`).join('')
    p.innerHTML = `
      <label class="rij"><input type="checkbox" data-f="aan" ${filter.aan ? 'checked' : ''}> <b>Laag Klimmen tonen</b></label>
      <fieldset><legend>Discipline</legend>
        ${['sport', 'boulder', 'trad', 'onbekend'].map((d) => `<label><input type="checkbox" data-f="${d}" ${(filter as any)[d] ? 'checked' : ''}> ${DISC[d]}</label>`).join('')}
      </fieldset>
      <fieldset><legend>Graad (Frans, boulders volgens Font)</legend>
        <label>van <select data-g="van"><option value="0">alle</option>${opties(filter.van)}</select></label>
        <label>tot <select data-g="tot"><option value="99">alle</option>${opties(filter.tot)}</select></label>
        <label><input type="checkbox" data-f="zonderGraad" ${filter.zonderGraad ? 'checked' : ''}> ook zonder graad</label>
      </fieldset>
      ${meldingen()}
      ${telling()}
      <fieldset><legend>Eigen invoer (gaat voor)</legend>
        <label class="knop bestand">Importeer CSV of GeoJSON<input type="file" accept=".csv,.geojson,.json" hidden></label>
        <button class="knop" data-a="nieuw">Plek toevoegen</button>
        <button class="knop" data-a="export" ${leesEigen().length ? '' : 'disabled'}>Exporteer eigen plekken (CSV)</button>
        <p class="klein">Kolommen: naam, lat, lon, discipline (sport/boulder/trad), graad_min, graad_max, bron; mag ook: schaal, aantal_routes, omgerekend, bron_url.
          Eigen plekken staan alleen in deze browser; stuur de export door om ze voor iedereen op de kaart te zetten.</p>
      </fieldset>`
    p.querySelectorAll<HTMLInputElement>('input[data-f]').forEach((i) => i.onchange = () => { (filter as any)[i.dataset.f!] = i.checked; ververs() })
    p.querySelectorAll<HTMLSelectElement>('select[data-g]').forEach((s) => s.onchange = () => { (filter as any)[s.dataset.g!] = Number(s.value); ververs() })
    p.querySelector<HTMLInputElement>('input[type=file]')!.onchange = async (e) => {
      const f = (e.target as HTMLInputElement).files?.[0]
      if (!f) return
      const n = importeer(f.name, await f.text())
      samen(); ververs(); vul()
      p.insertAdjacentHTML('afterbegin', `<p class="klimmelding ok">${n} plekken ingelezen.</p>`)
    }
    p.querySelector<HTMLButtonElement>('[data-a=nieuw]')!.onclick = () => formulier(null)
    p.querySelector<HTMLButtonElement>('[data-a=export]')!.onclick = exporteer
  }
}

function csvRijen(tekst: string): Record<string, string>[] {
  const regels = tekst.replace(/^﻿/, '').split(/\r?\n/).filter((r) => r.trim())
  if (!regels.length) return []
  const scheid = regels[0].includes(';') && !regels[0].includes(',') ? ';' : ','
  const cel = (r: string) => {
    const uit: string[] = []; let cur = '', q = false
    for (let i = 0; i < r.length; i++) {
      const c = r[i]
      if (c === '"') { if (q && r[i + 1] === '"') { cur += '"'; i++ } else q = !q }
      else if (c === scheid && !q) { uit.push(cur); cur = '' } else cur += c
    }
    uit.push(cur)
    return uit.map((x) => x.trim())
  }
  const kop = cel(regels[0]).map((k) => k.toLowerCase())
  return regels.slice(1).map((r) => Object.fromEntries(cel(r).map((v, i) => [kop[i], v])))
}
function importeer(naam: string, tekst: string) {
  let rijen: Record<string, string>[] = []
  if (/\.(geo)?json$/i.test(naam)) {
    const gj = JSON.parse(tekst)
    rijen = (gj.features ?? []).filter((f: any) => f.geometry?.type === 'Point')
      .map((f: any) => ({ ...f.properties, lon: f.geometry.coordinates[0], lat: f.geometry.coordinates[1] }))
  } else rijen = csvRijen(tekst)
  const nieuw = rijen.map((r, i) => eigenPlek(r, i)).filter((x): x is KlimPlek => !!x)
  bewaarEigen([...leesEigen(), ...nieuw])
  return nieuw.length
}
function exporteer() {
  const e = leesEigen()
  const q = (v: unknown) => `"${String(v ?? '').replace(/"/g, '""')}"`
  const rijen = e.map((p) => [p.naam, p.lat, p.lon, p.disciplines.join(';'), p.graad?.min, p.graad?.max,
    p.bronnen[0]?.bron.replace(/^eigen invoer ?\(?|\)$/g, '')].map(q).join(','))
  const blob = new Blob([['naam,lat,lon,discipline,graad_min,graad_max,bron', ...rijen].join('\n')], { type: 'text/csv' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob); a.download = 'klimplekken-eigen.csv'; a.click()
}

// Formulier: één plek toevoegen, of een bestaande plek verbeteren (dan als eigen invoer op dezelfde plaats).
function formulier(p: KlimPlek | null) {
  open = null
  staat.open = 'klim:formulier'
  el().hidden = false
  const c = kaart.getCenter()
  const w = (v: unknown) => esc(String(v ?? ''))
  el().innerHTML = `<button class="sluit" aria-label="Sluiten">×</button>
    <h2>${p ? 'Plek verbeteren' : 'Plek toevoegen'}</h2>
    <form class="klimform">
      <label>Naam <input name="naam" value="${w(p?.naam)}" required></label>
      <label>Breedte (lat) <input name="lat" inputmode="decimal" value="${w(p?.lat ?? c.lat.toFixed(5))}" required></label>
      <label>Lengte (lon) <input name="lon" inputmode="decimal" value="${w(p?.lon ?? c.lng.toFixed(5))}" required></label>
      <label>Discipline <select name="discipline">
        ${['sport', 'boulder', 'trad'].map((d) => `<option ${p?.disciplines.includes(d) ? 'selected' : ''}>${d}</option>`).join('')}</select></label>
      <label>Laagste graad <input name="graad_min" placeholder="bv. 5c of 6A+" value="${w(p?.graad?.min)}"></label>
      <label>Hoogste graad <input name="graad_max" placeholder="bv. 7b of 7B" value="${w(p?.graad?.max)}"></label>
      <label>Bron <input name="bron" placeholder="bv. topo, eigen bezoek" value=""></label>
      <p class="klein">Frans voor routes (kleine letters, 6a+), Font voor boulders (hoofdletters, 6A+). Een graad
        die niet in die vorm staat, wordt niet bewaard.</p>
      <button class="knop" type="submit">Bewaren</button>
    </form>`
  el().querySelector('.sluit')!.addEventListener('click', sluit)
  el().querySelector('form')!.addEventListener('submit', (ev) => {
    ev.preventDefault()
    const r = Object.fromEntries(new FormData(ev.target as HTMLFormElement)) as Record<string, string>
    const nieuw = eigenPlek(r, 0)
    if (!nieuw) return
    bewaarEigen([...leesEigen(), nieuw])
    samen(); ververs(); openKlim(nieuw.id) || sluit()
  })
}

function sluit() { open = null; staat.open = null; el().hidden = true; history.replaceState(null, '', location.pathname) }

export function openKlim(id: string) {
  const p = plekken.find((q) => q.id === id) ?? plekken.find((q) => q.bronnen.some((b) => b.id === id))
  if (!p) return false
  open = p
  staat.open = `klim:${p.id}`
  el().hidden = false
  history.replaceState(null, '', `#${encodeURIComponent(`klim:${p.id}`)}`)
  vliegNaar(p.lon, p.lat, true)
  render()
  return true
}

const ROTS: Record<string, string> = {
  limestone: 'kalksteen', granite: 'graniet', sandstone: 'zandsteen', quartzite: 'kwartsiet', schist: 'schist',
  gneiss: 'gneis', basalt: 'basalt', conglomerate: 'conglomeraat', slate: 'leisteen', marble: 'marmer',
}
const rotsTekst = (r: string | null) => r ? r.split(';').map((x) => ROTS[x.trim().toLowerCase()] ?? x.trim()).join(', ') : 'onbekend'
const getal = (x: number | null | undefined, nd = 0) => (x == null ? '–' : x.toFixed(nd).replace('.', ','))

async function render() {
  const p = open!
  const i = staat.i
  const ms = utc(staat.index.tijd[i])
  let weer: Weer | null = null
  if (p.w) {
    if (!weerCache.has(p.w)) weerCache.set(p.w, data(`klim/weer/${p.w}.json`))
    weer = await weerCache.get(p.w)!.catch(() => null)
    if (open !== p || staat.i !== i) return
  }
  const r = rood.get(p.id)?.[i] ?? '-'
  const reden = r === '1' ? 'het regent' : r === '2' ? 'zandsteen is nog nat na regen' : ''
  const vocht = weer?.vocht[i]
  const nota = [
    vocht != null && vocht > 70 ? 'klam, minder grip' : '',
    weer?.regen24[i] && p.rots?.trim().toLowerCase() !== 'granite' ? 'rots kan nog nat zijn' : '',
  ].filter(Boolean)
  const sinds = weer?.sinds[i]
  const sindsTekst = weer == null || weer.neerslag[i] == null ? '–' : sinds == null ? `meer dan ${weer.terug + i} uur`
    : sinds === 0 ? 'regent nu' : `${sinds} uur`
  const g = p.graad
  const label = !g ? '<span class="label">graad onbekend</span>' : g.soort === 'omgerekend' ? `<span class="label">omgerekend${g.toelichting ? ` – ${esc(g.toelichting)}` : ''}</span>`
    : g.romeins ? '<span class="label">Romeins cijfer zoals in de bron, niet omgerekend</span>' : ''
  const ander = isBoulder(p) ? null : p.disciplines.includes('boulder') ? p.font : null // boulders in een gebied: Font apart
  const rij = (a: string, b: string) => `<tr><th>${a}</th><td>${b}</td></tr>`
  el().innerHTML = `<button class="sluit" aria-label="Sluiten">×</button>
    <h2>${esc(p.naam ?? 'Naam onbekend')}</h2>
    <div class="sub">${p.disciplines.map((d) => DISC[d]).join(', ')} · ${toonDag(ms)}</div>
    <div class="klimkop" style="--kleur:${isBoulder(p) ? LICHTBRUIN : BRUIN}">
      <span class="graadpil ${isBoulder(p) ? 'boulder' : ''} ${r === '1' || r === '2' ? 'rood' : ''}">${esc(kort(g))}</span>
      ${reden ? `<b class="reden">Slecht weer: ${reden}</b>` : ''}</div>
    <table class="klimtabel">
      ${rij('Discipline', p.disciplines.map((d) => DISC[d]).join(', '))}
      ${rij('Soort plek', SOORT[p.soort] ?? p.soort)}
      ${rij(`Graad ${p.schaal === 'font' ? '(Font)' : '(Frans)'}`, `${esc(graadTekst(g))} ${g ? label : ''}`)}
      ${g?.gemiddeld ? rij('Gemiddeld', esc(g.gemiddeld)) : ''}
      ${ander ? rij('Boulders (Font)', `${esc(graadTekst(ander))}${ander.soort === 'omgerekend' ? ' <span class="label">omgerekend</span>' : ''}`) : ''}
      ${rij('Aantal routes', p.routes == null ? 'onbekend' : String(p.routes))}
      ${rij('Rotssoort', esc(rotsTekst(p.rots)))}
    </table>
    <h3 class="kop">Weer om ${toonTijd(ms)}</h3>
    ${weer ? `<table class="klimtabel">
      ${rij('Neerslag', `${getal(weer.neerslag[i], 1)} mm`)}
      ${rij('Sinds de laatste regen', sindsTekst)}
      ${rij('Luchtvochtigheid', `${getal(vocht)}%`)}
      ${rij('Temperatuur', `${getal(weer.temp[i])} °C`)}
      ${rij('Wind', `${getal(weer.wind[i])} kn`)}
    </table>
    ${nota.length ? `<ul class="klimnota">${nota.map((n) => `<li>${n}</li>`).join('')}</ul>` : ''}`
    : `<p class="klein">${p.lokaal ? 'Nog geen weer: deze plek staat alleen in deze browser.' : 'Nog geen weer voor deze plek.'}</p>`}
    <h3 class="kop">Bron</h3>
    <ul class="klimbronnen">${p.bronnen.map((b) => `<li>${b.link ? `<a href="${esc(b.link)}" target="_blank" rel="noopener">${esc(b.bron)}</a>` : esc(b.bron)}
      ${b.datum ? `<small>opgehaald ${esc(b.datum.slice(0, 10))}</small>` : ''}</li>`).join('')}</ul>
    <p><a class="thecrag" href="https://www.thecrag.com/search?S=${encodeURIComponent(p.naam ?? '')}" target="_blank" rel="noopener">Zoek op theCrag</a>
      · <button class="linkknop" data-a="bewerk">Verbeteren</button></p>
    <p class="klein">Geen veiligheidsadvies.</p>`
  el().querySelector('.sluit')!.addEventListener('click', sluit)
  el().querySelector('[data-a=bewerk]')!.addEventListener('click', () => formulier(p))
}
