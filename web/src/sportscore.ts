// Sportscore 1 tot 5 met uitleg, voor de fiche. Zelfde regels als pipeline/sport/score.py
// (document "Sportscore 1 tot 5: rekenregels per sport"); de uitleg volgt de Watersportwijzer.
// De grenzen komen uit index.json (pipeline/sport/sporten.yaml). tests/test_sport.py rekent
// de 41 testgevallen ook met dit bestand na.

export interface SportCfg {
  id: string
  naam: string
  groep: string
  [k: string]: any
}

export type Tij = 'laag' | 'op' | 'hoog' | 'af' | null

export interface Invoer {
  N: number | null
  K?: number | null
  BESTTIJ?: string | null
  DROOG?: boolean
  LUWTE?: [number, number] | null
  H: number | null
  T: number | null
  GR: number | null
  V: number | null
  G: number | null
  WR: number | null
  TIJ: Tij
}

export interface Afgeleid {
  theta: number; K: number; H: number; T: number; golf0: number; R: number
  GOLF: number; RUW: number; a: number; V: number; G: number; W: number; luw: boolean
  TIJ: Tij; BESTTIJ: string | null; DROOG: boolean
}

export interface Uitkomst { s: number; b: number; uitleg: string[] }

export const NAMEN = ['', 'niets', 'te licht', 'ideaal', 'sterk', 'te moeilijk']
const TIJ_NAAM: Record<string, string> = { laag: 'laag', op: 'opkomend', hoog: 'hoog', af: 'afgaand' }

const norm = (x: number) => ((x % 360) + 360) % 360
export const hoek = (d: number, n: number) => { const x = Math.abs(norm(d) - norm(n)); return x > 180 ? 360 - x : x }
const getal = (v: unknown): v is number => typeof v === 'number' && isFinite(v)
const trap = (x: number, g: number[]) => (x >= g[1] ? 2 : x >= g[0] ? 1 : 0)
const binA = (x: number, g: number[]) => g.reduce((n, gi) => (x >= gi ? n + 1 : n), 1)
const inSector = (r: number, van: number, tot: number) => {
  r = norm(r); van = norm(van); tot = norm(tot)
  return van <= tot ? r >= van && r <= tot : r >= van || r <= tot
}
export const schuif = (a: number, w: number[]) =>
  a <= 45 ? w[0] : a <= 90 ? w[0] + (w[1] - w[0]) * (a - 45) / 45 : a < 135 ? w[1] + (w[2] - w[1]) * (a - 90) / 45 : w[2]
export const k1 = (x: number) => (Math.round(x * 10) / 10).toFixed(1).replace('.', ',').replace(',0', '')
export const k2 = (x: number) => x.toFixed(2).replace('.', ',')

export function afgeleid(inv: Invoer): Afgeleid | null {
  const K = getal(inv.K) ? Math.min(1.5, Math.max(0, inv.K)) : 1
  let H = inv.H, T = inv.T
  if (K === 0) { H = 0; T = 10 }
  if (!getal(H) || !getal(T) || !getal(inv.V) || !getal(inv.WR) || !getal(inv.N) || H < 0 || T <= 0 || inv.V < 0) return null
  let V = inv.V
  let G = getal(inv.G) && inv.G > inv.V ? inv.G : inv.V
  let luw = false
  if (inv.LUWTE && inSector(inv.WR, inv.LUWTE[0], inv.LUWTE[1])) { V *= 0.5; G *= 0.5; luw = true }
  const theta = getal(inv.GR) ? hoek(inv.GR, inv.N) : 0
  const Tr = Math.min(T, 20)
  const golf0 = 0.33 * Math.pow(H, 0.8) * Math.pow(Tr, 0.4) * Math.pow(Math.max(1, Tr / 10), 0.85)
  const R = theta <= 80 ? Math.pow(Math.cos(theta * Math.PI / 180), 0.4) : theta < 135 ? 0.496 * (135 - theta) / 55 : 0
  return {
    theta, K, H, T, golf0, R, GOLF: K * R * golf0, RUW: K * Math.max(R, 0.1) * Math.max(golf0, H),
    a: hoek(inv.WR, inv.N), V, G, W: Math.max(V, G / 1.3), luw,
    TIJ: inv.TIJ ?? null, BESTTIJ: inv.BESTTIJ ?? null, DROOG: !!inv.DROOG,
  }
}

// Eerst OMHOOG (U), dan OMLAAG (D).
function pas(b: number, U: number, D: number) {
  let s = b
  if (U >= 2 && s >= 2) s = 5
  else if (U === 1 && s === 3) s = 4
  if (D > 0) {
    if (s <= 3) s = D >= 2 ? 1 : Math.max(1, s - 1)
    else if (s === 4 && D >= 2) s = 5
  }
  return s
}

export const kant = (a: number) =>
  a < 22.5 ? 'recht van zee' : a < 67.5 ? 'schuin van zee' : a <= 112.5 ? 'langs het strand' : a < 157.5 ? 'schuin van land' : 'recht van land'
const windTekst = (x: Afgeleid) => `${k1(x.W)} kn ${kant(x.a)}`
const vlagen = (x: Afgeleid) => (x.G >= 2 * x.V && x.G >= 25 ? 2 : x.G - x.V >= 10 && x.G >= 1.5 * x.V ? 1 : 0)
function windBasis(g: number[], x: Afgeleid) {
  if (x.W >= g[3]) return 5
  if (x.W >= g[2]) return 4
  if (x.V >= g[1]) return 3
  if (x.V >= g[0]) return 2
  return 1
}

function scoreA(sp: SportCfg, x: Afgeleid): Uitkomst {
  let b = binA(x.GOLF, sp.golf)
  const u: string[] = []
  u.push(x.K === 0 ? 'Lagune: hier breken geen golven.'
    : x.R === 0 ? 'De golven lopen van het strand weg: er komt niets binnen.'
    : `Golf aan het strand ${k2(x.GOLF)} m: ${NAMEN[b]}.`)
  if (sp.periode && b === 3 && x.T < 6) { b = 2; u.push('Periode onder 6 s: slappe windgolven, van 3 naar 2.') }
  const p = trap(x.W, [schuif(x.a, sp.wind1), schuif(x.a, sp.wind2)])
  const isU = sp.straf === 'omhoog' || x.a > 112.5
  const tij = (x.BESTTIJ === 'laag' && x.TIJ === 'hoog') || (x.BESTTIJ === 'hoog' && x.TIJ === 'laag') ? 1 : 0
  const s = isU ? pas(b, p, tij) : pas(b, 0, Math.min(2, p + tij))
  if (p > 0) u.push(`Wind ${windTekst(x)}: ${isU ? (p === 2 ? 'te zwaar.' : 'zwaarder.') : (p === 2 ? 'de golven zijn verpest.' : 'de golven zijn rommelig.')}`)
  if (tij) u.push(`Dit strand werkt het best bij ${x.BESTTIJ} water, en het is nu ${TIJ_NAAM[x.TIJ!]} water.`)
  return { s, b, uitleg: u }
}

function scoreB(sp: SportCfg, x: Afgeleid): Uitkomst {
  const b = windBasis(sp.wind, x)
  const u = [`Wind ${k1(x.V)} kn${x.W > x.V + 1e-9 ? ` (met de stoten telt ${k1(x.W)} kn)` : ''}: ${NAMEN[b]}.`]
  const land = sp.richting === 'land'
  if (land && x.TIJ === 'hoog') return { s: 1, b, uitleg: u.concat(['Hoog water: er is geen hard strand om op te rijden.']) }
  const ur = sp.ruw ? trap(x.RUW, sp.ruw) : 0
  let ud = 0
  if (sp.richting === 'kite') ud = x.a <= 90 ? 0 : x.a <= 112.5 ? 1 : 2
  else if (sp.richting === 'zeil') ud = x.a > 112.5 && x.W >= 10 ? 1 : 0
  else ud = x.a > 112.5 ? 1 : 0
  if (x.K === 0 && !land) ud = 0
  const uv = vlagen(x)
  if (b >= 2) {
    if (ur) u.push(`Water ${k2(x.RUW)} m ruw: ${ur === 2 ? 'te ruw.' : 'alleen met ervaring.'}`)
    if (ud) u.push(`Wind ${kant(x.a)}: ${ud === 2 ? 'je wordt van het strand weggeblazen.' : 'alleen met ervaring.'}`)
    if (uv) u.push(`Vlagerig, stoten van ${k1(x.G)} kn: ${uv === 2 ? 'te gevaarlijk.' : 'alleen met ervaring.'}`)
  }
  return { s: pas(b, Math.max(ur, ud, uv), 0), b, uitleg: u }
}

function scoreC(sp: SportCfg, x: Afgeleid): Uitkomst {
  const bw = windBasis(sp.wind, x)
  const bg = x.RUW >= 3.0 ? 5 : x.RUW >= 2.0 ? 4 : x.GOLF >= 0.8 ? 3 : x.GOLF >= 0.5 ? 2 : 1
  let b: number
  if (bw === 1) b = 1
  else if (bw === 5 || bg === 5) b = 5
  else if (bg === 1) b = 1
  else if (bw === 2) b = bg >= 4 ? 5 : 2
  else if (bw === 4 || bg === 4) b = 4
  else b = Math.min(bw, bg)
  const u = [`Wind ${k1(x.V)} kn: ${NAMEN[bw]}. Golf ${k2(x.GOLF)} m: ${NAMEN[bg]}.`]
  if (bw === 2 && bg === 4) u.push('Te weinig wind voor zulke golven: je raakt niet meer uit de branding.')
  let ud = x.a <= 112.5 ? 0 : x.a <= 157.5 ? 1 : 2
  if (sp.zeekant && x.a < 22.5) ud = Math.max(ud, 1)
  const uv = vlagen(x)
  if (b >= 2) {
    if (ud) u.push(`Wind ${kant(x.a)}: ${ud === 2 ? 'je wordt van het strand weggeblazen.' : 'alleen met ervaring.'}`)
    if (uv) u.push(`Vlagerig, stoten van ${k1(x.G)} kn: ${uv === 2 ? 'te gevaarlijk.' : 'alleen met ervaring.'}`)
  }
  return { s: pas(b, Math.max(ud, uv), 0), b, uitleg: u }
}

function scoreD(sp: SportCfg, x: Afgeleid): Uitkomst {
  const w = x.a > 112.5 && x.K > 0 ? sp.land : sp.wind
  const ur = trap(x.RUW, sp.ruw), uw = trap(x.W, w)
  return {
    s: 3 + Math.max(ur, uw), b: 3, uitleg: [
      `Water ${k2(x.RUW)} m ruw: ${ur === 2 ? 'te ruw.' : ur === 1 ? 'alleen met ervaring.' : 'kalm genoeg.'}`,
      `Wind ${windTekst(x)}: ${uw === 2 ? 'te veel.' : uw === 1 ? 'alleen met ervaring.' : 'geen probleem.'}`,
    ],
  }
}

export function bereken(sporten: SportCfg[], inv: Invoer): { x: Afgeleid; d: Record<string, Uitkomst> } | null {
  const x = afgeleid(inv)
  if (!x) return null
  const d: Record<string, Uitkomst> = {}
  for (const sp of sporten) {
    const f = { A: scoreA, B: scoreB, C: scoreC, D: scoreD }[sp.groep as 'A' | 'B' | 'C' | 'D']
    let r = f(sp, x)
    if (x.DROOG && x.TIJ === 'laag' && sp.id !== 'landkite') r = { s: 1, b: r.b, uitleg: ['Laag water: hier staat nu geen water.'] }
    d[sp.id] = r
  }
  return { x, d }
}
