// Het verblijf van de bezoeker: waar je verblijft en hoe lang je wil rijden (eigenaar, 8 oktober 2026).
// - plaats zoeken terwijl je typt (zoals Google Maps): Photon (komoot, op OpenStreetMap), met Nominatim als reserve;
//   of je huidige locatie
// - rijtijden en routes: OSRM (router.project-osrm.org), rechtstreeks vanuit de browser
// Het verblijf wordt in deze browser bewaard; kaart en planning rekenen er vanaf dan mee.

export interface Verblijf { naam: string; lat: number; lon: number; max: number } // max in minuten
export interface Plek { id: string; lat: number; lon: number }

const SLEUTEL = 'verblijf-v1'
const OSRM = 'https://router.project-osrm.org'
const NOMINATIM = 'https://nominatim.openstreetmap.org/search'
const PHOTON = 'https://photon.komoot.io/api/'

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

export interface Gevonden { naam: string; lat: number; lon: number; titel: string; adres: string; id?: string }

// Suggesties terwijl je typt (zoals Google Maps): eerst Google Places via onze eigen Vercel-functie /api/plaats
// (vindt ook hotels en vakantieappartementen); werkt die niet (nog geen sleutel), dan Photon (OpenStreetMap).
// Antwoorden worden onthouden, zodat terugtypen meteen gaat.
let googleWerkt: boolean | null = null
const bewaard = new Map<string, Gevonden[]>()
export const nieuweSessie = () => (crypto.randomUUID?.() ?? String(Math.random()).slice(2))

async function viaGoogle(q: string, sessie: string, signal?: AbortSignal): Promise<Gevonden[] | null> {
  if (googleWerkt === false) return null
  const r = await fetch(`/api/plaats?q=${encodeURIComponent(q)}&s=${sessie}`, { signal })
  const type = r.headers.get('content-type') ?? ''
  if (!r.ok || !type.includes('json')) { googleWerkt = false; return null }
  googleWerkt = true
  return (await r.json()).map((x: { id: string; titel: string; adres: string }) =>
    ({ ...x, naam: [x.titel, x.adres].filter(Boolean).join(', '), lat: NaN, lon: NaN }))
}

async function viaPhoton(q: string, signal?: AbortSignal): Promise<Gevonden[]> {
  const url = `${PHOTON}?q=${encodeURIComponent(q)}&limit=8&lat=37.12&lon=-8.5&bbox=-9.6,36.9,-6.1,42.2`
  const r = await fetch(url, { signal })
  if (!r.ok) throw new Error(`Photon ${r.status}`)
  return (await r.json()).features.map((f: any) => {
    const p = f.properties ?? {}
    const straat = [p.street, p.housenumber].filter(Boolean).join(' ')
    const titel = p.name || straat || p.city || q
    const plaats = [p.postcode, p.city || p.town || p.village || p.district].filter(Boolean).join(' ')
    const adres = [p.name && straat, plaats !== titel && plaats, p.state].filter(Boolean).join(', ')
    return { titel, adres, naam: [titel, plaats].filter(Boolean).join(', '), lon: f.geometry.coordinates[0], lat: f.geometry.coordinates[1] }
  })
}

export async function zoekPlaats(q: string, sessie: string, signal?: AbortSignal): Promise<Gevonden[]> {
  const k = q.toLowerCase()
  if (bewaard.has(k)) return bewaard.get(k)!
  let r: Gevonden[] | null = null
  try { r = await viaGoogle(q, sessie, signal) } catch (e) { if ((e as Error).name === 'AbortError') throw e }
  if (r == null) {
    try { r = await viaPhoton(q, signal) } catch (e) {
      if ((e as Error).name === 'AbortError') throw e
      const n = await fetch(`${NOMINATIM}?format=json&countrycodes=pt&limit=6&accept-language=nl&q=${encodeURIComponent(q)}`, { signal })
      if (!n.ok) throw new Error(`Nominatim ${n.status}`)
      r = (await n.json()).map((x: any) => {
        const delen = String(x.display_name).split(', ')
        return { naam: x.display_name, titel: delen[0], adres: delen.slice(1, 4).join(', '), lat: Number(x.lat), lon: Number(x.lon) }
      })
    }
  }
  bewaard.set(k, r!)
  return r!
}

// Een Google-suggestie heeft nog geen coördinaten: die komen pas bij het kiezen (zelfde sessie = goedkoper).
export async function plaatsVan(g: Gevonden, sessie: string): Promise<Gevonden> {
  if (!g.id || Number.isFinite(g.lat)) return g
  const r = await fetch(`/api/plaats?id=${encodeURIComponent(g.id)}&s=${sessie}`)
  if (!r.ok) throw new Error(`plaats ${r.status}`)
  const p = await r.json()
  return { ...g, naam: [g.titel, g.adres].filter(Boolean).join(', '), lat: p.lat, lon: p.lon }
}

// Rijtijd (minuten) over de weg van het verblijf naar elke plek, voor alle plekken (geen vogelvlucht).
// Resultaten blijven in deze browser bewaard per verblijf.
const geheugen = new Map<string, number | null>()
const cacheSleutel = (v: Verblijf) => `rij-v2:${v.lat.toFixed(4)},${v.lon.toFixed(4)}`
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
      <div class="zoekrij"><input name="q" type="search" placeholder="Adres, hotel, straat of dorp" autocomplete="off"
        role="combobox" aria-expanded="false" aria-autocomplete="list" aria-label="Zoek je verblijf"
        value="${huidig ? huidig.naam.split(',')[0].replace(/"/g, '&quot;') : ''}"></div>
      <ul class="gevonden" role="listbox"></ul>
      <button type="button" class="linkknop" data-a="hier">Gebruik mijn huidige locatie</button>
      <p class="keuze">${huidig ? `Gekozen: <b>${huidig.naam.split(',').slice(0, 2).join(',')}</b>` : ''}</p>
      <h2>Hoe lang wil je rijden?</h2>
      <div class="tijden">
        <label><input name="uren" type="number" inputmode="numeric" min="0" max="12" step="1" value="${Math.floor((huidig?.max ?? 120) / 60)}" aria-label="Uren"> u</label>
        <label><input name="min" type="number" inputmode="numeric" min="0" max="59" step="1" value="${(huidig?.max ?? 120) % 60}" aria-label="Minuten"> min</label>
      </div>
      <p class="fout" hidden></p>
      <div class="knoppen"><button value="sluit" class="linkknop">Overslaan</button><button value="ok" class="knop hoofd">Toon de kaart</button></div>
    </form>`
    document.body.appendChild(d)
    const veld = d.querySelector<HTMLInputElement>('input[name=q]')!
    const lijst = d.querySelector('.gevonden')!
    const keuze = d.querySelector('.keuze')!
    const fout = d.querySelector<HTMLElement>('.fout')!
    const toonFout = (t: string) => { fout.textContent = t; fout.hidden = !t }
    let sessie = nieuweSessie()
    const kies = async (g0: Gevonden | { naam: string; lat: number; lon: number }) => {
      let g = g0
      if ('titel' in g0) {
        try { g = await plaatsVan(g0, sessie) } catch { toonFout('Deze plaats kon niet worden geladen. Kies een andere.'); return }
        sessie = nieuweSessie()
      }
      gekozen = g; lijst.innerHTML = ''; resultaten = []
      veld.value = g.naam.split(',')[0]; veld.setAttribute('aria-expanded', 'false')
      keuze.innerHTML = `Gekozen: <b>${g.naam.split(',').slice(0, 2).join(',')}</b>`
      toonFout('')
    }
    // Zoeken terwijl je typt: even wachten tot je stopt met typen, oude vragen afbreken.
    const PIN = '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M12 21s-7-6.2-7-11a7 7 0 0 1 14 0c0 4.8-7 11-7 11z"/><circle cx="12" cy="10" r="2.5"/></svg>'
    const esc = (t: string) => t.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]!)
    let wacht: ReturnType<typeof setTimeout> | undefined, bezig: AbortController | null = null
    let resultaten: Gevonden[] = [], actief = -1
    const markeer = (i: number) => {
      actief = i
      lijst.querySelectorAll('button').forEach((b, k) => b.setAttribute('aria-selected', String(k === i)))
    }
    const zoek = async () => {
      const q = veld.value.trim()
      bezig?.abort()
      if (q.length < 2) { lijst.innerHTML = ''; resultaten = []; veld.setAttribute('aria-expanded', 'false'); return }
      bezig = new AbortController()
      try {
        resultaten = await zoekPlaats(q, sessie, bezig.signal)
        lijst.innerHTML = resultaten.length ? '' : '<li class="rustig">Niets gevonden in Portugal.</li>'
        resultaten.forEach((g) => {
          const li = document.createElement('li')
          li.innerHTML = `<button type="button" role="option">${PIN}<span><b>${esc(g.titel)}</b><small>${esc(g.adres)}</small></span></button>`
          li.querySelector('button')!.onclick = () => kies(g)
          lijst.appendChild(li)
        })
        veld.setAttribute('aria-expanded', String(resultaten.length > 0))
        markeer(-1)
        toonFout('')
      } catch (e) {
        if ((e as Error).name === 'AbortError') return
        lijst.innerHTML = ''; toonFout('Zoeken lukt nu niet. Probeer opnieuw of gebruik je locatie.')
      }
    }
    veld.oninput = () => { clearTimeout(wacht); wacht = setTimeout(zoek, 120) }
    veld.onkeydown = (e) => {
      if (e.key === 'ArrowDown' && resultaten.length) { e.preventDefault(); markeer((actief + 1) % resultaten.length) }
      else if (e.key === 'ArrowUp' && resultaten.length) { e.preventDefault(); markeer((actief - 1 + resultaten.length) % resultaten.length) }
      else if (e.key === 'Enter') { e.preventDefault(); if (resultaten.length) kies(resultaten[Math.max(0, actief)]); else zoek() }
    }
    d.querySelector<HTMLButtonElement>('[data-a=hier]')!.onclick = () => {
      navigator.geolocation?.getCurrentPosition(
        (pos) => kies({ naam: 'Mijn locatie', lat: pos.coords.latitude, lon: pos.coords.longitude }),
        () => toonFout('Je locatie is niet beschikbaar.'))
    }
    const maxTijd = () => {
      const u = Number(d.querySelector<HTMLInputElement>('input[name=uren]')!.value || 0)
      const m = Number(d.querySelector<HTMLInputElement>('input[name=min]')!.value || 0)
      return Math.round(u) * 60 + Math.round(m)
    }
    d.addEventListener('close', () => {
      const max = maxTijd()
      const ok = d.returnValue === 'ok' && gekozen
      d.remove()
      klaar(ok ? { ...gekozen!, max } : null)
    })
    d.querySelector('form')!.addEventListener('submit', (e) => {
      if ((e as SubmitEvent).submitter?.getAttribute('value') !== 'ok') return
      if (!gekozen) { e.preventDefault(); toonFout('Kies eerst een plaats.') }
      else if (maxTijd() < 1) { e.preventDefault(); toonFout('Vul in hoe lang je wil rijden.') }
    })
    d.showModal()
  })
}
