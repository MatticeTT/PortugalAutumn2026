// Spots op de kaart, bovenop de animatie van wind en golven: goede spots als label met cijfer en naam; ingezoomd ook
// de andere stranden, grijs, zodat je elk strand terugvindt. Tik opent het blad van de spot.

import maplibregl from 'maplibre-gl'
import { besteOpDag, esc, rond, type SpotIndex, type SpotKort } from './spots'

const ALLES_VANAF_ZOOM = 8.5

export class KaartSpots {
  private markers = new Map<number, maplibregl.Marker>()
  private dag = ''
  private planken: string[] = []

  constructor(private map: maplibregl.Map, private data: () => SpotIndex | null, private open: (s: SpotKort) => void) {
    map.on('zoomend', () => this.update())
  }

  zet(dag: string, planken: string[]) {
    this.dag = dag
    this.planken = planken
    this.update()
  }

  private update() {
    const index = this.data()
    if (!index) return
    const alles = this.map.getZoom() >= ALLES_VANAF_ZOOM
    const zichtbaar = new Set<number>()
    for (const s of index.spots) {
      const best = besteOpDag(s, this.dag, this.planken)
      if (!best && !alles) continue
      zichtbaar.add(s.id)
      const sleutel = best ? `g${rond(best)}` : 'grijs'
      let m = this.markers.get(s.id)
      if (m && m.getElement().dataset.soort !== sleutel) {
        m.remove()
        m = undefined
      }
      if (!m) {
        const el = document.createElement('button')
        el.dataset.soort = sleutel
        el.className = best ? `spot-label c${rond(best)}` : 'spot-label grijs'
        el.innerHTML = best ? `<b>${rond(best)}</b>${esc(s.naam)}` : `<i></i>${esc(s.naam)}`
        el.setAttribute('aria-label', `${s.naam}${best ? `, score ${rond(best)}` : ', niet goed'}`)
        el.addEventListener('click', (e) => {
          e.stopPropagation()
          this.open(s)
        })
        m = new maplibregl.Marker({ element: el, anchor: 'left', offset: [-12, 0] }).setLngLat([s.lon, s.lat]).addTo(this.map)
        this.markers.set(s.id, m)
      }
      // Goede spots boven de grijze.
      m.getElement().style.zIndex = best ? String(10 + rond(best)) : '3'
    }
    for (const [id, m] of this.markers) {
      if (!zichtbaar.has(id)) {
        m.remove()
        this.markers.delete(id)
      }
    }
  }
}
