// Planning in het tabblad (geen venster): eerst instellen waar je verblijft, hoe lang je maximaal wil rijden en met
// welke planken; dan per dag de stranden binnen die rijtijd waar je minstens 3 uur na elkaar een 4 of 5 hebt. Op 1 staat
// het strand met de langste sessie (meeste uren fun); bij gelijke duur de hoogste score, dan de kortste rit.

import { kleur } from './fiche'
import { esc, komma, PLANKEN, uur, vakkenOpDag, type SpotIndex, type SpotKort, type Vak } from './spots'
import { plaatsVan, rijTekst, zoekInDeBuurt, zoekPlaats, type Gevonden, type Verblijf } from './verblijf'

const dagFmt = new Intl.DateTimeFormat('nl-NL', { weekday: 'short' })
const maandFmt = new Intl.DateTimeFormat('nl-NL', { month: 'short' })
const STANDAARD_RIJTIJD = 120 // minuten, zoals in de eerste versie
const PIN = '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M12 21s-7-6.2-7-11a7 7 0 0 1 14 0c0 4.8-7 11-7 11z"/><circle cx="12" cy="10" r="2.5"/></svg>'

export interface PlanningOpties {
  data: SpotIndex | null
  planken: string[]
  verblijf: Verblijf | null
  rijtijd: (id: number) => number | null | undefined
  /** 'bezig' terwijl de rijtijden berekend worden, 'fout' als de routeplanner niet bereikbaar is. */
  rijStatus: 'bezig' | 'klaar' | 'fout'
  dagen: string[]
  zetVerblijf: (v: Verblijf) => void
  zetPlanken: (p: string[]) => void
  gewicht: number | null
  zetGewicht: (kg: number | null) => void
  open: (s: SpotKort, dag: string) => void
}

/** Duur van een tijdvak in minuten. */
const duur = (v: Vak) => (Date.parse(v[1]) - Date.parse(v[0])) / 60e3
const duurTekst = (m: number) => {
  const u = Math.floor(m / 60), r = Math.round(m % 60)
  return r ? `${u} uur ${r} min` : `${u} uur`
}

export class Planning {
  private o!: PlanningOpties
  private lijst: HTMLElement
  private instellingen: HTMLElement

  constructor(box: HTMLElement) {
    box.innerHTML = '<div class="instellingen"></div><div class="planlijst"></div>'
    this.instellingen = box.querySelector('.instellingen')!
    this.lijst = box.querySelector('.planlijst')!
  }

  /** Zoekveld van stap 1 in beeld en klaar om te typen. */
  focus() {
    this.instellingen.scrollIntoView({ block: 'start' })
    this.instellingen.querySelector<HTMLInputElement>('input[type=search]')?.focus()
  }

  teken(o: PlanningOpties) {
    const eerste = !this.o
    this.o = o
    if (eerste) this.bouwInstellingen()
    this.werkInstellingenBij()
    this.tekenLijst()
  }

  // ---- Stap 1 tot 3: blijft staan (ook tijdens het typen), alleen de keuzes worden bijgewerkt ----
  private bouwInstellingen() {
    const el = this.instellingen
    el.innerHTML = `
      <div class="stap"><span class="nr">1</span><h3>Waar verblijf je?</h3></div>
      <div class="zoekrij"><input type="search" placeholder="Adres, hotel of dorp" autocomplete="off" aria-label="Zoek je verblijf"
        role="combobox" aria-expanded="false" aria-autocomplete="list"></div>
      <ul class="gevonden" role="listbox"></ul>
      <div class="keuzelijn"><span class="gekozen"></span><button type="button" class="linkknop" data-a="hier">Gebruik mijn locatie</button></div>
      <p class="fout" hidden></p>
      <div class="stap"><span class="nr">2</span><h3>Hoe lang wil je maximaal rijden?</h3></div>
      <div class="tijden">
        <label><input name="uren" type="number" inputmode="numeric" min="0" max="12" step="1" aria-label="Uren"> u</label>
        <label><input name="min" type="number" inputmode="numeric" min="0" max="59" step="1" aria-label="Minuten"> min</label>
      </div>
      <div class="stap"><span class="nr">3</span><h3>Met welke planken?</h3></div>
      <div class="chips planken">${Object.entries(PLANKEN).map(([k, n]) => `<button type="button" data-p="${k}" aria-pressed="false">${n}</button>`).join('')}</div>
      <div class="gewicht"><label>Gewicht <input name="gewicht" type="number" inputmode="numeric" min="20" max="200" step="1"> kg</label></div>`
    const veld = el.querySelector<HTMLInputElement>('input[type=search]')!
    const lijst = el.querySelector('.gevonden')!
    const fout = el.querySelector<HTMLElement>('.fout')!
    const toonFout = (t: string) => { fout.textContent = t; fout.hidden = !t }
    let resultaten: Gevonden[] = [], actief = -1, wacht: ReturnType<typeof setTimeout> | undefined, bezig: AbortController | null = null

    const kies = async (g0: Gevonden | { naam: string; lat: number; lon: number }) => {
      let g = g0
      if ('titel' in g0) {
        try { g = await plaatsVan(g0) } catch { toonFout('Deze plaats kon niet worden geladen. Kies een andere.'); return }
      }
      lijst.innerHTML = ''; resultaten = []; veld.value = ''; veld.setAttribute('aria-expanded', 'false'); toonFout('')
      this.o.zetVerblijf({ naam: g.naam, lat: g.lat, lon: g.lon, max: ingevuld() || this.o.verblijf?.max || STANDAARD_RIJTIJD })
    }
    // Ingevulde rijtijd (stap 2) in minuten; 0 als er niets bruikbaars staat.
    const ingevuld = () => {
      const u = Number(el.querySelector<HTMLInputElement>('input[name=uren]')!.value || 0)
      const m = Number(el.querySelector<HTMLInputElement>('input[name=min]')!.value || 0)
      return Math.max(0, Math.round(u)) * 60 + Math.max(0, Math.min(59, Math.round(m)))
    }
    const markeer = (i: number) => {
      actief = i
      lijst.querySelectorAll('button').forEach((b, k) => b.setAttribute('aria-selected', String(k === i)))
    }
    const zoek = async () => {
      const q = veld.value.trim()
      bezig?.abort()
      if (q.length < 2) { lijst.innerHTML = ''; resultaten = []; veld.setAttribute('aria-expanded', 'false'); return }
      bezig = new AbortController()
      try {
        resultaten = await zoekPlaats(q, bezig.signal)
        lijst.innerHTML = resultaten.length ? '' : '<li class="rustig">Niets gevonden.</li>'
        resultaten.forEach((g) => {
          const li = document.createElement('li')
          li.innerHTML = `<button type="button" role="option">${PIN}<span><b>${esc(g.titel)}</b><small>${esc(g.adres)}</small></span></button>`
          li.querySelector('button')!.onclick = () => kies(g)
          lijst.appendChild(li)
        })
        veld.setAttribute('aria-expanded', String(resultaten.length > 0))
        markeer(-1)
        toonFout('')
      } catch (e) {
        if ((e as Error).name === 'AbortError') return
        lijst.innerHTML = ''; toonFout('Zoeken lukt nu niet. Probeer opnieuw of gebruik je locatie.')
      }
    }
    veld.oninput = () => {
      clearTimeout(wacht)
      if (veld.value.trim().length >= 2 && !lijst.querySelector('button')) lijst.innerHTML = '<li class="rustig">Zoeken…</li>'
      wacht = setTimeout(zoek, 150)
    }
    veld.onkeydown = (e) => {
      if (e.key === 'ArrowDown' && resultaten.length) { e.preventDefault(); markeer((actief + 1) % resultaten.length) }
      else if (e.key === 'ArrowUp' && resultaten.length) { e.preventDefault(); markeer((actief - 1 + resultaten.length) % resultaten.length) }
      else if (e.key === 'Enter') { e.preventDefault(); if (resultaten.length) kies(resultaten[Math.max(0, actief)]); else zoek() }
      else if (e.key === 'Escape') { veld.value = ''; lijst.innerHTML = ''; resultaten = [] }
    }
    el.querySelector<HTMLButtonElement>('[data-a=hier]')!.onclick = () => {
      if (!navigator.geolocation) { toonFout('Je locatie is niet beschikbaar.'); return }
      navigator.geolocation.getCurrentPosition(
        (pos) => kies({ naam: 'Mijn locatie', lat: pos.coords.latitude, lon: pos.coords.longitude }),
        () => toonFout('Je locatie is niet beschikbaar.'))
    }
    // Rijtijd in uren en minuten (zoals in de eerste versie); telt pas als je klaar bent met typen.
    const uren = el.querySelector<HTMLInputElement>('input[name=uren]')!
    const min = el.querySelector<HTMLInputElement>('input[name=min]')!
    const zetRijtijd = () => {
      const max = ingevuld()
      const v = this.o.verblijf
      if (max < 1) { toonFout('Vul in hoe lang je wil rijden.'); return }
      if (!v) return // wordt gebruikt zodra je je verblijf kiest
      toonFout('')
      if (max !== v.max) this.o.zetVerblijf({ ...v, max })
    }
    uren.addEventListener('change', zetRijtijd)
    min.addEventListener('change', zetRijtijd)
    const kg = el.querySelector<HTMLInputElement>('input[name=gewicht]')!
    kg.addEventListener('change', () => this.o.zetGewicht(Number(kg.value) || null))
    el.querySelectorAll<HTMLButtonElement>('.planken button').forEach((b) => b.addEventListener('click', () => {
      const alle = this.o.planken.length === Object.keys(PLANKEN).length
      const p = b.dataset.p!
      // Alles aan: een tik kiest alleen die plank. Anders aan/uit; niets meer aan = weer alle planken.
      let nieuw = alle ? [p] : this.o.planken.includes(p) ? this.o.planken.filter((x) => x !== p) : [...this.o.planken, p]
      if (!nieuw.length) nieuw = Object.keys(PLANKEN)
      this.o.zetPlanken(Object.keys(PLANKEN).filter((k) => nieuw.includes(k)))
    }))
  }

  private werkInstellingenBij() {
    const el = this.instellingen
    const v = this.o.verblijf
    if (v) zoekInDeBuurt(v.lon, v.lat)
    el.querySelector('.gekozen')!.innerHTML = v ? `<b>${esc(v.naam.split(',').slice(0, 2).join(','))}</b>` : ''
    el.querySelector<HTMLInputElement>('input[type=search]')!.placeholder = v ? 'Ander verblijf zoeken' : 'Adres, hotel of dorp'
    const max = v?.max ?? STANDAARD_RIJTIJD
    const uren = el.querySelector<HTMLInputElement>('input[name=uren]')!, min = el.querySelector<HTMLInputElement>('input[name=min]')!
    if (v || !uren.value) {
      if (document.activeElement !== uren) uren.value = String(Math.floor(max / 60))
      if (document.activeElement !== min) min.value = String(max % 60)
    }
    const kg = el.querySelector<HTMLInputElement>('input[name=gewicht]')!
    if (document.activeElement !== kg) kg.value = this.o.gewicht ? String(this.o.gewicht) : ''
    const alle = this.o.planken.length === Object.keys(PLANKEN).length
    el.querySelectorAll<HTMLButtonElement>('.planken button').forEach((b) => b.setAttribute('aria-pressed', String(!alle && this.o.planken.includes(b.dataset.p!))))
  }

  // ---- De dagen ----
  private tekenLijst() {
    const o = this.o
    const v = o.verblijf
    const plankTekst = o.planken.length === Object.keys(PLANKEN).length ? 'alle planken' : o.planken.map((p) => PLANKEN[p]).join(', ')
    if (!v) {
      this.lijst.innerHTML = '<p class="dagniets">Kies eerst waar je verblijft (stap 1). Dan zie je per dag de beste stranden binnen je rijtijd.</p>'
      return
    }
    if (!o.data) {
      this.lijst.innerHTML = '<p class="dagniets">De voorspelling wordt geladen…</p>'
      return
    }
    if (o.rijStatus === 'bezig') {
      this.lijst.innerHTML = '<p class="dagniets">Rijtijden berekenen…</p>'
      return
    }
    const zonderRit = o.rijStatus === 'fout'
    const bereikbaar = (s: SpotKort) => {
      if (zonderRit) return true
      const m = o.rijtijd(s.id)
      return m != null && m <= v.max
    }
    const dagen = o.dagen.map((dag) => {
      // Per strand de langste goede sessie van de dag met je planken.
      const goed = o.data!.spots.filter(bereikbaar).flatMap((s) => {
        const vakken = vakkenOpDag(s, dag, o.planken)
        if (!vakken.length) return []
        const [plank, vak] = vakken.reduce((a, b) => (duur(b[1]) > duur(a[1]) || (duur(b[1]) === duur(a[1]) && b[1][2] > a[1][2]) ? b : a))
        return [{ s, plank, vak, min: duur(vak), rit: o.rijtijd(s.id) ?? Infinity }]
      })
      type X = (typeof goed)[number]
      const beter = (a: X, b: X) => b.min - a.min || b.vak[2] - a.vak[2] || a.rit - b.rit
      // Buurstranden (zelfde groep) maar één keer: de beste.
      const perGroep = new Map<number, X>()
      for (const x of goed) {
        const y = perGroep.get(x.s.groep)
        if (!y || beter(x, y) < 0) perGroep.set(x.s.groep, x)
      }
      return { dag, lijst: [...perGroep.values()].sort(beter) }
    })
    const ritTekst = (x: { rit: number }) => (Number.isFinite(x.rit) ? `${rijTekst(x.rit)} rijden` : '')
    const kaart = (dag: string, lijst: (typeof dagen)[number]['lijst']) => {
      const d = new Date(dag + 'T12:00')
      if (!lijst.length) {
        return `<p class="dagniets"><b>${dagFmt.format(d)} ${d.getDate()} ${maandFmt.format(d)}</b> nergens minstens ${o.data!.min_uren} uur goed binnen ${rijTekst(v.max)} met ${plankTekst}</p>`
      }
      const [x, ...rest] = lijst
      const [k, t] = kleur(x.vak[2])
      return `<article class="plandag" style="--kleur:${k};--tekstkleur:${t}">
        <figure data-id="${x.s.id}" data-dag="${dag}"><img src="./foto/golfsurfen.webp" alt="" loading="lazy">
          <figcaption>
            <span class="datumlijn"><b>${dagFmt.format(d).replace('.', '').toUpperCase()} ${d.getDate()}</b>${maandFmt.format(d).replace('.', '')}</span>
            <span class="cijfer">${komma(x.vak[2])}</span>
            <span class="wat">${duurTekst(x.min)} surf · ${PLANKEN[x.plank]}</span>
            <span class="uren">${uur(x.vak[0])}–${uur(x.vak[1])}</span>
            <span class="waar"><b>${esc(x.s.naam)}</b>${ritTekst(x) ? `<em>${ritTekst(x)}</em>` : ''}</span>
          </figcaption></figure>
        ${rest.length ? `<div class="onder">${rest.slice(0, 4).map((y) => {
          const [k2, t2] = kleur(y.vak[2])
          return `<button class="linkrij" style="--kleur:${k2};--tekstkleur:${t2}" data-id="${y.s.id}" data-dag="${dag}"><i>${komma(y.vak[2])}</i>
            <span><b>${esc(y.s.naam)}</b><small>${duurTekst(y.min)} · ${PLANKEN[y.plank]} · ${uur(y.vak[0])}–${uur(y.vak[1])}${ritTekst(y) ? ` · ${ritTekst(y)}` : ''}</small></span></button>`
        }).join('')}</div>` : ''}
      </article>`
    }
    this.lijst.innerHTML = `<h2 class="week">De komende dagen</h2>
      <p class="uitleg">Per dag het strand waar je het langst kan surfen (minstens ${o.data.min_uren} uur na elkaar een 4 of 5) met ${plankTekst}, binnen ${rijTekst(v.max)} rijden${zonderRit ? '. De rijtijden konden niet berekend worden: alle stranden staan erin' : ''}.</p>` +
      dagen.map(({ dag, lijst }) => kaart(dag, lijst)).join('') +
      `<p class="bron">Voorspelling van ${new Date(o.data.run).toLocaleString('nl-NL', { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}. Golven: Copernicus Marine · wind: ECMWF · getij: EOT20 · rijtijden: OSRM.</p>`
    this.lijst.querySelectorAll<HTMLElement>('[data-id]').forEach((el) => el.addEventListener('click', () => {
      const s = o.data!.spots.find((x) => x.id === Number(el.dataset.id))
      if (s) o.open(s, el.dataset.dag!)
    }))
  }
}
