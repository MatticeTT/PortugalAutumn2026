import maplibregl, { type GeoJSONSource, type StyleSpecification } from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import './style.css'
import { themaKnop } from './thema'
import { bolletjeWW } from './kleuren'
import { openFiche, sluitFiche, toonUur } from './fiche'
import { zoekveld } from './zoek'
import { groepIcoon, laadKlim, openKlim, ververs as klimVervers } from './klim'
import type { Getij, Index, KaartStrand } from './types'
import { surfPaneel, toont } from './surf'
import { zoekInDeBuurt, bewaarVerblijf, komtViaTab, leesVerblijf, tabWissel, wisVerblijf, rijTekst, rijtijden, route, vraagVerblijf, type Verblijf } from './verblijf'

const TZ = 'Europe/Lisbon'
const fmtDag = new Intl.DateTimeFormat('nl-BE', { timeZone: TZ, weekday: 'short', day: 'numeric', month: 'short' })
const fmtUur = new Intl.DateTimeFormat('nl-BE', { timeZone: TZ, hour: '2-digit', minute: '2-digit' })
const fmtSleutel = new Intl.DateTimeFormat('en-CA', { timeZone: TZ, year: 'numeric', month: '2-digit', day: '2-digit' })
const fmtUurNr = new Intl.DateTimeFormat('en-GB', { timeZone: TZ, hour: '2-digit', hourCycle: 'h23' })

export const staat = {
  index: null as unknown as Index,
  stranden: [] as KaartStrand[],
  getij: null as unknown as Getij,
  cijfers: [] as string[], // per strand (volgorde van kaart.json) per uur 5 tekens, zie features()
  i: 0, // index in index.tijd
  open: null as string | null,
}

export const utc = (s: string) => Date.parse(s + ':00Z')
export const lisDag = (ms: number) => fmtSleutel.format(ms)
export const lisUur = (ms: number) => Number(fmtUurNr.format(ms))
export const toonTijd = (ms: number) => fmtUur.format(ms)
export const toonDag = (ms: number) => fmtDag.format(ms)

const OFM = 'https://tiles.openfreemap.org/styles/liberty'

// Wisselen tussen de tabbladen Kaart en Planning: het verblijf onthouden (zie tabWissel in verblijf.ts).
const viaTab = komtViaTab()
tabWissel()
themaKnop()

function reserveStijl(): StyleSpecification {
  const css = getComputedStyle(document.documentElement)
  return {
    version: 8,
    sources: { land: { type: 'geojson', data: '/basis/land.geojson', attribution: '© OpenStreetMap-bijdragers' } },
    layers: [
      { id: 'zee', type: 'background', paint: { 'background-color': css.getPropertyValue('--zee').trim() || '#cfe6f5' } },
      { id: 'land', type: 'fill', source: 'land', paint: { 'fill-color': css.getPropertyValue('--land').trim() || '#eef0e8' } },
      { id: 'kust', type: 'line', source: 'land', paint: { 'line-color': '#8aa0b0', 'line-width': 0.6 } },
    ],
  } as StyleSpecification
}

async function stijl(): Promise<StyleSpecification | string> {
  try {
    const ctl = new AbortController()
    const t = setTimeout(() => ctl.abort(), 4000)
    const r = await fetch(OFM, { signal: ctl.signal })
    clearTimeout(t)
    if (r.ok) return OFM
  } catch { /* geen OpenFreeMap: eigen eenvoudige kaart */ }
  return reserveStijl()
}

// De kaart opent uitgezoomd over heel Portugal; daarna vraagt ze waar je verblijft (eigenaar, 8 oktober 2026).
// Uitgezoomd over alle landen met stranden: Portugal, Spanje, Frankrijk en België.
const PORTUGAL: [[number, number], [number, number]] = [[-9.8, 36.0], [8.0, 51.4]]

// Per strand (volgorde van kaart.json) per uur 5 tekens: WIND en WAVE (level 1–4), het rode kader,
// de conclusie-letter (hoofdletter G/O/S/R = ideaal) en bij ideaal de score (a = 75, b = 76, …).
function features() {
  const i = staat.i
  return {
    type: 'FeatureCollection' as const,
    features: staat.stranden.flatMap((s, k) => {
      const rij = staat.cijfers[k] ?? ''
      const w = Number(rij[5 * i] ?? 0)
      const v = Number(rij[5 * i + 1] ?? 0)
      const l = rij[5 * i + 2] ?? '0' // rood kader: 1 wind van land, 2 golf komt niet aan, 3 beide
      if (!toont(rij[5 * i + 3] ?? '')) return [] // filters van de knop Surfen
      return [{ type: 'Feature' as const, geometry: { type: 'Point' as const, coordinates: [s.x, s.y] },
        properties: { id: s.id, naam: s.n, w, v, l } }]
    }),
  }
}

let kaart: maplibregl.Map
const BOL = 36 // diameter van een strandbolletje in px (was 44, iets kleiner op vraag van de eigenaar)
const perDag = new Map<string, number[]>()
const slider = () => document.getElementById('uur') as HTMLInputElement
const datumKeuze = () => document.getElementById('datum') as HTMLSelectElement

function ververs() {
  const src = kaart?.getSource('stranden') as GeoJSONSource | undefined
  src?.setData(features())
  const ms = utc(staat.index.tijd[staat.i])
  ;(document.getElementById('uurlabel') as HTMLOutputElement).value = toonTijd(ms)
  toonUur()
  klimVervers()
  tekenRoutes()
}

// ---- Verblijf: waar je verblijft en hoe lang je wil rijden ----
// Per sport de route naar de beste ideale plek dit uur binnen je rijtijd: eerst de hoogste score,
// dan de kortste rijtijd. De lijn krijgt de kleur van de sport.
const SPORTEN = [
  { letter: 'G', naam: 'Golfsurfen', kleur: '#2a6fdb', tekst: '#2a6fdb', prio: 4 },
  { letter: 'O', naam: 'Windsurfen op golven', kleur: '#f5c400', tekst: '#b38f00', prio: 3 },
  { letter: 'S', naam: 'Windsurfen', kleur: '#14b8d4', tekst: '#0e8fa6', prio: 2 },
  { letter: 'R', naam: 'Stille waters', kleur: '#8a949c', tekst: '#6b757d', prio: 1 },
]
let verblijf: Verblijf | null = null
let rij = new Map<string, number | null>()
let verblijfPunt: maplibregl.Marker | null = null
let routeBeurt = 0
let inBeeld = false // na een nieuwe keuze één keer verblijf en bestemmingen samen in beeld brengen

function besteDitUur() {
  const i = staat.i, max = verblijf?.max ?? 0
  const uit: { sport: (typeof SPORTEN)[number]; s: KaartStrand; score: number; min: number }[] = []
  for (const sport of SPORTEN) {
    let best: (typeof uit)[number] | null = null
    staat.stranden.forEach((s, k) => {
      const c = staat.cijfers[k] ?? ''
      if (c[5 * i + 3] !== sport.letter) return
      const m = rij.get(s.id)
      if (m == null || m > max) return
      const score = 75 + c.charCodeAt(5 * i + 4) - 97
      if (!best || score > best.score || (score === best.score && m < best.min)) best = { sport, s, score, min: m }
    })
    if (best) uit.push(best)
  }
  return uit
}

async function tekenRoutes() {
  const src = kaart?.getSource('routes') as GeoJSONSource | undefined
  const lijst = document.getElementById('routes')!
  if (!src || !verblijf) { lijst.hidden = true; return }
  const beurt = ++routeBeurt
  const v = verblijf
  const beste = besteDitUur()
  const lijnen = await Promise.all(beste.map((b) => route(v, { id: b.s.id, lat: b.s.y, lon: b.s.x }).catch(() => null)))
  if (beurt !== routeBeurt) return // intussen een ander uur gekozen
  // Alleen echte routes over de weg; lukt een route niet, dan geen lijn (nooit vogelvlucht).
  src.setData({ type: 'FeatureCollection', features: beste.flatMap((b, k) => lijnen[k]
    ? [{ type: 'Feature' as const, geometry: lijnen[k], properties: { kleur: b.sport.kleur, prio: b.sport.prio } }] : []) })
  const naam = (n: string) => n === n.toUpperCase() ? n.charAt(0) + n.slice(1).toLowerCase() : n
  lijst.innerHTML = beste.length
    ? beste.map((b) => `<li><button type="button" data-id="${b.s.id}" style="--kleur:${b.sport.kleur};--tekstkleur:${b.sport.tekst}"><b>${b.sport.naam}</b>
        <span>${naam(b.s.n).replace(/</g, '&lt;')}</span><em>${rijTekst(b.min)}</em></button></li>`).join('')
    : `<li class="rustig">Dit uur niets ideaal binnen ${rijTekst(v.max)}</li>`
  lijst.querySelectorAll<HTMLButtonElement>('button[data-id]').forEach((k) => { k.onclick = () => openFiche(k.dataset.id!) })
  lijst.hidden = false
  if (inBeeld && beste.length) {
    // Je verblijf blijft in het midden; zo ver uitzoomen dat ook de bestemmingen in beeld zijn
    // (maar niet verder dan zoom 10, zodat je de stranden zelf blijft zien).
    inBeeld = false
    const b = new maplibregl.LngLatBounds([v.lon, v.lat], [v.lon, v.lat])
    beste.forEach((x) => { b.extend([x.s.x, x.s.y]); b.extend([2 * v.lon - x.s.x, 2 * v.lat - x.s.y]) })
    const c = kaart.cameraForBounds(b, { padding: { top: 60, bottom: 40 + lijst.offsetHeight, left: 40, right: 40 }, maxZoom: 11 })
    kaart.easeTo({ center: [v.lon, v.lat], zoom: Math.max(10, c?.zoom ?? 10), duration: 1000 })
  }
}

function toonVerblijfKnop() {
  const k = document.getElementById('verblijfknop') as HTMLButtonElement
  k.innerHTML = verblijf
    ? `<span class="huisje" aria-hidden="true"></span>${verblijf.naam.split(',')[0].replace(/</g, '&lt;')} · ${rijTekst(verblijf.max)}`
    : 'Waar verblijf je?'
}

async function kiesVerblijf(v: Verblijf | null, vlieg = true) {
  verblijf = v
  toonVerblijfKnop()
  verblijfPunt?.remove(); verblijfPunt = null
  if (!v) { rij = new Map(); tekenRoutes(); return }
  bewaarVerblijf(v)
  const el = document.createElement('div')
  el.className = 'verblijfpunt'
  el.title = v.naam
  verblijfPunt = new maplibregl.Marker({ element: el }).setLngLat([v.lon, v.lat]).addTo(kaart)
  if (vlieg) { kaart.flyTo({ center: [v.lon, v.lat], zoom: v.max <= 45 ? 10.5 : 10, speed: 1.4 }); inBeeld = true }
  try {
    rij = await rijtijden(v, staat.stranden.map((s) => ({ id: s.id, lat: s.y, lon: s.x })))
  } catch {
    rij = new Map()
    document.getElementById('routes')!.innerHTML = '<li class="rustig">Rijtijden lukken nu niet (OpenStreetMap-routeplanner). Probeer later opnieuw.</li>'
    document.getElementById('routes')!.hidden = false
    return
  }
  if (verblijf === v) tekenRoutes()
}

// Via de knop bovenaan: het huidige verblijf staat al ingevuld. Bij herladen: een lege vraag.
async function vraag(leeg = false) {
  const c = kaart.getCenter()
  zoekInDeBuurt(c.lng, c.lat) // zoeken: plaatsen rond het midden van de kaart eerst
  const v = await vraagVerblijf(leeg ? null : verblijf ?? leesVerblijf())
  if (v) kiesVerblijf(v)
  else if (leeg) { wisVerblijf(); kiesVerblijf(null) } // overgeslagen na herladen: geen verblijf
}

function zetDag(k: string) {
  const idx = perDag.get(k)!
  const T = staat.index.tijd
  const huidig = lisUur(utc(T[staat.i]))
  const best = idx.reduce((a, b) => (Math.abs(lisUur(utc(T[b])) - huidig) < Math.abs(lisUur(utc(T[a])) - huidig) ? b : a))
  staat.i = best
  datumKeuze().value = k
  const s = slider()
  s.min = String(lisUur(utc(T[idx[0]])))
  s.max = String(lisUur(utc(T[idx[idx.length - 1]])))
  s.value = String(lisUur(utc(T[best])))
  ververs()
}

function dagen() {
  staat.index.tijd.forEach((t, i) => {
    const k = lisDag(utc(t))
    if (!perDag.has(k)) perDag.set(k, [])
    perDag.get(k)!.push(i)
  })
  const sel = datumKeuze()
  for (const [k, idx] of perDag) {
    const o = document.createElement('option')
    o.value = k
    o.textContent = toonDag(utc(staat.index.tijd[idx[0]]))
    sel.appendChild(o)
  }
  sel.onchange = () => zetDag(sel.value)
  slider().oninput = () => {
    const idx = perDag.get(lisDag(utc(staat.index.tijd[staat.i])))!
    const want = Number(slider().value)
    staat.i = idx.find((i) => lisUur(utc(staat.index.tijd[i])) === want) ?? staat.i
    ververs()
  }
  // Standaard het huidige uur.
  const nu = Date.now()
  staat.i = staat.index.tijd.reduce((a, t, i) => (Math.abs(utc(t) - nu) < Math.abs(utc(staat.index.tijd[a]) - nu) ? i : a), 0)
  zetDag(lisDag(utc(staat.index.tijd[staat.i])))
}

export function kiesUur(i: number) {
  staat.i = i
  datumKeuze().value = lisDag(utc(staat.index.tijd[i]))
  zetDag(datumKeuze().value)
}




// Kaart en fiche moeten uit dezelfde berekening komen. Daarom haalt de app elk databestand op met het
// tijdstip van de berekening (index.json, "gemaakt") erbij. Komt er een nieuwe berekening terwijl de
// pagina openstaat, dan laadt de pagina opnieuw: anders toont de kaart de oude en de fiche de nieuwe.
const vers = () => fetch('data/index.json', { cache: 'no-store' }).then((r) => r.json())
export const data = (pad: string) => fetch(`data/${pad}?v=${encodeURIComponent(staat.index.gemaakt)}`).then((r) => r.json())

async function nieuweBerekening() {
  try {
    if ((await vers()).gemaakt !== staat.index.gemaakt) location.reload()
  } catch { /* offline: de huidige gegevens blijven staan */ }
}

async function start() {
  const index = await vers()
  staat.index = index
  const [stranden, getij] = await Promise.all([data('kaart.json'), data('getij.json')])
  Object.assign(staat, { stranden, getij })
  const eerste = data('sport/ww.json')
  setInterval(nieuweBerekening, 5 * 60 * 1000)
  document.addEventListener('visibilitychange', () => { if (!document.hidden) nieuweBerekening() })

  kaart = new maplibregl.Map({
    container: 'kaart', style: await stijl(), bounds: PORTUGAL, minZoom: 5, maxZoom: 16,
    maxBounds: [[-16, 33], [14, 55]], attributionControl: { compact: true },
  })
  kaart.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-left')
  kaart.addControl(new maplibregl.GeolocateControl({ trackUserLocation: false }), 'top-left')

  kaart.on('load', async () => {
    staat.cijfers = await eerste
    for (let w = 0; w <= 4; w++) for (let v = 0; v <= 4; v++) {
      if ((w === 0) !== (v === 0)) continue
      kaart.addImage(`b${w}${v}`, bolletjeWW(w, v, BOL), { pixelRatio: 2 })
      for (let rood = 0; rood <= 3; rood++) kaart.addImage(`b${w}${v}${rood}`, bolletjeWW(w, v, BOL, false, rood), { pixelRatio: 2 })
    }
    kaart.addSource('stranden', {
      type: 'geojson', data: features(), cluster: true, clusterRadius: 30, clusterMaxZoom: 9,
      clusterProperties: { w: ['max', ['get', 'w']], v: ['max', ['get', 'v']] },
    })
    // Links WIND, rechts WAVE.
    const ww = ['concat', 'b', ['to-string', ['get', 'w']], ['to-string', ['get', 'v']]]
    // Samengeklonterd: het aantal stranden in een wit bolletje met cyaan rand en cijfer.
    kaart.on('styleimagemissing', (e) => {
      const n = /^sg\|(\d+)$/.exec(e.id)
      if (n && !kaart.hasImage(e.id)) kaart.addImage(e.id, groepIcoon(Number(n[1]), '#0e8fa6'), { pixelRatio: 2 })
    })
    // Routes vanaf het verblijf, onder de bolletjes.
    kaart.addSource('routes', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } })
    // Waar routes over dezelfde weg lopen, ligt de sport met voorrang bovenop:
    // golfsurfen, dan windsurfen op golven, dan windsurfen, dan stille waters.
    kaart.addLayer({ id: 'routes-rand', type: 'line', source: 'routes', layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-color': '#ffffff', 'line-width': 7, 'line-opacity': 0.9 } })
    kaart.addLayer({ id: 'routes', type: 'line', source: 'routes',
      layout: { 'line-cap': 'round', 'line-join': 'round', 'line-sort-key': ['get', 'prio'] },
      paint: { 'line-color': ['get', 'kleur'], 'line-width': 4 } })
    kaart.addLayer({ id: 'groepen', type: 'symbol', source: 'stranden', filter: ['has', 'point_count'],
      layout: { 'icon-image': ['concat', 'sg|', ['to-string', ['get', 'point_count']]] as any, 'icon-allow-overlap': true } })
    kaart.addLayer({ id: 'stranden', type: 'symbol', source: 'stranden', filter: ['!', ['has', 'point_count']],
      layout: { 'icon-image': ['concat', ww, ['get', 'l']] as any, 'icon-allow-overlap': true,
        'symbol-sort-key': ['+', ['get', 'w'], ['get', 'v']] } })
    kaart.on('click', 'stranden', (e) => {
      const id = e.features?.[0]?.properties?.id
      if (id) openFiche(id)
    })
    kaart.on('click', 'groepen', async (e) => {
      const f = e.features![0]
      const src = kaart.getSource('stranden') as GeoJSONSource
      const z = await src.getClusterExpansionZoom(f.properties!.cluster_id)
      kaart.easeTo({ center: (f.geometry as any).coordinates, zoom: z })
    })
    for (const l of ['stranden', 'groepen']) {
      kaart.on('mouseenter', l, () => (kaart.getCanvas().style.cursor = 'pointer'))
      kaart.on('mouseleave', l, () => (kaart.getCanvas().style.cursor = ''))
    }
    await laadKlim(kaart)
    dagen()
    zoekveld()
    document.getElementById('verblijfknop')!.onclick = () => vraag()
    surfPaneel(() => (kaart.getSource('stranden') as GeoJSONSource).setData(features()))
    // Bronvermelding dichtgeklapt (het i-knopje), zodat ze de routes niet bedekt.
    document.querySelector('.maplibregl-ctrl-attrib')?.classList.remove('maplibregl-compact-show')
    const hash = decodeURIComponent(location.hash.slice(1))
    document.body.dataset.klaar = '1'
    ;(window as any).__kaart = kaart // voor de test
    if (hash && stranden.some((s: KaartStrand) => s.id === hash)) {
      // Rechtstreekse link naar een strand: geen vraag, wel het bewaarde verblijf.
      openFiche(hash)
      const oud = leesVerblijf()
      if (oud) kiesVerblijf(oud, false)
    } else {
      // Kom je via het tabblad terug van de planning (of met de terugknop), dan blijft je verblijf staan.
      // Herladen of de site opnieuw openen: een lege vraag.
      const oud = leesVerblijf()
      const nav = (performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming | undefined)?.type
      if (oud && (viaTab || nav === 'back_forward')) kiesVerblijf(oud)
      else vraag(true)
    }
  })
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') sluitFiche() })
  window.addEventListener('hashchange', () => {
    const id = decodeURIComponent(location.hash.slice(1))
    if (id.startsWith('klim:') && id !== staat.open) openKlim(id.slice(5))
    else if (id && id !== staat.open && staat.stranden.some((s) => s.id === id)) openFiche(id)
  })
}


export function vliegNaar(lon: number, lat: number, dichtbij = false) {
  if (dichtbij) kaart.easeTo({ center: [lon, lat], zoom: Math.max(kaart.getZoom(), 13) })
  else if (kaart.getZoom() < 10) kaart.easeTo({ center: [lon, lat], zoom: 11 })
}

start()
