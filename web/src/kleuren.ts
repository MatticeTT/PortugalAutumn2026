// Eén kleur per cijfer, zoals de Watersportwijzer: 1 niets (grijs), 2 te licht (blauw),
// 3 ideaal (groen), 4 sterk (oranjegeel), 5 te moeilijk (rood).
export const KLEUR = ['#dfe7e9', '#2a78d6', '#0a8a0a', '#fab219', '#d03b3b']
const TEKST = ['#40545d', '#ffffff', '#ffffff', '#2b1d00', '#ffffff']
export const tekstKleur = (n: number) => TEKST[n - 1] ?? '#40545d'

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
  g.fillStyle = n ? KLEUR[n - 1] : '#eef1f2'; g.fill()
  g.lineWidth = 1.5; g.strokeStyle = 'rgba(13,28,35,0.55)'; g.stroke()
  g.font = `700 ${Math.round(size * 0.5)}px system-ui, sans-serif`
  g.textAlign = 'center'; g.textBaseline = 'middle'
  g.fillStyle = n ? tekstKleur(n) : '#6f838b'
  g.fillText(n ? String(n) : '–', cx, cx + 1)
  return g.getImageData(0, 0, c.width, c.height)
}
