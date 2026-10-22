// Surfspots op de kaart: per gekozen dag de spots waar minstens één gekozen plank minstens 3 uur na elkaar goed is
// (score >= kaartdrempel). Het cijfer is de hoogste gemiddelde score van die tijdvakken over de gekozen planken.
// Tik op een spot: per plank van wanneer tot wanneer, en de omstandigheden op het gekozen tijdstip.

import maplibregl from 'maplibre-gl'

export const PLANKEN: Record<string, string> = {
  LB: 'Longboard', MM: 'Minimal', MID: 'Midlength', GR: 'Groveler', FI: 'Fish', SB: 'Shortboard', SU: 'Step-up', GUN: 'Gun',
}

type Vak = [string, string, number] // van, tot (ISO, UTC), gemiddelde score

interface SpotIndex {
  run: string
  drempel: number
  min_uren: number
  spots: { id: number; naam: string; lat: number; lon: number; tijdvakken: Record<string, Vak[]>; max: Record<string, number> }[]
}

interface UurRij {
  t: string
  wind_kn: number
  wind_rel: number
  stoot_kn: number
  golven: Record<string, [number, number, number] | null>
  Hb: number
  vlaggen?: string[]
  getij: { h: number; stand: number; bakje: string } | null
  expert: string[]
}

interface SpotDetail {
  naam: string
  richting: number
  soort: string | null
  herkomst: Record<string, string>
  golfbron: string
  uur: UurRij[]
}

const KOMPAS = ['N', 'NNO', 'NO', 'ONO', 'O', 'OZO', 'ZO', 'ZZO', 'Z', 'ZZW', 'ZW', 'WZW', 'W', 'WNW', 'NW', 'NNW']
const kompas = (deg: number) => KOMPAS[Math.round(deg / 22.5) % 16]
const fmt = (x: number, d = 1) => x.toLocaleString('nl-NL', { minimumFractionDigits: d, maximumFractionDigits: d })
const uurFmt = new Intl.DateTimeFormat('nl-NL', { hour: '2-digit', minute: '2-digit' })
const dagFmt = new Intl.DateTimeFormat('nl-NL', { weekday: 'long', day: 'numeric', month: 'long' })
const dagSleutel = (d: Date) => `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`
const rond = (x: number) => Math.floor(x + 0.5) // ,5 naar boven (regels)
const relWoord = (rel: number) => (rel <= 45 ? 'aflandig' : rel < 135 ? 'zijwind' : 'aanlandig')

export class Spots {
  private index: SpotIndex | null = null
  private detail = new Map<number, Promise<SpotDetail>>()
  private dag = new Date()
  private tijd = new Date()
  planken = new Set(Object.keys(PLANKEN))
  private popup = new maplibregl.Popup({ className: 'punt spot-pop', maxWidth: '300px', closeOnClick: true })

  constructor(private map: maplibregl.Map, private base: string) {}

  private markers = new Map<number, maplibregl.Marker>()

  async load() {
    const r = await fetch(`${this.base}/index.json`, { cache: 'no-cache' })
    if (!r.ok) return
    this.index = await r.json()
    this.update()
  }

  /** Gekozen tijdstip (van de tijdlijn): de dag bepaalt welke spots er staan. */
  setTime(iso: string) {
    this.tijd = new Date(iso)
    const nieuweDag = dagSleutel(this.tijd) !== dagSleutel(this.dag)
    this.dag = this.tijd
    if (nieuweDag) this.update()
  }

  setPlanken(p: Set<string>) {
    this.planken = p
    this.update()
  }

  /** Markers bijwerken: een rondje met het cijfer per spot die op de gekozen dag goed is. */
  private update() {
    const zichtbaar = new Set<number>()
    for (const s of this.index?.spots ?? []) {
      const v = this.vakkenOpDag(s.tijdvakken)
      const best = Math.max(0, ...Object.values(v).flat().map((x) => x[2]))
      if (!best) continue
      zichtbaar.add(s.id)
      let m = this.markers.get(s.id)
      if (!m) {
        const el = document.createElement('button')
        el.className = 'spot'
        el.setAttribute('aria-label', s.naam)
        el.title = s.naam
        el.addEventListener('click', (e) => {
          e.stopPropagation()
          this.toon(s.id, [s.lon, s.lat])
        })
        m = new maplibregl.Marker({ element: el }).setLngLat([s.lon, s.lat]).addTo(this.map)
        this.markers.set(s.id, m)
      }
      m.getElement().textContent = String(rond(best))
    }
    for (const [id, m] of this.markers) {
      if (!zichtbaar.has(id)) {
        m.remove()
        this.markers.delete(id)
      }
    }
  }

  /** Goede tijdvakken van een spot op de gekozen dag, per gekozen plank (op lokale tijd). */
  private vakkenOpDag(tv: Record<string, Vak[]>): Record<string, Vak[]> {
    const uit: Record<string, Vak[]> = {}
    const d = dagSleutel(this.dag)
    for (const p of this.planken) {
      const v = (tv[p] ?? []).filter(([van, tot]) => dagSleutel(new Date(van)) === d || dagSleutel(new Date(tot)) === d)
      if (v.length) uit[p] = v
    }
    return uit
  }

  private haal(id: number): Promise<SpotDetail> {
    let p = this.detail.get(id)
    if (!p) {
      p = fetch(`${this.base}/${id}.json`).then((r) => r.json())
      this.detail.set(id, p)
    }
    return p
  }

  private async toon(id: number, xy: [number, number]) {
    const s = this.index!.spots.find((x) => x.id === id)!
    const v = this.vakkenOpDag(s.tijdvakken)
    const rijen = Object.entries(v)
      .sort((a, b) => Math.max(...b[1].map((x) => x[2])) - Math.max(...a[1].map((x) => x[2])))
      .map(([p, vs]) => `<tr><th>${PLANKEN[p]}</th><td>${vs.map(([van, tot, g]) =>
        `${uurFmt.format(new Date(van))}–${uurFmt.format(new Date(tot))} <b>${rond(g)}</b>`).join('<br>')}</td></tr>`)
    this.popup.setLngLat(xy).setHTML(`<div class="punt-kop">${s.naam}</div>
      <div class="punt-coord">${dagFmt.format(this.dag)} · goed (4 of 5) per plank</div>
      <table>${rijen.join('')}</table><div class="spot-nu">…</div>`).addTo(this.map)
    const d = await this.haal(id)
    // Omstandigheden op het gekozen tijdstip (dichtstbijzijnde uur).
    const t = this.tijd.getTime()
    const r = d.uur.reduce((a, b) => (Math.abs(Date.parse(b.t) - t) < Math.abs(Date.parse(a.t) - t) ? b : a), d.uur[0])
    const el = this.popup.getElement()?.querySelector('.spot-nu')
    if (!el || !r) return
    const golf = (naam: string, g: [number, number, number] | null) =>
      g && g[0] >= 0.1 ? `<tr><th>${naam}</th><td>${fmt(g[0])} m · ${fmt(g[2], 0)} s · uit ${kompas(g[1])}</td></tr>` : ''
    el.innerHTML = `<div class="punt-coord">om ${uurFmt.format(new Date(r.t))} · strand kijkt naar ${kompas(d.richting)}</div><table>
      ${golf('Deining', r.golven.deining1)}${golf('Deining 2', r.golven.deining2)}${golf('Windzee', r.golven.windzee)}
      <tr><th>Breker</th><td>${fmt(r.Hb)} m</td></tr>
      <tr><th>Wind</th><td>${fmt(r.wind_kn, 0)} kn (stoten ${fmt(r.stoot_kn, 0)}) · ${relWoord(r.wind_rel)}</td></tr>
      ${r.getij ? `<tr><th>Getij</th><td>${r.getij.bakje} (${fmt(r.getij.stand * 100, 0)}%)</td></tr>` : ''}
      ${r.vlaggen?.length ? `<tr><th>Let op</th><td>${r.vlaggen.join(', ')}</td></tr>` : ''}
      ${r.expert.length ? `<tr><th>Ervaren</th><td>${r.expert.join(', ')}</td></tr>` : ''}
      </table><div class="punt-bron">golven: ${d.golfbron.includes('ibi') ? 'Copernicus IBI (per uur)' : 'Copernicus MFWAM'} · wind: ECMWF · getij: EOT20 · strandhelling: ${d.herkomst.tanb ?? '—'}</div>`
  }
}
