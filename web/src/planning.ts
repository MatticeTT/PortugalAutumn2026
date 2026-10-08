// Tabblad Planning: 4 weken, per dag één resultaat (pipeline/site/planning.py):
// golfsurfen, anders stille waters / e-foil, anders windsurfles, anders klimmen, anders niets.
import './style.css'

interface Keuze { sport: 'golfsurfen' | 'stil' | 'windsurf' | 'klim'; plek: string; id: string | null; van: string; tot: string; km: number; score?: number }
interface Dag { dag: string; voorspelling: boolean; keuze?: Keuze | null }

const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]!)
const fmt = (o: Intl.DateTimeFormatOptions) => new Intl.DateTimeFormat('nl-BE', { ...o, timeZone: 'UTC' })
const WEEKDAG = fmt({ weekday: 'short' }), DAGNR = fmt({ day: 'numeric' }), MAAND = fmt({ month: 'short' })

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

const chip = (l: Link) => `<a class="chip" href="${l.url}" target="_blank" rel="noopener" title="${esc(l.uitleg ?? l.label)}">${esc(l.label)}${l.uitleg ? `<small>${esc(l.uitleg)}</small>` : ''}</a>`

function datum(d: string) {
  const t = new Date(d + 'T12:00:00Z')
  return `<div class="datum"><span>${WEEKDAG.format(t)}</span><b>${DAGNR.format(t)}</b><span>${MAAND.format(t)}</span></div>`
}

function kaartje(d: Dag) {
  if (!d.voorspelling) return `<article class="dagkaart leeg">${datum(d.dag)}<p class="rustig">${ICOON.wolk} nog geen voorspelling</p></article>`
  const k = d.keuze
  if (!k) return `<article class="dagkaart leeg">${datum(d.dag)}<p class="rustig">–</p></article>`
  const s = SPORT[k.sport]
  const plek = k.id && (k.sport === 'golfsurfen' || k.sport === 'stil')
    ? `<a href="./#${encodeURIComponent(k.id)}">${esc(k.plek)}</a>` : esc(k.plek)
  const beeld = s.foto ? `<img src="foto/${s.foto}.webp" alt="">` : `<span class="icoonbeeld">${ICOON.rots}</span>`
  return `<article class="dagkaart" style="--kleur:${s.kleur}">
    ${datum(d.dag)}
    <div class="inhoud">
      <div class="kop">${beeld}<div><span class="sport">${s.naam}</span><span class="ideaal">ideaal</span></div></div>
      <ul class="feiten">
        <li>${ICOON.klok}<b>${k.van} – ${k.tot}</b></li>
        <li>${ICOON.plek}<span>${plek}</span></li>
        <li>${ICOON.afstand}<span>${k.km} km van Ferragudo</span></li>
      </ul>
      ${s.nota ? `<p class="nota">${ICOON.info}${s.nota}</p>` : ''}
      ${s.links.length ? `<div class="chips">${s.links.map(chip).join('')}</div>` : ''}
      ${s.extra ? `<details class="extra"><summary>${s.extra.titel}</summary><div class="chips">${s.extra.links.map(chip).join('')}</div></details>` : ''}
    </div>
  </article>`
}

async function start() {
  const doel = document.getElementById('dagen')!
  try {
    const g = await (await fetch('data/index.json', { cache: 'no-store' })).json()
    const p = await (await fetch(`data/planning.json?v=${encodeURIComponent(g.gemaakt)}`)).json()
    doel.innerHTML = (p.dagen as Dag[]).map(kaartje).join('')
  } catch {
    doel.innerHTML = '<p class="rustig">De planning kon niet worden geladen.</p>'
  }
}
start()
