// Fiche van een spot (zoals in de eerste versie: rechts op een groot scherm, onderaan op een telefoon, de kaart blijft
// zichtbaar). Bovenaan het antwoord, dan per plank een tegel met de uren, de dag per uur en waarom.

import {
  dagNaam, dagSleutel, esc, EXPERT, golfWoord, kompas, krachtWoord, PLANKEN, rond, routeLink, SOORT, uur, vakkenOpDag,
  windWoord, type SpotData, type SpotDetail, type SpotKort,
} from './spots'
import { rijTekst } from './verblijf'

const VAN_UUR = 6
const TOT_UUR = 21
const GEVAAR: Record<string, string> = {
  ondiep: 'Ondiep rif of rotsen bij laag water', stroming: 'Sterke stroming', strekdam: 'Strekdam: terugslag bij hoog water',
  pier: 'Pier vlakbij', closeout: 'Golven klappen bij grote deining snel dicht',
}
export const kleur = (s: number) => (rond(s) >= 5 ? ['var(--s5)', 'var(--s5t)'] : ['var(--s4)', 'var(--s4t)'])

export interface FicheOpties {
  data: SpotData
  planken: () => string[]
  rijtijd: (id: number) => number | null | undefined
  tijd: () => Date // tijdstip van de kaart
  dagen: () => string[]
  naarDag: (dag: string) => void
  gesloten: () => void
}

export class Fiche {
  private el = document.getElementById('fiche')!
  id = -1

  constructor(private o: FicheOpties) {
    window.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !this.el.hidden) this.sluit() })
  }

  sluit() {
    this.el.hidden = true
    this.id = -1
    this.o.gesloten()
  }

  /** Opnieuw tekenen als de dag, het uur of de planken veranderen. */
  ververs() {
    if (this.id >= 0 && !this.el.hidden) this.open(this.id)
  }

  async open(id: number) {
    const s = this.o.data.spot(id)
    if (!s) return
    const nieuw = this.id !== id
    this.id = id
    this.el.hidden = false
    if (nieuw) this.el.scrollTop = 0
    const d = await this.o.data.detail(id)
    if (this.id !== id) return
    const t = this.o.tijd()
    const dag = dagSleutel(t)
    const planken = this.o.planken()
    const vakken = vakkenOpDag(s, dag, planken)
    const rij = this.o.rijtijd(id)
    this.el.innerHTML = `<button class="sluit" aria-label="Sluiten">×</button>
      <h2>${esc(s.naam)}</h2>
      <div class="sub">${s.soort ? SOORT[s.soort] ?? 'Strand' : 'Strand'} · strand kijkt naar het ${kompas(s.richting)}${rij ? ` · ${rijTekst(rij)} rijden` : ''}</div>
      ${this.conclusie(s, dag, vakken)}
      ${vakken.length ? `<div class="tegels">${this.tegels(vakken)}</div>` : ''}
      <h3 class="kop">${dagNaam(new Date(dag + 'T12:00'), true)} per uur</h3>
      ${this.perUur(d, dag, planken, t)}
      <h3 class="kop">Waarom ${this.momentTekst(d, t, vakken)}</h3>
      ${this.waarom(d, this.moment(d, t, vakken))}
      <div class="knoppen"><a class="knop hoofd" href="${routeLink(s)}" target="_blank" rel="noopener">Route${rij ? ` · ${rijTekst(rij)}` : ''}</a></div>
      <p class="bron">Golven: Copernicus Marine · wind: ECMWF · getij: EOT20 · strandhelling: ${esc(d.herkomst.tanb ?? '—')}</p>`
    this.el.querySelector('.sluit')!.addEventListener('click', () => this.sluit())
    this.el.querySelectorAll<HTMLElement>('[data-dag]').forEach((b) => b.addEventListener('click', () => this.o.naarDag(b.dataset.dag!)))
  }

  private conclusie(s: SpotKort, dag: string, vakken: ReturnType<typeof vakkenOpDag>) {
    if (vakken.length) {
      const [, [van, tot, g]] = vakken[0]
      return `<div class="conclusie" style="--kleur:${kleur(g)[0]}"><p>Ja, ga surfen: ${uur(van)} – ${uur(tot)}</p>
        <small>${rond(g) >= 5 ? 'Top' : 'Goed'} (${rond(g)} van 5) met ${PLANKEN[vakken[0][0]]}</small></div>`
    }
    const later = this.o.dagen().filter((x) => x > dag).map((x) => [x, vakkenOpDag(s, x, this.o.planken())[0]] as const).find(([, v]) => v)
    return `<div class="conclusie"><p>Nee, ${dag === dagSleutel(new Date()) ? 'vandaag' : 'deze dag'} niet goed</p>
      <small>${later ? `Eerstvolgende goede dag: <a href="#" data-dag="${later[0]}">${dagNaam(new Date(later[0] + 'T12:00'))}</a>, ${uur(later[1][1][0])} – ${uur(later[1][1][1])} met ${PLANKEN[later[1][0]]}`
        : 'De komende dagen nergens minstens 3 uur na elkaar een 4 of 5 met je planken.'}</small></div>`
  }

  private tegels(vakken: ReturnType<typeof vakkenOpDag>) {
    // Per plank het beste tijdvak van de dag.
    const per = new Map<string, (typeof vakken)[number][1]>()
    for (const [p, v] of vakken) if (!per.has(p)) per.set(p, v)
    return [...per].slice(0, 4).map(([p, [van, tot, g]]) => {
      const [k, t] = kleur(g)
      return `<div class="tegel" style="--kleur:${k};--tekstkleur:${t}"><span class="soort">${PLANKEN[p]}</span><b>${rond(g)}</b>
        <span class="betekenis">${uur(van)} – ${uur(tot)}</span></div>`
    }).join('')
  }

  private index(d: SpotDetail, t: Date) {
    const i = Math.round((t.getTime() - Date.parse(d.start)) / 3600e3)
    return i >= 0 && i < d.uren ? i : -1
  }

  private perUur(d: SpotDetail, dag: string, planken: string[], nu: Date) {
    const begin = new Date(dag + 'T00:00').getTime()
    const uren = Array.from({ length: TOT_UUR - VAN_UUR + 1 }, (_, k) => new Date(begin + (VAN_UUR + k) * 3600e3))
    const nuUur = nu.getHours()
    const kop = `<tr class="uren"><th></th>${uren.map((t) => `<td>${t.getHours()}</td>`).join('')}</tr>`
    const rijen = planken.map((p) => `<tr><th>${PLANKEN[p]}</th>${uren.map((t) => {
      const i = this.index(d, t)
      const sc = i < 0 ? 0 : d.score[p][i] / 10
      const nacht = i >= 0 && d.wind[i] === null
      const klas = sc >= 4.5 ? 's5' : sc >= 3.8 ? 's4' : 's0'
      return `<td class="${klas}${nacht ? ' nacht' : ''}${dagSleutel(nu) === dag && t.getHours() === nuUur ? ' nu' : ''}">${i < 0 ? '' : rond(sc)}</td>`
    }).join('')}</tr>`).join('')
    return `<div class="dag"><table>${kop}${rijen}</table></div>`
  }

  /** Moment om uit te leggen: het uur van de kaart als het licht is, anders het midden van de beste sessie, anders 13u. */
  private moment(d: SpotDetail, t: Date, vakken: ReturnType<typeof vakkenOpDag>) {
    const u = new Date(t)
    u.setMinutes(0, 0, 0)
    const i = this.index(d, u)
    if (i >= 0 && d.wind[i]) return i
    if (vakken.length) return this.index(d, new Date((Date.parse(vakken[0][1][0]) + Date.parse(vakken[0][1][1])) / 2 - 1800e3))
    return this.index(d, new Date(dagSleutel(t) + 'T13:00'))
  }

  private momentTekst(d: SpotDetail, t: Date, vakken: ReturnType<typeof vakkenOpDag>) {
    const i = this.moment(d, t, vakken)
    return i < 0 ? '' : `<span style="text-transform:none;letter-spacing:0">(om ${new Date(Date.parse(d.start) + i * 3600e3).getHours()}u)</span>`
  }

  private waarom(d: SpotDetail, i: number) {
    if (i < 0 || !d.wind[i]) return '<p class="bron">Geen gegevens voor dit moment.</p>'
    const li = (kop: string, tekst: string, klas = '') => `<li class="${klas}"><small>${kop}</small>${tekst}</li>`
    const uit: string[] = []
    const dn = d.deining[i], br = d.breker[i] ?? 0, wz = d.windzee[i] ?? 0
    uit.push(dn && br >= 0.1
      ? li('Golven', `<b>${golfWoord(br)}</b> (${br.toLocaleString('nl-NL')} m), ${krachtWoord(dn[2])} (${dn[2]} s), uit het ${kompas(dn[1])}${wz > dn[0] * 0.6 && wz > 0.4 ? '; veel korte windgolven ertussen' : ''}`)
      : li('Golven', '<b>Bijna vlak</b>'))
    const [kn, rel, stoot] = d.wind[i]!
    uit.push(li('Wind', windWoord(kn, rel) + (stoot - kn >= 8 ? ` · vlagen tot ${stoot} kn` : '')))
    const dag = dagSleutel(new Date(Date.parse(d.start) + i * 3600e3))
    const tij = d.getij.filter(([x]) => dagSleutel(new Date(x)) === dag).map(([x, soort]) => `${soort} om ${uur(x)}`).join(' · ')
    if (tij) uit.push(li('Getij', tij.charAt(0).toUpperCase() + tij.slice(1) + (d.werkt_bij_tij?.length ? `<br>Werkt het best bij ${d.werkt_bij_tij.map((w) => (w === 'half' ? 'halftij' : `${w} water`)).join(' of ')}` : '')))
    const letop = new Set<string>()
    for (const c of d.expert[i] ?? '') if (EXPERT[c]) letop.add(EXPERT[c].charAt(0).toUpperCase() + EXPERT[c].slice(1))
    for (const g of d.gevaren) if (GEVAAR[g]) letop.add(GEVAAR[g])
    if (d.vlaggen[String(i)]?.includes('bliksem')) letop.add('Kans op onweer')
    if (letop.size) uit.push(li('Let op', [...letop].join(' · ') + (d.expert[i] ? '<br>Alleen voor ervaren surfers' : ''), 'letop'))
    return `<ul class="waarom">${uit.join('')}</ul>`
  }
}
