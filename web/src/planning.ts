// Planning (zoals in de eerste versie): bovenaan je verblijf en hoe lang je wil rijden, dan per dag de beste spot
// met een foto, de uren en de rijtijd, en de andere goede spots eronder.

import { kleur } from './fiche'
import { besteOpDag, dagSleutel, een, esc, komma, PLANKEN, uur, vakkenOpDag, type SpotIndex, type SpotKort } from './spots'
import { rijTekst, type Verblijf } from './verblijf'

const dagFmt = new Intl.DateTimeFormat('nl-NL', { weekday: 'short' })
const maandFmt = new Intl.DateTimeFormat('nl-NL', { month: 'short' })

export interface PlanningOpties {
  data: SpotIndex | null
  planken: string[]
  verblijf: Verblijf | null
  rijtijd: (id: number) => number | null | undefined
  dagen: string[]
  wijzigVerblijf: () => void
  open: (s: SpotKort, dag: string) => void
}

export function toonPlanning(box: HTMLElement, o: PlanningOpties) {
  const v = o.verblijf
  const plankTekst = o.planken.length === Object.keys(PLANKEN).length ? 'alle planken' : o.planken.map((p) => PLANKEN[p]).join(', ')
  const kop = `<div class="instellingen">
    <div class="planvan"><span class="huis" aria-hidden="true"></span>
      <span class="waar"><b>${v ? esc(v.naam.split(',')[0]) : 'Geen verblijf gekozen'}</b><small>${v ? `max ${rijTekst(v.max)} rijden` : 'Kies je verblijf om de reistijd mee te tellen'}</small></span>
      <button class="wijzig" type="button">${v ? 'Wijzig' : 'Kies'}</button></div>
    <p class="uitleg">Per dag de beste spot waar ${plankTekst} minstens ${o.data?.min_uren ?? 3} uur na elkaar een 4 of 5 halen${v ? ', binnen je rijtijd' : ''}. Je planken kies je met de knop Surfen op de kaart.</p>
  </div>`
  if (!o.data) {
    box.innerHTML = kop + '<p class="dagniets">De voorspelling wordt geladen…</p>'
    box.querySelector('.wijzig')!.addEventListener('click', o.wijzigVerblijf)
    return
  }
  const bereikbaar = (s: SpotKort) => {
    if (!v) return true
    const m = o.rijtijd(s.id)
    return m != null && m <= v.max
  }
  const dagen = o.dagen.map((dag) => {
    const goed = o.data!.spots.filter((s) => bereikbaar(s) && besteOpDag(s, dag, o.planken) > 0)
      .map((s) => ({ s, best: besteOpDag(s, dag, o.planken), vak: vakkenOpDag(s, dag, o.planken)[0] }))
    // Per groep buurstranden alleen de beste; dan beste score, dan kortste rit.
    const perGroep = new Map<number, (typeof goed)[number]>()
    for (const x of goed) {
      const y = perGroep.get(x.s.groep)
      if (!y || een(x.best) > een(y.best) || (een(x.best) === een(y.best) && (o.rijtijd(x.s.id) ?? 0) < (o.rijtijd(y.s.id) ?? 0))) perGroep.set(x.s.groep, x)
    }
    const lijst = [...perGroep.values()].sort((a, b) => een(b.best) - een(a.best) || (o.rijtijd(a.s.id) ?? 0) - (o.rijtijd(b.s.id) ?? 0) || b.best - a.best)
    return { dag, lijst }
  })
  const kaart = (dag: string, lijst: (typeof dagen)[number]['lijst']) => {
    const d = new Date(dag + 'T12:00')
    if (!lijst.length) {
      return `<p class="dagniets"><b>${dagFmt.format(d)} ${d.getDate()} ${maandFmt.format(d)}</b> nergens goed${v ? ` binnen ${rijTekst(v.max)}` : ''} met ${plankTekst}</p>`
    }
    const [eerste, ...rest] = lijst
    const [k, t] = kleur(eerste.best)
    const rij = (s: SpotKort) => o.rijtijd(s.id)
    return `<article class="plandag" style="--kleur:${k};--tekstkleur:${t}">
      <figure data-id="${eerste.s.id}" data-dag="${dag}"><img src="./foto/golfsurfen.webp" alt="" loading="lazy">
        <figcaption>
          <span class="datumlijn"><b>${dagFmt.format(d).replace('.', '').toUpperCase()} ${d.getDate()}</b>${maandFmt.format(d).replace('.', '')}</span>
          <span class="cijfer">${komma(eerste.best)}</span>
          <span class="wat">Surfen · ${PLANKEN[eerste.vak[0]]}</span>
          <span class="uren">${uur(eerste.vak[1][0])}–${uur(eerste.vak[1][1])}</span>
          <span class="waar"><b>${esc(eerste.s.naam)}</b>${rij(eerste.s) ? `<em>${rijTekst(rij(eerste.s)!)} rijden</em>` : ''}</span>
        </figcaption></figure>
      ${rest.length ? `<div class="onder">${rest.slice(0, 4).map((x) => {
        const [k2, t2] = kleur(x.best)
        return `<button class="linkrij" style="--kleur:${k2};--tekstkleur:${t2}" data-id="${x.s.id}" data-dag="${dag}"><i>${komma(x.best)}</i>
          <span><b>${esc(x.s.naam)}</b><small>${PLANKEN[x.vak[0]]} · ${uur(x.vak[1][0])}–${uur(x.vak[1][1])}${rij(x.s) ? ` · ${rijTekst(rij(x.s)!)} rijden` : ''}</small></span></button>`
      }).join('')}</div>` : ''}
    </article>`
  }
  box.innerHTML = kop + '<h2 class="week">De komende dagen</h2>' + dagen.map(({ dag, lijst }) => kaart(dag, lijst)).join('') +
    `<p class="bron">Voorspelling van ${new Date(o.data.run).toLocaleString('nl-NL', { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}. Golven: Copernicus Marine · wind: ECMWF · getij: EOT20.</p>`
  box.querySelector('.wijzig')!.addEventListener('click', o.wijzigVerblijf)
  box.querySelectorAll<HTMLElement>('[data-id]').forEach((el) => el.addEventListener('click', () => {
    const s = o.data!.spots.find((x) => x.id === Number(el.dataset.id))
    if (s) o.open(s, el.dataset.dag!)
  }))
  void dagSleutel
}
