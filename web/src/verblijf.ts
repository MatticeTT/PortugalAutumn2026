// Het verblijf van de bezoeker: waar je verblijft en hoe lang je wil rijden (eigenaar, 8 oktober 2026).
// - plaats zoeken: Nominatim (OpenStreetMap), of je huidige locatie
// - rijtijden en routes: OSRM (router.project-osrm.org), rechtstreeks vanuit de browser
// Het verblijf wordt in deze browser bewaard; kaart en planning rekenen er vanaf dan mee.

export interface Verblijf { naam: string; lat: number; lon: number; max: number } // max in minuten
export interface Plek { id: string; lat: number; lon: number }

const SLEUTEL = 'verblijf-v1'
const OSRM = 'https://router.project-osrm.org'
const NOMINATIM = 'https://nominatim.openstreetmap.org/search'
export const RIJTIJDEN = [30, 45, 60, 90, 120, 180]

export function leesVerblijf(): Verblijf | null {
  try {
    const v = JSON.parse(localStorage.getItem(SLEUTEL) ?? 'null')
    return v && Number.isFinite(v.lat) && Number.isFinite(v.lon) && Number.isFinite(v.max) ? v : null
  } catch { return null }
}
export function bewaarVerblijf(v: Verblijf) {
  try { localStorage.setItem(SLEUTEL, JSON.stringify(v)) } catch { /* niet bewaard */ }
}

export const rijTekst = (m: number) => m < 60 ? `${m} min` : `${Math.floor(m / 60)}u${m % 60 ? String(m % 60).padStart(2, '0') : ''}`

export async function zoekPlaats(q: string): Promise<{ naam: string; lat: number; lon: number }[]> {
  const url = `${NOMINATIM}?format=json&countrycodes=pt&limit=6&accept-language=nl&q=${encodeURIComponent(q)}`
  const r = await fetch(url)
  if (!r.ok) throw new Error(`Nominatim ${r.status}`)
  return (await r.json()).map((x: any) => ({ naam: x.display_name as string, lat: Number(x.lat), lon: Number(x.lon) }))
}

function km(a: { lat: number; lon: number }, b: { lat: number; lon: number }) {
  const r = 6371, t = Math.PI / 180
  const dp = (b.lat - a.lat) * t, dl = (b.lon - a.lon) * t
  const h = Math.sin(dp / 2) ** 2 + Math.cos(a.lat * t) * Math.cos(b.lat * t) * Math.sin(dl / 2) ** 2
  return 2 * r * Math.asin(Math.sqrt(h))
}

// Rijtijd (minuten) van het verblijf naar elke plek. Plekken die in vogelvlucht al verder liggen dan je
// met 130 km/h in de maximale tijd haalt, worden niet opgevraagd (die vallen zeker af). Resultaten blijven
// in deze browser bewaard per verblijf.
const geheugen = new Map<string, number | null>()
const cacheSleutel = (v: Verblijf) => `rij-v1:${v.lat.toFixed(4)},${v.lon.toFixed(4)}`
function laadCache(v: Verblijf) {
  try { return JSON.parse(localStorage.getItem(cacheSleutel(v)) ?? '{}') as Record<string, number | null> } catch { return {} }
}
function bewaarCache(v: Verblijf, c: Record<string, number | null>) {
  try { localStorage.setItem(cacheSleutel(v), JSON.stringify(c)) } catch { /* niet bewaard */ }
}

export async function rijtijden(v: Verblijf, plekken: Plek[]): Promise<Map<string, number | null>> {
  const cache = laadCache(v)
  const uit = new Map<string, number | null>()
  const vragen: Plek[] = []
  for (const p of plekken) {
    const k = `${p.id}`
    if (k in cache) { uit.set(p.id, cache[k]); continue }
    if (km(v, p) > (v.max / 60) * 130) { uit.set(p.id, null); continue } // te ver, ook in vogelvlucht
    vragen.push(p)
  }
  for (let i = 0; i < vragen.length; i += 90) {
    const deel = vragen.slice(i, i + 90)
    const coords = [v, ...deel].map((p) => `${p.lon.toFixed(5)},${p.lat.toFixed(5)}`).join(';')
    const r = await fetch(`${OSRM}/table/v1/driving/${coords}?sources=0&annotations=duration`)
    if (!r.ok) throw new Error(`OSRM ${r.status}`)
    const d = await r.json()
    deel.forEach((p, k) => {
      const s = d.durations?.[0]?.[k + 1]
      const m = s == null ? null : Math.round(s / 60)
      uit.set(p.id, m); cache[p.id] = m
    })
  }
  bewaarCache(v, cache)
  for (const [k, m] of uit) geheugen.set(k, m)
  return uit
}

const routes = new Map<string, any>()
export async function route(v: Verblijf, p: Plek): Promise<any | null> {
  const k = `${v.lat},${v.lon}>${p.id}`
  if (routes.has(k)) return routes.get(k)
  const r = await fetch(`${OSRM}/route/v1/driving/${v.lon},${v.lat};${p.lon},${p.lat}?overview=simplified&geometries=geojson`)
  if (!r.ok) return null
  const g = (await r.json()).routes?.[0]?.geometry ?? null
  routes.set(k, g)
  return g
}

// Het venster met de twee vragen. Geeft het gekozen verblijf terug (of null bij sluiten zonder keuze).
export function vraagVerblijf(huidig: Verblijf | null): Promise<Verblijf | null> {
  return new Promise((klaar) => {
    const d = document.createElement('dialog')
    d.className = 'verblijfvraag'
    let gekozen: { naam: string; lat: number; lon: number } | null = huidig
    d.innerHTML = `<form method="dialog">
      <h2>Waar verblijf je?</h2>
      <div class="zoekrij"><input name="q" type="search" placeholder="bv. Ferragudo, Lagos, Sagres" autocomplete="off" value="${huidig ? huidig.naam.split(',')[0].replace(/"/g, '&quot;') : ''}">
        <button type="button" class="knop" data-a="zoek">Zoek</button></div>
      <button type="button" class="linkknop" data-a="hier">Gebruik mijn huidige locatie</button>
      <ul class="gevonden"></ul>
      <p class="keuze">${huidig ? `Gekozen: <b>${huidig.naam.split(',').slice(0, 2).join(',')}</b>` : ''}</p>
      <h2>Hoe lang wil je rijden?</h2>
      <div class="tijden">${RIJTIJDEN.map((m) => `<label><input type="radio" name="max" value="${m}" ${(huidig?.max ?? 120) === m ? 'checked' : ''}> ${rijTekst(m)}</label>`).join('')}</div>
      <p class="fout" hidden></p>
      <div class="knoppen"><button value="sluit" class="linkknop">Overslaan</button><button value="ok" class="knop hoofd">Toon de kaart</button></div>
    </form>`
    document.body.appendChild(d)
    const veld = d.querySelector<HTMLInputElement>('input[name=q]')!
    const lijst = d.querySelector('.gevonden')!
    const keuze = d.querySelector('.keuze')!
    const fout = d.querySelector<HTMLElement>('.fout')!
    const toonFout = (t: string) => { fout.textContent = t; fout.hidden = !t }
    const kies = (g: { naam: string; lat: number; lon: number }) => {
      gekozen = g; lijst.innerHTML = ''
      keuze.innerHTML = `Gekozen: <b>${g.naam.split(',').slice(0, 2).join(',')}</b>`
      toonFout('')
    }
    const zoek = async () => {
      if (!veld.value.trim()) return
      lijst.innerHTML = '<li class="rustig">Zoeken…</li>'
      try {
        const r = await zoekPlaats(veld.value.trim())
        lijst.innerHTML = r.length ? '' : '<li class="rustig">Niets gevonden in Portugal.</li>'
        r.forEach((g) => {
          const li = document.createElement('li')
          li.innerHTML = `<button type="button">${g.naam.replace(/</g, '&lt;')}</button>`
          li.querySelector('button')!.onclick = () => kies(g)
          lijst.appendChild(li)
        })
      } catch { lijst.innerHTML = ''; toonFout('Zoeken lukt nu niet (OpenStreetMap). Probeer opnieuw of gebruik je locatie.') }
    }
    d.querySelector<HTMLButtonElement>('[data-a=zoek]')!.onclick = zoek
    veld.onkeydown = (e) => { if (e.key === 'Enter') { e.preventDefault(); zoek() } }
    d.querySelector<HTMLButtonElement>('[data-a=hier]')!.onclick = () => {
      navigator.geolocation?.getCurrentPosition(
        (pos) => kies({ naam: 'Mijn locatie', lat: pos.coords.latitude, lon: pos.coords.longitude }),
        () => toonFout('Je locatie is niet beschikbaar.'))
    }
    d.addEventListener('close', () => {
      const max = Number((d.querySelector<HTMLInputElement>('input[name=max]:checked'))?.value ?? 120)
      const ok = d.returnValue === 'ok' && gekozen
      d.remove()
      klaar(ok ? { ...gekozen!, max } : null)
    })
    d.querySelector('form')!.addEventListener('submit', (e) => {
      if ((e as SubmitEvent).submitter?.getAttribute('value') === 'ok' && !gekozen) { e.preventDefault(); toonFout('Kies eerst een plaats.') }
    })
    d.showModal()
  })
}
