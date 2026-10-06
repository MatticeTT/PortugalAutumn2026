// Eén kleur per cijfer: 1 niets (grijs), 2 te licht, 3 ideaal (groen), 4 sterk (oranje), 5 te moeilijk (rood).
export const KLEUR = ['#c3cad0', '#c4e6a8', '#1f9d55', '#f0932b', '#d0021b']
export const DONKERE_TEKST = (n: number) => n === 1 || n === 2 || n === 4
export const tekstKleur = (n: number) => (DONKERE_TEKST(n) ? '#14202b' : '#fff')

// Voor een groep stranden op de kaart: het interessantste cijfer (3, dan 4, 2, 5, 1).
export const RANG = [0, 1, 3, 5, 4, 2] // cijfer -> rang

export function bolletje(n: number, size = 30, groep = false): ImageData {
  const c = document.createElement('canvas')
  const ratio = 2
  c.width = c.height = size * ratio
  const g = c.getContext('2d')!
  g.scale(ratio, ratio)
  const cx = size / 2
  const r = size / 2 - 2
  if (groep) {
    g.beginPath(); g.arc(cx, cx, r + 1, 0, Math.PI * 2)
    g.fillStyle = 'rgba(255,255,255,0.9)'; g.fill()
  }
  g.beginPath(); g.arc(cx, cx, groep ? r - 2.5 : r, 0, Math.PI * 2)
  g.fillStyle = n ? KLEUR[n - 1] : '#e2e6e9'; g.fill()
  g.lineWidth = 1.5; g.strokeStyle = 'rgba(20,32,43,0.55)'; g.stroke()
  g.font = `700 ${Math.round(size * 0.5)}px system-ui, sans-serif`
  g.textAlign = 'center'; g.textBaseline = 'middle'
  g.fillStyle = n ? tekstKleur(n) : '#4a545c'
  g.fillText(n ? String(n) : '–', cx, cx + 1)
  return g.getImageData(0, 0, c.width, c.height)
}
