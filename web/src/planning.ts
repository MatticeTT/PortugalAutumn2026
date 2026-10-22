// Planning: per dag (tot 10 dagen vooruit) waar en wanneer je kan surfen met je planken.

import { hemelsbreed, type Profiel } from './profiel'
import { PLANKEN, type SpotIndex, type Vak } from './spots'

const dagFmt = new Intl.DateTimeFormat('nl-NL', { weekday: 'long', day: 'numeric', month: 'long' })
const uurFmt = new Intl.DateTimeFormat('nl-NL', { hour: '2-digit', minute: '2-digit' })
const dagSleutel = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
const rond = (x: number) => Math.floor(x + 0.5)

export interface Keuze { id: number; van: string }

export function toonPlanning(box: HTMLElement, data: SpotIndex | null, planken: Set<string>, profiel: Profiel, kies: (k: Keuze) => void) {
  if (!data) {
    box.innerHTML = '<h2>Planning</h2><p class="zacht">Nog geen scores geladen.</p>'
    return
  }
  // dag -> rijen
  const dagen = new Map<string, { id: number; naam: string; plank: string; van: string; tot: string; score: number; km: number | null }[]>()
  for (const s of data.spots) {
    const km = profiel.verblijf ? hemelsbreed(profiel.verblijf, s) : null
    for (const p of planken) {
      for (const [van, tot, g] of (s.tijdvakken[p] ?? []) as Vak[]) {
        const d = dagSleutel(new Date(van))
        if (!dagen.has(d)) dagen.set(d, [])
        dagen.get(d)!.push({ id: s.id, naam: s.naam, plank: p, van, tot, score: g, km })
      }
    }
  }
  const delen: string[] = [`<h2>Planning</h2><p class="zacht">Spots waar je plank minstens ${data.min_uren} uur na elkaar een 4 of 5 haalt.
    Planken: ${[...planken].map((p) => PLANKEN[p]).join(', ') || 'geen gekozen'}.${profiel.verblijf ? ` Afstand in rechte lijn vanaf ${profiel.verblijf.naam}.` : ''}</p>`]
  const vandaag = dagSleutel(new Date())
  for (const d of [...dagen.keys()].sort()) {
    if (d < vandaag) continue
    const rijen = dagen.get(d)!.sort((a, b) => b.score - a.score || (a.km ?? 0) - (b.km ?? 0))
    delen.push(`<h3>${dagFmt.format(new Date(rijen[0].van))}</h3><ul class="plan">${rijen.map((r) =>
      `<li><button data-id="${r.id}" data-van="${r.van}"><b class="cijfer">${rond(r.score)}</b>
        <span><b>${r.naam}</b> · ${PLANKEN[r.plank]}<br><span class="zacht">${uurFmt.format(new Date(r.van))}–${uurFmt.format(new Date(r.tot))}${r.km !== null ? ` · ${Math.round(r.km)} km` : ''}</span></span></button></li>`).join('')}</ul>`)
  }
  if (delen.length === 1) delen.push('<p>Geen goede sessies gevonden met deze planken.</p>')
  delen.push(`<p class="zacht">Scores van run ${data.run.replace('T', ' ').replace(':00Z', ' UTC')}. Golven: Copernicus Marine · wind: ECMWF · getij: EOT20.</p>`)
  box.innerHTML = delen.join('')
  box.querySelectorAll<HTMLButtonElement>('button[data-id]').forEach((b) =>
    b.addEventListener('click', () => kies({ id: Number(b.dataset.id), van: b.dataset.van! })))
}
