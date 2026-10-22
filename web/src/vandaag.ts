// Startscherm "Waar kan ik surfen?": per dag de goede spots, beste eerst; buren met dezelfde richting samen.

import type { Profiel } from './profiel'
import {
  besteOpDag, dagNaam, dagSleutel, esc, hemelsbreed, PLANKEN, rond, uur, vakkenOpDag, woordScore, type SpotIndex,
} from './spots'

export interface VandaagOpties {
  data: SpotIndex | null
  planken: string[]
  profiel: Profiel
  dag: string
  kiesDag: (dag: string) => void
  open: (id: number, dag: string) => void
}

export function toonVandaag(box: HTMLElement, o: VandaagOpties) {
  const { data, planken, profiel, dag } = o
  if (!data) {
    box.innerHTML = `<div class="v-kop"><h1>Waar kan ik surfen?</h1><p class="zacht">De voorspelling wordt geladen…</p></div>`
    return
  }
  // Dagen: vandaag tot het einde van de voorspelling.
  const dagen: Date[] = []
  const nu = new Date()
  for (let i = 0; i < 10; i++) dagen.push(new Date(nu.getFullYear(), nu.getMonth(), nu.getDate() + i, 12))
  const laatste = Math.max(...data.spots.flatMap((s) => Object.values(s.tijdvakken).flat().map((v) => Date.parse(v[1]))), 0)
  const zichtbaar = dagen.filter((d) => d.getTime() - 12 * 3600e3 <= laatste)

  // Spots met een goede sessie op deze dag; per groep (buurstranden) alleen de beste.
  const km = (s: { lat: number; lon: number }) => (profiel.verblijf ? hemelsbreed(profiel.verblijf, s) : null)
  // Reistijd: nog geen routeplanner, dus geen filter; de dichtstbijzijnde spots komen bij gelijke score eerst.
  const goed = data.spots.filter((s) => besteOpDag(s, dag, planken) > 0)
  const perGroep = new Map<number, typeof goed>()
  for (const s of goed) perGroep.set(s.groep, [...(perGroep.get(s.groep) ?? []), s])
  const kaarten = [...perGroep.values()].map((g) => {
    g.sort((a, b) => besteOpDag(b, dag, planken) - besteOpDag(a, dag, planken) || (km(a) ?? 0) - (km(b) ?? 0))
    return { s: g[0], andere: g.length - 1, score: besteOpDag(g[0], dag, planken) }
  }).sort((a, b) => rond(b.score) - rond(a.score) || (km(a.s) ?? 0) - (km(b.s) ?? 0) || b.score - a.score)

  const waar = profiel.verblijf
    ? `Vanuit ${esc(profiel.verblijf.naam)} · dichtstbij eerst`
    : 'Vul je verblijfplaats in bij Profiel om de dichtstbijzijnde spots eerst te zien'
  const plankTekst = planken.length === Object.keys(PLANKEN).length ? 'alle planken' : planken.map((p) => PLANKEN[p]).join(', ')

  box.innerHTML = `
    <div class="v-kop">
      <div class="zacht">${waar}</div>
      <h1>Waar kan ik surfen?</h1>
    </div>
    <div class="v-dagen" role="tablist">${zichtbaar.map((d) => {
      const k = dagSleutel(d)
      return `<button role="tab" aria-selected="${k === dag}" data-dag="${k}" class="${k === dag ? 'aan' : ''}">${dagNaam(d)}</button>`
    }).join('')}</div>
    <div class="v-lijst">
      ${kaarten.length ? kaarten.map(({ s, andere, score }) => {
        const [[plank, vak], ...rest] = vakkenOpDag(s, dag, planken)
        const ook = [...new Set(rest.filter(([, v]) => rond(v[2]) >= 4).map(([p]) => PLANKEN[p]))].filter((p) => p !== PLANKEN[plank])
        const k = km(s)
        return `<button class="v-kaart" data-id="${s.id}">
          <span class="cijfer c${rond(score)}"><b>${rond(score)}</b><small>${woordScore(score)}</small></span>
          <span class="v-tekst">
            <span class="v-naam">${esc(s.naam)}</span>
            ${k !== null ? `<span class="zacht">ongeveer ${Math.round(k)} km in rechte lijn</span>` : ''}
            <span class="v-ja"><b>Ja, ga surfen</b> van <b>${uur(vak[0])} tot ${uur(vak[1])}</b></span>
            <span class="v-chips"><span>${PLANKEN[plank]}</span>${ook.slice(0, 2).map((p) => `<span>ook ${p}</span>`).join('')}</span>
            ${andere ? `<span class="zacht">+ ${andere} ${andere === 1 ? 'strand' : 'stranden'} hiernaast ook goed</span>` : ''}
          </span>
        </button>`
      }).join('') : `<div class="v-leeg"><b>${dagNaam(new Date(dag + 'T12:00'), true)}: nergens goed</b><br>
        Geen spot haalt minstens ${data.min_uren} uur na elkaar een 4 of 5 met ${plankTekst}. Kies een andere dag hierboven.</div>`}
    </div>
    <p class="zacht v-voet">Met ${plankTekst} (aan te passen bij Profiel). Goed = minstens ${data.min_uren} uur na elkaar een 4 of 5.
      Voorspelling van ${new Date(data.run).toLocaleString('nl-NL', { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}.</p>`

  box.querySelectorAll<HTMLButtonElement>('.v-dagen button').forEach((b) => b.addEventListener('click', () => o.kiesDag(b.dataset.dag!)))
  box.querySelectorAll<HTMLButtonElement>('.v-kaart').forEach((b) => b.addEventListener('click', () => o.open(Number(b.dataset.id), dag)))
}
