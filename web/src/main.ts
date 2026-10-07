import maplibregl, { type GeoJSONSource, type StyleSpecification } from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import './style.css'
import { bolletjeWW } from './kleuren'
import { openFiche, sluitFiche, toonUur } from './fiche'
import { zoekveld } from './zoek'
import type { Getij, Index, KaartStrand } from './types'

const TZ = 'Europe/Lisbon'
const fmtDag = new Intl.DateTimeFormat('nl-BE', { timeZone: TZ, weekday: 'short', day: 'numeric', month: 'short' })
const fmtUur = new Intl.DateTimeFormat('nl-BE', { timeZone: TZ, hour: '2-digit', minute: '2-digit' })
const fmtSleutel = new Intl.DateTimeFormat('en-CA', { timeZone: TZ, year: 'numeric', month: '2-digit', day: '2-digit' })
const fmtUurNr = new Intl.DateTimeFormat('en-GB', { timeZone: TZ, hour: '2-digit', hourCycle: 'h23' })

export const staat = {
  index: null as unknown as Index,
  stranden: [] as KaartStrand[],
  getij: null as unknown as Getij,
  cijfers: [] as string[], // per strand (volgorde van kaart.json): WIND, WAVE, "!" per uur
  i: 0, // index in index.tijd
  open: null as string | null,
}

export const utc = (s: string) => Date.parse(s + ':00Z')
export const lisDag = (ms: number) => fmtSleutel.format(ms)
export const lisUur = (ms: number) => Number(fmtUurNr.format(ms))
export const toonTijd = (ms: number) => fmtUur.format(ms)
export const toonDag = (ms: number) => fmtDag.format(ms)

const OFM = 'https://tiles.openfreemap.org/styles/liberty'

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

// Waar de kaart opent: Praia da Rocha (Portimão), op vraag van de eigenaar.
const START = { center: [-8.5326, 37.1148] as [number, number], zoom: 13 }

// Per strand (volgorde van kaart.json) per uur twee cijfers: WIND en WAVE (level 1–4).
function features() {
  const i = staat.i
  return {
    type: 'FeatureCollection' as const,
    features: staat.stranden.map((s, k) => {
      const rij = staat.cijfers[k] ?? ''
      const w = Number(rij[2 * i] ?? 0)
      const v = Number(rij[2 * i + 1] ?? 0)
      const l = ''
      return { type: 'Feature' as const, geometry: { type: 'Point' as const, coordinates: [s.x, s.y] },
        properties: { id: s.id, naam: s.n, w, v, l } }
    }),
  }
}

let kaart: maplibregl.Map
const perDag = new Map<string, number[]>()
const slider = () => document.getElementById('uur') as HTMLInputElement
const datumKeuze = () => document.getElementById('datum') as HTMLSelectElement

function ververs() {
  const src = kaart?.getSource('stranden') as GeoJSONSource | undefined
  src?.setData(features())
  const ms = utc(staat.index.tijd[staat.i])
  ;(document.getElementById('uurlabel') as HTMLOutputElement).value = toonTijd(ms)
  toonUur()
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
    container: 'kaart', style: await stijl(), ...START, minZoom: 5, maxZoom: 16,
    maxBounds: [[-12.5, 35.5], [-4.5, 43.5]], attributionControl: { compact: true },
  })
  kaart.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-left')
  kaart.addControl(new maplibregl.GeolocateControl({ trackUserLocation: false }), 'top-left')

  kaart.on('load', async () => {
    staat.cijfers = await eerste
    for (let w = 0; w <= 4; w++) for (let v = 0; v <= 4; v++) {
      if ((w === 0) !== (v === 0)) continue
      kaart.addImage(`b${w}${v}`, bolletjeWW(w, v, 44), { pixelRatio: 2 })
    }
    kaart.addSource('stranden', {
      type: 'geojson', data: features(), cluster: true, clusterRadius: 30, clusterMaxZoom: 9,
      clusterProperties: { w: ['max', ['get', 'w']], v: ['max', ['get', 'v']] },
    })
    // Links WIND, rechts WAVE. Samengeklonterd: het hoogste WIND- en WAVE-cijfer van de groep.
    const ww = ['concat', 'b', ['to-string', ['get', 'w']], ['to-string', ['get', 'v']]]
    kaart.addLayer({ id: 'groepen', type: 'symbol', source: 'stranden', filter: ['has', 'point_count'],
      layout: { 'icon-image': ww as any, 'icon-size': 1.1, 'icon-allow-overlap': true } })
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
    dagen()
    zoekveld()
    const hash = decodeURIComponent(location.hash.slice(1))
    if (hash && stranden.some((s: KaartStrand) => s.id === hash)) openFiche(hash)
    document.body.dataset.klaar = '1'
  })
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') sluitFiche() })
  window.addEventListener('hashchange', () => {
    const id = decodeURIComponent(location.hash.slice(1))
    if (id && id !== staat.open && staat.stranden.some((s) => s.id === id)) openFiche(id)
  })
}


export function vliegNaar(lon: number, lat: number, dichtbij = false) {
  if (dichtbij) kaart.easeTo({ center: [lon, lat], zoom: Math.max(kaart.getZoom(), 13) })
  else if (kaart.getZoom() < 10) kaart.easeTo({ center: [lon, lat], zoom: 11 })
}

start()
