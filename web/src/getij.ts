import type { Getij } from './types'

export type Extreem = { t: number; h: number; hoog: boolean } // t in minuten sinds 1970 UTC, h in m tegenover het ZH

// Zelfde rekenwijze als pipeline/tides/interp.py: elk hoog- en laagwater van station a
// gemengd met dat van station b, gewicht w.
export function extremen(g: Getij, a: string, b: string, w: number): Extreem[] {
  const ea = g.stations[a].e
  const eb = g.stations[b].e
  if (w === 0 || a === b) return ea.map(([t, h, hi]) => ({ t, h: h / 100, hoog: hi === 1 }))
  const out: Extreem[] = []
  let j = 0
  for (const [t, h, hi] of ea) {
    while (j < eb.length - 1 && eb[j + 1][0] < t - 180) j++
    let best: [number, number, number] | null = null
    for (let k = Math.max(0, j - 2); k < Math.min(eb.length, j + 4); k++) {
      const e = eb[k]
      if (e[2] === hi && Math.abs(e[0] - t) <= 180 && (!best || Math.abs(e[0] - t) < Math.abs(best[0] - t))) best = e
    }
    if (best) out.push({ t: Math.round(t + w * (best[0] - t)), h: (h + w * (best[1] - h)) / 100, hoog: hi === 1 })
  }
  return out
}

// Waterhoogte tussen twee extremen: halve cosinus (zoals de "regel van twaalfden").
export function hoogte(ex: Extreem[], t: number): number | null {
  let i = ex.findIndex((e) => e.t > t)
  if (i <= 0) return null
  const a = ex[i - 1], b = ex[i]
  const f = (t - a.t) / (b.t - a.t)
  return a.h + (b.h - a.h) * (1 - Math.cos(Math.PI * f)) / 2
}

// Surfvenster (PLAN.md 2.7): het middelste deel tussen elk laag- en hoogwater, bij daglicht.
export function vensters(ex: Extreem[], van: number, tot: number, breedte: number, licht: [number, number] | null) {
  const out: [number, number][] = []
  for (let i = 1; i < ex.length; i++) {
    const a = ex[i - 1], b = ex[i]
    if (b.t < van || a.t > tot) continue
    const d = b.t - a.t
    let s = a.t + d * (1 - breedte) / 2
    let e = b.t - d * (1 - breedte) / 2
    if (licht) { s = Math.max(s, licht[0]); e = Math.min(e, licht[1]) }
    if (e > s) out.push([s, e])
  }
  return out
}

// Zonsopgang en -ondergang (NOAA, vereenvoudigd), in minuten sinds 1970 UTC.
export function zon(lat: number, lon: number, dagUtc0: number): [number, number] | null {
  const rad = Math.PI / 180
  const d = new Date(dagUtc0 * 60000)
  const n = Math.floor((Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()) - Date.UTC(d.getUTCFullYear(), 0, 0)) / 864e5)
  const g = (2 * Math.PI / 365) * (n - 1)
  const eq = 229.18 * (0.000075 + 0.001868 * Math.cos(g) - 0.032077 * Math.sin(g) - 0.014615 * Math.cos(2 * g) - 0.040849 * Math.sin(2 * g))
  const decl = 0.006918 - 0.399912 * Math.cos(g) + 0.070257 * Math.sin(g) - 0.006758 * Math.cos(2 * g) + 0.000907 * Math.sin(2 * g)
  const cosH = (Math.cos(90.833 * rad) - Math.sin(lat * rad) * Math.sin(decl)) / (Math.cos(lat * rad) * Math.cos(decl))
  if (Math.abs(cosH) > 1) return null
  const H = Math.acos(cosH) / rad
  const mid = 720 - 4 * lon - eq
  const base = Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()) / 60000
  return [base + mid - 4 * H, base + mid + 4 * H]
}
