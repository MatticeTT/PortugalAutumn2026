import maplibregl from 'maplibre-gl'
import { FieldSet, heeft, type Kind, type Manifest } from './field'
import { Fiche } from './fiche'
import { KaartSpots } from './kaartspots'
import { Labels } from './labels'
import { ParticleLayer } from './particles'
import { Planning } from './planning'
import { enablePointInfo } from './punt'
import { dagSleutel, SpotData, vakkenOpDag, type SpotKort } from './spots'
import { bewaarSurf, leesSurf } from './surfpaneel'
import { themaKnop } from './thema'
import { bewaarVerblijf, leesVerblijf, rijtijden, rijTekst, zoekInDeBuurt, type Verblijf } from './verblijf'
import { zoekveld } from './zoek'

const DATA = './data'
const FINE_ZOOM = 3 // vanaf dit zoomniveau het fijne raster (0,25 graad) voor het zichtbare gebied
const PLAY_MS = 900

const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T
const datum = $<HTMLSelectElement>('datum')
const slider = $<HTMLInputElement>('uur')
const uurLabel = $<HTMLOutputElement>('uurlabel')
const playBtn = $('afspelen')
const windBtn = $('knop-wind')
const swellBtn = $('knop-deining')
const altBtn = $('knop-afwisselen')

// ---- Kaart met de animatie van wind en golven (ongewijzigd) ----
const map = new maplibregl.Map({
  container: 'kaart',
  style: {
    version: 8,
    sources: {
      land: { type: 'geojson', data: './basis/land.geojson', tolerance: 0.3, attribution: 'Kaart: <a href="https://www.naturalearthdata.com">Natural Earth</a>' },
      meren: { type: 'geojson', data: './basis/meren.geojson', tolerance: 0.3 },
      grenzen: { type: 'geojson', data: './basis/grenzen.geojson', tolerance: 0.3 },
      // Ingezoomd: de wereldkaart zonder Portugal plus de fijne kust van Portugal (GSHHG, ongeveer 100 m).
      'land-buiten': { type: 'geojson', data: './basis/land-buiten.geojson', tolerance: 0.3 },
      'land-fijn': { type: 'geojson', data: './basis/land-fijn.geojson', tolerance: 0.1, attribution: 'Kust: GSHHG' },
      // Vanaf zoom 9: de kust van Portugal uit OpenStreetMap (tot op de meter, past bij stranden en wegen).
      'land-osm': { type: 'geojson', data: './basis/land-osm.geojson', tolerance: 0.15 },
      // Strandvlakken van Portugal uit OpenStreetMap (pipeline/stranden_osm.py).
      stranden: { type: 'geojson', data: './basis/stranden.geojson', tolerance: 0.2 },
      // Ingezoomd: wegen uit OpenStreetMap (vectortegels van OpenFreeMap, zoals de eerste versie).
      osm: { type: 'vector', url: 'https://tiles.openfreemap.org/planet',
        attribution: '<a href="https://openfreemap.org">OpenFreeMap</a> © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' },
    },
    layers: [
      { id: 'zee', type: 'background', paint: { 'background-color': '#1b2430' } },
      { id: 'land', type: 'fill', source: 'land', maxzoom: 7, paint: { 'fill-color': '#3b4048', 'fill-antialias': true } },
      { id: 'land-buiten', type: 'fill', source: 'land-buiten', minzoom: 7, paint: { 'fill-color': '#3b4048', 'fill-antialias': true } },
      { id: 'land-fijn', type: 'fill', source: 'land-fijn', minzoom: 7, maxzoom: 9, paint: { 'fill-color': '#3b4048', 'fill-antialias': true } },
      { id: 'land-osm', type: 'fill', source: 'land-osm', minzoom: 9, paint: { 'fill-color': '#3b4048', 'fill-antialias': true } },
      { id: 'meren', type: 'fill', source: 'meren', paint: { 'fill-color': '#1b2430' } },
      // Rivieren en meren (niet de zee: daar loopt de animatie onder het land door).
      { id: 'binnenwater', type: 'fill', source: 'osm', 'source-layer': 'water', minzoom: 9, filter: ['!=', ['get', 'class'], 'ocean'],
        paint: { 'fill-color': '#1b2430' } },
      // Stranden beige, wegen als donkere lijnen op het grijze land.
      { id: 'stranden', type: 'fill', source: 'stranden', minzoom: 8,
        paint: { 'fill-color': '#d9c49a', 'fill-opacity': ['interpolate', ['linear'], ['zoom'], 8, 0.7, 11, 0.95] } },
      { id: 'wegen', type: 'line', source: 'osm', 'source-layer': 'transportation', minzoom: 8,
        filter: ['match', ['get', 'class'], ['motorway', 'trunk', 'primary', 'secondary', 'tertiary', 'minor'], true, false],
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-color': '#22262c',
          'line-width': ['interpolate', ['linear'], ['zoom'],
            8, ['match', ['get', 'class'], ['motorway', 'trunk'], 1.4, ['primary'], 1, ['minor'], 0, 0.6],
            12, ['match', ['get', 'class'], ['motorway', 'trunk'], 3.5, ['primary'], 2.8, ['secondary'], 2.2, ['tertiary'], 1.8, 1.1]] } },
      { id: 'kust', type: 'line', source: 'land', maxzoom: 7, paint: { 'line-color': '#6c7682', 'line-width': ['interpolate', ['linear'], ['zoom'], 1, 0.5, 6, 1.1] } },
      { id: 'kust-buiten', type: 'line', source: 'land-buiten', minzoom: 7, paint: { 'line-color': '#6c7682', 'line-width': 1.1 } },
      { id: 'kust-fijn', type: 'line', source: 'land-fijn', minzoom: 7, maxzoom: 9, paint: { 'line-color': '#8a96a3', 'line-width': 1.2 } },
      { id: 'kust-osm', type: 'line', source: 'land-osm', minzoom: 9, paint: { 'line-color': '#8a96a3', 'line-width': 1.2 } },
      { id: 'grenzen', type: 'line', source: 'grenzen', paint: { 'line-color': '#5c636d', 'line-width': ['interpolate', ['linear'], ['zoom'], 1, 0.4, 6, 0.9], 'line-dasharray': [3, 2] } },
    ],
  },
  center: [-9.2, 39.3],
  zoom: 5.6,
  minZoom: 1,
  maxZoom: 12,
  dragRotate: false,
  pitchWithRotate: false,
  touchPitch: false,
  renderWorldCopies: true,
  attributionControl: { compact: true },
})
map.touchZoomRotate.disableRotation()
map.keyboard.disableRotation()

const layer = new ParticleLayer()
let manifest: Manifest
let idx = 0
let playing: number | null = null
const show: Record<Kind, boolean> = { wind: true, swell: true, windsea: false }
const KINDS: Kind[] = ['wind', 'swell']
const knop: Partial<Record<Kind, HTMLElement>> = { wind: windBtn, swell: swellBtn }

const cache = new Map<string, FieldSet>()
function fieldSet(kind: Kind, i: number): FieldSet {
  const t = manifest.times[i]
  const key = `${kind}:${t.h}`
  let fs = cache.get(key)
  if (!fs) {
    fs = new FieldSet(kind, t, manifest, DATA, () => map.triggerRepaint())
    cache.set(key, fs)
    while (cache.size > 24) cache.delete(cache.keys().next().value!)
  } else {
    cache.delete(key)
    cache.set(key, fs)
  }
  return fs
}

function updateFine() {
  const fine = map.getZoom() >= FINE_ZOOM
  const b = map.getBounds()
  for (const fs of [layer.wind, layer.swell.field]) fs?.useFine(fine, b.getWest(), b.getSouth(), b.getEast(), b.getNorth())
}

// ---- Spots, fiche, verblijf ----
const spots = new SpotData(`${DATA}/spots`)
let surf = leesSurf()
let verblijf: Verblijf | null = leesVerblijf()
const rij = new Map<number, number | null>()
let verblijfMarker: maplibregl.Marker | null = null
const tijdNu = () => new Date(manifest.times[idx].time)
const dagenMetScore = () => [...new Set(manifest.times.map((t) => dagSleutel(new Date(t.time))))]
  .filter((d) => d >= dagSleutel(new Date()))
  .filter((d) => !spots.index || spots.index.spots.some((s) => Object.values(s.tijdvakken).flat().some((v) => dagSleutel(new Date(v[0])) >= d)))

const fiche = new Fiche({
  data: spots,
  planken: () => surf.planken,
  rijtijd: (id) => rij.get(id),
  tijd: () => tijdNu(),
  dagen: dagenMetScore,
  naarDag: (d) => zetDag(d),
  gesloten: () => {
    kaartSpots.kies(-1)
    map.easeTo({ padding: { top: 0, bottom: 0, left: 0, right: 0 } })
  },
})
const kaartSpots = new KaartSpots(map, () => spots.index, (s) => openSpot(s))

function openSpot(s: SpotKort) {
  kaartSpots.kies(s.id)
  fiche.open(s.id)
  // De spot boven het blad houden: op een telefoon bedekt de fiche het onderste deel van de kaart.
  const smal = window.innerWidth <= 640
  map.easeTo({ center: [s.lon, s.lat], zoom: Math.max(map.getZoom(), 9),
    padding: smal ? { top: 0, bottom: map.getContainer().clientHeight * 0.72, left: 0, right: 0 } : { top: 0, bottom: 0, left: 0, right: 460 } })
}

// ---- Tijd: dag kiezen, uur binnen die dag ----
const uurFmt = new Intl.DateTimeFormat('nl-NL', { hour: '2-digit', minute: '2-digit' })
const dagFmt = new Intl.DateTimeFormat('nl-NL', { weekday: 'short', day: 'numeric', month: 'short' })
const indicesVanDag = (dag: string) => manifest.times.map((t, i) => [t, i] as const).filter(([t]) => dagSleutel(new Date(t.time)) === dag).map(([, i]) => i)

function vulDagen() {
  const vandaag = dagSleutel(new Date())
  datum.innerHTML = [...new Set(manifest.times.map((t) => dagSleutel(new Date(t.time))))].map((d) => {
    const naam = d === vandaag ? 'Vandaag' : dagFmt.format(new Date(d + 'T12:00'))
    return `<option value="${d}">${naam}</option>`
  }).join('')
}

/** Naar een dag, op ongeveer hetzelfde uur (standaard 13u). */
function zetDag(dag: string, uur = 13) {
  const lijst = indicesVanDag(dag)
  if (!lijst.length) return
  let best = lijst[0]
  for (const i of lijst) if (Math.abs(new Date(manifest.times[i].time).getHours() - uur) < Math.abs(new Date(manifest.times[best].time).getHours() - uur)) best = i
  setTime(best)
}

async function setTime(i: number) {
  const vorigeDag = manifest.times[idx] ? dagSleutel(new Date(manifest.times[idx].time)) : ''
  idx = i
  const t = manifest.times[i]
  const d = new Date(t.time)
  const dag = dagSleutel(d)
  datum.value = dag
  const lijst = indicesVanDag(dag)
  slider.max = String(lijst.length - 1)
  slider.value = String(lijst.indexOf(i))
  uurLabel.textContent = uurFmt.format(d)
  if (dag !== vorigeDag) kaartSpots.zet(dag, surf.planken)
  fiche.ververs()
  const jobs = KINDS.filter((k) => show[k]).map(async (k) => {
    if (k !== 'wind' && !heeft(t, k)) {
      layer[k].field = null
      return
    }
    const fs = await fieldSet(k, i).loadCoarse()
    if (idx !== i) return
    if (k === 'wind') layer.wind = fs
    else layer[k].field = fs
  })
  await Promise.allSettled(jobs)
  if (idx === i) {
    updateFine()
    map.triggerRepaint()
  }
}

const togglePlaying = () => playing !== null
function togglePlay(on = playing === null) {
  if (playing !== null) clearInterval(playing)
  playing = null
  playBtn.classList.toggle('speelt', on)
  playBtn.setAttribute('aria-label', on ? 'Pauzeren' : 'Afspelen')
  if (!on) return
  let busy = false
  playing = window.setInterval(async () => {
    if (busy) return
    busy = true
    const next = (idx + 1) % manifest.times.length
    await setTime(next)
    const after = (next + 1) % manifest.times.length
    for (const k of KINDS) if (show[k] && heeft(manifest.times[after], k)) fieldSet(k, after).loadCoarse().catch(() => {})
    busy = false
  }, PLAY_MS)
}

function setLayer(kind: Kind, on: boolean) {
  show[kind] = on
  knop[kind]?.classList.toggle('aan', on)
  knop[kind]?.setAttribute('aria-pressed', String(on))
  if (kind === 'wind') layer.showWind = on
  else layer[kind].show = on
  if (on) setTime(idx)
  altBtn.hidden = !(show.wind && show.swell)
  map.triggerRepaint()
}

function setAlternate(on: boolean) {
  layer.alternate = on
  layer.restartAlternation()
  altBtn.classList.toggle('aan', on)
  altBtn.setAttribute('aria-pressed', String(on))
  try { localStorage.setItem('afwisselen', on ? '1' : '0') } catch { /* privévenster */ }
}

// ---- Tabbladen: Kaart en Planning ----
let tab = 'kaart'
function kiesTab(naam: string) {
  tab = naam
  document.querySelectorAll<HTMLButtonElement>('.tabs button').forEach((b) => {
    if (b.dataset.tab === naam) b.setAttribute('aria-current', 'page')
    else b.removeAttribute('aria-current')
  })
  $('planning').hidden = naam !== 'planning'
  if (naam === 'planning') tekenPlanning()
}

const planning = new Planning($('planning'))
let rijStatus: 'bezig' | 'klaar' | 'fout' = 'klaar'
function tekenPlanning() {
  if (tab !== 'planning') return
  planning.teken({
    data: spots.index, planken: surf.planken, verblijf, rijtijd: (id) => rij.get(id), rijStatus, dagen: dagenMetScore(),
    zetVerblijf: (v) => kiesVerblijf(v),
    gewicht: surf.gewicht,
    zetGewicht: (kg) => { surf = { ...surf, gewicht: kg }; bewaarSurf(surf) },
    zetPlanken: (p) => {
      surf = { ...surf, planken: p }
      bewaarSurf(surf)
      kaartSpots.zet(dagSleutel(tijdNu()), surf.planken)
      fiche.ververs()
      tekenPlanning()
    },
    open: (s, dag) => {
      kiesTab('kaart')
      const v = vakkenOpDag(s, dag, surf.planken)[0]
      const midden = v ? new Date((Date.parse(v[1][0]) + Date.parse(v[1][1])) / 2) : new Date(dag + 'T13:00')
      zetDag(dag, midden.getHours())
      openSpot(s)
    },
  })
}

// ---- Verblijf en rijtijden (OSRM, zoals in de eerste versie) ----
function toonVerblijf() {
  const k = $('verblijfknop')
  k.innerHTML = verblijf ? `<span class="huisje" aria-hidden="true"></span>${verblijf.naam.split(',')[0]} · ${rijTekst(verblijf.max)}` : 'Waar verblijf je?'
  verblijfMarker?.remove()
  verblijfMarker = null
  if (verblijf) {
    const el = document.createElement('div')
    el.className = 'verblijfpunt'
    el.title = verblijf.naam
    verblijfMarker = new maplibregl.Marker({ element: el }).setLngLat([verblijf.lon, verblijf.lat]).addTo(map)
  }
}

let rijVraag = 0
async function berekenRijtijden() {
  rij.clear()
  if (!verblijf || !spots.index) return
  const nr = ++rijVraag
  rijStatus = 'bezig'
  tekenPlanning()
  try {
    const m = await rijtijden(verblijf, spots.index.spots.map((s) => ({ id: String(s.id), lat: s.lat, lon: s.lon })))
    if (nr !== rijVraag) return
    for (const [k, v] of m) rij.set(Number(k), v)
    rijStatus = 'klaar'
  } catch {
    if (nr !== rijVraag) return
    rijStatus = 'fout' // routeplanner niet bereikbaar: dan zonder rijtijden
  }
  fiche.ververs()
  tekenPlanning()
}

/** Nieuw verblijf of andere rijtijd (Planning, stap 1 en 2). */
async function kiesVerblijf(v: Verblijf) {
  const andereplek = !verblijf || verblijf.lat !== v.lat || verblijf.lon !== v.lon
  const verder = !verblijf || v.max > verblijf.max
  verblijf = v
  bewaarVerblijf(v)
  toonVerblijf()
  // Rijtijden worden alleen opgevraagd voor stranden die binnen de rijtijd kunnen liggen: bij een langere rijtijd opnieuw.
  if (andereplek || verder) await berekenRijtijden()
  else tekenPlanning()
}

// ---- Starten ----
async function start() {
  const res = await fetch(`${DATA}/manifest.json`, { cache: 'no-cache' })
  if (!res.ok) {
    uurLabel.textContent = 'geen voorspelling'
    return
  }
  manifest = await res.json()
  vulDagen()
  const nu = Date.now()
  let best = 0
  manifest.times.forEach((t, i) => {
    if (Math.abs(Date.parse(t.time) - nu) < Math.abs(Date.parse(manifest.times[best].time) - nu)) best = i
  })
  await spots.load().catch(() => null)
  await setTime(best)
  kaartSpots.zet(dagSleutel(tijdNu()), surf.planken)
  toonVerblijf()
  berekenRijtijden()
}

datum.addEventListener('change', () => zetDag(datum.value, tijdNu().getHours()))
// Schuifbalk voor het uur. Op een telefoon: overal op de balk tikken of slepen werkt (ook op iPhone), en tijdens
// het slepen wordt alleen het nieuwste uur getekend (geen achterstand als de kaart even werk heeft).
let gevraagd: number | null = null
let tekent = false
async function naarUur(k: number) {
  const lijst = indicesVanDag(datum.value)
  const i = lijst[Math.max(0, Math.min(lijst.length - 1, k))]
  if (i === undefined) return
  uurLabel.textContent = uurFmt.format(new Date(manifest.times[i].time))
  gevraagd = i
  if (tekent) return
  tekent = true
  while (gevraagd !== null) {
    const j = gevraagd
    gevraagd = null
    if (j !== idx) await setTime(j)
  }
  tekent = false
}
slider.addEventListener('input', () => naarUur(Number(slider.value)))
const uitPositie = (e: PointerEvent) => {
  const r = slider.getBoundingClientRect()
  const max = Number(slider.max)
  const k = Math.round(Math.max(0, Math.min(1, (e.clientX - r.left - 14) / Math.max(1, r.width - 28))) * max)
  if (String(k) !== slider.value) { slider.value = String(k); naarUur(k) }
}
slider.addEventListener('pointerdown', (e) => {
  if (togglePlaying()) togglePlay(false)
  slider.setPointerCapture(e.pointerId)
  uitPositie(e)
  e.preventDefault()
})
slider.addEventListener('pointermove', (e) => { if (slider.hasPointerCapture(e.pointerId)) uitPositie(e) })
slider.addEventListener('pointerdown', () => togglePlay(false))
playBtn.addEventListener('click', () => togglePlay())
windBtn.addEventListener('click', () => setLayer('wind', !show.wind))
swellBtn.addEventListener('click', () => setLayer('swell', !show.swell))
altBtn.addEventListener('click', () => setAlternate(!layer.alternate))
let savedAlt = true
try { savedAlt = localStorage.getItem('afwisselen') !== '0' } catch { /* privévenster */ }
setAlternate(savedAlt)
document.querySelectorAll<HTMLButtonElement>('.tabs button').forEach((b) => b.addEventListener('click', () => kiesTab(b.dataset.tab!)))
$('verblijfknop').addEventListener('click', () => { kiesTab('planning'); planning.focus() })
themaKnop()
// Gezochte plaats: een speld op de kaart, ingezoomd zodat de stranden in de buurt met hun cijfer zichtbaar zijn.
let plekMarker: maplibregl.Marker | null = null
zoekveld(() => spots.index, (s) => {
  kiesTab('kaart')
  openSpot(s)
}, (g) => {
  kiesTab('kaart')
  fiche.sluit()
  plekMarker?.remove()
  const el = document.createElement('div')
  el.className = 'plekspeld'
  el.innerHTML = '<i></i>'
  el.title = g.titel
  plekMarker = new maplibregl.Marker({ element: el, anchor: 'bottom' }).setLngLat([g.lon, g.lat]).addTo(map)
  map.flyTo({ center: [g.lon, g.lat], zoom: Math.max(map.getZoom(), 10.5), padding: { top: 0, bottom: 0, left: 0, right: 0 } })
})
// Plaatsen in de buurt van wat je bekijkt eerst (zoals Google Maps).
map.on('moveend', () => { const c = map.getCenter(); zoekInDeBuurt(c.lng, c.lat) })
map.on('moveend', updateFine)
new Labels(map).load('./basis/plaatsen.geojson').catch(() => {})
enablePointInfo(map, {
  wind: () => fieldSet('wind', idx),
  swell: () => (heeft(manifest.times[idx], 'swell') ? fieldSet('swell', idx) : null),
  windsea: () => null,
  time: () => manifest.times[idx].time,
  run: () => manifest.run,
})

const addLayer = () => {
  if (map.getLayer(layer.id)) return
  map.addLayer(layer, 'land')
  map.addLayer(layer.windLayer())
}
if (map.isStyleLoaded()) addLayer()
else map.once('style.load', addLayer)
;(window as unknown as { kaart: unknown }).kaart = { map, layer }
start().catch((e) => {
  console.error(e)
  uurLabel.textContent = 'laden mislukt'
})
