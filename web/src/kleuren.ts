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
  g.fillText(n ? String(n - 1) : '–', cx, cx + 1) // level 1–4 getoond als 0–3 (eigenaar)
  return g.getImageData(0, 0, c.width, c.height)
}

// WIND en WAVE (M5): een halve cirkel cyaan voor WIND, een halve blauw voor WAVE.
// Vijf stappen van flets (1) naar fel (5): cyaan voor WIND, blauw voor WAVE (PLAN.md 2.6).
// Vier levels (1 niets, 2 beginner, 3 sterk, 4 te sterk).
export const CYAAN = ['#d4f5fa', '#7ee0f0', '#16b3d0', '#007a96']
export const BLAUW = ['#dbe5fb', '#93b3f2', '#4f7fe6', '#143aa6']
export const LICHT = (s: number) => s <= 2 // donkere cijfers op een lichte helft

// rood: 1 = WIND-helft rood omkaderd (wind van land), 2 = WAVE-helft (golf komt niet aan), 3 = beide.
export function bolletjeWW(w: number, v: number, size = 44, letOp = false, rood = 0): ImageData {
  const c = document.createElement('canvas')
  const ratio = 2
  c.width = c.height = size * ratio
  const g = c.getContext('2d')!
  g.scale(ratio, ratio)
  const r = size / 2 - 3
  const cx = size / 2
  const cy = size / 2
  const leeg = w === 0 || v === 0
  const gevaar = w === 4 || v === 4
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
    // Levels 1–4 uit het rekenmodel worden getoond als 0–3 (eigenaar, 8 oktober 2026).
    g.fillStyle = LICHT(w) ? '#0d2530' : '#fff'; g.fillText(String(w - 1), cx - r / 2.1, cy + 1)
    g.fillStyle = LICHT(v) ? '#0d2530' : '#fff'; g.fillText(String(v - 1), cx + r / 2.1, cy + 1)
  } else {
    g.fillStyle = '#4a545c'; g.fillText('–', cx, cy + 1)
  }
  // Rood kader rond de helft met de verkeerde richting: links WIND, rechts WAVE.
  g.lineWidth = 3.2; g.strokeStyle = '#e0242f'
  if (rood & 1) { g.beginPath(); g.arc(cx, cy, r + 0.6, Math.PI / 2, Math.PI * 1.5); g.stroke() }
  if (rood & 2) { g.beginPath(); g.arc(cx, cy, r + 0.6, -Math.PI / 2, Math.PI / 2); g.stroke() }
  if (letOp) {
    // WIND 2 met aflandige wind: te licht om te kiten, verkeerde richting.
    const br = size * 0.17
    g.beginPath(); g.arc(br + 1, br + 1, br, 0, Math.PI * 2)
    g.fillStyle = '#fab219'; g.fill(); g.lineWidth = 1; g.strokeStyle = '#2b1d00'; g.stroke()
    g.fillStyle = '#2b1d00'; g.font = `800 ${Math.round(br * 1.5)}px system-ui, sans-serif`
    g.fillText('!', br + 1, br + 1.5)
  }
  return g.getImageData(0, 0, c.width, c.height)
}

// Dagplan op de kaart: goed (groen, vinkje), mogelijk (geel, tilde), niet (klein grijs bolletje).
export const PLAN_KLEUR = ['#c3cad0', '#fab219', '#0a8a0a']
export function bolletjePlan(n: number, size = 28, groep = false): ImageData {
  const c = document.createElement('canvas')
  const ratio = 2
  c.width = c.height = size * ratio
  const g = c.getContext('2d')!
  g.scale(ratio, ratio)
  const cx = size / 2
  const r = n === 0 ? size / 5 : size / 2 - 2
  if (groep && n > 0) {
    g.beginPath(); g.arc(cx, cx, r + 1, 0, Math.PI * 2)
    g.fillStyle = 'rgba(255,255,255,0.9)'; g.fill()
  }
  g.beginPath(); g.arc(cx, cx, groep && n > 0 ? r - 2.5 : r, 0, Math.PI * 2)
  g.fillStyle = PLAN_KLEUR[n]; g.fill()
  g.lineWidth = 1.2; g.strokeStyle = 'rgba(13,28,35,0.55)'; g.stroke()
  if (n > 0) {
    g.font = `800 ${Math.round(size * 0.5)}px system-ui, sans-serif`
    g.textAlign = 'center'; g.textBaseline = 'middle'
    g.fillStyle = n === 2 ? '#fff' : '#2b1d00'
    g.fillText(n === 2 ? '✓' : '~', cx, cx + 1)
  }
  return g.getImageData(0, 0, c.width, c.height)
}

export function bolletjeUrl(w: number, v: number, size = 34, letOp = false): string {
  const img = bolletjeWW(w, v, size, letOp)
  const c = document.createElement('canvas')
  c.width = img.width; c.height = img.height
  c.getContext('2d')!.putImageData(img, 0, 0)
  return c.toDataURL()
}

export function plaatje(img: ImageData): string {
  const c = document.createElement('canvas')
  c.width = img.width; c.height = img.height
  c.getContext('2d')!.putImageData(img, 0, 0)
  return c.toDataURL()
}
