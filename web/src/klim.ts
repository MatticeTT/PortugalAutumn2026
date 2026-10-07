// Klimplekken op de kaart (OpenStreetMap, sport=climbing). Los van de surfberekening.
// Cirkel: donkerbruin muurklimmen, lichtbruin boulderen, met de graad ("5a–7b", of "?" als er geen is).
// Rode rand bij slecht weer in het gekozen uur (pipeline/klim/weer.py): het regent, of zandsteen na regen.
import type { GeoJSONSource, Map as Kaart } from 'maplibre-gl'
import { data, staat, toonDag, toonTijd, utc, vliegNaar } from './main'

export interface KlimPlek {
  id: string; n: string | null; s: 'M' | 'B'; x: number; y: number; g: string
  rots: string | null; richting: string | null; graden: Record<string, string | null>; w: string | null
}
interface Weer {
  neerslag: (number | null)[]; vocht: (number | null)[]; temp: (number | null)[]; wind: (number | null)[]
  sinds: (number | null)[]; regen24: (number | null)[]; terug: number
}

const KLEUR = { M: '#6B4226', B: '#B5803A' }
const SOORT = { M: 'Muurklimmen', B: 'Boulderen' }
const ROOD = '#e0242f'
let plekken: KlimPlek[] = []
let rood: string[] = []
let kaart: Kaart
const weerCache = new Map<string, Promise<Weer>>()
let open: KlimPlek | null = null

const el = () => document.getElementById('fiche')!
const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]!)

// Een pil met de graad erin, gemaakt zodra de kaart ze nodig heeft (naam: k|M|1|5a–7b).
function pil(soort: 'M' | 'B', randRood: boolean, tekst: string) {
  const ratio = 2, h = 26
  const c = document.createElement('canvas')
  const g = c.getContext('2d')!
  const font = '700 13px system-ui, sans-serif'
  g.font = font
  const w = Math.max(h, Math.ceil(g.measureText(tekst).width) + 18)
  c.width = w * ratio; c.height = h * ratio
  g.scale(ratio, ratio)
  const r = h / 2
  const vorm = (i: number) => { g.beginPath(); g.roundRect(i, i, w - 2 * i, h - 2 * i, r - i) }
  vorm(0); g.fillStyle = randRood ? ROOD : 'rgba(20,32,43,0.55)'; g.fill()
  vorm(randRood ? 3 : 1.5); g.fillStyle = KLEUR[soort]; g.fill()
  g.font = font; g.fillStyle = '#fff'; g.textAlign = 'center'; g.textBaseline = 'middle'
  g.fillText(tekst, w / 2, h / 2 + 1)
  return { width: c.width, height: c.height, data: new Uint8Array(g.getImageData(0, 0, c.width, c.height).data.buffer) }
}

function features() {
  const i = staat.i
  return {
    type: 'FeatureCollection' as const,
    features: plekken.map((p, k) => ({
      type: 'Feature' as const, geometry: { type: 'Point' as const, coordinates: [p.x, p.y] },
      properties: { id: p.id, s: p.s, g: p.g, r: /[12]/.test(rood[k]?.[i] ?? '') ? 1 : 0 },
    })),
  }
}

export async function laadKlim(k: Kaart) {
  kaart = k
  try {
    ;[plekken, rood] = await Promise.all([data('klim/kaart.json'), data('klim/rood.json')])
  } catch { return } // nog geen klimdata
  kaart.on('styleimagemissing', (e) => {
    const m = /^k\|([MB])\|([01])\|(.*)$/.exec(e.id)
    if (m && !kaart.hasImage(e.id)) kaart.addImage(e.id, pil(m[1] as 'M' | 'B', m[2] === '1', m[3]), { pixelRatio: 2 })
  })
  kaart.addSource('klim', { type: 'geojson', data: features() })
  kaart.addLayer({ id: 'klim', type: 'symbol', source: 'klim',
    layout: { 'icon-image': ['concat', 'k|', ['get', 's'], '|', ['to-string', ['get', 'r']], '|', ['get', 'g']] as any,
      'icon-allow-overlap': false, 'symbol-sort-key': ['-', 0, ['get', 'r']] } })
  kaart.on('click', 'klim', (e) => { const id = e.features?.[0]?.properties?.id; if (id) openKlim(id) })
  kaart.on('mouseenter', 'klim', () => (kaart.getCanvas().style.cursor = 'pointer'))
  kaart.on('mouseleave', 'klim', () => (kaart.getCanvas().style.cursor = ''))
  const hash = decodeURIComponent(location.hash.slice(1))
  if (hash.startsWith('klim:')) openKlim(hash.slice(5))
}

export function ververs() {
  (kaart?.getSource('klim') as GeoJSONSource | undefined)?.setData(features())
  if (open && staat.open === `klim:${open.id}`) render()
}

export const isKlim = (id: string) => plekken.some((p) => p.id === id)

export function openKlim(id: string) {
  const p = plekken.find((q) => q.id === id)
  if (!p) return
  open = p
  staat.open = `klim:${id}`
  el().hidden = false
  history.replaceState(null, '', `#${encodeURIComponent(`klim:${id}`)}`)
  vliegNaar(p.x, p.y, true)
  render()
}

const ROTS: Record<string, string> = {
  limestone: 'kalksteen', granite: 'graniet', sandstone: 'zandsteen', quartzite: 'kwartsiet', schist: 'schist',
  gneiss: 'gneis', basalt: 'basalt', conglomerate: 'conglomeraat', slate: 'leisteen', marble: 'marmer',
  dolomite: 'dolomiet', volcanic: 'vulkanisch gesteente', greywacke: 'grauwacke',
}
const rotsTekst = (r: string | null) => r ? r.split(';').map((x) => ROTS[x.trim().toLowerCase()] ?? x.trim()).join(', ') : 'onbekend'
const WINDSTREEK: Record<string, string> = { N: 'N', S: 'Z', E: 'O', W: 'W' }
const richtingTekst = (r: string | null) => r ? r.split(';').map((x) => x.trim().toUpperCase().replace(/[NSEW]/g, (c) => WINDSTREEK[c])).join(', ') : 'onbekend'
const graadTekst = (lo: string | null, hi: string | null) => lo && hi ? (lo === hi ? lo : `${lo}–${hi}`) : lo || hi || 'onbekend'
const getal = (x: number | null | undefined, nd = 0) => (x == null ? '–' : x.toFixed(nd).replace('.', ','))

async function render() {
  const p = open!
  const i = staat.i
  const ms = utc(staat.index.tijd[i])
  const k = plekken.indexOf(p)
  let weer: Weer | null = null
  if (p.w) {
    if (!weerCache.has(p.w)) weerCache.set(p.w, data(`klim/weer/${p.w}.json`))
    weer = await weerCache.get(p.w)!
    if (open !== p || staat.i !== i) return
  }
  const r = rood[k]?.[i] ?? '-'
  const reden = r === '1' ? 'het regent' : r === '2' ? 'zandsteen is nog nat na regen' : ''
  const vocht = weer?.vocht[i]
  const nota = [
    vocht != null && vocht > 70 ? 'klam, minder grip' : '',
    weer?.regen24[i] && p.rots?.trim().toLowerCase() !== 'granite' ? 'rots kan nog nat zijn' : '',
  ].filter(Boolean)
  const sinds = weer?.sinds[i]
  const sindsTekst = weer == null || weer.neerslag[i] == null ? '–' : sinds == null ? `meer dan ${weer.terug + i} uur`
    : sinds === 0 ? 'regent nu' : `${sinds} uur`
  const rij = (a: string, b: string) => `<tr><th>${a}</th><td>${b}</td></tr>`
  el().innerHTML = `<button class="sluit" aria-label="Sluiten">×</button>
    <h2>${esc(p.n ?? 'Naam onbekend')}</h2>
    <div class="sub">${SOORT[p.s]} · ${toonDag(ms)}</div>
    <div class="klimkop" style="--kleur:${KLEUR[p.s]}"><span class="graadpil ${r === '1' || r === '2' ? 'rood' : ''}">${esc(p.g)}</span>
      ${reden ? `<b class="reden">Slecht weer: ${reden}</b>` : ''}</div>
    <table class="klimtabel">
      ${rij('Soort', SOORT[p.s])}
      ${rij('Graad Frans', esc(graadTekst(p.graden['french:min'], p.graden['french:max'])))}
      ${rij('Graad Font', esc(graadTekst(p.graden['font:min'], p.graden['font:max'])))}
      ${rij('Rotssoort', esc(rotsTekst(p.rots)))}
      ${rij('Wandrichting', esc(richtingTekst(p.richting)))}
    </table>
    <h3 class="kop">Weer om ${toonTijd(ms)}</h3>
    ${weer ? `<table class="klimtabel">
      ${rij('Neerslag', `${getal(weer.neerslag[i], 1)} mm`)}
      ${rij('Sinds de laatste regen', sindsTekst)}
      ${rij('Luchtvochtigheid', `${getal(vocht)}%`)}
      ${rij('Temperatuur', `${getal(weer.temp[i])} °C`)}
      ${rij('Wind', `${getal(weer.wind[i])} kn`)}
    </table>
    ${nota.length ? `<ul class="klimnota">${nota.map((n) => `<li>${n}</li>`).join('')}</ul>` : ''}`
    : '<p class="klein">Nog geen weer voor deze plek.</p>'}
    <p class="klein">Bron: <a href="https://www.openstreetmap.org/${esc(p.id)}" rel="noopener">OpenStreetMap</a> (ODbL),
      weer: Open-Meteo. Geen veiligheidsadvies.</p>`
  el().querySelector('.sluit')?.addEventListener('click', () => {
    open = null; staat.open = null; el().hidden = true; history.replaceState(null, '', location.pathname)
  })
}
