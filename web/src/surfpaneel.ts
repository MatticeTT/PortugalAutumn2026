// Je planken (kies je in Planning, stap 3): die tellen mee op de kaart en in de planning. Bewaard in deze browser.

import { PLANKEN } from './spots'

export interface SurfKeuze { planken: string[]; gewicht: number | null }
const SLEUTEL = 'surf-v1'

export function leesSurf(): SurfKeuze {
  try {
    const s = JSON.parse(localStorage.getItem(SLEUTEL) ?? 'null')
    if (s && Array.isArray(s.planken)) {
      const planken = s.planken.filter((p: string) => p in PLANKEN)
      return { planken: planken.length ? planken : Object.keys(PLANKEN), gewicht: s.gewicht ?? null }
    }
  } catch { /* niets bewaard */ }
  return { planken: Object.keys(PLANKEN), gewicht: null }
}

export function bewaarSurf(s: SurfKeuze) {
  try { localStorage.setItem(SLEUTEL, JSON.stringify(s)) } catch { /* niet bewaard */ }
}
