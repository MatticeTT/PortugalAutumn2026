// De nieuwe cirkels (score van de rekenchat, versie 2.1): links WIND (cyaan), rechts WAVE (blauw), elk 0-4.
// Rand alleen bij 3 of 4: groen = alle niveaus, oranje = niet voor beginners, rood = enkel ervaren.
// Een zwarte helft = te veel (te gevaarlijk); storm = zwarte achtergrond.
// De kaart leest per uur één teken per groep (pipeline/site/invoer.py, teken):
//   0 1 2 = cijfer; a b c = cijfer 0 1 2 en te veel; g o r = 3 met die rand; G O R = 4 met die rand;
//   - = geen voorspelling; ? = onzeker strand (geen score).
// Stille waters en storm: 0-4, of S T U V W = 0-4 met storm.
import type { Groep, Rand, StrandUur } from './score'

export interface Helft { cijfer: number | null; rand: Rand | null; teVeel: boolean; onzeker?: boolean }

const RANDNAAM: Record<string, Rand> = { g: 'groen', o: 'oranje', r: 'rood' }

export function leesTeken(t: string | undefined): Helft {
  if (!t || t === '-') return { cijfer: null, rand: null, teVeel: false }
  if (t === '?') return { cijfer: null, rand: null, teVeel: false, onzeker: true }
  if (t >= '0' && t <= '2') return { cijfer: Number(t), rand: null, teVeel: false }
  if (t >= 'a' && t <= 'c') return { cijfer: t.charCodeAt(0) - 97, rand: null, teVeel: true }
  const k = t.toLowerCase()
  if (k in RANDNAAM) return { cijfer: t === k ? 3 : 4, rand: RANDNAAM[k], teVeel: false }
  return { cijfer: null, rand: null, teVeel: false }
}

export function leesStil(t: string | undefined): { cijfer: number | null; storm: boolean } {
  if (!t || t === '-' || t === '?') return { cijfer: null, storm: false }
  const n = 'STUVW'.indexOf(t)
  return n >= 0 ? { cijfer: n, storm: true } : { cijfer: Number(t), storm: false }
}

export function uitGroep(g: Groep): Helft {
  return { cijfer: g.cijfer, rand: g.rand, teVeel: g.te_veel }
}

export function tekenVan(u: StrandUur): [string, string, string] {
  const t = (g: Groep) => g.cijfer >= 3 ? (g.cijfer === 3 ? g.rand![0] : g.rand![0].toUpperCase())
    : g.te_veel ? 'abc'[g.cijfer] : String(g.cijfer)
  return [t(u.golf), t(u.wind), (u.storm ? 'STUVW' : '01234')[u.stille_waters.cijfer]]
}

// Kleuren: vijf stappen van flets (0) naar fel (4).
export const CYAAN5 = ['#e3f7fa', '#a9e9f3', '#5fd0e4', '#16b3d0', '#007a96']
export const BLAUW5 = ['#e6ecfb', '#b4c8f4', '#7d9fec', '#3f6fe0', '#143aa6']
export const STIL5 = ['#eef0f1', '#d5dadd', '#b3bbc0', '#8a949c', '#5f6970']
export const RANDKLEUR: Record<Rand, string> = { groen: '#13a538', oranje: '#f08a00', rood: '#e0242f' }
export const RANDUITLEG: Record<Rand, string> = {
  groen: 'alle niveaus', oranje: 'niet meer voor beginners', rood: 'enkel voor ervaren',
}
export const BETEKENIS = ['niets', 'iets', 'potentieel', 'zekerheid', 'ideaal']
export const donkerCijfer = (n: number) => n <= 2

// Eén cirkel: links WIND, rechts WAVE. storm = zwarte achtergrond.
export function cirkel(wind: Helft, golf: Helft, size = 36, storm = false): ImageData {
  const c = document.createElement('canvas')
  const ratio = 2
  c.width = c.height = size * ratio
  const g = c.getContext('2d')!
  g.scale(ratio, ratio)
  const cx = size / 2, cy = size / 2
  const r = size / 2 - 4
  // achtergrond: storm zwart, anders een dunne donkere rand
  g.beginPath(); g.arc(cx, cy, r + 3.5, 0, Math.PI * 2)
  g.fillStyle = storm ? '#000' : 'rgba(20,32,43,0.45)'; g.fill()
  const onzeker = wind.onzeker || golf.onzeker
  const leeg = !onzeker && wind.cijfer === null && golf.cijfer === null
  const helft = (h: Helft, links: boolean, pal: string[]) => {
    g.beginPath(); g.moveTo(cx, cy)
    if (links) g.arc(cx, cy, r, Math.PI / 2, Math.PI * 1.5)
    else g.arc(cx, cy, r, -Math.PI / 2, Math.PI / 2)
    g.fillStyle = onzeker || leeg || h.cijfer === null ? '#c9cfd4' : h.teVeel ? '#111' : pal[h.cijfer]
    g.fill()
  }
  helft(wind, true, CYAAN5)
  helft(golf, false, BLAUW5)
  g.fillStyle = 'rgba(255,255,255,0.9)'; g.fillRect(cx - 0.5, cy - r, 1, 2 * r)
  // rand per helft bij 3 of 4
  const rand = (h: Helft, links: boolean) => {
    if (!h.rand || h.cijfer === null || h.cijfer < 3) return
    g.lineWidth = 3.4; g.strokeStyle = RANDKLEUR[h.rand]
    g.beginPath()
    if (links) g.arc(cx, cy, r + 1.2, Math.PI / 2, Math.PI * 1.5)
    else g.arc(cx, cy, r + 1.2, -Math.PI / 2, Math.PI / 2)
    g.stroke()
  }
  rand(wind, true); rand(golf, false)
  g.font = `700 ${Math.round(size * 0.36)}px system-ui, sans-serif`
  g.textAlign = 'center'; g.textBaseline = 'middle'
  if (onzeker || leeg) {
    g.fillStyle = '#4a545c'; g.fillText(onzeker ? '?' : '–', cx, cy + 1)
  } else {
    const cijfer = (h: Helft, x: number) => {
      if (h.cijfer === null) return
      g.fillStyle = h.teVeel ? '#fff' : donkerCijfer(h.cijfer) ? '#0d2530' : '#fff'
      g.fillText(String(h.cijfer), x, cy + 1)
    }
    cijfer(wind, cx - r / 2.1)
    cijfer(golf, cx + r / 2.1)
  }
  return g.getImageData(0, 0, c.width, c.height)
}

export function plaatjeUrl(img: ImageData): string {
  const c = document.createElement('canvas')
  c.width = img.width; c.height = img.height
  c.getContext('2d')!.putImageData(img, 0, 0)
  return c.toDataURL()
}

// Naam van een afbeelding op de kaart: w<teken>v<teken>s<0|1>
export const beeldNaam = (w: string, v: string, storm: boolean) => `c${w}${v}${storm ? 1 : 0}`
export function beeldUitNaam(naam: string): ImageData | null {
  const m = /^c(.)(.)([01])$/.exec(naam)
  if (!m) return null
  return cirkel(leesTeken(m[1]), leesTeken(m[2]), 36, m[3] === '1')
}
