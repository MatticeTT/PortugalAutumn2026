// Vijf stappen van flets (1) naar fel (5): cyaan voor WIND, blauw voor WAVE (PLAN.md 2.6).
export const CYAAN = ['#d4f5fa', '#93e6f3', '#3fcde6', '#0fa9c9', '#007a96']
export const BLAUW = ['#dbe5fb', '#a3bdf4', '#6693ec', '#2f63da', '#143aa6']
export const LICHT = (s: number) => s <= 2 // donkere cijfers op een lichte helft

export function bolletje(w: number, v: number, size = 44): ImageData {
  const c = document.createElement('canvas')
  const ratio = 2
  c.width = c.height = size * ratio
  const g = c.getContext('2d')!
  g.scale(ratio, ratio)
  const r = size / 2 - 3
  const cx = size / 2
  const cy = size / 2
  const leeg = w === 0 || v === 0
  const gevaar = w === 5 || v === 5
  g.beginPath(); g.arc(cx, cy, r + 2, 0, Math.PI * 2)
  g.fillStyle = gevaar ? '#d0021b' : 'rgba(20,32,43,0.55)'; g.fill()
  g.beginPath(); g.moveTo(cx, cy); g.arc(cx, cy, r, Math.PI / 2, Math.PI * 1.5)
  g.fillStyle = leeg ? '#c9cfd4' : CYAAN[w - 1]; g.fill()
  g.beginPath(); g.moveTo(cx, cy); g.arc(cx, cy, r, -Math.PI / 2, Math.PI / 2)
  g.fillStyle = leeg ? '#aeb5bb' : BLAUW[v - 1]; g.fill()
  g.fillStyle = 'rgba(255,255,255,0.9)'; g.fillRect(cx - 0.5, cy - r, 1, 2 * r)
  g.font = `700 ${Math.round(size * 0.36)}px system-ui, sans-serif`
  g.textAlign = 'center'; g.textBaseline = 'middle'
  if (!leeg) {
    g.fillStyle = LICHT(w) ? '#0d2530' : '#fff'; g.fillText(String(w), cx - r / 2.1, cy + 1)
    g.fillStyle = LICHT(v) ? '#0d2530' : '#fff'; g.fillText(String(v), cx + r / 2.1, cy + 1)
  } else {
    g.fillStyle = '#4a545c'; g.fillText('–', cx, cy + 1)
  }
  return g.getImageData(0, 0, c.width, c.height)
}

export function bolletjeUrl(w: number, v: number, size = 34): string {
  const img = bolletje(w, v, size)
  const c = document.createElement('canvas')
  c.width = img.width; c.height = img.height
  c.getContext('2d')!.putImageData(img, 0, 0)
  return c.toDataURL()
}
