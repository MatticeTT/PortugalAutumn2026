import maplibregl from 'maplibre-gl'
import { FieldSet, heeft, type Kind, type Manifest } from './field'
import { Labels } from './labels'
import { enablePointInfo } from './punt'
import { ParticleLayer } from './particles'
import { PLANKEN, Spots } from './spots'

const DATA = './data'
const FINE_ZOOM = 3 // vanaf dit zoomniveau het fijne raster (0,25 graad) voor het zichtbare gebied
const PLAY_MS = 900

const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T
const slider = $<HTMLInputElement>('schuif')
const label = $('tijd')
const playBtn = $('afspelen')
const windBtn = $('knop-wind')
const swellBtn = $('knop-deining')
const altBtn = $('knop-afwisselen')

// Basiskaart uit Natural Earth (publiek domein), zelf gehost: rustig grijs land, donkere zee, kustlijn en grenzen.
const map = new maplibregl.Map({
  container: 'kaart',
  style: {
    version: 8,
    sources: {
      land: { type: 'geojson', data: './basis/land.geojson', tolerance: 0.3, attribution: 'Kaart: <a href="https://www.naturalearthdata.com">Natural Earth</a>' },
      meren: { type: 'geojson', data: './basis/meren.geojson', tolerance: 0.3 },
      grenzen: { type: 'geojson', data: './basis/grenzen.geojson', tolerance: 0.3 },
    },
    layers: [
      { id: 'zee', type: 'background', paint: { 'background-color': '#1b2430' } },
      { id: 'land', type: 'fill', source: 'land', paint: { 'fill-color': '#3b4048', 'fill-antialias': true } },
      { id: 'meren', type: 'fill', source: 'meren', paint: { 'fill-color': '#1b2430' } },
      { id: 'kust', type: 'line', source: 'land', paint: { 'line-color': '#6c7682', 'line-width': ['interpolate', ['linear'], ['zoom'], 1, 0.5, 6, 1.1] } },
      { id: 'grenzen', type: 'line', source: 'grenzen', paint: { 'line-color': '#5c636d', 'line-width': ['interpolate', ['linear'], ['zoom'], 1, 0.4, 6, 0.9], 'line-dasharray': [3, 2] } },
    ],
  },
  center: [-10, 44],
  zoom: 3.8,
  minZoom: 1,
  maxZoom: 10,
  dragRotate: false,
  pitchWithRotate: false,
  touchPitch: false,
  renderWorldCopies: true,
  attributionControl: { compact: true, customAttribution: 'Wind: <a href="https://www.ecmwf.int/en/forecasts/datasets/open-data">ECMWF</a> (CC BY 4.0) · Golven: Generated using E.U. <a href="https://marine.copernicus.eu">Copernicus Marine Service</a> Information' },
})
map.touchZoomRotate.disableRotation()
map.keyboard.disableRotation()

const layer = new ParticleLayer()
const spots = new Spots(map, `${DATA}/spots`)

// Plankfilter: welke planken meetellen voor de spots op de kaart (onthouden in deze browser).
function bouwPlankfilter() {
  const box = $('planken')
  let gekozen = new Set(Object.keys(PLANKEN))
  try {
    const s = JSON.parse(localStorage.getItem('planken') ?? 'null')
    if (Array.isArray(s) && s.length) gekozen = new Set(s.filter((x: string) => x in PLANKEN))
  } catch { /* privévenster */ }
  for (const [k, naam] of Object.entries(PLANKEN)) {
    const b = document.createElement('button')
    b.className = 'laag' + (gekozen.has(k) ? ' aan' : '')
    b.textContent = naam
    b.setAttribute('aria-pressed', String(gekozen.has(k)))
    b.addEventListener('click', () => {
      if (gekozen.has(k)) gekozen.delete(k)
      else gekozen.add(k)
      b.classList.toggle('aan', gekozen.has(k))
      b.setAttribute('aria-pressed', String(gekozen.has(k)))
      try { localStorage.setItem('planken', JSON.stringify([...gekozen])) } catch { /* privévenster */ }
      spots.setPlanken(new Set(gekozen))
    })
    box.append(b)
  }
  spots.setPlanken(new Set(gekozen))
}
let manifest: Manifest
let idx = 0
let playing: number | null = null
const show: Record<Kind, boolean> = { wind: true, swell: true, windsea: false }
const KINDS: Kind[] = ['wind', 'swell', 'windsea']
// Op de kaart: wind en deining. Windzee staat niet op de kaart, alleen in de info van een punt.
const knop: Partial<Record<Kind, HTMLElement>> = { wind: windBtn, swell: swellBtn }

// Velden per soort en uur; de laatste paar bewaren zodat terugschuiven direct werkt.
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
    cache.set(key, fs) // als laatst gebruikt markeren
  }
  return fs
}

function updateFine() {
  const fine = map.getZoom() >= FINE_ZOOM
  const b = map.getBounds()
  for (const fs of [layer.wind, layer.swell.field, layer.windsea.field]) fs?.useFine(fine, b.getWest(), b.getSouth(), b.getEast(), b.getNorth())
}

/** Tijdstip kiezen: het oude veld blijft zichtbaar tot het nieuwe binnen is. */
async function setTime(i: number) {
  idx = i
  spots.setTime(manifest.times[i].time)
  slider.value = String(i)
  label.textContent = fmtTime(manifest.times[i].time)
  const t = manifest.times[i]
  const jobs = KINDS.filter((k) => show[k]).map(async (k) => {
    if (k !== 'wind' && !heeft(t, k)) {
      layer[k].field = null // na de horizon van het golfmodel: geen golven
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

const fmtDay = new Intl.DateTimeFormat('nl-NL', { weekday: 'short', day: 'numeric', month: 'short' })
const fmtHour = new Intl.DateTimeFormat('nl-NL', { hour: '2-digit', minute: '2-digit' })
function fmtTime(iso: string) {
  const d = new Date(iso)
  return `${fmtDay.format(d)} · ${fmtHour.format(d)}`
}

function buildDayTicks() {
  const box = $('dagen')
  box.textContent = ''
  const n = manifest.times.length - 1
  let prev = ''
  manifest.times.forEach((t, i) => {
    const d = new Date(t.time)
    const day = d.toDateString()
    if (day === prev) return
    prev = day
    // Alleen een streepje bij middernacht (lokale tijd) of het eerste tijdstip.
    if (i > 0 && d.getHours() >= 3) return
    const s = document.createElement('span')
    s.style.left = `${(i / n) * 100}%`
    s.textContent = new Intl.DateTimeFormat('nl-NL', { weekday: 'short', day: 'numeric' }).format(d)
    box.append(s)
  })
  // Labels die elkaar raken (bv. eerste dag kort voor middernacht) weglaten.
  let lastRight = -Infinity
  for (const s of Array.from(box.children) as HTMLElement[]) {
    const r = s.getBoundingClientRect()
    if (r.left < lastRight + 4) s.remove()
    else lastRight = r.right
  }
}

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
    // Alvast het volgende tijdstip ophalen.
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

async function start() {
  const res = await fetch(`${DATA}/manifest.json`, { cache: 'no-cache' })
  if (!res.ok) {
    label.textContent = 'Geen voorspelling gevonden'
    return
  }
  manifest = await res.json()
  slider.max = String(manifest.times.length - 1)
  // Het tijdstip dat het dichtst bij nu ligt.
  const now = Date.now()
  let best = 0
  manifest.times.forEach((t, i) => {
    if (Math.abs(Date.parse(t.time) - now) < Math.abs(Date.parse(manifest.times[best].time) - now)) best = i
  })
  const run = new Date(manifest.run)
  const golfTot = [...manifest.times].reverse().find((t) => t.waves)
  $('bron').textContent = `Wind: ECMWF-run ${run.getUTCDate()}/${run.getUTCMonth() + 1} ${String(run.getUTCHours()).padStart(2, '0')} UTC, tot ${fmtDay.format(new Date(manifest.times[manifest.times.length - 1].time))} · golven: Copernicus${golfTot ? `, tot ${fmtDay.format(new Date(golfTot.time))}` : ''}`
  buildDayTicks()
  window.addEventListener('resize', buildDayTicks)
  bouwPlankfilter()
  spots.load().catch(() => {})
  await setTime(best)
}

new Labels(map).load('./basis/plaatsen.geojson').catch(() => {})

slider.addEventListener('input', () => setTime(Number(slider.value)))
slider.addEventListener('pointerdown', () => togglePlay(false))
playBtn.addEventListener('click', () => togglePlay())
windBtn.addEventListener('click', () => setLayer('wind', !show.wind))
swellBtn.addEventListener('click', () => setLayer('swell', !show.swell))
altBtn.addEventListener('click', () => setAlternate(!layer.alternate))
let savedAlt = true
try { savedAlt = localStorage.getItem('afwisselen') !== '0' } catch { /* privévenster */ }
setAlternate(savedAlt)
map.on('moveend', updateFine)
enablePointInfo(map, {
  wind: () => fieldSet('wind', idx),
  swell: () => (heeft(manifest.times[idx], 'swell') ? fieldSet('swell', idx) : null),
  windsea: () => (heeft(manifest.times[idx], 'windsea') ? fieldSet('windsea', idx) : null),
  time: () => manifest.times[idx].time,
  run: () => manifest.run,
})

// Niet op 'load' wachten: dat komt pas als alle tegels van de basiskaart binnen zijn.
// Golven onder het land (de kustlijn snijdt ze af), wind bovenop alles.
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
  label.textContent = 'Laden mislukt'
})
