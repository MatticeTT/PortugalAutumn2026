// Score per watersport (rekenchat, versie 2.1). Letterlijke omzetting van pipeline/rules/score.py
// (referentie: docs/rekenchat/score_referentie.py). Alle grenswaarden komen uit score_parameters.json;
// tests/test_score_ts.py controleert dat deze versie exact dezelfde uitkomst geeft als de Python-versie.
// Windsnelheden in knopen, hoogtes in meter, periodes in seconden, hoeken in graden ten opzichte van de
// kijkrichting (wind: 0 = recht aanlandig, 90 = side-shore, 180 = recht aflandig; golf: 0 = recht op het strand).
import P from './score_parameters.json'

const G = 9.81
export const GO: number = P.ga_vanaf
const LOW_SIDE: number = P.brekende_golf_onderkant_factor
const SEC_MAX: number = P.bijkomend_max_aftrek
const REF_WEIGHT: number = P.referentiegewicht_kg

type Trap = (number | null)[]
type Pts = [number, number][]

export interface Cond {
  wind: number
  vlaag?: number
  windhoek: number
  golfhoogte?: number
  hb?: number
  periode?: number
  golfhoek?: number
  aandeel_hoofdgolf?: number | null
  golf_aan_strand?: number
  stroming?: number | null
  stroming_tov_wind?: 'tegen' | 'mee' | 'dwars'
  neerslag?: number | null
  onweer?: boolean
  donker?: boolean
  uur_tot_donker?: number | null
  watertemperatuur?: number | null
  gewicht?: number
  getij_match?: number | null
}

// ---------- bouwstenen ----------
export function breakingHeight(h0: number, t: number): number {
  if (h0 <= 0 || t <= 0) return 0
  return 0.39 * G ** 0.2 * (t * h0 * h0) ** 0.4
}

function trap(x: number, a: number | null, b: number | null, c: number | null, d: number | null): number {
  if (a !== null && x <= a) return 0
  if (d !== null && x >= d) return 0
  if (b !== null && x < b) return (x - (a as number)) / (b - (a as number))
  if (c !== null && x > c) return ((d as number) - x) / ((d as number) - c)
  return 1
}

function golfSub(hb: number, [a, b, c, d]: Trap): number {
  return Math.min(trap(LOW_SIDE * hb, a, b, null, null), trap(hb, null, null, c, d))
}

function upper(x: number, ideal: number, zero: number): number {
  return trap(x, null, null, ideal, zero)
}

function piecewise(x: number, pts: Pts): number {
  if (x <= pts[0][0]) return pts[0][1]
  for (let i = 0; i < pts.length - 1; i++) {
    const [x0, y0] = pts[i]
    const [x1, y1] = pts[i + 1]
    if (x <= x1) return x1 > x0 ? y0 + (y1 - y0) * (x - x0) / (x1 - x0) : y1
  }
  return pts[pts.length - 1][1]
}

function surfWind(v: number, angle: number, anchors: Record<string, number[]>): number {
  let f: number, lo: number[], hi: number[]
  if (angle <= 90) {
    f = angle / 90
    lo = anchors['0']; hi = anchors['90']
  } else {
    f = (angle - 90) / 90
    lo = anchors['90']; hi = anchors['180']
  }
  const ideal = lo[0] + f * (hi[0] - lo[0])
  const zero = lo[1] + f * (hi[1] - lo[1])
  return upper(v, ideal, zero)
}

type Deel = Record<string, number>
type Bij = Record<string, number | null>

function combine(essentials: Deel, secondary: Bij): number {
  const vals = Object.values(essentials)
  const lo = Math.min(...vals)
  const rest = vals.slice()
  rest.splice(rest.indexOf(lo), 1)
  const meanRest = rest.length ? sum(rest) / rest.length : 1
  const core = lo * (0.75 + 0.25 * meanRest)
  const known = Object.values(secondary).filter((v): v is number => v !== null && v !== undefined)
  const sec = known.length ? sum(known) / known.length : 1
  return 100 * core * (1 - SEC_MAX * (1 - sec))
}

function sum(xs: number[]): number {
  let s = 0
  for (const x of xs) s += x
  return s
}

// Zoals Python round(x, 1): afronden op de exacte waarde van het getal (toFixed doet dat), en een exacte
// helft (alleen mogelijk bij x = k/4 met k oneven, bv. 87,25) naar het even cijfer.
function round1(x: number): number {
  if (Number.isInteger(x * 4) && !Number.isInteger(x * 2)) {
    const n = Math.floor(x * 10)
    return (n % 2 === 0 ? n : n + 1) / 10
  }
  return parseFloat(x.toFixed(1))
}

// ---------- grenswaarden ----------
interface SurfP { hb: Trap; t: Trap; wind: Record<string, number[]>; cur: number[] }
interface FlatP { wind: number[]; angle: Pts; gust: number[]; water: Trap }
interface WaveP { wind: number[]; angle: Pts; gust: number[]; hb: Trap; t: Trap }

const SURF = P.golfsurfen as unknown as Record<string, SurfP>
const FLAT = Object.fromEntries(Object.entries(P.vlak_water).map(([k, v]) => [k, v.profielen])) as unknown as
  Record<string, Record<string, FlatP>>
const WAVE = P.op_golven as unknown as Record<string, WaveP>

export const CATEGORIES: string[] = [...Object.keys(SURF), ...Object.keys(FLAT), ...Object.keys(WAVE)]

// ---------- bijkomende factoren ----------
function secWaveAngleSurf(a: number): number {
  return piecewise(Math.abs(a), [[0, 0.8], [10, 1], [30, 1], [60, 0.7], [90, 0.5]])
}

function secWaveAngleWave(a: number): number {
  return piecewise(Math.abs(a), [[0, 1], [20, 1], [45, 0.5], [70, 0]])
}

function secClean(share: number | null | undefined): number | null {
  return share === null || share === undefined ? null : piecewise(share, [[0.4, 0], [0.8, 1]])
}

function secCurrentWind(cur: number | null | undefined, rel: string): number | null {
  if (cur === null || cur === undefined) return null
  const zero = rel !== 'mee' ? 3.0 : 2.0
  return upper(cur, 1.0, zero)
}

function secRain(mm: number | null | undefined): number | null {
  return mm === null || mm === undefined ? null : piecewise(mm, [[0.5, 1], [3, 0.5], [8, 0.2]])
}

function effWind(v: number, cur: number | null | undefined, rel: string): number {
  if (!cur) return v
  return rel === 'tegen' ? v + cur : rel === 'mee' ? v - cur : v
}

function hbVan(c: Cond): number {
  return c.hb !== undefined ? c.hb : breakingHeight(c.golfhoogte ?? 0, c.periode ?? 0)
}

// ---------- score ----------
export interface Score {
  score: number
  veto: string | null
  profiel: string | null
  essentieel: Deel
  bijkomend: Bij
  hb?: number
}

export function score(category: string, c: Cond): Score {
  if (c.onweer || c.donker) {
    return { score: 0, veto: c.onweer ? 'onweer' : 'donker', profiel: null, essentieel: {}, bijkomend: {} }
  }
  const wratio = (c.gewicht ?? REF_WEIGHT) / REF_WEIGHT
  const f = category.startsWith('kite') ? wratio : Math.sqrt(wratio)
  const tide = c.getij_match ?? null
  const cur = c.stroming ?? null
  const rel = c.stroming_tov_wind ?? 'dwars'
  let best: Score | null = null
  const keep = (res: Score) => { if (best === null || res.score > best.score) best = res }

  if (category in SURF) {
    const p = SURF[category]
    const hb = hbVan(c)
    const w = surfWind(c.wind, c.windhoek, p.wind)
    const ess = { golf: golfSub(hb, p.hb), wind: w, periode: trap(c.periode ?? 0, ...(p.t as [number, number, number, number])) }
    const sec = {
      golfrichting: secWaveAngleSurf(c.golfhoek ?? 20),
      zuiverheid: secClean(c.aandeel_hoofdgolf),
      stroming: cur === null ? null : upper(cur, p.cur[0], p.cur[1]),
      getij: tide,
    }
    keep({ score: combine(ess, sec), profiel: null, essentieel: ess, bijkomend: sec, veto: null, hb })
  } else if (category in FLAT) {
    const v = effWind(c.wind, cur, rel)
    const gust = Math.max(0, (c.vlaag ?? c.wind) - c.wind)
    for (const [name, p] of Object.entries(FLAT[category])) {
      const [a, b, cc, d] = p.wind
      const ess = {
        wind: trap(v, a * f, b * f, cc * f, d * f),
        windrichting: piecewise(c.windhoek, p.angle),
        vlagen: upper(gust, p.gust[0], p.gust[1]),
        water: trap(c.golf_aan_strand ?? 0, p.water[0], p.water[1], p.water[2], p.water[3]),
      }
      const sec = { stroming: secCurrentWind(cur, rel), neerslag: secRain(c.neerslag), getij: tide }
      keep({ score: combine(ess, sec), profiel: name, essentieel: ess, bijkomend: sec, veto: null })
    }
  } else {
    const p = WAVE[category]
    const v = effWind(c.wind, cur, rel)
    const gust = Math.max(0, (c.vlaag ?? c.wind) - c.wind)
    const hb = hbVan(c)
    const [a, b, cc, d] = p.wind
    const ess = {
      wind: trap(v, a * f, b * f, cc * f, d * f),
      windrichting: piecewise(c.windhoek, p.angle),
      vlagen: upper(gust, p.gust[0], p.gust[1]),
      golf: golfSub(hb, p.hb),
      periode: trap(c.periode ?? 0, ...(p.t as [number, number, number, number])),
    }
    const sec = {
      golfrichting: secWaveAngleWave(c.golfhoek ?? 10),
      stroming: secCurrentWind(cur, rel), neerslag: secRain(c.neerslag), getij: tide,
    }
    keep({ score: combine(ess, sec), profiel: null, essentieel: ess, bijkomend: sec, veto: null, hb })
  }
  const b = best as unknown as Score
  b.score = round1(b.score)
  return b
}

// ---------- categorie 18: stille waters ----------
const STIL = P.stille_waters
const STORM_WIND: number = P.storm.wind_vanaf_knopen
const STORM_GUST: number = P.storm.vlaag_vanaf_knopen

export function isStorm(c: Cond): boolean {
  return c.wind >= STORM_WIND || (c.vlaag ?? 0) >= STORM_GUST
}

export function stilleWaters(c: Cond): Score {
  if (c.onweer || c.donker) {
    return { score: 0, veto: c.onweer ? 'onweer' : 'donker', profiel: null, essentieel: {}, bijkomend: {} }
  }
  let w = upper(c.wind, STIL.wind[0], STIL.wind[1])
  if ((c.windhoek ?? 0) >= 120) w = Math.min(w, upper(c.wind, STIL.off_wind[0], STIL.off_wind[1]))
  const hb = c.hb !== undefined ? c.hb : breakingHeight(c.golfhoogte ?? 0, c.periode ?? 0)
  const ess = { wind: w, water: upper(Math.max(c.golf_aan_strand ?? 0, hb), STIL.water[0], STIL.water[1]) }
  const cur = c.stroming ?? null
  const sec = { stroming: cur === null ? null : upper(cur, STIL.cur[0], STIL.cur[1]), neerslag: secRain(c.neerslag) }
  return { score: round1(combine(ess, sec)), veto: null, profiel: null, essentieel: ess, bijkomend: sec }
}

export function waarschuwingen(category: string, c: Cond): string[] {
  const out: string[] = []
  const t = c.watertemperatuur
  if (t !== null && t !== undefined && t < 8) out.push('water onder 8 graden: wedstrijden gaan dan niet door')
  else if (t !== null && t !== undefined && t < 15) out.push('water onder 15 graden: kans op koudeshock, wetsuit nodig')
  const u = c.uur_tot_donker
  if (u !== null && u !== undefined && u < 1) out.push('minder dan een uur tot donker')
  const hoek = c.windhoek ?? 0
  const windCat = category in FLAT || category in WAVE
  if (windCat && hoek >= 110) out.push('wind van land: je drijft naar zee bij pech')
  if (category.startsWith('kite') && hoek <= 20) out.push('recht aanlandige wind: blijf 80 m van de kust en van obstakels')
  if (category.startsWith('kite')) out.push('houd drie lijnlengtes vrij benedenwinds')
  if (category in SURF && c.stroming !== null && c.stroming !== undefined && c.stroming >= 1.0) out.push('sterke stroming')
  return out
}

// ---------- algemene score: cirkel 0-4 met rand ----------
export type Niveau = 'beginner' | 'gemiddeld' | 'ervaren'
const LEVEL: Record<string, number> = { beginner: 0, gemiddeld: 1, ervaren: 2 }
export type Rand = 'groen' | 'oranje' | 'rood'
const RAND: Rand[] = ['groen', 'oranje', 'rood']
export const GOLF = CATEGORIES.filter((k) => ['golfsurfen', 'longboard', 'shortboard'].includes(k.split('_')[0]))
export const WIND = CATEGORIES.filter((k) => !GOLF.includes(k))

export function cijfer(score100: number): number {
  return Math.min(4, Math.floor(score100 / 20))
}

function teVeel(cats: string[], c: Cond): boolean {
  if (c.onweer || c.donker) return false
  const surf = cats.filter((k) => k in SURF)
  if (surf.length) {
    const hb = hbVan(c)
    return hb > Math.max(...surf.map((k) => SURF[k].hb[2] as number))
  }
  const wratio = (c.gewicht ?? REF_WEIGHT) / REF_WEIGHT
  let grens = 0
  for (const k of cats) {
    const f = k.startsWith('kite') ? wratio : Math.sqrt(wratio)
    const profs = k in FLAT ? Object.values(FLAT[k]) : [WAVE[k]]
    grens = Math.max(grens, Math.max(...profs.map((p) => p.wind[2] * f)))
  }
  return c.wind > grens
}

export interface Groep {
  cijfer: number
  rand: Rand | null
  beste: string
  scores: Record<string, number>
  te_veel: boolean
}

export function algemeen(groep: string[], c: Cond, niveau: Niveau | null = null): Groep {
  const cats = groep.filter((k) => niveau === null || k.endsWith(niveau))
  const scores: Record<string, number> = {}
  for (const k of cats) scores[k] = score(k, c).score
  let beste = cats[0]
  for (const k of cats) if (scores[k] > scores[beste]) beste = k
  const n = cijfer(scores[beste])
  let rand: Rand | null = null
  if (n >= 3) {
    const laagste = Math.min(...cats.filter((k) => scores[k] >= GO).map((k) => LEVEL[k.slice(k.lastIndexOf('_') + 1)]))
    rand = RAND[laagste]
  }
  return { cijfer: n, rand, beste, scores, te_veel: n < 3 && teVeel(cats, c) }
}

export const BETEKENIS = ['niets', 'iets', 'potentieel', 'zekerheid', 'ideaal']

export interface StrandUur {
  golf: Groep
  wind: Groep
  stille_waters: Score & { cijfer: number }
  storm: boolean
  te_gevaarlijk: boolean
  onweer: boolean
  donker: boolean
}

export function strandUur(c: Cond, niveau: Niveau | null = null): StrandUur {
  const g = algemeen(GOLF, c, niveau)
  const w = algemeen(WIND, c, niveau)
  const st = stilleWaters(c)
  return {
    golf: g, wind: w, stille_waters: { ...st, cijfer: cijfer(st.score) },
    storm: isStorm(c), te_gevaarlijk: isStorm(c) || g.te_veel || w.te_veel,
    onweer: !!c.onweer, donker: !!c.donker,
  }
}
