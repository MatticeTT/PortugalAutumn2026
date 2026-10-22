// Profiel: bewaard in deze browser (later te delen via een account). Alles is optioneel.

import { PLANKEN } from './spots'

export interface Profiel {
  gewicht: number | null // kg
  verblijf: { naam: string; lat: number; lon: number } | null
  planken: string[] // eigen planken (codes uit PLANKEN)
  wetsuits: string[]
  reistijd: number | null // minuten, hoogstens
}

export const WETSUITS = ['shorty 2 mm', '3/2 mm', '4/3 mm', '5/4 mm', '6/5 mm']
const LEEG: Profiel = { gewicht: null, verblijf: null, planken: [], wetsuits: [], reistijd: null }

export function laadProfiel(): Profiel {
  try {
    return { ...LEEG, ...JSON.parse(localStorage.getItem('profiel') ?? '{}') }
  } catch {
    return { ...LEEG }
  }
}

function bewaar(p: Profiel) {
  try { localStorage.setItem('profiel', JSON.stringify(p)) } catch { /* privévenster */ }
}

/** Afstand in km in rechte lijn. */
export function hemelsbreed(a: { lat: number; lon: number }, b: { lat: number; lon: number }) {
  const r = Math.PI / 180
  const x = Math.sin(((b.lat - a.lat) * r) / 2) ** 2 + Math.cos(a.lat * r) * Math.cos(b.lat * r) * Math.sin(((b.lon - a.lon) * r) / 2) ** 2
  return 2 * 6371 * Math.asin(Math.sqrt(x))
}

export function toonProfiel(box: HTMLElement, opNieuw: (p: Profiel) => void) {
  const p = laadProfiel()
  const vink = (naam: string, waarde: string, aan: boolean, label: string) =>
    `<label class="vink"><input type="checkbox" name="${naam}" value="${waarde}" ${aan ? 'checked' : ''}> ${label}</label>`
  box.innerHTML = `<h2>Profiel</h2>
    <p class="zacht">Bewaard op dit toestel. Alles is optioneel.</p>
    <label class="veld">Gewicht (kg)<input name="gewicht" type="number" min="20" max="200" inputmode="numeric" value="${p.gewicht ?? ''}"></label>
    <div class="veld">Verblijfplaats
      <div class="rij"><input name="zoek" type="search" placeholder="Plaats of adres" value="${p.verblijf?.naam ?? ''}"><button type="button" class="laag" id="zoek">Zoek</button></div>
      <button type="button" class="laag" id="hier">Mijn huidige locatie</button>
      <div class="zacht" id="verblijf">${p.verblijf ? `${p.verblijf.naam} (${p.verblijf.lat.toFixed(3)}, ${p.verblijf.lon.toFixed(3)})` : 'nog niet gekozen'}</div>
    </div>
    <div class="veld">Mijn planken<div class="vinken">${Object.entries(PLANKEN).map(([k, n]) => vink('planken', k, p.planken.includes(k), n)).join('')}</div></div>
    <div class="veld">Mijn wetsuits<div class="vinken">${WETSUITS.map((w) => vink('wetsuits', w, p.wetsuits.includes(w), w)).join('')}</div></div>
    <label class="veld">Hoogstens reistijd (minuten)<input name="reistijd" type="number" min="0" max="600" inputmode="numeric" value="${p.reistijd ?? ''}"></label>
    <p class="zacht">Reistijd en route: volgt (routeplanner nog aan te sluiten).</p>`
  const lees = () => {
    const f = (n: string) => box.querySelector<HTMLInputElement>(`[name=${n}]`)!
    const getal = (n: string) => (f(n).value ? Number(f(n).value) : null)
    p.gewicht = getal('gewicht')
    p.reistijd = getal('reistijd')
    p.planken = [...box.querySelectorAll<HTMLInputElement>('[name=planken]:checked')].map((x) => x.value)
    p.wetsuits = [...box.querySelectorAll<HTMLInputElement>('[name=wetsuits]:checked')].map((x) => x.value)
    bewaar(p)
    opNieuw(p)
  }
  const zetVerblijf = (naam: string, lat: number, lon: number) => {
    p.verblijf = { naam, lat, lon }
    box.querySelector('#verblijf')!.textContent = `${naam} (${lat.toFixed(3)}, ${lon.toFixed(3)})`
    lees()
  }
  box.addEventListener('change', lees)
  box.querySelector('#zoek')!.addEventListener('click', async () => {
    const q = box.querySelector<HTMLInputElement>('[name=zoek]')!.value.trim()
    if (!q) return
    const el = box.querySelector('#verblijf')!
    el.textContent = 'zoeken…'
    try {
      // OpenStreetMap Nominatim (gebruiksregels: weinig vragen, met bronvermelding)
      const r = await fetch(`https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&q=${encodeURIComponent(q)}`)
      const [x] = await r.json()
      if (x) zetVerblijf(x.display_name.split(',').slice(0, 2).join(','), Number(x.lat), Number(x.lon))
      else el.textContent = 'niet gevonden'
    } catch {
      el.textContent = 'zoeken lukt niet (geen verbinding?)'
    }
  })
  box.querySelector('#hier')!.addEventListener('click', () => {
    navigator.geolocation?.getCurrentPosition(
      (pos) => zetVerblijf('Huidige locatie', pos.coords.latitude, pos.coords.longitude),
      () => (box.querySelector('#verblijf')!.textContent = 'locatie niet beschikbaar'),
    )
  })
}
