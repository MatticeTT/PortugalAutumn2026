// Het verblijf: waar je verblijft en hoe lang je wil rijden (overgenomen uit de eerste versie van de app).
// - plaats zoeken terwijl je typt (zoals Google Maps): Esri ArcGIS World Geocoding (zonder sleutel; kent ook hotels
//   en vakantieappartementen), met Photon (OpenStreetMap) als reserve; of je huidige locatie
// - rijtijden en routes: OSRM (router.project-osrm.org), rechtstreeks vanuit de browser
// Het verblijf wordt in deze browser bewaard; kaart en planning rekenen er vanaf dan mee.

export interface Verblijf { naam: string; lat: number; lon: number; max: number } // max in minuten
export interface Plek { id: string; lat: number; lon: number }

const SLEUTEL = 'verblijf-v1'
const OSRM = 'https://router.project-osrm.org'
const ESRI = 'https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer'
const PHOTON = 'https://photon.komoot.io/api/'

export function leesVerblijf(): Verblijf | null {
  try {
    const v = JSON.parse(localStorage.getItem(SLEUTEL) ?? 'null')
    return v && Number.isFinite(v.lat) && Number.isFinite(v.lon) && Number.isFinite(v.max) ? v : null
  } catch { return null }
}
export function bewaarVerblijf(v: Verblijf) {
  try { localStorage.setItem(SLEUTEL, JSON.stringify(v)) } catch { /* niet bewaard */ }
}

export function wisVerblijf() {
  try { localStorage.removeItem(SLEUTEL) } catch { /* niets */ }
}

// Klik je op een tabblad (Kaart, Planning), dan zet de pagina een merkteken voor de volgende pagina.
// Zo weet de kaart dat je van de planning komt (verblijf onthouden) en niet herlaadt (lege vraag).
export function tabWissel() {
  document.querySelectorAll<HTMLAnchorElement>('.tabs a').forEach((a) =>
    a.addEventListener('click', () => { try { sessionStorage.setItem('via-tab', '1') } catch { /* niets */ } }))
}
export function komtViaTab() {
  try { const ja = sessionStorage.getItem('via-tab') === '1'; sessionStorage.removeItem('via-tab'); return ja } catch { return false }
}

export const rijTekst = (m: number) => m < 60 ? `${m} min` : `${Math.floor(m / 60)}u${m % 60 ? String(m % 60).padStart(2, '0') : ''}`

export interface Gevonden { naam: string; lat: number; lon: number; titel: string; adres: string; sleutel?: string }

// Suggesties terwijl je typt, eerst rond de Algarve. Antwoorden worden onthouden, zodat terugtypen meteen gaat.
const bewaard = new Map<string, Gevonden[]>()

// Zoeken zoals Google Maps: overal ter wereld, met plaatsen in de buurt eerst (het midden van de kaart,
// anders je verblijf, anders de Algarve).
let buurt = { lon: -8.5, lat: 37.12 }
export function zoekInDeBuurt(lon: number, lat: number) { buurt = { lon, lat } }
const zonderLand = (t: string) => t.replace(/, [A-Z]{3}$/, '') // Esri sluit af met de landcode (PRT, ESP, ...)

async function viaEsri(q: string, signal?: AbortSignal): Promise<Gevonden[]> {
  const url = `${ESRI}/suggest?f=json&location=${buurt.lon.toFixed(3)},${buurt.lat.toFixed(3)}&maxSuggestions=8&text=${encodeURIComponent(q)}`
  const r = await fetch(url, { signal })
  if (!r.ok) throw new Error(`Esri ${r.status}`)
  const d = await r.json()
  if (!d.suggestions) throw new Error('Esri')
  return d.suggestions.filter((x: any) => !x.isCollection).map((x: any) => {
    const delen = zonderLand(String(x.text)).split(', ')
    return { titel: delen[0], adres: delen.slice(1).join(', '), naam: zonderLand(String(x.text)),
      lat: NaN, lon: NaN, sleutel: x.magicKey }
  })
}

async function viaPhoton(q: string, signal?: AbortSignal): Promise<Gevonden[]> {
  const url = `${PHOTON}?q=${encodeURIComponent(q)}&limit=8&lat=${buurt.lat.toFixed(3)}&lon=${buurt.lon.toFixed(3)}`
  const r = await fetch(url, { signal })
  if (!r.ok) throw new Error(`Photon ${r.status}`)
  return (await r.json()).features.map((f: any) => {
    const p = f.properties ?? {}
    const straat = [p.street, p.housenumber].filter(Boolean).join(' ')
    const titel = p.name || straat || p.city || q
    const plaats = [p.postcode, p.city || p.town || p.village || p.district].filter(Boolean).join(' ')
    const adres = [p.name && straat, plaats !== titel && plaats, p.state].filter(Boolean).join(', ')
    return { titel, adres, naam: [titel, plaats].filter(Boolean).join(', '), lon: f.geometry.coordinates[0], lat: f.geometry.coordinates[1] }
  })
}

export async function zoekPlaats(q: string, signal?: AbortSignal): Promise<Gevonden[]> {
  const k = q.toLowerCase()
  if (bewaard.has(k)) return bewaard.get(k)!
  let r: Gevonden[]
  try { r = await viaEsri(q, signal) } catch (e) {
    if ((e as Error).name === 'AbortError') throw e
    r = await viaPhoton(q, signal)
  }
  bewaard.set(k, r)
  return r
}

// Een Esri-suggestie heeft nog geen coördinaten: die komen pas bij het kiezen.
export async function plaatsVan(g: Gevonden): Promise<Gevonden> {
  if (!g.sleutel || Number.isFinite(g.lat)) return g
  const r = await fetch(`${ESRI}/findAddressCandidates?f=json&maxLocations=1&singleLine=${encodeURIComponent(g.naam)}&magicKey=${encodeURIComponent(g.sleutel)}`)
  if (!r.ok) throw new Error(`Esri ${r.status}`)
  const c = (await r.json()).candidates?.[0]
  if (!c?.location) throw new Error('geen plaats')
  return { ...g, lat: c.location.y, lon: c.location.x }
}

// Rijtijd (minuten) over de weg van het verblijf naar elke plek (OSRM, de echte route).
// Plekken die je zelfs aan 140 km/h in rechte lijn niet binnen je maximale rijtijd haalt, worden niet
// opgevraagd: over de weg lukt dat zeker niet (zo blijven het er een paar honderd, ook met vier landen).
// Resultaten blijven in deze browser bewaard per verblijf.
export const ONBEREIKBAAR_KMH = 140
export function hemelsbreed(a: { lat: number; lon: number }, b: { lat: number; lon: number }) {
  const t = Math.PI / 180
  const h = Math.sin((b.lat - a.lat) * t / 2) ** 2 + Math.cos(a.lat * t) * Math.cos(b.lat * t) * Math.sin((b.lon - a.lon) * t / 2) ** 2
  return 2 * 6371 * Math.asin(Math.sqrt(h))
}
const geheugen = new Map<string, number | null>()
const cacheSleutel = (v: Verblijf) => `rij-v2:${v.lat.toFixed(4)},${v.lon.toFixed(4)}`
function laadCache(v: Verblijf) {
  try { return JSON.parse(localStorage.getItem(cacheSleutel(v)) ?? '{}') as Record<string, number | null> } catch { return {} }
}
function bewaarCache(v: Verblijf, c: Record<string, number | null>) {
  try { localStorage.setItem(cacheSleutel(v), JSON.stringify(c)) } catch { /* niet bewaard */ }
}

export async function rijtijden(v: Verblijf, plekken: Plek[]): Promise<Map<string, number | null>> {
  const cache = laadCache(v)
  const uit = new Map<string, number | null>()
  const vragen: Plek[] = []
  for (const p of plekken) {
    const k = `${p.id}`
    if (k in cache) { uit.set(p.id, cache[k]); continue }
    if (hemelsbreed(v, p) > (v.max / 60) * ONBEREIKBAAR_KMH) { uit.set(p.id, null); continue } // zeker te ver
    vragen.push(p)
  }
  for (let i = 0; i < vragen.length; i += 90) {
    const deel = vragen.slice(i, i + 90)
    const coords = [v, ...deel].map((p) => `${p.lon.toFixed(5)},${p.lat.toFixed(5)}`).join(';')
    const r = await fetch(`${OSRM}/table/v1/driving/${coords}?sources=0&annotations=duration`)
    if (!r.ok) throw new Error(`OSRM ${r.status}`)
    const d = await r.json()
    deel.forEach((p, k) => {
      const s = d.durations?.[0]?.[k + 1]
      const m = s == null ? null : Math.round(s / 60)
      uit.set(p.id, m); cache[p.id] = m
    })
  }
  bewaarCache(v, cache)
  for (const [k, m] of uit) geheugen.set(k, m)
  return uit
}

const routes = new Map<string, any>()
export async function route(v: Verblijf, p: Plek): Promise<any | null> {
  const k = `${v.lat},${v.lon}>${p.id}`
  if (routes.has(k)) return routes.get(k)
  const r = await fetch(`${OSRM}/route/v1/driving/${v.lon},${v.lat};${p.lon},${p.lat}?overview=simplified&geometries=geojson`)
  if (!r.ok) return null
  const g = (await r.json()).routes?.[0]?.geometry ?? null
  routes.set(k, g)
  return g
}
