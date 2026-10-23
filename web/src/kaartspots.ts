// Spots op de kaart, bovenop de animatie van wind en golven: een bolletje met het cijfer (4 of 5) voor de spots die
// die dag minstens 3 uur goed zijn met je planken. Ingezoomd ook de andere stranden (klein en grijs) en de namen.

import maplibregl from 'maplibre-gl'
import { besteOpDag, esc, rond, type SpotIndex, type SpotKort } from './spots'

const ALLES_VANAF_ZOOM = 8.5
const NAMEN_VANAF_ZOOM = 9

export class KaartSpots {
  private markers = new Map<number, maplibregl.Marker>()
  private dag = ''
  private planken: string[] = []
  private gekozen = -1

  constructor(private map: maplibregl.Map, private data: () => SpotIndex | null, private open: (s: SpotKort) => void) {
    map.on('zoomend', () => this.update())
  }

  zet(dag: string, planken: string[]) {
    this.dag = dag
    this.planken = planken
    this.update()
  }

  kies(id: number) {
    this.gekozen = id
    for (const [k, m] of this.markers) m.getElement().setAttribute('aria-pressed', String(k === id))
  }

  private update() {
    const index = this.data()
    if (!index) return
    const z = this.map.getZoom()
    this.map.getContainer().classList.toggle('met-namen', z >= NAMEN_VANAF_ZOOM)
    const alles = z >= ALLES_VANAF_ZOOM
    const zichtbaar = new Set<number>()
    for (const s of index.spots) {
      const best = besteOpDag(s, this.dag, this.planken)
      if (!best && !alles) continue
      zichtbaar.add(s.id)
      const klasse = best ? `spot s${rond(best) >= 5 ? 5 : 4}` : 'spot grijs'
      let m = this.markers.get(s.id)
      if (!m) {
        const el = document.createElement('button')
        el.type = 'button'
        el.addEventListener('click', (e) => {
          e.stopPropagation()
          this.open(s)
        })
        m = new maplibregl.Marker({ element: el, anchor: 'left', offset: [-14, 0] }).setLngLat([s.lon, s.lat]).addTo(this.map)
        this.markers.set(s.id, m)
      }
      const el = m.getElement()
      el.className = klasse
      el.innerHTML = `<b>${best ? rond(best) : ''}</b><span>${esc(s.naam)}</span>`
      el.setAttribute('aria-label', `${s.naam}: ${best ? `score ${rond(best)}` : 'niet goed'}`)
      el.setAttribute('aria-pressed', String(s.id === this.gekozen))
      el.style.zIndex = best ? String(10 + rond(best)) : '3'
    }
    for (const [id, m] of this.markers) {
      if (!zichtbaar.has(id)) {
        m.remove()
        this.markers.delete(id)
      }
    }
  }
}
