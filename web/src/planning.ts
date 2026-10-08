// Tabblad Planning: 4 weken, per dag één resultaat (pipeline/site/planning.py):
// golfsurfen, anders windsurfen, anders stille waters / e-foil, anders klimmen, anders niets (volgorde aanpasbaar).
import './style.css'
import { themaKnop } from './thema'
import { laadActiviteiten, nieuweActiviteit, wisActiviteit, type Activiteit } from './activiteiten'
import { bewaarVerblijf, hemelsbreed, leesVerblijf, ONBEREIKBAAR_KMH, tabWissel, rijTekst, rijtijden, vraagVerblijf, type Verblijf } from './verblijf'

interface Keuze { sport: 'golfsurfen' | 'stil' | 'windsurf' | 'klim'; plek: string; id: string | null; van: string; tot: string; km: number; rij: number | null; score?: number; lat?: number; lon?: number }
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
  // Vliegtuig dat landt / opstijgt (vormen van Material Icons "flight_land" en "flight_takeoff", Apache 2.0).
  aankomst: '<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true"><path d="M2.5 19h19v2h-19v-2zm7.18-5.73l4.35 1.16 5.31 1.42c.8.21 1.62-.26 1.84-1.06.21-.8-.26-1.62-1.06-1.84l-5.31-1.42-2.76-9.02L10.12 2v8.28L5.15 8.95l-.93-2.32-1.45-.39v5.17l1.6.43 5.31 1.43z"/></svg>',
  vertrek: '<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true"><path d="M2.5 19h19v2h-19v-2zm19.57-9.36c-.21-.8-1.04-1.28-1.84-1.06L14.92 10l-6.9-6.43-1.93.51 4.14 7.17-4.97 1.33-1.97-1.54-1.45.39 1.82 3.16.77 1.33 1.6-.43 5.31-1.42 4.35-1.16L21 11.49c.81-.23 1.28-1.05 1.07-1.85z"/></svg>',
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
    naam: 'Windsurfen', kleur: '#0e8fa6', foto: 'windsurfen',
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
// De scholen in SPORT liggen rond Lagos en Alvor.
const ALGARVE_SCHOLEN = { lat: 37.12, lon: -8.62 }

function plan(d: Dag, k: Keuze) {
  // Namen die helemaal in hoofdletters staan (bv. FERRAGUDO) gewoon schrijven.
  const naam = k.plek === k.plek.toUpperCase() ? k.plek.charAt(0) + k.plek.slice(1).toLowerCase() : k.plek
  // Link naar de fiche op de kaart (strand of klimplek).
  const doel = k.id ? (k.sport === 'klim' ? `klim:${k.id}` : k.id) : null
  const plek = doel ? `<a href="./#${encodeURIComponent(doel)}">${esc(naam)}</a>` : esc(naam)
  // Scholen en lessen (Algarve): alleen tonen als de plek in de buurt ligt.
  const s = { ...SPORT[k.sport] }
  if (!(k.lat != null && k.lon != null && hemelsbreed({ lat: k.lat, lon: k.lon }, ALGARVE_SCHOLEN) <= 45)) {
    s.links = []; s.extra = undefined; s.nota = undefined
  }
  const beeld = s.foto ? `<img src="foto/${s.foto}.webp" alt="">` : `<div class="geenfoto">${ICOON.rots}</div>`
  return `<article class="plandag" style="--kleur:${s.kleur}">
    <figure>${beeld}${plus(d.dag)}
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

// Eigen activiteiten (van iedereen, gedeeld via /api/activiteiten).
let eigen: Activiteit[] = []
const eigenVan = (dag: string) => eigen.filter((a) => a.dag === dag)
const PLUS = '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>'
const plus = (dag: string) => `<button type="button" class="plus" data-plus="${dag}" aria-label="Activiteit toevoegen op ${dag}">${PLUS}</button>`
const KLEUR_EIGEN = '#2e9e5b'

// Een eigen activiteit: dezelfde kaart als een plan, met de eigen foto (of een effen vlak).
function eigenKaart(a: Activiteit) {
  const beeld = a.foto ? `<img src="${esc(a.foto)}" alt="" loading="lazy">` : `<img class="vlag" src="foto/vlag-portugal.svg" alt="">`
  const plek = a.plek
    ? `<a href="https://www.openstreetmap.org/?mlat=${a.plek.lat}&mlon=${a.plek.lon}#map=15/${a.plek.lat}/${a.plek.lon}" target="_blank" rel="noopener">${esc(a.plek.naam)}</a>` : ''
  return `<article class="plandag eigen" style="--kleur:${KLEUR_EIGEN}">
    <figure>${beeld}${plus(a.dag)}
      <figcaption>
        <span class="datumlijn"><b>${datumTekst(a.dag, { weekday: 'short' })} ${DAGNR.format(new Date(a.dag + 'T12:00:00Z'))}</b>${datumTekst(a.dag, { month: 'short' })}</span>
        <span class="wat">${esc(a.titel)}</span>
        <span class="uren">${a.van.replace(/^0/, '').replace(':00', '')}–${a.tot.replace(/^0/, '').replace(':00', '')}u</span>
        ${plek ? `<span class="waar">${ICOON.plek}${plek}</span>` : ''}
      </figcaption>
    </figure>
    <div class="onder eigenonder"><span>Eigen activiteit</span><button type="button" class="linkknop" data-wis="${a.id}">Verwijderen</button></div>
  </article>`
}

// Weken: deze week, volgende week, daarna "week van ..."; dagen zonder voorspelling samen op één regel.
function weekKop(d: string, eerste: string) {
  const t = new Date(d + 'T12:00:00Z'), t0 = new Date(eerste + 'T12:00:00Z')
  const maandag = (x: Date) => { const y = new Date(x); y.setUTCDate(y.getUTCDate() - ((y.getUTCDay() + 6) % 7)); return y }
  const w = Math.round((maandag(t).getTime() - maandag(t0).getTime()) / (7 * 864e5))
  return w === 0 ? 'Deze week' : w === 1 ? 'Volgende week' : `Week van ${fmt({ day: 'numeric', month: 'long' }).format(maandag(t))}`
}

// Aankomst of terugvlucht: één regel met icoon.
const reis = (r: Reis) => `<p class="reis ${r.soort}"><i>${r.soort === 'aankomst' ? ICOON.aankomst : ICOON.vertrek}</i>
  <span><b>${r.soort === 'aankomst' ? 'Aankomst' : 'Terugvlucht'}</b><br>${esc(r.wie.join(', '))}</span></p>`

// Dagen zonder plan staan per week in één kader, als regels met links altijd dezelfde datumkolom:
// reisdagen, "niets ideaal", en opeenvolgende dagen zonder voorspelling samen op één regel.
const kortDag = (d: string) => `${datumTekst(d, { weekday: 'short' })} ${DAGNR.format(new Date(d + 'T12:00:00Z'))} ${datumTekst(d, { month: 'short' })}`
function bereik(a: string, b: string) {
  if (a === b) return kortDag(a)
  const ma = datumTekst(a, { month: 'short' }), mb = datumTekst(b, { month: 'short' })
  const na = DAGNR.format(new Date(a + 'T12:00:00Z')), nb = DAGNR.format(new Date(b + 'T12:00:00Z'))
  return ma === mb ? `${na} – ${nb} ${mb}` : `${na} ${ma} – ${nb} ${mb}`
}
const regel = (datum: string, inhoud: string, soort = '', dag = '') => soort === 'leeg'
  // Periode zonder voorspelling: kopregel van het kader, tekst links en de periode rechts (past altijd).
  ? `<li class="leeg">${inhoud}<span class="periode">${datum}</span>${dag ? plus(dag) : ''}</li>`
  : `<li class="${soort}"><span class="datum">${datum}</span><div>${inhoud}</div>${dag ? plus(dag) : ''}</li>`

function toon(dagen: Dag[]) {
  // Per week: is er voor geen enkele dag een voorspelling, dan staat dat één keer bovenaan het kader
  // en tonen de regels eronder alleen nog de reisdagen. Eigen activiteiten staan als kaart op hun dag.
  const weken = new Map<string, Dag[]>()
  for (const d of dagen) {
    const w = weekKop(d.dag, dagen[0].dag)
    if (!weken.has(w)) weken.set(w, [])
    weken.get(w)!.push(d)
  }
  const geenVoorspelling = `<span class="stil">${ICOON.wolk} Nog geen voorspelling</span>`
  const kaarten = (dag: string) => eigenVan(dag).map(eigenKaart).join('')
  let html = ''
  for (const [w, ds] of weken) {
    html += `<h2 class="week">${w}</h2>`
    if (ds.every((d) => !d.voorspelling)) {
      const rijen = [regel(bereik(ds[0].dag, ds[ds.length - 1].dag), geenVoorspelling, 'leeg', ds[0].dag)]
      for (const d of ds) if (d.reizen?.length) rijen.push(regel(kortDag(d.dag), d.reizen.map(reis).join(''), 'reisregel', d.dag))
      html += `<ul class="daglijst">${rijen.join('')}</ul>` + ds.map((d) => kaarten(d.dag)).join('')
      continue
    }
    let lijst: string[] = [], zonder: Dag[] = []
    const sluitZonder = () => {
      if (zonder.length) lijst.push(regel(bereik(zonder[0].dag, zonder[zonder.length - 1].dag), geenVoorspelling, 'leeg', zonder[0].dag))
      zonder = []
    }
    const sluitLijst = () => { sluitZonder(); if (lijst.length) html += `<ul class="daglijst">${lijst.join('')}</ul>`; lijst = [] }
    for (const d of ds) {
      const reizen = d.reizen ?? []
      const eigenHier = eigenVan(d.dag).length > 0
      if (!d.voorspelling && !reizen.length && !eigenHier) { zonder.push(d); continue }
      sluitZonder()
      const reisHtml = reizen.map(reis).join('')
      if (d.voorspelling && d.keuze) {
        // Een dag met plan: eventuele reis als regel net boven de fotokaart.
        if (reizen.length) lijst.push(regel(kortDag(d.dag), reisHtml, 'reisregel', d.dag))
        sluitLijst()
        html += plan(d, d.keuze) + kaarten(d.dag)
      } else if (!reizen.length && eigenHier) {
        sluitLijst()
        html += kaarten(d.dag)
      } else {
        const status = d.voorspelling ? '<span class="stil">Niets ideaal</span>' : geenVoorspelling
        lijst.push(regel(kortDag(d.dag), reisHtml + status, reizen.length ? 'reisregel' : '', d.dag))
        if (eigenHier) { sluitLijst(); html += kaarten(d.dag) }
      }
    }
    sluitLijst()
  }
  return html
}

// Keuze per dag, zoals pipeline/site/planning.py, maar met de rijtijd vanaf je verblijf, jouw maximale rijtijd
// (voor alle sporten) en jouw volgorde van voorrang. Golfsurfen en stille waters: eerst de hoogste score
// (afgerond zoals Python), dan de kortste rijtijd; zo ook windsurfen; klimmen: het langste blok, dan de kortste rijtijd.
const rondPy = (x: number) => { const f = Math.floor(x), d = x - f; return d > 0.5 ? f + 1 : d < 0.5 ? f : f % 2 === 0 ? f : f + 1 }
const lengte = (b: Blok) => Number(b.tot.slice(0, 2)) - Number(b.van.slice(0, 2))

// Volgorde van voorrang: standaard golfsurfen, windsurfen, stille waters, klimmen; aanpasbaar en bewaard.
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
  // Klimmen: eerst het langste droge blok, dan de kortste rijtijd.
  const langste = (bs: Blok[]) => {
    const top = Math.max(...bs.map(lengte))
    return bs.filter((b) => lengte(b) === top).reduce((a, b) => (b.rij! < a.rij! ? b : a))
  }
  for (const sport of volgorde) {
    const bs = binnen(k[sport] ?? [])
    if (bs.length) return { sport, ...(sport === 'klim' ? langste(bs) : beste(bs)) }
  }
  return null
}

const KORT: Record<Sport, string> = { golfsurfen: 'Golfsurfen', windsurf: 'Windsurfen', stil: 'Stille waters', klim: 'Klimmen' }
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
themaKnop()

// Andere landen (planning_<land>.json): alleen laden als een stuk van dat land binnen je rijtijd kan liggen,
// en dan hun blokken golfsurfen en stille waters bij de kandidaten van elke dag zetten.
const LAND_KADER: Record<string, [number, number, number, number]> = {
  es: [-9.45, 35.95, 3.4, 43.85], fr: [-5.3, 42.3, 8.3, 51.15], be: [2.4, 50.9, 3.5, 51.45],
}
async function andereLanden(dagen: Dag[], v: Verblijf, versie: string) {
  const perDag = new Map(dagen.map((d) => [d.dag, d]))
  await Promise.all(Object.entries(LAND_KADER).map(async ([land, [x0, y0, x1, y1]]) => {
    const dichtst = { lat: Math.min(y1, Math.max(y0, v.lat)), lon: Math.min(x1, Math.max(x0, v.lon)) }
    if (hemelsbreed(v, dichtst) > (v.max / 60) * ONBEREIKBAAR_KMH) return
    try {
      const r = await fetch(`data/planning_${land}.json?v=${encodeURIComponent(versie)}`)
      if (!r.ok) return
      // Compact (pipeline/site/planning.py): plekken {id: [naam, lat, lon]}, per dag per sport [id, van, tot, score].
      const j = await r.json() as { plekken: Record<string, [string, number, number]>; dagen: Record<string, Record<string, [string, string, string, number | null][]>> }
      for (const [dag, sporten] of Object.entries(j.dagen)) {
        const d = perDag.get(dag)
        if (!d?.voorspelling || !d.kandidaten) continue
        for (const [sport, rijen] of Object.entries(sporten)) {
          const bs: Blok[] = rijen.map(([id, van, tot, score]) => {
            const [plek, lat, lon] = j.plekken[id]
            return { plek, id, van, tot, km: 0, rij: null, lat, lon, ...(score == null ? {} : { score }) }
          })
          d.kandidaten[sport as Keuze['sport']] = [...(d.kandidaten[sport as Keuze['sport']] ?? []), ...bs]
        }
      }
    } catch { /* dat land dan niet */ }
  }))
}

async function start() {
  const doel = document.getElementById('dagen')!
  let p: { dagen: Dag[] }
  let g: { gemaakt: string }
  try {
    g = await (await fetch('data/index.json', { cache: 'no-store' })).json()
    p = await (await fetch(`data/planning.json?v=${encodeURIComponent(g.gemaakt)}`)).json()
  } catch {
    doel.innerHTML = '<p class="rustig">De planning kon niet worden geladen.</p>'
    return
  }
  eigen = await laadActiviteiten()
  const doelTonen = (rij: (b: Blok) => number | null, max: number) => {
    const teken = () => { doel.innerHTML = toon(p.dagen.map((d) => (d.voorspelling && d.kandidaten ? { ...d, keuze: kies(d, rij, max) } : d))) }
    voorrang(teken); teken()
    // Plusje: activiteit toevoegen; Verwijderen: eigen activiteit weg. Daarna opnieuw tekenen.
    doel.onclick = async (e) => {
      const t = (e.target as HTMLElement).closest<HTMLElement>('[data-plus], [data-wis]')
      if (!t) return
      if (t.dataset.plus) {
        const a = await nieuweActiviteit(p.dagen.map((d) => [d.dag, kortDag(d.dag)]), t.dataset.plus)
        if (a) { eigen = [...eigen, a].sort((x, y) => (x.dag + x.van).localeCompare(y.dag + y.van)); teken() }
      } else if (t.dataset.wis && confirm('Deze activiteit voor iedereen verwijderen?')) {
        try { await wisActiviteit(t.dataset.wis); eigen = eigen.filter((a) => a.id !== t.dataset.wis); teken() }
        catch { alert('Verwijderen lukt nu niet. Probeer opnieuw.') }
      }
    }
  }
  // Zonder verblijf (of als de rijtijden niet lukken): vanaf Ferragudo met 2 uur rijden.
  const vanafFerragudo = (b: Blok) => b.rij ?? null
  const v = leesVerblijf()
  if (!v) { kop(null); doelTonen(vanafFerragudo, 120); return }
  kop(v, 'rijtijden berekenen…')
  await andereLanden(p.dagen, v, g.gemaakt)
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
