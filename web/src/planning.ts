// Tabblad Planning: 4 weken, per dag één resultaat (pipeline/site/planning.py):
// golfsurfen, anders stille waters / e-foil, anders windsurfles, anders klimmen, anders niets.
import './style.css'

interface Keuze { sport: 'golfsurfen' | 'stil' | 'windsurf' | 'klim'; plek: string; id: string | null; van: string; tot: string; km: number; rij: number | null; score?: number }
interface Dag { dag: string; voorspelling: boolean; keuze?: Keuze | null }

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
    naam: 'Klimmen', kleur: '#6B4226',
    links: [
      { url: 'https://climbingalgarve.pt/trips/climbing-in-lagos/', label: 'Climbing Algarve · halve dag', uitleg: '4 u · routes IV+ tot 6a+ · beginners' },
      { url: 'https://climbingalgarve.pt/courses/top-rope-course/', label: 'Top rope · volledige dag', uitleg: '8 u' },
      { url: 'https://www.amea.pt/?page_id=84', label: 'AMEA · cursus 3 dagen', uitleg: 'vaste data, niet weersafhankelijk' },
    ],
  },
}

const chip = (l: Link) => `<a class="schoolpil" href="${l.url}" target="_blank" rel="noopener" title="${esc(l.uitleg ?? l.label)}">${esc(l.label)}</a>`
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
      ${s.links.length ? `<div class="pillen">${s.links.map(chip).join('')}</div>` : ''}
      ${s.extra ? `<details><summary>${s.extra.titel}</summary><div class="pillen">${s.extra.links.map(chip).join('')}</div></details>` : ''}
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

function toon(dagen: Dag[]) {
  const met = dagen.filter((d) => d.voorspelling)
  const zonder = dagen.filter((d) => !d.voorspelling)
  let html = '', kop = ''
  for (const d of met) {
    const w = weekKop(d.dag, dagen[0].dag)
    if (w !== kop) { html += `<h2 class="week">${w}</h2>`; kop = w }
    html += d.keuze ? plan(d, d.keuze) : niets(d)
  }
  if (zonder.length) {
    const a = zonder[0].dag, b = zonder[zonder.length - 1].dag
    html += `<p class="nogniet">${ICOON.wolk} ${datumTekst(a, { day: 'numeric', month: 'short' })} – ${datumTekst(b, { day: 'numeric', month: 'short' })}:
      nog geen voorspelling</p>`
  }
  return html
}

async function start() {
  const doel = document.getElementById('dagen')!
  try {
    const g = await (await fetch('data/index.json', { cache: 'no-store' })).json()
    const p = await (await fetch(`data/planning.json?v=${encodeURIComponent(g.gemaakt)}`)).json()
    doel.innerHTML = toon(p.dagen as Dag[])
  } catch {
    doel.innerHTML = '<p class="rustig">De planning kon niet worden geladen.</p>'
  }
}
start()
