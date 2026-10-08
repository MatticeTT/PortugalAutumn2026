// Knop "Surfen" op de kaart, zoals "Klimmen": uitleg bij de bolletjes en filters.
// De filters gelden voor het gekozen uur en blijven in deze browser bewaard.
import { bolletjeWW } from './kleuren'

const SLEUTEL = 'surf-filter-v2'
// Eén keuze: alles, of alleen de stranden die op het gekozen uur ideaal zijn voor één sport.
export const KEUZES = [
  { waarde: 'alles', naam: 'Alles' },
  { waarde: 'G', naam: 'Ideale golfsurfdag', kleur: '#2a6fdb' },
  { waarde: 'S', naam: 'Ideale windsurfdag', kleur: '#14b8d4' },
  { waarde: 'O', naam: 'Windsurfen op golven', kleur: '#f5c400' },
  { waarde: 'R', naam: 'Ideale stille waters', kleur: '#8a949c' },
] as const
export const surfFilter = { keuze: 'alles' as string }
try { Object.assign(surfFilter, JSON.parse(localStorage.getItem(SLEUTEL) ?? '{}')) } catch { /* standaard */ }

// Telt dit strand mee? letter = conclusie-letter van het gekozen uur (hoofdletter = ideaal).
export const toont = (letter: string) => surfFilter.keuze === 'alles' || letter === surfFilter.keuze

const voorbeeld = (w: number, v: number, rood = 0) => {
  const d = bolletjeWW(w, v, 30, false, rood)
  const c = document.createElement('canvas'); c.width = d.width; c.height = d.height
  c.getContext('2d')!.putImageData(d, 0, 0)
  return `<img src="${c.toDataURL()}" width="30" height="30" alt="">`
}

export function surfPaneel(opnieuw: () => void) {
  const knop = document.createElement('button')
  knop.className = 'laagknop surf'
  knop.textContent = surfFilter.keuze === 'alles' ? 'Surfen'
    : `Surfen · ${KEUZES.find((k) => k.waarde === surfFilter.keuze)?.naam.replace(/^Ideale /, '') ?? ''}`
  knop.setAttribute('aria-expanded', 'false')
  const p = document.createElement('div')
  p.className = 'klimpaneel surfpaneel'
  p.hidden = true
  const houder = document.getElementById('laagknoppen')!
  houder.prepend(knop)
  document.getElementById('kaart')!.append(p)
  knop.onclick = () => {
    // Eén paneel tegelijk open.
    document.querySelectorAll<HTMLElement>('.klimpaneel').forEach((x) => { if (x !== p) x.hidden = true })
    document.querySelectorAll('#laagknoppen button').forEach((b) => { if (b !== knop) b.setAttribute('aria-expanded', 'false') })
    p.hidden = !p.hidden; knop.setAttribute('aria-expanded', String(!p.hidden)); if (!p.hidden) vul()
  }
  const bewaar = () => { try { localStorage.setItem(SLEUTEL, JSON.stringify(surfFilter)) } catch { /* niet bewaard */ } }
  const NIVEAU = ['niets', 'ideaal, ook voor beginners', 'sterk, ervaring nodig', 'te sterk']
  const vul = () => {
    p.innerHTML = `
      <fieldset class="keuzes"><legend>Toon</legend>
        ${KEUZES.map((k) => `<label style="--kleur:${'kleur' in k ? k.kleur : 'transparent'}"><input type="radio" name="surfkeuze" value="${k.waarde}"
          ${surfFilter.keuze === k.waarde ? 'checked' : ''}>${'kleur' in k ? '<i></i>' : ''} ${k.naam}</label>`).join('')}
        <p class="klein">Ideaal op het gekozen dag en uur (schuifbalk bovenaan).</p>
      </fieldset>
      <fieldset class="uitleg"><legend>Zo lees je een bolletje</legend>
        <p>${voorbeeld(2, 3)}<span>Links <b>WIND</b>, rechts <b>WAVE</b> (golf op zee).</span></p>
        <ol class="niveaus">${NIVEAU.map((n, i) => `<li><b>${i + 1}</b> ${n}</li>`).join('')}</ol>
        <p>${voorbeeld(2, 2, 1)}<span>Rode rand links: wind van land.</span></p>
        <p>${voorbeeld(2, 2, 2)}<span>Rode rand rechts: genoeg golf op zee, maar die komt hier niet aan.</span></p>
        <p class="klein">Een getal in een wit bolletje is het aantal stranden. Tik op een strand voor de fiche.</p>
      </fieldset>`
    p.querySelectorAll<HTMLInputElement>('input[name=surfkeuze]').forEach((i) => i.onchange = () => {
      surfFilter.keuze = i.value; bewaar(); opnieuw()
      knop.textContent = i.value === 'alles' ? 'Surfen' : `Surfen · ${KEUZES.find((k) => k.waarde === i.value)!.naam.replace(/^Ideale /, '')}`
    })
  }
}
