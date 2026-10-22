// Blad van één spot: het antwoord (ja of nee, wanneer, welke plank), per plank een balk door de dag, en waarom in
// gewone woorden.

import {
  dagNaam, dagSleutel, esc, EXPERT, golfWoord, hemelsbreed, kompas, krachtWoord, PLANKEN, rond, routeLink, SOORT, uur,
  vakkenOpDag, windWoord, type SpotData, type SpotDetail, type SpotKort,
} from './spots'
import type { Profiel } from './profiel'

const VAN_UUR = 6
const TOT_UUR = 21 // balken van 6u tot 21u (lokale tijd)

const GEVAAR: Record<string, string> = {
  ondiep: 'ondiep rif of rotsen bij laag water', stroming: 'sterke stroming', strekdam: 'strekdam: terugslag bij hoog water',
  pier: 'pier vlakbij', closeout: 'golven klappen bij grote deining snel dicht',
}

export interface BladOpties {
  data: SpotData
  planken: string[]
  profiel: Profiel
  dagen: string[] // dagen met voorspelling
  opKaart: (s: SpotKort, tijd: number) => void
}

export class Blad {
  private el = document.createElement('section')
  private id = -1
  private dag = ''

  constructor(private o: BladOpties) {
    this.el.className = 'blad'
    this.el.hidden = true
    this.el.setAttribute('role', 'dialog')
    this.el.setAttribute('aria-modal', 'true')
    document.body.append(this.el)
    window.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !this.el.hidden) this.sluit() })
  }

  sluit() {
    this.el.hidden = true
  }

  async open(id: number, dag: string) {
    this.id = id
    this.dag = dag
    const s = this.o.data.spot(id)
    if (!s) return
    this.el.hidden = false
    this.el.scrollTop = 0
    this.el.innerHTML = this.kop(s) + '<p class="zacht">Laden…</p>'
    this.knoppen(s)
    const d = await this.o.data.detail(id)
    if (this.id !== id || this.dag !== dag) return
    this.el.innerHTML = this.kop(s) + this.antwoord(s) + this.dagen() + this.balken(s, d) + this.waarom(s, d) + this.acties(s) +
      `<p class="zacht blad-voet">Golven: Copernicus Marine · wind: ECMWF · getij: EOT20 · strandhelling: ${esc(d.herkomst.tanb ?? '—')}</p>`
    this.knoppen(s)
  }

  private kop(s: SpotKort) {
    const km = this.o.profiel.verblijf ? Math.round(hemelsbreed(this.o.profiel.verblijf, s)) : null
    return `<div class="blad-kop">
      <button class="terug" aria-label="Terug"><svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><path d="M15 18l-6-6 6-6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
      <span class="zacht">${dagNaam(new Date(this.dag + 'T12:00'), true)}</span>
    </div>
    <h1>${esc(s.naam)}</h1>
    <div class="zacht">${s.soort ? SOORT[s.soort] ?? s.soort : 'Strand'}${km !== null ? ` · ongeveer ${km} km in rechte lijn` : ''}</div>`
  }

  private antwoord(s: SpotKort) {
    const v = vakkenOpDag(s, this.dag, this.o.planken)
    if (v.length) {
      const [plank, [van, tot, g]] = v[0]
      const ook = [...new Set(v.slice(1).map(([p]) => PLANKEN[p]))].filter((p) => p !== PLANKEN[plank])
      return `<div class="antwoord ja c${rond(g)}">
        <div class="groot">Ja, ga surfen</div>
        <div class="middel">${uur(van)} – ${uur(tot)} · score ${rond(g)} van 5</div>
        <div>Beste plank: ${PLANKEN[plank]}${ook.length ? ` · ook goed: ${ook.join(', ')}` : ''}</div>
      </div>`
    }
    // Volgende dag waarop het wel goed is.
    const later = this.o.dagen.filter((d) => d > this.dag).map((d) => [d, vakkenOpDag(s, d, this.o.planken)[0]] as const).find(([, x]) => x)
    return `<div class="antwoord nee">
      <div class="groot">Nee, ${this.dag === dagSleutel(new Date()) ? 'vandaag' : 'deze dag'} niet goed</div>
      <div>${later ? `Eerstvolgende goede dag: <b>${dagNaam(new Date(later[0] + 'T12:00'))}</b>, ${uur(later[1][1][0])} – ${uur(later[1][1][1])} (${PLANKEN[later[1][0]]})` : 'De komende dagen nergens 3 uur na elkaar een 4 of 5.'}</div>
    </div>`
  }

  private dagen() {
    return `<div class="v-dagen blad-dagen">${this.o.dagen.map((d) =>
      `<button data-dag="${d}" class="${d === this.dag ? 'aan' : ''}" aria-pressed="${d === this.dag}">${dagNaam(new Date(d + 'T12:00'))}</button>`).join('')}</div>`
  }

  /** Index van het uur in de reeks van de spot (of -1). */
  private uurIndex(d: SpotDetail, t: Date) {
    const i = Math.round((t.getTime() - Date.parse(d.start)) / 3600e3)
    return i >= 0 && i < d.uren ? i : -1
  }

  private balken(s: SpotKort, d: SpotDetail) {
    const dagStart = new Date(this.dag + 'T00:00')
    const uren = Array.from({ length: TOT_UUR - VAN_UUR }, (_, k) => new Date(dagStart.getTime() + (VAN_UUR + k) * 3600e3))
    const rijen = this.o.planken.map((p) => {
      const cellen = uren.map((t) => {
        const i = this.uurIndex(d, t)
        const sc = i < 0 ? 0 : d.score[p][i] / 10
        const klasse = sc >= 4.5 ? 'c5' : sc >= R_DREMPEL ? 'c4' : ''
        return `<span class="${klasse}" title="${t.getHours()}u: ${sc ? sc.toFixed(1) : '–'}"></span>`
      }).join('')
      const goed = vakkenOpDag(s, this.dag, [p]).length > 0
      return `<div class="balk-rij"><span class="${goed ? '' : 'zacht'}">${PLANKEN[p]}</span><div class="balk">${cellen}</div></div>`
    }).join('')
    const as = [7, 10, 13, 16, 19].map((h) => `<span style="left:${((h - VAN_UUR) / (TOT_UUR - VAN_UUR)) * 100}%">${h}u</span>`).join('')
    return `<h2 class="sectie">Per plank doorheen de dag</h2>${rijen}
      <div class="balk-rij"><span></span><div class="balk-as">${as}</div></div>
      <div class="legende"><span><i class="c5"></i>5 top</span><span><i class="c4"></i>4 goed</span><span><i></i>niet goed of donker</span></div>`
  }

  private waarom(s: SpotKort, d: SpotDetail) {
    const v = vakkenOpDag(s, this.dag, this.o.planken)[0]
    // Moment om uit te leggen: midden van de beste sessie, anders 13u.
    const t = v ? new Date((Date.parse(v[1][0]) + Date.parse(v[1][1])) / 2) : new Date(this.dag + 'T13:00')
    t.setMinutes(0, 0, 0)
    const i = this.uurIndex(d, t)
    if (i < 0 || !d.wind[i]) return '<h2 class="sectie">Waarom</h2><p class="zacht">Geen gegevens voor dit moment.</p>'
    const rij = (k: string, w: string) => `<div class="waarom-rij"><span class="zacht">${k}</span><span>${w}</span></div>`
    const regels: string[] = []
    const dn = d.deining[i], br = d.breker[i] ?? 0, wz = d.windzee[i] ?? 0
    if (dn && br >= 0.1) {
      regels.push(rij('Golven', `<b>${golfWoord(br)}</b> (${br.toLocaleString('nl-NL')} m), ${krachtWoord(dn[2])}, uit het ${kompas(dn[1])}${wz > dn[0] * 0.6 && wz > 0.4 ? '; veel korte windgolven ertussen' : ''}`))
    } else regels.push(rij('Golven', '<b>Bijna vlak</b>'))
    const [kn, rel, stoot] = d.wind[i]!
    regels.push(rij('Wind', windWoord(kn, rel) + (stoot - kn >= 8 ? ` · vlagen tot ${stoot} kn` : '')))
    const dag = this.dag
    const tij = d.getij.filter(([x]) => dagSleutel(new Date(x)) === dag).map(([x, soort]) => `${soort} om ${uur(x)}`).join(', ')
    if (tij) regels.push(rij('Getij', tij.charAt(0).toUpperCase() + tij.slice(1) + (d.werkt_bij_tij?.length ? ` · deze spot werkt het best bij ${d.werkt_bij_tij.map((w) => w === 'half' ? 'halftij' : w + ' water').join(' of ')}` : '')))
    const letop = new Set<string>()
    for (const c of d.expert[i] ?? '') if (EXPERT[c]) letop.add(EXPERT[c])
    for (const g of d.gevaren) if (GEVAAR[g]) letop.add(GEVAAR[g])
    if (d.vlaggen[String(i)]?.includes('bliksem')) letop.add('kans op onweer')
    if (letop.size) regels.push(rij('Let op', [...letop].join(', ') + (d.expert[i] ? ': alleen voor ervaren surfers' : '')))
    return `<h2 class="sectie">Waarom${v ? '' : ''} <span class="zacht">(om ${t.getHours()}u)</span></h2>${regels.join('')}`
  }

  private acties(s: SpotKort) {
    return `<div class="blad-acties">
      <a class="knop vol" href="${routeLink(s)}" target="_blank" rel="noopener">Route</a>
      <button class="knop" data-kaart>Toon op kaart</button>
    </div>`
  }

  private knoppen(s: SpotKort) {
    this.el.querySelector('.terug')?.addEventListener('click', () => this.sluit())
    this.el.querySelectorAll<HTMLButtonElement>('.blad-dagen button').forEach((b) =>
      b.addEventListener('click', () => this.open(this.id, b.dataset.dag!)))
    this.el.querySelector('[data-kaart]')?.addEventListener('click', () => {
      this.sluit()
      // Op de kaart het midden van de beste sessie die dag tonen, anders 13u.
      const v = vakkenOpDag(s, this.dag, this.o.planken)[0]
      this.o.opKaart(s, v ? (Date.parse(v[1][0]) + Date.parse(v[1][1])) / 2 : Date.parse(this.dag + 'T13:00'))
    })
  }
}

const R_DREMPEL = 3.8 // kaartdrempel uit de regels (index.json 'drempel'); goed = 4 na afronden van het gemiddelde
