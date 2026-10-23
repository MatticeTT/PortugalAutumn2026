// Zoeken zoals Google Maps: eerst stranden en spots met die naam, daarna plaatsen en adressen overal ter wereld
// (dezelfde zoekdienst als bij het verblijf). Een strand opent de fiche; een plaats zet de kaart daar, met de
// stranden in de buurt.

import { esc, type SpotIndex, type SpotKort } from './spots'
import { plaatsVan, zoekPlaats, type Gevonden } from './verblijf'

const MAX_SPOTS = 5
const MAX_PLAATSEN = 5
// Zonder hoofdletters en accenten: "sao" vindt "São", "rocha" vindt "Praia da Rocha".
const plat = (s: string) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()

function zoekSpots(spots: SpotKort[], q: string): SpotKort[] {
  const w = plat(q).trim().split(/\s+/).filter(Boolean)
  if (!w.length) return []
  const kern = (s: SpotKort) => plat(s.naam).replace(/^praia( d[aoe]s?)? /, '')
  return spots.filter((s) => w.every((x) => plat(s.naam).includes(x)))
    .sort((a, b) => Number(!kern(a).startsWith(w[0])) - Number(!kern(b).startsWith(w[0])) || a.naam.localeCompare(b.naam, 'pt'))
    .slice(0, MAX_SPOTS)
}

type Res = { spot: SpotKort } | { plaats: Gevonden }

export function zoekveld(data: () => SpotIndex | null, kies: (s: SpotKort) => void, kiesPlek: (g: Gevonden) => void) {
  const veld = document.getElementById('zoek') as HTMLInputElement
  const lijst = document.getElementById('zoeklijst') as HTMLUListElement
  let res: Res[] = []
  let actief = -1
  let bezig = false
  let klok = 0
  let vraag: AbortController | null = null

  const toon = () => {
    const li = res.map((r, k) => 'spot' in r
      ? `<li role="option" id="z${k}" data-k="${k}" aria-selected="${k === actief}"><b><span class="zi" aria-hidden="true">🏄</span>${esc(r.spot.naam)}</b></li>`
      : `<li role="option" id="z${k}" data-k="${k}" aria-selected="${k === actief}"><b><span class="zi" aria-hidden="true">📍</span>${esc(r.plaats.titel)}</b>${r.plaats.adres ? `<small>${esc(r.plaats.adres)}</small>` : ''}</li>`)
    lijst.innerHTML = li.length ? li.join('') + (bezig ? '<li class="niets">Plaatsen zoeken…</li>' : '')
      : `<li class="niets">${bezig ? 'Zoeken…' : 'Niets gevonden'}</li>`
    lijst.hidden = !veld.value.trim()
    veld.setAttribute('aria-expanded', String(!lijst.hidden))
  }
  const sluit = () => {
    veld.value = ''
    res = []
    lijst.hidden = true
    vraag?.abort()
    veld.blur()
  }
  const kiesUit = async (r: Res) => {
    sluit()
    if ('spot' in r) return kies(r.spot)
    try { kiesPlek(await plaatsVan(r.plaats)) } catch { /* plaats niet gevonden: niets doen */ }
  }
  veld.addEventListener('input', () => {
    const q = veld.value.trim()
    const spots: Res[] = zoekSpots(data()?.spots ?? [], q).map((spot) => ({ spot }))
    res = spots
    actief = res.length ? 0 : -1
    vraag?.abort()
    clearTimeout(klok)
    bezig = q.length >= 2
    toon()
    if (!bezig) return
    // Plaatsen pas na een korte pauze in het typen.
    klok = window.setTimeout(async () => {
      vraag = new AbortController()
      try {
        const p = (await zoekPlaats(q, vraag.signal)).slice(0, MAX_PLAATSEN).map((plaats) => ({ plaats }))
        if (veld.value.trim() !== q) return
        res = [...spots, ...p]
        if (actief < 0 && res.length) actief = 0
      } catch (e) {
        if ((e as Error).name === 'AbortError') return
      }
      bezig = false
      toon()
    }, 250)
  })
  veld.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowDown' && res.length) { actief = (actief + 1) % res.length; toon(); e.preventDefault() }
    else if (e.key === 'ArrowUp' && res.length) { actief = (actief - 1 + res.length) % res.length; toon(); e.preventDefault() }
    else if (e.key === 'Enter' && res[actief]) { kiesUit(res[actief]); e.preventDefault() }
    else if (e.key === 'Escape') sluit()
  })
  lijst.addEventListener('pointerdown', (e) => {
    const li = (e.target as HTMLElement).closest<HTMLElement>('li[data-k]')
    if (li) { e.preventDefault(); kiesUit(res[Number(li.dataset.k)]) }
  })
  veld.addEventListener('blur', () => setTimeout(() => { lijst.hidden = true }, 150))
}
