export interface Sport {
  id: string
  naam: string
  groep: 'A' | 'B' | 'C' | 'D'
  [k: string]: any // grenzen, zie pipeline/sport/sporten.yaml
}

export interface Index {
  gemaakt: string
  opgehaald: Record<string, string>
  tijd: string[] // UTC, "YYYY-MM-DDTHH:MM"
  bron: string
  sporten: Sport[]
  groepen: Record<string, string>
  schaal: string[]
  ipma: { area: string; level: string; start: string; end: string }[]
  nauwkeurigheid?: any
  // WIND en WAVE (M5)
  labels: string[]
  notas: string[]
  teksten: string[]
  regels: any
  activiteiten: Record<string, string> // surf, wind, windgolf, plat -> naam
}

export interface KaartStrand {
  id: string
  n: string
  x: number
  y: number
}

export interface Detail {
  id: string
  naam: string
  lat: number
  lon: number
  kust: number // kustrichting
  venster: [number, number][] // swell-venster
  district: string
  getij: { a: string; b: string; w: number; nauwkeurigheid: string; nota: string | null } | null
  wind: (number | null)[]
  vlagen: (number | null)[]
  windrichting: (number | null)[]
  uitkomst: string // per uur: W te wild, G golfsurfen, O windsurfen op golven, S windsurfen, R stille waters, - geen
  straf: string // per uur: strafpunten van de uitkomst (0 ideaal, 1 goed, 2+ kan)
  WAVE: string // per uur level 1–4 (0 = geen)
  WIND: string
  licht: string // per uur 1 = daglicht
  ipma: string[]
  [k: string]: any // de golfreeksen (wave_height, swell_wave_period, ...)
}

export interface Getij {
  stations: Record<string, { naam: string; lat: number; lon: number; e: [number, number, number][] }>
}

// WIND en WAVE (M5): [WIND, WAVE, label, [nota's], [redenen], Hb, [laag, hoog], windsurf, waarschuwing, windklasse]
export type ScoreRij = [number, number, number, number[], number[], number, [number, number], number | null, number | null, string | null, boolean]
