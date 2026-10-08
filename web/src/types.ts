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
  redenen: Record<string, string> // code -> tekst
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
  d?: string // district of provincie
  l?: string // land, zonder = Portugal (es, fr, be)
  x: number
  y: number
}

export interface Detail {
  id: string
  land?: string // zonder = Portugal
  nota?: string // vaste nota bij een land (België: getijstroom)
  stroom?: (number | null)[] // stroming (kn), per uur
  waarschuwing?: string // per uur het hoogste niveau van MeteoAlarm (0 geen, 1 geel, 2 oranje, 3 rood)
  waarschuwingen?: { niveau: number; soort: string; van: string; tot: string }[]
  stroom_naar?: (number | null)[] // richting waarheen de stroom gaat (graden)
  stroom_pct?: (number | null)[] // golf zoveel % hoger (+) of lager (-) door de stroming
  naam: string
  lat: number
  lon: number
  kust: number // kustrichting
  venster: [number, number][] // swell-venster(s) uit de stranddata
  district: string
  getij: { a: string; b: string; w: number; nauwkeurigheid: string; nota: string | null } | null
  controle: { blokkerend: string[]; nakijken: string[]; aandeel16?: number[] }
  piekperiode: boolean
  wind: (number | null)[]
  vlagen: (number | null)[]
  windrichting: (number | null)[]
  // laag 1 en 2
  WAVE: string // per uur level 1–4 (0 = geen)
  WIND: string
  zee_h: (number | null)[] // krachtigste deining op zee
  zee_t: (number | null)[]
  zee_r: (number | null)[]
  E_zee: (number | null)[] // kJ, 1,96 × hoogte² × periode² van die deining
  // laag 3
  WAVE_strand: string
  bereikt: (number | null)[]
  E: (number | null)[]
  periode: (number | null)[]
  H: (number | null)[]
  windhoek: (number | null)[]
  tij: (number | null)[]
  tijgewicht: (number | null)[]
  verval: (number | null)[]
  // laag 4
  scores: (number[] | null)[] // golfsurfen, windsurfen op golven, windsurfen, stille waters, te wild
  conclusie: (string | null)[]
  letter: string // per uur: G O S R ideaal, g o s r andere, W te wild, "." niet berekend, "-" geen data
  rood: string // per uur: 0 niets, 1 wind van land, 2 golf komt niet aan, 3 beide (rood kader)
  licht: string // per uur 1 = daglicht
  ipma: string[]
}

export interface Getij {
  stations: Record<string, { naam: string; lat: number; lon: number; e: [number, number, number][] }>
}

// WIND en WAVE (M5): [WIND, WAVE, label, [nota's], [redenen], Hb, [laag, hoog], windsurf, waarschuwing, windklasse]
export type ScoreRij = [number, number, number, number[], number[], number, [number, number], number | null, number | null, string | null, boolean]
