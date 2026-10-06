import maplibregl, { type GeoJSONSource, type StyleSpecification } from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import './style.css'
import { bolletje, KLEUR, RANG, tekstKleur } from './kleuren'
import { openFiche, sluitFiche, toonUur } from './fiche'
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
  sport: 'short',
  cijfers: [] as string[], // per strand (volgorde van kaart.json) één teken per uur
  i: 0, // index in index.tijd
  open: null as string | null,
}

export const utc = (s: string) => Date.parse(s + ':00Z')
export const lisDag = (ms: number) => fmtSleutel.format(ms)
export const lisUur = (ms: number) => Number(fmtUurNr.format(ms))
export const toonTijd = (ms: number) => fmtUur.format(ms)
export const toonDag = (ms: number) => fmtDag.format(ms)
export const sportNaam = (id: string) => staat.index.sporten.find((s) => s.id === id)?.naam ?? id

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

const sportCache = new Map<string, Promise<string[]>>()
function laadSport(id: string) {
  if (!sportCache.has(id)) sportCache.set(id, fetch(`data/sport/${id}.json`).then((r) => r.json()))
  return sportCache.get(id)!
}

function features() {
  const i = staat.i
  return {
    type: 'FeatureCollection' as const,
    features: staat.stranden.map((s, k) => {
      const n = Number(staat.cijfers[k]?.[i] ?? 0)
      return { type: 'Feature' as const, geometry: { type: 'Point' as const, coordinates: [s.x, s.y] },
        properties: { id: s.id, naam: s.n, n, rang: RANG[n] } }
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

export async function kiesSport(id: string) {
  staat.sport = id
  ;(document.getElementById('sport') as HTMLSelectElement).value = id
  try { localStorage.setItem('sport', id) } catch { /* privévenster */ }
  const rows = await laadSport(id)
  if (staat.sport !== id) return
  staat.cijfers = rows
  ververs()
}

function sportKeuze() {
  const sel = document.getElementById('sport') as HTMLSelectElement
  const I = staat.index
  for (const [g, naam] of Object.entries(I.groepen)) {
    const og = document.createElement('optgroup')
    og.label = naam
    for (const s of I.sporten.filter((s) => s.groep === g)) {
      const o = document.createElement('option')
      o.value = s.id; o.textContent = s.naam
      og.appendChild(o)
    }
    sel.appendChild(og)
  }
  let start = I.sporten[0].id
  try { start = localStorage.getItem('sport') || start } catch { /* geen opslag */ }
  if (!I.sporten.some((s) => s.id === start)) start = I.sporten[0].id
  staat.sport = start
  sel.value = start
  sel.onchange = () => kiesSport(sel.value)
}

function legende() {
  const t = document.getElementById('schaal')!
  t.innerHTML = staat.index.schaal.map((naam, k) =>
    `<tr><th style="background:${KLEUR[k]};color:${tekstKleur(k + 1)}">${k + 1}</th><td>${naam}</td></tr>`).join('')
  const dlg = document.getElementById('legende') as HTMLDialogElement
  document.getElementById('legende-knop')!.onclick = () => dlg.showModal()
}

async function start() {
  const [index, stranden, getij] = await Promise.all([
    fetch('data/index.json').then((r) => r.json()),
    fetch('data/kaart.json').then((r) => r.json()),
    fetch('data/getij.json').then((r) => r.json()),
  ])
  Object.assign(staat, { index, stranden, getij })
  sportKeuze()
  legende()
  const eerste = laadSport(staat.sport)

  kaart = new maplibregl.Map({
    container: 'kaart', style: await stijl(), center: [-8.6, 39.4], zoom: 5.8, minZoom: 5, maxZoom: 16,
    maxBounds: [[-12.5, 35.5], [-4.5, 43.5]], attributionControl: { compact: true },
  })
  kaart.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-left')
  kaart.addControl(new maplibregl.GeolocateControl({ trackUserLocation: false }), 'top-left')

  kaart.on('load', async () => {
    staat.cijfers = await eerste
    for (let n = 0; n <= 5; n++) {
      kaart.addImage(`s${n}`, bolletje(n, 30), { pixelRatio: 2 })
      kaart.addImage(`g${n}`, bolletje(n, 36, true), { pixelRatio: 2 })
    }
    kaart.addSource('stranden', {
      type: 'geojson', data: features(), cluster: true, clusterRadius: 30, clusterMaxZoom: 9,
      clusterProperties: { rang: ['max', ['get', 'rang']] },
    })
    // Samengeklonterd: het interessantste cijfer van de groep (3, dan 4, 2, 5, 1).
    kaart.addLayer({
      id: 'groepen', type: 'symbol', source: 'stranden', filter: ['has', 'point_count'],
      layout: { 'icon-image': ['concat', 'g', ['to-string', ['match', ['get', 'rang'], 5, 3, 4, 4, 3, 2, 2, 5, 1, 1, 0]]],
        'icon-allow-overlap': true },
    })
    kaart.addLayer({
      id: 'stranden', type: 'symbol', source: 'stranden', filter: ['!', ['has', 'point_count']],
      layout: { 'icon-image': ['concat', 's', ['to-string', ['get', 'n']]], 'icon-allow-overlap': true,
        'symbol-sort-key': ['get', 'rang'] },
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
