import maplibregl, { type GeoJSONSource, type StyleSpecification } from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import './style.css'
import { bolletje, bolletjeUrl } from './kleuren'
import { openFiche, sluitFiche, toonUur } from './fiche'
import type { Getij, Index, KaartStrand, Mode } from './types'

const TZ = 'Europe/Lisbon'
const fmtDag = new Intl.DateTimeFormat('nl-BE', { timeZone: TZ, weekday: 'short', day: 'numeric', month: 'short' })
const fmtUur = new Intl.DateTimeFormat('nl-BE', { timeZone: TZ, hour: '2-digit', minute: '2-digit' })
const fmtSleutel = new Intl.DateTimeFormat('en-CA', { timeZone: TZ, year: 'numeric', month: '2-digit', day: '2-digit' })
const fmtUurNr = new Intl.DateTimeFormat('en-GB', { timeZone: TZ, hour: '2-digit', hourCycle: 'h23' })

export const staat = {
  index: null as unknown as Index,
  stranden: [] as KaartStrand[],
  getij: null as unknown as Getij,
  stand: 'wg' as Mode,
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

function features() {
  const i = staat.i
  return {
    type: 'FeatureCollection' as const,
    features: staat.stranden.map((s) => {
      const reeks = s[staat.stand] ?? ''
      const w = Number(reeks[2 * i] ?? 0)
      const v = Number(reeks[2 * i + 1] ?? 0)
      return { type: 'Feature' as const, geometry: { type: 'Point' as const, coordinates: [s.x, s.y] },
        properties: { id: s.id, naam: s.n, w, v, icoon: `b${w}${v}` } }
    }),
  }
}

let kaart: maplibregl.Map

function ververs() {
  const src = kaart?.getSource('stranden') as GeoJSONSource | undefined
  src?.setData(features())
  const ms = utc(staat.index.tijd[staat.i])
  ;(document.getElementById('uurlabel') as HTMLOutputElement).value = `${toonDag(ms)} ${toonTijd(ms)}`
  toonUur()
  try { localStorage.setItem('stand', staat.stand) } catch { /* privévenster */ }
}

function dagen() {
  const nav = document.getElementById('dagen')!
  const perDag = new Map<string, number[]>()
  staat.index.tijd.forEach((t, i) => {
    const k = lisDag(utc(t))
    if (!perDag.has(k)) perDag.set(k, [])
    perDag.get(k)!.push(i)
  })
  const slider = document.getElementById('uur') as HTMLInputElement
  const knoppen: HTMLButtonElement[] = []
  const zetDag = (k: string) => {
    knoppen.forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.dag === k)))
    const idx = perDag.get(k)!
    const huidig = lisUur(utc(staat.index.tijd[staat.i]))
    const best = idx.reduce((a, b) => Math.abs(lisUur(utc(staat.index.tijd[b])) - huidig) < Math.abs(lisUur(utc(staat.index.tijd[a])) - huidig) ? b : a)
    staat.i = best
    slider.min = String(lisUur(utc(staat.index.tijd[idx[0]])))
    slider.max = String(lisUur(utc(staat.index.tijd[idx[idx.length - 1]])))
    slider.value = String(lisUur(utc(staat.index.tijd[best])))
    ververs()
  }
  for (const [k, idx] of perDag) {
    const b = document.createElement('button')
    b.dataset.dag = k
    b.textContent = toonDag(utc(staat.index.tijd[idx[0]]))
    b.onclick = () => zetDag(k)
    nav.appendChild(b)
    knoppen.push(b)
  }
  slider.oninput = () => {
    const k = lisDag(utc(staat.index.tijd[staat.i]))
    const idx = perDag.get(k)!
    const want = Number(slider.value)
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
  const k = lisDag(utc(staat.index.tijd[i]))
  document.querySelectorAll<HTMLButtonElement>('#dagen button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.dag === k)))
  ;(document.getElementById('uur') as HTMLInputElement).value = String(lisUur(utc(staat.index.tijd[i])))
  ververs()
}

async function start() {
  const [index, stranden, getij] = await Promise.all([
    fetch('data/index.json').then((r) => r.json()),
    fetch('data/kaart.json').then((r) => r.json()),
    fetch('data/getij.json').then((r) => r.json()),
  ])
  Object.assign(staat, { index, stranden, getij })
  staat.stand = (index.standaard as Mode) || 'fijn'
  try { staat.stand = (localStorage.getItem('stand') as Mode) || staat.stand } catch { /* geen opslag */ }

  const sel = document.getElementById('stand') as HTMLSelectElement
  for (const [m, s] of Object.entries(index.standen) as [Mode, { naam: string; bron: string }][]) {
    const o = document.createElement('option')
    o.value = m; o.textContent = s.naam; o.title = s.bron
    sel.appendChild(o)
  }
  sel.value = staat.stand
  sel.onchange = () => { staat.stand = sel.value as Mode; ververs() }

  const legBol = document.getElementById('leg-bol')!
  for (const [w, v] of [[1, 1], [3, 2], [2, 3], [4, 4], [5, 3], [3, 5]]) {
    const img = document.createElement('img')
    img.src = bolletjeUrl(w, v); img.alt = `WIND ${w}, WAVE ${v}`
    legBol.appendChild(img)
  }
  const dlg = document.getElementById('legende') as HTMLDialogElement
  document.getElementById('legende-knop')!.onclick = () => dlg.showModal()

  kaart = new maplibregl.Map({
    container: 'kaart', style: await stijl(), center: [-8.6, 39.4], zoom: 5.8, minZoom: 5, maxZoom: 16,
    maxBounds: [[-12.5, 35.5], [-4.5, 43.5]], attributionControl: { compact: true },
  })
  kaart.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-left')
  kaart.addControl(new maplibregl.GeolocateControl({ trackUserLocation: false }), 'top-left')

  kaart.on('load', () => {
    for (let w = 0; w <= 5; w++) for (let v = 0; v <= 5; v++) {
      if ((w === 0) !== (v === 0)) continue
      kaart.addImage(`b${w}${v}`, bolletje(w, v, 44), { pixelRatio: 2 })
    }
    kaart.addSource('stranden', {
      type: 'geojson', data: features(), cluster: true, clusterRadius: 34, clusterMaxZoom: 9,
      clusterProperties: { w: ['max', ['get', 'w']], v: ['max', ['get', 'v']] },
    })
    // Samengeklonterd: het bolletje toont het hoogste WIND- en WAVE-cijfer van de groep.
    kaart.addLayer({
      id: 'groepen', type: 'symbol', source: 'stranden', filter: ['has', 'point_count'],
      layout: { 'icon-image': ['concat', 'b', ['to-string', ['get', 'w']], ['to-string', ['get', 'v']]],
        'icon-allow-overlap': true, 'icon-size': 1.1 },
    })
    kaart.addLayer({
      id: 'stranden', type: 'symbol', source: 'stranden', filter: ['!', ['has', 'point_count']],
      layout: { 'icon-image': ['get', 'icoon'], 'icon-allow-overlap': true, 'icon-size': 1 },
    })
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

export function vliegNaar(lon: number, lat: number) {
  if (kaart.getZoom() < 10) kaart.easeTo({ center: [lon, lat], zoom: 11 })
}

start()
