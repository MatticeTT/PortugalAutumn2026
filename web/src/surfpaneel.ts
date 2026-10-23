// Paneel "Surfen" op de kaart: welke planken je hebt (die tellen mee op de kaart en in de planning) en je gewicht.
// Bewaard in deze browser.

import { PLANKEN } from './spots'

export interface SurfKeuze { planken: string[]; gewicht: number | null }
const SLEUTEL = 'surf-v1'

export function leesSurf(): SurfKeuze {
  try {
    const s = JSON.parse(localStorage.getItem(SLEUTEL) ?? 'null')
    if (s && Array.isArray(s.planken)) return { planken: s.planken.filter((p: string) => p in PLANKEN), gewicht: s.gewicht ?? null }
  } catch { /* niets bewaard */ }
  return { planken: Object.keys(PLANKEN), gewicht: null }
}

function bewaar(s: SurfKeuze) {
  try { localStorage.setItem(SLEUTEL, JSON.stringify(s)) } catch { /* niet bewaard */ }
}

export function surfPaneel(knop: HTMLElement, paneel: HTMLElement, gewijzigd: (s: SurfKeuze) => void) {
  const teken = () => {
    const s = leesSurf()
    paneel.innerHTML = `<h2>Surfen</h2>
      <fieldset><legend>Mijn planken</legend>
        ${Object.entries(PLANKEN).map(([k, n]) => `<label><input type="checkbox" value="${k}" ${s.planken.includes(k) ? 'checked' : ''}> ${n}</label>`).join('')}
        <p class="klein">De kaart en de planning tonen waar en wanneer deze planken goed zijn.</p>
      </fieldset>
      <fieldset><legend>Gewicht</legend>
        <label><input type="number" name="gewicht" min="20" max="200" inputmode="numeric" value="${s.gewicht ?? ''}"> kg</label>
      </fieldset>`
  }
  const lees = () => {
    const s: SurfKeuze = {
      planken: [...paneel.querySelectorAll<HTMLInputElement>('input[type=checkbox]:checked')].map((x) => x.value),
      gewicht: Number(paneel.querySelector<HTMLInputElement>('[name=gewicht]')!.value) || null,
    }
    if (!s.planken.length) s.planken = Object.keys(PLANKEN)
    bewaar(s)
    knop.textContent = s.planken.length === Object.keys(PLANKEN).length ? 'Surfen' : `Surfen · ${s.planken.map((p) => PLANKEN[p]).join(', ')}`
    gewijzigd(s)
  }
  const s = leesSurf()
  knop.textContent = s.planken.length === Object.keys(PLANKEN).length ? 'Surfen' : `Surfen · ${s.planken.map((p) => PLANKEN[p]).join(', ')}`
  knop.addEventListener('click', () => {
    const open = paneel.hidden
    if (open) teken()
    paneel.hidden = !open
    knop.setAttribute('aria-expanded', String(open))
  })
  paneel.addEventListener('change', lees)
}
