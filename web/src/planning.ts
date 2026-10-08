// Tabblad Planning: 4 weken, één blok per dag; de blokken komen uit data/planning.json
// (pipeline/site/planning.py). Volgorde per dag: golfsurfen, stille waters / e-foil, windsurfles, klimmen.
import './style.css'

interface Blok { plek: string; id: string | null; van: string; tot: string; km: number; score?: number; beste?: boolean; dichtstbij?: boolean }
interface Dag { dag: string; voorspelling: boolean; golfsurfen?: Blok[]; stil?: Blok[]; windsurf?: Blok[]; klim?: Blok[] }

const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]!)
const fmtDag = new Intl.DateTimeFormat('nl-BE', { weekday: 'long', day: 'numeric', month: 'long', timeZone: 'UTC' })
const link = (url: string, tekst: string, uitleg = '') =>
  `<li><a href="${url}" target="_blank" rel="noopener">${esc(tekst)}</a>${uitleg ? ` <small>${esc(uitleg)}</small>` : ''}</li>`

const regel = (b: Blok, opStrand: boolean) => {
  const plek = opStrand && b.id ? `<a href="./#${encodeURIComponent(b.id)}">${esc(b.plek)}</a>` : esc(b.plek)
  const label = [b.beste ? 'beste' : '', b.dichtstbij ? 'dichtstbij' : ''].filter(Boolean).join(', ')
  return `<li>ideaal van <b>${b.van}</b> tot <b>${b.tot}</b> op ${plek} (${b.km} km)${label ? ` <span class="label">${label}</span>` : ''}</li>`
}
const blokken = (lijst: Blok[] | undefined, opStrand = false) =>
  lijst?.length ? `<ul class="blokken">${lijst.map((b) => regel(b, opStrand)).join('')}</ul>` : '<p class="niets">geen blok</p>'

function strandLinks(lijst: Blok[] | undefined) {
  const uniek = [...new Map((lijst ?? []).filter((b) => b.id).map((b) => [b.id, b])).values()]
  return uniek.map((b) => link(`./#${encodeURIComponent(b.id!)}`, `Strandpagina ${b.plek}`)).join('')
}

const EFOIL = link('https://www.efoilalgarve.com/', 'eFoil Algarve', 'WhatsApp +351 912 991 460, 1 u, beginners welkom, reserveren verplicht')
  + link('https://www.efoil-riders.com/pages/lesson-location-algarve-portugal', 'eFoil Riders', 'beginnerscursus 90 min')
const WINDSURF = link('https://algarvewatersport.com/en/lagos-windsurf-school/', 'Algarve Watersport – windsurfschool', 'Ria de Alvor, beginners, 2,5 u, start rond 10:00')
  + link('https://windsportscenter.com/lessons/', 'Windsports Center', 'beginners in de kleine lagune van Alvor, 3 u')
const KITE = link('https://www.eakitelagos.com/', 'EA Kite Lagos', 'heel het jaar open, Ria de Alvor')
  + link('https://kiteschoolportugal.com/kitesurfing-lessons/', 'Kite School Portugal')
  + link('https://alvorkitecenter.com/', 'Alvor Kite Center')
  + link('https://kitesurfschoolalgarve.com/', 'Kitesurf School Algarve')
  + link('https://algarvewatersport.com/en/kite-school-portugal/', 'Algarve Watersport – kiteschool', 'zegt zelf: oktober buiten seizoen, geen garantie')
const KLIM = link('https://climbingalgarve.pt/trips/climbing-in-lagos/', 'Climbing Algarve – Climbing in Lagos', 'halve dag 4 u, routes IV+ tot 6a+, beginners')
  + link('https://climbingalgarve.pt/courses/top-rope-course/', 'Climbing Algarve – Top rope course', 'volledige dag 8 u')
  + link('https://www.amea.pt/?page_id=84', 'AMEA – cursus van 3 dagen', 'vaste data, niet weersafhankelijk')

function dag(d: Dag) {
  const t = fmtDag.format(new Date(d.dag + 'T12:00:00Z'))
  const titel = t[0].toUpperCase() + t.slice(1)
  if (!d.voorspelling) return `<section class="dagblok leeg"><h2>${titel}</h2><p class="niets">nog geen voorspelling</p></section>`
  return `<section class="dagblok"><h2>${titel}</h2>
    <h3><span class="nr">1</span> Golfsurfen</h3>
    ${blokken(d.golfsurfen, true)}
    ${d.golfsurfen?.length ? `<ul class="links">${strandLinks(d.golfsurfen)}</ul>` : ''}
    <h3><span class="nr">2</span> Stille waters / e-foil</h3>
    ${blokken(d.stil, true)}
    ${d.stil?.length ? '<p class="nota">E-foil: vraag de school waar en of de les doorgaat.</p>' : ''}
    <ul class="links">${strandLinks(d.stil)}${EFOIL}</ul>
    <h3><span class="nr">3</span> Windsurfles (beginners)</h3>
    ${blokken(d.windsurf)}
    ${d.windsurf?.length ? '<p class="nota">De school bevestigt de avond ervoor of de les doorgaat.</p>' : ''}
    <ul class="links">${WINDSURF}</ul>
    <details><summary>Kite (geen eigen regel, de school beslist op de dag zelf)</summary><ul class="links">${KITE}</ul></details>
    <h3><span class="nr">4</span> Klimmen</h3>
    ${blokken(d.klim)}
    <ul class="links">${KLIM}</ul>
  </section>`
}

async function start() {
  const doel = document.getElementById('dagen')!
  try {
    const g = await (await fetch('data/index.json', { cache: 'no-store' })).json()
    const p = await (await fetch(`data/planning.json?v=${encodeURIComponent(g.gemaakt)}`)).json()
    doel.innerHTML = (p.dagen as Dag[]).map(dag).join('')
      + '<p class="klein">Boulderen wordt niet gepland: een beginnersniveau is niet te bevestigen.</p>'
  } catch {
    doel.innerHTML = '<p class="niets">De planning kon niet worden geladen.</p>'
  }
}
start()
