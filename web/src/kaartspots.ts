// Stranden en spots op de kaart, bovenop de animatie van wind en golven. Elk strand krijgt een bolletje met het cijfer
// van de dag (de hoogste score overdag met je planken). Groen: minstens 3 uur na elkaar een 4 of 5 (ga surfen);
// grijs: niet goed genoeg. Bolletjes die elkaar zouden bedekken worden verborgen, de beste eerst: hoe verder je
// inzoomt, hoe meer stranden. Ingezoomd ook de namen.

import maplibregl from 'maplibre-gl'
import { besteOpDag, dagCijfer, esc, een, komma, type SpotIndex, type SpotKort } from './spots'

const NAMEN_VANAF_ZOOM = 9

export class KaartSpots {
  private markers = new Map<number, { m: maplibregl.Marker; prio: number }>()
  private dag = ''
  private planken: string[] = []
  private gekozen = -1

  constructor(private map: maplibregl.Map, private data: () => SpotIndex | null, private open: (s: SpotKort) => void) {
    map.on('moveend', () => this.schik())
  }

  zet(dag: string, planken: string[]) {
    this.dag = dag
    this.planken = planken
    this.update()
  }

  kies(id: number) {
    this.gekozen = id
    for (const [k, { m }] of this.markers) m.getElement().setAttribute('aria-pressed', String(k === id))
    this.schik()
  }

  private update() {
    const index = this.data()
    if (!index) return
    for (const s of index.spots) {
      const goed = besteOpDag(s, this.dag, this.planken)
      const cijfer = een(goed || dagCijfer(s, this.dag, this.planken, index.planken))
      let x = this.markers.get(s.id)
      if (!x) {
        const el = document.createElement('button')
        el.type = 'button'
        el.addEventListener('click', (e) => {
          e.stopPropagation()
          this.open(s)
        })
        x = { m: new maplibregl.Marker({ element: el, anchor: 'left' }).setLngLat([s.lon, s.lat]).addTo(this.map), prio: 0 }
        this.markers.set(s.id, x)
      }
      const el = x.m.getElement()
      // Alleen onze eigen klassen wisselen: die van MapLibre (maplibregl-marker ...) zetten het bolletje op zijn plaats.
      el.classList.remove('s4', 's5', 'grijs')
      el.classList.add('spot', goed ? (cijfer >= 4.5 ? 's5' : 's4') : 'grijs')
      el.innerHTML = `<b>${cijfer ? komma(cijfer) : ''}</b><span>${esc(s.naam)}</span>`
      el.setAttribute('aria-label', `${s.naam}: ${goed ? `ga surfen, score ${komma(cijfer)}` : `niet goed (hoogste score ${cijfer ? komma(cijfer) : 'onbekend'})`}`)
      el.setAttribute('aria-pressed', String(s.id === this.gekozen))
      x.prio = (goed ? 100 : 0) + (goed || dagCijfer(s, this.dag, this.planken, index.planken))
      el.style.zIndex = String(Math.round(x.prio))
    }
    this.schik()
  }

  /** Bolletjes en namen die elkaar zouden bedekken verbergen: de gekozen spot en de beste scores eerst. */
  private schik() {
    const namen = this.map.getZoom() >= NAMEN_VANAF_ZOOM
    this.map.getContainer().classList.toggle('met-namen', namen)
    const lijst = [...this.markers.entries()].sort((a, b) =>
      Number(b[0] === this.gekozen) - Number(a[0] === this.gekozen) || b[1].prio - a[1].prio)
    const bol: DOMRect[] = []
    const tekst: DOMRect[] = []
    const raakt = (r: DOMRect, in_: DOMRect[], marge: number) =>
      in_.some((q) => r.left < q.right + marge && r.right > q.left - marge && r.top < q.bottom + marge && r.bottom > q.top - marge)
    const w = this.map.getContainer().clientWidth, h = this.map.getContainer().clientHeight
    const vak = this.map.getContainer().getBoundingClientRect()
    for (const [, { m }] of lijst) {
      const el = m.getElement()
      el.style.visibility = 'visible'
      const b = (el.querySelector('b') as HTMLElement).getBoundingClientRect()
      const buiten = b.right < vak.left || b.left > vak.left + w || b.bottom < vak.top || b.top > vak.top + h
      if (buiten) continue
      if (raakt(b, bol, 1)) {
        el.style.visibility = 'hidden'
        continue
      }
      bol.push(b)
      const span = el.querySelector('span') as HTMLElement
      span.style.visibility = 'visible'
      if (namen) {
        const r = span.getBoundingClientRect()
        if (raakt(r, tekst, 2) || raakt(r, bol.slice(0, -1), 0)) span.style.visibility = 'hidden'
        else tekst.push(r)
      }
    }
  }
}
