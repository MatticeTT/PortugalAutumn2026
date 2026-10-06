export type Mode = 'wg' | 'fijn'

export interface Index {
  gemaakt: string
  opgehaald: Record<string, string>
  tijd: string[] // UTC, "YYYY-MM-DDTHH:MM"
  standen: Record<Mode, { naam: string; bron: string }>
  labels: string[]
  notas: string[]
  teksten: string[]
  ipma: { area: string; level: string; start: string; end: string }[]
  regels: any
  standaard?: Mode
  nauwkeurigheid?: any
}

export interface KaartStrand {
  id: string
  n: string
  x: number
  y: number
  wg?: string
  fijn?: string
}

// [WIND, WAVE, label, [nota's], [redenen], Hb, [laag, hoog], windsurf, waarschuwing, windklasse]
export type ScoreRij = [number, number, number, number[], number[], number, [number, number], number | null, number | null, string | null]

export interface StandData {
  bron: string
  wind: (number | null)[]
  vlagen: (number | null)[]
  windrichting: (number | null)[]
  score: (ScoreRij | null)[]
  [k: string]: any
}

export interface Detail {
  id: string
  naam: string
  lat: number
  lon: number
  kijkrichting: number
  district: string
  onzeker: boolean
  redenen_onzeker: string[]
  venster: [number, number][]
  getij: { a: string; b: string; w: number; nauwkeurigheid: string; nota: string | null } | null
  standen: Record<Mode, StandData>
}

export interface Getij {
  stations: Record<string, { naam: string; lat: number; lon: number; e: [number, number, number][] }>
}
