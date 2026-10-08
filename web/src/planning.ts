// Tabblad Planning: 4 weken, per dag één resultaat (pipeline/site/planning.py):
// golfsurfen, anders windsurfles, anders stille waters / e-foil, anders klimmen, anders niets.
import './style.css'
import { bewaarVerblijf, leesVerblijf, tabWissel, rijTekst, rijtijden, vraagVerblijf, type Verblijf } from './verblijf'

interface Keuze { sport: 'golfsurfen' | 'stil' | 'windsurf' | 'klim'; plek: string; id: string | null; van: string; tot: string; km: number; rij: number | null; score?: number }
interface Reis { soort: 'aankomst' | 'terugvlucht'; wie: string[] }
type Blok = Omit<Keuze, 'sport'> & { lat: number; lon: number }
interface Dag { dag: string; voorspelling: boolean; keuze?: Keuze | null; reizen?: Reis[]; kandidaten?: Record<Keuze['sport'], Blok[]> }

const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]!)
const fmt = (o: Intl.DateTimeFormatOptions) => new Intl.DateTimeFormat('nl-BE', { ...o, timeZone: 'UTC' })
const DAGNR = fmt({ day: 'numeric' })

const svg = (inhoud: string) => `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"
  stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${inhoud}</svg>`
const ICOON = {
  klok: svg('<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>'),
  plek: svg('<path d="M12 21s-7-6.2-7-11a7 7 0 0 1 14 0c0 4.8-7 11-7 11z"/><circle cx="12" cy="10" r="2.5"/>'),
  afstand: svg('<path d="M4 19h16"/><path d="M6 19V9l6-4 6 4v10"/><path d="M10 19v-5h4v5"/>'),
  info: svg('<circle cx="12" cy="12" r="9"/><path d="M12 11v6"/><path d="M12 7.5v.5"/>'),
  wolk: svg('<path d="M7 18h10a4 4 0 0 0 .5-8A6 6 0 0 0 6 11a3.5 3.5 0 0 0 1 7z"/>'),
  aankomst: svg('<path d="M2 20h20"/><path d="M3 10l3 1 3-4 2 1-1 4 5 2 4-1c1 0 1.5 1.5.5 2L8 17l-5-2z"/>'),
  vertrek: svg('<path d="M2 20h20"/><path d="M3 14l3-1 3 3 2-1-2-4 5-3 4-2c1-.5 2 .8 1.2 1.6L9 17l-5 1z"/>'),
  rots: svg('<path d="M3 20l5-9 3 4 3-7 7 12z"/><path d="M14 8l1.5 3"/>'),
}

// Per sport: naam, kleur, foto (zoals op de kaart) en de links (kort label, uitleg in de tooltip).
interface Link { url: string; label: string; uitleg?: string }
const SPORT: Record<Keuze['sport'], { naam: string; kleur: string; foto?: string; nota?: string; links: Link[]; extra?: { titel: string; links: Link[] } }> = {
  golfsurfen: { naam: 'Golfsurfen', kleur: '#2a6fdb', foto: 'golfsurfen', links: [] },
  stil: {
    naam: 'Stille waters / e-foil', kleur: '#6b757d', foto: 'plat-water',
    nota: 'E-foil: vraag de school waar en of de les doorgaat.',
    links: [
      { url: 'https://www.efoilalgarve.com/', label: 'eFoil Algarve', uitleg: 'WhatsApp +351 912 991 460 · 1 u · beginners welkom · reserveren verplicht' },
      { url: 'https://www.efoil-riders.com/pages/lesson-location-algarve-portugal', label: 'eFoil Riders', uitleg: 'beginnerscursus 90 min' },
    ],
  },
  windsurf: {
    naam: 'Windsurfles', kleur: '#0e8fa6', foto: 'windsurfen',
    nota: 'De school bevestigt de avond ervoor of de les doorgaat.',
    links: [
      { url: 'https://algarvewatersport.com/en/lagos-windsurf-school/', label: 'Algarve Watersport', uitleg: 'Ria de Alvor · beginners · 2,5 u · start rond 10:00' },
      { url: 'https://windsportscenter.com/lessons/', label: 'Windsports Center', uitleg: 'beginners in de kleine lagune van Alvor · 3 u' },
    ],
    extra: {
      titel: 'Kite (de school beslist op de dag zelf)',
      links: [
        { url: 'https://www.eakitelagos.com/', label: 'EA Kite Lagos', uitleg: 'heel het jaar open · Ria de Alvor' },
        { url: 'https://kiteschoolportugal.com/kitesurfing-lessons/', label: 'Kite School Portugal' },
        { url: 'https://alvorkitecenter.com/', label: 'Alvor Kite Center' },
        { url: 'https://kitesurfschoolalgarve.com/', label: 'Kitesurf School Algarve' },
        { url: 'https://algarvewatersport.com/en/kite-school-portugal/', label: 'Algarve Watersport kite', uitleg: 'oktober buiten seizoen, geen garantie' },
      ],
    },
  },
  klim: {
    naam: 'Klimmen', kleur: '#6B4226', foto: 'klimmen',
    links: [
      { url: 'https://climbingalgarve.pt/trips/climbing-in-lagos/', label: 'Climbing Algarve · halve dag', uitleg: '4 u · routes IV+ tot 6a+ · beginners' },
      { url: 'https://climbingalgarve.pt/courses/top-rope-course/', label: 'Top rope · volledige dag', uitleg: '8 u' },
      { url: 'https://www.amea.pt/?page_id=84', label: 'AMEA · cursus 3 dagen', uitleg: 'vaste data, niet weersafhankelijk' },
    ],
  },
}

// Elke school of link op een eigen regel: naam, korte uitleg eronder, pijltje rechts.
const chip = (l: Link) => `<a class="linkrij" href="${l.url}" target="_blank" rel="noopener">
  <span><b>${esc(l.label)}</b>${l.uitleg ? `<small>${esc(l.uitleg)}</small>` : ''}</span>
  <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 6l6 6-6 6"/></svg></a>`
const rijtijd = (m: number | null) => m == null ? '' : m < 60 ? `${m} min rijden` : `${Math.floor(m / 60)}u${String(m % 60).padStart(2, '0')} rijden`
const uur = (t: string) => String(Number(t.slice(0, 2)))
const datumTekst = (d: string, o: Intl.DateTimeFormatOptions) => fmt(o).format(new Date(d + 'T12:00:00Z'))

// Eén dag met een plan: een fotostrook zoals bovenaan de strandfiche, met de links eronder.
function plan(d: Dag, k: Keuze) {
  const s = SPORT[k.sport]
  const strand = k.id && (k.sport === 'golfsurfen' || k.sport === 'stil')
  // Namen die helemaal in hoofdletters staan (bv. FERRAGUDO) gewoon schrijven.
  const naam = k.plek === k.plek.toUpperCase() ? k.plek.charAt(0) + k.plek.slice(1).toLowerCase() : k.plek
  const plek = strand ? `<a href="./#${encodeURIComponent(k.id!)}">${esc(naam)}</a>` : esc(naam)
  const beeld = s.foto ? `<img src="foto/${s.foto}.webp" alt="">` : `<div class="geenfoto">${ICOON.rots}</div>`
  return `<article class="plandag" style="--kleur:${s.kleur}">
    <figure>${beeld}
      <figcaption>
        <span class="datumlijn"><b>${datumTekst(d.dag, { weekday: 'short' })} ${DAGNR.format(new Date(d.dag + 'T12:00:00Z'))}</b>${datumTekst(d.dag, { month: 'short' })}</span>
        <span class="wat">${s.naam}</span>
        <span class="uren">${uur(k.van)}–${uur(k.tot)}u</span>
        <span class="waar">${ICOON.plek}${plek}<em>${rijtijd(k.rij) || `${k.km} km`}</em></span>
      </figcaption>
    </figure>
    ${s.nota || s.links.length || s.extra ? `<div class="onder">
      ${s.nota ? `<p class="nota">${s.nota}</p>` : ''}
      ${s.links.length ? `<div class="links">${s.links.map(chip).join('')}</div>` : ''}
      ${s.extra ? `<details><summary>${s.extra.titel}</summary><div class="links">${s.extra.links.map(chip).join('')}</div></details>` : ''}
    </div>` : ''}
  </article>`
}

const niets = (d: Dag) => `<p class="dagniets"><b>${datumTekst(d.dag, { weekday: 'short' })} ${DAGNR.format(new Date(d.dag + 'T12:00:00Z'))}</b> niets ideaal</p>`

// Weken: deze week, volgende week, daarna "week van ..."; dagen zonder voorspelling samen op één regel.
function weekKop(d: string, eerste: string) {
  const t = new Date(d + 'T12:00:00Z'), t0 = new Date(eerste + 'T12:00:00Z')
  const maandag = (x: Date) => { const y = new Date(x); y.setUTCDate(y.getUTCDate() - ((y.getUTCDay() + 6) % 7)); return y }
  const w = Math.round((maandag(t).getTime() - maandag(t0).getTime()) / (7 * 864e5))
  return w === 0 ? 'Deze week' : w === 1 ? 'Volgende week' : `Week van ${fmt({ day: 'numeric', month: 'long' }).format(maandag(t))}`
}

// Aankomst of terugvlucht: een balk boven de dag.
const reis = (r: Reis) => `<p class="reis ${r.soort}">${r.soort === 'aankomst' ? ICOON.aankomst : ICOON.vertrek}
  <b>${r.soort === 'aankomst' ? 'Aankomst' : 'Terugvlucht'}</b> ${esc(r.wie.join(', '))}</p>`

function toon(dagen: Dag[]) {
  let html = '', kop = '', zonder: Dag[] = []
  const sluitZonder = () => {
    if (!zonder.length) return
    const a = zonder[0].dag, b = zonder[zonder.length - 1].dag
    const tekst = a === b ? datumTekst(a, { weekday: 'short', day: 'numeric', month: 'short' })
      : `${datumTekst(a, { day: 'numeric', month: 'short' })} – ${datumTekst(b, { day: 'numeric', month: 'short' })}`
    html += `<p class="nogniet">${ICOON.wolk} ${tekst}: nog geen voorspelling</p>`
    zonder = []
  }
  for (const d of dagen) {
    const w = weekKop(d.dag, dagen[0].dag)
    if (w !== kop) { sluitZonder(); html += `<h2 class="week">${w}</h2>`; kop = w }
    const reizen = d.reizen ?? []
    if (!d.voorspelling && !reizen.length) { zonder.push(d); continue }
    sluitZonder()
    if (reizen.length) html += `<div class="reisdag"><span class="reisdatum">${datumTekst(d.dag, { weekday: 'short' })} ${DAGNR.format(new Date(d.dag + 'T12:00:00Z'))} ${datumTekst(d.dag, { month: 'short' })}</span>${reizen.map(reis).join('')}</div>`
    if (!d.voorspelling) html += `<p class="nogniet klein-na-reis">${ICOON.wolk} nog geen voorspelling</p>`
    else html += d.keuze ? plan(d, d.keuze) : niets(d)
  }
  sluitZonder()
  return html
}

// Keuze per dag, zoals pipeline/site/planning.py, maar met de rijtijd vanaf je verblijf, jouw maximale rijtijd
// (voor alle sporten) en jouw volgorde van voorrang. Golfsurfen en stille waters: eerst de hoogste score
// (afgerond zoals Python), dan de kortste rijtijd; windsurfles en klimmen: het langste blok.
const rondPy = (x: number) => { const f = Math.floor(x), d = x - f; return d > 0.5 ? f + 1 : d < 0.5 ? f : f % 2 === 0 ? f : f + 1 }
const lengte = (b: Blok) => Number(b.tot.slice(0, 2)) - Number(b.van.slice(0, 2))

// Volgorde van voorrang: standaard golfsurfen, windsurfles, stille waters, klimmen; aanpasbaar en bewaard.
type Sport = Keuze['sport']
const STANDAARD: Sport[] = ['golfsurfen', 'windsurf', 'stil', 'klim']
const VOLGORDE_SLEUTEL = 'planning-volgorde-v1'
function leesVolgorde(): Sport[] {
  try {
    const v = JSON.parse(localStorage.getItem(VOLGORDE_SLEUTEL) ?? 'null')
    if (Array.isArray(v) && v.length === 4 && STANDAARD.every((x) => v.includes(x))) return v
  } catch { /* standaard */ }
  return [...STANDAARD]
}
let volgorde = leesVolgorde()

function kies(d: Dag, rij: (b: Blok) => number | null, max: number): Keuze | null {
  const k = d.kandidaten!
  const binnen = (bs: Blok[]) => bs.flatMap((b) => { const m = rij(b); return m != null && m <= max ? [{ ...b, rij: m }] : [] })
  const beste = (bs: Blok[]) => {
    const top = Math.max(...bs.map((b) => rondPy(b.score ?? 0)))
    return bs.filter((b) => rondPy(b.score ?? 0) === top).reduce((a, b) => (b.rij! < a.rij! ? b : a))
  }
  const langste = (bs: Blok[]) => bs.reduce((a, b) => (lengte(b) > lengte(a) ? b : a))
  for (const sport of volgorde) {
    const bs = binnen(k[sport] ?? [])
    if (bs.length) return { sport, ...(sport === 'golfsurfen' || sport === 'stil' ? beste(bs) : langste(bs)) }
  }
  return null
}

const KORT: Record<Sport, string> = { golfsurfen: 'Golfsurfen', windsurf: 'Windsurfles', stil: 'Stille waters', klim: 'Klimmen' }
function voorrang(opnieuw: () => void) {
  const el = document.getElementById('voorrang')!
  const pijl = (r: string) => `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${r}"/></svg>`
  const anders = volgorde.join() !== STANDAARD.join()
  el.innerHTML = `<div class="kopregel"><span>Voorrang</span>${anders ? '<button type="button" class="terug" data-a="standaard">Standaard</button>' : ''}</div>
    <ol>${volgorde.map((s, i) => `<li style="--kleur:${SPORT[s].kleur}">
      <b>${i + 1}</b><span>${KORT[s]}</span>
      <button type="button" data-i="${i}" data-r="-1" ${i === 0 ? 'disabled' : ''} aria-label="${KORT[s]} hoger">${pijl('M6 15l6-6 6 6')}</button>
      <button type="button" data-i="${i}" data-r="1" ${i === volgorde.length - 1 ? 'disabled' : ''} aria-label="${KORT[s]} lager">${pijl('M6 9l6 6 6-6')}</button>
    </li>`).join('')}</ol>`
  el.querySelectorAll<HTMLButtonElement>('button[data-i]').forEach((k) => k.onclick = () => {
    const i = Number(k.dataset.i), j = i + Number(k.dataset.r)
    ;[volgorde[i], volgorde[j]] = [volgorde[j], volgorde[i]]
    try { localStorage.setItem(VOLGORDE_SLEUTEL, JSON.stringify(volgorde)) } catch { /* niet bewaard */ }
    voorrang(opnieuw); opnieuw()
  })
  const st = el.querySelector<HTMLButtonElement>('[data-a=standaard]')
  if (st) st.onclick = () => {
    volgorde = [...STANDAARD]
    try { localStorage.removeItem(VOLGORDE_SLEUTEL) } catch { /* niets */ }
    voorrang(opnieuw); opnieuw()
  }
}

function kop(v: Verblijf | null, melding = '') {
  const el = document.getElementById('planvan')!
  el.innerHTML = `<span class="huis" aria-hidden="true"></span>
    <span class="waar"><b>${esc(v ? v.naam.split(',')[0] : 'Ferragudo')}</b><small>max ${rijTekst(v?.max ?? 120)} rijden${melding ? ` · ${melding}` : ''}</small></span>
    <button type="button" class="terug">Wijzig</button>`
  el.querySelector('button')!.onclick = async () => {
    const n = await vraagVerblijf(v ?? leesVerblijf())
    if (n) { bewaarVerblijf(n); start() }
  }
}

tabWissel()

async function start() {
  const doel = document.getElementById('dagen')!
  let p: { dagen: Dag[] }
  try {
    const g = await (await fetch('data/index.json', { cache: 'no-store' })).json()
    p = await (await fetch(`data/planning.json?v=${encodeURIComponent(g.gemaakt)}`)).json()
  } catch {
    doel.innerHTML = '<p class="rustig">De planning kon niet worden geladen.</p>'
    return
  }
  const doelTonen = (rij: (b: Blok) => number | null, max: number) => {
    const teken = () => { doel.innerHTML = toon(p.dagen.map((d) => (d.voorspelling && d.kandidaten ? { ...d, keuze: kies(d, rij, max) } : d))) }
    voorrang(teken); teken()
  }
  // Zonder verblijf (of als de rijtijden niet lukken): vanaf Ferragudo met 2 uur rijden.
  const vanafFerragudo = (b: Blok) => b.rij ?? null
  const v = leesVerblijf()
  if (!v) { kop(null); doelTonen(vanafFerragudo, 120); return }
  kop(v, 'rijtijden berekenen…')
  const plekken = new Map<string, { id: string; lat: number; lon: number }>()
  for (const d of p.dagen) for (const bs of Object.values(d.kandidaten ?? {})) for (const b of bs) {
    const id = b.id ?? b.plek
    if (!plekken.has(id)) plekken.set(id, { id, lat: b.lat, lon: b.lon })
  }
  try {
    const rij = await rijtijden(v, [...plekken.values()])
    kop(v)
    doelTonen((b) => rij.get(b.id ?? b.plek) ?? null, v.max)
  } catch {
    kop(v, 'rijtijden lukken nu niet, planning vanaf Ferragudo')
    doelTonen(vanafFerragudo, 120)
  }
}
start()
