// Zoeken op naam van een strand (of de gemeente/het district): kies er een, dan gaat de kaart erheen
// en opent de fiche.
import { openFiche } from './fiche'
import { staat, vliegNaar } from './main'
import type { KaartStrand } from './types'

const MAX = 8
// Zonder hoofdletters en accenten: "sao" vindt "São", "rocha" vindt "Praia da Rocha".
const plat = (s: string) => s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase()
const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]!)

function zoek(q: string): KaartStrand[] {
  const w = plat(q).trim().split(/\s+/).filter(Boolean)
  if (!w.length) return []
  const treffers = staat.stranden.filter((s) => {
    const t = plat(`${s.n} ${s.d ?? ''}`)
    return w.every((x) => t.includes(x))
  })
  // Eerst namen die met de zoekterm beginnen (na "Praia d.."), dan de rest, alfabetisch.
  const kern = (s: KaartStrand) => plat(s.n).replace(/^praia( d[aoe]s?)? /, '')
  const begint = (s: KaartStrand) => (kern(s).startsWith(w[0]) || plat(s.n).startsWith(w[0]) ? 0 : 1)
  return treffers.sort((a, b) => begint(a) - begint(b) || a.n.localeCompare(b.n, 'pt')).slice(0, MAX)
}

export function zoekveld() {
  const veld = document.getElementById('zoek') as HTMLInputElement
  const lijst = document.getElementById('zoeklijst') as HTMLUListElement
  let res: KaartStrand[] = []
  let actief = -1

  const toon = () => {
    lijst.innerHTML = res.length
      ? res.map((s, k) => `<li role="option" id="z${k}" data-k="${k}" aria-selected="${k === actief}">
          <b>${esc(s.n)}</b>${s.d ? `<small>${esc(s.d)}</small>` : ''}</li>`).join('')
      : '<li class="niets">Geen strand gevonden</li>'
    lijst.hidden = !veld.value.trim()
    veld.setAttribute('aria-expanded', String(!lijst.hidden))
    veld.setAttribute('aria-activedescendant', actief >= 0 ? `z${actief}` : '')
  }
  const kies = (s: KaartStrand) => {
    veld.value = ''
    res = []
    lijst.hidden = true
    veld.setAttribute('aria-expanded', 'false')
    veld.blur()
    vliegNaar(s.x, s.y, true)
    openFiche(s.id)
  }

  veld.addEventListener('input', () => { res = zoek(veld.value); actief = res.length ? 0 : -1; toon() })
  veld.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowDown' && res.length) { actief = (actief + 1) % res.length; toon(); e.preventDefault() }
    else if (e.key === 'ArrowUp' && res.length) { actief = (actief - 1 + res.length) % res.length; toon(); e.preventDefault() }
    else if (e.key === 'Enter' && res[actief]) { kies(res[actief]); e.preventDefault() }
    else if (e.key === 'Escape') { veld.value = ''; res = []; lijst.hidden = true; e.stopPropagation() }
  })
  // pointerdown: kiezen vóór het veld de focus verliest.
  lijst.addEventListener('pointerdown', (e) => {
    const li = (e.target as HTMLElement).closest<HTMLElement>('li[data-k]')
    if (li) { e.preventDefault(); kies(res[Number(li.dataset.k)]) }
  })
  veld.addEventListener('blur', () => setTimeout(() => { lijst.hidden = true }, 150))
  veld.addEventListener('focus', () => { if (veld.value.trim()) toon() })
}
