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
  redenen: Record<string, string>
  ipma: { area: string; level: string; start: string; end: string }[]
  nauwkeurigheid?: any
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
  kijkrichting: number
  district: string
  onzeker: boolean
  redenen_onzeker: string[]
  getij: { a: string; b: string; w: number; nauwkeurigheid: string; nota: string | null } | null
  K: number
  K_bron: string
  BESTTIJ: string | null
  DROOG: boolean
  LUWTE: [number, number] | null
  wind: (number | null)[]
  vlagen: (number | null)[]
  windrichting: (number | null)[]
  piekperiode: (number | null)[]
  GOLF: (number | null)[]
  RUW: (number | null)[]
  tij: (number | null)[] // 0 laag, 1 opkomend, 2 hoog, 3 afgaand
  ipma: string[]
  cijfers: Record<string, string> // één teken per uur, 0 = geen cijfer
  redenen: Record<string, string> // één teken per uur, 0 = geen reden
  [k: string]: any // de golfreeksen (wave_height, swell_wave_period, ...)
}

export interface Getij {
  stations: Record<string, { naam: string; lat: number; lon: number; e: [number, number, number][] }>
}
