// Knop "Surfen" op de kaart: uitleg bij de cirkels en de filters (score van de rekenchat, versie 2.1).
// Filters: wat tonen (alles, golfsporten, windsporten, stille waters vanaf 3), het niveau, en je gewicht.
// Ze blijven in deze browser bewaard.
import { cirkel, leesStil, leesTeken, plaatjeUrl, RANDUITLEG, type Helft } from './scorekaart'
import type { Niveau } from './score'

const SLEUTEL = 'surf-filter-v3'
export const TOON = [
  { waarde: 'alles', naam: 'Alles' },
  { waarde: 'golf', naam: 'Golfsporten (WAVE 3 of 4)', kleur: '#3f6fe0' },
  { waarde: 'wind', naam: 'Windsporten (WIND 3 of 4)', kleur: '#16b3d0' },
  { waarde: 'stil', naam: 'Stille waters (3 of 4)', kleur: '#8a949c' },
] as const
export const NIVEAUS = [
  { waarde: '', naam: 'Alle niveaus' },
  { waarde: 'beginner', naam: 'Beginner' },
  { waarde: 'gemiddeld', naam: 'Gemiddeld' },
  { waarde: 'ervaren', naam: 'Ervaren' },
] as const

export const instelling = { toon: 'alles' as string, niveau: '' as string, gewicht: null as number | null }
try { Object.assign(instelling, JSON.parse(localStorage.getItem(SLEUTEL) ?? '{}')) } catch { /* standaard */ }
export const niveau = (): Niveau | null => (instelling.niveau || null) as Niveau | null
// Gewicht in klassen van 5 kg (pipeline/site/invoer.py, GEWICHTEN); kaart, fiche en planning rekenen ermee.
export const GEWICHTEN = Array.from({ length: 13 }, (_, i) => 50 + 5 * i)
const klasse = (g: number) => Math.min(110, Math.max(50, Math.round(g / 5) * 5))
if (instelling.gewicht != null) instelling.gewicht = klasse(instelling.gewicht)
export const gewicht = (): number | undefined => (instelling.gewicht && instelling.gewicht !== 75 ? instelling.gewicht : undefined)
const bewaar = () => { try { localStorage.setItem(SLEUTEL, JSON.stringify(instelling)) } catch { /* niet bewaard */ } }

// Telt dit strand mee op het gekozen uur? g = golfteken, w = windteken, s = stille waters.
export function toont(g: string, w: string, s: string): boolean {
  const n = (h: Helft) => h.cijfer !== null && h.cijfer >= 3
  if (instelling.toon === 'golf') return n(leesTeken(g))
  if (instelling.toon === 'wind') return n(leesTeken(w))
  if (instelling.toon === 'stil') { const x = leesStil(s).cijfer; return x !== null && x >= 3 }
  return true
}

const voorbeeld = (w: string, v: string, storm = false) =>
  `<img src="${plaatjeUrl(cirkel(leesTeken(w), leesTeken(v), 30, storm))}" width="30" height="30" alt="">`

const knopTekst = () => {
  const t = TOON.find((k) => k.waarde === instelling.toon)
  const n = NIVEAUS.find((k) => k.waarde === instelling.niveau)
  const delen = [instelling.toon !== 'alles' ? t?.naam.replace(/ \(.*\)$/, '') : '', instelling.niveau ? n?.naam : '',
    gewicht() ? `${gewicht()} kg` : '']
    .filter(Boolean)
  return delen.length ? `Surfen · ${delen.join(' · ')}` : 'Surfen'
}

// opnieuw(bestandNodig): de kaart opnieuw tekenen (bij een ander niveau of gewicht eerst dat bestand laden).
export function surfPaneel(opnieuw: (bestandNodig: boolean) => void) {
  const knop = document.createElement('button')
  knop.className = 'laagknop surf'
  knop.textContent = knopTekst()
  knop.setAttribute('aria-expanded', 'false')
  const p = document.createElement('div')
  p.className = 'klimpaneel surfpaneel'
  p.hidden = true
  document.getElementById('laagknoppen')!.prepend(knop)
  document.getElementById('kaart')!.append(p)
  knop.onclick = () => {
    document.querySelectorAll<HTMLElement>('.klimpaneel').forEach((x) => { if (x !== p) x.hidden = true })
    document.querySelectorAll('#laagknoppen button').forEach((b) => { if (b !== knop) b.setAttribute('aria-expanded', 'false') })
    p.hidden = !p.hidden; knop.setAttribute('aria-expanded', String(!p.hidden)); if (!p.hidden) vul()
  }
  const vul = () => {
    p.innerHTML = `
      <fieldset class="keuzes"><legend>Toon</legend>
        ${TOON.map((k) => `<label style="--kleur:${'kleur' in k ? k.kleur : 'transparent'}"><input type="radio" name="surftoon" value="${k.waarde}"
          ${instelling.toon === k.waarde ? 'checked' : ''}>${'kleur' in k ? '<i></i>' : ''} ${k.naam}</label>`).join('')}
      </fieldset>
      <fieldset class="keuzes"><legend>Niveau</legend>
        ${NIVEAUS.map((k) => `<label><input type="radio" name="surfniveau" value="${k.waarde}"
          ${instelling.niveau === k.waarde ? 'checked' : ''}> ${k.naam}</label>`).join('')}
        <p class="klein">Met een niveau telt alleen dat niveau mee: zo zie je ook wat te veel is voor beginners.</p>
      </fieldset>
      <fieldset class="keuzes"><legend>Je gewicht</legend>
        <label class="gewicht"><select name="gewicht">${GEWICHTEN.map((g) => `<option value="${g}"
          ${(instelling.gewicht ?? 75) === g ? 'selected' : ''}>${g}</option>`).join('')}</select> kg</label>
        <p class="klein">Telt mee voor kite- en windsurfen, op de kaart, in de fiche en in de planning (per 5 kg).</p>
      </fieldset>
      <fieldset class="uitleg"><legend>Zo lees je een cirkel</legend>
        <p>${voorbeeld('2', 'G')}<span>Links <b>WIND</b> (windsporten), rechts <b>WAVE</b> (golfsporten).</span></p>
        <ol class="niveaus"><li><b>0</b> niets</li><li><b>1</b> iets</li><li><b>2</b> potentieel</li>
          <li><b>3</b> zekerheid</li><li><b>4</b> ideaal</li></ol>
        <p>${voorbeeld('g', 'G')}<span>Groene rand: ${RANDUITLEG.groen}.</span></p>
        <p>${voorbeeld('o', 'O')}<span>Oranje rand: ${RANDUITLEG.oranje}.</span></p>
        <p>${voorbeeld('r', 'R')}<span>Rode rand: ${RANDUITLEG.rood}.</span></p>
        <p>${voorbeeld('a', '1')}<span>Zwarte helft: te veel wind of golf (te gevaarlijk).</span></p>
        <p>${voorbeeld('c', 'a', true)}<span>Zwarte achtergrond: storm.</span></p>
        <p class="klein">Een getal in een wit bolletje is het aantal stranden. Tik op een strand voor de fiche.</p>
      </fieldset>`
    p.querySelectorAll<HTMLInputElement>('input[name=surftoon]').forEach((i) => i.onchange = () => {
      instelling.toon = i.value; bewaar(); knop.textContent = knopTekst(); opnieuw(false)
    })
    p.querySelectorAll<HTMLInputElement>('input[name=surfniveau]').forEach((i) => i.onchange = () => {
      instelling.niveau = i.value; bewaar(); knop.textContent = knopTekst(); opnieuw(true)
    })
    const gw = p.querySelector<HTMLSelectElement>('select[name=gewicht]')!
    gw.onchange = () => {
      const v = Number(gw.value)
      instelling.gewicht = v === 75 ? null : v
      bewaar(); knop.textContent = knopTekst(); opnieuw(true)
    }
  }
}
