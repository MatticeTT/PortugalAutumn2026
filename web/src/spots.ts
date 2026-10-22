// Surfspots: gegevens (scores per spot) en alles wat ze in gewone woorden zegt.

export const PLANKEN: Record<string, string> = {
  LB: 'Longboard', MM: 'Minimal', MID: 'Midlength', GR: 'Groveler', FI: 'Fish', SB: 'Shortboard', SU: 'Step-up', GUN: 'Gun',
}

export type Vak = [string, string, number] // van, tot (ISO, UTC), gemiddelde score

export interface SpotKort {
  id: number
  naam: string
  lat: number
  lon: number
  richting: number
  soort: string | null
  groep: number
  tijdvakken: Record<string, Vak[]>
}

export interface SpotIndex {
  run: string
  drempel: number
  min_uren: number
  spots: SpotKort[]
}

export interface SpotDetail {
  naam: string
  richting: number
  soort: string | null
  werkt_bij_tij: string[] | null
  gevaren: string[]
  bodem: string | null
  herkomst: Record<string, string>
  start: string
  uren: number
  score: Record<string, number[]> // x 10, per uur vanaf start
  deining: ([number, number, number] | null)[] // hoogte m, richting vandaan, periode s
  windzee: (number | null)[]
  breker: (number | null)[]
  wind: ([number, number, number] | null)[] // kn, rel (0 aflandig, 180 aanlandig), stoten kn
  vlaggen: Record<string, string[]>
  expert: string[]
  getij: [string, 'hoog' | 'laag', number][]
}

export class SpotData {
  index: SpotIndex | null = null
  private details = new Map<number, Promise<SpotDetail>>()

  constructor(private base: string) {}

  async load() {
    const r = await fetch(`${this.base}/index.json`, { cache: 'no-cache' })
    if (r.ok) this.index = await r.json()
    return this.index
  }

  detail(id: number): Promise<SpotDetail> {
    let p = this.details.get(id)
    if (!p) {
      p = fetch(`${this.base}/${id}.json`).then((r) => r.json())
      this.details.set(id, p)
    }
    return p
  }

  spot(id: number) {
    return this.index?.spots.find((s) => s.id === id)
  }
}

// ---- Dagen en tijden (lokale tijd van het toestel) ----

export const dagSleutel = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
export const uur = (iso: string | Date) => {
  const d = new Date(iso)
  return `${d.getHours()}u${d.getMinutes() ? String(d.getMinutes()).padStart(2, '0') : ''}`
}
const dagKort = new Intl.DateTimeFormat('nl-NL', { weekday: 'short', day: 'numeric' })
const dagLang = new Intl.DateTimeFormat('nl-NL', { weekday: 'long', day: 'numeric', month: 'long' })
export function dagNaam(d: Date, lang = false) {
  const vandaag = new Date()
  const morgen = new Date(vandaag.getTime() + 864e5)
  const s = (lang ? dagLang : dagKort).format(d)
  const naam = s.charAt(0).toUpperCase() + s.slice(1)
  if (dagSleutel(d) === dagSleutel(vandaag)) return lang ? `Vandaag, ${s}` : 'Vandaag'
  if (dagSleutel(d) === dagSleutel(morgen)) return lang ? `Morgen, ${s}` : 'Morgen'
  return naam
}

export const rond = (x: number) => Math.floor(x + 0.5) // ,5 naar boven (regels)
export const woordScore = (s: number) => (rond(s) >= 5 ? 'TOP' : rond(s) >= 4 ? 'GOED' : '')

/** Goede tijdvakken op een dag voor de gekozen planken: [plank, vak][], beste eerst. */
export function vakkenOpDag(s: SpotKort, dag: string, planken: string[]): [string, Vak][] {
  const uit: [string, Vak][] = []
  for (const p of planken) {
    for (const v of s.tijdvakken[p] ?? []) {
      if (dagSleutel(new Date(v[0])) === dag) uit.push([p, v])
    }
  }
  return uit.sort((a, b) => b[1][2] - a[1][2] || Date.parse(a[1][0]) - Date.parse(b[1][0]))
}

/** Beste score van een spot op een dag (0 als nergens goed). */
export const besteOpDag = (s: SpotKort, dag: string, planken: string[]) =>
  Math.max(0, ...vakkenOpDag(s, dag, planken).map(([, v]) => v[2]))

// ---- Gewone woorden ----

const KOMPAS = ['noorden', 'noordnoordoosten', 'noordoosten', 'oostnoordoosten', 'oosten', 'oostzuidoosten', 'zuidoosten',
  'zuidzuidoosten', 'zuiden', 'zuidzuidwesten', 'zuidwesten', 'westzuidwesten', 'westen', 'westnoordwesten', 'noordwesten', 'noordnoordwesten']
export const kompas = (deg: number) => KOMPAS[Math.round(deg / 22.5) % 16]

export function golfWoord(hb: number) {
  if (hb < 0.3) return 'vlak'
  if (hb < 0.6) return 'kniehoog'
  if (hb < 0.9) return 'heuphoog'
  if (hb < 1.2) return 'borsthoog'
  if (hb < 1.6) return 'schouder- tot hoofdhoog'
  if (hb < 2.2) return 'overhead'
  if (hb < 3) return 'anderhalve keer overhead'
  return 'dubbel overhead of meer'
}

export const krachtWoord = (tp: number) => (tp >= 12 ? 'krachtig' : tp >= 9 ? 'met goede kracht' : 'zwak en kort')

export function windWoord(kn: number, rel: number) {
  const sterkte = kn < 5 ? 'Windstil' : kn < 11 ? 'Zwak' : kn < 17 ? 'Matig' : kn < 22 ? 'Stevig' : 'Hard'
  if (kn < 5) return `${sterkte} (${kn} kn): glad water`
  if (rel <= 45) return `${sterkte} aflandig (${kn} kn): ${kn > 20 ? 'golven netjes, maar moeilijk inpeddelen' : 'golven netjes en glad'}`
  if (rel < 135) return `${sterkte}, van opzij (${kn} kn): ${kn < 11 ? 'bijna glad' : 'wat rommelig'}`
  return `${sterkte} aanlandig (${kn} kn): ${kn < 8 ? 'licht rommelig' : 'rommelig en brokkelig'}`
}

export const EXPERT: Record<string, string> = {
  g: 'grote golven', h: 'holle golf over rif of rotsen', s: 'zware shorebreak', o: 'ondiep rif of rotsen', t: 'sterke stroming',
}

export const SOORT: Record<string, string> = {
  strand: 'Strand', zandbank: 'Zandbank', rif: 'Rif', point: 'Point break', riviermonding: 'Riviermonding', pier: 'Pier',
}

/** Afstand in km in rechte lijn. */
export function hemelsbreed(a: { lat: number; lon: number }, b: { lat: number; lon: number }) {
  const r = Math.PI / 180
  const x = Math.sin(((b.lat - a.lat) * r) / 2) ** 2 + Math.cos(a.lat * r) * Math.cos(b.lat * r) * Math.sin(((b.lon - a.lon) * r) / 2) ** 2
  return 2 * 6371 * Math.asin(Math.sqrt(x))
}

/** Route in Google Maps (opent de app op de telefoon als die er is). */
export const routeLink = (s: { lat: number; lon: number }) =>
  `https://www.google.com/maps/dir/?api=1&destination=${s.lat.toFixed(5)},${s.lon.toFixed(5)}&travelmode=driving`

export const esc = (t: string) => t.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]!)
