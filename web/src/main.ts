import maplibregl, { type GeoJSONSource, type StyleSpecification } from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import './style.css'
import { themaKnop } from './thema'
import { beeldNaam, beeldUitNaam, leesStil, leesTeken } from './scorekaart'
import { ontpak } from './inpakken'
import { openFiche, sluitFiche, toonUur } from './fiche'
import { zoekveld } from './zoek'
import { groepIcoon, laadKlim, openKlim, ververs as klimVervers } from './klim'
import type { Getij, Index, KaartStrand } from './types'
import { gewicht, instelling, surfPaneel, toont } from './surf'
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
  // Score van de rekenchat (2.1), standaardgewicht. alle: per strand per uur golf- en windteken, daarna per uur
  // stille waters en storm. Per niveau (beginner, gemiddeld, ervaren): alleen golf- en windteken.
  score: {} as Record<string, string[]>,
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

// Per strand per uur: golf- en windteken (van het gekozen niveau) en stille waters met storm.
// Bij een ander gewicht dan 75 kg: de uren waar het windteken anders is, uit sport/gewicht_<kg>.json
// (per strand stukjes van 6 tekens: uur in 2 tekens, dan het windteken voor alle, beginner, gemiddeld, ervaren).
const NIVEAU_KOLOM: Record<string, number> = { '': 0, beginner: 1, gemiddeld: 2, ervaren: 3 }
const gewichtVerschil = new Map<number, Map<number, string>[]>()
export function tekensUur(k: number, i: number): { g: string; w: string; s: string } {
  const alle = staat.score.alle?.[k] ?? ''
  const rij = (instelling.niveau ? staat.score[instelling.niveau]?.[k] : null) ?? alle
  const n = staat.index.tijd.length
  const anders = gewicht() ? gewichtVerschil.get(gewicht()!)?.[k]?.get(i) : undefined
  const w = anders ? anders[NIVEAU_KOLOM[instelling.niveau] ?? 0] : rij[2 * i + 1]
  return { g: rij[2 * i] ?? '-', w: w ?? '-', s: alle[2 * n + i] ?? '-' }
}
async function laadGewicht(g: number) {
  if (gewichtVerschil.has(g)) return
  const rijen: string[] = await data(`sport/gewicht_${g}.json`)
  gewichtVerschil.set(g, rijen.map((r) => {
    const m = new Map<number, string>()
    for (let j = 0; j < r.length; j += 6) m.set(ontpak(r.slice(j, j + 2), 1, 2)[0]!, r.slice(j + 2, j + 6))
    return m
  }))
}

const rang = (t: string) => leesTeken(t).cijfer ?? -1

function features() {
  const i = staat.i
  return {
    type: 'FeatureCollection' as const,
    features: staat.stranden.flatMap((s, k) => {
      const { g, w, s: stil } = tekensUur(k, i)
      if (!toont(g, w, stil)) return [] // filters van de knop Surfen
      const storm = leesStil(stil).storm
      return [{ type: 'Feature' as const, geometry: { type: 'Point' as const, coordinates: [s.x, s.y] },
        properties: { id: s.id, naam: s.n, beeld: beeldNaam(w, g, storm), r: Math.max(rang(g), rang(w)) } }]
    }),
  }
}

async function laadNiveau(nv: string) {
  await Promise.all([nv && !staat.score[nv] ? data(`sport/score_${nv}.json`).then((r) => { staat.score[nv] = r }) : null,
    gewicht() ? laadGewicht(gewicht()!) : null])
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
  klimVervers()
  tekenRoutes()
}

// ---- Verblijf: waar je verblijft en hoe lang je wil rijden ----
// Per groep de route naar de beste plek dit uur binnen je rijtijd (cijfer 3 of 4): eerst het hoogste cijfer,
// dan de kortste rijtijd. Golfsporten gaan voor windsporten, die voor stille waters.
const SPORTEN = [
  { groep: 'golf', naam: 'Golfsporten', kleur: '#3f6fe0', tekst: '#2f5bc4', prio: 3 },
  { groep: 'wind', naam: 'Windsporten', kleur: '#16b3d0', tekst: '#0e8fa6', prio: 2 },
  { groep: 'stil', naam: 'Stille waters', kleur: '#8a949c', tekst: '#6b757d', prio: 1 },
] as const
let verblijf: Verblijf | null = null
let rij = new Map<string, number | null>()
let verblijfPunt: maplibregl.Marker | null = null
let routeBeurt = 0
let inBeeld = false // na een nieuwe keuze één keer verblijf en bestemmingen samen in beeld brengen

function besteDitUur() {
  const i = staat.i, max = verblijf?.max ?? 0
  const uit: { sport: (typeof SPORTEN)[number]; s: KaartStrand; score: number; min: number }[] = []
  for (const sport of SPORTEN) {
    if (instelling.toon !== 'alles' && instelling.toon !== sport.groep) continue
    let best: (typeof uit)[number] | null = null
    staat.stranden.forEach((s, k) => {
      const t = tekensUur(k, i)
      const score = sport.groep === 'stil' ? leesStil(t.s).cijfer : leesTeken(sport.groep === 'golf' ? t.g : t.w).cijfer
      if (score === null || score < 3) return
      const m = rij.get(s.id)
      if (m == null || m > max) return
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
    : `<li class="rustig">Dit uur niets met 3 of 4 binnen ${rijTekst(v.max)}</li>`
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
  const eerste = Promise.all([data('sport/score_alle.json'), laadNiveau(instelling.niveau)])
  setInterval(nieuweBerekening, 5 * 60 * 1000)
  document.addEventListener('visibilitychange', () => { if (!document.hidden) nieuweBerekening() })

  kaart = new maplibregl.Map({
    container: 'kaart', style: await stijl(), bounds: PORTUGAL, minZoom: 5, maxZoom: 16,
    maxBounds: [[-16, 33], [14, 55]], attributionControl: { compact: true },
  })
  kaart.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-left')
  kaart.addControl(new maplibregl.GeolocateControl({ trackUserLocation: false }), 'top-left')

  kaart.on('load', async () => {
    const [alle] = await eerste
    staat.score.alle = alle
    kaart.addSource('stranden', {
      type: 'geojson', data: features(), cluster: true, clusterRadius: 30, clusterMaxZoom: 9,
      clusterProperties: { r: ['max', ['get', 'r']] },
    })
    // Links WIND, rechts WAVE.
    // Samengeklonterd: het aantal stranden in een wit bolletje met cyaan rand en cijfer.
    // De cirkels zelf worden pas getekend als de kaart ze nodig heeft (veel combinaties).
    kaart.on('styleimagemissing', (e) => {
      if (kaart.hasImage(e.id)) return
      const n = /^sg\|(\d+)$/.exec(e.id)
      if (n) { kaart.addImage(e.id, groepIcoon(Number(n[1]), '#0e8fa6'), { pixelRatio: 2 }); return }
      const c = beeldUitNaam(e.id)
      if (c) kaart.addImage(e.id, c, { pixelRatio: 2 })
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
      layout: { 'icon-image': ['get', 'beeld'] as any, 'icon-allow-overlap': true, 'symbol-sort-key': ['get', 'r'] } })
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
    surfPaneel(async (niveauAnders) => {
      if (niveauAnders) await laadNiveau(instelling.niveau)
      ;(kaart.getSource('stranden') as GeoJSONSource).setData(features())
      toonUur()
      tekenRoutes()
    })
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
