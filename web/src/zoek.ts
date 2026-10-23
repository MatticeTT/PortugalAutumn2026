// Zoeken op naam van een strand of spot: kies er een, dan gaat de kaart erheen en opent de fiche (zoals in de eerste
// versie van de app).

import { esc, type SpotIndex, type SpotKort } from './spots'

const MAX = 8
// Zonder hoofdletters en accenten: "sao" vindt "São", "rocha" vindt "Praia da Rocha".
const plat = (s: string) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()

function zoek(spots: SpotKort[], q: string): SpotKort[] {
  const w = plat(q).trim().split(/\s+/).filter(Boolean)
  if (!w.length) return []
  const kern = (s: SpotKort) => plat(s.naam).replace(/^praia( d[aoe]s?)? /, '')
  return spots.filter((s) => w.every((x) => plat(s.naam).includes(x)))
    .sort((a, b) => Number(!kern(a).startsWith(w[0])) - Number(!kern(b).startsWith(w[0])) || a.naam.localeCompare(b.naam, 'pt'))
    .slice(0, MAX)
}

export function zoekveld(data: () => SpotIndex | null, kies: (s: SpotKort) => void) {
  const veld = document.getElementById('zoek') as HTMLInputElement
  const lijst = document.getElementById('zoeklijst') as HTMLUListElement
  let res: SpotKort[] = []
  let actief = -1
  const toon = () => {
    lijst.innerHTML = res.length
      ? res.map((s, k) => `<li role="option" id="z${k}" data-k="${k}" aria-selected="${k === actief}"><b>${esc(s.naam)}</b></li>`).join('')
      : '<li class="niets">Geen strand gevonden</li>'
    lijst.hidden = !veld.value.trim()
    veld.setAttribute('aria-expanded', String(!lijst.hidden))
  }
  const kiesUit = (s: SpotKort) => {
    veld.value = ''
    res = []
    lijst.hidden = true
    veld.blur()
    kies(s)
  }
  veld.addEventListener('input', () => { res = zoek(data()?.spots ?? [], veld.value); actief = res.length ? 0 : -1; toon() })
  veld.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowDown' && res.length) { actief = (actief + 1) % res.length; toon(); e.preventDefault() }
    else if (e.key === 'ArrowUp' && res.length) { actief = (actief - 1 + res.length) % res.length; toon(); e.preventDefault() }
    else if (e.key === 'Enter' && res[actief]) { kiesUit(res[actief]); e.preventDefault() }
    else if (e.key === 'Escape') { veld.value = ''; res = []; lijst.hidden = true }
  })
  lijst.addEventListener('pointerdown', (e) => {
    const li = (e.target as HTMLElement).closest<HTMLElement>('li[data-k]')
    if (li) { e.preventDefault(); kiesUit(res[Number(li.dataset.k)]) }
  })
  veld.addEventListener('blur', () => setTimeout(() => { lijst.hidden = true }, 150))
}
