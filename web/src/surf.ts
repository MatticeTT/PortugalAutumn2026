// Knop "Surfen" op de kaart, zoals "Klimmen": uitleg bij de bolletjes en filters.
// De filters gelden voor het gekozen uur en blijven in deze browser bewaard.
import { bolletjeWW } from './kleuren'

export const SPORTEN = [
  { letter: 'G', naam: 'golfsurfen', kleur: '#2a6fdb' },
  { letter: 'O', naam: 'windsurfen op golven', kleur: '#f5c400' },
  { letter: 'S', naam: 'windsurfen', kleur: '#14b8d4' },
  { letter: 'R', naam: 'stille waters', kleur: '#8a949c' },
] as const

const SLEUTEL = 'surf-filter-v1'
export const surfFilter = {
  aan: true, // laag Surfen tonen
  alleenIdeaal: false, // alleen stranden die dit uur ideaal zijn voor een aangevinkte sport
  G: true, O: true, S: true, R: true,
  wave: [true, true, true, true], // WAVE 1–4
  wind: [true, true, true, true], // WIND 1–4
  zonderRood: false, // rood omkaderde stranden verbergen
}
try { Object.assign(surfFilter, JSON.parse(localStorage.getItem(SLEUTEL) ?? '{}')) } catch { /* standaard */ }

// Telt dit strand mee met de filters? w, v = WIND, WAVE (0 = geen gegevens), rood = 0–3, letter = conclusie-letter.
export function toont(w: number, v: number, rood: string, letter: string) {
  const f = surfFilter
  if (!f.aan) return false
  if (f.alleenIdeaal && !(SPORTEN.some((s) => s.letter === letter && (f as any)[s.letter]))) return false
  if (w > 0 && !f.wind[w - 1]) return false
  if (v > 0 && !f.wave[v - 1]) return false
  if (f.zonderRood && rood !== '0') return false
  return true
}

const voorbeeld = (w: number, v: number, rood = 0) => {
  const d = bolletjeWW(w, v, 30, false, rood)
  const c = document.createElement('canvas'); c.width = d.width; c.height = d.height
  c.getContext('2d')!.putImageData(d, 0, 0)
  return `<img src="${c.toDataURL()}" width="30" height="30" alt="">`
}

export function surfPaneel(opnieuw: () => void) {
  const knop = document.createElement('button')
  knop.className = 'laagknop surf'
  knop.textContent = 'Surfen'
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
    const f = surfFilter
    const vak = (k: string, aan: boolean, tekst: string) => `<label><input type="checkbox" data-f="${k}" ${aan ? 'checked' : ''}> ${tekst}</label>`
    p.innerHTML = `
      <label class="rij"><input type="checkbox" data-f="aan" ${f.aan ? 'checked' : ''}> <b>Laag Surfen tonen</b></label>
      <fieldset class="uitleg"><legend>Zo lees je een bolletje</legend>
        <p>${voorbeeld(2, 3)}<span>Links <b>WIND</b>, rechts <b>WAVE</b> (golf op zee).</span></p>
        <ol class="niveaus">${NIVEAU.map((n, i) => `<li><b>${i + 1}</b> ${n}</li>`).join('')}</ol>
        <p>${voorbeeld(2, 2, 1)}<span>Rode rand links: wind van land.</span></p>
        <p>${voorbeeld(2, 2, 2)}<span>Rode rand rechts: genoeg golf op zee, maar die komt hier niet aan.</span></p>
        <p class="klein">Een getal in een wit bolletje is het aantal stranden. Tik op een strand voor de fiche.</p>
      </fieldset>
      <fieldset><legend>Toon</legend>
        <label><input type="radio" name="ideaal" value="0" ${f.alleenIdeaal ? '' : 'checked'}> alle stranden</label>
        <label><input type="radio" name="ideaal" value="1" ${f.alleenIdeaal ? 'checked' : ''}> alleen ideaal dit uur</label>
      </fieldset>
      <fieldset ${f.alleenIdeaal ? '' : 'disabled'} class="sporten"><legend>Ideaal voor</legend>
        ${SPORTEN.map((s) => `<label style="--kleur:${s.kleur}"><input type="checkbox" data-f="${s.letter}" ${(f as any)[s.letter] ? 'checked' : ''}><i></i> ${s.naam}</label>`).join('')}
      </fieldset>
      <fieldset><legend>WAVE</legend>${[1, 2, 3, 4].map((n) => vak(`wave${n}`, f.wave[n - 1], String(n))).join('')}</fieldset>
      <fieldset><legend>WIND</legend>${[1, 2, 3, 4].map((n) => vak(`wind${n}`, f.wind[n - 1], String(n))).join('')}</fieldset>
      <fieldset><legend>Richting</legend>${vak('zonderRood', f.zonderRood, 'verberg stranden met een rode rand')}</fieldset>`
    p.querySelectorAll<HTMLInputElement>('input[data-f]').forEach((i) => i.onchange = () => {
      const k = i.dataset.f!
      const m = /^(wave|wind)(\d)$/.exec(k)
      if (m) (f as any)[m[1]][Number(m[2]) - 1] = i.checked
      else (f as any)[k] = i.checked
      bewaar(); opnieuw()
    })
    p.querySelectorAll<HTMLInputElement>('input[name=ideaal]').forEach((i) => i.onchange = () => {
      f.alleenIdeaal = i.value === '1'; bewaar(); opnieuw(); vul()
    })
  }
}
