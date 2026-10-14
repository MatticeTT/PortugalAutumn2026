import maplibregl from 'maplibre-gl'
import { FieldSet, type Kind, type Manifest } from './field'
import { ParticleLayer } from './particles'

const DATA = './data'
const FINE_ZOOM = 3 // vanaf dit zoomniveau het fijne raster (0,25 graad) voor het zichtbare gebied
const PLAY_MS = 900

const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T
const slider = $<HTMLInputElement>('schuif')
const label = $('tijd')
const playBtn = $('afspelen')
const windBtn = $('knop-wind')
const waveBtn = $('knop-golven')

const carto = (style: string) => ['a', 'b', 'c', 'd'].map((s) => `https://${s}.basemaps.cartocdn.com/${style}/{z}/{x}/{y}@2x.png`)

const map = new maplibregl.Map({
  container: 'kaart',
  style: {
    version: 8,
    sources: {
      basis: { type: 'raster', tiles: carto('dark_nolabels'), tileSize: 256, maxzoom: 18,
        attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> © <a href="https://carto.com/attributions">CARTO</a>' },
      namen: { type: 'raster', tiles: carto('dark_only_labels'), tileSize: 256, maxzoom: 18 },
    },
    layers: [
      { id: 'achtergrond', type: 'background', paint: { 'background-color': '#0e1013' } },
      { id: 'basis', type: 'raster', source: 'basis', paint: { 'raster-saturation': -1, 'raster-brightness-max': 0.85 } },
      { id: 'namen', type: 'raster', source: 'namen', paint: { 'raster-opacity': 0.7 } },
    ],
  },
  center: [-12, 41],
  zoom: 3.6,
  minZoom: 1,
  maxZoom: 10,
  dragRotate: false,
  pitchWithRotate: false,
  touchPitch: false,
  renderWorldCopies: true,
  attributionControl: { compact: true, customAttribution: 'Wind en golven: NOAA GFS / WaveWatch III' },
})
map.touchZoomRotate.disableRotation()
map.keyboard.disableRotation()

const layer = new ParticleLayer()
let manifest: Manifest
let idx = 0
let playing: number | null = null
const show: Record<Kind, boolean> = { wind: true, wave: true }

// Velden per soort en uur; de laatste paar bewaren zodat terugschuiven direct werkt.
const cache = new Map<string, FieldSet>()
function fieldSet(kind: Kind, i: number): FieldSet {
  const h = manifest.times[i].h
  const key = `${kind}:${h}`
  let fs = cache.get(key)
  if (!fs) {
    fs = new FieldSet(kind, h, manifest, DATA, () => map.triggerRepaint())
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
  for (const fs of [layer.wind, layer.wave]) fs?.useFine(fine, b.getWest(), b.getSouth(), b.getEast(), b.getNorth())
}

/** Tijdstip kiezen: het oude veld blijft zichtbaar tot het nieuwe binnen is. */
async function setTime(i: number) {
  idx = i
  slider.value = String(i)
  label.textContent = fmtTime(manifest.times[i].time)
  const jobs = (['wind', 'wave'] as Kind[]).filter((k) => show[k]).map(async (k) => {
    const fs = await fieldSet(k, i).loadCoarse()
    if (idx !== i) return
    if (k === 'wind') layer.wind = fs
    else layer.wave = fs
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
    for (const k of ['wind', 'wave'] as Kind[]) if (show[k]) fieldSet(k, after).loadCoarse().catch(() => {})
    busy = false
  }, PLAY_MS)
}

function setLayer(kind: Kind, on: boolean) {
  show[kind] = on
  const btn = kind === 'wind' ? windBtn : waveBtn
  btn.classList.toggle('aan', on)
  btn.setAttribute('aria-pressed', String(on))
  if (kind === 'wind') layer.showWind = on
  else layer.showWaves = on
  if (on) setTime(idx)
  map.triggerRepaint()
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
  $('bron').textContent = `GFS-run ${fmtDay.format(run)} ${fmtHour.format(run)} · wind 10 m, golven WW3`
  buildDayTicks()
  window.addEventListener('resize', buildDayTicks)
  await setTime(best)
}

slider.addEventListener('input', () => setTime(Number(slider.value)))
slider.addEventListener('pointerdown', () => togglePlay(false))
playBtn.addEventListener('click', () => togglePlay())
windBtn.addEventListener('click', () => setLayer('wind', !show.wind))
waveBtn.addEventListener('click', () => setLayer('wave', !show.wave))
map.on('moveend', updateFine)

// Niet op 'load' wachten: dat komt pas als alle tegels van de basiskaart binnen zijn.
const addLayer = () => { if (!map.getLayer(layer.id)) map.addLayer(layer, 'namen') }
if (map.isStyleLoaded()) addLayer()
else map.once('style.load', addLayer)
;(window as unknown as { kaart: unknown }).kaart = { map, layer }
start().catch((e) => {
  console.error(e)
  label.textContent = 'Laden mislukt'
})
