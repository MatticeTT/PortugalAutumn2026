// Kompascirkel in de fiche (zoals Surfline en Windy): hoe het strand ligt, vanwaar deining open zee heeft, en
// vanwaar deining en wind op dit moment komen. Pijlen wijzen naar het strand (midden), vanuit de richting waar ze
// vandaan komen.

import { kompas } from './spots'

const R = 88 // buitenrand
const xy = (deg: number, r: number) => {
  const a = (deg * Math.PI) / 180
  return [+(Math.sin(a) * r).toFixed(1), +(-Math.cos(a) * r).toFixed(1)]
}

/** Ringstuk tussen twee richtingen (met de klok mee van `van` tot `tot`). */
function sector(van: number, tot: number, r1: number, r2: number) {
  const span = (((tot - van) % 360) + 360) % 360 || 360
  const groot = span > 180 ? 1 : 0
  const [a, b] = xy(van, r2), [c, d] = xy(van + span, r2), [e, f] = xy(van + span, r1), [g, h] = xy(van, r1)
  return `M${a} ${b}A${r2} ${r2} 0 ${groot} 1 ${c} ${d}L${e} ${f}A${r1} ${r1} 0 ${groot} 0 ${g} ${h}Z`
}

/** Pijl van de rand naar het midden; `dik` in px. */
function pijl(deg: number, kleur: string, dik: number, van = R - 4, tot = 22, opzij = 0) {
  // `opzij`: evenwijdig verschuiven (px), zodat twee pijlen uit bijna dezelfde richting naast elkaar liggen.
  const [ox, oy] = xy(deg + 90, opzij)
  const p = (d: number, r: number) => { const [x, y] = xy(d, r); return `${+(x + ox).toFixed(1)} ${+(y + oy).toFixed(1)}` }
  // Pijlpunt: 9 px breed aan elke kant, 12 px lang.
  const hoek = (Math.atan2(9, tot + 12) * 180) / Math.PI
  return `<path d="M${p(deg, van)}L${p(deg, tot + 8)}" stroke="${kleur}" stroke-width="${dik}" stroke-linecap="round"/>
    <path d="M${p(deg, tot)}L${p(deg + hoek, Math.hypot(tot + 12, 9))}L${p(deg - hoek, Math.hypot(tot + 12, 9))}Z" fill="${kleur}"/>`
}

export const windKleur = (rel: number) => (rel <= 45 ? '#16a34a' : rel < 135 ? '#f08a00' : '#e5484d')
export const windSoort = (rel: number) => (rel <= 45 ? 'aflandig' : rel < 135 ? 'van opzij' : 'aanlandig')
const DEINING = '#2f7cf6'

export interface KompasInvoer {
  richting: number // strand kijkt naar (graden)
  venster: number[][] // open zee: [van, tot] met de klok mee
  deining: [number, number, number] | null // m, vandaan, s
  breker: number | null
  wind: number[] | null // kn, rel, stoten, vandaan
}

export function kompasSvg(k: KompasInvoer) {
  const ticks = Array.from({ length: 36 }, (_, i) => {
    const d = i * 10
    const [a, b] = xy(d, R), [c, e] = xy(d, R - (d % 90 === 0 ? 9 : d % 30 === 0 ? 6 : 3))
    return `<line x1="${a}" y1="${b}" x2="${c}" y2="${e}" stroke="var(--zacht)" stroke-width="${d % 30 ? 1 : 1.5}" opacity=".7"/>`
  }).join('')
  const letters = [['N', 0], ['O', 90], ['Z', 180], ['W', 270]].map(([t, d]) => {
    const [x, y] = xy(d as number, R - 19)
    return `<text x="${x}" y="${y}" dy=".35em" text-anchor="middle" font-size="12" font-weight="700" fill="var(--zacht)">${t}</text>`
  }).join('')
  // Land: de helft achter het strand; de kustlijn dwars op de richting van het strand.
  const land = sector(k.richting + 90, k.richting + 270, 0, R - 26)
  const [k1, k2] = xy(k.richting + 90, R - 26), [k3, k4] = xy(k.richting - 90, R - 26)
  const zee = k.venster.map(([van, tot]) => `<path d="${sector(van, tot, R - 26, R)}" fill="${DEINING}" opacity=".16"/>`).join('')
  const [sx, sy] = xy(k.richting, 30)
  const metGolf = !!k.deining && (k.breker ?? 0) >= 0.1
  const dichtbij = metGolf && !!k.wind && Math.abs(((k.deining![1] - k.wind[3] + 540) % 360) - 180) < 25
  const golf = metGolf ? pijl(k.deining![1], DEINING, 6, R - 4, 22, dichtbij ? -7 : 0) : ''
  const wind = k.wind ? pijl(k.wind[3], windKleur(k.wind[1]), 4, R - 4, 30, dichtbij ? 7 : 0) : ''
  return `<svg class="kompas" viewBox="-${R + 2} -${R + 2} ${2 * R + 4} ${2 * R + 4}" role="img"
      aria-label="Kompas: strand kijkt naar het ${kompas(k.richting)}${k.deining ? `, deining uit het ${kompas(k.deining[1])}` : ''}${k.wind ? `, wind uit het ${kompas(k.wind[3])}` : ''}">
    <circle r="${R}" fill="var(--zacht-vlak)"/>
    ${zee}
    <path d="${land}" fill="#c9a96e" opacity=".28"/>
    <line x1="${k1}" y1="${k2}" x2="${k3}" y2="${k4}" stroke="#c9a96e" stroke-width="3" stroke-linecap="round"/>
    <text x="${sx}" y="${sy}" dy=".35em" text-anchor="middle" font-size="10" fill="var(--zacht)" transform="rotate(${((k.richting + 90) % 180) - 90} ${sx} ${sy})">zee</text>
    ${ticks}${letters}${golf}${wind}
    <circle r="4" fill="var(--tekst)"/>
  </svg>`
}

/** Uitleg onder het kompas: kleur en waarde per pijl. */
export function kompasLegende(k: KompasInvoer) {
  const uit: string[] = []
  if (k.deining && (k.breker ?? 0) >= 0.1)
    uit.push(`<span><i style="background:${DEINING}"></i>Deining ${k.deining[0].toLocaleString('nl-NL')} m · ${k.deining[2]} s uit ${k.deining[1]}° (${kompas(k.deining[1])})</span>`)
  if (k.wind)
    uit.push(`<span><i style="background:${windKleur(k.wind[1])}"></i>Wind ${k.wind[0]} kn uit ${k.wind[3]}° · ${windSoort(k.wind[1])}</span>`)
  if (k.venster.length) uit.push(`<span><i style="background:${DEINING};opacity:.3"></i>Open zee: hier kan deining vandaan komen</span>`)
  return `<div class="legende">${uit.join('')}</div>`
}
