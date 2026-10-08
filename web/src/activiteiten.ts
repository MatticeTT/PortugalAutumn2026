// Eigen activiteiten in de planning: iedereen die de site gebruikt kan per dag iets toevoegen
// (wat, van–tot, locatie, foto). Bewaard via de Vercel-functie /api/activiteiten (Vercel Blob),
// zodat iedereen dezelfde lijst ziet.
import { plaatsVan, zoekPlaats, type Gevonden } from './verblijf'

export interface Activiteit {
  id: string; dag: string; titel: string; van: string; tot: string
  plek: { naam: string; lat: number; lon: number } | null; foto: string | null
}

const API = '/api/activiteiten'
export let opslagAan = true

export async function laadActiviteiten(): Promise<Activiteit[]> {
  try {
    const r = await fetch(API, { cache: 'no-store' })
    if (r.status === 501 || r.status === 404 || !(r.headers.get('content-type') ?? '').includes('json')) { opslagAan = false; return [] }
    if (!r.ok) return []
    opslagAan = true
    return await r.json()
  } catch { return [] }
}

export async function wisActiviteit(id: string) {
  const r = await fetch(`${API}?id=${encodeURIComponent(id)}`, { method: 'DELETE' })
  if (!r.ok) throw new Error(`wissen ${r.status}`)
}

// Foto verkleinen in de browser (max. 1280 px, webp of jpeg), zodat het opladen snel gaat.
async function verklein(f: File): Promise<string> {
  const beeld = await createImageBitmap(f)
  const schaal = Math.min(1, 1280 / Math.max(beeld.width, beeld.height))
  const c = document.createElement('canvas')
  c.width = Math.round(beeld.width * schaal); c.height = Math.round(beeld.height * schaal)
  c.getContext('2d')!.drawImage(beeld, 0, 0, c.width, c.height)
  const webp = c.toDataURL('image/webp', 0.82)
  return webp.startsWith('data:image/webp') ? webp : c.toDataURL('image/jpeg', 0.85)
}

const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]!)

// Het formulier. dagen = alle dagen van de planning (waarde, tekst); dag = de dag van het plusje.
export function nieuweActiviteit(dagen: [string, string][], dag: string): Promise<Activiteit | null> {
  return new Promise((klaar) => {
    const d = document.createElement('dialog')
    d.className = 'verblijfvraag activiteitvraag'
    d.innerHTML = `<form method="dialog">
      <h2>Activiteit toevoegen</h2>
      <label class="veld">Wat<input name="titel" maxlength="80" placeholder="bv. Kajakken in Benagil" required></label>
      <label class="veld">Dag<select name="dag">${dagen.map(([w, t]) => `<option value="${w}" ${w === dag ? 'selected' : ''}>${esc(t)}</option>`).join('')}</select></label>
      <div class="tweeling">
        <label class="veld">Van<input name="van" type="time" value="10:00" required></label>
        <label class="veld">Tot<input name="tot" type="time" value="12:00" required></label>
      </div>
      <label class="veld"><span>Locatie <small>(mag leeg)</small></span><input name="plek" type="search" autocomplete="off" placeholder="Strand, dorp, adres…"></label>
      <ul class="gevonden" role="listbox"></ul>
      <label class="veld"><span>Foto <small>(mag leeg)</small></span>
        <span class="fotokeuze"><img alt="" hidden><span class="knop">Kies een foto</span><input name="foto" type="file" accept="image/*" hidden></span></label>
      <p class="fout" hidden></p>
      <div class="knoppen"><button value="sluit" class="linkknop" formnovalidate>Annuleren</button><button value="ok" class="knop hoofd">Opslaan</button></div>
    </form>`
    document.body.appendChild(d)
    const q = <T extends Element>(s: string) => d.querySelector<T>(s as any)!
    const fout = q<HTMLElement>('.fout')
    const toonFout = (t: string) => { fout.textContent = t; fout.hidden = !t }
    // Locatie: suggesties terwijl je typt (dezelfde zoekdienst als bij het verblijf).
    const veld = q<HTMLInputElement>('input[name=plek]'), lijst = q<HTMLUListElement>('.gevonden')
    let plek: Activiteit['plek'] = null, wacht: ReturnType<typeof setTimeout> | undefined, bezig: AbortController | null = null
    veld.oninput = () => {
      plek = null; clearTimeout(wacht)
      wacht = setTimeout(async () => {
        const t = veld.value.trim()
        bezig?.abort()
        if (t.length < 2) { lijst.innerHTML = ''; return }
        bezig = new AbortController()
        try {
          const r = await zoekPlaats(t, bezig.signal)
          lijst.innerHTML = ''
          r.slice(0, 5).forEach((g: Gevonden) => {
            const li = document.createElement('li')
            li.innerHTML = `<button type="button"><span><b>${esc(g.titel)}</b><small>${esc(g.adres)}</small></span></button>`
            li.querySelector('button')!.onclick = async () => {
              try { const p = await plaatsVan(g); plek = { naam: p.titel, lat: p.lat, lon: p.lon }; veld.value = p.titel; lijst.innerHTML = '' }
              catch { toonFout('Deze locatie kon niet worden geladen.') }
            }
            lijst.appendChild(li)
          })
        } catch { /* afgebroken of geen verbinding: geen suggesties */ }
      }, 120)
    }
    // Foto: kiezen, verkleinen, voorbeeld tonen.
    let foto: string | null = null
    const fotoVeld = q<HTMLInputElement>('input[name=foto]'), voorbeeld = q<HTMLImageElement>('.fotokeuze img')
    q<HTMLElement>('.fotokeuze .knop').onclick = () => fotoVeld.click()
    fotoVeld.onchange = async () => {
      const f = fotoVeld.files?.[0]
      if (!f) return
      try { foto = await verklein(f); voorbeeld.src = foto; voorbeeld.hidden = false; q<HTMLElement>('.fotokeuze .knop').textContent = 'Andere foto' }
      catch { toonFout('Deze foto kan niet gelezen worden.') }
    }
    const form = q<HTMLFormElement>('form')
    form.addEventListener('submit', async (e) => {
      if ((e as SubmitEvent).submitter?.getAttribute('value') !== 'ok') return
      e.preventDefault()
      const f = new FormData(form)
      const van = String(f.get('van')), tot = String(f.get('tot'))
      if (tot <= van) { toonFout('Het einduur moet na het startuur liggen.'); return }
      const knop = q<HTMLButtonElement>('button[value=ok]')
      knop.disabled = true; knop.textContent = 'Opslaan…'; toonFout('')
      try {
        const r = await fetch(API, { method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ titel: f.get('titel'), dag: f.get('dag'), van, tot, plek, foto }) })
        if (r.status === 501 || r.status === 404) throw new Error('De gedeelde opslag staat nog niet aan.')
        const a = await r.json().catch(() => ({}))
        if (!r.ok) throw new Error(a.fout ? `Opslaan lukt niet: ${a.fout}` : 'Opslaan lukt niet.')
        d.close(); d.remove(); klaar(a)
      } catch (err) {
        toonFout((err as Error).message || 'Opslaan lukt niet.')
        knop.disabled = false; knop.textContent = 'Opslaan'
      }
    })
    d.addEventListener('close', () => { if (d.isConnected) { d.remove(); klaar(null) } })
    d.showModal()
  })
}
